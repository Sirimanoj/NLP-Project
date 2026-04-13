# Graph IR Backend (Render)

FastAPI backend for your Graph IR project.

## Features

- Corpus loading (`demo`, `trec-covid`)
- Graph-based retrieval with weighted node + edge scoring
- Topic-driven search (`qid` + `topic_field`)
- Evaluation (`Precision@K`, `Recall@K`, `F1@K`)
- CORS ready for Vercel frontend
- Deployment-safe NLP fallback parser when spaCy is unavailable

## Local Run

```bash
pip install -r graph_ir_backend/requirements.txt
uvicorn graph_ir_backend.main:app --reload --host 127.0.0.1 --port 8001
```

Optional (stronger semantic model):

```bash
pip install -r graph_ir_backend/requirements-advanced.txt
set GRAPH_IR_EMBEDDING_MODE=sentence
```

Optional (full spaCy dependency parsing quality) is included in
`requirements-advanced.txt`. Default `requirements.txt` is kept lightweight for
reliable cloud builds.

## API Endpoints

- `GET /health`
- `GET /api/v1/status`
- `POST /api/v1/corpus/load`
- `GET /api/v1/topics`
- `POST /api/v1/search`
- `POST /api/v1/evaluate`

## Render Start Command

```bash
uvicorn graph_ir_backend.main:app --host 0.0.0.0 --port $PORT
```

## Environment Variables

- `CORS_ORIGINS` (default `*`)
- `GRAPH_IR_EMBEDDING_MODE` (`lite` or `sentence`, default `lite`)
