from __future__ import annotations

from ..server import mcp


@mcp.tool()
async def custom_echo(text: str) -> str:
    """Example custom tool that echoes the provided text."""
    return f"custom echo: {text}"
