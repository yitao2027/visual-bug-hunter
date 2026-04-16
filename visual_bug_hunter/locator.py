"""
locator.py — Token-efficient code locator
Maps visual bugs to exact file + line number in the project source.
"""

import ast
import os
from pathlib import Path
from typing import List, Dict, Optional


# ─────────────────────────────────────────────────────────────────
# UI keyword → code search term mapping
# ─────────────────────────────────────────────────────────────────

UI_TO_CODE_PATTERNS: Dict[str, List[str]] = {
    # English
    "search": ["search", "Search", "query", "find", "SearchBar", "SearchInput"],
    "button": ["Button", "button", "QPushButton", "tk.Button", "ttk.Button", "onClick"],
    "input": ["Entry", "LineEdit", "input", "TextField", "QLineEdit", "TextInput"],
    "tab": ["Tab", "tab", "Notebook", "QTabWidget", "tabview", "TabBar"],
    "overlap": ["pack", "place", "grid", "add_widget", "insert", "addWidget"],
    "disabled": ["setEnabled", "state=", "disabled", "DISABLED", "isEnabled"],
    "click": ["command=", "clicked.connect", "bind(", "on_click", "onClick"],
    "duplicate": ["pack(", "grid(", "place(", "add(", "insert("],
    # Chinese keywords (from user descriptions)
    "搜索": ["search", "Search", "搜索", "query"],
    "新建": ["new", "create", "add", "New", "Create", "新建"],
    "按钮": ["Button", "button", "QPushButton", "tk.Button"],
    "输入框": ["Entry", "LineEdit", "input", "TextField"],
    "Tab": ["Tab", "tab", "Notebook", "QTabWidget", "tabview"],
    "重叠": ["pack", "place", "grid", "add_widget"],
    "禁用": ["setEnabled", "state=", "disabled", "DISABLED"],
    "点击": ["command=", "clicked.connect", "bind(", "on_click"],
}

# Source file extensions to scan
SOURCE_EXTENSIONS = [".py", ".swift", ".kt", ".js", ".ts", ".tsx", ".jsx", ".vue"]


def _extract_search_terms(bug: Dict) -> List[str]:
    """Extract relevant code search terms from a bug dict."""
    bug_text = " ".join([
        bug.get("location", ""),
        bug.get("description", ""),
        bug.get("likely_cause", ""),
        bug.get("location_desc", ""),   # Chinese field alias
        bug.get("visual_desc", ""),
        bug.get("possible_cause", ""),
        bug.get("type", ""),
    ]).lower()

    terms: List[str] = []
    for keyword, patterns in UI_TO_CODE_PATTERNS.items():
        if keyword.lower() in bug_text:
            terms.extend(patterns)

    # Deduplicate while preserving order
    seen = set()
    unique = []
    for t in terms:
        if t not in seen:
            seen.add(t)
            unique.append(t)

    return unique or ["Button", "Entry", "Tab", "widget", "frame"]


