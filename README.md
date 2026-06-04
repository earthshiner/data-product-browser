# ai-native-data-product-guide

Generate AI-Native Data Product artefacts (Cookbook, Ops Dashboard) deterministically from Teradata metadata.

## Quick start

```bash
cp .env.example .env   # fill in TD_HOST, TD_USER, TD_PASSWORD
uv sync
tdp-reporter generate MortgagePlatform --output ./output
```

## Commands

| Command | Description |
|---|---|
| `generate <product>` | Connect to Teradata, collect metadata, write HTML artefacts |
| `dump <product>` | Collect metadata and save as JSON snapshot (no HTML) |
| `render <snapshot.json>` | Render HTML from a previously saved JSON snapshot |

## Options

`--artefact all|cookbook|ops` — which artefacts to generate (default: `all`)  
`--output <dir>` — output directory (default: `.`)  
`--lookback <days>` — Observability window in days (default: `90`)

## Running tests

```bash
uv run pytest
```

