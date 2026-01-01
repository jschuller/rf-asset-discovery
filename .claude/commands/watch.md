---
description: Autonomous spectrum monitoring with alerts
allowed-tools: Bash, Read, Write, Grep
---

Monitor spectrum continuously, alert on changes.

## Usage
`/watch` or `/watch aircraft` or `/watch "Watch 121.5 MHz emergency"`

## Commands
```bash
# Preset bands
uv run rfad-watch --band fm
uv run rfad-watch --band aircraft
uv run rfad-watch --band marine

# Natural language
uv run rfad-watch "Watch aircraft band, alert on 121.5 MHz"
uv run rfad-watch "Monitor 433 MHz for new signals"

# With ntfy.sh notifications
uv run rfad-watch --band aircraft --ntfy sdr-alerts

# Specific frequency
uv run rfad-watch --freq 121.5
```

## Alert Types
- `new_signal` - Signal not in baseline
- `threshold_breach` - Power exceeds threshold
- `signal_loss` - Expected signal missing
- `band_activity` - Activity level change

## Environment
```bash
export DYLD_LIBRARY_PATH=/opt/homebrew/lib
```
