from fastapi.testclient import TestClient
from goreecloud_ai.app import create_app
from goreecloud_ai.settings import Settings
from goreecloud_ai.ollama import OllamaError


class FakeOllama:
    def __init__(self):
        self.calls = []

    async def models(self):
        return ["gemma3:4b", "qwen2.5-coder:7b"]

    async def stream_chat(self, model, messages):
        self.calls.append((model, messages))
        for part in ("hello", " world"):
            yield part

    async def chat(self, model, messages):
        self.calls.append((model, messages))
        return "Response from " + model


def client(tmp_path, token=None):
    backend = FakeOllama()
    app = create_app(Settings(database_path=str(tmp_path / "ai.sqlite"), api_token=token), backend)
    return TestClient(app), backend


def test_chat_round_trip(tmp_path):
    c, backend = client(tmp_path)
    chat = c.post("/api/chats", json={"title": "Test"}).json()
    r = c.post("/api/chats/" + chat["id"] + "/messages", json={"content": "Write Python code"})
    assert r.status_code == 200
    assert r.json()["message"]["model"] == "qwen2.5-coder:7b"
    assert backend.calls[0][1][-1] == {"role": "user", "content": "Write Python code"}
    loaded = c.get("/api/chats/" + chat["id"]).json()
    assert [m["role"] for m in loaded["messages"]] == ["user", "assistant"]
    assert c.delete("/api/chats/" + chat["id"]).json() == {"deleted": True}
    assert c.get("/api/chats/" + chat["id"]).status_code == 404


def test_authentication(tmp_path):
    c, _ = client(tmp_path, token="test-token-1234567890")
    assert c.get("/api/chats").status_code == 401
    assert c.get("/api/chats", headers={"X-API-Key": "test-token-1234567890"}).status_code == 200


def test_invalid_model_fails_closed(tmp_path):
    c, backend = client(tmp_path)
    chat = c.post("/api/chats", json={}).json()
    response = c.post("/api/chats/" + chat["id"] + "/messages", json={"content": "hi", "model": "uninstalled:latest"})
    assert response.status_code == 422
    assert backend.calls == []


def test_invalid_chat(tmp_path):
    c, _ = client(tmp_path)
    assert c.post("/api/chats/unknown/messages", json={"content": "hello"}).status_code == 404


def test_input_limit(tmp_path):
    c, _ = client(tmp_path)
    chat = c.post("/api/chats", json={}).json()
    r = c.post("/api/chats/" + chat["id"] + "/messages", json={"content": "a" * 12001})
    assert r.status_code == 422


def test_health(tmp_path):
    c, _ = client(tmp_path)
    assert c.get("/api/health").json()["ollama"] == "online"



def test_stream_and_persistence(tmp_path):
    c, backend = client(tmp_path)
    chat = c.post("/api/chats", json={}).json()
    r = c.post("/api/chats/" + chat["id"] + "/stream", json={"content": "Write Python code"})
    assert r.status_code == 200
    assert "event: chunk" in r.text
    assert "event: done" in r.text
    assert c.get("/api/chats/" + chat["id"]).json()["messages"][-1]["content"] == "hello world"
    assert backend.calls[-1][0] == "qwen2.5-coder:7b"


def test_browser_assets_are_served(tmp_path):
    c, _ = client(tmp_path)
    assert "GoreeCloud AI" in c.get("/").text
    assert "streamAnswer" in c.get("/assets/app.js").text


def test_first_message_updates_new_conversation_title(tmp_path):
    c, _ = client(tmp_path)
    chat = c.post("/api/chats", json={}).json()
    c.post("/api/chats/" + chat["id"] + "/messages", json={"content": "Explain Smart Model"})
    assert c.get("/api/chats/" + chat["id"]).json()["title"] == "Explain Smart Model"


def test_knowledge_api_and_opt_in_context(tmp_path):
    c, backend = client(tmp_path)
    document = c.post('/api/knowledge/documents', json={'title':'Workspace guide','content':'Workspace instructions describe safe project setup.'})
    assert document.status_code == 201
    item = document.json()
    assert c.get('/api/knowledge/search?q=workspace').json()[0]['id'] == item['id']
    chat = c.post('/api/chats', json={}).json()
    response = c.post('/api/chats/' + chat['id'] + '/messages', json={'content':'Explain workspace setup','use_knowledge':True})
    assert response.status_code == 200
    assert response.json()['sources'][0]['id'] == item['id']
    assert backend.calls[-1][1][0]['role'] == 'system'
    assert c.delete('/api/knowledge/documents/' + item['id']).status_code == 200
    assert c.get('/api/knowledge/search?q=workspace').json() == []


