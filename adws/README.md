# RF Asset Discovery - Agentic Developer Workflows

Autonomous spectrum monitoring, plus helpers for running Claude Code from Python.

The earlier scan, record and analyze ADW scripts were folded into the
`/survey` and `/capture` slash commands; `adw_spectrum_watch.py` is the one
workflow left in this package.

## Workflow

| Module | Purpose | Usage |
|--------|---------|-------|
| `adw_spectrum_watch.py` | Continuous watch: baseline, then alerts | `uv run rfad-watch --band fm` (see `uv run rfad-watch --help`) |

`rfad-watch` is the command-line entry point (`rf_asset_discovery.cli.main:spectrum_watch`).

## Core Modules

| Module | Purpose |
|--------|---------|
| `adw_modules/watch_config.py` | Pydantic models (`WatchConfig`, `AlertCondition`, `Alert`, `WatchState`), bands and notable frequencies, natural-language parsing |
| `adw_modules/baseline.py` | `SpectrumBaseline` (signals and power of one range) and `RangeBaselines` (one baseline per scanned range) |
| `adw_modules/notifier.py` | Notification backends: ntfy.sh, console, `MultiBackend` |
| `adw_modules/observability.py` | Audit logging (JSON Lines), compliance awareness, session statistics |
| `adw_modules/agent.py` | Claude Code CLI execution (`AgentRequest`, `run_claude_agent`) |

## Observability Features

1. **Audit Logging** - JSON Lines format (`AuditLogger`, default `audit.jsonl`; a watch writes `watch_audit.jsonl`)
2. **Compliance Awareness** - Frequency band classification (informational only)
3. **Session Statistics** - `SessionStats` tracks scans, recordings and frequencies

## Integration Pattern

```python
import asyncio

from adws import watch_band
from adws.adw_modules import (
    AgentRequest,
    AuditLogger,
    ComplianceChecker,
    FrequencyBand,
    generate_adw_id,
    run_claude_agent,
)

# Start a watch (needs an RTL-SDR); it runs until stopped
async def main() -> None:
    watch = await watch_band(FrequencyBand.AIRCRAFT_VHF, ntfy_topic="my-sdr-alerts")
    await asyncio.sleep(600)
    await watch.stop()

asyncio.run(main())

# Execute an agentic workflow through the Claude Code CLI
response = run_claude_agent(
    AgentRequest(
        prompt="Scan FM band and identify strongest signals",
        adw_id=generate_adw_id("adw_scan"),
        allowed_tools=["Bash", "Read", "Write"],
    )
)
print(response.success, response.output)

# Log operation
logger = AuditLogger()
logger.log_scan(
    adw_id="adw_scan_001",
    start_freq_hz=87.5e6,
    end_freq_hz=108e6,
    num_signals=15,
    duration_seconds=30.5,
)

# Check frequency (informational only)
checker = ComplianceChecker()
is_known, message = checker.check_frequency(100.1)
# Returns: (True, "Legal: FM Broadcast")
```

## Compliance Note

The observability module provides **awareness** of frequency regulations, not restrictions. The toolkit can discover ALL signals. Users are responsible for compliance with local laws.
