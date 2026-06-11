#!/usr/bin/env python3
"""
sanity_check.py — end-to-end smoke test for documents-rag

Tests every layer of the stack through the public nginx entrypoint:
  auth → upload → pipeline processing → search → agent CRUD

Usage:
  python scripts/sanity_check.py
  python scripts/sanity_check.py --base-url http://myserver:8081
  python scripts/sanity_check.py --email admin@example.com --password changeme
  python scripts/sanity_check.py --no-cleanup   # keep test document after run
"""

import argparse
import json
import sys
import time
import urllib.error
import urllib.request

# ── ANSI colours ──────────────────────────────────────────────────────────────
GREEN  = "\033[32m"
RED    = "\033[31m"
YELLOW = "\033[33m"
CYAN   = "\033[36m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

PASS = f"{GREEN}✓ PASS{RESET}"
FAIL = f"{RED}✗ FAIL{RESET}"
SKIP = f"{YELLOW}– SKIP{RESET}"

results: list[tuple[str, bool, str]] = []   # (label, passed, detail)


# ── HTTP helpers ──────────────────────────────────────────────────────────────

def _request(method: str, url: str, *, body=None, headers=None, timeout=15):
    headers = headers or {}
    data = None
    if body is not None:
        if isinstance(body, (dict, list)):
            data = json.dumps(body).encode()
            headers.setdefault("Content-Type", "application/json")
        else:
            data = body
    # Follow redirects manually so DELETE/PATCH aren't swallowed by urllib's
    # refusal to redirect non-GET requests (nginx / FastAPI both emit 307s for slash mismatches).
    for _ in range(3):
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read()
                try:
                    return resp.status, json.loads(raw)
                except Exception:
                    return resp.status, {}
        except urllib.error.HTTPError as e:
            if e.code in (301, 302, 307, 308) and "Location" in e.headers:
                url = e.headers["Location"]
                continue
            try:
                return e.code, json.loads(e.read())
            except Exception:
                return e.code, {}
        except Exception as exc:
            return None, {"error": str(exc)}
    return None, {"error": "too many redirects"}


def get(url, token=None, timeout=15):
    h = {"Authorization": f"Bearer {token}"} if token else {}
    return _request("GET", url, headers=h, timeout=timeout)


def post(url, body=None, token=None, timeout=30):
    h = {"Authorization": f"Bearer {token}"} if token else {}
    return _request("POST", url, body=body, headers=h, timeout=timeout)


def delete(url, token, timeout=15):
    h = {"Authorization": f"Bearer {token}"}
    return _request("DELETE", url, headers=h, timeout=timeout)


def multipart_upload(url, token, filename, content, source_type, timeout=60):
    """Send multipart/form-data upload (no external deps)."""
    boundary = "----SanityCheckBoundary"
    body_parts = []
    body_parts.append(f"--{boundary}\r\n"
                      f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
                      f"Content-Type: text/plain\r\n\r\n"
                      f"{content}\r\n")
    body_parts.append(f"--{boundary}\r\n"
                      f'Content-Disposition: form-data; name="source_type"\r\n\r\n'
                      f"{source_type}\r\n")
    body_parts.append(f"--{boundary}--\r\n")
    raw = "".join(body_parts).encode()
    headers = {
        "Content-Type": f"multipart/form-data; boundary={boundary}",
        "Authorization": f"Bearer {token}",
    }
    return _request("POST", url, body=raw, headers=headers, timeout=timeout)


# ── Test runner ───────────────────────────────────────────────────────────────

def check(label: str, passed: bool, detail: str = ""):
    icon = PASS if passed else FAIL
    suffix = f"  {CYAN}{detail}{RESET}" if detail else ""
    print(f"  {icon}  {label}{suffix}")
    results.append((label, passed, detail))
    return passed


