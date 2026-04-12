from __future__ import annotations

import hashlib

import numpy as np
import pandas as pd
import streamlit as st

from graph_ir_app.engine import (
    GraphIRRetriever,
    get_demo_corpus,
    load_trec_covid,
    precision_recall_at_k,
)

st.set_page_config(page_title="Graph IR Web App", layout="wide")
st.title("Graph IR: Information Retrieval Using Dependency Graphs")
st.caption(
    "Built from your assignment flow: dependency graph features + semantic node matching + "
    "improved edge relation similarity."
)


class LightweightEmbeddingModel:
    """Fallback encoder used when sentence-transformers is unavailable."""

    def __init__(self, dim: int = 384) -> None:
        self.dim = dim

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


@st.cache_resource
def load_nlp_model():
    import spacy

    try:
        return spacy.load("en_core_web_sm")
    except OSError:
        try:
            from spacy.cli import download

            download("en_core_web_sm")
            return spacy.load("en_core_web_sm")
        except Exception:
            nlp = spacy.blank("en")
            if "sentencizer" not in nlp.pipe_names:
                nlp.add_pipe("sentencizer")
            return nlp


@st.cache_resource
def load_embedding_model():
    try:
        from sentence_transformers import SentenceTransformer

        return SentenceTransformer("all-MiniLM-L6-v2")
    except Exception:
        return LightweightEmbeddingModel()


