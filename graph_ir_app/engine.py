from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity


@dataclass(frozen=True)
class RawDocument:
    docno: str
    title: str
    abstract: str


@dataclass(frozen=True)
class GraphFeatures:
    nodes: frozenset[str]
    edges: frozenset[tuple[str, str, str]]
    relations: frozenset[str]


@dataclass(frozen=True)
class PreparedDocument:
    docno: str
    title: str
    abstract: str
    features: GraphFeatures


class GraphIRRetriever:
    def __init__(
        self,
        documents: list[RawDocument],
        nlp,
        embedding_model,
        remove_stopwords: bool = True,
    ) -> None:
        self.documents = documents
        self.nlp = nlp
        self.embedding_model = embedding_model
        self.remove_stopwords = remove_stopwords
        self._embedding_cache: dict[str, np.ndarray] = {}
        self.prepared_documents = [self._prepare_document(doc) for doc in self.documents]
        self._doc_index = {doc.docno: doc for doc in self.prepared_documents}

    def _normalize(self, token) -> str:
        lemma = (token.lemma_ or token.text).strip().lower()
        return lemma if lemma else token.text.strip().lower()

    def extract_graph_features(self, text: str) -> GraphFeatures:
        if not text or not text.strip():
            return GraphFeatures(frozenset(), frozenset(), frozenset())

        doc = self.nlp(text)
        nodes: set[str] = set()
        edges: set[tuple[str, str, str]] = set()

        for token in doc:
            if token.is_space or token.is_punct:
                continue
            if self.remove_stopwords and token.is_stop:
                continue

            child = self._normalize(token)
            head = self._normalize(token.head)
            if not child or not head:
                continue

            nodes.add(child)
            nodes.add(head)
            edges.add((child, head, token.dep_))

        relations = {edge[2] for edge in edges}
        return GraphFeatures(frozenset(nodes), frozenset(edges), frozenset(relations))

    def _prepare_document(self, doc: RawDocument) -> PreparedDocument:
        return PreparedDocument(
            docno=doc.docno,
            title=doc.title,
            abstract=doc.abstract,
            features=self.extract_graph_features(doc.abstract),
        )

    def _encode_node_set(self, nodes: Iterable[str]) -> np.ndarray:
        ordered_nodes = sorted(set(nodes))
        if not ordered_nodes:
            return np.empty((0, 384), dtype=np.float32)

        missing = [node for node in ordered_nodes if node not in self._embedding_cache]
        if missing:
            encoded = self.embedding_model.encode(
                missing,
                normalize_embeddings=True,
                show_progress_bar=False,
            )
            for node, vector in zip(missing, encoded):
                self._embedding_cache[node] = np.asarray(vector, dtype=np.float32)

        return np.vstack([self._embedding_cache[node] for node in ordered_nodes])

    def semantic_node_similarity(self, nodes1: frozenset[str], nodes2: frozenset[str]) -> float:
        if not nodes1 or not nodes2:
            return 0.0

        emb1 = self._encode_node_set(nodes1)
        emb2 = self._encode_node_set(nodes2)
        if emb1.size == 0 or emb2.size == 0:
            return 0.0

        sim_matrix = cosine_similarity(emb1, emb2)
        max_sims = sim_matrix.max(axis=1)
        return float(max_sims.mean())

    @staticmethod
    def edge_similarity_improved(rels1: frozenset[str], rels2: frozenset[str]) -> float:
        if not rels1 or not rels2:
            return 0.0
        return float(len(rels1 & rels2) / len(rels1 | rels2))

    def score_pair(
        self,
        query_features: GraphFeatures,
        doc_features: GraphFeatures,
        node_weight: float = 0.7,
        edge_weight: float = 0.3,
    ) -> tuple[float, float, float]:
        total_weight = node_weight + edge_weight
        if total_weight <= 0:
            node_weight, edge_weight = 0.7, 0.3
            total_weight = 1.0

        node_w = node_weight / total_weight
        edge_w = edge_weight / total_weight

        node_sim = self.semantic_node_similarity(query_features.nodes, doc_features.nodes)
        edge_sim = self.edge_similarity_improved(query_features.relations, doc_features.relations)
        final_score = (node_w * node_sim) + (edge_w * edge_sim)
        return final_score, node_sim, edge_sim

    def retrieve_top_k(
        self,
        query: str,
        k: int = 5,
        node_weight: float = 0.7,
        edge_weight: float = 0.3,
    ) -> list[dict]:
        query_features = self.extract_graph_features(query)
        scored: list[dict] = []

        for doc in self.prepared_documents:
            score, node_sim, edge_sim = self.score_pair(
                query_features=query_features,
                doc_features=doc.features,
                node_weight=node_weight,
                edge_weight=edge_weight,
            )
            scored.append(
                {
                    "docno": doc.docno,
                    "title": doc.title,
                    "abstract": doc.abstract,
                    "score": score,
                    "node_similarity": node_sim,
                    "edge_similarity": edge_sim,
                }
            )

        scored.sort(key=lambda item: item["score"], reverse=True)
        return scored[:k]

    def document_features(self, docno: str) -> GraphFeatures | None:
        doc = self._doc_index.get(docno)
        return doc.features if doc else None


