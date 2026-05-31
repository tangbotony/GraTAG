# Configuration Reference

## Algorithm Service — `alg/src/include/config/common_config.py`

| Section | Key Parameters | Description |
|---------|---------------|-------------|
| `FSCHAT` | `vllm_url`, `hf_url` | LLM inference service endpoints |
| `MODEL_CONFIG` | `qwen2_72b_vllm`, `memory25_72b` | Model-specific URLs and prompt templates |
| `ES_QA` | `url`, `index`, `auth` | Elasticsearch connection for QA context |
| `MILVUS` | `host`, `port`, `collection` | Milvus vector database connection |
| `RERANK` | `topk_es`, `topk_vec`, `topk_rerank` | Retrieval and reranking thresholds |
| `IAAR_DataBase` | `url`, `default_param` | External search API configuration |
| `CHUNK_SPLIT` | `model_url` | Text chunking model endpoint |
| `SIMILARITY_CONFIG` | `url` | Embedding similarity service |

## Backend Service — `backend/Backend/config/config.ini`

| Section | Key Parameters | Description |
|---------|---------------|-------------|
| `DEFAULT` | `Host`, `Port`, `ALGORITHM_URL` | Service binding and algorithm service address |
| `MONGO` | `Host`, `Port`, `DB`, `Username`, `Password` | MongoDB connection |
| `ES` | `url`, `auth`, `passwd` | Elasticsearch connection |
| `OSS` | `endpoint`, `access_key_id`, `bucket_name` | Object storage for documents/images |
| `MINIO` | `url`, `access_key`, `secret_key` | MinIO alternative storage |
| `PROMETHEUS` | `enable_flask`, `process_name` | Monitoring configuration |
