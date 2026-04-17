from __future__ import annotations

import hashlib
import os
import re
import threading
from dataclasses import dataclass
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from graph_ir_app.engine import (
    GraphIRRetriever,
    RawDocument,
    get_demo_corpus,
    load_trec_covid,
    precision_recall_at_k,
)


class LightweightEmbeddingModel:
    """Fallback embedding model to keep the API available without heavy dependencies."""

    def __init__(self, dim: int = 384) -> None:
        self.dim = dim
        self.is_lightweight_hash = True

    def encode(self, texts, normalize_embeddings: bool = True, show_progress_bar: bool = False):
        vectors = []
        for text in texts:
            seed = int(hashlib.sha256(str(text).encode("utf-8")).hexdigest()[:8], 16)
            rng = np.random.default_rng(seed)
            vec = rng.normal(size=self.dim).astype(np.float32)
            if normalize_embeddings:
                norm = np.linalg.norm(vec)
                if norm > 0:
                    vec = vec / norm
            vectors.append(vec)
        return np.vstack(vectors) if vectors else np.empty((0, self.dim), dtype=np.float32)


class _LiteToken:
    def __init__(self, text: str, is_stop: bool = False) -> None:
        self.text = text
        self.lemma_ = text.lower()
        self.is_space = text.isspace()
        self.is_punct = bool(text) and all(not ch.isalnum() for ch in text)
        self.is_stop = is_stop
        self.dep_ = "dep"
        self.head = self


class LightweightDependencyNLP:
    """Tiny parser fallback used when spaCy is unavailable in deployment."""

    _stopwords = {
        "a",
        "an",
        "the",
        "and",
        "or",
        "to",
        "of",
        "in",
        "on",
        "for",
        "with",
        "is",
        "are",
        "was",
        "were",
        "be",
        "by",
        "as",
        "at",
        "it",
        "this",
        "that",
        "from",
    }

    def __call__(self, text: str) -> list[_LiteToken]:
        parts = re.findall(r"[A-Za-z0-9']+|[^\w\s]", text or "")
        tokens = [_LiteToken(p, is_stop=(p.lower() in self._stopwords)) for p in parts]
        prev_content: _LiteToken | None = None
        for tok in tokens:
            if tok.is_space:
                continue
            if tok.is_punct:
                tok.dep_ = "punct"
                tok.head = prev_content or tok
                continue
            if prev_content is None:
                tok.dep_ = "root"
                tok.head = tok
            else:
                tok.dep_ = "dep"
                tok.head = prev_content
            prev_content = tok
        return tokens


@dataclass
class CorpusState:
    source: str
    limit: int
    remove_stopwords: bool
    retriever: GraphIRRetriever
    topics: pd.DataFrame
    qrels: pd.DataFrame
    nlp_mode: str
    embedding_mode: str
    loaded_at: str


