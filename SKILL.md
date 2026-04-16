---
name: visual-bug-hunter
description: 视觉 Bug 定位与修复 Skill。当用户描述 GUI App 或 Web App 存在视觉 Bug（按钮点不了、元素重叠、布局错位、样式异常），或 AI 反复修 Bug 但无法自检验证效果，或需要对应用进行 UI 自动化测试时触发。通过截图感知 + UI 交互测试 + 控制台捕获 + 代码精准定位的闭环流程，让 AI 像人一样"眼睛看 + 手点击"来发现和修复 Bug，并以省 token 的最小 Diff 方式生成代码修复方案。不适用于纯后端逻辑 Bug、数据库问题或无 UI 界面的 API 报错。
---

# Visual Bug Hunter Skill

## 一句话定位
让 AI 像人一样「眼睛看 + 手点击」来测试 GUI/Web App，精准定位 Bug 并映射到代码行，同时以省 token 的方式生成和自检代码。

## 触发条件
当用户满足以下任意一项时触发本 Skill：
- 描述 GUI App / Web App 存在视觉 Bug（布局错位、按钮点不了、元素重叠、样式异常）
- 要求对已有应用进行自动化 UI 测试或自检
- 要求 AI 帮助修 Bug 但反复改不好（AI 只能读代码、无法看到界面效果）
- 要求生成代码时防止臃肿、节省 token

**不触发场景：** 纯后端逻辑 Bug、数据库问题、API 报错（无 UI 界面）

---

## 核心能力矩阵

| 能力 | 说明 | 技术实现 |
|------|------|---------|
| 👁️ 视觉感知 | 截图 App 界面，Vision 模型识别 UI 异常 | macOS screencapture / pyautogui + Vision |
| 🖱️ UI 交互测试 | 自动点击按钮/输入框，捕获响应 | pyautogui / AppleScript / accessibility API |
| 🔍 控制台捕获 | 捕获 App 运行时的 stderr/stdout/崩溃日志 | subprocess + log tail |
| 📍 代码精准定位 | 将视觉问题映射到具体文件+行号 | grep_search + AST 分析 |
| 🧹 防臃肿生成 | 写代码时遵循最小改动原则，禁止无关重构 | Diff-only 策略 + token 预算控制 |
| ✅ 视觉自检 | 修改后自动截图对比，确认 Bug 是否消失 | 截图前后对比 + Vision 二次验证 |

---

## 工作流（标准 Bug 修复流程）

```
Step 1: 接收问题描述 + 用户截图（可选）
         ↓
Step 2: 启动目标 App，全屏截图
         ↓
Step 3: Vision 分析截图，生成「视觉 Bug 清单」（位置 + 类型 + 严重度）
         ↓
Step 4: 对每个 Bug 执行 UI 交互测试（点击、输入、滚动）
         ↓
Step 5: 捕获运行时日志（stderr/崩溃/异常）
         ↓
Step 6: 将视觉问题 → 代码定位（文件路径 + 行号 + 问题代码片段）
         ↓
Step 7: 输出「精准 Bug 报告」（问题描述 + 截图证据 + 代码位置）
         ↓
Step 8: 按「最小 Diff 原则」修复代码（只改有问题的行，不重构无关代码）
         ↓
Step 9: 重新截图，Vision 自检验证修复是否生效
         ↓
Step 10: 输出验证报告（修复前后截图对比 + 结论）
```

---

## 省 Token 策略

### 代码生成原则
1. **Diff-only 输出**：只输出需要修改的代码块，不输出整个文件
2. **上下文窗口控制**：每次只加载与 Bug 相关的文件，不全量读取项目
3. **问题优先队列**：先修最高优先级 Bug，逐个验证，不批量盲改
4. **禁止预防性重构**：修 Bug 时严禁顺手重构无关代码（这是 AI 代码臃肿的主因）

### 自检原则
1. **视觉验证优先**：修完必须截图，用眼睛（Vision）确认，不只靠代码逻辑推理
2. **单一变量原则**：每次只改一处，截图确认后再改下一处
3. **回归检测**：修复后检查周边元素是否受影响

---

## 技术栈

- **截图**：`mcp_runtime system_capabilities screen.capture` (macOS 原生)
- **UI 自动化**：`pyautogui`（跨平台）/ `AppKit` + `accessibility`（macOS 精准）
- **Vision 分析**：`understand_media` (Qwen Omni)
- **代码定位**：`grep_search` + `ast` 模块
- **日志捕获**：`subprocess.Popen` + `stderr` 重定向
- **Diff 生成**：`difflib` + `unified_diff`

---

## 输出格式

### Bug 报告（JSON）
```json
{
  "bug_id": "BUG-001",
  "visual_description": "搜索输入框点击无响应",
  "location_on_screen": {"x": 120, "y": 45, "w": 200, "h": 30},
  "code_location": {
    "file": "src/ui/sidebar.py",
    "line": 87,
    "snippet": "self.search_input.setEnabled(False)"
  },
  "root_cause": "setEnabled(False) 导致输入框被禁用",
  "fix": "将 False 改为 True，或移除该行",
  "severity": "HIGH",
  "screenshot_evidence": "screenshots/bug_001_before.png"
}
```

### 修复验证报告
```
✅ BUG-001 搜索输入框 - 已修复（截图对比确认）
❌ BUG-002 重复Tab - 未修复（截图仍显示两个气泡）
```
