"""
Visual Bug Hunter - 核心实现
让 AI 像人一样「眼睛看 + 手点击」测试 GUI/Web App，精准定位 Bug 并映射到代码行
"""

import os
import sys
import json
import subprocess
import time
import ast
import difflib
from pathlib import Path
from typing import Optional

# ─────────────────────────────────────────────
# 模块 1：截图感知
# ─────────────────────────────────────────────

def capture_screenshot(save_path: str, region: Optional[dict] = None) -> str:
    """
    截取屏幕截图（macOS 原生）
    region: {"x": int, "y": int, "w": int, "h": int} 可选区域截图
    返回截图文件路径
    """
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
        raise RuntimeError(f"截图失败: {result.stderr}")
    return save_path


def capture_window(app_name: str, save_path: str) -> str:
    """
    截取指定 App 窗口（macOS AppleScript）
    """
    script = f'''
    tell application "{app_name}"
        activate
    end tell
    delay 0.5
    do shell script "screencapture -x -o {save_path}"
    '''
    result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
    if result.returncode != 0:
        # 降级为全屏截图
        return capture_screenshot(save_path)
    return save_path


# ─────────────────────────────────────────────
# 模块 2：Vision 分析（调用 understand_media 的 prompt 模板）
# ─────────────────────────────────────────────

VISION_ANALYSIS_PROMPT = """
请仔细分析这张 App 截图，找出所有 UI Bug 和视觉异常。

对每个问题，请按以下格式输出：
---
Bug ID: BUG-XXX
问题类型: [布局错位 / 元素重叠 / 点击无响应 / 样式异常 / 内容重复 / 其他]
位置描述: 在界面的哪个区域（如"左上角搜索框"、"右侧聊天气泡"）
视觉描述: 具体看到了什么问题（如"两个相同的气泡重叠显示"）
严重程度: [HIGH / MEDIUM / LOW]
可能原因: 从 UI 角度推测的原因（如"组件被渲染了两次"）
---

如果截图中没有明显 Bug，请回答"未发现明显 UI 问题"。
"""


def build_vision_prompt(user_description: str = "") -> str:
    """构建 Vision 分析 prompt，可附加用户描述"""
    prompt = VISION_ANALYSIS_PROMPT
    if user_description:
        prompt += f"\n\n用户额外说明：{user_description}"
    return prompt


def parse_vision_bugs(vision_output: str) -> list[dict]:
    """
    解析 Vision 模型输出，提取结构化 Bug 列表
    """
    bugs = []
    current_bug = {}
    
    for line in vision_output.split('\n'):
        line = line.strip()
        if line.startswith('Bug ID:'):
            if current_bug:
                bugs.append(current_bug)
            current_bug = {"bug_id": line.replace("Bug ID:", "").strip()}
        elif line.startswith('问题类型:'):
            current_bug["type"] = line.replace("问题类型:", "").strip()
        elif line.startswith('位置描述:'):
            current_bug["location_desc"] = line.replace("位置描述:", "").strip()
        elif line.startswith('视觉描述:'):
            current_bug["visual_desc"] = line.replace("视觉描述:", "").strip()
        elif line.startswith('严重程度:'):
            current_bug["severity"] = line.replace("严重程度:", "").strip()
        elif line.startswith('可能原因:'):
            current_bug["possible_cause"] = line.replace("可能原因:", "").strip()
    
    if current_bug and "bug_id" in current_bug:
        bugs.append(current_bug)
    
    return bugs


# ─────────────────────────────────────────────
# 模块 3：UI 交互测试（pyautogui）
# ─────────────────────────────────────────────

