# Cookbook tab

Targets `main`. Final tab of the browser build.

## What

A **Cookbook** nav view rendering `Query_Cookbook` recipes as ready-to-run query
templates straight from the standard's Memory module.

- Each recipe: title, description, use case, complexity + target-module pills,
  parameter descriptions and performance notes.
- SQL shown in a syntax-highlighted code block — a small client-side highlighter
  wraps keywords, strings, numbers and comments (no library).
- **Copy SQL** button per recipe (copies the raw template) with copied-feedback.
- Live text search across recipe title/description/use-case/module/SQL.

## Verification

- `uv run pytest` — 15 passed; `ruff`/`node --check` clean.
- Rendered end-to-end via the preview harness (seeded with SIMPLE + COMPLEX
  recipes): syntax highlighting, complexity pills, copy buttons, and live search
  (filtered 2 → 1) all working. No console errors.

## Browser build complete

1 plumbing · 2 shell · 3 cross-linking · 4 operations · 5 ERD · 6 cookbook — all done.
