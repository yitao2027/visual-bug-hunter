"""
Visual Bug Hunter - MCP Server Adapter
Exposes visual bug hunting capabilities as MCP tools.
"""

import os
import json
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
from src.core.analyzer import capture_screenshot, build_vision_prompt
from src.core.locator import locate_code_for_bug, analyze_disabled_widgets

app = Server("visual-bug-hunter")

@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="analyze_ui_bug",
            description="Analyze a screenshot to identify UI bugs and locate the corresponding code.",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_path": {"type": "string", "description": "Path to the project directory"},
                    "screenshot_path": {"type": "string", "description": "Path to the screenshot file"},
                    "user_description": {"type": "string", "description": "User's description of the problem"}
                },
                "required": ["project_path"]
            }
        ),
        Tool(
            name="scan_disabled_widgets",
            description="Scan the project for UI components that are programmatically disabled.",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_path": {"type": "string", "description": "Path to the project directory"}
                },
                "required": ["project_path"]
            }
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    if name == "analyze_ui_bug":
        project_path = arguments.get("project_path")
        screenshot_path = arguments.get("screenshot_path")
        user_desc = arguments.get("user_description", "")
        
        # 1. Capture screenshot if not provided
        if not screenshot_path:
            screenshots_dir = os.path.join(project_path, "screenshots")
            os.makedirs(screenshots_dir, exist_ok=True)
            screenshot_path = os.path.join(screenshots_dir, "mcp_capture.png")
            capture_screenshot(screenshot_path)
        
        # 2. Build prompt for Vision model (returned as instruction for the AI agent)
        prompt = build_vision_prompt(user_desc)
        
        # 3. Static analysis
        disabled = analyze_disabled_widgets(project_path)
        
        result = {
            "action": "analyze_ui_bug",
            "vision_prompt": prompt,
            "screenshot_path": screenshot_path,
            "static_findings": {
                "disabled_widgets": disabled
            },
            "next_step": "Please use the 'understand_media' tool on the screenshot_path with the vision_prompt to identify specific bugs."
        }
        return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]

    elif name == "scan_disabled_widgets":
        project_path = arguments.get("project_path")
        findings = analyze_disabled_widgets(project_path)
        return [TextContent(type="text", text=json.dumps(findings, ensure_ascii=False, indent=2))]
    
    else:
        raise ValueError(f"Unknown tool: {name}")

def main():
    """Entry point for the MCP server."""
    import asyncio
    async def run():
        async with stdio_server() as (read_stream, write_stream):
            await app.run(read_stream, write_stream, app.create_initialization_options())
    asyncio.run(run())

if __name__ == "__main__":
    main()
