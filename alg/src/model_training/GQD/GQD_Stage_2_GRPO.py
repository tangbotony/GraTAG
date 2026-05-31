import argparse
import torch
import torch.nn.functional as F
import random
import os
import sys
import time
import numpy as np
from typing import List, Dict, Tuple
from dataclasses import dataclass
from transformers import AutoTokenizer, AutoModelForCausalLM
from datasets import load_dataset
from torch.utils.data import DataLoader
import wandb

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

from constants import *
from utils import (
    parse_gqd_output,
    group_relative_normalize,
    clip_rewards,
    compute_query_similarity,
    create_topological_order,
)
from prompt import PROMPTS
from retrieval import retrieve_documents

random_seed = 42
torch.manual_seed(random_seed)
random.seed(random_seed)
np.random.seed(random_seed)

parser = argparse.ArgumentParser()
parser.add_argument("--debug", action="store_true")
parser.add_argument("--model_path", type=str, required=True)
parser.add_argument("--dataset_path", type=str, required=True)
parser.add_argument("--output_dir", type=str, default=None)
parser.add_argument("--run_id", type=str, default=None)
parser.add_argument("--gen_model_path", type=str, default=None,
                    help="Path to the generation model M for reward computation. Defaults to ref model.")
parser.add_argument("--lr", type=float, default=DEFAULT_LEARNING_RATE_GRPO)
parser.add_argument("--batch_size", type=int, default=DEFAULT_BATCH_SIZE)
parser.add_argument("--num_epochs", type=int, default=DEFAULT_NUM_TRAIN_EPOCHS)
parser.add_argument("--max_steps", type=int, default=-1)
parser.add_argument("--K_samples", type=int, default=DEFAULT_K_SAMPLES)
parser.add_argument("--C_retrievals", type=int, default=DEFAULT_C_RETRIEVALS,
                    help="Number of independent retrievals per GQD candidate for reward averaging (Eq. 2)")
parser.add_argument("--beta_kl", type=float, default=DEFAULT_BETA_KL)
parser.add_argument("--epsilon_clip", type=float, default=DEFAULT_EPSILON_CLIP)
parser.add_argument("--reward_clip", type=float, default=DEFAULT_REWARD_CLIP,
                    help="Clip extreme rewards to [-reward_clip, reward_clip] for variance control")
parser.add_argument("--cache_similarity_threshold", type=float, default=DEFAULT_CACHE_SIMILARITY_THRESHOLD,
                    help="Sub-query similarity threshold for evidence cache reuse (BGE-M3 in production)")
parser.add_argument("--evidence_sample_ratio", type=float, default=DEFAULT_EVIDENCE_SAMPLE_RATIO,
                    help="Ratio of cached chunks to sample per independent retrieval round")
parser.add_argument("--temperature", type=float, default=DEFAULT_TEMPERATURE)
parser.add_argument("--top_p", type=float, default=DEFAULT_TOP_P)
parser.add_argument("--save_steps", type=int, default=100)
parser.add_argument("--logging_steps", type=int, default=10)

args = parser.parse_args()

wandb_cache_dir = root_prefix + "cache/GQD/wandb_cache"
project_name = "GQD-GRPO"
os.environ["WANDB_PROJECT"] = project_name
os.environ["WANDB_CACHE_DIR"] = wandb_cache_dir
if args.debug:
    os.environ["WANDB_DISABLED"] = "true"


@dataclass
class GQDSample:
    tokens: torch.Tensor
    text: str
    subqueries: List[str]
    dependencies: List[List[str]]
    valid: bool