def test_knowledge_not_shared_without_opt_in(tmp_path):
    c, backend = client(tmp_path)
    c.post('/api/knowledge/documents', json={'title':'Secret context','content':'Sensitive content stays isolated by default.'})
    chat = c.post('/api/chats', json={}).json()
    c.post('/api/chats/' + chat['id'] + '/messages', json={'content':'Tell me about sensitive content'})
    assert all(m['role'] != 'system' for m in backend.calls[-1][1])


def test_knowledge_rejects_oversized_payload(tmp_path):
    c, _ = client(tmp_path)
    assert c.post('/api/knowledge/documents', json={'title':'Oversize','content':'x' * 50001}).status_code == 422



def test_conversation_search_and_portable_json_export(tmp_path):
    c, _ = client(tmp_path)
    chat = c.post("/api/chats", json={"title": "Research notes"}).json()
    c.post("/api/chats/" + chat["id"] + "/messages", json={"content": "Explaining Qwen models"})
    found = c.post("/api/chats/search", json={"query": "Qwen"}).json()
    assert found and found[0]["id"] == chat["id"]
    assert c.post("/api/chats/search", json={"query": "not-present"}).json() == []
    exported = c.get("/api/chats/" + chat["id"] + "/export")
    assert exported.status_code == 200
    assert exported.headers["cache-control"] == "no-store"
    assert exported.json()["format"] == "goreecloud-ai-chat"
    assert exported.json()["conversation"]["messages"][-1]["role"] == "assistant"


def test_smart_route_preview_does_not_infer_or_save(tmp_path):
    c, backend = client(tmp_path)
    result = c.post("/api/smart/route", json={"content": "Debug this Python code"})
    assert result.status_code == 200
    assert result.json()["model"] == "qwen2.5-coder:7b"
    assert backend.calls == []
    assert c.get("/api/chats").json() == []


def test_search_and_export_require_auth(tmp_path):
    c, _ = client(tmp_path, token="test-token-1234567890")
    assert c.post("/api/chats/search", json={"query": "abc"}).status_code == 401
    assert c.get("/api/chats/random/export").status_code == 401
    assert c.post("/api/smart/route", json={"content": "abc"}).status_code == 401



def test_knowledge_management_api_end_to_end(tmp_path):
    c, _ = client(tmp_path)
    document = c.post("/api/knowledge/documents", json={
        "title": "Project onboarding", "content": "This is a project onboarding guide."
    }).json()
    assert any(d["id"] == document["id"] for d in c.get("/api/knowledge/documents").json())
    assert c.delete("/api/knowledge/documents/" + document["id"]).status_code == 200
    assert c.get("/api/knowledge/documents").json() == []
    assert c.delete("/api/knowledge/documents/" + document["id"]).status_code == 404


def test_stream_error_does_not_persist_partial_response(tmp_path):
    class BrokenStream(FakeOllama):
        async def stream_chat(self, model, messages):
            yield "partial"
            raise OllamaError("upstream failed")
    backend = BrokenStream()
    app = create_app(Settings(database_path=str(tmp_path / "broken.sqlite")), backend)
    c = TestClient(app)
    chat = c.post("/api/chats", json={}).json()
    response = c.post("/api/chats/" + chat["id"] + "/stream", json={"content": "Hello"})
    assert response.status_code == 200
    assert "event: chunk" in response.text
    assert "event: error" in response.text
    assert c.get("/api/chats/" + chat["id"]).json()["messages"] == []


def test_controls_are_in_browser(tmp_path):
    c, _ = client(tmp_path)
    html = c.get("/").text
    assert 'id="knowledge-dialog"' in html
    assert 'id="delete-chat"' in html
    assert 'id="stop"' in html
    script = c.get("/assets/app.js").text
    assert "function saveKnowledge" in script
    assert "new AbortController()" in script



def test_whitespace_search_rejected(tmp_path):
    c, _ = client(tmp_path)
    c.post("/api/chats", json={"title": "private"})
    assert c.post("/api/chats/search", json={"query": "   "}).status_code == 422


def test_stale_chat_write_is_rejected_atomically(tmp_path):
    import pytest
    from goreecloud_ai.store import Store, ConversationConflict
    store = Store(str(tmp_path / "concurrent.sqlite"))
    chat = store.create_chat("New conversation")
    store.add_exchange(chat["id"], "first", "answer", "gemma3:4b", expected_count=0)
    with pytest.raises(ConversationConflict):
        store.add_exchange(chat["id"], "stale", "second", "gemma3:4b", expected_count=0)
    saved = store.get_chat(chat["id"])
    assert len(saved["messages"]) == 2
    assert saved["title"] == "first"


