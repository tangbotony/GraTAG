# coding=utf-8
# Copyright 2023 Mistral AI and the HuggingFace Inc. team. All rights reserved.
#
# This code is based on EleutherAI's GPT-NeoX library and the GPT-NeoX
# and OPT implementations in this library. It has been modified from its
# original forms to accommodate minor architectural differences compared
# to GPT-NeoX and OPT used by the Meta AI team that trained the model.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""PyTorch Mistral model."""

from collections import defaultdict
import math
from typing import List, Optional, Tuple, Union

import torch
import torch.utils.checkpoint
from torch import nn
from torch.nn import BCEWithLogitsLoss, CrossEntropyLoss, MSELoss
import wandb
import numpy as np
import torch.nn.functional as F
from ...activations import ACT2FN
from ...cache_utils import Cache, DynamicCache, SlidingWindowCache, StaticCache
from ...modeling_attn_mask_utils import AttentionMaskConverter
from ...modeling_outputs import (
    BaseModelOutputWithPast,
    CausalLMOutputWithPast,
    SequenceClassifierOutputWithPast,
    TokenClassifierOutput,
)
from ...modeling_utils import PreTrainedModel
from ...utils import (
    add_start_docstrings,
    add_start_docstrings_to_model_forward,
    is_flash_attn_2_available,
    is_flash_attn_greater_or_equal_2_10,
    logging,
    replace_return_docstrings,
)
from .configuration_mistral import MistralConfig


if is_flash_attn_2_available():
    from ...modeling_flash_attention_utils import _flash_attention_forward

logger = logging.get_logger(__name__)

_CONFIG_FOR_DOC = "MistralConfig"


# Copied from transformers.models.llama.modeling_llama.LlamaRMSNorm with Llama->Mistral
class MistralRMSNorm(nn.Module):
    def __init__(self, hidden_size, eps=1e-6):
        """
        MistralRMSNorm is equivalent to T5LayerNorm
        """
        super().__init__()
        self.weight = nn.Parameter(torch.ones(hidden_size))
        self.variance_epsilon = eps

    def forward(self, hidden_states):
        input_dtype = hidden_states.dtype
        hidden_states = hidden_states.to(torch.float32)
        variance = hidden_states.pow(2).mean(-1, keepdim=True)
        hidden_states = hidden_states * torch.rsqrt(variance + self.variance_epsilon)
        return self.weight * hidden_states.to(input_dtype)


class MistralRotaryEmbedding(nn.Module):
    def __init__(self, dim, max_position_embeddings=2048, base=10000, device=None):
        super().__init__()

        self.dim = dim
        self.max_position_embeddings = max_position_embeddings
        self.base = base
        inv_freq = 1.0 / (self.base ** (torch.arange(0, self.dim, 2, dtype=torch.int64).float().to(device) / self.dim))
        self.register_buffer("inv_freq", inv_freq, persistent=False)

    @torch.no_grad()
    # copied from transformers.models.llama.modeling_llama.LlamaRotaryEmbedding.forward
    # TODO(joao): add me back asap :)
    def forward(self, x, position_ids):
        # x: [bs, num_attention_heads, seq_len, head_size]
        inv_freq_expanded = self.inv_freq[None, :, None].float().expand(position_ids.shape[0], -1, 1)
        position_ids_expanded = position_ids[:, None, :].float()
        # Force float32 since bfloat16 loses precision on long contexts
        # See https://github.com/huggingface/transformers/pull/29285
        device_type = x.device.type
        device_type = device_type if isinstance(device_type, str) and device_type != "mps" else "cpu"
        with torch.autocast(device_type=device_type, enabled=False):
            freqs = (inv_freq_expanded.float() @ position_ids_expanded.float()).transpose(1, 2)
            emb = torch.cat((freqs, freqs), dim=-1)
            cos = emb.cos()
            sin = emb.sin()
        return cos.to(dtype=x.dtype), sin.to(dtype=x.dtype)


