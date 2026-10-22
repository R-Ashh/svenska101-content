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

    if book.get("kind") == "grammar":
        check_grammar(path, book)
        return

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


PRACTICE_TYPES = {"fill_in", "choose", "translate_to_swedish", "correct_the_error", "reorder"}


def check_grammar(path: Path, book: dict) -> None:
    chapter_ids, item_ids = set(), set()
    item_count = 0
    for part in book.get("parts", []):
        for chapter in part.get("chapters", []):
            where = f"{path.name} › {chapter.get('id', '?')} {chapter.get('title', '')}"
            if chapter.get("id") in chapter_ids:
                errors.append(f"{where}: duplicate chapter id")
            chapter_ids.add(chapter.get("id"))
            for field in ("id", "title", "summary", "rules", "commonMistakes", "practice"):
                if field not in chapter:
                    errors.append(f"{where}: missing '{field}'")
            for rule in chapter.get("rules", []):
                for example in rule.get("examples", []):
                    if not example.get("swedish") or not example.get("english"):
                        errors.append(f"{where} › {rule.get('title')}: example missing swedish/english")
                table = rule.get("table")
                if table and any(len(row) != len(table.get("headers", [])) for row in table.get("rows", [])):
                    errors.append(f"{where} › {rule.get('title')}: a table row has the wrong number of columns")
            for item in chapter.get("practice", []):
                item_count += 1
                label = f"{where} › practice '{item.get('prompt', '?')}'"
                if not item.get("id"):
                    errors.append(f"{label}: missing 'id'")
                elif item["id"] in item_ids:
                    errors.append(f"{label}: duplicate id '{item['id']}'")
                item_ids.add(item.get("id"))
                if item.get("type") not in PRACTICE_TYPES:
                    errors.append(f"{label}: unknown type '{item.get('type')}'")
                if not item.get("acceptedAnswers"):
                    errors.append(f"{label}: needs a non-empty 'acceptedAnswers' list")
                if item.get("type") == "choose" and item.get("answer") not in item.get("options", []):
                    errors.append(f"{label}: the answer must be one of the options")
    print(f"✓ {path.name}: {len(chapter_ids)} chapters, {item_count} practice items")


books = sorted(Path(__file__).resolve().parent.parent.joinpath("books").glob("*.json"))
for book_path in books:
    check_book(book_path)

if errors:
    print("\n".join(["", "Problems found:"] + [f"  ✗ {e}" for e in errors]))
    sys.exit(1)
print("All books look good.")
