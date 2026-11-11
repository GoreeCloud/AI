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
