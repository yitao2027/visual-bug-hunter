"""
reporter.py — Bug report generation (JSON + Markdown)
"""

import json
import os
import time
from typing import Dict, List, Optional


def generate_report(
    project_path: str,
    vision_bugs: List[Dict],
    code_locations: List[Dict],
    static_analysis: Dict,
    screenshot_path: Optional[str] = None,
    user_description: str = "",
    output_dir: str = "bug_reports",
) -> Dict:
    """
    Generate a structured bug report and save to disk.

    Returns:
        Dict with report data and saved file paths.
    """
    os.makedirs(output_dir, exist_ok=True)
    timestamp = time.strftime("%Y%m%d_%H%M%S")

    report = {
        "meta": {
            "tool": "visual-bug-hunter",
            "version": "1.0.0",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "project_path": project_path,
            "screenshot": screenshot_path,
            "user_description": user_description,
        },
        "summary": {
            "vision_bugs": len(vision_bugs),
            "disabled_widgets": len(static_analysis.get("disabled_widgets", [])),
            "duplicate_renders": len(static_analysis.get("duplicate_renders", [])),
            "total_issues": (
                len(vision_bugs)
                + len(static_analysis.get("disabled_widgets", []))
                + len(static_analysis.get("duplicate_renders", []))
            ),
        },
        "vision_bugs": vision_bugs,
        "code_locations": code_locations,
        "static_analysis": static_analysis,
    }

    # Save JSON
    json_path = os.path.join(output_dir, f"bug_report_{timestamp}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    # Save Markdown
    md_path = os.path.join(output_dir, f"bug_report_{timestamp}.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(_render_markdown(report))

    report["_saved"] = {"json": json_path, "markdown": md_path}
    return report


def _render_markdown(report: Dict) -> str:
    """Render a human-readable Markdown bug report."""
    meta = report["meta"]
    summary = report["summary"]
    lines = [
        "# 🔍 Visual Bug Hunter — Report",
        "",
        f"**Project:** `{meta['project_path']}`  ",
        f"**Time:** {meta['timestamp']}  ",
        f"**Screenshot:** `{meta.get('screenshot', 'N/A')}`  ",
        "",
        "---",
        "",
        "## Summary",
        "",
        f"| Category | Count |",
        f"|----------|-------|",
        f"| Vision-detected bugs | {summary['vision_bugs']} |",
        f"| Disabled widgets (static scan) | {summary['disabled_widgets']} |",
        f"| Duplicate renders (static scan) | {summary['duplicate_renders']} |",
        f"| **Total issues** | **{summary['total_issues']}** |",
        "",
        "---",
        "",
    ]

    # Vision bugs
    vision_bugs = report.get("vision_bugs", [])
    if vision_bugs:
        lines += ["## 👁️ Vision-Detected Bugs", ""]
        for bug in vision_bugs:
            sev = bug.get("severity", "MEDIUM")
            icon = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢"}.get(sev, "⚪")
            lines += [
                f"### {icon} {bug.get('bug_id', 'BUG-?')} — {bug.get('description', '')}",
                "",
                f"- **Type:** {bug.get('type', 'unknown')}",
                f"- **Location:** {bug.get('location', 'unknown')}",
                f"- **Severity:** {sev}",
                f"- **Likely Cause:** {bug.get('likely_cause', 'unknown')}",
                "",
            ]
    else:
        lines += ["## 👁️ Vision Analysis", "", "_No screenshot provided or no bugs detected._", ""]

    # Static analysis — disabled widgets
    disabled = report.get("static_analysis", {}).get("disabled_widgets", [])
    if disabled:
        lines += ["## 🚫 Disabled Widgets (Static Scan)", ""]
        for d in disabled:
            lines += [
                f"- **`{d['file']}` line {d['line']}**",
                f"  ```python",
                f"  {d['code']}",
                f"  ```",
                f"  💡 {d['fix_hint']}",
                "",
            ]

    # Static analysis — duplicate renders
    dupes = report.get("static_analysis", {}).get("duplicate_renders", [])
    if dupes:
        lines += ["## 🔁 Duplicate Renders (Static Scan)", ""]
        for d in dupes:
            lines += [
                f"- **`{d['file']}` line {d['line']}** (first call at line {d['first_call_line']})",
                f"  💡 {d['fix_hint']}",
                "",
            ]

    # Code locations
    locations = report.get("code_locations", [])
    if locations:
        lines += ["## 📍 Code Locations", ""]
        for loc in locations:
            lines += [f"### {loc.get('bug_id', '')} — related code", ""]
            for snippet in loc.get("code_snippets", [])[:3]:
                lines += [
                    f"**`{snippet['file']}` (line {snippet['line']})**",
                    "```",
                    snippet.get("context", snippet.get("highlight", "")),
                    "```",
                    "",
                ]

    lines += [
        "---",
        "",
        "_Generated by [visual-bug-hunter](https://github.com/yitao2027/visual-bug-hunter)_",
    ]

    return "\n".join(lines)


def print_summary(report: Dict) -> None:
    """Print a concise summary to stdout."""
    summary = report.get("summary", {})
    saved = report.get("_saved", {})

    print("\n" + "=" * 55)
    print("  🎯  Visual Bug Hunter — Scan Complete")
    print("=" * 55)
    print(f"  Vision bugs detected  : {summary.get('vision_bugs', 0)}")
    print(f"  Disabled widgets      : {summary.get('disabled_widgets', 0)}")
    print(f"  Duplicate renders     : {summary.get('duplicate_renders', 0)}")
    print(f"  ─────────────────────────────────────")
    print(f"  Total issues          : {summary.get('total_issues', 0)}")
    if saved:
        print(f"\n  📄 JSON  → {saved.get('json', '')}")
        print(f"  📝 Markdown → {saved.get('markdown', '')}")
    print("=" * 55 + "\n")
