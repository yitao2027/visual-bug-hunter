"""
Visual Bug Hunter - Core Locator Module
Handles code scanning and bug-to-code mapping.
"""

import ast
from pathlib import Path
from typing import list, dict

UI_TO_CODE_PATTERNS = {
    "搜索": ["search", "Search", "搜索", "query", "find"],
    "新建": ["new", "create", "add", "New", "Create", "新建"],
    "按钮": ["Button", "button", "QPushButton", "tk.Button", "ttk.Button"],
    "输入框": ["Entry", "LineEdit", "input", "TextField", "QLineEdit"],
    "Tab": ["Tab", "tab", "Notebook", "QTabWidget", "tabview"],
    "重叠": ["pack", "place", "grid", "add_widget", "insert"],
    "禁用": ["setEnabled", "state=", "disabled", "DISABLED"],
    "点击": ["command=", "clicked.connect", "bind(", "on_click"],
}

def locate_code_for_bug(bug: dict, project_path: str) -> dict:
    """Locate relevant code based on bug description."""
    location_result = {
        "bug_id": bug.get("bug_id"),
        "files_found": [],
        "code_snippets": []
    }
    
    bug_text = f"{bug.get('location_desc', '')} {bug.get('visual_desc', '')} {bug.get('possible_cause', '')}"
    
    search_terms = []
    for ui_keyword, code_patterns in UI_TO_CODE_PATTERNS.items():
        if ui_keyword in bug_text:
            search_terms.extend(code_patterns)
    
    if not search_terms:
        search_terms = ["Button", "Entry", "Tab", "widget", "frame"]
    
    project = Path(project_path)
    py_files = list(project.rglob("*.py")) + list(project.rglob("*.swift")) + \
               list(project.rglob("*.kt")) + list(project.rglob("*.js")) + \
               list(project.rglob("*.ts"))
    
    found_snippets = []
    for py_file in py_files[:20]:
        try:
            content = py_file.read_text(encoding="utf-8", errors="replace")
            lines = content.split('\n')
            
            for term in search_terms[:5]:
                for i, line in enumerate(lines):
                    if term in line:
                        start = max(0, i - 2)
                        end = min(len(lines), i + 3)
                        snippet = {
                            "file": str(py_file.relative_to(project)),
                            "line": i + 1,
                            "term": term,
                            "code": '\n'.join(lines[start:end]),
                            "highlight_line": lines[i].strip()
                        }
                        found_snippets.append(snippet)
                        
                        if len(found_snippets) >= 10:
                            break
                if len(found_snippets) >= 10:
                    break
        except Exception:
            continue
    
    location_result["code_snippets"] = found_snippets
    location_result["files_found"] = list(set(s["file"] for s in found_snippets))
    return location_result

def analyze_disabled_widgets(project_path: str) -> list[dict]:
    """Scan for disabled UI components."""
    disabled_patterns = [
        "setEnabled(False)", "setEnabled(0)", 'state="disabled"', 
        "state=DISABLED", ".disabled = True", "isEnabled = false",
    ]
    
    findings = []
    project = Path(project_path)
    
    for py_file in project.rglob("*.py"):
        try:
            content = py_file.read_text(encoding="utf-8", errors="replace")
            lines = content.split('\n')
            for i, line in enumerate(lines):
                for pattern in disabled_patterns:
                    if pattern in line:
                        findings.append({
                            "file": str(py_file.relative_to(project)),
                            "line": i + 1,
                            "code": line.strip(),
                            "pattern": pattern,
                            "warning": "This component is forced to be disabled, which may prevent user clicks"
                        })
        except Exception:
            continue
    
    return findings