def _read_field(record, key: str) -> str:
    if isinstance(record, dict):
        return str(record.get(key, "") or "")
    return str(getattr(record, key, "") or "")


def load_trec_covid(limit: int = 1000) -> tuple[list[RawDocument], pd.DataFrame, pd.DataFrame]:
    try:
        import pyterrier as pt

        if not pt.started():
            pt.init()

        dataset = pt.get_dataset("irds:cord19/trec-covid")
        topics = dataset.get_topics()
        qrels = dataset.get_qrels()

        docs: list[RawDocument] = []
        for _, record in zip(range(limit), dataset.get_corpus_iter()):
            abstract = _read_field(record, "abstract").strip()
            if not abstract:
                continue
            docs.append(
                RawDocument(
                    docno=_read_field(record, "docno").strip(),
                    title=_read_field(record, "title").strip(),
                    abstract=abstract,
                )
            )

        topics = topics.rename(columns={"query_id": "qid"}).copy()
        qrels = qrels.rename(columns={"query_id": "qid", "doc_id": "docno", "relevance": "label"}).copy()
        if "qid" in topics.columns:
            topics["qid"] = topics["qid"].astype(str)
        if "qid" in qrels.columns:
            qrels["qid"] = qrels["qid"].astype(str)
        if "docno" in qrels.columns:
            qrels["docno"] = qrels["docno"].astype(str)

        return docs, topics, qrels
    except Exception as pt_exc:
        try:
            import ir_datasets
        except ImportError as ir_exc:
            raise RuntimeError(
                "Failed to load TREC-COVID. Install either python-terrier or ir-datasets."
            ) from ir_exc

        dataset = ir_datasets.load("cord19/trec-covid")

        docs: list[RawDocument] = []
        for _, record in zip(range(limit), dataset.docs_iter()):
            docno = _read_field(record, "doc_id") or _read_field(record, "docno")
            title = _read_field(record, "title")
            abstract = _read_field(record, "abstract").strip()
            if not abstract:
                continue
            docs.append(RawDocument(docno=docno.strip(), title=title.strip(), abstract=abstract))

        topics_records = []
        for query in dataset.queries_iter():
            if hasattr(query, "_asdict"):
                topics_records.append(query._asdict())
            else:
                topics_records.append(dict(query))
        topics = pd.DataFrame(topics_records).rename(columns={"query_id": "qid"})

        qrels_records = []
        for rel in dataset.qrels_iter():
            if hasattr(rel, "_asdict"):
                qrels_records.append(rel._asdict())
            else:
                qrels_records.append(dict(rel))
        qrels = pd.DataFrame(qrels_records).rename(
            columns={"query_id": "qid", "doc_id": "docno", "relevance": "label"}
        )

        if "qid" in topics.columns:
            topics["qid"] = topics["qid"].astype(str)
        if "qid" in qrels.columns:
            qrels["qid"] = qrels["qid"].astype(str)
        if "docno" in qrels.columns:
            qrels["docno"] = qrels["docno"].astype(str)

        if docs:
            return docs, topics, qrels

        raise RuntimeError(
            "Failed to load TREC-COVID via python-terrier and fallback ir-datasets."
        ) from pt_exc


def get_demo_corpus() -> list[RawDocument]:
    return [
        RawDocument(
            docno="demo-1",
            title="Airborne spread of respiratory viruses",
            abstract=(
                "Respiratory viruses can spread through aerosols in enclosed spaces. "
                "Transmission risk increases with poor ventilation and crowded rooms."
            ),
        ),
        RawDocument(
            docno="demo-2",
            title="Surface transmission and hygiene behavior",
            abstract=(
                "Fomite transmission is possible when contaminated surfaces are touched. "
                "Regular hand hygiene reduces infection probability."
            ),
        ),
        RawDocument(
            docno="demo-3",
            title="Masking and source control",
            abstract=(
                "Face masks reduce emission of infectious particles from symptomatic and "
                "asymptomatic individuals, lowering community transmission."
            ),
        ),
        RawDocument(
            docno="demo-4",
            title="Vaccination and severe disease reduction",
            abstract=(
                "Vaccination lowers hospitalization and mortality by priming immune memory. "
                "Breakthrough infections still occur but are generally less severe."
            ),
        ),
        RawDocument(
            docno="demo-5",
            title="Environmental controls in classrooms",
            abstract=(
                "HEPA filtration and increased outdoor airflow reduce viral concentration in "
                "classroom air and improve outbreak control."
            ),
        ),
    ]


def precision_recall_at_k(
    retrieved_docnos: list[str],
    relevant_docnos: set[str],
    k: int,
) -> tuple[float, float]:
    if k <= 0:
        return 0.0, 0.0

    top_k = retrieved_docnos[:k]
    if not top_k:
        return 0.0, 0.0

    hits = sum(1 for docno in top_k if docno in relevant_docnos)
    precision = hits / k
    recall = 0.0 if not relevant_docnos else hits / len(relevant_docnos)
    return precision, recall
