#!/usr/bin/env python3
"""
Seed the documents-rag system with synthetic Forge SaaS data.

Usage:
    python scripts/seed_data.py                         # seed both scenarios
    python scripts/seed_data.py --scenario a            # only Scenario A (P1 incident)
    python scripts/seed_data.py --scenario b            # only Scenario B (feature rollout)
    python scripts/seed_data.py --reset                 # delete all [seed] docs
    python scripts/seed_data.py --reset --seed          # delete then reseed
    python scripts/seed_data.py --wait                  # seed + wait for processing to complete
    python scripts/seed_data.py --base-url http://localhost:8081
    python scripts/seed_data.py --email admin@example.com --password changeme

Company: Forge — unified project management + CRM + customer support SaaS.

Scenario A — P1 Incident: Notification Delivery Failure
  Sources: 2 Confluence, 3 Jira, 1 Slack, 1 GitHub, 1 HubSpot

Scenario B — Feature: AI-Powered Smart Ticket Routing
  Sources: 2 Confluence, 2 Jira, 1 Slack, 1 GitHub, 1 HubSpot
"""
import argparse
import sys
import os

# Allow running from repo root without installing
sys.path.insert(0, os.path.dirname(__file__))

from seed.builders import (
    build_jira_text,
    build_confluence_text,
    build_slack_text,
    build_hubspot_text,
    build_github_text,
)
from seed.client import (
    login,
    upload_text,
    poll_until_done,
    delete_seed_docs,
    get_document,
)
from seed import scenario_a, scenario_b


BUILDERS = {
    "jira":       build_jira_text,
    "confluence": build_confluence_text,
    "slack":      build_slack_text,
    "hubspot":    build_hubspot_text,
    "github":     build_github_text,
}

COL_W = (52, 12, 11, 36)
DIVIDER = "─" * (sum(COL_W) + len(COL_W) * 3 + 1)


def _row(name, source_type, status, doc_id=""):
    return (
        f"  {name:<{COL_W[0]}}  "
        f"{source_type:<{COL_W[1]}}  "
        f"{status:<{COL_W[2]}}  "
        f"{doc_id:<{COL_W[3]}}"
    )


def _header():
    return _row("Document", "source_type", "status", "doc_id")


def seed_documents(
    documents: list[dict],
    base_url: str,
    token: str,
    wait: bool,
) -> list[dict]:
    results = []
    for doc in documents:
        source_type = doc["source_type"]
        filename    = doc["filename"]
        builder     = BUILDERS[source_type]
        text        = builder(doc["data"])

        try:
            doc_id = upload_text(base_url, token, text, filename, source_type)
            status = "UPLOADED"

            if wait:
                status = poll_until_done(base_url, token, doc_id, timeout=120)
                # Also verify source_type was stored
                detail = get_document(base_url, token, doc_id)
                stored_type = detail.get("source_type") or "?"
                status_display = f"{status} [{stored_type}]"
            else:
                status_display = status

            print(_row(filename[:COL_W[0]], source_type, status_display, doc_id))
            results.append({"filename": filename, "doc_id": doc_id, "status": status})

        except Exception as exc:
            print(_row(filename[:COL_W[0]], source_type, "ERROR", str(exc)[:36]))
            results.append({"filename": filename, "doc_id": None, "status": "ERROR", "error": str(exc)})

    return results


def main():
    parser = argparse.ArgumentParser(description="Seed Forge SaaS synthetic data")
    parser.add_argument("--scenario", choices=["a", "b"], default=None,
                        help="Seed only scenario A or B (default: both)")
    parser.add_argument("--reset", action="store_true",
                        help="Delete all [seed] docs before seeding")
    parser.add_argument("--seed", action="store_true",
                        help="Seed after reset (use with --reset to reset+seed)")
    parser.add_argument("--wait", action="store_true",
                        help="Wait for all documents to finish processing (COMPLETED/FAILED)")
    parser.add_argument("--base-url", default="http://localhost:8081",
                        help="Base URL of the nginx proxy (default: http://localhost:8081)")
    parser.add_argument("--email", default="admin@example.com")
    parser.add_argument("--password", default="changeme")
    args = parser.parse_args()

    # If neither --reset nor --seed nor --scenario is given, default to seeding both
    seeding = not args.reset or args.seed or (args.reset and not args.seed)
    if args.reset and not args.seed:
        seeding = False

    print(f"\n🔐 Logging in as {args.email} …")
    try:
        token = login(args.base_url, args.email, args.password)
        print("   ✓ Authenticated\n")
    except Exception as exc:
        print(f"   ✗ Login failed: {exc}")
        sys.exit(1)

    # ── Reset ─────────────────────────────────────────────────────────────────
    if args.reset:
        print("🗑  Deleting existing [seed] documents …")
        count = delete_seed_docs(args.base_url, token)
        print(f"   ✓ Deleted {count} seed document(s)\n")
        if not args.seed:
            print("Done. Run with --seed to reseed, or without --reset to seed fresh.\n")
            return

    # ── Seed ──────────────────────────────────────────────────────────────────
    if seeding or args.seed:
        scenarios = []
        if args.scenario in (None, "a"):
            scenarios.append(("A — P1 Incident: Notification Delivery Failure", scenario_a.DOCUMENTS))
        if args.scenario in (None, "b"):
            scenarios.append(("B — Feature: AI-Powered Smart Ticket Routing", scenario_b.DOCUMENTS))

        all_results = []
        for scenario_label, documents in scenarios:
            print(f"📦 Scenario {scenario_label}")
            print(DIVIDER)
            print(_header())
            print(DIVIDER)
            results = seed_documents(documents, args.base_url, token, wait=args.wait)
            all_results.extend(results)
            print(DIVIDER)

            ok    = sum(1 for r in results if r["status"] not in ("ERROR", "FAILED", "TIMEOUT"))
            fail  = sum(1 for r in results if r["status"] in ("ERROR", "FAILED"))
            total = len(results)
            print(f"   {ok}/{total} uploaded successfully" + (f", {fail} errors" if fail else "") + "\n")

        # ── Summary ───────────────────────────────────────────────────────────
        total = len(all_results)
        ok    = sum(1 for r in all_results if r["status"] not in ("ERROR", "FAILED", "TIMEOUT"))
        print(f"✅ Done — {ok}/{total} documents seeded")
        if args.wait:
            completed = sum(1 for r in all_results if r["status"] == "COMPLETED")
            print(f"   {completed}/{ok} fully processed (COMPLETED)")
        print()
        print("Next steps:")
        print("  • Search UI → http://localhost:8081/search")
        print("    Try: 'notification outage' or 'ticket routing'")
        print("  • Agent builder → http://localhost:8081/agents")
        print("    Create an agent, query: 'Summarize the notification P1 incident'")
        print()


if __name__ == "__main__":
    main()
