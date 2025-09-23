# -*- coding: utf-8 -*-
from pathlib import Path
import importlib.util
import sys
from .config import logger
from typing import Dict, Type

class ToolManager:
    """
    Dynamically discovers and loads tools from the 'tools' directory.
    It populates the registry defined in the BaseTool class.
    """
    def __init__(self, tool_dir: str = "tools"):
        self.tool_dir = Path(tool_dir)
        # The actual registry is a class variable on BaseTool,
        # this class just triggers the loading process.
        from tools.base import BaseTool
        self.registry: Dict[str, Type[BaseTool]] = BaseTool.registry

    def load_tools(self):
        """Loads all tool modules from the specified directory."""
        if not self.tool_dir.is_dir():
            logger.warning(f"Tools directory '{self.tool_dir}' not found. No tools will be loaded.")
            return

        logger.info(f"Loading tools from '{self.tool_dir}'...")
        for file in self.tool_dir.glob("*.py"):
            if file.stem in ("__init__", "base"):
                continue

            module_name = f"{self.tool_dir.name}.{file.stem}"
            try:
                if module_name not in sys.modules:
                    spec = importlib.util.spec_from_file_location(module_name, file)
                    if spec and spec.loader:
                        module = importlib.util.module_from_spec(spec)
                        sys.modules[module_name] = module
                        spec.loader.exec_module(module)
                        logger.info(f"  -> Module '{file.name}' loaded successfully.")
                    else:
                        logger.warning(f"Could not create module spec for {file.name}")
            except Exception as e:
                logger.error(f"  -> Failed to load module {file.name}: {e}", exc_info=True)
        
        logger.info(f"✅ Tool loading complete. {len(self.registry)} tools registered.")
