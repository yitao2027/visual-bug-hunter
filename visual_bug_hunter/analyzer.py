"""
analyzer.py — Vision-based UI bug analysis
Provides prompts and parsers for LLM/Vision model integration.
"""

from typing import List, Dict, Optional


# ─────────────────────────────────────────────────────────────────
# Vision Prompt — works with any Vision-capable LLM
# (GPT-4o, Claude 3.5 Sonnet, Qwen-VL, Gemini Pro Vision, etc.)
# ─────────────────────────────────────────────────────────────────

VISION_ANALYSIS_PROMPT = """\
Please carefully analyze this app screenshot and identify all UI bugs and visual anomalies.

For each issue found, output in EXACTLY this format:
---
Bug ID: BUG-XXX
Type: [layout-broken / element-overlap / click-unresponsive / style-error / duplicate-render / other]
Location: Where on screen (e.g. "top-left search bar", "right-side chat bubble")
Description: What you see that looks wrong (e.g. "two identical bubbles stacked on top of each other")
Severity: [HIGH / MEDIUM / LOW]
Likely Cause: UI-level hypothesis (e.g. "component rendered twice")
---

If no obvious bugs are found, respond with: "No visible UI issues detected."
"""

VISION_ANALYSIS_PROMPT_CN = """\
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


def build_vision_prompt(user_description: str = "", lang: str = "en") -> str:
    """
    Build the Vision analysis prompt, optionally appending user's description.

    Args:
        user_description: Free-text description of the issue from the user
        lang: "en" for English prompt, "cn" for Chinese prompt

    Returns:
        Complete prompt string ready to send to a Vision LLM
    """
    base = VISION_ANALYSIS_PROMPT if lang == "en" else VISION_ANALYSIS_PROMPT_CN
    if user_description:
        if lang == "en":
            base += f"\n\nAdditional context from user: {user_description}"
        else:
            base += f"\n\n用户额外说明：{user_description}"
    return base


def parse_vision_bugs(vision_output: str) -> List[Dict]:
    """
    Parse the structured output from a Vision model into a list of bug dicts.

    Args:
        vision_output: Raw text output from the Vision LLM

    Returns:
        List of bug dicts with keys: bug_id, type, location, description,
        severity, likely_cause
    """
    bugs: List[Dict] = []
    current: Dict = {}

    # Support both English and Chinese field names
    field_map = {
        "Bug ID:": "bug_id",
        "Type:": "type",
        "Location:": "location",
        "Description:": "description",
        "Severity:": "severity",
        "Likely Cause:": "likely_cause",
        # Chinese aliases
        "问题类型:": "type",
        "位置描述:": "location",
        "视觉描述:": "description",
        "严重程度:": "severity",
        "可能原因:": "likely_cause",
    }

    for line in vision_output.splitlines():
        line = line.strip()
        if line.startswith("Bug ID:"):
            if current:
                bugs.append(current)
            current = {"bug_id": line.replace("Bug ID:", "").strip()}
            continue
        for prefix, key in field_map.items():
            if line.startswith(prefix) and prefix != "Bug ID:":
                current[key] = line[len(prefix):].strip()
                break

    if current and "bug_id" in current:
        bugs.append(current)

    # Sort: HIGH first
    severity_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    bugs.sort(key=lambda b: severity_order.get(b.get("severity", "LOW"), 2))

    return bugs


def analyze_screenshot(
    screenshot_path: str,
    user_description: str = "",
    lang: str = "en",
    llm_provider: Optional[str] = None,
) -> Dict:
    """
    Analyze a screenshot for UI bugs.

    This function returns the prompt and metadata needed to call your Vision LLM.
    Actual LLM invocation is left to the caller so this library stays
    provider-agnostic (works with OpenAI, Anthropic, Qwen, Gemini, local models…).

    Args:
        screenshot_path: Path to the screenshot image
        user_description: Optional user-provided bug description
        lang: Prompt language ("en" or "cn")
        llm_provider: Optional hint for the caller ("openai", "anthropic", "qwen")

    Returns:
        Dict with keys:
            - prompt: The Vision prompt to send
            - screenshot_path: Confirmed path to the image
            - instructions: How to call your Vision LLM with this prompt
    """
    import os
    if not os.path.exists(screenshot_path):
        raise FileNotFoundError(f"Screenshot not found: {screenshot_path}")

    prompt = build_vision_prompt(user_description, lang=lang)

    instructions = {
        "openai": (
            "from openai import OpenAI; client = OpenAI()\n"
            "import base64\n"
            "with open(screenshot_path, 'rb') as f:\n"
            "    img_b64 = base64.b64encode(f.read()).decode()\n"
            "response = client.chat.completions.create(\n"
            "    model='gpt-4o',\n"
            "    messages=[{'role':'user','content':[\n"
            "        {'type':'text','text': prompt},\n"
            "        {'type':'image_url','image_url':{'url':f'data:image/png;base64,{img_b64}'}}\n"
            "    ]}]\n"
            ")"
        ),
        "anthropic": (
            "import anthropic, base64\n"
            "client = anthropic.Anthropic()\n"
            "with open(screenshot_path, 'rb') as f:\n"
            "    img_b64 = base64.b64encode(f.read()).decode()\n"
            "response = client.messages.create(\n"
            "    model='claude-3-5-sonnet-20241022', max_tokens=2048,\n"
            "    messages=[{'role':'user','content':[\n"
            "        {'type':'image','source':{'type':'base64','media_type':'image/png','data':img_b64}},\n"
            "        {'type':'text','text': prompt}\n"
            "    ]}]\n"
            ")"
        ),
    }

    return {
        "prompt": prompt,
        "screenshot_path": screenshot_path,
        "instructions": instructions.get(llm_provider or "", instructions["openai"]),
        "tip": (
            "Pass `prompt` + the image to any Vision-capable LLM. "
            "Then feed the response text into parse_vision_bugs() to get structured results."
        ),
    }
