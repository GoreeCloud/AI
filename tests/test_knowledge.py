from goreecloud_ai.knowledge import KnowledgeStore


def test_local_knowledge_search_and_delete(tmp_path):
    store = KnowledgeStore(str(tmp_path / "ai.sqlite"))
    doc = store.add("Python setup", "Use a virtual environment for Python application setup.")
    other = store.add("Gardening", "Plant basil in spring.")
    results = store.search("How to setup Python?")
    assert results
    assert results[0]["id"] == doc["id"]
    assert all(r["id"] != other["id"] for r in results)
    assert "Python" in results[0]["excerpt"]
    assert store.delete(doc["id"])
    assert store.search("Python setup") == []


def test_no_knowledge_match_for_stopwords(tmp_path):
    store = KnowledgeStore(str(tmp_path / "ai.sqlite"))
    store.add("Test", "Sample information.")
    assert store.search("what is this about") == []
