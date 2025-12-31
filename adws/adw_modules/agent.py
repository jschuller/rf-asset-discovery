"""Claude Code agent execution module for SDR workflows.

Adapted from IndyDevDan's TAC-8 patterns for agentic developer workflows.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Literal

logger = logging.getLogger(__name__)


class RetryCode(str, Enum):
    """Codes indicating different types of errors that may be retryable."""

    NONE = "none"
    TIMEOUT = "timeout"
    EXECUTION_ERROR = "execution_error"
    CLAUDE_ERROR = "claude_error"


@dataclass
class AgentRequest:
    """Request configuration for Claude Code agent execution."""

    prompt: str
    adw_id: str
    model: Literal["sonnet", "opus", "haiku"] = "sonnet"
    max_turns: int = 10
    allowed_tools: list[str] | None = None
    working_dir: Path | None = None
    timeout_seconds: int = 300
    output_format: Literal["json", "text"] = "json"


@dataclass
class AgentResponse:
    """Response from Claude Code agent execution."""

    success: bool
    output: str
    session_id: str | None = None
    duration_ms: int = 0
    cost_usd: float = 0.0
    num_turns: int = 0
    retry_code: RetryCode = RetryCode.NONE
    error: str | None = None
    raw_output: str = ""


@dataclass
class ClaudeMessage:
    """Parsed message from Claude Code JSONL output."""

    type: str
    subtype: str = ""
    content: str = ""
    is_error: bool = False
    extra: dict[str, Any] = field(default_factory=dict)


def generate_adw_id(prefix: str = "adw_sdr") -> str:
    """Generate a unique ADW ID for workflow tracking.

    Args:
        prefix: Prefix for the ID (e.g., "adw_sdr_scan").

    Returns:
        Unique ID like "adw_sdr_scan_20241230_143022_a1b2c3d4"
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    short_uuid = str(uuid.uuid4())[:8]
    return f"{prefix}_{timestamp}_{short_uuid}"


def get_safe_env() -> dict[str, str]:
    """Get filtered environment variables safe for subprocess execution."""
    safe_vars = {
        "ANTHROPIC_API_KEY": os.getenv("ANTHROPIC_API_KEY"),
        "HOME": os.getenv("HOME"),
        "USER": os.getenv("USER"),
        "PATH": os.getenv("PATH"),
        "SHELL": os.getenv("SHELL"),
        "TERM": os.getenv("TERM"),
        "LANG": os.getenv("LANG"),
        "DYLD_LIBRARY_PATH": os.getenv("DYLD_LIBRARY_PATH"),  # For macOS rtl-sdr
        "PYTHONPATH": os.getenv("PYTHONPATH"),
        "PYTHONUNBUFFERED": "1",
        "PWD": os.getcwd(),
    }
    return {k: v for k, v in safe_vars.items() if v is not None}


def parse_jsonl_output(output: str) -> tuple[list[ClaudeMessage], ClaudeMessage | None]:
    """Parse JSONL output from Claude Code CLI.

    Args:
        output: Raw JSONL output string.

    Returns:
        Tuple of (all messages, final result message or None).
    """
    messages: list[ClaudeMessage] = []
    result_message: ClaudeMessage | None = None

    for line in output.strip().split("\n"):
        if not line.strip():
            continue

        try:
            data = json.loads(line)
            msg = ClaudeMessage(
                type=data.get("type", ""),
                subtype=data.get("subtype", ""),
                content=data.get("result", data.get("content", "")),
                is_error=data.get("is_error", False),
                extra=data,
            )
            messages.append(msg)

            # Check for result message
            if msg.type == "result":
                result_message = msg

        except json.JSONDecodeError:
            logger.warning("Failed to parse JSONL line: %s", line[:100])
            continue

    return messages, result_message


def run_claude_agent(request: AgentRequest) -> AgentResponse:
    """Execute Claude Code CLI with the given request.

    Args:
        request: Agent request configuration.

    Returns:
        AgentResponse with execution results.
    """
    claude_path = os.getenv("CLAUDE_CODE_PATH", "claude")

    # Build command
    cmd = [
        claude_path,
        "--print",
        "--output-format",
        request.output_format,
        "--model",
        request.model,
        "--max-turns",
        str(request.max_turns),
    ]

    if request.allowed_tools:
        cmd.extend(["--allowedTools", ",".join(request.allowed_tools)])

    cmd.append(request.prompt)

    logger.info("Executing agent [%s]: %s...", request.adw_id, request.prompt[:50])

    # Execute
    try:
        working_dir = request.working_dir or Path.cwd()
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=request.timeout_seconds,
            cwd=str(working_dir),
            env=get_safe_env(),
        )

        raw_output = result.stdout

        # Parse output
        if request.output_format == "json":
            messages, final_msg = parse_jsonl_output(raw_output)

            if final_msg:
                return AgentResponse(
                    success=not final_msg.is_error,
                    output=final_msg.content,
                    session_id=final_msg.extra.get("session_id"),
                    duration_ms=final_msg.extra.get("duration_ms", 0),
                    cost_usd=final_msg.extra.get("total_cost_usd", 0.0),
                    num_turns=final_msg.extra.get("num_turns", 0),
                    raw_output=raw_output,
                )
            else:
                # No result message found
                return AgentResponse(
                    success=False,
                    output="No result message in output",
                    retry_code=RetryCode.EXECUTION_ERROR,
                    raw_output=raw_output,
                )
        else:
            # Text format
            return AgentResponse(
                success=result.returncode == 0,
                output=raw_output,
                raw_output=raw_output,
            )

    except subprocess.TimeoutExpired:
        logger.error("Agent timed out after %d seconds", request.timeout_seconds)
        return AgentResponse(
            success=False,
            output="",
            error=f"Timeout after {request.timeout_seconds} seconds",
            retry_code=RetryCode.TIMEOUT,
        )

    except FileNotFoundError:
        logger.error("Claude CLI not found at: %s", claude_path)
        return AgentResponse(
            success=False,
            output="",
            error=f"Claude CLI not found: {claude_path}",
            retry_code=RetryCode.CLAUDE_ERROR,
        )

    except Exception as e:
        logger.exception("Agent execution failed")
        return AgentResponse(
            success=False,
            output="",
            error=str(e),
            retry_code=RetryCode.EXECUTION_ERROR,
        )


def run_slash_command(
    command: str,
    args: list[str] | None = None,
    adw_id: str | None = None,
    model: Literal["sonnet", "opus", "haiku"] = "sonnet",
    working_dir: Path | None = None,
) -> AgentResponse:
    """Execute a slash command via Claude Code CLI.

    Args:
        command: Slash command name (without leading slash).
        args: Command arguments.
        adw_id: ADW ID for tracking (auto-generated if None).
        model: Model to use.
        working_dir: Working directory.

    Returns:
        AgentResponse with execution results.
    """
    if adw_id is None:
        adw_id = generate_adw_id(f"adw_{command}")

    # Build prompt from slash command
    prompt = f"/{command}"
    if args:
        prompt += " " + " ".join(args)

    request = AgentRequest(
        prompt=prompt,
        adw_id=adw_id,
        model=model,
        working_dir=working_dir,
    )

    return run_claude_agent(request)
