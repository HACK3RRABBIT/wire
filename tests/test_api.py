from fastapi.testclient import TestClient

from app import api


class FakeIndex:
    def search(self, query, opts):
        assert isinstance(query, str)
        return {
            "hits": [{"id": "1_1", "text": "hello world", "channel_username": "foo"}],
            "facetDistribution": {"channel_username": {"foo": 1}},
        }


def _client(monkeypatch):
    monkeypatch.setattr(api, "get_search_index", lambda: FakeIndex())
    monkeypatch.setattr(api, "list_channels", lambda db_path: [])
    return TestClient(api.app)


def test_search_returns_hits_and_channels(monkeypatch):
    client = _client(monkeypatch)
    resp = client.get("/search", params={"q": "hello"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["hits"][0]["text"] == "hello world"
    assert body["channels"] == {"foo": 1}


def test_search_with_hashtag_filter(monkeypatch):
    client = _client(monkeypatch)
    resp = client.get("/search", params={"hashtag": "news"})
    assert resp.status_code == 200


def test_user_channels(monkeypatch):
    client = _client(monkeypatch)
    resp = client.get("/users/12345/channels")
    assert resp.status_code == 200
    assert resp.json()["channels"] == {"foo": 1}


def test_channels_list_empty(monkeypatch):
    client = _client(monkeypatch)
    resp = client.get("/channels")
    assert resp.status_code == 200
    assert resp.json() == []


def test_analyze_without_api_key_returns_503(monkeypatch):
    client = _client(monkeypatch)
    object.__setattr__(api.settings, "ai_api_key", "")
    resp = client.get("/analyze", params={"q": "hello"})
    assert resp.status_code == 503


def test_analyze_with_no_hits_skips_ai_call(monkeypatch):
    class EmptyIndex:
        def search(self, query, opts):
            return {"hits": []}

    monkeypatch.setattr(api, "get_search_index", lambda: EmptyIndex())
    object.__setattr__(api.settings, "ai_api_key", "test-key")
    client = TestClient(api.app)
    resp = client.get("/analyze", params={"q": "nothing"})
    assert resp.status_code == 200
    assert resp.json()["hit_count"] == 0


def test_analyze_summarizes_hits(monkeypatch):
    client = _client(monkeypatch)
    object.__setattr__(api.settings, "ai_api_key", "test-key")
    monkeypatch.setattr(api, "summarize_hits", lambda settings, q, hits: "a summary")
    resp = client.get("/analyze", params={"q": "hello"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["summary"] == "a summary"
    assert body["hit_count"] == 1


def test_ask_without_api_key_returns_503(monkeypatch):
    client = _client(monkeypatch)
    object.__setattr__(api.settings, "ai_api_key", "")
    resp = client.get("/ask", params={"q": "who talks about crypto"})
    assert resp.status_code == 503


def test_ask_runs_agentic_search(monkeypatch):
    client = _client(monkeypatch)
    object.__setattr__(api.settings, "ai_api_key", "test-key")
    fake_result = {"answer": "crypto is discussed in @foo", "searches": [{"query": "crypto", "hashtag": None, "hit_count": 1}]}
    monkeypatch.setattr(api, "agentic_search", lambda settings, q, search_fn: fake_result)
    resp = client.get("/ask", params={"q": "who talks about crypto"})
    assert resp.status_code == 200
    assert resp.json() == fake_result


def test_get_settings_masks_api_key(monkeypatch):
    client = _client(monkeypatch)
    object.__setattr__(api.settings, "ai_api_key", "test-key")
    resp = client.get("/settings")
    assert resp.status_code == 200
    body = resp.json()
    assert body["ai_api_key_set"] is True
    assert "ai_api_key" not in body


def test_post_settings_saves_and_applies_immediately(monkeypatch, tmp_path):
    client = _client(monkeypatch)
    object.__setattr__(api.settings, "state_db_path", str(tmp_path / "state.db"))
    resp = client.post("/settings", json={
        "ai_base_url": "http://example.com/v1",
        "ai_api_key": "new-key",
        "ai_model": "gpt-test",
    })
    assert resp.status_code == 200
    assert api.settings.ai_base_url == "http://example.com/v1"
    assert api.settings.ai_model == "gpt-test"


def test_settings_test_route_without_key_returns_503(monkeypatch):
    client = _client(monkeypatch)
    object.__setattr__(api.settings, "ai_api_key", "")
    resp = client.post("/settings/test")
    assert resp.status_code == 503


def test_settings_test_route_calls_model(monkeypatch):
    client = _client(monkeypatch)
    object.__setattr__(api.settings, "ai_api_key", "test-key")
    monkeypatch.setattr(api, "test_connection", lambda settings: "ok")
    resp = client.post("/settings/test")
    assert resp.status_code == 200
    assert resp.json() == {"ok": True, "reply": "ok"}


def test_post_settings_blank_key_keeps_existing(monkeypatch, tmp_path):
    client = _client(monkeypatch)
    object.__setattr__(api.settings, "state_db_path", str(tmp_path / "state.db"))
    object.__setattr__(api.settings, "ai_api_key", "keep-me")
    resp = client.post("/settings", json={
        "ai_base_url": "http://example.com/v1",
        "ai_api_key": "",
        "ai_model": "gpt-test",
    })
    assert resp.status_code == 200
    assert api.settings.ai_api_key == "keep-me"
