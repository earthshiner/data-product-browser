# Rebrand: data-product-guide → data-product-browser

## Why

The repository's purpose has shifted from a fixed artefact *generator* to a
general-purpose **Data Product Browser** — a human-facing way to explore an
AI-Native Data Product that does not depend on an AI client being present. The
old name no longer reflects that direction, so the project, package, and CLI
are renamed to match.

## What changed

### Infrastructure
- GitHub repo renamed `ai-native-data-product-guide` → `data-product-browser`
  (GitHub auto-redirects the old URL).
- Git remote URL updated.
- Local working folder renamed.

### Code rebrand
- Python package `src/data_product_guide/` → `src/data_product_browser/`
  (renamed via `git mv`, history preserved).
- CLI script `data-product-guide` → `data-product-browser`.
- Keyring service name updated to `data-product-browser`.
- `pyproject.toml` project name + wheel package; `uv.lock` regenerated.
- All internal imports, docstrings, README, and `.env*` examples updated.

### Bundled fix
- Pre-existing working-tree edits committed as their own checkpoint:
  timestamp fields renamed `_at` → `_dts` (Teradata convention), which also
  fixes the `measured_at` model field vs `measured_dts` query mismatch.

## ⚠️ Breaking change

The keyring service name changed, so any password stored under the old name is
no longer found. Users re-store once:

```
data-product-browser store-password
```

## Verification

- `uv run pytest` — 27 passed.
- `uv run data-product-browser --help` — new command resolves.
- `uv run ruff format src/` — clean.

## Commits

1. `refactor(models): align timestamp fields to _dts naming convention`
2. `refactor: rebrand package to data-product-browser`