class GRPOTrainer:
    def __init__(self, model, tokenizer, args):
        self.model = model
        self.tokenizer = tokenizer
        self.args = args

        self.ref_model = None
        self.gen_model = None
        self.evidence_cache: Dict[str, List[str]] = {}

        self.optimizer = torch.optim.AdamW(
            self.model.parameters(),
            lr=args.lr,
            weight_decay=0.01,
        )
        self.global_step = 0

    def save_reference_model(self):
        self.ref_model = type(self.model).from_pretrained(
            self.model.config._name_or_path,
            torch_dtype=self.model.dtype,
            device_map=self.model.device,
        )
        self.ref_model.load_state_dict(self.model.state_dict())
        self.ref_model.eval()
        for param in self.ref_model.parameters():
            param.requires_grad = False

    def _ensure_gen_model(self):
        if self.gen_model is not None:
            return
        if self.args.gen_model_path:
            self.gen_model = AutoModelForCausalLM.from_pretrained(
                self.args.gen_model_path,
                torch_dtype=self.model.dtype,
                device_map="auto" if torch.cuda.is_available() else None,
            )
            self.gen_model.eval()
            for param in self.gen_model.parameters():
                param.requires_grad = False
        else:
            if self.ref_model is None:
                self.save_reference_model()
            self.gen_model = self.ref_model
        
    def generate_samples(self, query: str, K: int) -> List[GQDSample]:
        samples = []
        prompt = PROMPTS["gqd_decomposition"].format(query=query)
        input_ids = self.tokenizer.encode(prompt, return_tensors="pt").to(self.model.device)
        
        for _ in range(K):
            with torch.no_grad():
                outputs = self.model.generate(
                    input_ids,
                    max_new_tokens=512,
                    temperature=self.args.temperature,
                    top_p=self.args.top_p,
                    do_sample=True,
                    pad_token_id=self.tokenizer.pad_token_id,
                )
                
                generated_ids = outputs[0]
                generated_text = self.tokenizer.decode(generated_ids, skip_special_tokens=False)
                parsed = parse_gqd_output(generated_text)
                
                sample = GQDSample(
                    tokens=generated_ids,
                    text=generated_text,
                    subqueries=parsed["subqueries"],
                    dependencies=parsed["dependencies"],
                    valid=parsed["valid"] and parsed.get("is_complex", False),
                )
                samples.append(sample)
        
        return samples
    
    def compute_reward_for_sample(self, query: str, sample: GQDSample, ground_truth: str) -> float:
        """
        Compute reward r_k for a GQD candidate via C independent retrievals (Eq. 2):
            r_k = (1/C) * sum_{c=1}^{C} log M(y | a_k^{(c)})
        where M is the generation model and a_k^{(c)} is the evidence from the c-th retrieval.
        """
        if not sample.valid or len(sample.subqueries) == 0:
            return -100.0

        self._ensure_gen_model()
        topo_order = create_topological_order(sample.dependencies, sample.subqueries)

        all_cached_docs = {}
        for idx in topo_order:
            subquery = sample.subqueries[idx]
            all_cached_docs[subquery] = self._retrieve_with_cache(subquery, query)

        log_likelihoods = []
        for c in range(self.args.C_retrievals):
            evidence = []
            for idx in topo_order:
                subquery = sample.subqueries[idx]
                cached = all_cached_docs[subquery]
                sampled_docs = self._sample_evidence_subset(cached)
                evidence.append({"subquery": subquery, "documents": sampled_docs})

            log_ll = self._compute_log_likelihood(query, evidence, ground_truth)
            log_likelihoods.append(log_ll)

        reward = sum(log_likelihoods) / len(log_likelihoods)
        return reward

    def _retrieve_with_cache(self, subquery: str, original_query: str) -> List[str]:
        cache_key = subquery.strip().lower()

        if cache_key in self.evidence_cache:
            return self.evidence_cache[cache_key]

        for cached_key, cached_docs in self.evidence_cache.items():
            if compute_query_similarity(cache_key, cached_key) > self.args.cache_similarity_threshold:
                self.evidence_cache[cache_key] = cached_docs
                return cached_docs

        try:
            docs = retrieve_documents(subquery, original_query)
        except Exception as e:
            print(f"Retrieval error for subquery '{subquery}': {e}")
            docs = []

        self.evidence_cache[cache_key] = docs
        return docs

    def _sample_evidence_subset(self, docs: List[str]) -> List[str]:
        if not docs:
            return []
        n_sample = max(1, int(len(docs) * self.args.evidence_sample_ratio))
        if n_sample >= len(docs):
            return list(docs)
        return random.sample(docs, n_sample)

    def _compute_log_likelihood(self, query: str, evidence: List[Dict], ground_truth: str) -> float:
        prompt = self._build_evidence_prompt(query, evidence)
        full_text = prompt + ground_truth

        prompt_ids = self.tokenizer.encode(prompt, return_tensors="pt")
        full_ids = self.tokenizer.encode(full_text, return_tensors="pt")
        prompt_len = prompt_ids.shape[1]

        if full_ids.shape[1] <= prompt_len:
            return -100.0

        full_ids = full_ids.to(self.gen_model.device)
        with torch.no_grad():
            outputs = self.gen_model(full_ids)
            logits = outputs.logits

        answer_logits = logits[:, prompt_len - 1:-1, :]
        answer_labels = full_ids[:, prompt_len:]

        log_probs = F.log_softmax(answer_logits, dim=-1)
        token_log_probs = torch.gather(log_probs, -1, answer_labels.unsqueeze(-1)).squeeze(-1)

        return token_log_probs.mean().item()

    def _build_evidence_prompt(self, query: str, evidence: List[Dict]) -> str:
        prompt = f"Question: {query}\n\nEvidence:\n"
        for item in evidence:
            prompt += f"\nSubquery: {item['subquery']}\n"
            for doc in item['documents']:
                prompt += f"- {doc}\n"
        prompt += "\nAnswer: "
        return prompt
    
    def compute_log_probs(self, tokens: torch.Tensor, model) -> torch.Tensor:
        if tokens.dim() == 1:
            tokens = tokens.unsqueeze(0)
        
        outputs = model(tokens)
        logits = outputs.logits[:, :-1, :]
        labels = tokens[:, 1:]
        
        log_probs = F.log_softmax(logits, dim=-1)
        token_log_probs = torch.gather(log_probs, -1, labels.unsqueeze(-1)).squeeze(-1)
        
        return token_log_probs.squeeze(0)
    
    def compute_grpo_loss(self, samples: List[GQDSample], rewards: torch.Tensor) -> torch.Tensor:
        """
        GRPO objective (Eq. 3-5):
            L = (1/K) sum_k [ (1/|g_k|) sum_t min(rho * A, clip(rho) * A) ] - beta * D_KL
        where advantages are group-normalized rewards (Eq. 3):
            A_k = (r_k - mu_r) / sigma_r
        and rho is the importance sampling ratio (Eq. 5):
            rho_{k,t} = pi_theta(g_{k,t} | q, g_{k,<t}) / pi_theta_old(g_{k,t} | q, g_{k,<t})
        """
        if self.ref_model is None:
            self.save_reference_model()

        advantages = group_relative_normalize(rewards)

        total_policy_loss = torch.tensor(0.0, device=self.model.device)
        total_kl = torch.tensor(0.0, device=self.model.device)
        valid_count = 0

        for sample, advantage in zip(samples, advantages):
            if not sample.valid:
                continue

            policy_log_probs = self.compute_log_probs(sample.tokens, self.model)

            with torch.no_grad():
                ref_log_probs = self.compute_log_probs(sample.tokens, self.ref_model)

            ratio = torch.exp(policy_log_probs - ref_log_probs.detach())

            adv_value = advantage.item()
            adv_tensor = torch.full_like(ratio, adv_value)

            surr1 = ratio * adv_tensor
            surr2 = torch.clamp(ratio, 1 - self.args.epsilon_clip, 1 + self.args.epsilon_clip) * adv_tensor
            sample_policy_loss = -torch.min(surr1, surr2).mean()

            sample_kl = (policy_log_probs - ref_log_probs.detach()).mean()

            total_policy_loss = total_policy_loss + sample_policy_loss
            total_kl = total_kl + sample_kl
            valid_count += 1

        if valid_count > 0:
            loss = total_policy_loss / valid_count + self.args.beta_kl * (total_kl / valid_count)
        else:
            loss = torch.tensor(0.0, device=self.model.device, requires_grad=True)

        return loss
    
    def train_step(self, batch: Dict) -> Dict:
        query = batch["query"]
        ground_truth = batch["answer"]

        samples = self.generate_samples(query, self.args.K_samples)

        raw_rewards = []
        for sample in samples:
            r_k = self.compute_reward_for_sample(query, sample, ground_truth)
            raw_rewards.append(r_k)

        rewards = torch.tensor(raw_rewards, dtype=torch.float32)

        rewards = clip_rewards(rewards, self.args.reward_clip)

        loss = self.compute_grpo_loss(samples, rewards)

        loss.backward()
        torch.nn.utils.clip_grad_norm_(self.model.parameters(), 1.0)
        self.optimizer.step()
        self.optimizer.zero_grad()

        self.global_step += 1

        return {
            "loss": loss.item(),
            "mean_reward": rewards.mean().item(),
            "std_reward": rewards.std().item() if len(rewards) > 1 else 0.0,
            "num_valid": sum(1 for s in samples if s.valid),
            "cache_size": len(self.evidence_cache),
        }
    
    def save_checkpoint(self, output_dir: str):
        os.makedirs(output_dir, exist_ok=True)
        self.model.save_pretrained(output_dir)
        self.tokenizer.save_pretrained(output_dir)
        
        state = {
            "global_step": self.global_step,
            "optimizer_state": self.optimizer.state_dict(),
        }
        torch.save(state, os.path.join(output_dir, "training_state.pt"))


