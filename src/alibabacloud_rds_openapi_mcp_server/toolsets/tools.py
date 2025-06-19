from __future__ import annotations

from types import ModuleType

from .toolsets import ToolsetManager


def load_groups(manager: ToolsetManager, server_module: ModuleType) -> None:
    """Assign selected tools to groups using ``ToolsetManager``."""

    if hasattr(server_module, "describe_db_instances"):
        manager.set_group(server_module.describe_db_instances, "rds")
    if hasattr(server_module, "describe_db_instance_attribute"):
        manager.set_group(server_module.describe_db_instance_attribute, "rds")

    # Load tools defined in separate modules
    from . import rds_custom

    manager.set_group(rds_custom.custom_echo, "custom")
