"""
Visual Bug Hunter
~~~~~~~~~~~~~~~~~
Let AI see your GUI app like a human — screenshot, analyze, locate, fix.

:author: yitao2027
:license: MIT
"""

__version__ = "1.0.0"
__author__ = "yitao2027"
__license__ = "MIT"

from .analyzer import analyze_screenshot, parse_vision_bugs, VISION_ANALYSIS_PROMPT
from .locator import locate_code_for_bug, analyze_disabled_widgets, detect_duplicate_renders
from .reporter import generate_report, print_summary
from .utils import capture_screenshot, launch_app_and_capture

__all__ = [
    "analyze_screenshot",
    "parse_vision_bugs",
    "VISION_ANALYSIS_PROMPT",
    "locate_code_for_bug",
    "analyze_disabled_widgets",
    "detect_duplicate_renders",
    "generate_report",
    "print_summary",
    "capture_screenshot",
    "launch_app_and_capture",
]