def section(title: str):
    print(f"\n{BOLD}{title}{RESET}")


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_reachability(base: str) -> bool:
    section("1. Reachability")
    status, body = get(f"{base}/api/auth/login", timeout=5)
    reachable = status is not None and status != 502
    return check("nginx entrypoint reachable", reachable,
                 f"HTTP {status}" if status else str(body.get("error", "")))


def test_auth(base: str, email: str, password: str) -> str | None:
    section("2. Authentication")
    status, body = post(f"{base}/api/auth/login", {"email": email, "password": password})
    ok = status == 200 and "access_token" in body
    check("POST /api/auth/login", ok, f"HTTP {status}")
    if not ok:
        print(f"      {RED}→ response: {body}{RESET}")
        return None
    token = body["access_token"]

    # Verify token works
    status2, body2 = get(f"{base}/api/documents", token=token)
    check("JWT token accepted (GET /api/documents)", status2 == 200,
          f"HTTP {status2}")
    return token


def test_upload_pipeline(base: str, token: str, cleanup: bool) -> str | None:
    section("3. Upload & Processing Pipeline")

    content = (
        "JIRA ISSUE: SANITY-001\n"
        "Project: Sanity Check\nType: Task\n"
        "Summary: Automated sanity check test document\n"
        "Status: Open   Priority: P3   Reporter: sanity_bot\n\n"
        "Description:\n"
        "This document was uploaded by the sanity_check.py script "
        "to verify the full processing pipeline is working correctly.\n"
    )

    # Upload directly to api_gateway so the document is owned by the test user
    # (search_ui proxy uploads as a service account, which breaks cross-user polling)
    status, body = multipart_upload(
        f"{base}/api/documents/upload",
        token, "[sanity] test-jira.txt", content, "jira",
    )
    ok = status == 201 and "document_id" in body
    check("POST /api/documents/upload", ok, f"HTTP {status}")
    if not ok:
        print(f"      {RED}→ {body}{RESET}")
        return None

    doc_id = body["document_id"]
    check("document_id returned", bool(doc_id), doc_id[:8] + "…")

    # Poll until all pipeline stages complete (max 90s)
    print(f"      {CYAN}polling pipeline…{RESET}", end="", flush=True)
    deadline = time.time() + 90
    final_status = None
    jobs = []
    while time.time() < deadline:
        time.sleep(4)
        s, d = get(f"{base}/api/documents/{doc_id}", token=token)
        if s == 200:
            final_status = d.get("status")
            jobs = d.get("processing_jobs", [])
            if final_status in ("COMPLETED", "FAILED"):
                break
        print(".", end="", flush=True)
    print()

    check("document reached COMPLETED", final_status == "COMPLETED",
          f"status={final_status}")

    stage_map = {j["stage"]: j["status"] for j in jobs}
    for stage in ("TEXT_EXTRACTION", "CHUNKING", "EMBEDDING", "SUMMARIZATION"):
        s = stage_map.get(stage, "MISSING")
        check(f"  pipeline stage {stage}", s == "COMPLETED", s)

    src = None
    if jobs or final_status:
        s, d = get(f"{base}/api/documents/{doc_id}", token=token)
        src = d.get("source_type")
    check("source_type=jira stored", src == "jira", f"source_type={src}")

    return doc_id


def test_search(base: str, token: str) -> bool:
    section("4. Search")

    # Keyword search
    status, body = post(
        f"{base}/search-ui/api/search",
        {"query": "sanity check test document", "user_id": "admin@example.com",
         "top_k": 5, "mode": "keyword"},
        token=token,
    )
    ok = status == 200 and "results" in body
    check("POST /search-ui/api/search (keyword)", ok, f"HTTP {status}")
    if ok:
        check("  results returned", len(body["results"]) > 0,
              f"{len(body['results'])} chunk(s)")

    # Hybrid search with source filter
    status2, body2 = post(
        f"{base}/search-ui/api/search",
        {"query": "sanity check", "user_id": "admin@example.com",
         "top_k": 5, "mode": "hybrid", "source_types": ["jira"]},
        token=token,
    )
    ok2 = status2 == 200
    check("POST /search-ui/api/search (hybrid + source filter)", ok2,
          f"HTTP {status2}")

    return ok


