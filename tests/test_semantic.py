import pytest
from goreecloud_ai.knowledge import KnowledgeStore
from goreecloud_ai.semantic import SemanticIndex, clean_vector, chunk_text


def test_chunking_is_bounded_and_deterministic():
    text = "a" * 1500
    chunks = chunk_text(text)
    assert len(chunks) == 3
    assert chunks[0][-80:] == chunks[1][:80]
    assert sum(len(chunk) for chunk in chunks) >= len(text)


def test_vector_validation():
    assert clean_vector([3, 4]) == [3.0, 4.0]
    with pytest.raises(ValueError):
        clean_vector([float("nan"), 1])
    with pytest.raises(ValueError):
        clean_vector([0, 0])


def test_semantic_index_and_delete_cascade(tmp_path):
    path = str(tmp_path / "semantic.sqlite")
    knowledge = KnowledgeStore(path)
    index = SemanticIndex(path)
    cats = knowledge.add("Cats", "Domestic cats have whiskers.")
    dogs = knowledge.add("Dogs", "Dogs are social companions.")
    assert index.save(cats["id"], "embeddinggemma", ["cats"], [[1.0, 0.0]]) == 1
    index.save(dogs["id"], "embeddinggemma", ["dogs"], [[0.0, 1.0]])
    assert index.search([1.0, 0.0], "embeddinggemma")[0]["id"] == cats["id"]
    assert index.search([1.0, 0.0], "other") == []
    assert knowledge.delete(cats["id"])
    assert index.search([1.0, 0.0], "embeddinggemma") == []


def test_invalid_vectors_do_not_overwrite_existing_index(tmp_path):
    path = str(tmp_path / "vectors.sqlite")
    knowledge = KnowledgeStore(path)
    index = SemanticIndex(path)
    doc = knowledge.add("Saved", "Retain original index")
    index.save(doc["id"], "embeddinggemma", ["good"], [[1.0, 0.0]])
    with pytest.raises(ValueError):
        index.save(doc["id"], "embeddinggemma", ["bad"], [[float("inf"), 0.0]])
    assert index.search([1.0, 0.0], "embeddinggemma")[0]["excerpt"] == "good"
