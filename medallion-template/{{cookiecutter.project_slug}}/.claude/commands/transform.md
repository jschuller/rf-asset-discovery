---
description: Run medallion transformation pipeline
---

# Transform Command

Runs the Bronze → Silver → Gold transformation pipeline.

## Usage

```
/transform
```

## What It Does

1. Shows current layer counts (bronze/silver/gold)
2. Runs bronze_to_silver transformation with validation
3. Runs silver_to_gold transformation with enrichment
4. Reports final counts and promotion rates

## Example Output

```
Current state:
  Bronze: 10,000
  Silver: 500
  Gold:   50

Running transformation pipeline...
  ✓ bronze_to_silver: 10,000 → 8,500 (1.23s)
  ✓ silver_to_gold: 8,500 → 1,200 (0.45s)

Final state:
  Bronze: 10,000
  Silver: 8,500
  Gold:   1,200
```

## Implementation

```bash
uv run {{ cookiecutter.project_slug }}-transform
```
