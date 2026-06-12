"""
agent_ui — Flask proxy + UI for the agent builder.

Routes:
  GET  /agents                        render agents.html
  GET  /agent-ui/health               health check
  GET  /agent-ui/api/agents           proxy → agent_service GET /agents
  POST /agent-ui/api/agents           proxy → agent_service POST /agents
  PATCH  /agent-ui/api/agents/<id>    proxy → agent_service PATCH /agents/{id}
  DELETE /agent-ui/api/agents/<id>    proxy → agent_service DELETE /agents/{id}
  POST /agent-ui/api/agents/<id>/run  SSE proxy → agent_service POST /agents/{id}/run
  GET  /agent-ui/api/runs/<run_id>    proxy → agent_service GET /agents/runs/{run_id}
"""
import base64
import json
import logging
import os

import requests as http
from flask import Flask, Response, jsonify, render_template, request, stream_with_context

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

app = Flask(__name__)

AGENT_SERVICE_URL = os.getenv("AGENT_SERVICE_URL", "http://agent_service:8002")


def _user_id_from_token() -> str | None:
    """Extract user_id (sub claim) from the Bearer JWT without verifying signature."""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None
    try:
        payload_b64 = auth.split(".")[1]
        payload_b64 += "=" * (-len(payload_b64) % 4)  # re-pad
        return json.loads(base64.urlsafe_b64decode(payload_b64)).get("sub")
    except Exception:
        return None


# ── UI pages ──────────────────────────────────────────────────────────────────

@app.get("/agents")
def agents_page():
    return render_template("agents.html")


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/agent-ui/health")
def health():
    try:
        r = http.get(f"{AGENT_SERVICE_URL}/health", timeout=3)
        svc_ok = r.status_code == 200
    except Exception:
        svc_ok = False
    return jsonify({"status": "ok", "agent_service": svc_ok})


# ── Agent CRUD proxies ────────────────────────────────────────────────────────

@app.get("/agent-ui/api/agents")
def api_list_agents():
    params = request.args.to_dict()
    try:
        r = http.get(f"{AGENT_SERVICE_URL}/agents", params=params, timeout=10)
        return Response(r.content, status=r.status_code,
                        content_type=r.headers.get("Content-Type", "application/json"))
    except Exception as exc:
        return jsonify({"error": str(exc)}), 502


@app.post("/agent-ui/api/agents")
def api_create_agent():
    try:
        body = request.get_json(silent=True) or {}
        if "user_id" not in body:
            body["user_id"] = _user_id_from_token() or "anonymous"
        r = http.post(f"{AGENT_SERVICE_URL}/agents", json=body, timeout=10)
        return Response(r.content, status=r.status_code,
                        content_type=r.headers.get("Content-Type", "application/json"))
    except Exception as exc:
        return jsonify({"error": str(exc)}), 502


@app.route("/agent-ui/api/agents/<agent_id>", methods=["PATCH"])
def api_update_agent(agent_id):
    try:
        r = http.patch(f"{AGENT_SERVICE_URL}/agents/{agent_id}",
                       json=request.get_json(silent=True) or {}, timeout=10)
        return Response(r.content, status=r.status_code,
                        content_type=r.headers.get("Content-Type", "application/json"))
    except Exception as exc:
        return jsonify({"error": str(exc)}), 502


@app.delete("/agent-ui/api/agents/<agent_id>")
def api_delete_agent(agent_id):
    try:
        r = http.delete(f"{AGENT_SERVICE_URL}/agents/{agent_id}", timeout=10)
        return Response(r.content, status=r.status_code,
                        content_type=r.headers.get("Content-Type", "application/json"))
    except Exception as exc:
        return jsonify({"error": str(exc)}), 502


# ── Run proxy (SSE stream) ────────────────────────────────────────────────────

@app.post("/agent-ui/api/agents/<agent_id>/run")
def api_run_agent(agent_id):
    body = request.get_json(silent=True) or {}
    if "user_id" not in body:
        body["user_id"] = _user_id_from_token() or "anonymous"
    try:
        upstream = http.post(
            f"{AGENT_SERVICE_URL}/agents/{agent_id}/run",
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
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )
    except Exception as exc:
        logger.error("agent_service /run error: %s", exc)
        return jsonify({"error": str(exc)}), 502


@app.get("/agent-ui/api/agents/<agent_id>/runs")
def api_list_runs(agent_id):
    params = request.args.to_dict()
    try:
        r = http.get(f"{AGENT_SERVICE_URL}/agents/{agent_id}/runs",
                     params=params, timeout=10)
        return Response(r.content, status=r.status_code,
                        content_type=r.headers.get("Content-Type", "application/json"))
    except Exception as exc:
        return jsonify({"error": str(exc)}), 502


@app.get("/agent-ui/api/runs/<run_id>")
def api_get_run(run_id):
    try:
        r = http.get(f"{AGENT_SERVICE_URL}/agents/runs/{run_id}", timeout=10)
        return Response(r.content, status=r.status_code,
                        content_type=r.headers.get("Content-Type", "application/json"))
    except Exception as exc:
        return jsonify({"error": str(exc)}), 502


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5001))
    app.run(host="0.0.0.0", port=port, debug=os.getenv("FLASK_ENV") == "development")
