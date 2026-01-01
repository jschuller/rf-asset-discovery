# Medallion Architecture Template

Cookiecutter template for creating data lakehouse projects with Bronze → Silver → Gold architecture.

## Usage

```bash
# Install cookiecutter
pip install cookiecutter

# Generate project from template
cookiecutter medallion-template/

# Or from GitHub
cookiecutter gh:jschuller/sdr-toolkit --directory="medallion-template"
```

## What You Get

```
your_project/
├── src/your_project/
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

1. Edit `storage/classification.py` with your domain mappings
2. Define quality gates in `apps/transform.py`
3. Add domain-specific enums in `storage/models.py`

## Based On

This template is extracted from the SDR Toolkit project. See:
- `docs/MEDALLION-PATTERN.md` for pattern documentation
- `docs/LESSONS-LEARNED.md` for best practices