def test_agents(base: str, token: str) -> str | None:
    section("5. Agent Service")

    # List agents
    status, body = get(f"{base}/agent-ui/api/agents", token=token)
    ok = status == 200 and isinstance(body, list)
    check("GET /agent-ui/api/agents", ok, f"HTTP {status}")
    if not ok:
        print(f"      {RED}→ {body}{RESET}")
        return None
    check("  response is list", isinstance(body, list), f"{len(body)} agent(s)")

    # Create a test agent
    status2, body2 = post(
        f"{base}/agent-ui/api/agents",
        {
            "user_id": "admin@example.com",
            "name": "[sanity] test agent",
            "description": "Created by sanity_check.py",
            "system_prompt": "You are a test assistant.",
            "output_format": "markdown",
            "tools": ["search_all"],
        },
        token=token,
    )
    ok2 = status2 in (200, 201) and "id" in body2
    check("POST /agent-ui/api/agents (create)", ok2, f"HTTP {status2}")
    if not ok2:
        print(f"      {RED}→ {body2}{RESET}")
        return None

    agent_id = body2["id"]
    check("  agent id returned", bool(agent_id), agent_id[:8] + "…")
    return agent_id


def cleanup_test_data(base: str, token: str, doc_id: str | None, agent_id: str | None):
    section("6. Cleanup")
    if doc_id:
        s, _ = delete(f"{base}/api/documents/{doc_id}", token=token)
        check("DELETE test document", s in (200, 204), f"HTTP {s}")
    if agent_id:
        s, _ = delete(f"{base}/agent-ui/api/agents/{agent_id}", token=token)
        check("DELETE test agent", s in (200, 204), f"HTTP {s}")


def print_summary():
    total  = len(results)
    passed = sum(1 for _, ok, _ in results if ok)
    failed = total - passed

    print(f"\n{BOLD}{'─'*50}{RESET}")
    print(f"{BOLD}Results: {passed}/{total} checks passed{RESET}")
    if failed:
        print(f"\n{RED}Failed checks:{RESET}")
        for label, ok, detail in results:
            if not ok:
                print(f"  {RED}✗{RESET}  {label}" + (f"  ({detail})" if detail else ""))
    if failed == 0:
        print(f"\n{GREEN}{BOLD}All checks passed — system is healthy ✓{RESET}")
    else:
        print(f"\n{RED}{BOLD}{failed} check(s) failed — review output above{RESET}")
    print()
    return failed == 0


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="documents-rag sanity check")
    parser.add_argument("--base-url",  default="http://localhost:8081")
    parser.add_argument("--email",     default="admin@example.com")
    parser.add_argument("--password",  default="changeme")
    parser.add_argument("--no-cleanup", action="store_true",
                        help="keep test document and agent after run")
    args = parser.parse_args()

    base = args.base_url.rstrip("/")

    print(f"\n{BOLD}documents-rag sanity check{RESET}")
    print(f"  target : {CYAN}{base}{RESET}")
    print(f"  user   : {args.email}")

    doc_id   = None
    agent_id = None
    token    = None

    try:
        if not test_reachability(base):
            print(f"\n{RED}Cannot reach {base} — is the stack running?{RESET}")
            print("  Run: docker compose up -d   (or ./setup.sh)")
            sys.exit(1)

        token = test_auth(base, args.email, args.password)
        if not token:
            print(f"\n{RED}Auth failed — run: docker compose exec api_gateway python seed.py{RESET}")
            sys.exit(1)

        doc_id = test_upload_pipeline(base, token, cleanup=not args.no_cleanup)
        test_search(base, token)
        agent_id = test_agents(base, token)

    finally:
        if not args.no_cleanup and token:
            cleanup_test_data(base, token, doc_id, agent_id)

    ok = print_summary()
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
