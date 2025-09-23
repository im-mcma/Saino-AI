# -*- coding: utf-8 -*-
# tools/base.py (Titan Edition)

from abc import ABC, abstractmethod
from typing import Any, Dict, Type, Optional, Literal, Callable, List
from pydantic import BaseModel, Field
from google.generativeai.types import FunctionDeclaration
from fastapi import APIRouter
import logging

logger = logging.getLogger(__name__)

# --- Enums and Metadata Models ---

class AccessLevel:
    AI_ONLY = "ai_only"
    UI_ONLY = "ui_only"
    BOTH = "both"
    DISABLED = "disabled"

class ToolMeta(BaseModel):
    name: str = Field(..., description="Unique name of the tool, in snake_case.")
    description: str = Field(..., description="Description for the AI model.")
    parameters: Optional[Type[BaseModel]] = Field(None, description="Pydantic model for input parameters.")
    access_level: str = Field(AccessLevel.AI_ONLY, description="Access level for the tool.")
    has_dedicated_page: bool = Field(False, description="Whether this tool provides a dedicated API router.")
    page_endpoint: Optional[str] = Field(None, description="The URL prefix for the dedicated page router.")

class ToolFrontendComponent(BaseModel):
    """Defines the UI component for a tool to be rendered dynamically on the frontend."""
    html: str = Field(..., description="HTML content for the component (e.g., a button or a form).")
    js: Optional[str] = Field(None, description="Associated JavaScript for interactivity (using Alpine.js).")
    css: Optional[str] = Field(None, description="Scoped CSS styles for this component.")
    placement: Literal["toolbar", "sidebar_widget", "message_action"] = Field("toolbar", description="Where to render the component.")

# --- Abstract Base Class for All Tools ---

class BaseTool(ABC):
    """
    Advanced abstract base class for self-contained tools.
    Each tool can define its own logic, AI declaration, and even UI components.
    """
    registry: Dict[str, Type["BaseTool"]] = {}
    META: ToolMeta

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if hasattr(cls, 'META') and isinstance(cls.META, ToolMeta):
            if cls.META.access_level != AccessLevel.DISABLED:
                cls.registry[cls.META.name] = cls
            else:
                # Log disabled tools if needed
                pass
        elif cls.__name__ != 'BaseTool':
            logger.warning(f"Tool class '{cls.__name__}' lacks a valid META attribute and will not be registered.")

    def __init__(self, db, user, **kwargs):
        self.db = db
        self.user = user

    @abstractmethod
    async def _execute(self, stream_callback: Callable[[str], None], **kwargs: Any) -> Dict:
        """
        The core execution logic of the tool.
        - stream_callback: An async function to send real-time updates to the client.
        Must be implemented by child classes.
        """
        pass

    async def execute(self, stream_callback: Callable[[str], None], **kwargs: Any) -> Dict:
        """Validates input parameters and calls the core execution logic."""
        if not self.META:
            return {"status": "error", "message": "Tool META is not defined."}

        params_model = self.META.parameters
        validated_params = {}
        if params_model:
            try:
                validated_params = params_model(**kwargs).model_dump()
            except Exception as e:
                logger.error(f"Validation error in tool '{self.META.name}': {e}")
                return {"status": "error", "message": f"Invalid parameters: {e}"}
        
        try:
            result = await self._execute(stream_callback=stream_callback, **validated_params)
            return {"status": "success", "result": result}
        except Exception as e:
            logger.exception(f"Error executing tool '{self.META.name}': {e}")
            return {"status": "error", "message": str(e)}

    def get_declaration(self) -> Optional[FunctionDeclaration]:
        """Generates the FunctionDeclaration for Google's Generative AI."""
        if self.META.access_level not in [AccessLevel.AI_ONLY, AccessLevel.BOTH]:
            return None
        
        schema = self.META.parameters.model_json_schema() if self.META.parameters else {}
        
        return FunctionDeclaration(
            name=self.META.name,
            description=self.META.description,
            parameters=schema
        )

    def get_frontend_component(self) -> Optional[ToolFrontendComponent]:
        """
        Returns the UI component definition for this tool.
        Should be overridden by child classes that have a UI presence.
        """
        return None

    def get_page_router(self) -> Optional[APIRouter]:
        """
        Returns a FastAPI APIRouter for a dedicated tool page.
        Should be overridden by child classes that need custom API endpoints.
        """
        return None

    @property
    def is_ai_enabled(self) -> bool:
        return self.META.access_level in [AccessLevel.AI_ONLY, AccessLevel.BOTH]

    @property
    def is_ui_enabled(self) -> bool:
        return self.META.access_level in [AccessLevel.UI_ONLY, AccessLevel.BOTH]
