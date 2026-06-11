"""
search_ui — standalone search & ingest web UI for documents-rag.

Routes (all new, nothing shared with existing services):
  GET  /search                     Search UI
  GET  /ingest                     File-upload / link ingest UI
  POST /search-ui/api/search       Proxy → rag_service /search
  POST /search-ui/api/query        Proxy → rag_service /query  (SSE stream)
  POST /search-ui/api/upload       Proxy → api_gateway /documents/upload
  POST /search-ui/api/link         Proxy → api_gateway /documents/link
  GET  /search-ui/api/documents    Proxy → api_gateway /documents
  DELETE /search-ui/api/documents/<id>  Proxy → api_gateway /documents/<id>
  GET  /search-ui/health           Internal health check
"""
import os
import logging
from flask import Flask, Response, jsonify, render_template, request, stream_with_context
import requests as http
from elasticsearch import Elasticsearch

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

app = Flask(__name__)

RAG_SERVICE_URL   = os.getenv("RAG_SERVICE_URL",   "http://rag_service:8001")
API_GATEWAY_URL   = os.getenv("API_GATEWAY_URL",   "http://api_gateway:8000")
# Static token takes priority; if absent, auto-login with service account credentials
API_GW_TOKEN      = os.getenv("API_GW_TOKEN",      "")
GW_SERVICE_EMAIL  = os.getenv("GW_SERVICE_EMAIL",  "admin1@example.com")
GW_SERVICE_PASS   = os.getenv("GW_SERVICE_PASS",   "changeme")
ES_URL            = os.getenv("ELASTICSEARCH_URL",  "http://elasticsearch:9200")
ES_INDEX          = os.getenv("ES_INDEX_CHUNKS",    "document_chunks")

_es: Elasticsearch | None = None
_cached_token: str = ""


def _get_es() -> Elasticsearch:
    global _es
    if _es is None:
        _es = Elasticsearch(ES_URL, request_timeout=10)
    return _es


def _fetch_token() -> str:
    """Login to api_gateway and return a fresh access token."""
    try:
        r = http.post(
            f"{API_GATEWAY_URL}/api/auth/login",
            json={"email": GW_SERVICE_EMAIL, "password": GW_SERVICE_PASS},
            timeout=10,
        )
        r.raise_for_status()
        token = r.json().get("access_token", "")
        logger.info("search_ui: obtained api_gateway token for %s", GW_SERVICE_EMAIL)
        return token
    except Exception as exc:
        logger.error("search_ui: failed to obtain api_gateway token: %s", exc)
        return ""


def _gw_headers(retry: bool = False) -> dict:
    """Return Authorization headers for api_gateway, auto-fetching token if needed."""
    global _cached_token
    # Static token from env always wins
    if API_GW_TOKEN:
        return {"Authorization": f"Bearer {API_GW_TOKEN}"}
    # Fetch/refresh if empty or caller signals a retry after 401
    if not _cached_token or retry:
        _cached_token = _fetch_token()
    return {"Authorization": f"Bearer {_cached_token}"} if _cached_token else {}


# ── UI pages ──────────────────────────────────────────────────────────────────

@app.get("/search")
def search_page():
    return render_template("search.html")


@app.get("/ingest")
def ingest_page():
    return render_template("ingest.html")


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/search-ui/health")
def health():
    rag_ok = False
    try:
        r = http.get(f"{RAG_SERVICE_URL}/health", timeout=3)
        rag_ok = r.status_code == 200
    except Exception:
        pass
    return jsonify({"status": "ok", "rag_service": rag_ok})


# ── Search proxy ──────────────────────────────────────────────────────────────

@app.post("/search-ui/api/search")
def api_search():
    """Forward POST /search-ui/api/search → rag_service /search"""
    body = request.get_json(silent=True) or {}
    try:
        r = http.post(
            f"{RAG_SERVICE_URL}/search",
            json=body,
            timeout=30,
        )
        return Response(r.content, status=r.status_code,
                        content_type=r.headers.get("Content-Type", "application/json"))
    except Exception as exc:
        logger.error("rag_service /search error: %s", exc)
        return jsonify({"error": str(exc)}), 502


@app.post("/search-ui/api/query")
def api_query():
    """
    Forward POST /search-ui/api/query → rag_service /query  (SSE stream).
    Streams the SSE response back to the browser.
    """
    body = request.get_json(silent=True) or {}
    try:
        upstream = http.post(
            f"{RAG_SERVICE_URL}/query",
            json=body,
            stream=True,
            timeout=None,
        )

        def generate():
            for chunk in upstream.iter_content(chunk_size=None):
                if chunk:
                    yield chunk

        return Response(
            stream_with_context(generate()),
            status=upstream.status_code,
            content_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )
    except Exception as exc:
        logger.error("rag_service /query error: %s", exc)
        return jsonify({"error": str(exc)}), 502


