# Svenska 101 — content

The learning material read by the Svenska 101 app. Edit a file here, commit, and the app
picks it up the next time it opens (or when you pull down on the Learn tab).

> GitHub's raw file server caches for about 5 minutes, so a fresh edit can take a few
> minutes to show up in the app.

## Files

| Path | What it is |
| --- | --- |
| `books/essential-650.json` | The vocabulary book (words, pronunciation, example sentences) |
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

## Using AI to add content

Paste an existing entry as an example and ask for new entries "in exactly this JSON format,
with unique ids". Then run `python3 scripts/validate.py` (or just push and check Actions).
