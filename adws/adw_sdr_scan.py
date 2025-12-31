#!/usr/bin/env python3
"""Agentic spectrum scan workflow.

This workflow uses Claude Code to intelligently scan the RF spectrum,
identify signals, and provide analysis.

Workflow phases:
1. PLAN: Determine optimal scan parameters based on user intent
2. EXECUTE: Run the spectrum scan with SDR toolkit
3. VERIFY: Validate results and classify signals
4. COMPLETE: Generate report and save results
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from adws.adw_modules.agent import (
    AgentRequest,
    generate_adw_id,
    run_claude_agent,
)
from adws.adw_modules.data_models import (
    ScanResult,
    ScanTask,
    TaskStatus,
    WorkflowConfig,
    WorkflowPhase,
    WorkflowState,
)
from adws.adw_modules.utils import (
    generate_report,
    save_scan_result,
    save_workflow_state,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def create_scan_prompt(task: ScanTask) -> str:
    """Create the prompt for the scan agent."""
    return f"""You are an SDR spectrum scanning agent. Your task is to scan the RF spectrum and identify signals.

## Task
{task.description}

## Parameters
- Start Frequency: {task.start_freq_mhz} MHz
- End Frequency: {task.end_freq_mhz} MHz
- Step Size: {task.step_khz} kHz
- Detection Threshold: {task.threshold_db} dB

## Instructions

1. Use the SDR toolkit to perform the spectrum scan:
   ```python
   from sdr_toolkit.apps import SpectrumScanner

   scanner = SpectrumScanner(threshold_db={task.threshold_db})
   result = scanner.scan({task.start_freq_mhz}e6, {task.end_freq_mhz}e6, step_hz={task.step_khz}e3)
   ```

2. Analyze the detected signals and classify them by type (FM broadcast, narrowband, etc.)

3. Report the findings including:
   - Number of signals detected
   - Strongest signals with frequencies and power levels
   - Signal classifications
   - Noise floor estimate

4. Save the results to a JSON file.

Provide a concise summary of the scan results.
"""


def run_scan_workflow(
    start_freq_mhz: float,
    end_freq_mhz: float,
    description: str = "Spectrum scan",
    step_khz: float = 200,
    threshold_db: float = -30,
    config: WorkflowConfig | None = None,
) -> WorkflowState:
    """Run the agentic spectrum scan workflow.

    Args:
        start_freq_mhz: Start frequency in MHz.
        end_freq_mhz: End frequency in MHz.
        description: Task description.
        step_khz: Step size in kHz.
        threshold_db: Detection threshold in dB.
        config: Workflow configuration.

    Returns:
        WorkflowState with results.
    """
    config = config or WorkflowConfig()
    adw_id = generate_adw_id("adw_sdr_scan")

    # Initialize workflow state
    state = WorkflowState(
        adw_id=adw_id,
        workflow_type="scan",
    )
    state.log(f"Starting scan workflow: {start_freq_mhz}-{end_freq_mhz} MHz")

    # Create task
    task = ScanTask(
        adw_id=adw_id,
        description=description,
        start_freq_mhz=start_freq_mhz,
        end_freq_mhz=end_freq_mhz,
        step_khz=step_khz,
        threshold_db=threshold_db,
    )
    state.current_task = task

    # Phase 1: Plan
    state.log("Phase 1: Planning scan parameters")
    state.phase = WorkflowPhase.PLAN

    # For scans, we can skip the planning phase if parameters are explicit
    state.log(f"Using parameters: {start_freq_mhz}-{end_freq_mhz} MHz, step={step_khz} kHz")
    state.advance_phase()

    # Phase 2: Execute
    state.log("Phase 2: Executing spectrum scan")

    # Create agent request
    prompt = create_scan_prompt(task)
    request = AgentRequest(
        prompt=prompt,
        adw_id=adw_id,
        model=config.model,
        max_turns=15,
        timeout_seconds=config.timeout_seconds,
        working_dir=Path.cwd(),
    )

    # Run agent
    response = run_claude_agent(request)

    if not response.success:
        state.fail(response.error or "Agent execution failed")
        logger.error("Scan workflow failed: %s", response.error)
        return state

    state.log(f"Agent completed in {response.num_turns} turns, cost: ${response.cost_usd:.4f}")
    state.advance_phase()

    # Phase 3: Verify
    state.log("Phase 3: Verifying results")

    # Parse results from agent output
    # In a real implementation, we'd parse the JSON output
    # For now, create a placeholder result
    scan_result = ScanResult(
        adw_id=adw_id,
        start_freq_mhz=start_freq_mhz,
        end_freq_mhz=end_freq_mhz,
        peaks=[],  # Would be populated from agent output
        scan_time_seconds=response.duration_ms / 1000,
    )
    state.results.append(scan_result)

    state.advance_phase()

    # Phase 4: Complete
    state.complete()

    # Save results
    if config.save_results:
        output_dir = config.output_dir / adw_id
        save_workflow_state(state, output_dir)
        save_scan_result(scan_result, output_dir)
        state.log(f"Results saved to {output_dir}")

    # Generate and log report
    report = generate_report(scan_result=scan_result)
    logger.info("\n%s", report)

    return state


def run_fm_scan_workflow(config: WorkflowConfig | None = None) -> WorkflowState:
    """Run a scan of the FM broadcast band (87.5-108 MHz).

    Args:
        config: Workflow configuration.

    Returns:
        WorkflowState with results.
    """
    return run_scan_workflow(
        start_freq_mhz=87.5,
        end_freq_mhz=108.0,
        description="FM broadcast band scan",
        step_khz=200,
        threshold_db=-30,
        config=config,
    )


def main() -> int:
    """CLI entry point for scan workflow."""
    parser = argparse.ArgumentParser(description="Agentic Spectrum Scan Workflow")
    parser.add_argument(
        "-s", "--start", type=float, default=87.5, help="Start frequency in MHz"
    )
    parser.add_argument(
        "-e", "--end", type=float, default=108.0, help="End frequency in MHz"
    )
    parser.add_argument(
        "--step", type=float, default=200, help="Step size in kHz"
    )
    parser.add_argument(
        "-t", "--threshold", type=float, default=-30, help="Detection threshold in dB"
    )
    parser.add_argument(
        "--model", choices=["sonnet", "opus", "haiku"], default="sonnet", help="Model to use"
    )
    parser.add_argument(
        "-o", "--output", type=str, default="./adw_outputs", help="Output directory"
    )
    parser.add_argument(
        "--fm", action="store_true", help="Quick scan of FM band"
    )

    args = parser.parse_args()

    config = WorkflowConfig(
        model=args.model,
        output_dir=Path(args.output),
    )

    if args.fm:
        state = run_fm_scan_workflow(config)
    else:
        state = run_scan_workflow(
            start_freq_mhz=args.start,
            end_freq_mhz=args.end,
            step_khz=args.step,
            threshold_db=args.threshold,
            config=config,
        )

    if state.status == TaskStatus.COMPLETED:
        print(f"\nWorkflow completed successfully: {state.adw_id}")
        return 0
    else:
        print(f"\nWorkflow failed: {state.error}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
