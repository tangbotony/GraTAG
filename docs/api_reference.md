# Backend API Reference

The backend exposes RESTful endpoints under `/api/`. All endpoints (except login) require JWT authentication.

## QA Endpoints (`/api/qa/`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/qa/series` | Create a new QA conversation series |
| `POST` | `/api/qa/collection` | Create a QA collection within a series |
| `POST` | `/api/qa/complete/ask` | Submit a query for intent analysis and supplementary question generation |
| `POST` | `/api/qa/ask` | Submit a query for answer generation (SSE streaming response) |
| `GET` | `/api/qa/history` | Retrieve QA conversation history |
| `GET` | `/api/qa/series/<id>` | Get details of a specific QA series |
| `DELETE` | `/api/qa/series/<id>` | Delete a QA series |
| `GET` | `/api/qa/pair/<id>` | Get a specific QA pair |

## Search Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/qa/search/completion` | Query auto-completion and recommendation |
| `GET` | `/api/qa/recommend` | Get recommended/trending questions |
| `GET` | `/api/qa/search/history` | Get user search history |
| `DELETE` | `/api/qa/search/history` | Clear search history |

## Document Search Endpoints (`/api/doc_search/`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/doc_search/<doc_id>` | Preview a document |
| `GET` | `/api/doc_search/doc_list/<series_id>` | List documents in a QA series |
| `DELETE` | `/api/doc_search/doc` | Remove a document |
| `PUT` | `/api/doc_search/update_select` | Update document selection state |

## Search Modes

| Mode | Description |
|------|-------------|
| `pro` | Full pipeline with GQD + TAG + Timeline |
| `lite` | Lightweight mode without timeline generation |
| `doc` | Document-scoped QA (searches within uploaded documents) |
| `doc_pro` | Document QA with full pipeline features |

## Streaming Response Protocol

The `/api/qa/ask` endpoint returns Server-Sent Events (SSE) with JSON payloads. Each event has a `type` field:

```
data: {"type": "state", "content": "searching"}
data: {"type": "intention_query", "content": "rewritten query"}
data: {"type": "ref_page", "content": [{"url": "...", "title": "...", "summary": "..."}]}
data: {"type": "ref_answer", "content": {"references": [...]}}
data: {"type": "text", "content": "answer chunk..."}
data: {"type": "image", "content": {"url": "...", "position": 3}}
data: {"type": "time_line", "content": {"events": [...]}}
data: {"type": "text_end", "content": ""}
data: {"type": "recommendation", "content": ["follow-up question 1", "..."]}
```

## Data Models (MongoDB)

| Collection | Key Fields | Description |
|------------|-----------|-------------|
| `Qa_series` | `user_id`, `title`, `qa_pair_collection_list` | Top-level conversation thread |
| `Qa_pair_collection` | `qa_series_id`, `query`, `qa_pair_list`, `is_subscribed` | Collection of Q&A pairs within a series |
| `Qa_pair` | `query`, `general_answer`, `images`, `timeline_id`, `reference`, `search_mode` | Individual question-answer pair with references |
| `Timeline` | `data` (DictField) | Timeline visualization data |
| `Subscription` | `query`, `push_interval`, `email`, `user_id` | Query subscription for periodic updates |
