#!/usr/bin/env python3
"""Generates natural-voice audio clips for every word and example sentence in the books.

The app plays these clips instead of the phone's built-in voice. Only missing clips are
generated, so re-running after editing a book is cheap. Clips are keyed by their exact
Swedish text: edit a sentence and its old clip stops being used automatically.

ENGINES
  azure  (default) Microsoft neural voices — very natural Swedish. The free tier (F0) covers
         0.5 million characters a month; the whole book is roughly 30,000.
         Setup: create a free "Speech" resource at https://portal.azure.com, then
           export AZURE_SPEECH_KEY=...    AZURE_SPEECH_REGION=swedencentral   (or your region)
         Voices: sv-SE-SofieNeural (female), sv-SE-MattiasNeural (male), sv-SE-HilleviNeural (female)
  say    macOS built-in voice (Alva). No account needed — handy for testing the pipeline.

USAGE
  python3 scripts/generate_audio.py                       # Azure, Sofie
  python3 scripts/generate_audio.py --voice sv-SE-MattiasNeural
  python3 scripts/generate_audio.py --engine say --base-url http://127.0.0.1:8000/audio/
  python3 scripts/generate_audio.py --prune               # also delete clips no longer used

Afterwards commit the audio/ folder and the updated book(s), and push.
"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent.parent
BOOKS = ROOT / "books"
AUDIO = ROOT / "audio"
DEFAULT_BASE_URL = "https://raw.githubusercontent.com/R-Ashh/svenska101-content/main/audio/"


def speakable_word(swedish: str) -> str:
    # Must match Entry.speakableWord in the app: "de/dom" is read as "de, dom".
    return swedish.replace("/", ", ")


def collect_texts() -> list[str]:
    texts: list[str] = []
    for path in sorted(BOOKS.glob("*.json")):
        book = json.loads(path.read_text(encoding="utf-8"))
        for part in book.get("parts", []):
            # Grammar books: rule examples, corrected mistakes and practice answers.
            for chapter in part.get("chapters", []):
                for rule in chapter.get("rules", []):
                    texts.extend(example["swedish"] for example in rule.get("examples", []))
                texts.extend(mistake["right"] for mistake in chapter.get("commonMistakes", []))
                texts.extend(item["sentence"] for item in chapter.get("practice", []) if item.get("sentence"))
            for section in part.get("sections", []):
                for entry in section.get("entries", []):
                    texts.append(speakable_word(entry["swedish"]))
                    texts.extend(example["swedish"] for example in entry.get("examples", []))
    # Keep order, drop duplicates.
    return list(dict.fromkeys(t.strip() for t in texts if t.strip()))


def clip_name(voice: str, text: str, extension: str) -> str:
    digest = hashlib.sha1(f"{voice}\n{text}".encode("utf-8")).hexdigest()[:16]
    return f"{voice}/{digest}.{extension}"


def synthesize_azure(text: str, voice: str, output: Path) -> None:
    key = os.environ.get("AZURE_SPEECH_KEY")
    region = os.environ.get("AZURE_SPEECH_REGION")
    if not key or not region:
        sys.exit("Set AZURE_SPEECH_KEY and AZURE_SPEECH_REGION first (see the top of this script).")
    ssml = (
        "<speak version='1.0' xml:lang='sv-SE'>"
        f"<voice name='{voice}'>{escape(text)}</voice></speak>"
    )
    request = urllib.request.Request(
        f"https://{region}.tts.speech.microsoft.com/cognitiveservices/v1",
        data=ssml.encode("utf-8"),
        headers={
            "Ocp-Apim-Subscription-Key": key,
            "Content-Type": "application/ssml+xml",
            "X-Microsoft-OutputFormat": "audio-24khz-48kbitrate-mono-mp3",
            "User-Agent": "svenska101-audio",
        },
    )
    for attempt in range(5):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                output.write_bytes(response.read())
            return
        except urllib.error.HTTPError as error:
            if error.code == 429 and attempt < 4:  # free tier rate limit — back off and retry
                time.sleep(2 ** attempt)
                continue
            raise


def synthesize_say(text: str, voice: str, output: Path) -> None:
    with tempfile.TemporaryDirectory() as folder:
        aiff = Path(folder) / "clip.aiff"
        subprocess.run(["say", "-v", voice, "-o", str(aiff), text], check=True)
        subprocess.run(["afconvert", "-f", "m4af", "-d", "aac", str(aiff), str(output)], check=True)


def link_books(manifest_url: str) -> None:
    for path in sorted(BOOKS.glob("*.json")):
        book = json.loads(path.read_text(encoding="utf-8"))
        if book.get("audioManifest") != manifest_url:
            book["audioManifest"] = manifest_url
            path.write_text(json.dumps(book, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            print(f"Linked {path.name} → {manifest_url}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--engine", choices=["azure", "say"], default="azure")
    parser.add_argument("--voice", help="Azure voice name, or macOS voice for --engine say (default Alva)")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="Public URL of the audio/ folder")
    parser.add_argument("--prune", action="store_true", help="Delete clips that are no longer used")
    parser.add_argument("--limit", type=int, help="Only generate this many new clips (for a quick try)")
    args = parser.parse_args()

    voice = args.voice or ("sv-SE-SofieNeural" if args.engine == "azure" else "Alva")
    extension = "mp3" if args.engine == "azure" else "m4a"
    synthesize = synthesize_azure if args.engine == "azure" else synthesize_say
    if args.engine == "say" and not shutil.which("say"):
        sys.exit("--engine say only works on macOS.")

    texts = collect_texts()
    files: dict[str, str] = {}
    created = 0
    for index, text in enumerate(texts, 1):
        name = clip_name(voice, text, extension)
        path = AUDIO / name
        if not path.exists():
            if args.limit is not None and created >= args.limit:
                continue
            path.parent.mkdir(parents=True, exist_ok=True)
            print(f"[{index}/{len(texts)}] {text}")
            synthesize(text, voice, path)
            created += 1
        files[text] = name

    base_url = args.base_url if args.base_url.endswith("/") else args.base_url + "/"
    manifest = {"voice": voice, "baseURL": base_url, "files": files}
    AUDIO.mkdir(exist_ok=True)
    (AUDIO / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")

    if args.prune:
        used = {AUDIO / name for name in files.values()}
        for clip in AUDIO.glob("*/*.*"):
            if clip not in used:
                clip.unlink()
                print(f"Removed unused {clip.relative_to(AUDIO)}")

    link_books(base_url + "manifest.json")
    print(f"Done: {created} new clips, {len(files)} in the manifest ({len(texts)} texts).")


if __name__ == "__main__":
    main()
