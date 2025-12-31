#!/usr/bin/env python3
"""Agentic signal analysis workflow.

This workflow uses Claude Code to analyze recorded signals,
classify them, and provide detailed reports.

Workflow phases:
1. PLAN: Determine analysis approach based on signal type
2. EXECUTE: Perform signal analysis
3. VERIFY: Validate analysis results
4. COMPLETE: Generate detailed report
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
    AnalysisResult,
    AnalyzeTask,
    SignalType,
    TaskStatus,
    WorkflowConfig,
    WorkflowPhase,
    WorkflowState,
)
from adws.adw_modules.utils import (
    generate_report,
    save_analysis_result,
    save_workflow_state,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def create_analyze_prompt(task: AnalyzeTask) -> str:
    """Create the prompt for the analysis agent."""
    return f"""You are an SDR signal analysis agent. Your task is to analyze recorded RF signals.

## Task
{task.description}

## Recording
- Path: {task.recording_path}
- Analysis Type: {task.analysis_type}

## Instructions

1. Load the recording using SDR toolkit:
   ```python
   from sdr_toolkit.io import SigMFRecording

   recording = SigMFRecording.load("{task.recording_path}")
   samples = recording.to_numpy()
   print(f"Loaded {{len(samples)}} samples at {{recording.sample_rate}} Hz")
   ```

2. Perform the requested analysis:

   For "spectrum" analysis:
   - Compute power spectrum
   - Identify dominant frequencies
   - Estimate bandwidth and signal strength

   For "demod" analysis:
   - Attempt FM demodulation
   - Check audio quality
   - Identify content type (music, speech, etc.)

   For "classify" analysis:
   - Analyze signal characteristics
   - Determine modulation type
   - Classify as FM/AM/digital/other

3. Provide detailed findings:
   - Signal type classification
   - Signal strength (dB)
   - Signal-to-noise ratio (dB)
   - Bandwidth estimation
   - Modulation identification
   - Any notable characteristics

4. Generate a summary of the analysis.

Provide a comprehensive but concise analysis report.
"""


def run_analyze_workflow(
    recording_path: str,
    analysis_type: str = "spectrum",
    description: str = "Signal analysis",
    config: WorkflowConfig | None = None,
) -> WorkflowState:
    """Run the agentic signal analysis workflow.

    Args:
        recording_path: Path to the recording file.
        analysis_type: Type of analysis (spectrum, demod, classify).
        description: Task description.
        config: Workflow configuration.

    Returns:
        WorkflowState with results.
    """
    config = config or WorkflowConfig()
    adw_id = generate_adw_id("adw_sdr_analyze")

    # Initialize workflow state
    state = WorkflowState(
        adw_id=adw_id,
        workflow_type="analyze",
    )
    state.log(f"Starting analysis workflow: {recording_path}")

    # Verify recording exists
    recording_file = Path(recording_path)
    if not recording_file.exists():
        state.fail(f"Recording file not found: {recording_path}")
        return state

    # Create task
    task = AnalyzeTask(
        adw_id=adw_id,
        description=description,
        recording_path=recording_path,
        analysis_type=analysis_type,
    )
    state.current_task = task

    # Phase 1: Plan
    state.log("Phase 1: Planning analysis approach")
    state.phase = WorkflowPhase.PLAN
    state.log(f"Analysis type: {analysis_type}")
    state.advance_phase()

    # Phase 2: Execute
    state.log("Phase 2: Executing analysis")

    # Create agent request
    prompt = create_analyze_prompt(task)
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
        logger.error("Analysis workflow failed: %s", response.error)
        return state

    state.log(f"Agent completed in {response.num_turns} turns, cost: ${response.cost_usd:.4f}")
    state.advance_phase()

    # Phase 3: Verify
    state.log("Phase 3: Verifying analysis results")

    # Create result (would be parsed from agent output)
    analysis_result = AnalysisResult(
        adw_id=adw_id,
        recording_path=recording_path,
        analysis_type=analysis_type,
        signal_type=SignalType.UNKNOWN,
        summary="Analysis completed. See agent output for details.",
    )
    state.results.append(analysis_result)

    state.advance_phase()

    # Phase 4: Complete
    state.complete()

    # Save results
    if config.save_results:
        output_path = config.output_dir / adw_id
        save_workflow_state(state, output_path)
        save_analysis_result(analysis_result, output_path)
        state.log(f"Results saved to {output_path}")

    # Persist to database if configured
    if config.persist_to_db and config.db_path:
        from adws.adw_modules.survey_persistence import persist_analysis_result

        scan_id = persist_analysis_result(
            analysis_result,
            config.db_path,
            survey_id=config.survey_id,
        )
        if scan_id:
            state.log(f"Persisted to database: {config.db_path} (scan_id={scan_id})")
        else:
            state.log("Warning: Database persistence failed")

    # Generate and log report
    report = generate_report(analysis_result=analysis_result)
    logger.info("\n%s", report)

    return state


def main() -> int:
    """CLI entry point for analysis workflow."""
    parser = argparse.ArgumentParser(description="Agentic Signal Analysis Workflow")
    parser.add_argument(
        "recording", type=str, help="Path to recording file (.sigmf-meta or .sigmf-data)"
    )
    parser.add_argument(
        "-t",
        "--type",
        choices=["spectrum", "demod", "classify"],
        default="spectrum",
        help="Analysis type",
    )
    parser.add_argument(
        "--model", choices=["sonnet", "opus", "haiku"], default="sonnet", help="Model to use"
    )
    parser.add_argument(
        "-o", "--output", type=str, default="./adw_outputs", help="Output directory"
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
        output_dir=Path(args.output),
        db_path=Path(args.db) if args.db else None,
        survey_id=args.survey_id,
    )

    state = run_analyze_workflow(
        recording_path=args.recording,
        analysis_type=args.type,
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