# Copied from transformers.models.llama.modeling_llama.rotate_half
def rotate_half(x):
    """Rotates half the hidden dims of the input."""
    x1 = x[..., : x.shape[-1] // 2]
    x2 = x[..., x.shape[-1] // 2 :]
    return torch.cat((-x2, x1), dim=-1)


# Copied from transformers.models.llama.modeling_llama.apply_rotary_pos_emb
def apply_rotary_pos_emb(q, k, cos, sin, position_ids=None, unsqueeze_dim=1):
    """Applies Rotary Position Embedding to the query and key tensors.

    Args:
        q (`torch.Tensor`): The query tensor.
        k (`torch.Tensor`): The key tensor.
        cos (`torch.Tensor`): The cosine part of the rotary embedding.
        sin (`torch.Tensor`): The sine part of the rotary embedding.
        position_ids (`torch.Tensor`, *optional*):
            Deprecated and unused.
        unsqueeze_dim (`int`, *optional*, defaults to 1):
            The 'unsqueeze_dim' argument specifies the dimension along which to unsqueeze cos[position_ids] and
            sin[position_ids] so that they can be properly broadcasted to the dimensions of q and k. For example, note
            that cos[position_ids] and sin[position_ids] have the shape [batch_size, seq_len, head_dim]. Then, if q and
            k have the shape [batch_size, heads, seq_len, head_dim], then setting unsqueeze_dim=1 makes
            cos[position_ids] and sin[position_ids] broadcastable to the shapes of q and k. Similarly, if q and k have
            the shape [batch_size, seq_len, heads, head_dim], then set unsqueeze_dim=2.
    Returns:
        `tuple(torch.Tensor)` comprising of the query and key tensors rotated using the Rotary Position Embedding.
    """
    cos = cos.unsqueeze(unsqueeze_dim)
    sin = sin.unsqueeze(unsqueeze_dim)
    q_embed = (q * cos) + (rotate_half(q) * sin)
    k_embed = (k * cos) + (rotate_half(k) * sin)
    return q_embed, k_embed


class MistralMLP(nn.Module):
    def __init__(self, config):
        super().__init__()
        self.hidden_size = config.hidden_size
        self.intermediate_size = config.intermediate_size
        self.gate_proj = nn.Linear(self.hidden_size, self.intermediate_size, bias=False)
        self.up_proj = nn.Linear(self.hidden_size, self.intermediate_size, bias=False)
        self.down_proj = nn.Linear(self.intermediate_size, self.hidden_size, bias=False)
        self.act_fn = ACT2FN[config.hidden_act]

    def forward(self, hidden_state):
        return self.down_proj(self.act_fn(self.gate_proj(hidden_state)) * self.up_proj(hidden_state))


# Copied from transformers.models.llama.modeling_llama.repeat_kv
def repeat_kv(hidden_states: torch.Tensor, n_rep: int) -> torch.Tensor:
    """
    This is the equivalent of torch.repeat_interleave(x, dim=1, repeats=n_rep). The hidden states go from (batch,
    num_key_value_heads, seqlen, head_dim) to (batch, num_attention_heads, seqlen, head_dim)
    """
    batch, num_key_value_heads, slen, head_dim = hidden_states.shape
    if n_rep == 1:
        return hidden_states
    hidden_states = hidden_states[:, :, None, :, :].expand(batch, num_key_value_heads, n_rep, slen, head_dim)
    return hidden_states.reshape(batch, num_key_value_heads * n_rep, slen, head_dim)


class MistralAttention(nn.Module):
    """
    Multi-headed attention from 'Attention Is All You Need' paper. Modified to use sliding window attention: Longformer
    and "Generating Long Sequences with Sparse Transformers".
    """

    def __init__(self, config: MistralConfig, layer_idx: Optional[int] = None):
        super().__init__()
        self.config = config
        self.layer_idx = layer_idx
        if layer_idx is None:
            logger.warning_once(
                f"Instantiating {self.__class__.__name__} without passing a `layer_idx` is not recommended and will "
                "lead to errors during the forward call if caching is used. Please make sure to provide a `layer_idx` "
                "when creating this class."
            )

        self.attention_dropout = config.attention_dropout
        self.hidden_size = config.hidden_size
        self.num_heads = config.num_attention_heads
        self.head_dim = config.head_dim
        self.num_key_value_heads = config.num_key_value_heads
        self.num_key_value_groups = self.num_heads // self.num_key_value_heads
        self.max_position_embeddings = config.max_position_embeddings
        self.rope_theta = config.rope_theta
        self.is_causal = True

        self.q_proj = nn.Linear(self.hidden_size, self.num_heads * self.head_dim, bias=False)
        self.k_proj = nn.Linear(self.hidden_size, self.num_key_value_heads * self.head_dim, bias=False)
        self.v_proj = nn.Linear(self.hidden_size, self.num_key_value_heads * self.head_dim, bias=False)
        self.o_proj = nn.Linear(self.num_heads * self.head_dim, self.hidden_size, bias=False)

        self.rotary_emb = MistralRotaryEmbedding(
            self.head_dim,
            max_position_embeddings=self.max_position_embeddings,
            base=self.rope_theta,
        )

    def forward(
        self,
        hidden_states: torch.Tensor,
        attention_mask: Optional[torch.Tensor] = None,
        position_ids: Optional[torch.LongTensor] = None,
        past_key_value: Optional[Cache] = None,
        output_attentions: bool = False,
        use_cache: bool = False,
        cache_position: Optional[torch.LongTensor] = None,
    ) -> Tuple[torch.Tensor, Optional[torch.Tensor], Optional[Tuple[torch.Tensor]]]:
        bsz, q_len, _ = hidden_states.size()

        query_states = self.q_proj(hidden_states)
        key_states = self.k_proj(hidden_states)
        value_states = self.v_proj(hidden_states)

        query_states = query_states.view(bsz, q_len, self.num_heads, self.head_dim).transpose(1, 2)
        key_states = key_states.view(bsz, q_len, self.num_key_value_heads, self.head_dim).transpose(1, 2)
        value_states = value_states.view(bsz, q_len, self.num_key_value_heads, self.head_dim).transpose(1, 2)

        cos, sin = self.rotary_emb(value_states, position_ids)
        query_states, key_states = apply_rotary_pos_emb(query_states, key_states, cos, sin)

        if past_key_value is not None:
            # sin and cos are specific to RoPE models; cache_position needed for the static cache
            cache_kwargs = {"sin": sin, "cos": cos, "cache_position": cache_position}
            key_states, value_states = past_key_value.update(key_states, value_states, self.layer_idx, cache_kwargs)

        key_states = repeat_kv(key_states, self.num_key_value_groups)
        value_states = repeat_kv(value_states, self.num_key_value_groups)

        attn_weights = torch.matmul(query_states, key_states.transpose(2, 3)) / math.sqrt(self.head_dim)

        if attention_mask is not None:  # no matter the length, we just slice it
            causal_mask = attention_mask[:, :, :, : key_states.shape[-2]]
            attn_weights = attn_weights + causal_mask

        # upcast attention to fp32
        attn_weights = nn.functional.softmax(attn_weights, dim=-1, dtype=torch.float32).to(query_states.dtype)
        attn_weights = nn.functional.dropout(attn_weights, p=self.attention_dropout, training=self.training)
        attn_output = torch.matmul(attn_weights, value_states)

        if attn_output.size() != (bsz, self.num_heads, q_len, self.head_dim):
            raise ValueError(
                f"`attn_output` should be of size {(bsz, self.num_heads, q_len, self.head_dim)}, but is"
                f" {attn_output.size()}"
            )

        attn_output = attn_output.transpose(1, 2).contiguous()

        attn_output = attn_output.view(bsz, q_len, -1)
        attn_output = self.o_proj(attn_output)

        if not output_attentions:
            attn_weights = None

        return attn_output, attn_weights, past_key_value


class MistralFlashAttention2(MistralAttention):
    """
    Mistral flash attention module. This module inherits from `MistralAttention` as the weights of the module stays
    untouched. The only required change would be on the forward pass where it needs to correctly call the public API of
    flash attention and deal with padding tokens in case the input contains any of them.
    """

    # Copied from transformers.models.llama.modeling_llama.LlamaFlashAttention2.__init__
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # TODO: Should be removed once Flash Attention for RoCm is bumped to 2.1.
        # flash_attn<2.1 generates top-left aligned causal mask, while what is needed here is bottom-right alignement, that was made default for flash_attn>=2.1. This attribute is used to handle this difference. Reference: https://github.com/Dao-AILab/flash-attention/releases/tag/v2.1.0.
        # Beware that with flash_attn<2.1, using q_seqlen != k_seqlen (except for the case q_seqlen == 1) produces a wrong mask (top-left).
        self._flash_attn_uses_top_left_mask = not is_flash_attn_greater_or_equal_2_10()

    def forward(
        self,
        hidden_states: torch.Tensor,
        attention_mask: Optional[torch.Tensor] = None,
        position_ids: Optional[torch.LongTensor] = None,
        past_key_value: Optional[Cache] = None,
        output_attentions: bool = False,
        use_cache: bool = False,
        cache_position: Optional[torch.LongTensor] = None,
    ):
        if isinstance(past_key_value, StaticCache):
            raise ValueError(
                "`static` cache implementation is not compatible with `attn_implementation==flash_attention_2` "
                "make sure to use `sdpa` in the mean time, and open an issue at https://github.com/huggingface/transformers"
            )

        output_attentions = False

        bsz, q_len, _ = hidden_states.size()

        query_states = self.q_proj(hidden_states)
        key_states = self.k_proj(hidden_states)
        value_states = self.v_proj(hidden_states)

        query_states = query_states.view(bsz, q_len, self.num_heads, self.head_dim).transpose(1, 2)
        key_states = key_states.view(bsz, q_len, self.num_key_value_heads, self.head_dim).transpose(1, 2)
        value_states = value_states.view(bsz, q_len, self.num_key_value_heads, self.head_dim).transpose(1, 2)

        kv_seq_len = key_states.shape[-2]
        if past_key_value is not None:
            kv_seq_len += cache_position[0]

        cos, sin = self.rotary_emb(value_states, position_ids)
        query_states, key_states = apply_rotary_pos_emb(query_states, key_states, cos, sin)

        if past_key_value is not None:
            # Activate slicing cache only if the config has a value `sliding_windows` attribute
            cache_has_contents = past_key_value.get_seq_length(self.layer_idx) > 0
            if (
                getattr(self.config, "sliding_window", None) is not None
                and kv_seq_len > self.config.sliding_window
                and cache_has_contents
            ):
                slicing_tokens = 1 - self.config.sliding_window

                past_key = past_key_value[self.layer_idx][0]
                past_value = past_key_value[self.layer_idx][1]

                past_key = past_key[:, :, slicing_tokens:, :].contiguous()
                past_value = past_value[:, :, slicing_tokens:, :].contiguous()

                if past_key.shape[-2] != self.config.sliding_window - 1:
                    raise ValueError(
                        f"past key must have a shape of (`batch_size, num_heads, self.config.sliding_window-1, head_dim`), got"
                        f" {past_key.shape}"
                    )

                if attention_mask is not None:
                    attention_mask = attention_mask[:, slicing_tokens:]
                    attention_mask = torch.cat([attention_mask, torch.ones_like(attention_mask[:, -1:])], dim=-1)

            cache_kwargs = {"sin": sin, "cos": cos}  # Specific to RoPE models
            key_states, value_states = past_key_value.update(key_states, value_states, self.layer_idx, cache_kwargs)

        # repeat k/v heads if n_kv_heads < n_heads
        key_states = repeat_kv(key_states, self.num_key_value_groups)
        value_states = repeat_kv(value_states, self.num_key_value_groups)
        dropout_rate = 0.0 if not self.training else self.attention_dropout

        # In PEFT, usually we cast the layer norms in float32 for training stability reasons
        # therefore the input hidden states gets silently casted in float32. Hence, we need
        # cast them back in float16 just to be sure everything works as expected.
        input_dtype = query_states.dtype
        if input_dtype == torch.float32:
            if torch.is_autocast_enabled():
                target_dtype = torch.get_autocast_gpu_dtype()
            # Handle the case where the model is quantized
            elif hasattr(self.config, "_pre_quantization_dtype"):
                target_dtype = self.config._pre_quantization_dtype
            else:
                target_dtype = self.q_proj.weight.dtype

            logger.warning_once(
                f"The input hidden states seems to be silently casted in float32, this might be related to"
                f" the fact you have upcasted embedding or layer norm layers in float32. We will cast back the input in"
                f" {target_dtype}."
            )

            query_states = query_states.to(target_dtype)
            key_states = key_states.to(target_dtype)
            value_states = value_states.to(target_dtype)

        # Reashape to the expected shape for Flash Attention
        query_states = query_states.transpose(1, 2)
        key_states = key_states.transpose(1, 2)
        value_states = value_states.transpose(1, 2)

        attn_output = _flash_attention_forward(
            query_states,
            key_states,
            value_states,
            attention_mask,
            q_len,
            dropout=dropout_rate,
            sliding_window=getattr(self.config, "sliding_window", None),
            use_top_left_mask=self._flash_attn_uses_top_left_mask,
            is_causal=self.is_causal,
        )

        attn_output = attn_output.reshape(bsz, q_len, self.num_heads * self.head_dim).contiguous()
        attn_output = self.o_proj(attn_output)

        if not output_attentions:
            attn_weights = None

        return attn_output, attn_weights, past_key_value


# copied from transformers.models.llama.modeling_llama.LlamaSdpaAttention with Llama->Mistral
# TODO(joao): add me back asap :)
class MistralSdpaAttention(MistralAttention):
    """
    Mistral attention module using torch.nn.functional.scaled_dot_product_attention. This module inherits from
    `MistralAttention` as the weights of the module stays untouched. The only changes are on the forward pass to adapt to
    SDPA API.
    """

    # Adapted from MistralAttention.forward
    def forward(
        self,
        hidden_states: torch.Tensor,
        attention_mask: Optional[torch.Tensor] = None,
        position_ids: Optional[torch.LongTensor] = None,
        past_key_value: Optional[Cache] = None,
        output_attentions: bool = False,
        use_cache: bool = False,
        cache_position: Optional[torch.LongTensor] = None,
        **kwargs,
    ) -> Tuple[torch.Tensor, Optional[torch.Tensor], Optional[Tuple[torch.Tensor]]]:
        if output_attentions:
            # TODO: Improve this warning with e.g. `model.config.attn_implementation = "manual"` once this is implemented.
            logger.warning_once(
                "MistralModel is using MistralSdpaAttention, but `torch.nn.functional.scaled_dot_product_attention` does not support `output_attentions=True`. Falling back to the manual attention implementation, "
                'but specifying the manual implementation will be required from Transformers version v5.0.0 onwards. This warning can be removed using the argument `attn_implementation="eager"` when loading the model.'
            )
            return super().forward(
                hidden_states=hidden_states,
                attention_mask=attention_mask,
                position_ids=position_ids,
                past_key_value=past_key_value,
                output_attentions=output_attentions,
                use_cache=use_cache,
                cache_position=cache_position,
            )

        bsz, q_len, _ = hidden_states.size()

        query_states = self.q_proj(hidden_states)
        key_states = self.k_proj(hidden_states)
        value_states = self.v_proj(hidden_states)

        query_states = query_states.view(bsz, q_len, self.num_heads, self.head_dim).transpose(1, 2)
        key_states = key_states.view(bsz, q_len, self.num_key_value_heads, self.head_dim).transpose(1, 2)
        value_states = value_states.view(bsz, q_len, self.num_key_value_heads, self.head_dim).transpose(1, 2)

        cos, sin = self.rotary_emb(value_states, position_ids)
        query_states, key_states = apply_rotary_pos_emb(query_states, key_states, cos, sin)

        if past_key_value is not None:
            # sin and cos are specific to RoPE models; cache_position needed for the static cache
            cache_kwargs = {"sin": sin, "cos": cos, "cache_position": cache_position}
            key_states, value_states = past_key_value.update(key_states, value_states, self.layer_idx, cache_kwargs)

        key_states = repeat_kv(key_states, self.num_key_value_groups)
        value_states = repeat_kv(value_states, self.num_key_value_groups)

        causal_mask = attention_mask
        if attention_mask is not None:
            causal_mask = causal_mask[:, :, :, : key_states.shape[-2]]

        # SDPA with memory-efficient backend is currently (torch==2.1.2) bugged with non-contiguous inputs with custom attn_mask,
        # Reference: https://github.com/pytorch/pytorch/issues/112577.
        if query_states.device.type == "cuda" and causal_mask is not None:
            query_states = query_states.contiguous()
            key_states = key_states.contiguous()
            value_states = value_states.contiguous()

        # We dispatch to SDPA's Flash Attention or Efficient kernels via this `is_causal` if statement instead of an inline conditional assignment
        # in SDPA to support both torch.compile's dynamic shapes and full graph options. An inline conditional prevents dynamic shapes from compiling.
        is_causal = True if causal_mask is None and q_len > 1 else False

        attn_output = torch.nn.functional.scaled_dot_product_attention(
            query_states,
            key_states,
            value_states,
            attn_mask=causal_mask,
            dropout_p=self.attention_dropout if self.training else 0.0,
            is_causal=is_causal,
        )

        attn_output = attn_output.transpose(1, 2).contiguous()
        attn_output = attn_output.view(bsz, q_len, -1)

        attn_output = self.o_proj(attn_output)

        return attn_output, None, past_key_value


MISTRAL_ATTENTION_CLASSES = {
    "eager": MistralAttention,
    "flash_attention_2": MistralFlashAttention2,
    "sdpa": MistralSdpaAttention,
}


# copied from transformers.models.llama.modeling_llama.LlamaDecoderLayer with Llama->Mistral, LLAMA->MISTRAL
# TODO(joao): add me back asap :)
class MistralDecoderLayer(nn.Module):
    def __init__(self, config: MistralConfig, layer_idx: int):
        super().__init__()
        self.hidden_size = config.hidden_size

        self.self_attn = MISTRAL_ATTENTION_CLASSES[config._attn_implementation](config=config, layer_idx=layer_idx)

        self.mlp = MistralMLP(config)
        self.input_layernorm = MistralRMSNorm(config.hidden_size, eps=config.rms_norm_eps)
        self.post_attention_layernorm = MistralRMSNorm(config.hidden_size, eps=config.rms_norm_eps)

    def forward(
        self,
        hidden_states: torch.Tensor,
        attention_mask: Optional[torch.Tensor] = None,
        position_ids: Optional[torch.LongTensor] = None,
        past_key_value: Optional[Cache] = None,
        output_attentions: Optional[bool] = False,
        use_cache: Optional[bool] = False,
        cache_position: Optional[torch.LongTensor] = None,
        **kwargs,
    ) -> Tuple[torch.FloatTensor, Optional[Tuple[torch.FloatTensor, torch.FloatTensor]]]:
        """
        Args:
            hidden_states (`torch.FloatTensor`): input to the layer of shape `(batch, seq_len, embed_dim)`
            attention_mask (`torch.FloatTensor`, *optional*):
                attention mask of size `(batch_size, sequence_length)` if flash attention is used or `(batch_size, 1,
                query_sequence_length, key_sequence_length)` if default attention is used.
            output_attentions (`bool`, *optional*):
                Whether or not to return the attentions tensors of all attention layers. See `attentions` under
                returned tensors for more detail.
            use_cache (`bool`, *optional*):
                If set to `True`, `past_key_values` key value states are returned and can be used to speed up decoding
                (see `past_key_values`).
            past_key_value (`Tuple(torch.FloatTensor)`, *optional*): cached past key and value projection states
            cache_position (`torch.LongTensor` of shape `(sequence_length)`, *optional*):
                Indices depicting the position of the input sequence tokens in the sequence
            kwargs (`dict`, *optional*):
                Arbitrary kwargs to be ignored, used for FSDP and other methods that injects code
                into the model
        """
        residual = hidden_states

        hidden_states = self.input_layernorm(hidden_states)

        # Self Attention
        hidden_states, self_attn_weights, present_key_value = self.self_attn(
            hidden_states=hidden_states,
            attention_mask=attention_mask,
            position_ids=position_ids,
            past_key_value=past_key_value,
            output_attentions=output_attentions,
            use_cache=use_cache,
            cache_position=cache_position,
            **kwargs,
        )
        hidden_states = residual + hidden_states

        # Fully Connected
        residual = hidden_states
        hidden_states = self.post_attention_layernorm(hidden_states)
        hidden_states = self.mlp(hidden_states)
        hidden_states = residual + hidden_states

        outputs = (hidden_states,)

        if output_attentions:
            outputs += (self_attn_weights,)

        if use_cache:
            outputs += (present_key_value,)

        return outputs


MISTRAL_START_DOCSTRING = r"""
    This model inherits from [`PreTrainedModel`]. Check the superclass documentation for the generic methods the
    library implements for all its model (such as downloading or saving, resizing the input embeddings, pruning heads
    etc.)

    This model is also a PyTorch [torch.nn.Module](https://pytorch.org/docs/stable/nn.html#torch.nn.Module) subclass.
    Use it as a regular PyTorch Module and refer to the PyTorch documentation for all matter related to general usage
    and behavior.

    Parameters:
        config ([`MistralConfig`]):
            Model configuration class with all the parameters of the model. Initializing with a config file does not
            load the weights associated with the model, only the configuration. Check out the
            [`~PreTrainedModel.from_pretrained`] method to load the model weights.
"""


@add_start_docstrings(
    "The bare Mistral Model outputting raw hidden-states without any specific head on top.",
    MISTRAL_START_DOCSTRING,
)
class MistralPreTrainedModel(PreTrainedModel):
    config_class = MistralConfig
    base_model_prefix = "model"
    supports_gradient_checkpointing = True
    _no_split_modules = ["MistralDecoderLayer"]
    _skip_keys_device_placement = "past_key_values"
    _supports_flash_attn_2 = True
    _supports_sdpa = True
    _supports_cache_class = True
    _supports_static_cache = True

    def _init_weights(self, module):
        std = self.config.initializer_range
        if isinstance(module, nn.Linear):
            module.weight.data.normal_(mean=0.0, std=std)
            if module.bias is not None:
                module.bias.data.zero_()
            if module.out_features == 1:
                module.weight.data.zero_()
        elif isinstance(module, nn.Embedding):
            module.weight.data.normal_(mean=0.0, std=std)
            if module.padding_idx is not None:
                module.weight.data[module.padding_idx].zero_()


MISTRAL_INPUTS_DOCSTRING = r"""
    Args:
        input_ids (`torch.LongTensor` of shape `(batch_size, sequence_length)`):
            Indices of input sequence tokens in the vocabulary. Padding will be ignored by default should you provide
            it.

            Indices can be obtained using [`AutoTokenizer`]. See [`PreTrainedTokenizer.encode`] and
            [`PreTrainedTokenizer.__call__`] for details.

            [What are input IDs?](../glossary#input-ids)
        attention_mask (`torch.Tensor` of shape `(batch_size, sequence_length)`, *optional*):
            Mask to avoid performing attention on padding token indices. Mask values selected in `[0, 1]`:

            - 1 for tokens that are **not masked**,
            - 0 for tokens that are **masked**.

            [What are attention masks?](../glossary#attention-mask)

            Indices can be obtained using [`AutoTokenizer`]. See [`PreTrainedTokenizer.encode`] and
            [`PreTrainedTokenizer.__call__`] for details.

            If `past_key_values` is used, optionally only the last `decoder_input_ids` have to be input (see
            `past_key_values`).

            If you want to change padding behavior, you should read [`modeling_opt._prepare_decoder_attention_mask`]
            and modify to your needs. See diagram 1 in [the paper](https://arxiv.org/abs/1910.13461) for more
            information on the default strategy.

            - 1 indicates the head is **not masked**,
            - 0 indicates the head is **masked**.
        position_ids (`torch.LongTensor` of shape `(batch_size, sequence_length)`, *optional*):
            Indices of positions of each input sequence tokens in the position embeddings. Selected in the range `[0,
            config.n_positions - 1]`.

            [What are position IDs?](../glossary#position-ids)
        past_key_values (`Cache` or `tuple(tuple(torch.FloatTensor))`, *optional*):
            Pre-computed hidden-states (key and values in the self-attention blocks and in the cross-attention
            blocks) that can be used to speed up sequential decoding. This typically consists in the `past_key_values`
            returned by the model at a previous stage of decoding, when `use_cache=True` or `config.use_cache=True`.

            Two formats are allowed:
            - a [`~cache_utils.Cache`] instance;
            - Tuple of `tuple(torch.FloatTensor)` of length `config.n_layers`, with each tuple having 2 tensors of
            shape `(batch_size, num_heads, sequence_length, embed_size_per_head)`). This is also known as the legacy
            cache format.

            The model will output the same cache format that is fed as input. If no `past_key_values` are passed, the
            legacy cache format will be returned.

            If `past_key_values` are used, the user can optionally input only the last `input_ids` (those that don't
            have their past key value states given to this model) of shape `(batch_size, 1)` instead of all `input_ids`
            of shape `(batch_size, sequence_length)`.
        inputs_embeds (`torch.FloatTensor` of shape `(batch_size, sequence_length, hidden_size)`, *optional*):
            Optionally, instead of passing `input_ids` you can choose to directly pass an embedded representation. This
            is useful if you want more control over how to convert `input_ids` indices into associated vectors than the
            model's internal embedding lookup matrix.
        use_cache (`bool`, *optional*):
            If set to `True`, `past_key_values` key value states are returned and can be used to speed up decoding (see
            `past_key_values`).
        output_attentions (`bool`, *optional*):
            Whether or not to return the attentions tensors of all attention layers. See `attentions` under returned
            tensors for more detail.
        output_hidden_states (`bool`, *optional*):
            Whether or not to return the hidden states of all layers. See `hidden_states` under returned tensors for
            more detail.
        return_dict (`bool`, *optional*):
            Whether or not to return a [`~utils.ModelOutput`] instead of a plain tuple.
"""


@add_start_docstrings(
    "The bare Mistral Model outputting raw hidden-states without any specific head on top.",
    MISTRAL_START_DOCSTRING,
)
class MistralModel(MistralPreTrainedModel):
    """
    Transformer decoder consisting of *config.num_hidden_layers* layers. Each layer is a [`MistralDecoderLayer`]

    Args:
        config: MistralConfig
    """

    def __init__(self, config: MistralConfig):
        super().__init__(config)
        self.padding_idx = config.pad_token_id
        self.vocab_size = config.vocab_size

        self.embed_tokens = nn.Embedding(config.vocab_size, config.hidden_size, self.padding_idx)
        self.layers = nn.ModuleList(
            [MistralDecoderLayer(config, layer_idx) for layer_idx in range(config.num_hidden_layers)]
        )
        self._attn_implementation = config._attn_implementation
        self.norm = MistralRMSNorm(config.hidden_size, eps=config.rms_norm_eps)

        self.gradient_checkpointing = False
        # Initialize weights and apply final processing
        self.post_init()

    def get_input_embeddings(self):
        return self.embed_tokens

    def set_input_embeddings(self, value):
        self.embed_tokens = value

    @add_start_docstrings_to_model_forward(MISTRAL_INPUTS_DOCSTRING)
    def forward(
        self,
        input_ids: torch.LongTensor = None,
        attention_mask: Optional[torch.Tensor] = None,
        position_ids: Optional[torch.LongTensor] = None,
        past_key_values: Optional[Union[Cache, List[torch.FloatTensor]]] = None,
        inputs_embeds: Optional[torch.FloatTensor] = None,
        use_cache: Optional[bool] = None,
        output_attentions: Optional[bool] = None,
        output_hidden_states: Optional[bool] = None,
        return_dict: Optional[bool] = None,
        cache_position: Optional[torch.LongTensor] = None,
    ) -> Union[Tuple, BaseModelOutputWithPast]:
        output_attentions = output_attentions if output_attentions is not None else self.config.output_attentions
        output_hidden_states = (
            output_hidden_states if output_hidden_states is not None else self.config.output_hidden_states
        )
        use_cache = use_cache if use_cache is not None else self.config.use_cache

        return_dict = return_dict if return_dict is not None else self.config.use_return_dict

        # retrieve input_ids and inputs_embeds
        if (input_ids is None) ^ (inputs_embeds is not None):
            raise ValueError(
                "You cannot specify both input_ids and inputs_embeds at the same time, and must specify either one"
            )

        if self.gradient_checkpointing and self.training and use_cache:
            logger.warning_once(
                "`use_cache=True` is incompatible with gradient checkpointing. Setting `use_cache=False`..."
            )
            use_cache = False

        if inputs_embeds is None:
            inputs_embeds = self.embed_tokens(input_ids)

        return_legacy_cache = False
        if use_cache and not isinstance(past_key_values, Cache) and not self.training:
            past_key_values = DynamicCache.from_legacy_cache(past_key_values)
            return_legacy_cache = True
            logger.warning_once(
                "We detected that you are passing `past_key_values` as a tuple and this is deprecated and will be removed in v4.43. "
                "Please use an appropriate `Cache` class (https://huggingface.co/docs/transformers/v4.41.3/en/internal/generation_utils#transformers.Cache)"
            )

        if cache_position is None:
            past_seen_tokens = past_key_values.get_seq_length() if past_key_values is not None else 0
            cache_position = torch.arange(
                past_seen_tokens, past_seen_tokens + inputs_embeds.shape[1], device=inputs_embeds.device
            )

        if position_ids is None:
            position_ids = cache_position.unsqueeze(0)

        causal_mask = self._update_causal_mask(
            attention_mask, inputs_embeds, cache_position, past_key_values, use_cache, output_attentions
        )

        hidden_states = inputs_embeds

        # decoder layers
        all_hidden_states = () if output_hidden_states else None
        all_self_attns = () if output_attentions else None
        next_decoder_cache = None

        for decoder_layer in self.layers:
            if output_hidden_states:
                all_hidden_states += (hidden_states,)

            if self.gradient_checkpointing and self.training:
                layer_outputs = self._gradient_checkpointing_func(
                    decoder_layer.__call__,
                    hidden_states,
                    causal_mask,
                    position_ids,
                    past_key_values,
                    output_attentions,
                    use_cache,
                    cache_position,
                )
            else:
                layer_outputs = decoder_layer(
                    hidden_states,
                    attention_mask=causal_mask,
                    position_ids=position_ids,
                    past_key_value=past_key_values,
                    output_attentions=output_attentions,
                    use_cache=use_cache,
                    cache_position=cache_position,
                )

            hidden_states = layer_outputs[0]

            if use_cache:
                next_decoder_cache = layer_outputs[2 if output_attentions else 1]

            if output_attentions:
                all_self_attns += (layer_outputs[1],)

        hidden_states = self.norm(hidden_states)

        # add hidden states from the last decoder layer
        if output_hidden_states:
            all_hidden_states += (hidden_states,)

        next_cache = next_decoder_cache if use_cache else None
        if return_legacy_cache:
            next_cache = next_cache.to_legacy_cache()

        if not return_dict:
            return tuple(v for v in [hidden_states, next_cache, all_hidden_states, all_self_attns] if v is not None)
        return BaseModelOutputWithPast(
            last_hidden_state=hidden_states,
            past_key_values=next_cache,
            hidden_states=all_hidden_states,
            attentions=all_self_attns,
        )

    def _update_causal_mask(
        self,
        attention_mask: torch.Tensor,
        input_tensor: torch.Tensor,
        cache_position: torch.Tensor,
        past_key_values: Cache,
        use_cache: bool,
        output_attentions: bool,
    ):
        # TODO: As of torch==2.2.0, the `attention_mask` passed to the model in `generate` is 2D and of dynamic length even when the static
        # KV cache is used. This is an issue for torch.compile which then recaptures cudagraphs at each decode steps due to the dynamic shapes.
        # (`recording cudagraph tree for symint key 13`, etc.), which is VERY slow. A workaround is `@torch.compiler.disable`, but this prevents using
        # `fullgraph=True`. See more context in https://github.com/huggingface/transformers/pull/29114

        if self._attn_implementation == "flash_attention_2":
            if attention_mask is not None and use_cache:
                is_padding_right = attention_mask[:, -1].sum().item() != input_tensor.size()[0]
                if is_padding_right:
                    raise ValueError(
                        "You are attempting to perform batched generation with padding_side='right'"
                        " this may lead to unexpected behaviour for Flash Attention version of Mistral. Make sure to "
                        " call `tokenizer.padding_side  = 'left'` before tokenizing the input. "
                    )
            if attention_mask is not None and 0.0 in attention_mask:
                return attention_mask
            return None

        # For SDPA, when possible, we will rely on its `is_causal` argument instead of its `attn_mask` argument, in
        # order to dispatch on Flash Attention 2. This feature is not compatible with static cache, as SDPA will fail
        # to infer the attention mask.

        # cache_position must be valid here no matter which cache we use
        past_seen_tokens = cache_position[0] if past_key_values is not None else 0
        using_static_cache = isinstance(past_key_values, StaticCache)
        using_sliding_window_cache = isinstance(past_key_values, SlidingWindowCache)

        if (
            self.config._attn_implementation == "sdpa"
            and not (using_static_cache or using_sliding_window_cache)
            and not output_attentions
        ):
            if AttentionMaskConverter._ignore_causal_mask_sdpa(
                attention_mask,
                inputs_embeds=input_tensor,
                past_key_values_length=past_seen_tokens,
                sliding_window=self.config.sliding_window,
                is_training=self.training,
            ):
                return None

        dtype, device = input_tensor.dtype, input_tensor.device
        min_dtype = torch.finfo(dtype).min
        sequence_length = input_tensor.shape[1]
        # SlidingWindowCache
        if using_sliding_window_cache:
            target_length = max(sequence_length, self.config.sliding_window)
        # StaticCache
        elif using_static_cache:
            target_length = past_key_values.get_max_length()
        # DynamicCache or no cache
        else:
            target_length = (
                attention_mask.shape[-1]
                if isinstance(attention_mask, torch.Tensor)
                else past_seen_tokens + sequence_length + 1
            )

        if attention_mask is not None and attention_mask.dim() == 4:
            # in this case we assume that the mask comes already in inverted form and requires no inversion or slicing
            if attention_mask.max() != 0:
                raise ValueError("Custom 4D attention mask should be passed in inverted form with max==0`")
            causal_mask = attention_mask
        else:
            causal_mask = torch.full(
                (sequence_length, target_length), fill_value=min_dtype, dtype=dtype, device=device
            )
            exclude_mask = torch.arange(target_length, device=device) > cache_position.reshape(-1, 1)
            if self.config.sliding_window is not None:
                if not using_sliding_window_cache or sequence_length > self.config.sliding_window:
                    exclude_mask.bitwise_or_(
                        torch.arange(target_length, device=device)
                        <= (cache_position.reshape(-1, 1) - self.config.sliding_window)
                    )
            causal_mask *= exclude_mask
            causal_mask = causal_mask[None, None, :, :].expand(input_tensor.shape[0], 1, -1, -1)
            if attention_mask is not None:
                causal_mask = causal_mask.clone()  # copy to contiguous memory for in-place edit
                if attention_mask.dim() == 2:
                    mask_length = attention_mask.shape[-1]
                    padding_mask = causal_mask[:, :, :, :mask_length] + attention_mask[:, None, None, :]
                    padding_mask = padding_mask == 0
                    causal_mask[:, :, :, :mask_length] = causal_mask[:, :, :, :mask_length].masked_fill(
                        padding_mask, min_dtype
                    )

        if (
            self.config._attn_implementation == "sdpa"
            and attention_mask is not None
            and attention_mask.device.type == "cuda"
            and not output_attentions
        ):
            # Attend to all tokens in fully masked rows in the causal_mask, for example the relevant first rows when
            # using left padding. This is required by F.scaled_dot_product_attention memory-efficient attention path.
            # Details: https://github.com/pytorch/pytorch/issues/110213
            causal_mask = AttentionMaskConverter._unmask_unattended(causal_mask, min_dtype)

        return causal_mask

def nonzero_mean(x, axis=None):
    if axis is not None:
        return x.sum(axis) / (x != 0).sum(axis)
    return x.sum() / (x != 0).sum()

def loss_mean(x):
    return x.sum() / (x != 0).sum()

COT_PROMPT = """Instruction:
%s
Task:
Please analyze the provided Instruction. 
Write your thought process briefly after "Here is my thought process:". In the thought process, divide your response into two sections: "Requirement Evaluation" and "Steps to Answer".
Here is my thought process:
"""

class MistralForCausalLM(MistralPreTrainedModel):
    _tied_weights_keys = ["lm_head.weight"]

    def __init__(self, config):
        super().__init__(config)
        self.model = MistralModel(config)
        self.vocab_size = config.vocab_size
        self.lm_head = nn.Linear(config.hidden_size, config.vocab_size, bias=False)
        self.max_thoughts = config.max_thoughts
        self.merged_lm_and_talk_heads = config.merged_lm_and_talk_heads
        self.use_concat_talk_head = config.use_concat_talk_head
        self.use_shallow_talk = config.use_shallow_talk
        self.use_complex_talk_head = config.use_complex_talk_head
        self.use_weighted_talk_head = config.use_weighted_talk_head
        self.log_thoughts = config.log_thoughts
        self.log_kl_logits = config.log_kl_logits
        self.warmup = config.warmup
        # the weighted head will output a single value, so it can't be passed to the lm head
        assert not (self.use_weighted_talk_head and self.use_shallow_talk)

        self.n_ahead = 1
        self.n_ahead_talk = 1
        self.n_passes = 1
        self.n_tokens_print = 1
        self.gradient_accumulation_steps = 1
        self.training_steps = 0
        self.tokenizer = None
        self.start_token_id = None
        self.end_token_id = None
        self.rm_initialized = False
        self.residual_talk_head = True
        self.thought_init_std_scale = 1e-2

        self.final_only_mode = False
        self.first_and_last_mode = True
        self.first_only = False
        self.original_loss_weight = 0

        self.cumulative_residual = False
        self.clever_residual = False
        self.skip_residual = False
        self.no_residual = True

        self.optimize_lm_head_only_at_start = False
        self.optimize_model_only_at_start = False

        if self.optimize_model_only_at_start:
            raise NotImplementedError
        self.train_only_thinking_embedding = False
        self.weighted_embeddings = False
        self.use_start_thought_token = False
        self.use_end_thought_token = False
        self.initialize_thought_embedding_to_normal = False
        self.initial_start_token = "---"
        self.initial_end_token = "---"
        self.output_logits_at_the_end = True

        self.wandb_enabled = False
        self.gumbel_temperature = 0.9

        self.use_policy_loss = True
        self.include_policy_loss = True
        self.trice_mode = True
        self.remove_negative_rewards = True
        self.use_policy_loss_for_end_thought = True
        
        self.base_original_mode = False
        self.original_mode = False

        self.thought_prefix = "Think the instruction briefly. "
        
        self.thought_prompt = COT_PROMPT
        self.INSTRUCTION_MARK = "### Instruction:"
        self.RESPONSE_MARK = "### Response:"
        
        self.tokenized_thought_prefix = None
        self.log_dict = defaultdict(int)
        self.eval_log_dict = defaultdict(int)
        self.print_final_only = True
        self.loss_mean = loss_mean
        self.all_rewards = []
        self.all_unreduced_losses = []

        # self.start_embedding = nn.Parameter(torch.zeros(self.model.config.hidden_size))
        # self.end_embedding = nn.Parameter(torch.zeros(self.model.config.hidden_size))

        self.policy_loss_beta = 10
        self.embedding_scale = 1e2
        self.reinforce_temperature = 3
        self.base_loss_beta = 1

        # Not used in the paper:
        self.use_thought_prefix = False
        self.use_reparam_for_thought_embeddings = False
        self.use_upper_triangular = False
        self.comparison_mode = False
        self.gumbel_detach = True

        self.fixed_weight = False
        self.mixing_weight = None
        # For visualization
        self.eval_mode = False

        num_talk = 1
        talk_input_dim = config.hidden_size if not self.use_concat_talk_head else config.hidden_size * 2
        if self.use_weighted_talk_head:
            talk_output_dim = 1
        else:
            talk_output_dim = config.hidden_size if self.use_shallow_talk else config.vocab_size

        if not self.merged_lm_and_talk_heads:
            if self.use_complex_talk_head:
                self.talk_head = nn.ModuleList([nn.Sequential(
                    nn.Linear(talk_input_dim, config.hidden_size),
                    nn.ReLU(),
                    nn.Linear(config.hidden_size, config.hidden_size),
                    nn.ReLU(),
                    nn.Linear(config.hidden_size, talk_output_dim, bias=False)
                )])
            else:
                self.talk_head = nn.ModuleList([nn.Sequential(
                    nn.Linear(talk_input_dim, talk_output_dim, bias=False)
                )])

        # Initialize weights and apply final processing
        self.post_init()

    def get_input_embeddings(self):
        return self.model.embed_tokens

    def set_input_embeddings(self, value):
        self.model.embed_tokens = value

    def get_output_embeddings(self):
        return self.lm_head

    def set_output_embeddings(self, new_embeddings):
        self.lm_head = new_embeddings

    def set_decoder(self, decoder):
        self.model = decoder

    def get_decoder(self):
        return self.model

    @add_start_docstrings_to_model_forward(MISTRAL_INPUTS_DOCSTRING)
    @replace_return_docstrings(output_type=CausalLMOutputWithPast, config_class=_CONFIG_FOR_DOC)
    def forward(
        self,
        input_ids: torch.LongTensor = None,
        attention_mask: Optional[torch.Tensor] = None,
        position_ids: Optional[torch.LongTensor] = None,
        past_key_values: Optional[Union[Cache, List[torch.FloatTensor]]] = None,
        inputs_embeds: Optional[torch.FloatTensor] = None,
        labels: Optional[torch.LongTensor] = None,
        use_cache: Optional[bool] = None,
        output_attentions: Optional[bool] = None,
        output_hidden_states: Optional[bool] = None,
        return_dict: Optional[bool] = None,
        cache_position: Optional[torch.LongTensor] = None,
    ) -> Union[Tuple, CausalLMOutputWithPast]:
        r"""
        Args:
            labels (`torch.LongTensor` of shape `(batch_size, sequence_length)`, *optional*):
                Labels for computing the masked language modeling loss. Indices should either be in `[0, ...,
                config.vocab_size]` or -100 (see `input_ids` docstring). Tokens with indices set to `-100` are ignored
                (masked), the loss is only computed for the tokens with labels in `[0, ..., config.vocab_size]`.

        Returns:

        Example:

        ```python
        >>> from transformers import AutoTokenizer, MistralForCausalLM

        >>> model = MistralForCausalLM.from_pretrained("mistralai/Mistral-7B-v0.1")
        >>> tokenizer = AutoTokenizer.from_pretrained("mistralai/Mistral-7B-v0.1")

        >>> prompt = "Hey, are you conscious? Can you talk to me?"
        >>> inputs = tokenizer(prompt, return_tensors="pt")

        >>> # Generate
        >>> generate_ids = model.generate(inputs.input_ids, max_length=30)
        >>> tokenizer.batch_decode(generate_ids, skip_special_tokens=True, clean_up_tokenization_spaces=False)[0]
        "Hey, are you conscious? Can you talk to me?\nI'm not conscious, but I can talk to you."
        ```"""
        log_dict = self.log_dict if self.training else self.eval_log_dict

        output_attentions = output_attentions if output_attentions is not None else self.config.output_attentions
        output_hidden_states = (
            output_hidden_states if output_hidden_states is not None else self.config.output_hidden_states
        )
        return_dict = return_dict if return_dict is not None else self.config.use_return_dict

        assert self.cumulative_residual or self.clever_residual or self.skip_residual or self.no_residual
        assert not (self.skip_residual and self.use_policy_loss)

        if self.tokenized_thought_prefix is None and self.use_thought_prefix:
            self.tokenized_thought_prefix = self.tokenizer(self.thought_prefix, return_tensors="pt", add_special_tokens=False)["input_ids"]

        def apply_head(head, states, detach=False):
            if detach:
                head_weight = head.weight.detach()
            else:
                head_weight = head.weight
            head_weight = head_weight.to(states.device)
            return (head_weight @ states.transpose(-1, -2)).transpose(-1, -2).contiguous()

        self.tokenizer_has_start_thought_token = True
        self.tokenizer_has_end_thought_token = True

        if not self.rm_initialized and (self.n_ahead > 1 or not self.base_original_mode):
            self.rm_initialized = True                        
            if not self.use_shallow_talk:
                head = self.talk_head[0]
                cur_head = head[-1] if isinstance(head, nn.Sequential) else head
                talk_input_dim = cur_head.weight.data.shape[1]
                talk_output_dim = 1 if self.use_weighted_talk_head else self.lm_head.weight.data.shape[0]
                cur_head.weight.data = torch.zeros(talk_output_dim, talk_input_dim, device=cur_head.weight.device, dtype=cur_head.weight.dtype)
            else:
                # convert to identity transform
                def lambda_transform(cur_head):
                    if cur_head.weight.data.shape[0] != cur_head.weight.data.shape[1]:
                        return torch.cat([
                        torch.eye(
                            cur_head.weight.data.shape[0],
                            device=cur_head.weight.device,
                            dtype=cur_head.weight.dtype
                        ),
                        torch.zeros(
                            cur_head.weight.data.shape[0],
                            cur_head.weight.data.shape[1] - cur_head.weight.data.shape[0],
                            device=cur_head.weight.device,
                            dtype=cur_head.weight.dtype
                        )], dim=1)
                    return torch.eye(
                        cur_head.weight.data.shape[0],
                        device=cur_head.weight.device,
                        dtype=cur_head.weight.dtype
                    )
                if isinstance(self.talk_head[0], nn.Sequential):
                    for cur_head in self.talk_head[0]:
                        # if it has weights
                        if hasattr(cur_head, "weight"):
                            cur_head.weight.data = lambda_transform(cur_head)
                else:
                    self.talk_head[-1].weight.data = lambda_transform(self.talk_head[0])

        loss = None
        hidden_states = None
        logits = None
        rm_logits = None
        residual_logits = None
        batch_size, seq_len = input_ids.shape
        dqn_loss_list = []
        dqn_loss = None
        sampled_token_history = []
        action_loglikelihoods_list = []
        talk_loss_list = []
        sft_loss_list = []
        sft_loss = None
        train_policy_reward = None
        weights_list = []
        kl_list = []
        # print(self.start_token_id)
        contains_start = self.use_start_thought_token and (input_ids == self.start_token_id).any()
        contains_end = self.use_end_thought_token and (input_ids == self.end_token_id).any()
        # calculate the loss for the cot
        if contains_end and contains_start:
            # print(input_ids.shape)
            # print(self.tokenizer.batch_decode(input_ids))
            start_token_positions = [np.where(input_id == self.start_token_id)[0][0] for input_id in input_ids.cpu().numpy()]
            end_token_positions = [np.where(input_id == self.end_token_id)[0][0] for input_id in input_ids.cpu().numpy()]
            thought_lens = [end_token_positions[i] - start_token_positions[i] + 1 for i in range(len(start_token_positions))]
            # For the cot prompt training
            if self.training:
                # extract the instructions
                input_strs = self.tokenizer.batch_decode(input_ids)
                st_idx = [input_str.find(self.INSTRUCTION_MARK) + len(self.INSTRUCTION_MARK) for input_str in input_strs]
                ed_idx = [input_str.find(self.RESPONSE_MARK) for input_str in input_strs]
                instructions = [input_strs[i][st_idx[i]:ed_idx[i]].strip() for i in range(len(input_strs))]
                cot_prompts = [self.thought_prompt % (instructions[i]) for i in range(len(instructions))]
                cot_ids = self.tokenizer(cot_prompts, return_tensors="pt", add_special_tokens=False, padding=True)["input_ids"].to(input_ids.device)
                cot_labels = torch.full_like(cot_ids, -100, dtype=torch.long, device=input_ids.device)
                # max(thought_lens) - 1 = max(thought_lens) + 1 - 2(start & end)
                cot_ids = torch.cat([cot_ids, torch.full((cot_ids.shape[0], max(thought_lens) - 1), self.tokenizer.pad_token_id, dtype=torch.long, device=input_ids.device)], dim = -1)
                cot_start_idxs = []
                # TODO: cot_ids can be smaller
                for i in range(len(thought_lens)):
                    idx = np.where(cot_ids[i].cpu().numpy() == self.tokenizer.pad_token_id)[0][0]
                    cot_start_idxs.append(idx)
                    cot_ids[i, idx:idx+thought_lens[i]-2] = input_ids[i][start_token_positions[i]+1:end_token_positions[i]]
                cot_labels = torch.cat([cot_labels, cot_ids[:, cot_labels.shape[1]:]], dim = -1)
                cot_attention_mask = torch.ones_like(cot_ids, dtype=torch.long, device=input_ids.device)
            # 1. get the outputs from the inputs with thought
            if True:
                # get original_ids first
                original_ids = torch.full((int(input_ids.shape[0] / self.n_passes), input_ids.shape[1] - min(thought_lens)), self.tokenizer.pad_token_id, dtype=torch.long, device=input_ids.device)
                original_attention_mask = torch.zeros_like(original_ids, dtype=torch.long)
                
                for idx, i in enumerate(range(0, len(start_token_positions), self.n_passes)):
                    original_len = input_ids.shape[1] - thought_lens[i]
                    original_ids[idx, :original_len] = torch.cat([input_ids[i][:start_token_positions[i]], input_ids[i][end_token_positions[i] + 1:]], dim=-1)
                    original_attention_mask[idx, :original_len] = torch.cat([attention_mask[i][:start_token_positions[i]], attention_mask[i][end_token_positions[i] + 1:]], dim=-1)
                # clean the extra padding tokens
                end_idx = 0
                for original_id in original_ids.cpu().numpy():
                    for idx in range(len(original_id) - 1, -1, -1):
                        if original_id[idx] != self.tokenizer.pad_token_id:
                            break
                    end_idx = max(end_idx, idx + 1)

                original_ids = original_ids[:, :end_idx]
                original_attention_mask = original_attention_mask[:, :end_idx]
                original_labels = original_ids.clone() if labels is not None else None
                if labels is not None:
                    for i in range(len(original_labels)):
                        original_labels[i, : start_token_positions[i]] = -100
                
                # combine the input_ids, original_ids, cot_ids
                max_len = max(input_ids.shape[1], original_ids.shape[1], cot_ids.shape[1]) if self.training else max(input_ids.shape[1], original_ids.shape[1]) 
                final_input_ids =  torch.full((batch_size * (2 if self.training else 1) + batch_size // self.n_passes , max_len), self.tokenizer.pad_token_id, dtype=torch.long, device=input_ids.device)
                final_attention_mask = torch.ones_like(final_input_ids, dtype=torch.long, device=input_ids.device)
                final_labels = final_input_ids.clone() if labels is not None else None
                
                def copy_ids_att_lab(final, original, idx):
                    final_input_ids, final_attention_mask, final_labels = final
                    input_ids, attention_mask, labels = original
                    final_input_ids[idx: idx+input_ids.shape[0], :input_ids.shape[1]] = input_ids
                    final_attention_mask[idx: idx+input_ids.shape[0], :input_ids.shape[1]] = attention_mask
                    if labels is not None:
                        final_labels[idx: idx+input_ids.shape[0], :input_ids.shape[1]] = labels

                copy_ids_att_lab((final_input_ids, final_attention_mask, final_labels), (input_ids, attention_mask, labels), 0)
                copy_ids_att_lab((final_input_ids, final_attention_mask, final_labels), (original_ids, original_attention_mask, original_labels), batch_size)
                if self.training:
                    copy_ids_att_lab((final_input_ids, final_attention_mask, final_labels), (cot_ids, cot_attention_mask, cot_labels), batch_size + batch_size // self.n_passes)

                outputs = self.model(
                    input_ids=final_input_ids,
                    attention_mask=final_attention_mask,
                    position_ids=None,
                    past_key_values=None,
                    inputs_embeds=None,
                    use_cache=False, # can't use cache
                    output_attentions=output_attentions,
                    output_hidden_states=output_hidden_states,
                    return_dict=return_dict,
                )

                hidden_states = outputs[0][:batch_size, :input_ids.shape[1]]
                original_hidden_states = outputs[0][batch_size:batch_size + batch_size // self.n_passes, :original_ids.shape[1]]
                if self.training:
                    cot_hidden_states = outputs[0][batch_size + batch_size // self.n_passes:, :cot_ids.shape[1]]

                logits = self.lm_head(hidden_states)
                rm_logits = logits.clone()
                # 2. get the inputs without thought
                
                
                # 3. get the outputs from the inputs without thought
                # print("original_ids", original_ids.shape)
                
                original_logits = self.lm_head(original_hidden_states)
                original_logits = original_logits.float()
                # 4. get the sft loss
                if labels is not None:
                    shift_logits = original_logits[..., :-1, :].contiguous()
                    shift_labels = original_labels[..., 1:].contiguous()
                    # Flatten the tokens
                    loss_fct = CrossEntropyLoss()
                    for i in range(original_ids.shape[0]):
                        # Flatten logits and labels
                        flat_logits = shift_logits[i].view(-1, self.config.vocab_size)
                        flat_labels = shift_labels[i].view(-1)
                        
                        # Move labels to the same device as logits
                        flat_labels = flat_labels.to(flat_logits.device)
                        
                        # Replace pad token with -100 to ignore in loss calculation
                        flat_labels = torch.where(flat_labels == self.tokenizer.pad_token_id, -100, flat_labels)
                        # Calculate loss for the current sample
                        sft_loss_list.append(loss_fct(flat_logits, flat_labels))

                # 5. get the talk loss
                for i in range(len(start_token_positions)):
                    start_idx_4_no_thought = start_token_positions[i] - 1
                    start_idx_4_thought = end_token_positions[i]

                    base_hidden = original_hidden_states[i // self.n_passes, start_idx_4_no_thought:, :]
                    talk_hidden = hidden_states[i, start_idx_4_thought:, :]

                    if base_hidden.shape[0] != talk_hidden.shape[0]:
                        min_dim = min(base_hidden.shape[0], talk_hidden.shape[0])
                        base_hidden = base_hidden[:min_dim, :]
                        talk_hidden = talk_hidden[:min_dim, :]
                    
                    if self.log_kl_logits:   
                        base_output = self.lm_head(base_hidden.detach()).detach()
                        base_output = F.softmax(base_output, dim=-1)
                        talk_output = self.lm_head(talk_hidden.detach()).detach()
                        talk_output = F.softmax(talk_output, dim=-1)
                        kl = F.kl_div(talk_output.log(), base_output, reduction='none')
                        kl_div_per_sample = kl.sum(dim=-1)
                        kl_list.append(kl_div_per_sample.mean().item())  

                    if self.use_concat_talk_head:
                        head_input_hidden_states = torch.cat([base_hidden, talk_hidden], dim=-1)
                    else:
                        head_input_hidden_states = talk_hidden
                    
                    residual_logits = self.talk_head[0](head_input_hidden_states)
                    if self.use_shallow_talk:
                        residual_logits = apply_head(self.lm_head, residual_logits, detach=self.optimize_lm_head_only_at_start)                        
                    residual_logits = residual_logits.to(logits.device)
                    if self.use_weighted_talk_head:
                        # combine the cur_base_hidden with the talk_hidden_states according to the weighted head
                        weights_list.append(torch.mean(residual_logits.detach()).item())
                        if not self.fixed_weight:
                            residual_logits = base_hidden * (residual_logits) + talk_hidden * (1 - residual_logits)
                        else:
                            residual_logits = base_hidden * (1 - self.mixing_weight) + talk_hidden * self.mixing_weight
                        residual_logits = apply_head(self.lm_head, residual_logits, detach=self.optimize_lm_head_only_at_start)
                    
                    # just for output
                    rm_logits[i, start_idx_4_thought:start_idx_4_thought+residual_logits.shape[0], :] = residual_logits.detach()
                
                    if labels is not None:
                        shift_logits = residual_logits[:-1, :].contiguous()
                        shift_labels = labels[i, start_idx_4_thought + 1:start_idx_4_thought + 1 + shift_logits.shape[0]].contiguous()
                        # Flatten the tokens
                        if shift_logits.shape[0] != shift_labels.shape[0]:
                            raise ValueError
                        loss_fct = CrossEntropyLoss()
                        shift_logits = shift_logits.view(-1, self.config.vocab_size)
                        shift_labels = shift_labels.view(-1)
                        # Enable model parallelism
                        shift_labels = shift_labels.to(shift_logits.device)
                        # if shift_labels.min() == self.tokenizer.pad_token_id:
                        shift_labels = torch.where(shift_labels == self.tokenizer.pad_token_id, -100, shift_labels)
                        unreduced_loss = loss_fct(shift_logits, shift_labels)
                        if torch.any(unreduced_loss != unreduced_loss):
                            print(unreduced_loss)
                            print(shift_logits)
                            print(shift_labels)
                            print(start_idx_4_no_thought, start_idx_4_thought)
                            print(residual_logits)
                            print(self.tokenizer.decode(input_ids[i]))
                            raise ValueError("NaN loss")

                        talk_loss_list.append(unreduced_loss)
            if labels is not None:
                # 6. get the reinforce loss
                # first, rewawrd
                if not self.warmup:
                    train_policy_reward = torch.stack(sft_loss_list).repeat_interleave(self.n_passes) - torch.stack(talk_loss_list)
                    # print(sft_loss_list, talk_loss_list)
                    print("reward:", train_policy_reward)
                    original_train_policy_reward = train_policy_reward.detach()
                    train_policy_reward = train_policy_reward.clamp(min=0)
                    
                    # discard rewards below the mean
                    if self.trice_mode and self.n_passes > 1:
                        batched_policy_reward = train_policy_reward.reshape(-1, self.n_passes)
                        # average over the passes
                        train_policy_reward = batched_policy_reward - batched_policy_reward.mean(dim=1, keepdim=True)
                        train_policy_reward = train_policy_reward.reshape(len(talk_loss_list))

                    if self.remove_negative_rewards:
                        fixed_policy_reward = train_policy_reward.detach().clamp(min=0)
                    else:
                        fixed_policy_reward = train_policy_reward.detach()
                    
                    with open("reward.log", "a") as f:
                        for i in range(len(train_policy_reward)):
                            f.write(self.tokenizer.decode(input_ids[i]) + "\n")
                            f.write(f"train_policy_reward: {train_policy_reward[i]} fixed_policy_reward: {fixed_policy_reward[i]}\n")

                # second, action probability
                # print("cot_ids", cot_ids.shape)
                # if self.warmup:
                #     cot_outputs = self.model(
                #         input_ids=cot_ids,
                #         attention_mask=cot_attention_mask,
                #         position_ids=None,
                #         past_key_values=None,
                #         inputs_embeds=None,
                #         use_cache=False,
                #         output_attentions=False,
                #         output_hidden_states=False,
                #         return_dict=True,
                #     )
                #     outputs = cot_outputs
                #     cot_hidden_states = cot_outputs[0]
                cot_logits = self.lm_head(cot_hidden_states)
                cot_logits = cot_logits.float()
                for i in range(batch_size):
                    cur_logits = cot_logits[i, cot_start_idxs[i]-1:-1, :]
                    # don't allow it to predict the start thinking token
                    if self.tokenizer_has_start_thought_token:
                        cur_logits[..., self.start_token_id] = -1e10
                    if self.tokenizer_has_end_thought_token:
                        cur_logits[..., self.end_token_id] = -1e10
                    indices = cot_ids[i, cot_start_idxs[i]:]
                    action_loglikelihood = F.log_softmax(cur_logits / self.reinforce_temperature, dim=-1)[torch.arange(cur_logits.size(0)), indices]
                    action_loglikelihoods_list.append(action_loglikelihood)
                    if self.warmup or fixed_policy_reward[i] > 0:
                        dqn_loss_list.append(-action_loglikelihood.mean() * (fixed_policy_reward[i] if not self.warmup else 1))
        else:
            outputs = self.model(
                input_ids=input_ids,
                attention_mask=attention_mask,
                position_ids=position_ids,
                past_key_values=past_key_values,
                inputs_embeds=inputs_embeds,
                use_cache=use_cache,
                output_attentions=output_attentions,
                output_hidden_states=output_hidden_states,
                return_dict=return_dict,
            )

            hidden_states = outputs[0]
            logits = self.lm_head(hidden_states)
            logits = logits.float()

            if labels is not None:
                # Shift so that tokens < n predict n
                shift_logits = logits[..., :-1, :].contiguous()  
                shift_labels = labels[..., 1:].contiguous()
                # Flatten the tokens
                loss_fct = CrossEntropyLoss()
                shift_logits = shift_logits.view(-1, self.config.vocab_size)
                shift_labels = shift_labels.view(-1)
                # Enable model parallelism
                shift_labels = shift_labels.to(shift_logits.device)
                loss = loss_fct(shift_logits, shift_labels)
                sft_loss = loss

        if not return_dict:
            output = (logits,) + outputs[1:]
            return (loss,) + output if loss is not None else output
        
        if sft_loss_list and self.training:
            sft_loss = sum(sft_loss_list) / len(sft_loss_list)
            loss = (self.original_loss_weight) * sft_loss   # original_loss_weight 0.25
        if talk_loss_list:
            talk_loss = sum(talk_loss_list) / len(talk_loss_list)
            loss = loss + (1 - self.original_loss_weight) * talk_loss
        if dqn_loss_list:
            dqn_loss = sum(dqn_loss_list) / len(dqn_loss_list)
            dqn_loss = torch.clamp(dqn_loss * self.policy_loss_beta, max=1)
            if self.include_policy_loss:
                if loss is not None:
                    loss = loss + dqn_loss
                else:
                    loss = dqn_loss
    
        base_log_dict = {
            "sft_loss": sft_loss.item() if sft_loss is not None else None,
        }

        if loss is not None:
            base_log_dict["loss_train"] = loss.item()
        
        for loss_key, loss_val in base_log_dict.items():
            if loss_val is not None:
                log_dict[loss_key] += loss_val / self.n_tokens_print
                
        if self.use_policy_loss and train_policy_reward is not None:
            log_dict["policy_reward"] += original_train_policy_reward.mean().item() / self.n_tokens_print
            if fixed_policy_reward is not None:
                log_dict["fixed_policy_reward"] += fixed_policy_reward.mean().item() / self.n_tokens_print

        if self.use_policy_loss:
            log_dict["policy_loss"] += (dqn_loss.item() / self.n_tokens_print) if dqn_loss is not None else 0

        if action_loglikelihoods_list:
            log_dict["action_loglikelihoods"] += sum([nonzero_mean(action_loglikelihoods_list[i]) for i in range(len(action_loglikelihoods_list))]).item() / self.n_tokens_print

        if weights_list:
            log_dict["weights"] += np.mean(weights_list)

        if talk_loss_list:
            log_dict["loss_talk"] += sum([nonzero_mean(talk_loss_list[i]) for i in range(len(talk_loss_list))]).item() / self.n_tokens_print
        if self.log_kl_logits and kl_list:
            log_dict["kl_logits"] += np.mean(kl_list)
        # also log relative losses to loss_0
        if self.training and (contains_end and contains_start):
            self.training_steps += 1
            # print(self.training_steps)
        try:
            # if self.training_steps % (self.gradient_accumulation_steps * 256) == 0:
            if self.wandb_enabled and (contains_end and contains_start):
                if self.training_steps % (self.n_tokens_print) == 0 or not self.training:# and "0" in str(loss.device):
                    if not self.training:
                        new_log_dict = {}
                        for key in list(log_dict.keys()):
                            new_log_dict["eval_" + key] = log_dict[key]
                        log_dict = new_log_dict
                    log_dict["training_steps"] = self.training_steps 
                    log_dict["batch_size"] = batch_size
                    log_dict["example_steps"] = self.training_steps * batch_size * self.gradient_accumulation_steps
                    if self.n_ahead > 1:
                        log_dict["compute_steps"] = self.training_steps * batch_size * (self.n_ahead) * self.gradient_accumulation_steps
                    else: # There's no overhead for talk tokens if there's no thinking
                        log_dict["compute_steps"] = self.training_steps * batch_size * self.gradient_accumulation_steps
                    # remove all nans
                    for key in list(log_dict.keys()):
                        if log_dict[key] != log_dict[key]:
                            del log_dict[key]
                    if self.training:
                        wandb.log(log_dict)
                    if self.training:
                        self.log_dict = defaultdict(int)
                    else:
                        self.eval_log_dict = defaultdict(int)
        except Exception as e:
            # print(e)
            pass
        
        if self.log_thoughts:
            for i in range(input_ids.shape[0]):
                input = self.tokenizer.decode(input_ids[i])
                thought = []
                for j in range(len(sampled_token_history)):
                    thought.append(sampled_token_history[j][-1])
                with open(self.log_path, 'a') as f:
                    f.write(f"{input}{repr(self.tokenizer.decode(thought))}")
         
        return CausalLMOutputWithPast(
            loss=loss if loss is not None else None,
            logits=rm_logits if contains_start and contains_end else logits,
            past_key_values=outputs.past_key_values,
            hidden_states=outputs.hidden_states,
            attentions=outputs.attentions,
        )

    # Copied from transformers.models.llama.modeling_llama.LlamaForCausalLM.prepare_inputs_for_generation
    def prepare_inputs_for_generation(
        self,
        input_ids,
        past_key_values=None,
        attention_mask=None,
        inputs_embeds=None,
        cache_position=None,
        position_ids=None,
        use_cache=True,
        **kwargs,
    ):
        # If we have cache: let's slice `input_ids` through `cache_position`, to keep only the unprocessed tokens
        # Exception 1: when passing input_embeds, input_ids may be missing entries
        # Exception 2: some generation methods do special slicing of input_ids, so we don't need to do it here
        if past_key_values is not None:
            if inputs_embeds is not None:  # Exception 1
                input_ids = input_ids[:, -cache_position.shape[0] :]
            elif input_ids.shape[1] != cache_position.shape[0]:  # Default case (the "else", a no op, is Exception 2)
                input_ids = input_ids[:, cache_position]

        if attention_mask is not None and position_ids is None:
            # create position_ids on the fly for batch generation
            position_ids = attention_mask.long().cumsum(-1) - 1
            position_ids.masked_fill_(attention_mask == 0, 1)
            if past_key_values:
                position_ids = position_ids[:, -input_ids.shape[1] :]

        # if `inputs_embeds` are passed, we only want to use them in the 1st generation step
        if inputs_embeds is not None and cache_position[0] == 0:
            model_inputs = {"inputs_embeds": inputs_embeds}
        else:
            model_inputs = {"input_ids": input_ids.contiguous()}  # `contiguous()` needed for compilation use cases

        model_inputs.update(
            {
                "position_ids": position_ids,
                "cache_position": cache_position,
                "past_key_values": past_key_values,
                "use_cache": use_cache,
                "attention_mask": attention_mask,
            }
        )
        return model_inputs


@add_start_docstrings(
    """
    The Mistral Model transformer with a sequence classification head on top (linear layer).

    [`MistralForSequenceClassification`] uses the last token in order to do the classification, as other causal models
    (e.g. GPT-2) do.

    Since it does classification on the last token, it requires to know the position of the last token. If a
    `pad_token_id` is defined in the configuration, it finds the last token that is not a padding token in each row. If
    no `pad_token_id` is defined, it simply takes the last value in each row of the batch. Since it cannot guess the
    padding tokens when `inputs_embeds` are passed instead of `input_ids`, it does the same (take the last value in
    each row of the batch).
    """,
    MISTRAL_START_DOCSTRING,
)
# Copied from transformers.models.llama.modeling_llama.LlamaForSequenceClassification with Llama->Mistral, LLAMA->MISTRAL
class MistralForSequenceClassification(MistralPreTrainedModel):
    def __init__(self, config):
        super().__init__(config)
        self.num_labels = config.num_labels
        self.model = MistralModel(config)
        self.score = nn.Linear(config.hidden_size, self.num_labels, bias=False)

        # Initialize weights and apply final processing
        self.post_init()

    def get_input_embeddings(self):
        return self.model.embed_tokens

    def set_input_embeddings(self, value):
        self.model.embed_tokens = value

    @add_start_docstrings_to_model_forward(MISTRAL_INPUTS_DOCSTRING)
    def forward(
        self,
        input_ids: Optional[torch.LongTensor] = None,
        attention_mask: Optional[torch.Tensor] = None,
        position_ids: Optional[torch.LongTensor] = None,
        past_key_values: Optional[Union[Cache, List[torch.FloatTensor]]] = None,
        inputs_embeds: Optional[torch.FloatTensor] = None,
        labels: Optional[torch.LongTensor] = None,
        use_cache: Optional[bool] = None,
        output_attentions: Optional[bool] = None,
        output_hidden_states: Optional[bool] = None,
        return_dict: Optional[bool] = None,
    ) -> Union[Tuple, SequenceClassifierOutputWithPast]:
        r"""
        labels (`torch.LongTensor` of shape `(batch_size,)`, *optional*):
            Labels for computing the sequence classification/regression loss. Indices should be in `[0, ...,
            config.num_labels - 1]`. If `config.num_labels == 1` a regression loss is computed (Mean-Square loss), If
            `config.num_labels > 1` a classification loss is computed (Cross-Entropy).
        """
        return_dict = return_dict if return_dict is not None else self.config.use_return_dict

        transformer_outputs = self.model(
            input_ids,
            attention_mask=attention_mask,
            position_ids=position_ids,
            past_key_values=past_key_values,
            inputs_embeds=inputs_embeds,
            use_cache=use_cache,
            output_attentions=output_attentions,
            output_hidden_states=output_hidden_states,
            return_dict=return_dict,
        )
        hidden_states = transformer_outputs[0]
        logits = self.score(hidden_states)

        if input_ids is not None:
            batch_size = input_ids.shape[0]
        else:
            batch_size = inputs_embeds.shape[0]

        if self.config.pad_token_id is None and batch_size != 1:
            raise ValueError("Cannot handle batch sizes > 1 if no padding token is defined.")
        if self.config.pad_token_id is None:
            sequence_lengths = -1
        else:
            if input_ids is not None:
                # if no pad token found, use modulo instead of reverse indexing for ONNX compatibility
                sequence_lengths = torch.eq(input_ids, self.config.pad_token_id).int().argmax(-1) - 1
                sequence_lengths = sequence_lengths % input_ids.shape[-1]
                sequence_lengths = sequence_lengths.to(logits.device)
            else:
                sequence_lengths = -1

        pooled_logits = logits[torch.arange(batch_size, device=logits.device), sequence_lengths]

        loss = None
        if labels is not None:
            labels = labels.to(logits.device)
            if self.config.problem_type is None:
                if self.num_labels == 1:
                    self.config.problem_type = "regression"
                elif self.num_labels > 1 and (labels.dtype == torch.long or labels.dtype == torch.int):
                    self.config.problem_type = "single_label_classification"
                else:
                    self.config.problem_type = "multi_label_classification"

            if self.config.problem_type == "regression":
                loss_fct = MSELoss()
                if self.num_labels == 1:
                    loss = loss_fct(pooled_logits.squeeze(), labels.squeeze())
                else:
                    loss = loss_fct(pooled_logits, labels)
            elif self.config.problem_type == "single_label_classification":
                loss_fct = CrossEntropyLoss()
                loss = loss_fct(pooled_logits.view(-1, self.num_labels), labels.view(-1))
            elif self.config.problem_type == "multi_label_classification":
                loss_fct = BCEWithLogitsLoss()
                loss = loss_fct(pooled_logits, labels)
        if not return_dict:
            output = (pooled_logits,) + transformer_outputs[1:]
            return ((loss,) + output) if loss is not None else output

        return SequenceClassifierOutputWithPast(
            loss=loss,
            logits=pooled_logits,
            past_key_values=transformer_outputs.past_key_values,
            hidden_states=transformer_outputs.hidden_states,
            attentions=transformer_outputs.attentions,
        )


@add_start_docstrings(
    """
    The Mistral Model transformer with a token classification head on top (a linear layer on top of the hidden-states
    output) e.g. for Named-Entity-Recognition (NER) tasks.
    """,
    MISTRAL_START_DOCSTRING,
)
# Copied from transformers.models.llama.modeling_llama.LlamaForTokenClassification with Llama->Mistral, LLAMA->MISTRAL
class MistralForTokenClassification(MistralPreTrainedModel):
    def __init__(self, config):
        super().__init__(config)
        self.num_labels = config.num_labels
        self.model = MistralModel(config)
        if getattr(config, "classifier_dropout", None) is not None:
            classifier_dropout = config.classifier_dropout
        elif getattr(config, "hidden_dropout", None) is not None:
            classifier_dropout = config.hidden_dropout
        else:
            classifier_dropout = 0.1
        self.dropout = nn.Dropout(classifier_dropout)
        self.score = nn.Linear(config.hidden_size, config.num_labels)

        # Initialize weights and apply final processing
        self.post_init()

    def get_input_embeddings(self):
        return self.model.embed_tokens

    def set_input_embeddings(self, value):
        self.model.embed_tokens = value

    @add_start_docstrings_to_model_forward(MISTRAL_INPUTS_DOCSTRING)
    def forward(
        self,
        input_ids: Optional[torch.LongTensor] = None,
        attention_mask: Optional[torch.Tensor] = None,
        position_ids: Optional[torch.LongTensor] = None,
        past_key_values: Optional[List[torch.FloatTensor]] = None,
        inputs_embeds: Optional[torch.FloatTensor] = None,
        labels: Optional[torch.LongTensor] = None,
        use_cache: Optional[bool] = None,
        output_attentions: Optional[bool] = None,
        output_hidden_states: Optional[bool] = None,
        return_dict: Optional[bool] = None,
    ) -> Union[Tuple, TokenClassifierOutput]:
        r"""
        labels (`torch.LongTensor` of shape `(batch_size,)`, *optional*):
            Labels for computing the sequence classification/regression loss. Indices should be in `[0, ...,
            config.num_labels - 1]`. If `config.num_labels == 1` a regression loss is computed (Mean-Square loss), If
            `config.num_labels > 1` a classification loss is computed (Cross-Entropy).
        """
        return_dict = return_dict if return_dict is not None else self.config.use_return_dict

        outputs = self.model(
            input_ids,
            attention_mask=attention_mask,
            position_ids=position_ids,
            past_key_values=past_key_values,
            inputs_embeds=inputs_embeds,
            use_cache=use_cache,
            output_attentions=output_attentions,
            output_hidden_states=output_hidden_states,
            return_dict=return_dict,
        )
        sequence_output = outputs[0]
        sequence_output = self.dropout(sequence_output)
        logits = self.score(sequence_output)

        loss = None
        if labels is not None:
            loss_fct = CrossEntropyLoss()
            loss = loss_fct(logits.view(-1, self.num_labels), labels.view(-1))

        if not return_dict:
            output = (logits,) + outputs[2:]
            return ((loss,) + output) if loss is not None else output

        return TokenClassifierOutput(
            loss=loss,
            logits=logits,
            hidden_states=outputs.hidden_states,
            attentions=outputs.attentions,
        )
