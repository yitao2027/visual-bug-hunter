"""
Visual Bug Hunter - Core Analyzer Module
Handles screenshot capture and vision analysis logic.
"""

import os
import subprocess
from typing import Optional

def capture_screenshot(save_path: str, region: Optional[dict] = None) -> str:
    """Capture screen screenshot (macOS native)."""
    os.makedirs(os.path.dirname(save_path) if os.path.dirname(save_path) else ".", exist_ok=True)
    
    if region:
        cmd = [
            "screencapture", "-x",
            "-R", f"{region['x']},{region['y']},{region['w']},{region['h']}",
            save_path
        ]
    else:
        cmd = ["screencapture", "-x", save_path]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Screenshot failed: {result.stderr}")
    return save_path

def build_vision_prompt(user_description: str = "") -> str:
    """Build Vision analysis prompt."""
    prompt = """
Please analyze this App screenshot carefully and identify all UI bugs and visual anomalies.

For each issue, output in the following format:
---
Bug ID: BUG-XXX
Type: [Layout Misalignment / Element Overlap / Unresponsive Click / Style Anomaly / Content Duplication / Other]
Location: Which area of the interface (e.g., "top-left search box")
Visual Description: What specific problem was seen (e.g., "two identical bubbles overlapping")
Severity: [HIGH / MEDIUM / LOW]
Possible Cause: UI-level inference (e.g., "component rendered twice")
---

If no obvious bugs are found, please answer "No obvious UI issues found".
"""
    if user_description:
        prompt += f"\n\nUser's additional description: {user_description}"
    return prompt
