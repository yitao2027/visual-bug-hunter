"""
cli.py — Command-line interface for visual-bug-hunter

Usage:
    vbh scan <project_path> [--screenshot PATH] [--app PATH] [--desc TEXT]
    vbh static <project_path>
    vbh prompt [--lang en|cn] [--desc TEXT]
"""

import argparse
import json
import os
import sys


def cmd_scan(args):
    """Full scan: static analysis + optional screenshot Vision analysis."""
    from .locator import analyze_disabled_widgets, detect_duplicate_renders
    from .reporter import generate_report, print_summary

    project_path = args.project_path
    if not os.path.isdir(project_path):
        print(f"❌ Project path not found: {project_path}", file=sys.stderr)
        sys.exit(1)

    screenshot_path = args.screenshot
    vision_bugs = []
    code_locations = []

    # Launch app and capture screenshot if --app is provided
    if args.app and not screenshot_path:
        print(f"🚀 Launching app: {args.app}")
        try:
            from .utils import launch_app_and_capture
            _, screenshot_path = launch_app_and_capture(
                args.app,
                wait_seconds=getattr(args, "wait", 3),
                output_dir="screenshots",
            )
            print(f"📸 Screenshot saved: {screenshot_path}")
        except Exception as e:
            print(f"⚠️  Auto-screenshot failed: {e}", file=sys.stderr)

    if screenshot_path:
        print(f"\n👁️  Screenshot ready: {screenshot_path}")
        from .analyzer import build_vision_prompt
        prompt = build_vision_prompt(
            user_description=getattr(args, "desc", ""),
            lang=getattr(args, "lang", "en"),
        )
        print("\n─── Vision Prompt (send this + the screenshot to your LLM) ───")
        print(prompt)
        print("──────────────────────────────────────────────────────────────\n")
        print("💡 Tip: pipe the LLM's response back with --vision-output <file>")
        print("        or use the Python API: parse_vision_bugs(llm_response)")

    # Static analysis (always runs)
    print("\n🔍 Running static analysis…")
    disabled = analyze_disabled_widgets(project_path)
    dupes = detect_duplicate_renders(project_path)

    if disabled:
        print(f"  ⚠️  {len(disabled)} disabled widget(s) found:")
        for d in disabled:
            print(f"     📍 {d['file']}:{d['line']}  →  {d['code']}")
    else:
        print("  ✅ No forcibly-disabled widgets found")

    if dupes:
        print(f"  ⚠️  {len(dupes)} duplicate render(s) found:")
        for d in dupes:
            print(f"     📍 {d['file']}:{d['line']}  →  {d['fix_hint']}")
    else:
        print("  ✅ No duplicate renders found")

    static_analysis = {"disabled_widgets": disabled, "duplicate_renders": dupes}

    report = generate_report(
        project_path=project_path,
        vision_bugs=vision_bugs,
        code_locations=code_locations,
        static_analysis=static_analysis,
        screenshot_path=screenshot_path,
        user_description=getattr(args, "desc", ""),
        output_dir=getattr(args, "output", "bug_reports"),
    )
    print_summary(report)


def cmd_static(args):
    """Static-only scan — no screenshot needed."""
    from .locator import analyze_disabled_widgets, detect_duplicate_renders
    from .reporter import generate_report, print_summary

    project_path = args.project_path
    if not os.path.isdir(project_path):
        print(f"❌ Project path not found: {project_path}", file=sys.stderr)
        sys.exit(1)

    print(f"🔍 Static scan: {project_path}\n")
    disabled = analyze_disabled_widgets(project_path)
    dupes = detect_duplicate_renders(project_path)

    if not disabled and not dupes:
        print("✅ No issues found by static analysis.")
        return

    if disabled:
        print(f"🚫 Disabled widgets ({len(disabled)} found):")
        for d in disabled:
            print(f"  {d['file']}:{d['line']}")
            print(f"    Code : {d['code']}")
            print(f"    Fix  : {d['fix_hint']}\n")

    if dupes:
        print(f"🔁 Duplicate renders ({len(dupes)} found):")
        for d in dupes:
            print(f"  {d['file']}:{d['line']} (first at line {d['first_call_line']})")
            print(f"    Fix  : {d['fix_hint']}\n")

    report = generate_report(
        project_path=project_path,
        vision_bugs=[],
        code_locations=[],
        static_analysis={"disabled_widgets": disabled, "duplicate_renders": dupes},
        output_dir=getattr(args, "output", "bug_reports"),
    )
    print_summary(report)


def cmd_prompt(args):
    """Print the Vision prompt for use with any LLM."""
    from .analyzer import build_vision_prompt
    lang = getattr(args, "lang", "en")
    desc = getattr(args, "desc", "")
    print(build_vision_prompt(user_description=desc, lang=lang))


def main():
    parser = argparse.ArgumentParser(
        prog="vbh",
        description=(
            "visual-bug-hunter — Let AI see your GUI app like a human.\n"
            "Detect UI bugs via screenshot analysis + static code scan."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  vbh scan ./my_app --screenshot bug.png --desc "button can't be clicked"
  vbh scan ./my_app --app ./my_app/main.py
  vbh static ./my_app
  vbh prompt --lang cn --desc "搜索框点不了"

GitHub: https://github.com/yitao2027/visual-bug-hunter
        """,
    )

    sub = parser.add_subparsers(dest="command", metavar="COMMAND")
    sub.required = True

    # ── scan ──
    p_scan = sub.add_parser("scan", help="Full scan (static + optional Vision analysis)")
    p_scan.add_argument("project_path", help="Root directory of your project")
    p_scan.add_argument("--screenshot", metavar="PATH", help="Path to existing screenshot")
    p_scan.add_argument("--app", metavar="PATH", help="Launch this app and auto-screenshot (.py / .app / command)")
    p_scan.add_argument("--wait", type=int, default=3, metavar="SEC", help="Seconds to wait after launching app (default: 3)")
    p_scan.add_argument("--desc", default="", metavar="TEXT", help="Describe the bug in plain text")
    p_scan.add_argument("--lang", default="en", choices=["en", "cn"], help="Vision prompt language (default: en)")
    p_scan.add_argument("--output", default="bug_reports", metavar="DIR", help="Output directory for reports")
    p_scan.set_defaults(func=cmd_scan)

    # ── static ──
    p_static = sub.add_parser("static", help="Static code scan only (no screenshot needed)")
    p_static.add_argument("project_path", help="Root directory of your project")
    p_static.add_argument("--output", default="bug_reports", metavar="DIR", help="Output directory for reports")
    p_static.set_defaults(func=cmd_static)

    # ── prompt ──
    p_prompt = sub.add_parser("prompt", help="Print the Vision analysis prompt")
    p_prompt.add_argument("--lang", default="en", choices=["en", "cn"], help="Prompt language (default: en)")
    p_prompt.add_argument("--desc", default="", metavar="TEXT", help="Append user description to prompt")
    p_prompt.set_defaults(func=cmd_prompt)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
