#!/usr/bin/env python3
"""Converts a grammar book written in the "Essential Swedish Grammar" AI format
(snake_case keys, sv/pron/en examples, practice items with a single `answer` string)
into the format the Svenska 101 app reads.

    python3 scripts/import_grammar.py ~/Downloads/essential_swedish_grammar.json

Writes books/essential-grammar.json (or --output). What it does:
- camelCase keys and the same example shape as the vocabulary book (swedish/english/pronunciation)
- gives every practice item a stable id (e.g. "g1.1-3") — learning progress is linked to it,
  so after importing, edit the output file directly rather than re-importing over it
- turns each answer into an explicit `acceptedAnswers` list:
    "vore / var"                     → ["vore", "var"]
    "som (or nothing)"               → ["som", ""]      ("" = leaving it out is also right)
    "Det är vännen (som) jag …"      → with and without the optional word
"""
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def example(raw: dict) -> dict:
    result = {"swedish": raw["sv"], "english": raw["en"], "pronunciation": raw.get("pron")}
    if raw.get("note"):
        result["note"] = raw["note"]
    return result


def accepted_answers(item: dict) -> list[str]:
    answer = item["answer"].strip()
    if item["type"] == "choose":
        return [answer]  # must match one of the options exactly

    if answer.endswith("(or nothing)"):
        return [answer.removesuffix("(or nothing)").strip(), ""]

    if " / " in answer:
        return [part.strip() for part in answer.split(" / ")]

    optional = re.compile(r"\s*\(([^)]+)\)")
    if optional.search(answer):
        with_words = optional.sub(lambda m: " " + m.group(1), answer).strip()
        without_words = optional.sub("", answer).strip()
        return list(dict.fromkeys([with_words, without_words]))

    return [answer]


def full_sentence(item: dict, accepted: list[str]) -> str:
    """The complete Swedish sentence for an item — shown and read aloud after answering.

    Gap items get the answer filled in and hint brackets removed:
      "Om jag ___ (vara) rik, …"  → "Om jag vore rik, …"
      "en stol → ___ (the chair)" → "en stol, stolen"
    """
    if item["type"] not in ("fill_in", "choose") or "___" not in item["prompt"]:
        return accepted[0]
    gap = accepted[0]
    if gap.startswith("—"):  # "— (nothing)": the gap stays empty
        gap = ""
    sentence = item["prompt"].replace("___", gap)
    sentence = re.sub(r"\s*\([^)]*\)", "", sentence)
    sentence = sentence.replace(" → ", ", ").replace("→", ",")
    return re.sub(r"\s{2,}", " ", sentence).strip()


def convert(source: dict, book_id: str) -> dict:
    guide = source.get("pronunciation_guide", {})
    key = " · ".join(f"{sound} = {meaning}" for sound, meaning in guide.get("key", {}).items())
    parts = []
    for part in source["parts"]:
        chapters = []
        for chapter in part["chapters"]:
            practice = []
            for index, item in enumerate(chapter.get("practice", []), 1):
                accepted = accepted_answers(item)
                converted = {
                    "id": f"g{chapter['id']}-{index}",
                    "type": item["type"],
                    "prompt": item["prompt"],
                    "answer": item["answer"],
                    "acceptedAnswers": accepted,
                    "sentence": full_sentence(item, accepted),
                }
                if item.get("options"):
                    converted["options"] = item["options"]
                if item.get("explanation"):
                    converted["explanation"] = item["explanation"]
                practice.append(converted)

            rules = []
            for rule in chapter.get("rules", []):
                converted = {
                    "title": rule["title"],
                    "explanation": rule["explanation"],
                    "examples": [example(e) for e in rule.get("examples", [])],
                }
                if rule.get("table"):
                    converted["table"] = rule["table"]
                rules.append(converted)

            chapters.append({
                "id": chapter["id"],
                "title": chapter["title"],
                "level": chapter.get("level"),
                "summary": chapter["summary"],
                "keyTakeaway": chapter.get("key_takeaway"),
                "rules": rules,
                "commonMistakes": [
                    {"wrong": m["wrong"], "right": m["right"], "pronunciation": m.get("pron"),
                     "english": m["en"], "why": m["why"]}
                    for m in chapter.get("common_mistakes", [])
                ],
                "practice": practice,
            })
        parts.append({"id": part["id"], "title": part["title"],
                      "subtitle": part.get("description"), "chapters": chapters})

    return {
        "schemaVersion": 1,
        "id": book_id,
        "kind": "grammar",
        "title": source["title"],
        "subtitle": source.get("subtitle"),
        "version": str(source.get("version", "1")),
        "levelRange": source.get("level_range"),
        "howToUse": source.get("how_to_use"),
        "pronunciationGuide": " ".join(filter(None, [guide.get("description"), key and f"Key: {key}"])),
        "parts": parts,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("source", type=Path)
    parser.add_argument("--output", type=Path, default=ROOT / "books" / "essential-grammar.json")
    parser.add_argument("--id", default="essential-grammar")
    args = parser.parse_args()

    book = convert(json.loads(args.source.read_text(encoding="utf-8")), args.id)
    args.output.write_text(json.dumps(book, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    chapters = [c for p in book["parts"] for c in p["chapters"]]
    items = [q for c in chapters for q in c["practice"]]
    print(f"Wrote {args.output.relative_to(ROOT) if args.output.is_relative_to(ROOT) else args.output}: "
          f"{len(chapters)} chapters, {len(items)} practice items")
    for item in items:
        if len(item["acceptedAnswers"]) > 1:
            print(f"  {item['id']}: accepts {item['acceptedAnswers']}")


if __name__ == "__main__":
    sys.exit(main())