def _init_state() -> None:
    defaults = {
        "documents": [],
        "topics": pd.DataFrame(),
        "qrels": pd.DataFrame(),
        "retriever": None,
        "retriever_key": None,
        "results": [],
        "query_text": "",
        "query_features": None,
        "selected_qid": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _corpus_signature(source_name: str, docs: list, remove_stopwords: bool) -> tuple:
    if not docs:
        return source_name, 0, remove_stopwords
    return source_name, len(docs), docs[0].docno, docs[-1].docno, remove_stopwords


_init_state()

with st.sidebar:
    st.header("Data")
    source = st.radio(
        "Corpus source",
        options=["Demo corpus (instant)", "TREC-COVID (chat-aligned)"],
        index=0,
    )
    subset_size = st.slider("TREC subset size", min_value=100, max_value=2000, value=1000, step=100)
    load_clicked = st.button("Load / Reload Corpus", type="primary")

    st.header("Scoring")
    node_weight = st.slider("Node weight", min_value=0.0, max_value=1.0, value=0.7, step=0.05)
    edge_weight = st.slider("Edge weight", min_value=0.0, max_value=1.0, value=0.3, step=0.05)
    remove_stopwords = st.checkbox("Remove stopwords", value=True)
    top_k = st.slider("Top K", min_value=3, max_value=20, value=5, step=1)

if load_clicked or not st.session_state["documents"]:
    try:
        with st.spinner("Loading corpus..."):
            if source == "TREC-COVID (chat-aligned)":
                docs, topics, qrels = load_trec_covid(limit=subset_size)
            else:
                docs = get_demo_corpus()
                topics = pd.DataFrame()
                qrels = pd.DataFrame()
        st.session_state["documents"] = docs
        st.session_state["topics"] = topics
        st.session_state["qrels"] = qrels
        st.session_state["retriever"] = None
        st.session_state["retriever_key"] = None
        st.success(f"Loaded {len(docs)} documents.")
    except Exception as exc:
        st.error(str(exc))
        st.stop()

docs = st.session_state["documents"]
topics = st.session_state["topics"]
qrels = st.session_state["qrels"]

col_a, col_b, col_c = st.columns(3)
col_a.metric("Documents", len(docs))
col_b.metric("Topics", 0 if topics.empty else len(topics))
col_c.metric("Qrels", 0 if qrels.empty else len(qrels))

query_mode = "Custom query"
selected_qid = None

if not topics.empty and "qid" in topics.columns:
    query_mode = st.radio("Query mode", options=["Custom query", "TREC topic"], horizontal=True)

if query_mode == "TREC topic":
    topic_fields = [field for field in ["description", "title", "narrative"] if field in topics.columns]
    if not topic_fields:
        st.warning("No topic text field found. Falling back to custom query.")
        query_mode = "Custom query"
    else:
        selected_qid = st.selectbox("Topic ID", options=topics["qid"].astype(str).tolist())
        selected_field = st.selectbox("Topic text field", options=topic_fields, index=0)
        selected_row = topics[topics["qid"].astype(str) == str(selected_qid)].iloc[0]
        default_query = str(selected_row.get(selected_field, "") or "")
        query_text = st.text_area("Query", value=default_query, height=120)
else:
    query_text = st.text_area("Query", value="how does covid spread", height=120)

run = st.button("Run Retrieval", type="primary")

if run:
    if not query_text.strip():
        st.error("Enter a query before running retrieval.")
        st.stop()

    retriever_key = _corpus_signature(source, docs, remove_stopwords)
    if st.session_state["retriever_key"] != retriever_key or st.session_state["retriever"] is None:
        try:
            with st.spinner("Loading NLP + embedding models and preparing graph features..."):
                nlp = load_nlp_model()
                embedder = load_embedding_model()
                if "parser" not in getattr(nlp, "pipe_names", []):
                    st.warning(
                        "spaCy dependency parser model is unavailable; using blank English tokenizer. "
                        "Relation-based scoring quality will be lower."
                    )
                if isinstance(embedder, LightweightEmbeddingModel):
                    st.warning(
                        "Using lightweight fallback embeddings (sentence-transformers unavailable). "
                        "Install sentence-transformers for best semantic quality."
                    )
                st.session_state["retriever"] = GraphIRRetriever(
                    documents=docs,
                    nlp=nlp,
                    embedding_model=embedder,
                    remove_stopwords=remove_stopwords,
                )
                st.session_state["retriever_key"] = retriever_key
        except Exception as exc:
            st.error(str(exc))
            st.stop()

    retriever: GraphIRRetriever = st.session_state["retriever"]
    with st.spinner("Scoring documents..."):
        results = retriever.retrieve_top_k(
            query=query_text,
            k=top_k,
            node_weight=node_weight,
            edge_weight=edge_weight,
        )
    st.session_state["results"] = results
    st.session_state["query_text"] = query_text
    st.session_state["query_features"] = retriever.extract_graph_features(query_text)
    st.session_state["selected_qid"] = str(selected_qid) if selected_qid is not None else None

results = st.session_state["results"]
if results:
    st.subheader("Top Results")
    results_df = pd.DataFrame(results)[
        ["docno", "score", "node_similarity", "edge_similarity", "title"]
    ].copy()
    results_df["score"] = results_df["score"].round(4)
    results_df["node_similarity"] = results_df["node_similarity"].round(4)
    results_df["edge_similarity"] = results_df["edge_similarity"].round(4)
    st.dataframe(results_df, use_container_width=True)

    st.subheader("Document Snippets")
    for idx, item in enumerate(results, start=1):
        with st.expander(f"#{idx} {item['docno']} | score={item['score']:.4f}"):
            st.write(f"**Title:** {item['title'] or '(no title)'}")
            st.write(item["abstract"][:1200] + ("..." if len(item["abstract"]) > 1200 else ""))

    retriever: GraphIRRetriever = st.session_state["retriever"]
    query_features = st.session_state["query_features"]
    top_doc_features = retriever.document_features(results[0]["docno"]) if retriever else None

    st.subheader("Graph Diagnostics")
    left, right = st.columns(2)
    left.metric("Query nodes", len(query_features.nodes) if query_features else 0)
    left.metric("Query relations", len(query_features.relations) if query_features else 0)
    if top_doc_features:
        right.metric("Top doc nodes", len(top_doc_features.nodes))
        right.metric("Top doc relations", len(top_doc_features.relations))
    else:
        right.metric("Top doc nodes", 0)
        right.metric("Top doc relations", 0)

    if query_features and top_doc_features:
        common_relations = sorted(query_features.relations & top_doc_features.relations)
        st.write("Common dependency relations (query vs top doc):")
        if common_relations:
            st.code(", ".join(common_relations), language="text")
        else:
            st.code("(none)", language="text")

    chosen_qid = st.session_state["selected_qid"]
    if chosen_qid and not qrels.empty and {"qid", "docno", "label"}.issubset(set(qrels.columns)):
        relevant_docnos = set(
            qrels[(qrels["qid"].astype(str) == chosen_qid) & (qrels["label"] > 0)]["docno"].astype(str).tolist()
        )
        retrieved_docnos = [str(item["docno"]) for item in results]
        precision, recall = precision_recall_at_k(retrieved_docnos, relevant_docnos, top_k)
        f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0

        st.subheader("Evaluation (for selected TREC topic)")
        e1, e2, e3 = st.columns(3)
        e1.metric(f"Precision@{top_k}", f"{precision:.4f}")
        e2.metric(f"Recall@{top_k}", f"{recall:.4f}")
        e3.metric(f"F1@{top_k}", f"{f1:.4f}")
        st.caption(
            "Metrics are computed on the loaded subset. If your subset is small, "
            "scores may be low even for a good model."
        )

st.subheader("Viva Statement")
st.info(
    "My system retrieves documents by comparing the dependency graph of the query with the "
    "dependency graphs of documents using semantic similarity and graph-based matching."
)
