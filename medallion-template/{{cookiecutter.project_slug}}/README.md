# {{ cookiecutter.project_name }}

{{ cookiecutter.description }}

## Setup

```bash
# Install dependencies
uv sync --all-extras

# Or with pip
pip install -e ".[dev]"
```

## Usage

```bash
# Run transformation pipeline
uv run {{ cookiecutter.project_slug }}-transform
```

## Architecture

This project uses the **Medallion Architecture** pattern:

```
Bronze (Raw) → Silver (Validated) → Gold (Enriched)
```

| Layer | Table | Purpose |
|-------|-------|---------|
| Bronze | `{{ cookiecutter.bronze_table }}` | Raw ingested data |
| Silver | `{{ cookiecutter.silver_table }}` | Validated, deduplicated |
| Gold | `{{ cookiecutter.gold_table }}` | Enriched, production-ready |

## Project Structure

```
{{ cookiecutter.project_slug }}/
├── src/{{ cookiecutter.project_slug }}/
│   ├── apps/
│   │   └── transform.py      # MedallionTransformer
│   └── storage/
│       ├── classification.py # Domain mapping
│       └── models.py         # Domain enums
├── .claude/
│   ├── CLAUDE.md             # Dev instructions
│   └── commands/
│       └── transform.md      # Transform skill
├── data/                     # DuckDB storage
├── pyproject.toml
└── README.md
```

## Customization

1. **Define your domain enums** in `storage/models.py`
2. **Create classification mappings** in `storage/classification.py`
3. **Implement quality gates** by overriding transform methods

## Development

```bash
# Run tests
pytest tests/ -v

# Lint
ruff check src/
```

## License

MIT
