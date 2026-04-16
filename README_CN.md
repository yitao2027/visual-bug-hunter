# Visual Bug Hunter (视觉 Bug 猎人) 🕵️‍♂️

[![Python Version](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**专为 Vibe Coding 用户设计的 GUI 视觉调试工具。** 

让 AI 像人一样“眼睛看 + 手点击”，精准定位 UI Bug，生成最小化代码修复方案，并自动截图验证。

---

## 🚀 为什么需要它？

在用 AI 开发 GUI 应用（Tauri, Electron, Tkinter, Qt）时，你经常遇到：
- **“按钮点不了！”** → 是被禁用了？还是事件处理器没写对？
- **“元素重叠了！”** → AI 是不是把同一个组件渲染了两次？
- **“布局错位了！”** → 几百行代码里到底哪一行样式写错了？

Visual Bug Hunter 通过闭环流程解决这些问题：
1. **看**：利用 Vision AI 分析截图，识别视觉异常。
2. **点**：程序化模拟 UI 交互，测试响应。
3. **找**：静态扫描代码，定位常见的 UI 反模式。
4. **修**：生成最小 Diff 修复建议（而不是重写整个文件）。
5. **验**：再次截图，证明修复确实生效。

---

## 📦 安装

```bash
pip install visual-bug-hunter
```

或者从源码安装：
```bash
git clone https://github.com/yitao2027/visual-bug-hunter.git
cd visual-bug-hunter
pip install -e .
```

---

## 🛠️ 使用方法

### 1. 静态扫描项目
在不运行 App 的情况下查找潜在的 UI Bug：
```bash
vbh scan /path/to/your/project
```

### 2. 分析截图
提供一张截图来检测视觉异常：
```bash
vbh analyze --screenshot bug.png --project /path/to/project
```

### 3. 启动并测试 App
自动启动 Python/Tkinter 或 macOS App 并捕获初始状态：
```bash
vbh test --app my_app.py
```

---

## 🔍 核心功能

| 模块 | 功能 |
|------|------|
| **Utils** | 跨平台截图捕获 (`screencapture`, `scrot`)。 |
| **Analyzer** | 针对 UI Bug 检测优化的 Vision AI Prompt 模板。 |
| **Locator** | 基于 AST 的代码扫描，检测禁用组件和重复渲染。 |
| **Reporter** | 生成包含代码片段的结构化 JSON 报告。 |
| **CLI** | 简单易用的命令行入口。 |

### 专项检测器
- **禁用组件检测**：查找 `setEnabled(False)`, `state=DISABLED` 等。
- **重复渲染检测**：发现同一组件被多次调用 `.pack()` 或 `.grid()`。

---

## 🤝 参与贡献

欢迎提交 PR！请先阅读 [BUG_RULES.md](BUG_RULES.md) 了解我们的核心工作流。

---

## 📄 许可证

本项目采用 MIT 许可证。详见 `LICENSE` 文件。

---

## 🌟 致谢

- 专为 **Vibe Coding** 社区打造。
- 灵感来源于 AI Agent 自我验证 UI 工作的需求。
