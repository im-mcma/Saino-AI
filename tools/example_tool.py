# -*- coding: utf-8 -*-
from .base import BaseTool, ToolMeta, AccessLevel, ToolFrontendComponent, logger
from typing import Callable
import asyncio
import platform

class SystemStatusTool(BaseTool):
    """
    یک ابزار نمونه که اطلاعات سیستم را بررسی کرده و یک دکمه در UI نمایش می‌دهد.
    """
    META = ToolMeta(
        name="system_status_check",
        description="Gets the current status of the server system, like OS and Python version.",
        access_level=AccessLevel.BOTH # قابل استفاده توسط AI و UI
    )

    async def _execute(self, stream_callback: Callable[[str], None], **kwargs) -> Dict:
        """منطق اصلی ابزار: اطلاعات سیستم را جمع‌آوری می‌کند."""
        await stream_callback("در حال بررسی سیستم عامل...")
        await asyncio.sleep(0.5)
        os_info = f"Operating System: {platform.system()} {platform.release()}"
        await stream_callback(f"✅ {os_info}")
        
        await asyncio.sleep(0.5)
        
        await stream_callback("در حال بررسی نسخه پایتون...")
        await asyncio.sleep(0.5)
        python_version = f"Python Version: {platform.python_version()}"
        await stream_callback(f"✅ {python_version}")

        # نتیجه نهایی که به مدل AI برگردانده می‌شود
        return {
            "os_info": os_info,
            "python_version": python_version,
            "status": "OK"
        }

    def get_frontend_component(self) -> ToolFrontendComponent:
        """کامپوننت UI این ابزار را تعریف می‌کند: یک دکمه ساده."""
        return ToolFrontendComponent(
            placement="toolbar", # این دکمه در نوار ابزار نمایش داده می‌شود
            html="""
            <button @click="$dispatch('run-tool', { name: 'system_status_check' })"
                    class="flex items-center space-x-2 space-x-reverse px-3 py-1.5 bg-gray-700/50 hover:bg-gray-700 rounded-lg text-xs font-medium transition-colors">
                <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M12 6a2 2 0 100-4 2 2 0 000 4zm0 14a2 2 0 100-4 2 2 0 000 4zm6-8a2 2 0 100-4 2 2 0 000 4zm-14 0a2 2 0 100-4 2 2 0 000 4z"/></svg>
                <span>بررسی سیستم</span>
            </button>
            """,
            # این ابزار JS یا CSS خاصی نیاز ندارد
        )