def test_deleted_chat_cannot_be_recreated_by_late_result(tmp_path):
    import pytest
    from goreecloud_ai.store import Store, ConversationConflict
    store = Store(str(tmp_path / "deleted.sqlite"))
    chat = store.create_chat("New conversation")
    assert store.delete_chat(chat["id"])
    with pytest.raises(ConversationConflict):
        store.add_exchange(chat["id"], "late", "should not save", "gemma3:4b", expected_count=0)
    assert store.get_chat(chat["id"]) is None


def test_nonstreaming_reply_limit(tmp_path):
    class HugeReply(FakeOllama):
        async def chat(self, model, messages):
            return "x" * 11
    c = TestClient(create_app(Settings(database_path=str(tmp_path / "limit.sqlite"), max_reply_chars=10), HugeReply()))
    chat = c.post("/api/chats", json={}).json()
    assert c.post("/api/chats/" + chat["id"] + "/messages", json={"content": "hello"}).status_code == 502
    assert c.get("/api/chats/" + chat["id"]).json()["messages"] == []


def test_streaming_reply_limit(tmp_path):
    class HugeStream(FakeOllama):
        async def stream_chat(self, model, messages):
            yield "123456789"
            yield "too long"
    c = TestClient(create_app(Settings(database_path=str(tmp_path / "stream-limit.sqlite"), max_reply_chars=10), HugeStream()))
    chat = c.post("/api/chats", json={}).json()
    result = c.post("/api/chats/" + chat["id"] + "/stream", json={"content": "hello"})
    assert "event: error" in result.text
    assert "event: done" not in result.text
    assert c.get("/api/chats/" + chat["id"]).json()["messages"] == []



def test_json_export_import_round_trip_uses_new_ids(tmp_path):
    c, _ = client(tmp_path)
    chat = c.post("/api/chats", json={"title": "Original research"}).json()
    c.post("/api/chats/" + chat["id"] + "/messages", json={"content": "Explain Qwen"})
    data = c.get("/api/chats/" + chat["id"] + "/export").json()
    result = c.post("/api/chats/import", json=data)
    assert result.status_code == 201
    imported = result.json()
    assert imported["id"] != chat["id"]
    loaded = c.get("/api/chats/" + imported["id"]).json()
    assert loaded["title"] == "Original research"
    assert [item["content"] for item in loaded["messages"]] == [
        item["content"] for item in data["conversation"]["messages"]
    ]
    assert loaded["messages"][0]["id"] != data["conversation"]["messages"][0]["id"]
    assert c.get("/api/chats/" + chat["id"]).status_code == 200


def test_rejects_malformed_import_without_partial_mutation(tmp_path):
    c, _ = client(tmp_path)
    envelope = {
        "format": "goreecloud-ai-chat", "version": 1,
        "conversation": {"title": "Injected", "messages": [
            {"role": "assistant", "content": "Wrong first role"}
        ]},
    }
    assert c.post("/api/chats/import", json=envelope).status_code == 422
    assert c.get("/api/chats").json() == []
    envelope["conversation"]["messages"] = [
        {"role": "user", "content": "ok"},
        {"role": "assistant", "content": "ok"},
        {"role": "assistant", "content": "extra"},
        {"role": "user", "content": "invalid"},
    ]
    assert c.post("/api/chats/import", json=envelope).status_code == 422
    assert c.get("/api/chats").json() == []


def test_import_version_and_size_limits(tmp_path):
    c, _ = client(tmp_path)
    valid = {"format": "goreecloud-ai-chat", "version": 999,
             "conversation": {"title": "old", "messages": []}}
    assert c.post("/api/chats/import", json=valid).status_code == 422
    assert c.post("/api/chats/import", data="x" * 1500001,
                  headers={"Content-Type": "application/json"}).status_code == 413
    assert c.get("/api/chats").json() == []


def test_import_is_token_protected(tmp_path):
    c, _ = client(tmp_path, token="test-token-1234567890")
    payload = {"format": "goreecloud-ai-chat", "version": 1,
               "conversation": {"title": "safe", "messages": []}}
    assert c.post("/api/chats/import", json=payload).status_code == 401
    assert c.post("/api/chats/import", json=payload,
                  headers={"X-API-Key": "test-token-1234567890"}).status_code == 201


def test_import_controls_visible(tmp_path):
    c, _ = client(tmp_path)
    assert 'id="import-chat"' in c.get("/").text
    assert 'id="import-chat-file"' in c.get("/").text
    assert "async function importChat" in c.get("/assets/app.js").text



def test_knowledge_private_search_post(tmp_path):
    c, _ = client(tmp_path)
    document = c.post("/api/knowledge/documents", json={
        "title": "Notes", "content": "Ollama Qwen inference runs locally."
    }).json()
    result = c.post("/api/knowledge/search", json={"query": "qwen"})
    assert result.status_code == 200
    assert result.json()[0]["id"] == document["id"]
    assert c.post("/api/knowledge/search", json={"query": "  "}).status_code == 422
    assert c.post("/api/knowledge/search", json={"query": "x"*501}).status_code == 422


