# -*- coding: utf-8 -*-
"""Utility classes to manage groups of MCP tools."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Tuple

from mcp.server.fastmcp import FastMCP


@dataclass
class _ToolInfo:
    func: Callable
    args: Tuple[Any, ...]
    kwargs: Dict[str, Any]
    group: str


class ToolsetManager:
    """Manage tool groups and register them on demand."""

    def __init__(self) -> None:
        # Mapping of tool function to its metadata for easy regrouping
        self._tools: Dict[Callable, _ToolInfo] = {}
        self.groups: Dict[str, List[_ToolInfo]] = {}
        self.enabled: set[str] = set()

    def add_tool(
        self,
        func: Callable,
        group: str = "default",
        args: Tuple[Any, ...] | None = None,
        kwargs: Dict[str, Any] | None = None,
    ) -> None:
        """Add a tool to a group without registering it."""
        if args is None:
            args = ()
        if kwargs is None:
            kwargs = {}
        info = self._tools.get(func)
        if info:
            # remove from previous group list if re-added
            if info.group in self.groups:
                self.groups[info.group] = [i for i in self.groups[info.group] if i.func != func]
        info = _ToolInfo(func=func, args=args, kwargs=kwargs, group=group)
        self._tools[func] = info
        self.groups.setdefault(group, []).append(info)

    def set_group(self, func: Callable, group: str) -> None:
        """Move a registered tool to a different group."""
        info = self._tools.get(func)
        if info is None:
            # tool not registered yet; add directly
            self.add_tool(func, group=group)
            return
        if info.group == group:
            return
        # remove from old group
        old_group = info.group
        if old_group in self.groups:
            self.groups[old_group] = [i for i in self.groups[old_group] if i.func != func]
        info.group = group
        self.groups.setdefault(group, []).append(info)

    def enable(self, *groups: str) -> None:
        """Enable one or more groups."""
        for g in groups:
            self.enabled.add(g)

    def get_registered_groups(self) -> List[str]:
        """Return a list of all groups that have tools registered."""
        return list(self.groups.keys())

    def get_enabled_groups(self) -> List[str]:
        """Return a list of currently enabled groups."""
        return list(self.enabled)

    def get_enabled_tools(self) -> Dict[str, List[Callable]]:
        """Return mapping of enabled group name to its tools."""
        result: Dict[str, List[Callable]] = {}
        for name in self.enabled:
            result[name] = [info.func for info in self.groups.get(name, [])]
        return result

    def register_enabled(self, mcp: FastMCP) -> None:
        """Register all tools from enabled groups with the given MCP instance."""
        for info in self._tools.values():
            if info.group in self.enabled:
                FastMCP.tool(mcp, *info.args, **info.kwargs)(info.func)


class ToolsetMCP(FastMCP):
    """FastMCP variant that stores tools in ``ToolsetManager``."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        # Always use a single ``ToolsetManager`` instance per MCP.
        self.manager = ToolsetManager()
        super().__init__(*args, **kwargs)

    def tool(self, *dargs: Any, group: str = "default", **dkwargs: Any):
        """Decorate a tool and store it for later registration."""

        def decorator(func: Callable):
            self.manager.add_tool(func, group=group, args=dargs, kwargs=dkwargs)
            return func

        return decorator

    def register_enabled_tools(self) -> None:
        self.manager.register_enabled(self)


def initialize_toolsets(toolsets: list[str] | str | None = None) -> None:
    """Load tool groups and enable selected sets."""

    from .. import server as _server
    from .tools import load_groups

    # Assign tools to their groups once at startup
    load_groups(_server.toolset_manager, _server)

    if toolsets is None:
        enabled = ["default"]
    elif isinstance(toolsets, str):
        enabled = [g.strip() for g in toolsets.split(",") if g.strip()] or ["default"]
    else:
        enabled = list(toolsets) or ["default"]

    _server.toolset_manager.enable(*enabled)
    _server.mcp.register_enabled_tools()
