from __future__ import annotations

import os
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from graph_ir_backend.service import GraphIRService

app = FastAPI(
    title="Graph IR API",
    version="1.0.0",
    description=(
        "Backend API for Information Retrieval using dependency graphs + semantic node similarity. "
        "Designed for Vercel frontend + Render backend deployment."
    ),
)

service = GraphIRService()


def _cors_origins() -> list[str]:
    raw = os.getenv("CORS_ORIGINS", "*")
    origins = [part.strip() for part in raw.split(",") if part.strip()]
    return origins or ["*"]


app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class LoadCorpusRequest(BaseModel):
    source: Literal["demo", "trec-covid"] = "demo"
    limit: int = Field(default=1000, ge=10, le=5000)
    remove_stopwords: bool = True


class SearchRequest(BaseModel):
    source: Literal["demo", "trec-covid"] = "demo"
    limit: int = Field(default=1000, ge=10, le=5000)
    remove_stopwords: bool = True
    query: str = ""
    top_k: int = Field(default=5, ge=1, le=50)
    node_weight: float = Field(default=0.7, ge=0.0, le=1.0)
    edge_weight: float = Field(default=0.3, ge=0.0, le=1.0)
    qid: str | None = None
    topic_field: str = "description"


class EvaluateRequest(BaseModel):
    source: Literal["demo", "trec-covid"] = "trec-covid"
    limit: int = Field(default=1000, ge=10, le=5000)
    remove_stopwords: bool = True
    qid: str
    auto_pick_qid: bool = True
    topic_field: str = "description"
    top_k: int = Field(default=5, ge=1, le=50)
    node_weight: float = Field(default=0.7, ge=0.0, le=1.0)
    edge_weight: float = Field(default=0.3, ge=0.0, le=1.0)


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "service": "graph-ir-api",
        "loaded": service.status().get("loaded", False),
    }


@app.get("/api/v1/status")
def status() -> dict:
    return service.status()


@app.post("/api/v1/corpus/load")
def load_corpus(payload: LoadCorpusRequest) -> dict:
    try:
        state = service.ensure_loaded(
            source=payload.source,
            limit=payload.limit,
            remove_stopwords=payload.remove_stopwords,
        )
        return {
            "message": "corpus loaded",
            "status": service.status(),
            "topics_preview": service.list_topics(max_items=10),
            "documents_loaded": len(state.retriever.prepared_documents),
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/v1/topics")
def list_topics(limit: int = 200) -> dict:
    max_items = max(1, min(limit, 1000))
    return {"topics": service.list_topics(max_items=max_items)}


@app.post("/api/v1/search")
def search(payload: SearchRequest) -> dict:
    try:
        return service.search(
            source=payload.source,
            limit=payload.limit,
            remove_stopwords=payload.remove_stopwords,
            query=payload.query,
            top_k=payload.top_k,
            node_weight=payload.node_weight,
            edge_weight=payload.edge_weight,
            qid=payload.qid,
            topic_field=payload.topic_field,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/v1/evaluate")
def evaluate(payload: EvaluateRequest) -> dict:
    try:
        return service.evaluate(
            source=payload.source,
            limit=payload.limit,
            remove_stopwords=payload.remove_stopwords,
            qid=payload.qid,
            auto_pick_qid=payload.auto_pick_qid,
            topic_field=payload.topic_field,
            top_k=payload.top_k,
            node_weight=payload.node_weight,
            edge_weight=payload.edge_weight,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
