# RF Asset Discovery - Agentic Developer Workflows

AI-driven SDR operations using Claude Code CLI.

## Workflows

| Script | Purpose | Usage |
|--------|---------|-------|
| `adw_sdr_scan.py` | Spectrum scanning | `uv run adw_sdr_scan.py 87.5 108.0` |
| `adw_sdr_record.py` | Signal recording | `uv run adw_sdr_record.py 101.9 30` |
| `adw_sdr_analyze.py` | Recording analysis | `uv run adw_sdr_analyze.py recording.sigmf-meta` |

## Core Modules

| Module | Purpose |
|--------|---------|
| `adw_modules/agent.py` | Claude Code CLI execution |
| `adw_modules/data_models.py` | Pydantic models (SDRTask, ScanResult) |
| `adw_modules/observability.py` | Audit logging, compliance awareness |

## Observability Features

1. **Audit Logging** - JSON Lines format (`audit.jsonl`)
2. **Compliance Awareness** - Frequency band classification (informational only)
3. **Session Statistics** - Track scans, recordings, frequencies

## Integration Pattern

```python
from adws.adw_modules import (
    run_claude_agent,
    AuditLogger,
    ComplianceChecker,
)

# Execute agentic workflow
result = run_claude_agent(
    prompt="Scan FM band and identify strongest signals",
    allowed_tools=["Bash", "Read", "Write"],
)

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
