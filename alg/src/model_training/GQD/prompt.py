MISTRAL_PROMPT = """Below is an instruction that describes a task. Write a response that appropriately completes the request.

### Instruction:
%s

### Response:
"""

LLAMA_PROMPT = """<|begin_of_text|><|start_header_id|>system<|end_header_id|>

You are a helpful AI assistant.<|eot_id|><|start_header_id|>user<|end_header_id|>

%s<|eot_id|><|start_header_id|>assistant<|end_header_id|>
"""

QWEN_PROMPT = """<|im_start|>system
You are Qwen, created by Alibaba Cloud. You are a helpful assistant.<|im_end|>
<|im_start|>user
%s<|im_end|>
<|im_start|>assistant
"""

GQD_DECOMPOSITION_PROMPT = """Please analyze the following query and return the explanation in dictionary format.

Response format:
{{'is_complex': True/False, 'sub_queries': [], 'parent_child': []}}

Analysis:

1. Classify the nature of the query
   - Complex query: consists of multiple sub-queries (set is_complex to True)
   - Simple query: can be directly answered (set is_complex to False, leave sub_queries and parent_child empty)

2. Decomposing a Complex Query
   - Break down into sub-queries and store in sub_queries list
   - If a query contains multiple target entities, split it into multiple sub-queries
   - Each sub-query should be indivisible
   - No duplicates, use full names for people/places/organizations
   - Maximum 6 sub-queries

3. Analyzing Dependencies Between Sub-Queries
   - Analyze dependency relationships and store in parent_child
   - If sub-queries are independent, parent_child remains empty
   - If child cannot be answered without parent, it's a dependent relationship
   - A query can be both parent and child in different relationships

Query: {query}
Response:
"""

PROMPTS = {
    "gqd_decomposition": GQD_DECOMPOSITION_PROMPT,
    "mistral": MISTRAL_PROMPT,
    "llama": LLAMA_PROMPT,
    "qwen": QWEN_PROMPT,
}

