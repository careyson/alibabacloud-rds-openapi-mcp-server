import importlib
import sys
from pathlib import Path
import types

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

# Provide a minimal stub for the ``mcp`` package used during tests.
fastmcp_stub = types.ModuleType("mcp.server.fastmcp")

class FastMCP:
    def __init__(self, *args, **kwargs):
        self._tools = []

    @staticmethod
    def tool(mcp, *args, **kwargs):
        def decorator(func):
            mcp._tools.append(func)
            return func
        return decorator

fastmcp_stub.FastMCP = FastMCP
server_pkg_stub = types.ModuleType("mcp.server")
server_pkg_stub.fastmcp = fastmcp_stub
mcp_stub = types.ModuleType("mcp")
mcp_stub.server = server_pkg_stub
sys.modules.setdefault("mcp", mcp_stub)
sys.modules.setdefault("mcp.server", server_pkg_stub)
sys.modules.setdefault("mcp.server.fastmcp", fastmcp_stub)

from alibabacloud_rds_openapi_mcp_server.toolsets.toolsets import (
    ToolsetMCP,
    initialize_toolsets,
)


def make_server_module():
    """Create a dummy server module with two tools registered."""
    server = types.ModuleType("alibabacloud_rds_openapi_mcp_server.server")
    server.mcp = ToolsetMCP("dummy")
    server.toolset_manager = server.mcp.manager

    @server.mcp.tool()
    async def describe_db_instances():
        pass

    @server.mcp.tool()
    async def describe_db_instance_attribute():
        pass

    server.describe_db_instances = describe_db_instances
    server.describe_db_instance_attribute = describe_db_instance_attribute

    sys.modules["alibabacloud_rds_openapi_mcp_server.server"] = server
    return server


def make_rds_custom(server):
    module = types.ModuleType(
        "alibabacloud_rds_openapi_mcp_server.toolsets.rds_custom"
    )

    @server.mcp.tool()
    async def custom_echo(text: str):
        return text

    module.custom_echo = custom_echo
    sys.modules[
        "alibabacloud_rds_openapi_mcp_server.toolsets.rds_custom"
    ] = module
    return module


@pytest.fixture(autouse=True)
def dummy_env(monkeypatch):
    server = make_server_module()
    make_rds_custom(server)
    yield server


def test_load_groups_should_assign_tools_to_correct_groups_when_called(dummy_env):
    server = dummy_env
    from alibabacloud_rds_openapi_mcp_server.toolsets.tools import load_groups

    load_groups(server.toolset_manager, server)

    groups = server.toolset_manager.groups
    assert "rds" in groups
    assert server.describe_db_instances in [i.func for i in groups["rds"]]
    assert server.describe_db_instance_attribute in [i.func for i in groups["rds"]]
    assert "custom" in groups
    assert any(i.func.__name__ == "custom_echo" for i in groups["custom"])


def test_initialize_toolsets_should_enable_default_group_when_toolsets_none(dummy_env):
    server = dummy_env

    initialize_toolsets(None)

    assert server.toolset_manager.enabled == {"default"}


def test_manager_should_report_enabled_groups_and_tools_when_queried(dummy_env):
    server = dummy_env
    from alibabacloud_rds_openapi_mcp_server.toolsets.tools import load_groups

    load_groups(server.toolset_manager, server)
    server.toolset_manager.enable("rds", "custom")

    assert set(server.toolset_manager.get_registered_groups()) >= {"default", "rds", "custom"}
    assert set(server.toolset_manager.get_enabled_groups()) == {"rds", "custom"}
    enabled = server.toolset_manager.get_enabled_tools()
    assert "rds" in enabled and server.describe_db_instances in enabled["rds"]
    assert "custom" in enabled and any(f.__name__ == "custom_echo" for f in enabled["custom"])
