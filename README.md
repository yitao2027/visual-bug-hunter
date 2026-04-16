# Visual Bug Hunter - Universal MCP Skill

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![MCP Compatible](https://img.shields.io/badge/MCP-Compatible-blue)](https://modelcontextprotocol.io/)

**让 AI 像人一样“眼睛看 + 手点击”来调试 UI。**

`visual-bug-hunter` 是一个通用的 **MCP (Model Context Protocol)** 技能，旨在解决 Vibe Coding 时代 AI 无法自检 UI 效果的痛点。它不局限于任何特定平台，可无缝集成到 **悟空 (Wukong)**、**WorkBuddy**、**Cursor**、**Windsurf** 或任何支持 MCP 的 AI 助手中。

## 🚀 核心能力

*   **视觉感知**：自动截取当前 App 或网页快照。
*   **智能分析**：利用 Vision 模型识别布局错位、元素重叠、样式异常等 UI Bug。
*   **代码定位**：精准扫描项目源码，将视觉问题映射到具体的代码行。
*   **最小化修复**：生成省 Token 的最小 Diff 补丁，避免 AI 重写整个文件。
*   **闭环验证**：支持修复后的二次截图验证。

## 🛠️ 安装与配置

### 1. 安装依赖
```bash
pip install visual-bug-hunter-mcp
```

### 2. 在 AI 工具中配置 MCP
在你的 AI 助手（如 Cursor, Claude Desktop, Wukong）的 `mcp_config.json` 中添加：

```json
{
  "mcpServers": {
    "visual-bug-hunter": {
      "command": "python",
      "args": ["-m", "src.adapters.mcp_server"]
    }
  }
}
```

## 💡 使用示例

在对话中直接触发：
> “帮我看看这个界面哪里重叠了？”
> “为什么这个按钮点不了？”

AI 将自动调用 `analyze_ui_bug` 工具，完成截图、分析和代码定位。

## 📂 项目结构

```text
visual-bug-hunter-mcp/
├── src/
│   ├── core/               # 核心业务逻辑（视觉分析、代码定位）
│   └── adapters/           # 各平台适配器 (MCP, CLI)
├── pyproject.toml          # 现代 Python 项目配置
└── README.md
```

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！让我们一起完善 AI 时代的 UI 调试体验。

---
*Author: Yitao | GitHub: [yitao2027](https://github.com/yitao2027)*