def locate_code_for_bug(
    bug: Dict,
    project_path: str,
    max_files: int = 20,
    max_snippets: int = 10,
    context_lines: int = 3,
) -> Dict:
    """
    Locate source code related to a visual bug.

    Token-efficient strategy:
    - Only scans files matching SOURCE_EXTENSIONS
    - Stops after max_files files or max_snippets snippets
    - Returns only context_lines lines around each match

    Args:
        bug: Bug dict from parse_vision_bugs()
        project_path: Root directory of the project
        max_files: Max number of source files to inspect
        max_snippets: Max code snippets to return
        context_lines: Lines of context around each match

    Returns:
        Dict with files_found and code_snippets
    """
    result: Dict = {
        "bug_id": bug.get("bug_id", "UNKNOWN"),
        "search_terms": [],
        "files_found": [],
        "code_snippets": [],
    }

    search_terms = _extract_search_terms(bug)
    result["search_terms"] = search_terms[:8]

    project = Path(project_path)
    source_files: List[Path] = []
    for ext in SOURCE_EXTENSIONS:
        source_files.extend(project.rglob(f"*{ext}"))
    # Skip node_modules, .git, __pycache__, venv
    source_files = [
        f for f in source_files
        if not any(skip in str(f) for skip in
                   ["node_modules", ".git", "__pycache__", ".venv", "venv", "dist", "build"])
    ][:max_files]

    snippets: List[Dict] = []
    for src_file in source_files:
        if len(snippets) >= max_snippets:
            break
        try:
            lines = src_file.read_text(encoding="utf-8", errors="replace").splitlines()
        except Exception:
            continue

        for term in search_terms[:6]:
            for i, line in enumerate(lines):
                if term in line:
                    start = max(0, i - context_lines)
                    end = min(len(lines), i + context_lines + 1)
                    snippets.append({
                        "file": str(src_file.relative_to(project)),
                        "line": i + 1,
                        "match_term": term,
                        "highlight": line.strip(),
                        "context": "\n".join(
                            f"{'→' if j == i else ' '} {j+1:4d} | {lines[j]}"
                            for j in range(start, end)
                        ),
                    })
                    if len(snippets) >= max_snippets:
                        break
            if len(snippets) >= max_snippets:
                break

    result["code_snippets"] = snippets
    result["files_found"] = list(dict.fromkeys(s["file"] for s in snippets))
    return result


def analyze_disabled_widgets(project_path: str) -> List[Dict]:
    """
    Scan for forcibly-disabled UI widgets — the #1 cause of
    "button/input can't be clicked" bugs.

    Patterns detected:
        setEnabled(False), state="disabled", state=DISABLED,
        .disabled = True, isEnabled = false, userInteractionEnabled = false
    """
    patterns = [
        "setEnabled(False)",
        "setEnabled(0)",
        'state="disabled"',
        "state=DISABLED",
        ".disabled = True",
        "isEnabled = false",
        "userInteractionEnabled = false",
        'state=tk.DISABLED',
        "configure(state='disabled')",
    ]

    findings: List[Dict] = []
    project = Path(project_path)

    for src in project.rglob("*.py"):
        if any(skip in str(src) for skip in ["node_modules", ".git", "__pycache__", ".venv"]):
            continue
        try:
            lines = src.read_text(encoding="utf-8", errors="replace").splitlines()
            for i, line in enumerate(lines):
                for pat in patterns:
                    if pat in line:
                        findings.append({
                            "file": str(src.relative_to(project)),
                            "line": i + 1,
                            "code": line.strip(),
                            "pattern": pat,
                            "fix_hint": (
                                f"This widget is forcibly disabled. "
                                f"Change `{pat}` → enable it at the right time, "
                                f"or remove if unintentional."
                            ),
                        })
        except Exception:
            continue

    return findings


def detect_duplicate_renders(project_path: str) -> List[Dict]:
    """
    Detect widgets whose layout method (.pack / .grid / .place / .add)
    is called more than once — the #1 cause of "element appears twice" bugs.

    Uses Python AST for accurate detection (not regex).
    """
    findings: List[Dict] = []
    project = Path(project_path)

    for src in project.rglob("*.py"):
        if any(skip in str(src) for skip in ["node_modules", ".git", "__pycache__", ".venv"]):
            continue
        try:
            content = src.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(content)
        except Exception:
            continue

        widget_calls: Dict[str, int] = {}
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if not (isinstance(func, ast.Attribute) and
                    func.attr in ("pack", "grid", "place", "add", "insert")):
                continue
            # Use the object expression as the key
            try:
                obj_key = ast.dump(func.value)
            except Exception:
                obj_key = str(getattr(node, "lineno", "?"))

            if obj_key in widget_calls:
                findings.append({
                    "file": str(src.relative_to(project)),
                    "line": node.lineno,
                    "first_call_line": widget_calls[obj_key],
                    "method": func.attr,
                    "fix_hint": (
                        f"`.{func.attr}()` called twice on the same widget "
                        f"(first at line {widget_calls[obj_key]}, again at line {node.lineno}). "
                        f"Delete the duplicate call."
                    ),
                })
            else:
                widget_calls[obj_key] = node.lineno

    return findings