def main():
    print("Initializing GQD GRPO Training")
    
    tokenizer = AutoTokenizer.from_pretrained(args.model_path)
    tokenizer.padding_side = "right"
    tokenizer.pad_token_id = tokenizer.eos_token_id
    
    print(f"Loading model: {args.model_path}")
    model = AutoModelForCausalLM.from_pretrained(
        args.model_path,
        torch_dtype=torch.bfloat16 if torch.cuda.is_available() else torch.float32,
        device_map="auto" if torch.cuda.is_available() else None,
    )
    model.train()
    
    print(f"Loading dataset: {args.dataset_path}")
    dataset = load_dataset("json", data_files=args.dataset_path)["train"]
    print(f"Loaded {len(dataset)} training examples")
    
    trainer = GRPOTrainer(
        model=model,
        tokenizer=tokenizer,
        args=args,
    )
    
    run_id = args.run_id if args.run_id else str(int(time.time()))
    output_dir = args.output_dir if args.output_dir else (root_prefix + f"cache/GQD/stage2_{run_id}")
    
    if not args.debug:
        wandb.init(
            project=project_name,
            name=f"grpo_K{args.K_samples}_C{args.C_retrievals}_lr{args.lr}_{run_id}",
            config=vars(args),
        )

    print("Starting GRPO training...")
    print(f"K samples: {args.K_samples}, C retrievals: {args.C_retrievals}, "
          f"LR: {args.lr}, Beta KL: {args.beta_kl}, Reward clip: {args.reward_clip}")
    
    step = 0
    for epoch in range(args.num_epochs):
        for batch_idx, batch in enumerate(dataset):
            metrics = trainer.train_step(batch)
            
            if step % args.logging_steps == 0:
                print(f"Step {step}: loss={metrics['loss']:.4f}, reward={metrics['mean_reward']:.4f}")
                if not args.debug:
                    wandb.log(metrics, step=step)
            
            if step % args.save_steps == 0 and step > 0:
                checkpoint_dir = os.path.join(output_dir, f"checkpoint-{step}")
                trainer.save_checkpoint(checkpoint_dir)
                print(f"Saved checkpoint: {checkpoint_dir}")
            
            step += 1
            if args.max_steps > 0 and step >= args.max_steps:
                break
        
        if args.max_steps > 0 and step >= args.max_steps:
            break
    
    final_dir = os.path.join(output_dir, "final_model")
    trainer.save_checkpoint(final_dir)
    print(f"Training complete! Model saved: {final_dir}")
    
    if not args.debug:
        wandb.finish()


if __name__ == "__main__":
    main()
