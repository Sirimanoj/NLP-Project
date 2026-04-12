from __future__ import annotations

from agent.tools import ToolRegistry

_RAG_REGISTRY = ToolRegistry()


def search_rag(query: str) -> str:
    result = _RAG_REGISTRY.rag_search(query)
    return str(result.get("answer", "No safe documents found."))