def test_ui_interaction(x: int, y: int, action: str = "click") -> dict:
    """
    在指定坐标执行 UI 交互，捕获响应
    action: click / double_click / right_click / hover
    返回交互结果
    """
    try:
        import pyautogui
        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0.3
        
        # 移动到目标位置
        pyautogui.moveTo(x, y, duration=0.2)
        time.sleep(0.1)
        
        # 执行动作
        if action == "click":
            pyautogui.click(x, y)
        elif action == "double_click":
            pyautogui.doubleClick(x, y)
        elif action == "right_click":
            pyautogui.rightClick(x, y)
        elif action == "hover":
            pass  # 已移动到位置
        
        time.sleep(0.5)  # 等待 UI 响应
        
        return {"success": True, "action": action, "x": x, "y": y}
        
    except ImportError:
        return {"success": False, "error": "pyautogui 未安装，请运行: pip install pyautogui"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def launch_app_and_capture(app_path: str, wait_seconds: int = 3) -> tuple[subprocess.Popen, str]:
    """
    启动 GUI App 并截图
    返回 (进程对象, 截图路径)
    """
    screenshots_dir = "screenshots"
    os.makedirs(screenshots_dir, exist_ok=True)
    
    # 启动 App
    if app_path.endswith(".app"):
        proc = subprocess.Popen(["open", app_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    elif app_path.endswith(".py"):
        proc = subprocess.Popen(
            [sys.executable, app_path],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
    else:
        proc = subprocess.Popen(app_path, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    
    # 等待 App 启动
    time.sleep(wait_seconds)
    
    # 截图
    screenshot_path = f"{screenshots_dir}/app_initial_{int(time.time())}.png"
    capture_screenshot(screenshot_path)
    
    return proc, screenshot_path


def capture_runtime_logs(proc: subprocess.Popen, timeout: float = 2.0) -> dict:
    """
    捕获 App 运行时日志（非阻塞）
    """
    logs = {"stdout": "", "stderr": "", "crashed": False}
    
    try:
        stdout, stderr = proc.communicate(timeout=timeout)
        logs["stdout"] = stdout.decode("utf-8", errors="replace") if stdout else ""
        logs["stderr"] = stderr.decode("utf-8", errors="replace") if stderr else ""
        logs["crashed"] = proc.returncode not in (0, None)
    except subprocess.TimeoutExpired:
        # App 还在运行（正常）
        pass
    except Exception as e:
        logs["error"] = str(e)
    
    return logs


# ─────────────────────────────────────────────
# 模块 4：代码精准定位
# ─────────────────────────────────────────────

# UI 关键词 → 代码模式映射表
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
    """
    根据 Bug 描述，在项目代码中定位相关代码
    省 token 策略：只搜索关键词相关文件，不全量读取
    """
    location_result = {
        "bug_id": bug.get("bug_id"),
        "files_found": [],
        "code_snippets": []
    }
    
    # 从 Bug 描述提取搜索关键词
    bug_text = f"{bug.get('location_desc', '')} {bug.get('visual_desc', '')} {bug.get('possible_cause', '')}"
    
    search_terms = []
    for ui_keyword, code_patterns in UI_TO_CODE_PATTERNS.items():
        if ui_keyword in bug_text:
            search_terms.extend(code_patterns)
    
    if not search_terms:
        # 通用搜索
        search_terms = ["Button", "Entry", "Tab", "widget", "frame"]
    
    # 搜索相关代码文件
    project = Path(project_path)
    py_files = list(project.rglob("*.py")) + list(project.rglob("*.swift")) + \
               list(project.rglob("*.kt")) + list(project.rglob("*.js")) + \
               list(project.rglob("*.ts"))
    
    found_snippets = []
    for py_file in py_files[:20]:  # 省 token：最多检查 20 个文件
        try:
            content = py_file.read_text(encoding="utf-8", errors="replace")
            lines = content.split('\n')
            
            for term in search_terms[:5]:  # 每个文件最多搜 5 个关键词
                for i, line in enumerate(lines):
                    if term in line:
                        # 提取上下文（前后各 2 行）
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
                        
                        if len(found_snippets) >= 10:  # 省 token：最多返回 10 个片段
                            break
                if len(found_snippets) >= 10:
                    break
        except Exception:
            continue
    
    location_result["code_snippets"] = found_snippets
    location_result["files_found"] = list(set(s["file"] for s in found_snippets))
    return location_result


def analyze_disabled_widgets(project_path: str) -> list[dict]:
    """
    专项检测：扫描所有被禁用的 UI 组件（setEnabled(False), state=DISABLED 等）
    这是"按钮点不了"类 Bug 的最常见原因
    """
    disabled_patterns = [
        "setEnabled(False)",
        "setEnabled(0)",
        'state="disabled"',
        "state=DISABLED",
        ".disabled = True",
        "isEnabled = false",
        "userInteractionEnabled = false",
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
                            "warning": "此组件被强制禁用，可能导致用户无法点击"
                        })
        except Exception:
            continue
    
    return findings


def detect_duplicate_renders(project_path: str) -> list[dict]:
    """
    专项检测：扫描可能导致重复渲染的代码（pack/grid/add 被调用两次）
    这是"元素重叠显示两次"类 Bug 的常见原因
    """
    findings = []
    project = Path(project_path)
    
    for py_file in project.rglob("*.py"):
        try:
            content = py_file.read_text(encoding="utf-8", errors="replace")
            # 解析 AST，找重复调用
            tree = ast.parse(content)
            widget_calls = {}
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    call_str = ast.dump(node)
                    # 检测同一对象的 pack/grid/place 被调用多次
                    if hasattr(node, 'func') and hasattr(node.func, 'attr'):
                        attr = node.func.attr
                        if attr in ('pack', 'grid', 'place', 'add'):
                            key = ast.dump(node.func.value) if hasattr(node.func, 'value') else str(node.lineno)
                            if key in widget_calls:
                                findings.append({
                                    "file": str(py_file.relative_to(project)),
                                    "line": node.lineno,
                                    "first_call_line": widget_calls[key],
                                    "method": attr,
                                    "warning": f"同一组件的 .{attr}() 被调用了两次，可能导致重复渲染"
                                })
                            else:
                                widget_calls[key] = node.lineno
        except Exception:
            continue
    
    return findings


# ─────────────────────────────────────────────
# 模块 5：省 Token 代码修复生成
# ─────────────────────────────────────────────

def generate_minimal_fix(file_path: str, line_number: int, fix_description: str) -> dict:
    """
    省 token 原则：只输出最小 Diff，不重写整个文件
    返回 unified diff 格式的修复建议
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            original_lines = f.readlines()
        
        # 提取问题行上下文（前后各 5 行）
        start = max(0, line_number - 6)
        end = min(len(original_lines), line_number + 5)
        context = original_lines[start:end]
        
        return {
            "file": file_path,
            "target_line": line_number,
            "context_start_line": start + 1,
            "context": "".join(context),
            "fix_description": fix_description,
            "strategy": "MINIMAL_DIFF",
            "instruction": f"只需修改第 {line_number} 行，不要修改其他代码"
        }
    except Exception as e:
        return {"error": str(e)}


def apply_fix_and_diff(file_path: str, old_line: str, new_line: str) -> str:
    """
    应用修复并生成 diff，用于验证修改范围（防止 AI 偷偷改其他代码）
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            original = f.readlines()
        
        modified = [line.replace(old_line, new_line) if old_line in line else line 
                   for line in original]
        
        diff = list(difflib.unified_diff(
            original, modified,
            fromfile=f"{file_path} (修改前)",
            tofile=f"{file_path} (修改后)",
            lineterm=''
        ))
        
        return '\n'.join(diff)
    except Exception as e:
        return f"Diff 生成失败: {e}"


def estimate_token_cost(code_snippet: str) -> int:
    """估算代码片段的 token 数（粗略：4字符≈1token）"""
    return len(code_snippet) // 4


def build_minimal_context(project_path: str, relevant_files: list[str], max_tokens: int = 2000) -> str:
    """
    省 token 策略：只加载与 Bug 相关的代码片段，控制总 token 数
    max_tokens: 最大上下文 token 预算（默认 2000，约 8000 字符）
    """
    context_parts = []
    total_tokens = 0
    
    for file_path in relevant_files:
        try:
            full_path = Path(project_path) / file_path
            content = full_path.read_text(encoding='utf-8', errors='replace')
            file_tokens = estimate_token_cost(content)
            
            if total_tokens + file_tokens > max_tokens:
                # 超出预算：只取前 50 行
                lines = content.split('\n')[:50]
                content = '\n'.join(lines) + f"\n... (文件过长，已截断，共 {len(content.split(chr(10)))} 行)"
                file_tokens = estimate_token_cost(content)
            
            context_parts.append(f"### 文件: {file_path}\n```\n{content}\n```")
            total_tokens += file_tokens
            
            if total_tokens >= max_tokens:
                context_parts.append(f"\n⚠️ 已达到 token 预算上限 ({max_tokens})，剩余文件未加载")
                break
        except Exception as e:
            context_parts.append(f"### 文件: {file_path}\n❌ 读取失败: {e}")
    
    return '\n\n'.join(context_parts)


# ─────────────────────────────────────────────
# 模块 6：主流程编排
# ─────────────────────────────────────────────

def run_visual_bug_hunt(
    project_path: str,
    app_path: Optional[str] = None,
    screenshot_path: Optional[str] = None,
    user_description: str = "",
    output_dir: str = "bug_reports"
) -> dict:
    """
    主入口：完整的 Visual Bug Hunt 流程
    
    参数:
        project_path: 项目代码目录
        app_path: App 可执行路径（.app / .py），若提供则自动启动截图
        screenshot_path: 用户提供的截图路径（与 app_path 二选一）
        user_description: 用户描述的问题
        output_dir: 报告输出目录
    
    返回: Bug 报告字典
    """
    os.makedirs(output_dir, exist_ok=True)
    report = {
        "project_path": project_path,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "user_description": user_description,
        "screenshots": {},
        "vision_bugs": [],
        "code_locations": [],
        "static_analysis": {},
        "fix_suggestions": [],
        "token_usage": {"estimated": 0}
    }
    
    # Step 1: 获取截图
    print("📸 Step 1: 获取 App 截图...")
    if app_path and not screenshot_path:
        try:
            proc, screenshot_path = launch_app_and_capture(app_path)
            report["screenshots"]["initial"] = screenshot_path
            report["runtime_logs"] = capture_runtime_logs(proc)
            print(f"  ✅ 截图已保存: {screenshot_path}")
        except Exception as e:
            print(f"  ⚠️ 自动截图失败: {e}，请提供截图路径")
    elif screenshot_path:
        report["screenshots"]["user_provided"] = screenshot_path
        print(f"  ✅ 使用用户提供截图: {screenshot_path}")
    
    # Step 2: Vision 分析（需要外部调用 understand_media）
    print("\n👁️ Step 2: Vision 分析截图...")
    vision_prompt = build_vision_prompt(user_description)
    report["vision_prompt"] = vision_prompt
    report["vision_screenshot"] = screenshot_path
    print(f"  📋 Vision Prompt 已生成，请调用 understand_media 分析截图")
    print(f"  截图路径: {screenshot_path}")
    
    # Step 3: 静态代码分析（不依赖 Vision，立即执行）
    print("\n🔍 Step 3: 静态代码分析...")
    
    disabled = analyze_disabled_widgets(project_path)
    report["static_analysis"]["disabled_widgets"] = disabled
    if disabled:
        print(f"  ⚠️ 发现 {len(disabled)} 个被禁用的组件（可能导致点击无响应）:")
        for d in disabled:
            print(f"     📍 {d['file']}:{d['line']} → {d['code']}")
    else:
        print("  ✅ 未发现被强制禁用的组件")
    
    duplicate = detect_duplicate_renders(project_path)
    report["static_analysis"]["duplicate_renders"] = duplicate
    if duplicate:
        print(f"  ⚠️ 发现 {len(duplicate)} 处可能的重复渲染:")
        for d in duplicate:
            print(f"     📍 {d['file']}:{d['line']} → {d['warning']}")
    else:
        print("  ✅ 未发现明显的重复渲染问题")
    
    # Step 4: 输出报告
    report_path = os.path.join(output_dir, f"bug_report_{int(time.time())}.json")
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"\n📊 Bug 报告已保存: {report_path}")
    
    return report


# ─────────────────────────────────────────────
# CLI 入口
# ─────────────────────────────────────────────

def main():
    """CLI 入口点"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Visual Bug Hunter - AI 视觉 Bug 定位工具")
    parser.add_argument("project_path", help="项目代码目录路径")
    parser.add_argument("--app", help="App 可执行路径（.app 或 .py）")
    parser.add_argument("--screenshot", help="用户提供的截图路径")
    parser.add_argument("--desc", default="", help="用户描述的问题")
    parser.add_argument("--output", default="bug_reports", help="报告输出目录")
    
    args = parser.parse_args()
    
    result = run_visual_bug_hunt(
        project_path=args.project_path,
        app_path=args.app,
        screenshot_path=args.screenshot,
        user_description=args.desc,
        output_dir=args.output
    )
    
    print("\n" + "="*50)
    print("🎯 静态分析摘要")
    print("="*50)
    disabled_count = len(result["static_analysis"].get("disabled_widgets", []))
    duplicate_count = len(result["static_analysis"].get("duplicate_renders", []))
    print(f"  禁用组件检测: {disabled_count} 个问题")
    print(f"  重复渲染检测: {duplicate_count} 个问题")
    print(f"  总计: {disabled_count + duplicate_count} 个潜在 Bug")

if __name__ == "__main__":
    main()
