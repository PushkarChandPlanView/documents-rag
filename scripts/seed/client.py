"""
HTTP client helpers for the seed script.

All calls go through nginx at base_url (default http://localhost:8081).
Auth uses JWT Bearer tokens from /api/auth/login.
"""
import io
import time
import urllib.parse
import urllib.request
import json


# ── Auth ──────────────────────────────────────────────────────────────────────

def login(base_url: str, email: str, password: str) -> str:
    """POST /api/auth/login → returns JWT access token."""
    payload = json.dumps({"email": email, "password": password}).encode()
    req = urllib.request.Request(
        f"{base_url}/api/auth/login",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req) as r:
        data = json.loads(r.read())
    return data["access_token"]


# ── Upload ────────────────────────────────────────────────────────────────────

def upload_text(
    base_url: str,
    token: str,
    text: str,
    filename: str,
    source_type: str,
) -> str:
    """
    POST /api/documents/upload with a plain-text file + source_type.
    Returns the new document_id (UUID string).
    """
    file_bytes = text.encode("utf-8")
    boundary = "----SeedBoundary7MA4YWxkTrZu0gW"

    body_parts = []
    # file field
    body_parts.append(f"--{boundary}\r\n".encode())
    body_parts.append(
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'.encode()
    )
    body_parts.append(b"Content-Type: text/plain\r\n\r\n")
    body_parts.append(file_bytes)
    body_parts.append(b"\r\n")
    # source_type field
    body_parts.append(f"--{boundary}\r\n".encode())
    body_parts.append(b'Content-Disposition: form-data; name="source_type"\r\n\r\n')
    body_parts.append(source_type.encode())
    body_parts.append(b"\r\n")
    body_parts.append(f"--{boundary}--\r\n".encode())

    body = b"".join(body_parts)
    req = urllib.request.Request(
        f"{base_url}/api/documents/upload",
        data=body,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
        method="POST",
    )
    with urllib.request.urlopen(req) as r:
        data = json.loads(r.read())
    return str(data["document_id"])


# ── Poll ──────────────────────────────────────────────────────────────────────

def get_document(base_url: str, token: str, doc_id: str) -> dict:
    req = urllib.request.Request(
        f"{base_url}/api/documents/{doc_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())


def poll_until_done(
    base_url: str,
    token: str,
    doc_id: str,
    timeout: int = 90,
    interval: float = 3.0,
) -> str:
    """Poll GET /api/documents/{id} until status is COMPLETED or FAILED. Returns final status."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        doc = get_document(base_url, token, doc_id)
        status = doc.get("status", "PENDING")
        if status in ("COMPLETED", "FAILED"):
            return status
        time.sleep(interval)
    return "TIMEOUT"


# ── List + delete ─────────────────────────────────────────────────────────────

def list_all_documents(base_url: str, token: str) -> list[dict]:
    """Paginate through GET /api/documents and return all items."""
    items = []
    cursor = None
    while True:
        url = f"{base_url}/api/documents?limit=100"
        if cursor:
            url += f"&cursor={urllib.parse.quote(cursor)}"
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
        with urllib.request.urlopen(req) as r:
            data = json.loads(r.read())
        items.extend(data.get("items", []))
        if not data.get("has_more"):
            break
        cursor = data.get("next_cursor")
    return items


def delete_document(base_url: str, token: str, doc_id: str) -> None:
    req = urllib.request.Request(
        f"{base_url}/api/documents/{doc_id}",
        headers={"Authorization": f"Bearer {token}"},
        method="DELETE",
    )
    try:
        with urllib.request.urlopen(req):
            pass
    except urllib.error.HTTPError as e:
        if e.code != 404:
            raise


def delete_seed_docs(base_url: str, token: str, prefix: str = "[seed]") -> int:
    """Delete all documents whose name starts with prefix. Returns count deleted."""
    docs = list_all_documents(base_url, token)
    seed_docs = [d for d in docs if d.get("name", "").startswith(prefix)]
    for doc in seed_docs:
        delete_document(base_url, token, str(doc["id"]))
    return len(seed_docs)