class GraphIRService:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._state: CorpusState | None = None
        self._nlp, self._nlp_mode = self._load_nlp_model()
        self._embedder, self._embedding_mode = self._load_embedding_model()

    def _load_nlp_model(self):
        try:
            import spacy
        except Exception:
            return LightweightDependencyNLP(), "lightweight_dependency_parser"

        try:
            return spacy.load("en_core_web_sm"), "spacy_en_core_web_sm"
        except OSError:
            try:
                nlp = spacy.blank("en")
                if "sentencizer" not in nlp.pipe_names:
                    nlp.add_pipe("sentencizer")
                return nlp, "spacy_blank_en"
            except Exception:
                return LightweightDependencyNLP(), "lightweight_dependency_parser"

    def _load_embedding_model(self):
        mode = os.getenv("GRAPH_IR_EMBEDDING_MODE", "lite").lower()
        if mode in {"sentence", "auto"}:
            try:
                from sentence_transformers import SentenceTransformer

                return SentenceTransformer("all-MiniLM-L6-v2"), "sentence_transformers_all_MiniLM_L6_v2"
            except Exception:
                if mode == "sentence":
                    raise
        return LightweightEmbeddingModel(), "lightweight_hash_embeddings"

    def ensure_loaded(
        self,
        source: str,
        limit: int,
        remove_stopwords: bool,
    ) -> CorpusState:
        source = source.lower().strip()
        if source not in {"demo", "trec-covid"}:
            raise ValueError("source must be one of: demo, trec-covid")
        if limit < 10:
            raise ValueError("limit must be >= 10")

        with self._lock:
            if (
                self._state is not None
                and self._state.source == source
                and self._state.limit == limit
                and self._state.remove_stopwords == remove_stopwords
            ):
                return self._state

            if source == "trec-covid":
                docs, topics, qrels = load_trec_covid(limit=limit)
            else:
                docs = get_demo_corpus()
                topics = pd.DataFrame()
                qrels = pd.DataFrame()

            if not docs:
                raise RuntimeError("No documents were loaded for the requested corpus.")

            retriever = GraphIRRetriever(
                documents=docs,
                nlp=self._nlp,
                embedding_model=self._embedder,
                remove_stopwords=remove_stopwords,
            )

            self._state = CorpusState(
                source=source,
                limit=limit,
                remove_stopwords=remove_stopwords,
                retriever=retriever,
                topics=topics,
                qrels=qrels,
                nlp_mode=self._nlp_mode,
                embedding_mode=self._embedding_mode,
                loaded_at=datetime.now(timezone.utc).isoformat(),
            )
            return self._state

    def status(self) -> dict:
        if self._state is None:
            return {
                "loaded": False,
                "nlp_mode": self._nlp_mode,
                "embedding_mode": self._embedding_mode,
            }

        return {
            "loaded": True,
            "source": self._state.source,
            "limit": self._state.limit,
            "remove_stopwords": self._state.remove_stopwords,
            "documents": len(self._state.retriever.prepared_documents),
            "topics": 0 if self._state.topics.empty else len(self._state.topics),
            "qrels": 0 if self._state.qrels.empty else len(self._state.qrels),
            "loaded_at": self._state.loaded_at,
            "nlp_mode": self._state.nlp_mode,
            "embedding_mode": self._state.embedding_mode,
        }

    def list_topics(self, max_items: int = 200) -> list[dict]:
        if self._state is None or self._state.topics.empty:
            return []

        topics = self._state.topics.copy()
        if "qid" not in topics.columns:
            return []
        topics["qid"] = topics["qid"].astype(str)
        columns = [c for c in ["qid", "title", "description", "narrative"] if c in topics.columns]
        rows = topics[columns].head(max_items).to_dict(orient="records")

        if self._state.qrels.empty:
            return rows

        qrels = self._state.qrels.copy()
        if "qid" not in qrels.columns or "docno" not in qrels.columns or "label" not in qrels.columns:
            return rows

        qrels = qrels[qrels["label"] > 0].copy()
        if qrels.empty:
            return rows

        qrels["qid"] = qrels["qid"].astype(str)
        qrels["docno"] = qrels["docno"].astype(str)
        total_by_qid = qrels.groupby("qid")["docno"].nunique().to_dict()

        loaded_docnos = {str(doc.docno) for doc in self._state.retriever.prepared_documents}
        loaded_qrels = qrels[qrels["docno"].isin(loaded_docnos)]
        loaded_by_qid = loaded_qrels.groupby("qid")["docno"].nunique().to_dict()

        for row in rows:
            qid = str(row.get("qid", ""))
            row["relevant_total_qrels"] = int(total_by_qid.get(qid, 0))
            row["relevant_in_loaded_subset"] = int(loaded_by_qid.get(qid, 0))
        return rows

    def _resolve_query_text(self, state: CorpusState, query: str, qid: str | None, topic_field: str) -> str:
        if query and query.strip():
            return query.strip()

        if qid and not state.topics.empty and topic_field in state.topics.columns:
            topic_rows = state.topics[state.topics["qid"].astype(str) == str(qid)]
            if not topic_rows.empty:
                value = str(topic_rows.iloc[0].get(topic_field, "") or "").strip()
                if value:
                    return value

        raise ValueError("Provide a non-empty query or valid qid+topic_field.")

    def search(
        self,
        source: str,
        limit: int,
        remove_stopwords: bool,
        query: str,
        top_k: int,
        node_weight: float,
        edge_weight: float,
        qid: str | None = None,
        topic_field: str = "description",
    ) -> dict:
        state = self.ensure_loaded(source=source, limit=limit, remove_stopwords=remove_stopwords)
        resolved_query = self._resolve_query_text(state, query, qid, topic_field)

        results = state.retriever.retrieve_top_k(
            query=resolved_query,
            k=top_k,
            node_weight=node_weight,
            edge_weight=edge_weight,
        )
        query_features = state.retriever.extract_graph_features(resolved_query)

        return {
            "query": resolved_query,
            "source": state.source,
            "top_k": top_k,
            "results": results,
            "query_nodes": len(query_features.nodes),
            "query_relations": len(query_features.relations),
            "status": self.status(),
        }

    def evaluate(
        self,
        source: str,
        limit: int,
        remove_stopwords: bool,
        qid: str,
        auto_pick_qid: bool,
        topic_field: str,
        top_k: int,
        node_weight: float,
        edge_weight: float,
    ) -> dict:
        if not qid:
            raise ValueError("qid is required for evaluation.")

        state = self.ensure_loaded(source=source, limit=limit, remove_stopwords=remove_stopwords)
        if state.topics.empty or state.qrels.empty:
            raise ValueError("Evaluation is only available for trec-covid source.")

        requested_qid = str(qid)
        effective_qid = requested_qid
        query_text = self._resolve_query_text(state, query="", qid=effective_qid, topic_field=topic_field)
        search_payload = self.search(
            source=source,
            limit=limit,
            remove_stopwords=remove_stopwords,
            query=query_text,
            top_k=top_k,
            node_weight=node_weight,
            edge_weight=edge_weight,
            qid=effective_qid,
            topic_field=topic_field,
        )

        qrels = state.qrels.copy()
        qrels["qid"] = qrels["qid"].astype(str)
        qrels["docno"] = qrels["docno"].astype(str)
        qrels = qrels[qrels["label"] > 0].copy()

        loaded_docnos = {str(doc.docno) for doc in state.retriever.prepared_documents}
        relevant_docnos_total = set(qrels[qrels["qid"] == effective_qid]["docno"].tolist())
        relevant_docnos = relevant_docnos_total & loaded_docnos

        auto_selected_qid = None
        auto_selection_reason = None
        if not relevant_docnos and auto_pick_qid:
            loaded_qrels = qrels[qrels["docno"].isin(loaded_docnos)]
            if not loaded_qrels.empty:
                counts = loaded_qrels.groupby("qid")["docno"].nunique().sort_values(ascending=False)
                best_qid = str(counts.index[0])
                if best_qid and best_qid != effective_qid:
                    auto_selected_qid = best_qid
                    auto_selection_reason = (
                        f"Requested qid {effective_qid} had 0 judged relevant docs in loaded subset; "
                        f"auto-switched to qid {best_qid}."
                    )
                    effective_qid = best_qid
                    query_text = self._resolve_query_text(state, query="", qid=effective_qid, topic_field=topic_field)
                    search_payload = self.search(
                        source=source,
                        limit=limit,
                        remove_stopwords=remove_stopwords,
                        query=query_text,
                        top_k=top_k,
                        node_weight=node_weight,
                        edge_weight=edge_weight,
                        qid=effective_qid,
                        topic_field=topic_field,
                    )
                    relevant_docnos_total = set(qrels[qrels["qid"] == effective_qid]["docno"].tolist())
                    relevant_docnos = relevant_docnos_total & loaded_docnos

        retrieved_docnos = [str(item["docno"]) for item in search_payload["results"]]
        if not relevant_docnos and relevant_docnos_total:
            raise ValueError(
                "No judged relevant documents for this qid are present in the loaded subset. "
                "Increase corpus limit or choose a qid with relevant_in_loaded_subset > 0."
            )
        precision, recall = precision_recall_at_k(retrieved_docnos, relevant_docnos, top_k)
        f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0

        return {
            "qid": effective_qid,
            "requested_qid": requested_qid,
            "auto_selected_qid": auto_selected_qid,
            "auto_selection_reason": auto_selection_reason,
            "query": query_text,
            "top_k": top_k,
            "precision_at_k": precision,
            "recall_at_k": recall,
            "f1_at_k": f1,
            "relevant_docs_in_loaded_subset": len(relevant_docnos),
            "relevant_docs_total_qrels": len(relevant_docnos_total),
            "retrieved_docnos": retrieved_docnos,
            "status": self.status(),
        }


def map_docs_for_preview(docs: list[RawDocument], max_items: int = 20) -> list[dict]:
    payload = []
    for doc in docs[:max_items]:
        payload.append(
            {
                "docno": doc.docno,
                "title": doc.title,
                "abstract_preview": (doc.abstract[:240] + "...") if len(doc.abstract) > 240 else doc.abstract,
            }
        )
    return payload
