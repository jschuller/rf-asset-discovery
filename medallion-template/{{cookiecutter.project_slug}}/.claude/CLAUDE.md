# CLAUDE.md

{{ cookiecutter.project_name }}: Medallion Architecture Data Project

## Setup

```bash
uv sync --all-extras
```

## Commands

```bash
# Run transformation pipeline
uv run {{ cookiecutter.project_slug }}-transform
```

## Skills

```
/transform    Run Bronze → Silver → Gold pipeline
```

## Schema

| Layer | Table | Purpose |
|-------|-------|---------|
| Bronze | `{{ cookiecutter.bronze_table }}` | Raw ingested data |
| Silver | `{{ cookiecutter.silver_table }}` | Validated, deduplicated |
| Gold | `{{ cookiecutter.gold_table }}` | Enriched, production-ready |

**Quality Gates:**
- Bronze → Silver: Validation (nulls, duplicates, schema)
- Silver → Gold: Enrichment (classification, risk assessment)

## Architecture

```
src/{{ cookiecutter.project_slug }}/
├── apps/
│   └── transform.py      # MedallionTransformer
├── storage/
│   ├── classification.py # Domain mapping
│   └── models.py         # Domain enums
└── cli.py                # CLI entry points

data/
└── {{ cookiecutter.project_slug }}.duckdb  # Persistent storage
```

## Key Patterns

```python
# Always use context managers
with MedallionTransformer(db_path) as transformer:
    results = transformer.run_full_pipeline()

# Classification from Python dict → SQL CASE
from {{ cookiecutter.project_slug }}.storage.classification import CATEGORY_CASE_SQL
```

## Customization

1. Edit `storage/models.py` with your domain enums
2. Edit `storage/classification.py` with your domain mappings
3. Override `bronze_to_silver()` and `silver_to_gold()` in transform.py

## Tests

```bash
pytest tests/ -v
```