@app.post("/search-ui/api/agentic-query")
def api_agentic_query():
    """
    Forward POST /search-ui/api/agentic-query → rag_service /agentic-query  (SSE stream).
    Streams the SSE response back to the browser.
    """
    body = request.get_json(silent=True) or {}
    try:
        upstream = http.post(
            f"{RAG_SERVICE_URL}/agentic-query",
            json=body,
            stream=True,
            timeout=None,
        )

        def generate():
            for chunk in upstream.iter_content(chunk_size=None):
                if chunk:
                    yield chunk

        return Response(
            stream_with_context(generate()),
            status=upstream.status_code,
            content_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )
    except Exception as exc:
        logger.error("rag_service /agentic-query error: %s", exc)
        return jsonify({"error": str(exc)}), 502


# ── Ingest proxies ────────────────────────────────────────────────────────────

@app.post("/search-ui/api/upload")
def api_upload():
    """Forward multipart file upload → api_gateway /documents/upload"""
    try:
        file = request.files.get("file")
        if not file:
            return jsonify({"error": "No file provided"}), 400

        folder_id   = request.form.get("folder_id", "")
        source_type = request.form.get("source_type", "upload")
        for retry in (False, True):
            file.stream.seek(0)
            files_payload = {"file": (file.filename, file.stream, file.content_type)}
            data_payload  = {"source_type": source_type}
            if folder_id:
                data_payload["folder_id"] = folder_id
            r = http.post(
                f"{API_GATEWAY_URL}/api/documents/upload",
                files=files_payload,
                data=data_payload,
                headers=_gw_headers(retry=retry),
                timeout=60,
            )
            if r.status_code != 401:
                break
        return Response(r.content, status=r.status_code,
                        content_type=r.headers.get("Content-Type", "application/json"))
    except Exception as exc:
        logger.error("api_gateway /documents/upload error: %s", exc)
        return jsonify({"error": str(exc)}), 502


@app.post("/search-ui/api/link")
def api_link():
    """Forward POST /search-ui/api/link → api_gateway /documents/link"""
    body = request.get_json(silent=True) or {}
    try:
        for retry in (False, True):
            r = http.post(
                f"{API_GATEWAY_URL}/api/documents/link",
                json=body,
                headers=_gw_headers(retry=retry),
                timeout=30,
            )
            if r.status_code != 401:
                break
        return Response(r.content, status=r.status_code,
                        content_type=r.headers.get("Content-Type", "application/json"))
    except Exception as exc:
        logger.error("api_gateway /documents/link error: %s", exc)
        return jsonify({"error": str(exc)}), 502


@app.get("/search-ui/api/documents")
def api_list_documents():
    """Forward GET /search-ui/api/documents → api_gateway /documents"""
    params = request.args.to_dict()
    try:
        for retry in (False, True):
            r = http.get(
                f"{API_GATEWAY_URL}/api/documents",
                params=params,
                headers=_gw_headers(retry=retry),
                timeout=15,
            )
            if r.status_code != 401:
                break
        return Response(r.content, status=r.status_code,
                        content_type=r.headers.get("Content-Type", "application/json"))
    except Exception as exc:
        logger.error("api_gateway GET /documents error: %s", exc)
        return jsonify({"error": str(exc)}), 502


@app.get("/search-ui/api/documents/<document_id>/download")
def api_download_document(document_id):
    """Stream file download from api_gateway → client."""
    try:
        for retry in (False, True):
            r = http.get(
                f"{API_GATEWAY_URL}/api/documents/{document_id}/download",
                headers=_gw_headers(retry=retry),
                stream=True,
                timeout=60,
            )
            if r.status_code != 401:
                break
        if not r.ok:
            return jsonify({"error": "Download failed"}), r.status_code

        def generate():
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    yield chunk

        cd = r.headers.get("Content-Disposition", "attachment")
        ct = r.headers.get("Content-Type", "application/octet-stream")
        return Response(
            stream_with_context(generate()),
            status=r.status_code,
            content_type=ct,
            headers={"Content-Disposition": cd},
        )
    except Exception as exc:
        logger.error("download error: %s", exc)
        return jsonify({"error": str(exc)}), 502


@app.delete("/search-ui/api/documents/<document_id>")
def api_delete_document(document_id):
    """Forward DELETE → api_gateway /documents/<id>, then clean up ES chunks."""
    try:
        for retry in (False, True):
            r = http.delete(
                f"{API_GATEWAY_URL}/api/documents/{document_id}",
                headers=_gw_headers(retry=retry),
                timeout=15,
            )
            if r.status_code != 401:
                break
        if r.status_code == 204:
            # Clean up orphaned ES chunks for this document
            try:
                _get_es().delete_by_query(
                    index=ES_INDEX,
                    body={"query": {"term": {"document_id": document_id}}},
                    refresh=True,
                )
                logger.info("ES chunks deleted for document_id=%s", document_id)
            except Exception as exc:
                logger.warning("ES cleanup failed for %s: %s", document_id, exc)
            return jsonify({"status": "deleted", "document_id": document_id})
        return Response(r.content, status=r.status_code,
                        content_type=r.headers.get("Content-Type", "application/json"))
    except Exception as exc:
        logger.error("api_gateway DELETE /documents/%s error: %s", document_id, exc)
        return jsonify({"error": str(exc)}), 502


# ── Entry point (dev only — prod uses gunicorn) ───────────────────────────────

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=os.getenv("FLASK_ENV") == "development")
