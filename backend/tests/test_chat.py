import json

import pytest


def test_create_session(client, auth_headers):
    res = client.post("/chat/sessions", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert "session_id" in data
    assert data["title"] is None


def test_list_sessions(client, auth_headers):
    client.post("/chat/sessions", headers=auth_headers)
    client.post("/chat/sessions", headers=auth_headers)
    res = client.get("/chat/sessions", headers=auth_headers)
    assert res.status_code == 200
    sessions = res.json()
    assert len(sessions) >= 2


def test_get_session(client, auth_headers):
    create_res = client.post("/chat/sessions", headers=auth_headers)
    session_id = create_res.json()["session_id"]

    res = client.get(f"/chat/sessions/{session_id}", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["session_id"] == session_id
    assert data["messages"] == []


def test_get_session_not_found(client, auth_headers):
    res = client.get(
        "/chat/sessions/00000000-0000-0000-0000-000000000000",
        headers=auth_headers,
    )
    assert res.status_code == 404


def test_send_message_streams(client, auth_headers, monkeypatch):
    """Send a message with mocked embedding + LLM and verify SSE frame format."""
    from app.llm import openai_provider

    # Mock provider inits so tests don't need a real OpenAI key
    monkeypatch.setattr(openai_provider.OpenAIEmbeddingProvider, "__init__", lambda self: None)
    monkeypatch.setattr(openai_provider.OpenAILLMProvider, "__init__", lambda self: None)

    # Mock embedding
    monkeypatch.setattr(
        openai_provider.OpenAIEmbeddingProvider,
        "embed",
        lambda self, texts: [[0.1] * 10 for _ in texts],
    )

    # Mock retrieval
    from app.retrieval import chroma as chroma_mod
    from app.retrieval.interfaces import RetrievedChunk

    monkeypatch.setattr(
        chroma_mod.ChromaVectorStore,
        "__init__",
        lambda self: setattr(self, "collection", None) or None,
    )
    monkeypatch.setattr(
        chroma_mod.ChromaVectorStore,
        "query",
        lambda self, *args, **kwargs: [
            RetrievedChunk(
                id="chunk:doc1:0",
                text="The answer is 42.",
                score=0.95,
                metadata={"filename": "test.txt", "page_start": 1, "page_end": 1, "content_hash": "abc"},
            )
        ],
    )

    # Mock LLM streaming
    def fake_stream_answer(self, question, context, chat_history):
        tokens = ["The ", "answer ", "is ", "42. ", "[source: chunk:doc1:0]"]
        yield from tokens
        from app.llm.interfaces import GroundedAnswer
        return GroundedAnswer(
            answer="".join(tokens),
            citations=[{"id": "chunk:doc1:0", "filename": "test.txt", "page_start": "1", "page_end": "1"}],
        )

    monkeypatch.setattr(openai_provider.OpenAILLMProvider, "stream_answer", fake_stream_answer)

    create_res = client.post("/chat/sessions", headers=auth_headers)
    session_id = create_res.json()["session_id"]

    with client.stream(
        "POST",
        f"/chat/sessions/{session_id}/messages",
        headers=auth_headers,
        json={"message": "What is the answer?", "document_ids": []},
    ) as res:
        assert res.status_code == 200
        assert "text/event-stream" in res.headers["content-type"]

        lines = []
        for line in res.iter_lines():
            lines.append(line)

    data_lines = [l[6:] for l in lines if l.startswith("data: ")]
    assert "[DONE]" in data_lines

    token_events = [json.loads(l) for l in data_lines if l != "[DONE]" and json.loads(l).get("type") == "token"]
    done_events = [json.loads(l) for l in data_lines if l != "[DONE]" and json.loads(l).get("type") == "done"]

    assert len(token_events) > 0
    assert len(done_events) == 1
    assert "citations" in done_events[0]
    assert "message_id" in done_events[0]


def test_session_title_set_on_first_message(client, auth_headers, monkeypatch):
    from app.llm import openai_provider
    from app.retrieval import chroma as chroma_mod
    from app.retrieval.interfaces import RetrievedChunk

    monkeypatch.setattr(openai_provider.OpenAIEmbeddingProvider, "__init__", lambda self: None)
    monkeypatch.setattr(openai_provider.OpenAILLMProvider, "__init__", lambda self: None)
    monkeypatch.setattr(
        openai_provider.OpenAIEmbeddingProvider, "embed",
        lambda self, texts: [[0.0] * 10 for _ in texts],
    )
    monkeypatch.setattr(chroma_mod.ChromaVectorStore, "__init__", lambda self: None)
    monkeypatch.setattr(
        chroma_mod.ChromaVectorStore, "query",
        lambda self, *a, **kw: [],
    )

    def fake_stream(self, question, context, history):
        yield "answer"
        from app.llm.interfaces import GroundedAnswer
        return GroundedAnswer(answer="answer", citations=[])

    monkeypatch.setattr(openai_provider.OpenAILLMProvider, "stream_answer", fake_stream)

    create_res = client.post("/chat/sessions", headers=auth_headers)
    session_id = create_res.json()["session_id"]

    long_message = "What is the meaning of life?" + " extra" * 10

    with client.stream(
        "POST",
        f"/chat/sessions/{session_id}/messages",
        headers=auth_headers,
        json={"message": long_message, "document_ids": []},
    ) as res:
        for _ in res.iter_lines():
            pass

    detail_res = client.get(f"/chat/sessions/{session_id}", headers=auth_headers)
    assert detail_res.status_code == 200
    title = detail_res.json()["title"]
    assert title is not None
    assert len(title) <= 60
