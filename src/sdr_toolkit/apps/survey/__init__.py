"""Spectrum Survey module for comprehensive frequency scanning.

Provides multi-segment, resumable spectrum surveys with:
- Priority band scanning with optimal step sizes
- Gap-filling coarse sweeps for full coverage
- DuckDB persistence for cross-session operation
- ServiceNow-style signal state management
- Ralph Wiggum loop integration

Example:
    >>> from sdr_toolkit.apps.survey import SurveyManager
    >>> manager = SurveyManager(db)
    >>> survey = manager.create_survey("Full Sweep", full_coverage=True)
    >>> result = manager.execute_next_segment(survey.survey_id)
"""

from sdr_toolkit.apps.survey.band_catalog import (
    PRIORITY_BANDS,
    generate_gap_segments,
    generate_full_survey_segments,
)
from sdr_toolkit.apps.survey.manager import SurveyManager
from sdr_toolkit.apps.survey.executor import SurveyExecutor

__all__ = [
    "PRIORITY_BANDS",
    "generate_gap_segments",
    "generate_full_survey_segments",
    "SurveyManager",
    "SurveyExecutor",
]
