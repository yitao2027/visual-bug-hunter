# Visual Bug Hunter — Agent 操作手册

> 本文档是 AI Agent 使用本 Skill 时的执行指南，每一步必须严格遵守。

---

## 🚨 核心原则（违反即为失败）

1. **视觉验证优先**：修复代码后，必须截图确认，不得仅凭代码逻辑宣布"修复完成"
2. **最小 Diff 原则**：只修改有问题的行，禁止重构无关代码
3. **单步验证**：每次只改一个 Bug，截图确认后再改下一个
4. **省 Token**：不全量读取项目文件，只加载与当前 Bug 相关的代码片段

---

## 📋 标准执行流程

### Phase 1：问题接收与截图

```
用户反馈 Bug（文字描述 + 截图）
    ↓
调用 understand_media(screenshot_path, question=VISION_ANALYSIS_PROMPT)
    ↓
解析输出，生成结构化 Bug 清单
    ↓
按严重程度排序：HIGH > MEDIUM > LOW
```

**关键约束：** 如果用户没有提供截图，必须先截图再分析，不得靠猜测。

---

### Phase 2：代码定位（省 Token 版）

```
对每个 Bug（按优先级逐个处理）：
    ↓
从 Bug 描述提取 UI 关键词（搜索/按钮/Tab/输入框/重叠）
    ↓
调用 grep_search 搜索相关代码（不全量读文件）
    ↓
只读取命中行的上下文（前后 5 行），不读整个文件
    ↓
输出：文件路径 + 行号 + 问题代码片段
```

**Token 预算：** 每个 Bug 定位阶段最多消耗 1000 token（约 4000 字符代码上下文）

---

### Phase 3：修复执行

```
确认代码位置后：
    ↓
生成最小 Diff（只改目标行，不动其他代码）
    ↓
用 modify_file 精确替换（old_string → new_string）
    ↓
【必须执行】重新截图
    ↓
调用 understand_media 对比截图，确认 Bug 是否消失
    ↓
如果消失：标记为 ✅ FIXED，继续下一个 Bug
如果未消失：重新分析，不得重复同样的修复方式
```

**⛔ 禁止行为：**
- 修复后不截图就宣布"已修复"
- 同一个 Bug 用同样方式修了超过 2 次
- 一次性批量修改多个文件

---

### Phase 4：防臃肿自检

修复完成后，对修改过的文件执行以下检查：

```python
检查项目：
□ 是否引入了新的未使用变量/函数？
□ 是否有重复定义的函数或类？
□ 是否有注释掉但未删除的旧代码？
□ 修改行数是否超过必要范围（>10行视为可疑）？
□ 是否有 TODO/FIXME/HACK 注释遗留？
```

如果任何一项为 YES，必须清理后再提交。

---

## 🔧 针对常见 Bug 类型的快速定位指南

### 类型 1：按钮/输入框点不了

**优先搜索：**
```
grep_search: "setEnabled(False)" / "state=DISABLED" / "disabled=True"
```
**常见原因：** 初始化时被禁用，忘记在合适时机启用

**修复模板：**
```python
# 错误
self.search_input.setEnabled(False)
# 修复
self.search_input.setEnabled(True)
```

---

### 类型 2：元素重复显示（重叠两次）

**优先搜索：**
```
grep_search: ".pack(" / ".grid(" / ".place(" / "add_widget("
```
**常见原因：** 同一个组件的布局方法被调用了两次（如在 `__init__` 和 `setup_ui` 中各调用一次）

**修复模板：**
```python
# 错误：pack 被调用两次
self.bubble.pack()   # 第 45 行
# ... 其他代码 ...
self.bubble.pack()   # 第 89 行（重复！删除这行）
```

---

### 类型 3：Tab 重复

**优先搜索：**
```
grep_search: "add_tab" / "insert_tab" / "notebook.add" / "tabview.add"
```
**常见原因：** Tab 初始化在循环中或被调用两次

---

## 📊 Bug 报告输出模板

```markdown
## Visual Bug Report

**分析时间：** 2026-04-16 11:38
**截图路径：** screenshots/app_20260416.png

---

### BUG-001 ⭕ [HIGH] 搜索输入框点击无响应

**视觉描述：** 左上角搜索框有红圈标注，点击后无任何响应
**代码位置：** `src/ui/sidebar.py:87`
**问题代码：**
```python
self.search_input.setEnabled(False)  # ← 问题所在
```
**修复方案：** 将 `False` 改为 `True`
**验证方式：** 修复后截图确认输入框可点击

---

### BUG-002 ⭕ [HIGH] 聊天气泡重复显示

**视觉描述：** 右侧同一条消息出现两个气泡
**代码位置：** `src/ui/chat_view.py:134`
**问题代码：**
```python
self.bubble_frame.pack(fill="x", padx=10)  # 第 89 行（第一次）
# ... 省略 ...
self.bubble_frame.pack(fill="x", padx=10)  # 第 134 行（重复！）
```
**修复方案：** 删除第 134 行的重复 pack 调用
**验证方式：** 修复后截图确认只显示一个气泡
```

---

## ⚡ 省 Token 检查清单（每次修复前必查）

- [ ] 是否只读取了必要的代码文件？（不超过 3 个文件）
- [ ] 是否使用了 grep_search 而不是全量读取？
- [ ] 修复 Diff 是否控制在 10 行以内？
- [ ] 是否避免了重构无关代码？
