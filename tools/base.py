# -*- coding: utf-8 -*-
# tools/base.py

from abc import ABC, abstractmethod
from typing import Any, Dict, Type, Optional, Literal
from enum import Enum, auto
from pydantic import BaseModel, ValidationError, Field
from google.generativeai.types import FunctionDeclaration
import logging
from fastapi import APIRouter # <-- جدید: برای صفحات اختصاصی ابزار

logger = logging.getLogger(__name__)

# Enum برای تعریف سطح دسترسی ابزار
class AccessLevel(Enum):
    AI_ONLY = auto()
    UI_ONLY = auto()
    BOTH = auto()
    DISABLED = auto()

# مدل Pydantic برای تعریف متادیتای ابزار
class ToolMeta(BaseModel):
    name: str = Field(..., description="نام یکتای ابزار به فرمت snake_case.")
    description: str = Field(..., description="توضیحات ابزار برای مدل هوش مصنوعی.")
    parameters: Type[BaseModel] = Field(None, description="مدل Pydantic برای پارامترهای ورودی.")
    access_level: AccessLevel = Field(AccessLevel.AI_ONLY, description="سطح دسترسی ابزار.")
    
    # --- بخش‌های جدید برای UI قدرتمندتر ---
    ui_label: Optional[str] = Field(None, description="برچسب دکمه در رابط کاربری.")
    ui_icon: Optional[str] = Field(None, description="آیکون دکمه (مثلاً از FontAwesome یا SVG).")
    ui_render_type: Literal["button", "icon_button", "link"] = Field("button", description="نحوه نمایش در UI.")
    
    has_dedicated_page: bool = Field(False, description="آیا این ابزار صفحه اختصاصی خود را دارد؟")
    page_endpoint: Optional[str] = Field(None, description="مسیر URL برای صفحه اختصاصی (مثال: /tools/my-tool).")


class BaseTool(ABC):
    """
    کلاس پایه انتزاعی و پیشرفته برای تمام ابزارهای سفارشی.
    - ابزارها را به صورت خودکار بر اساس AccessLevel ثبت می‌کند.
    - از Pydantic برای اعتبارسنجی دقیق پارامترهای ورودی استفاده می‌کند.
    - منطق اجرا (_execute) را از اعتبارسنجی (execute) جدا می‌کند.
    - از دسترسی AI، UI، ترکیبی و حتی صفحات اختصاصی برای ابزارها پشتیبانی می‌کند.
    """

    registry: Dict[str, Type["BaseTool"]] = {}
    META: ToolMeta

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if hasattr(cls, 'META') and isinstance(cls.META, ToolMeta):
            if cls.META.access_level != AccessLevel.DISABLED:
                cls.registry[cls.META.name] = cls
                logger.info(f"ابزار '{cls.META.name}' با سطح دسترسی {cls.META.access_level.name} ثبت شد.")
                if cls.META.has_dedicated_page and not cls.META.page_endpoint:
                    logger.warning(f"ابزار '{cls.META.name}' صفحه اختصاصی دارد اما page_endpoint تعریف نشده است.")
            else:
                logger.info(f"ابزار '{cls.META.name}' غیرفعال است و ثبت نخواهد شد.")
        else:
            # از ثبت کلاس پایه جلوگیری می‌کند
            if cls.__name__ != 'BaseTool':
                logger.warning(f"کلاس '{cls.__name__}' از BaseTool ارث‌بری می‌کند اما META معتبر ندارد. این ابزار ثبت نخواهد شد.")

    def __init__(self, **kwargs):
        pass

    @abstractmethod
    async def _execute(self, **kwargs: Any) -> Dict:
        """
        منطق اصلی اجرای ابزار را پیاده‌سازی می‌کند.
        این متد باید توسط کلاس‌های فرزند پیاده‌سازی شود.
        """
        pass

    async def execute(self, **kwargs: Any) -> Dict:
        """
        پارامترهای ورودی را اعتبارسنجی کرده و منطق اصلی ابزار را اجرا می‌کند.
        این متد نباید بازنویسی شود.
        """
        if self.META is None:
            return {"status": "error", "message": "ابزار فاقد متادیتای META است."}

        if self.META.parameters is None:
            try:
                result = await self._execute(**kwargs)
                return {"status": "success", "result": result}
            except Exception as e:
                logger.exception(f"خطا در اجرای ابزار '{self.META.name}' بدون پارامتر: {e}")
                return {"status": "error", "message": str(e)}

        try:
            validated_params = self.META.parameters(**kwargs)
            result = await self._execute(**validated_params.model_dump())
            return {"status": "success", "result": result}
        except ValidationError as e:
            logger.error(f"خطای اعتبارسنجی در ابزار '{self.META.name}': {e}")
            return {"status": "error", "message": f"پارامترهای نامعتبر: {e.errors()}"}
        except Exception as e:
            logger.exception(f"خطا در اجرای ابزار '{self.META.name}': {e}")
            return {"status": "error", "message": str(e)}

    def get_declaration(self) -> Optional[FunctionDeclaration]:
        """
        FunctionDeclaration مورد نیاز Google Generative AI را از روی اسکیمای Pydantic تولید می‌کند.
        """
        if self.META is None:
            raise AttributeError("META برای این ابزار تعریف نشده است.")
        if self.META.access_level in [AccessLevel.UI_ONLY, AccessLevel.DISABLED]:
            return None

        schema = self.META.parameters.model_json_schema() if self.META.parameters else {}
        
        return FunctionDeclaration(
            name=self.META.name,
            description=self.META.description,
            parameters=schema
        )

    # --- متد جدید برای ابزارهای دارای صفحه اختصاصی ---
    def get_page_router(self) -> Optional[APIRouter]:
        """
        اگر ابزار صفحه اختصاصی داشته باشد، یک APIRouter برای آن برمی‌گرداند.
        این متد می‌تواند توسط کلاس‌های فرزند برای تعریف endpoint های صفحه اختصاصی بازنویسی شود.
        مثال:
        
        router = APIRouter()
        @router.get("/my-data")
        async def get_data():
            return {"data": "some value"}
        return router
        """
        return None

    @property
    def is_ai_enabled(self) -> bool:
        return self.META and self.META.access_level in [AccessLevel.AI_ONLY, AccessLevel.BOTH]

    @property
    def is_ui_enabled(self) -> bool:
        return self.META and self.META.access_level in [AccessLevel.UI_ONLY, AccessLevel.BOTH]
