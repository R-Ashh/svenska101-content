# Svenska 101 — content

The learning material read by the Svenska 101 app. Edit a file here, commit, and the app
picks it up the next time it opens (or when you pull down on the Learn tab).

> GitHub's raw file server caches for about 5 minutes, so a fresh edit can take a few
> minutes to show up in the app.

## Files

| Path | What it is |
| --- | --- |
| `books/essential-650.json` | The vocabulary book (words, pronunciation, example sentences) |
| `books/essential-grammar.json` | The grammar book (chapters, rules, tables, common mistakes, practice) |
| `scripts/import_grammar.py` | Converts an AI-written grammar file into the app's format |
| `audio/` | Recorded / neural-voice audio clips (optional — the app falls back to the phone's voice) |
| `scripts/validate.py` | Checks the books for mistakes; runs automatically on every push |

## Editing from your phone

1. Open the file on github.com → tap the **pencil** (Edit) icon.
2. Make the change → **Commit changes**.
3. Check the **Actions** tab: a green tick means the book is valid. A red cross lists what's
   wrong — the app keeps using its last good copy until it's fixed.

## Entry format

```json
{
  "id": "jag",
  "swedish": "jag",
  "english": "I",
  "pronunciation": "yah",
  "isNew": false,
  "notes": ["Optional usage note"],
  "examples": [
    { "swedish": "Jag heter Anna.", "english": "My name is Anna.", "pronunciation": "yah hehtehr annah." }
  ]
}
```

- **`id` must be unique and should never change** — your learning progress is linked to it.
  For a new word, use the Swedish word in lowercase with `-` instead of spaces (e.g. `god-morgon`).
- `pronunciation` is optional. `notes` and `examples` can be empty lists `[]`.
- Words separated by `/` (e.g. `de/dom`) are all accepted as correct answers in writing practice.
- Sections live inside parts: `parts → sections → entries`. Add a new section by copying an
  existing one and giving it a new `id`.
- Bump the top-level `version` (any text, e.g. a date) so you can see in the app's Settings which
  copy it has loaded.

## Grammar book format

`parts → chapters → rules / commonMistakes / practice`. A practice item:

```json
{
  "id": "g1.1-2",
  "type": "choose",
  "prompt": "___ lägenhet",
  "options": ["en", "ett"],
  "answer": "en",
  "acceptedAnswers": ["en"],
  "explanation": "Words ending in -het are en-words."
}
```

- `type` is one of `fill_in`, `choose`, `translate_to_swedish`, `correct_the_error`, `reorder`
  (reorder prompts list the words separated by ` / `).
- `answer` is what the app shows; `acceptedAnswers` is everything it accepts as right. An empty
  string `""` in `acceptedAnswers` means leaving the gap empty is also right.
- **Practice `id`s must be unique and should never change** — progress is linked to them.
- Rules can have an optional `table`: `{ "headers": [...], "rows": [[...], ...] }`.

A new grammar file written by an AI in the original format (`sv`/`pron`/`en`, `key_takeaway`, …)
can be converted with `python3 scripts/import_grammar.py <file> --output books/<name>.json`.

## Natural-voice audio

`scripts/generate_audio.py` creates a clip for every word and example sentence, and links the
book to `audio/manifest.json`. The app plays these clips and falls back to the phone's voice for
anything without one. Only missing clips are generated, so re-run it after adding content.

1. Create a free **Speech** resource in the [Azure portal](https://portal.azure.com) (free tier
   F0: 0.5M characters/month — the whole book is about 30,000).
2. Run:
   ```sh
   export AZURE_SPEECH_KEY=<key>  AZURE_SPEECH_REGION=<region, e.g. swedencentral>
   python3 scripts/generate_audio.py                 # voice: sv-SE-SofieNeural
   # or: --voice sv-SE-MattiasNeural (male) / sv-SE-HilleviNeural
   ```
3. Commit `audio/` and `books/`, push. In the app: Settings → Natural voice →
   "Download all for offline" if you want it to work without internet.

Clips are keyed by their exact text, so editing a sentence automatically falls back to the
phone's voice until you re-run the script. Add `--prune` to delete clips no longer used.

## Using AI to add content

Paste an existing entry as an example and ask for new entries "in exactly this JSON format,
with unique ids". Then run `python3 scripts/validate.py` (or just push and check Actions).