def test_knowledge_private_search_requires_token(tmp_path):
    c, _ = client(tmp_path, token="test-token-1234567890")
    assert c.post("/api/knowledge/search", json={"query": "secret"}).status_code == 401


def test_knowledge_explicit_file_controls_exist(tmp_path):
    c, _ = client(tmp_path)
    assert 'id="knowledge-file"' in c.get("/").text
    assert 'id="knowledge-search-form"' in c.get("/").text
    script = c.get("/assets/app.js").text
    assert "async function importKnowledgeFile" in script
    assert "await file.text()" in script
    assert '"/api/knowledge/search"' in script



def test_explicit_local_semantic_index_search_and_chat(tmp_path):
    class FakeEmbeddingOllama(FakeOllama):
        async def models(self):
            return await super().models() + ["embeddinggemma"]

        async def embed(self, model, inputs):
            assert model == "embeddinggemma"
            vectors = []
            for text in inputs:
                lower = text.lower()
                if "cats" in lower or "feline" in lower:
                    vectors.append([1.0, 0.0])
                elif "dogs" in lower:
                    vectors.append([0.0, 1.0])
                else:
                    vectors.append([0.4, 0.4])
            return vectors

    backend = FakeEmbeddingOllama()
    c = TestClient(create_app(Settings(database_path=str(tmp_path / "rag.sqlite")), backend))
    first = c.post("/api/knowledge/documents", json={"title":"Cats","content":"Cats purr and sleep."}).json()
    second = c.post("/api/knowledge/documents", json={"title":"Dogs","content":"Dogs are playful."}).json()
    assert c.post("/api/knowledge/semantic/index", json={"document_id":first["id"],"model":"embeddinggemma"}).json()["chunks"] == 1
    assert c.post("/api/knowledge/semantic/index", json={"document_id":second["id"],"model":"embeddinggemma"}).status_code == 200
    result = c.post("/api/knowledge/semantic/search", json={"model":"embeddinggemma","query":"feline pets"})
    assert result.status_code == 200
    assert result.json()[0]["id"] == first["id"]
    chat = c.post("/api/chats", json={}).json()
    response = c.post("/api/chats/" + chat["id"] + "/messages", json={
        "content":"Tell me about feline pets", "use_knowledge":True,
        "knowledge_mode":"semantic", "embedding_model":"embeddinggemma",
    })
    assert response.status_code == 200
    assert response.json()["sources"][0]["id"] == first["id"]
    assert response.json()["sources"][0]["retrieval"] == "semantic"
    assert "[Source 1]" in backend.calls[-1][1][0]["content"]


def test_semantic_requires_installed_embedding_model(tmp_path):
    c, _ = client(tmp_path)
    doc = c.post("/api/knowledge/documents", json={"title":"Example","content":"Local text"}).json()
    assert c.post("/api/knowledge/semantic/index", json={
        "document_id":doc["id"],"model":"nonexistent:latest"
    }).status_code == 422
    assert c.post("/api/knowledge/semantic/search", json={
        "model":"nonexistent:latest","query":"local"
    }).status_code == 422


def test_semantic_index_requires_token(tmp_path):
    c, _ = client(tmp_path, token="test-token-1234567890")
    assert c.post("/api/knowledge/semantic/search", json={
        "model":"embeddinggemma","query":"abc"
    }).status_code == 401



def test_semantic_embedding_failure_is_bounded_for_both_chat_paths(tmp_path):
    class BrokenEmbedding(FakeOllama):
        async def models(self):
            return await super().models() + ["embeddinggemma"]

        async def embed(self, model, inputs):
            raise OllamaError("Embedding backend unavailable")

    from goreecloud_ai.knowledge import KnowledgeStore
    from goreecloud_ai.semantic import SemanticIndex
    path = str(tmp_path / "broken-emb.sqlite")
    c = TestClient(create_app(Settings(database_path=path), BrokenEmbedding()))
    # Seed a valid index so the request reaches the simulated upstream failure.
    source = KnowledgeStore(path).add("Reference", "Project architecture reference")
    SemanticIndex(path).save(source["id"], "embeddinggemma", ["Project architecture"], [[1.0, 0.0]])
    chat = c.post("/api/chats", json={}).json()
    payload = {
        "content": "Explain project architecture",
        "use_knowledge": True, "knowledge_mode": "semantic",
        "embedding_model": "embeddinggemma",
    }
    assert c.post("/api/chats/" + chat["id"] + "/messages", json=payload).status_code == 502
    assert c.post("/api/chats/" + chat["id"] + "/stream", json=payload).status_code == 502
    assert c.get("/api/chats/" + chat["id"]).json()["messages"] == []
