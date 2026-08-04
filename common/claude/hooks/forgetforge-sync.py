#!/usr/bin/env python3
"""Sync the intent-patterns.md failure ledger into forgetforge's mistake ontology.

Organic connection between the two mistake systems: the ledger is the human-readable
source of truth (append-only, fed by intent-lock correction capture); the forgetforge
graph is its queryable/routable index. `graph-recall --mistakes --anchor <domain>` then
surfaces domain-relevant past mistakes before non-trivial work.

Bounded and cheap by construction: pure table parse (no LLM, no network), stable node ids
so re-runs upsert instead of duplicating, hard row cap. Runs at SessionEnd from
session-intent-archive.sh (fail-open, never blocks teardown).
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys

LEDGER = os.path.expanduser("~/.claude/guides/work/intent-patterns.md")
ROW_CAP = 2000
# graph-ingest bounds a single call at INGEST_NODE_CAP (200); chunk so no mistake is
# silently dropped once the ledger grows past one batch.
BATCH = 200


def parse_rows(text: str) -> list[dict]:
    rows = []
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) != 4:
            continue
        date, context, failure, rule = cells
        # skip header + separator rows
        if date.lower() == "date" or set(date) <= {"-", ":", " "}:
            continue
        if not rule or not context:
            continue
        rows.append({"date": date, "context": context, "failure": failure, "rule": rule})
    return rows[:ROW_CAP]


def to_nodes(rows: list[dict]) -> list[dict]:
    nodes = []
    for r in rows:
        nid = "mistake:" + hashlib.sha1((r["date"] + r["rule"]).encode("utf-8")).hexdigest()[:12]
        nodes.append(
            {
                "id": nid,
                "node_type": "mistake",
                # content is FTS-indexed; include failure + rule so recall matches either.
                "content": f"{r['failure']} → RULE: {r['rule']}",
                # domain_tags is what --mistakes routes on.
                "domain_tags": r["context"],
                "importance": 0.9,
            }
        )
    return nodes


def main() -> int:
    ff = shutil.which("forgetforge")
    if ff is None or not os.path.isfile(LEDGER):
        return 0  # nothing to do; never block the backup chain
    rows = parse_rows(open(LEDGER, encoding="utf-8").read())
    if not rows:
        return 0
    nodes = to_nodes(rows)
    synced = 0
    try:
        for i in range(0, len(nodes), BATCH):
            batch = nodes[i : i + BATCH]
            p = subprocess.run(
                [ff, "graph-ingest", "--stdin"],
                input=json.dumps({"nodes": batch, "edges": []}),
                capture_output=True,
                text=True,
                timeout=30,
            )
            if p.returncode != 0:
                break
            synced += len(batch)
        if synced:
            print(f"forgetforge-sync: {synced} ledger rows → mistake nodes")
        return 0
    except (subprocess.SubprocessError, OSError):
        return 0  # graceful: sync is best-effort


if __name__ == "__main__":
    sys.exit(main())
