#!/usr/bin/env python3
"""Checks every book in books/ before the app sees it.

Run locally:  python3 scripts/validate.py
Runs automatically on GitHub for every push (see .github/workflows/validate.yml).
"""
import json
import sys
from pathlib import Path

errors = []


def check_book(path: Path) -> None:
    try:
        book = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        errors.append(f"{path.name}: not valid JSON — line {error.lineno}, column {error.colno}: {error.msg}")
        return

    for key in ("schemaVersion", "id", "kind", "title", "version", "parts"):
        if key not in book:
            errors.append(f"{path.name}: missing top-level field '{key}'")

    seen_ids = set()
    entry_count = 0
    for part in book.get("parts", []):
        for section in part.get("sections", []):
            where = f"{path.name} › {section.get('id', '?')} {section.get('title', '')}"
            for entry in section.get("entries", []):
                entry_count += 1
                entry_id = entry.get("id")
                label = f"{where} › {entry.get('swedish', '?')}"
                if not entry_id:
                    errors.append(f"{label}: missing 'id'")
                elif entry_id in seen_ids:
                    errors.append(f"{label}: duplicate id '{entry_id}' (ids must be unique)")
                seen_ids.add(entry_id)
                for field in ("swedish", "english"):
                    if not str(entry.get(field, "")).strip():
                        errors.append(f"{label}: empty '{field}'")
                for field in ("isNew", "notes", "examples"):
                    if field not in entry:
                        errors.append(f"{label}: missing '{field}' (use false / [] if there's nothing)")
                for index, example in enumerate(entry.get("examples", [])):
                    for field in ("swedish", "english"):
                        if not str(example.get(field, "")).strip():
                            errors.append(f"{label} › example {index + 1}: empty '{field}'")

    print(f"✓ {path.name}: {entry_count} entries")


books = sorted(Path(__file__).resolve().parent.parent.joinpath("books").glob("*.json"))
for book_path in books:
    check_book(book_path)

if errors:
    print("\n".join(["", "Problems found:"] + [f"  ✗ {e}" for e in errors]))
    sys.exit(1)
print("All books look good.")
