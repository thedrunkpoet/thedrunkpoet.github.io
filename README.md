# thedrunkpoet.com

Static journal. Entries are markdown files in `scribe/entries/` named `YYYY-MM-DD-slug.md`.

Build and preview:

    python3 -m venv .venv && .venv/bin/pip install markdown   # once
    cd scribe && ../.venv/bin/python build.py && python3 -m http.server -d dist 8000
