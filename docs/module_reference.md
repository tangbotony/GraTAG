# Core Module Reference

## Pipeline Entry — `alg/src/pipeline/functions.py`

The main pipeline orchestrates the full answer generation flow through two primary functions:

| Function | Description |
|----------|-------------|
| `supply_question(body, headers)` | Phase 1: Receives user query, performs intent understanding (rejection check, supplementary question generation, query translation), and initializes the QA context. |
| `answer(body, headers)` | Phase 2: Executes the full RAG pipeline — query decomposition, retrieval, answer generation, and timeline construction — returning a streaming response. |

**Execution Flow of `answer()`:**

```
1. Load QA context from Elasticsearch
2. [Parallel] Query decomposition (GQD) + Retrieval range detection
3. Graph-based multi-source retrieval
4. [Parallel] Answer generation (TAG, streaming) + Timeline generation
5. Further question recommendation
6. Stream results via Server-Sent Events
```

## Query Preprocessing and Intent Understanding

**Query Preprocessing:** A fine-tuned LLM (Qwen-2.5-14B) filters unsafe/harmful queries and clarifies ambiguous ones by prompting the user with options. A second LLM (Qwen-2.5-14B) rewrites the query by resolving relative spatiotemporal terms (e.g., "last week" → precise timestamp ranges), vague locations ("nearby" → specific places), and incomplete entity names.

**Class: `IntentionUnderstandingTask`** — `modules/intention_understanding_group/`

| Method | Output |
|--------|--------|
| `get_intention()` | Returns rejection decision, supplementary question suggestions, related events, and translated query |
| `get_reject_judgement()` | Returns only the rejection decision for unsafe/inappropriate content |

Output structure:

```json
{
  "question_rejection": {"is_reject": false, "reject_reason": ""},
  "question_supplement": {"is_supply": false, "supply_description": "", "supply_choices": []},
  "related_event": ""
}
```

## Query Decomposition (GQD) — `modules/query_division_based_cot_group/`

**Class: `QueryDivisionBasedCoTTask`**

Decomposes complex queries into a directed acyclic graph (DAG) of sub-queries with explicit dependencies.

| Method | Description |
|--------|-------------|
| `get_cot(use_scene="general")` | Entry point; dispatches to `query_rewrite_general()` or `query_rewrite_timeline()` based on scene |
| `query_rewrite_general()` | Decomposes general queries via `MultiHopSplitQueries`, constructs DAG using `IGraph` |
| `query_rewrite_timeline()` | Decomposes timeline-specific queries via `TimeLineSplitQueries` |

**DAG Structure (`IGraph`):**

```python
class IGraph:
    """Directed acyclic graph for structured query decomposition."""
    add_new_node(node: ArcNode)          # Add sub-query node
    insert_node_front(new_node, ori_val) # Insert dependency before node
    add_arrow(query, former_val)         # Add dependency edge
    get_turns()                          # BFS execution order respecting dependencies
    get_attr(attr_name)                  # Filter nodes by attribute (need_rag, FunctionCall, etc.)
```

Each `ArcNode` contains: sub-query text, `need_rag` flag, `FunctionCall` indicator, retrieved answer, and dependency links.

## Multi-Source Retrieval — `modules/recall_group/`

**Class: `RecallTask`**

Performs graph-guided multi-source retrieval following the DAG execution order.

| Method | Description |
|--------|-------------|
| `get_graph_recall(graph, application, retrieval_field, top_n_indices)` | Traverses the DAG, retrieves documents for each sub-query in parallel |
| `_router(search_field, origin_query)` | Routes queries to appropriate data sources (news, hot news, general) |
| `_get_recall_queries(graph, application)` | Extracts retrieval queries from DAG nodes |

**Retrieval Sources:**
- Online web search (via IAAR Database API) — multiple search engines queried simultaneously
- Elasticsearch full-text search
- Milvus vector similarity search

**Chunking:** Uses `RecursiveCharacterTextSplitter` with chunk size **350** and overlap **25%**, following Azure AI Search findings.

**Chunk Deduplication:** Computes pairwise cosine similarity using fine-tuned `bge-large` embeddings. Chunks with similarity > **0.8** are deduplicated via a greedy maximum independent set strategy.

**Reranking:** Uses fine-tuned `bge-reranker-v2-m3` to sort chunks by relevance to each sub-query. Configuration from `CommonConfig`:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `topk_es` | 1000 | Top-K candidates from Elasticsearch |
| `topk_vec` | 500 | Top-K candidates from vector search |
| `topk_rerank` | 150 | Final top-K after reranking |

## Answer Generation (TAG) — `modules/query_answer_group/`

**Class: `QueryAnswerTask`**

Generates coherent answers by aligning extracted relation triplets with evidence chunks.

| Method | Description |
|--------|-------------|
| `get_query_answer(query, qa_series_id, ..., streaming=True)` | Streaming answer generation with inline citations and image placement |
| `get_query_answer_without_streaming(...)` | Synchronous answer generation |

**Textual-Visual Choreography:** Images from retrieved documents are filtered and placed alongside generated paragraphs:

| Step | Method | Threshold / Model |
|------|--------|-------------------|
| Image quality filtering | Rule-based | Removes logos, icons, low-res images |
| Image relevance filtering | bge-reranker-v2-m3 | similarity ≥ **0.3** |
| Image-text similarity (1) | clip-vit-huge-patch14 | paragraph ↔ image embedding |
| Image-text similarity (2) | bge-reranker-v2-m3 | paragraph ↔ document title |
| Image-text similarity (3) | bge-large | paragraph ↔ document text |
| Optimal alignment | Hungarian algorithm | weighted average of (1)(2)(3) |

**Streaming Output Types:**

| Type | Content |
|------|---------|
| `state` | Pipeline status updates |
| `text` | Answer text chunk |
| `image` | Image reference to insert |
| `ref_answer` | Citation/reference information |
| `text_end` | End-of-answer signal |
| `recommendation` | Suggested follow-up questions |

## Timeline Generation — `modules/timeline_group/`

**Class: `TimelineTask`**

Generates structured timeline visualizations for temporal queries.

**Pipeline Steps:**

```
Query Rewrite → Intent Understanding → CoT Query Splitting
→ Multi-source Retrieval → Event Extraction → Deduplication
→ Event Grouping → Highlight Extraction → Granularity Determination → Reference Extraction
```

**Key Parameters:**

| Parameter | Value |
|-----------|-------|
| Event extraction LLM | Qwen2.5-14B-Instruct |
| Event embedding model | bge-large |
| Event deduplication threshold | cosine similarity > 0.9 |

Runs in parallel with answer generation when `pro_flag=True`.

## Context Management — `include/context/RagQAContext.py`

**Class: `RagQAContext`**

Central context object shared across all pipeline modules within a single QA session.

| Category | Key Methods |
|----------|------------|
| **Question** | `add_single_question(request_id, question_id, question, pro_flag)`, `get_single_question()` |
| **DAG** | `set_dag(dag)`, `get_dag()` |
| **References** | `add_references_result(references)`, `get_references_result_doc(need_new_content)` |
| **Serialization** | `context_encode(obj)` → Base64 string, `context_decode(str)` → `RagQAContext` |

Context is persisted in Elasticsearch between the `supply_question` and `answer` phases, enabling stateful multi-turn conversations.
