import torch
import torch.nn.functional as F
import numpy as np
import json
import ast
from typing import List, Dict, Tuple, Optional
from constants import *


def formatting_prompts_func_mistral(examples):
    output_text = []
    for i in range(len(examples["query"])):
        query = examples["query"][i]
        decomposition = examples["decomposition"][i]
        from prompt import PROMPTS, MISTRAL_PROMPT
        text = MISTRAL_PROMPT % (PROMPTS["gqd_decomposition"].format(query=query)) + decomposition
        output_text.append(text)
    return output_text


def formatting_prompts_func_llama(examples):
    output_text = []
    for i in range(len(examples["query"])):
        query = examples["query"][i]
        decomposition = examples["decomposition"][i]
        from prompt import PROMPTS, LLAMA_PROMPT
        text = LLAMA_PROMPT % (PROMPTS["gqd_decomposition"].format(query=query)) + decomposition
        output_text.append(text)
    return output_text


def formatting_prompts_func_qwen(examples):
    output_text = []
    for i in range(len(examples["query"])):
        query = examples["query"][i]
        decomposition = examples["decomposition"][i]
        from prompt import PROMPTS, QWEN_PROMPT
        text = QWEN_PROMPT % (PROMPTS["gqd_decomposition"].format(query=query)) + decomposition
        output_text.append(text)
    return output_text


def parse_gqd_output(gqd_text: str) -> Dict[str, any]:
    try:
        gqd_text = gqd_text.strip()
        if gqd_text.startswith("```"):
            lines = gqd_text.split("\n")
            gqd_text = "\n".join(lines[1:-1]) if len(lines) > 2 else gqd_text
        
        try:
            result = json.loads(gqd_text)
        except:
            result = ast.literal_eval(gqd_text)
        
        is_complex = result.get("is_complex", False)
        sub_queries = result.get("sub_queries", [])
        parent_child = result.get("parent_child", [])
        
        dependencies = []
        for sq in sub_queries:
            deps = []
            for pc in parent_child:
                if pc.get("child") == sq:
                    deps.append(pc.get("parent"))
            dependencies.append(deps)
        
        return {
            "is_complex": is_complex,
            "subqueries": sub_queries,
            "dependencies": dependencies,
            "parent_child": parent_child,
            "valid": is_complex and len(sub_queries) > 0 or not is_complex
        }
    except:
        return {
            "is_complex": False,
            "subqueries": [],
            "dependencies": [],
            "parent_child": [],
            "valid": False
        }


def compute_retrieval_score(subquery: str, documents: List[str]) -> float:
    if not documents:
        return 0.0
    coverage = len(documents) / max(RETRIEVAL_TOP_K, 1)
    diversity = len(set(documents)) / max(len(documents), 1)
    return (coverage + diversity) / 2.0


def group_relative_normalize(values: torch.Tensor) -> torch.Tensor:
    if len(values) <= 1:
        return torch.zeros_like(values)
    mean = values.mean()
    std = values.std()
    if std < 1e-8:
        return torch.zeros_like(values)
    return (values - mean) / std


def compute_outcome_advantage(losses: torch.Tensor) -> torch.Tensor:
    rewards = -losses
    return group_relative_normalize(rewards)


def compute_process_advantage(
    losses_incremental: List[List[float]],
    subquery_positions: List[List[Tuple[int, int]]]
) -> List[torch.Tensor]:
    all_improvements = []
    for sample_losses in losses_incremental:
        for i in range(1, len(sample_losses)):
            improvement = -(sample_losses[i] - sample_losses[i-1])
            all_improvements.append(improvement)
    
    if not all_improvements:
        return [torch.zeros(1) for _ in losses_incremental]
    
    all_improvements = torch.tensor(all_improvements, dtype=torch.float32)
    normalized_improvements = group_relative_normalize(all_improvements)
    
    advantages = []
    idx = 0
    for sample_idx, sample_losses in enumerate(losses_incremental):
        sample_advantages = []
        for i in range(1, len(sample_losses)):
            sample_advantages.append(normalized_improvements[idx].item())
            idx += 1
        if sample_advantages:
            advantages.append(torch.tensor(sample_advantages, dtype=torch.float32))
        else:
            advantages.append(torch.zeros(1))
    return advantages


def assign_advantage_to_tokens(
    outcome_advantage: float,
    process_advantages: torch.Tensor,
    subquery_positions: List[Tuple[int, int]],
    sequence_length: int
) -> torch.Tensor:
    token_advantages = torch.full((sequence_length,), outcome_advantage)
    if len(process_advantages) > 0:
        for i, (start, end) in enumerate(subquery_positions):
            if i < len(process_advantages):
                cumulative_advantage = process_advantages[i:].sum().item()
                token_advantages[start:end] += cumulative_advantage
    return token_advantages


def compute_kl_divergence(
    log_probs_policy: torch.Tensor,
    log_probs_ref: torch.Tensor,
    reduction: str = 'mean'
) -> torch.Tensor:
    kl = log_probs_policy - log_probs_ref
    if reduction == 'mean':
        return kl.mean()
    elif reduction == 'sum':
        return kl.sum()
    else:
        return kl


def compute_ppo_loss(
    log_ratios: torch.Tensor,
    advantages: torch.Tensor,
    epsilon: float = DEFAULT_EPSILON_CLIP
) -> torch.Tensor:
    ratios = torch.exp(log_ratios)
    surr1 = ratios * advantages
    surr2 = torch.clamp(ratios, 1 - epsilon, 1 + epsilon) * advantages
    policy_loss = -torch.min(surr1, surr2).mean()
    return policy_loss


def sample_with_temperature(
    logits: torch.Tensor,
    temperature: float = DEFAULT_TEMPERATURE,
    top_p: float = DEFAULT_TOP_P
) -> torch.Tensor:
    logits = logits / temperature
    if top_p < 1.0:
        sorted_logits, sorted_indices = torch.sort(logits, descending=True, dim=-1)
        cumulative_probs = torch.cumsum(F.softmax(sorted_logits, dim=-1), dim=-1)
        sorted_indices_to_remove = cumulative_probs > top_p
        sorted_indices_to_remove[..., 1:] = sorted_indices_to_remove[..., :-1].clone()
        sorted_indices_to_remove[..., 0] = 0
        indices_to_remove = sorted_indices_to_remove.scatter(
            -1, sorted_indices, sorted_indices_to_remove
        )
        logits = logits.masked_fill(indices_to_remove, float('-inf'))
    probs = F.softmax(logits, dim=-1)
    next_token = torch.multinomial(probs, num_samples=1)
    return next_token


def create_topological_order(dependencies: List[List[str]], subqueries: List[str]) -> List[int]:
    n = len(subqueries)
    adj = [[] for _ in range(n)]
    in_degree = [0] * n
    
    for i, deps in enumerate(dependencies):
        for dep in deps:
            for j, subq in enumerate(subqueries):
                if dep.lower() in subq.lower() or subq.lower() in dep.lower():
                    adj[j].append(i)
                    in_degree[i] += 1
                    break
    
    queue = [i for i in range(n) if in_degree[i] == 0]
    topo_order = []
    
    while queue:
        node = queue.pop(0)
        topo_order.append(node)
        for neighbor in adj[node]:
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)
    
    if len(topo_order) != n:
        return list(range(n))
    return topo_order

