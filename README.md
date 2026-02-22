# GraTAG: Production AI Search via Graph-Based Query Decomposition and Triplet-Aligned Generation with Rich Multimodal Representations

<p align="center">
  <img src="material/teaser2_v1.png" alt="GraTAG Overview" width="100%">
</p>

**GraTAG** is a comprehensive AI search engine framework that addresses key challenges in relevance, comprehensiveness, and presentation through three core innovations:

* **Graph-Based Query Decomposition (GQD)** — dynamically breaks down complex or ambiguous queries into structured sub-queries with explicit dependencies, enabling more precise, stepwise retrieval.

<p align="center">
  <img src="material/GQD_v1.png" alt="Graph-Based Query Decomposition" width="80%">
</p>

* **Triplet-Aligned Generation (TAG)** — dynamically constructs relation triplets from retrieved documents to explicitly model entity relationships, factual dependencies, and logical connections, enabling the model to generate more coherent and comprehensive answers.

<p align="center">
  <img src="material/TAG.png" alt="Triplet-Aligned Generation" width="80%">
</p>

* **Rich Multimodal Presentations** — integrates timeline visualization and textual-visual choreography to reduce cognitive load and enhance information verification.

<p align="center">
  <img src="material/Rich Answer Presentations.png" alt="Rich Multimodal Presentations" width="80%">
</p>

Evaluated on 1,000 recent real-world queries with over 243,000 expert ratings across 9 criteria, GraTAG **outperforms eight existing systems** in human expert assessments, excelling in relevance, comprehensiveness, and insightfulness. Compared to the strongest baseline, GraTAG improves comprehensiveness by **10.8%**, insightfulness by **7.9%**, and the overall average score by **4.8%**. On the public benchmark BrowseComp, GraTAG outperforms the best baseline by **17.3%**.

<p align="center">
  <img src="material/results_v1.png" alt="Multi-faceted comparison of different systems. Higher value indicates better performance, 10 is the maximum." width="100%">
</p>

---

## Pipeline Overview

GraTAG is an end-to-end production-ready RAG system comprising seven key stages:

1. **Query Preprocessing** — uses a fine-tuned LLM to filter unsafe content, clarify ambiguous queries, and canonicalize spatiotemporal expressions.
2. **Graph-Based Query Decomposition (GQD)** — decomposes complex queries into structured sub-queries with explicit dependencies to enable hierarchical reasoning.
3. **Sub-query Expansion** — generates semantic variations to improve coverage.
4. **Stepwise Retrieval** — performs multi-source retrieval guided by the GQD structure.
5. **Deduplication and Reranking** — removes redundancy and suppresses noise from retrieved documents.
6. **Triplet-Aligned Generation (TAG)** — dynamically constructs relation triplets from evidence chunks to restore logical coherence.
7. **Rich Multimodal Presentations** — delivers structured outputs with timelines and citations to enhance user experience.

---

## Concepts at a Glance

* **GQD** decomposes complex queries into atomic sub-queries represented as a directed acyclic graph (DAG) that explicitly encodes information flow among sub-queries. In contrast to linear or tree-based approaches, GQD captures parallel and joint dependencies, enabling finer-grained and more flexible reasoning. The GQD model is post-trained via supervised fine-tuning on curated query-GQD pairs, followed by reinforcement learning (GRPO) alignment with RAG task performance.
* **TAG** extracts triplets from retrieved documents and aligns them with the answer generation process to explicitly bridge missing logic and relations across chunks. By injecting these structural cues, TAG enhances cross-chunk reasoning coherence and mitigates hallucination. TAG employs a cold-start triplet extraction stage followed by answer generation training with REINFORCE-based triplet alignment.
* **Rich Multimodal Presentation** integrates timeline visualizations and textual-visual choreography to reduce cognitive load and enhance information verification. Timeline visualization extracts, deduplicates, groups, and sorts events from retrieved chunks; textual-visual choreography matches and places relevant images alongside generated paragraphs using a multi-measure similarity scoring and the Hungarian algorithm.

---

## Repository Layout

```
.
├── alg/
│   ├── src/
│   │   ├── include/
│   │   ├── model_training/
│   │   │   ├── GQD/                 # GQD-related training code
│   │   │   └── TAG/                 # TAG-related training code
│   │   ├── modules/
│   │   ├── pipeline/
│   │   └── script/
│   ├── Dockerfile
│   ├── LICENSE
│   ├── requirements.txt
│   ├── route.json
│   ├── run.py
│   └── README.md
├── backend/                         # Backend application code
├── frontend/                        # Frontend application code
└── README.md                        # (this file)
```

> `frontend/` stores the web UI; `backend/` stores backend code; `alg/` contains algorithm services and training. The full GraTAG pipeline integrates GQD, TAG, and multimodal presentation components.

---

## Code Documentation

Due to the extensive codebase and complexity of the implementation, a detailed **Cookbook** with step-by-step explanations, usage examples, and implementation guides will be released in the near future.