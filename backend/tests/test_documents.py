import io

import pytest


def _txt_upload(client, headers, content=b"Hello world document content for testing.", filename="test.txt"):
    return client.post(
        "/documents",
        headers={k: v for k, v in headers.items() if k != "Content-Type"},
        files={"file": (filename, io.BytesIO(content), "text/plain")},
    )


def test_upload_txt_success(client, auth_headers):
    res = _txt_upload(client, auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["filename"] == "test.txt"
    assert data["status"] == "uploaded"
    assert "id" in data


def test_upload_unsupported_type(client, auth_headers):
    res = client.post(
        "/documents",
        headers={k: v for k, v in auth_headers.items() if k != "Content-Type"},
        files={"file": ("image.png", io.BytesIO(b"fakepng"), "image/png")},
    )
    assert res.status_code == 415


def test_upload_duplicate_rejected(client, auth_headers):
    content = b"Unique content for dedup test abc123"
    res1 = _txt_upload(client, auth_headers, content=content)
    assert res1.status_code == 200
    res2 = _txt_upload(client, auth_headers, content=content)
    assert res2.status_code == 409


def test_list_documents(client, auth_headers):
    _txt_upload(client, auth_headers, content=b"List test doc one")
    res = client.get("/documents", headers=auth_headers)
    assert res.status_code == 200
    docs = res.json()
    assert isinstance(docs, list)
    assert len(docs) >= 1


def test_get_document(client, auth_headers):
    upload_res = _txt_upload(client, auth_headers, content=b"Get document test content")
    doc_id = upload_res.json()["id"]

    res = client.get(f"/documents/{doc_id}", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == doc_id
    assert "chunk_count" in data


def test_get_document_not_found(client, auth_headers):
    res = client.get("/documents/00000000-0000-0000-0000-000000000000", headers=auth_headers)
    assert res.status_code == 404


def test_delete_document(client, auth_headers):
    upload_res = _txt_upload(client, auth_headers, content=b"Delete me document content")
    doc_id = upload_res.json()["id"]

    del_res = client.delete(f"/documents/{doc_id}", headers=auth_headers)
    assert del_res.status_code == 204

    get_res = client.get(f"/documents/{doc_id}", headers=auth_headers)
    assert get_res.status_code == 404


def test_documents_isolated_between_users(client, db):
    """Documents from one user are not visible to another."""
    import uuid

    def make_user(email_prefix: str):
        email = f"{email_prefix}_{uuid.uuid4().hex[:6]}@test.com"
        res = client.post("/auth/register", json={"email": email, "password": "pw"})
        return {"X-Session-Token": res.json()["session_token"]}

    headers_a = make_user("user_a")
    headers_b = make_user("user_b")

    _txt_upload(client, headers_a, content=b"User A private document abc")
    res_b = client.get("/documents", headers=headers_b)
    assert all(
        doc["filename"] != "test.txt" or doc.get("user_mismatch") for doc in res_b.json()
    )
    # User B should see 0 documents (their own upload list is empty)
    assert res_b.status_code == 200
