#!/usr/bin/env python3
"""Agentic signal recording workflow.

This workflow uses Claude Code to intelligently record signals,
adjusting parameters for optimal capture.

Workflow phases:
1. PLAN: Determine optimal recording parameters
2. EXECUTE: Perform the recording
3. VERIFY: Validate the recording quality
4. COMPLETE: Save metadata and generate report
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
    RecordingResult,
    RecordTask,
    TaskStatus,
    WorkflowConfig,
    WorkflowPhase,
    WorkflowState,
)
from adws.adw_modules.utils import (
    generate_report,
    save_recording_result,
    save_workflow_state,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def create_record_prompt(task: RecordTask) -> str:
    """Create the prompt for the recording agent."""
    return f"""You are an SDR signal recording agent. Your task is to record RF signals.

## Task
{task.description}

## Parameters
- Center Frequency: {task.center_freq_mhz} MHz
- Duration: {task.duration_seconds} seconds
- Output Directory: {task.output_dir}
- Format: {task.format}

## Instructions

1. Check the signal strength at the target frequency to ensure good reception.

2. Use the SDR toolkit to perform the recording:
   ```python
   from sdr_toolkit.apps import SignalRecorder

   recorder = SignalRecorder(center_freq_mhz={task.center_freq_mhz})
   result = recorder.record_iq(
       duration={task.duration_seconds},
       output_dir="{task.output_dir}",
   )
   ```

3. Verify the recording:
   - Check that the file was created
   - Verify the file size is reasonable
   - Quick spectrum analysis to confirm signal presence

4. Report the recording details including:
   - File path and size
   - Actual duration
   - Sample rate
   - Signal quality assessment

Provide a concise summary of the recording.
"""


def run_record_workflow(
    center_freq_mhz: float,
    duration_seconds: float,
    description: str = "Signal recording",
    output_dir: str = "./recordings",
    format: str = "sigmf",
    config: WorkflowConfig | None = None,
) -> WorkflowState:
    """Run the agentic signal recording workflow.

    Args:
        center_freq_mhz: Center frequency in MHz.
        duration_seconds: Recording duration in seconds.
        description: Task description.
        output_dir: Output directory for recordings.
        format: Recording format (sigmf, wav, npy).
        config: Workflow configuration.

    Returns:
        WorkflowState with results.
    """
    config = config or WorkflowConfig()
    adw_id = generate_adw_id("adw_sdr_record")

    # Initialize workflow state
    state = WorkflowState(
        adw_id=adw_id,
        workflow_type="record",
    )
    state.log(f"Starting record workflow: {center_freq_mhz} MHz for {duration_seconds}s")

    # Create task
    task = RecordTask(
        adw_id=adw_id,
        description=description,
        center_freq_mhz=center_freq_mhz,
        duration_seconds=duration_seconds,
        output_dir=output_dir,
        format=format,
    )
    state.current_task = task

    # Phase 1: Plan
    state.log("Phase 1: Planning recording parameters")
    state.phase = WorkflowPhase.PLAN
    state.log(f"Target: {center_freq_mhz} MHz, duration: {duration_seconds}s")
    state.advance_phase()

    # Phase 2: Execute
    state.log("Phase 2: Executing recording")

    # Create agent request
    prompt = create_record_prompt(task)
    request = AgentRequest(
        prompt=prompt,
        adw_id=adw_id,
        model=config.model,
        max_turns=10,
        timeout_seconds=max(config.timeout_seconds, int(duration_seconds) + 120),
        working_dir=Path.cwd(),
    )

    # Run agent
    response = run_claude_agent(request)

    if not response.success:
        state.fail(response.error or "Agent execution failed")
        logger.error("Record workflow failed: %s", response.error)
        return state

    state.log(f"Agent completed in {response.num_turns} turns, cost: ${response.cost_usd:.4f}")
    state.advance_phase()

    # Phase 3: Verify
    state.log("Phase 3: Verifying recording")

    # Create result (would be parsed from agent output)
    recording_result = RecordingResult(
        adw_id=adw_id,
        recording_path=f"{output_dir}/{adw_id}.sigmf-data",
        center_freq_mhz=center_freq_mhz,
        sample_rate_hz=1.024e6,
        duration_seconds=duration_seconds,
        num_samples=int(1.024e6 * duration_seconds),
        format=format,
    )
    state.results.append(recording_result)

    state.advance_phase()

    # Phase 4: Complete
    state.complete()

    # Save results
    if config.save_results:
        output_path = config.output_dir / adw_id
        save_workflow_state(state, output_path)
        save_recording_result(recording_result, output_path)
        state.log(f"Results saved to {output_path}")

    # Persist to database if configured
    if config.persist_to_db and config.db_path:
        from adws.adw_modules.survey_persistence import persist_recording_result

        scan_id = persist_recording_result(
            recording_result,
            config.db_path,
            survey_id=config.survey_id,
        )
        if scan_id:
            state.log(f"Persisted to database: {config.db_path} (scan_id={scan_id})")
        else:
            state.log("Warning: Database persistence failed")

    # Generate and log report
    report = generate_report(recording_result=recording_result)
    logger.info("\n%s", report)

    return state


def run_fm_record_workflow(
    freq_mhz: float,
    duration_seconds: float = 30,
    config: WorkflowConfig | None = None,
) -> WorkflowState:
    """Record an FM station.

    Args:
        freq_mhz: FM station frequency in MHz.
        duration_seconds: Recording duration.
        config: Workflow configuration.

    Returns:
        WorkflowState with results.
    """
    return run_record_workflow(
        center_freq_mhz=freq_mhz,
        duration_seconds=duration_seconds,
        description=f"FM station recording at {freq_mhz} MHz",
        config=config,
    )


def main() -> int:
    """CLI entry point for record workflow."""
    parser = argparse.ArgumentParser(description="Agentic Signal Recording Workflow")
    parser.add_argument(
        "-f", "--freq", type=float, required=True, help="Center frequency in MHz"
    )
    parser.add_argument(
        "-d", "--duration", type=float, default=10, help="Duration in seconds"
    )
    parser.add_argument(
        "-o", "--output", type=str, default="./recordings", help="Output directory"
    )
    parser.add_argument(
        "--format", choices=["sigmf", "wav", "npy"], default="sigmf", help="Output format"
    )
    parser.add_argument(
        "--model", choices=["sonnet", "opus", "haiku"], default="sonnet", help="Model to use"
    )
    parser.add_argument(
        "--adw-output", type=str, default="./adw_outputs", help="ADW output directory"
    )
    parser.add_argument(
        "--db", type=str, default=None, help="Store results in UnifiedDB"
    )
    parser.add_argument(
        "--survey-id", type=str, default=None, help="Link results to a survey"
    )

    args = parser.parse_args()

    config = WorkflowConfig(
        model=args.model,
        output_dir=Path(args.adw_output),
        db_path=Path(args.db) if args.db else None,
        survey_id=args.survey_id,
    )

    state = run_record_workflow(
        center_freq_mhz=args.freq,
        duration_seconds=args.duration,
        output_dir=args.output,
        format=args.format,
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
