"""
utils.py — Screenshot capture & app launcher utilities
"""

import os
import sys
import subprocess
import time
from pathlib import Path
from typing import Optional, Tuple


def capture_screenshot(save_path: str, region: Optional[dict] = None) -> str:
    """
    Capture a screenshot (macOS native screencapture).

    Args:
        save_path: Output file path (.png)
        region: Optional dict {x, y, w, h} for region capture

    Returns:
        Path to the saved screenshot
    """
    os.makedirs(os.path.dirname(os.path.abspath(save_path)), exist_ok=True)

    if sys.platform == "darwin":
        if region:
            cmd = [
                "screencapture", "-x",
                "-R", f"{region['x']},{region['y']},{region['w']},{region['h']}",
                save_path,
            ]
        else:
            cmd = ["screencapture", "-x", save_path]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"Screenshot failed: {result.stderr}")
    else:
        # Cross-platform fallback via pyautogui
        try:
            import pyautogui
            from PIL import Image
            img = pyautogui.screenshot()
            if region:
                img = img.crop((region["x"], region["y"],
                                region["x"] + region["w"],
                                region["y"] + region["h"]))
            img.save(save_path)
        except ImportError:
            raise RuntimeError(
                "pyautogui / Pillow required on non-macOS. "
                "Install with: pip install pyautogui Pillow"
            )

    return save_path


def launch_app_and_capture(
    app_path: str,
    wait_seconds: int = 3,
    output_dir: str = "screenshots",
) -> Tuple[subprocess.Popen, str]:
    """
    Launch a GUI app and capture its initial screenshot.

    Args:
        app_path: Path to .app bundle, .py script, or shell command
        wait_seconds: Seconds to wait for app to appear on screen
        output_dir: Directory to save screenshots

    Returns:
        (process, screenshot_path)
    """
    os.makedirs(output_dir, exist_ok=True)

    if app_path.endswith(".app"):
        proc = subprocess.Popen(["open", app_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    elif app_path.endswith(".py"):
        proc = subprocess.Popen(
            [sys.executable, app_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    else:
        proc = subprocess.Popen(
            app_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=True,
        )

    time.sleep(wait_seconds)

    screenshot_path = os.path.join(output_dir, f"app_{int(time.time())}.png")
    capture_screenshot(screenshot_path)

    return proc, screenshot_path


def capture_runtime_logs(proc: subprocess.Popen, timeout: float = 1.5) -> dict:
    """
    Non-blocking capture of app stdout/stderr logs.
    """
    logs = {"stdout": "", "stderr": "", "crashed": False}
    try:
        stdout, stderr = proc.communicate(timeout=timeout)
        logs["stdout"] = stdout.decode("utf-8", errors="replace") if stdout else ""
        logs["stderr"] = stderr.decode("utf-8", errors="replace") if stderr else ""
        logs["crashed"] = proc.returncode not in (0, None)
    except subprocess.TimeoutExpired:
        pass  # App still running — that's normal
    except Exception as e:
        logs["error"] = str(e)
    return logs
