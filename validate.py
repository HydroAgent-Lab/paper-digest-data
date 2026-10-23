"""Validate papers.json (schema_version 1). Standard library only.

Mirrors validate_papers() in HydroAgent_WP's digest/public.py: the server
checks before it pushes, this checks what actually landed in the repository.
Exit 0 when valid (or when no papers.json exists yet), 1 otherwise.
"""

import json
import re
import sys
from pathlib import Path
from urllib.parse import urlsplit

SCHEMA_VERSION = 1
MAX_AUTHORS = 4
LANGS = {"en", "zh"}
TYPES = {"published", "preprint"}
TOP_KEYS = {"schema_version", "generated_at", "count", "papers"}
PAPER_KEYS = {
    "id", "title", "type", "included_on", "date", "authors", "authors_total",
    "venue", "url", "doi", "summary", "details", "limitations",
}
DAY = re.compile(r"^\d{4}-\d{2}-\d{2}$")
DATE = re.compile(r"^\d{4}(-\d{2}(-\d{2})?)?$")


def safe_url(value):
    parts = urlsplit(value)
    return parts.scheme in {"http", "https"} and bool(parts.netloc) and not parts.username and not parts.password


def validate(doc):
    if not isinstance(doc, dict) or set(doc) != TOP_KEYS:
        return ["top-level keys"]
    errors = []
    if doc["schema_version"] != SCHEMA_VERSION:
        errors.append("schema_version")
    papers = doc["papers"]
    if not isinstance(papers, list) or doc["count"] != len(papers):
        return errors + ["count"]
    seen = set()
    for index, item in enumerate(papers):
        where = f"papers[{index}]"
        if not isinstance(item, dict) or set(item) != PAPER_KEYS:
            errors.append(f"{where}: keys")
            continue
        if not isinstance(item["id"], str) or not item["id"] or item["id"] in seen:
            errors.append(f"{where}: id")
        seen.add(item["id"])
        if not isinstance(item["title"], str) or not item["title"].strip():
            errors.append(f"{where}: title")
        if item["type"] not in TYPES:
            errors.append(f"{where}: type")
        if not isinstance(item["included_on"], str) or not DAY.match(item["included_on"]):
            errors.append(f"{where}: included_on")
        if item["date"] is not None and not (isinstance(item["date"], str) and DATE.match(item["date"])):
            errors.append(f"{where}: date")
        authors = item["authors"]
        if not isinstance(authors, list) or len(authors) > MAX_AUTHORS or not all(isinstance(a, str) for a in authors):
            errors.append(f"{where}: authors")
        elif not isinstance(item["authors_total"], int) or item["authors_total"] < len(authors):
            errors.append(f"{where}: authors_total")
        if item["url"] is not None and not (isinstance(item["url"], str) and safe_url(item["url"])):
            errors.append(f"{where}: url")
        for key in ("venue", "doi"):
            if item[key] is not None and not isinstance(item[key], str):
                errors.append(f"{where}: {key}")
        for key in ("summary", "details", "limitations"):
            value = item[key]
            if not isinstance(value, dict) or set(value) != LANGS or not all(v is None or isinstance(v, str) for v in value.values()):
                errors.append(f"{where}: {key}")
    return errors


def main(argv):
    path = Path(argv[1] if len(argv) > 1 else "papers.json")
    if not path.exists():
        print(f"{path}: not published yet")
        return 0
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"{path}: invalid JSON ({exc})")
        return 1
    errors = validate(doc)
    if errors:
        print(f"{path}: {len(errors)} problem(s)")
        for error in errors[:50]:
            print("  " + error)
        return 1
    print(f"{path}: valid, {doc['count']} papers, generated {doc['generated_at']}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
