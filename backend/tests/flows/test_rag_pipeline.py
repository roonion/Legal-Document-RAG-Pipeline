"""Integration tests for compiled LangGraph."""


def test_compile_graph() -> None:
    from app.rag.graph import compile_rag_graph

    g = compile_rag_graph()
    assert g is not None
