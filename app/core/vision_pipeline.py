"""Vision pipeline for screen understanding and interaction.

Inspired by:
- OpenClaw: screenshot -> OCR -> action plan
- Suna: lightweight multimodal local agent execution
- Browsr: full browser automation chain

Provides:
- Screenshot capture (native / browser)
- OCR text extraction (easyocr with graceful degradation)
- Screen description (multimodal understanding)
- Action plan generation (find + click / type)
"""

from __future__ import annotations

import asyncio
import base64
import dataclasses
import logging
import os
import tempfile
from dataclasses import dataclass
from typing import Any, Optional

import structlog

from app.core.file_patch import get_current_agent_mode
from app.core.security_sandbox import permission_system

logger = structlog.get_logger()


@dataclass
class VisionResult:
    """Result from a vision pipeline step."""
    success: bool
    content: str
    metadata: dict[str, Any] = dataclasses.field(default_factory=dict)
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "content": self.content,
            "metadata": self.metadata,
            "error": self.error,
        }


class VisionPipeline:
    """End-to-end screen understanding pipeline.

    Steps:
    1. Capture screenshot (native or browser)
    2. OCR extraction (easyocr)
    3. Screen description (multimodal LLM or heuristics)
    4. Action plan generation (find target + click/type)
    """

    def __init__(self):
        self._easyocr_available: bool | None = None
        self._check_easyocr()

    def _check_easyocr(self) -> None:
        """Check if easyocr is available."""
        if self._easyocr_available is not None:
            return
        try:
            import easyocr  # noqa: F401
            self._easyocr_available = True
        except ImportError:
            self._easyocr_available = False
            logger.warning("easyocr not available, OCR will be degraded")

    @property
    def ocr_available(self) -> bool:
        """Whether OCR is available."""
        return self._easyocr_available is True

    async def capture_screen(
        self,
        source: str = "native",
        region: tuple[int, int, int, int] | None = None,
        session_id: str = "default",
    ) -> VisionResult:
        """Capture a screenshot from native desktop or browser.

        Args:
            source: "native" for desktop, "browser" for browser screenshot
            region: optional (x, y, width, height) crop region
            session_id: browser session id (for browser source)

        Returns:
            VisionResult with file path and base64 content
        """
        try:
            output_path = tempfile.mktemp(suffix=".png", prefix="vision_")

            if source == "browser":
                from app.tools.browser_tools import browser_screenshot
                result_str = await browser_screenshot(
                    url="",
                    output_path=output_path,
                    session_id=session_id,
                )
                if result_str.startswith("Error") or not os.path.exists(output_path):
                    return VisionResult(
                        success=False,
                        content="",
                        error=f"Browser screenshot failed: {result_str}",
                    )
            else:
                from app.tools.native_tools import take_screenshot
                result_str = await take_screenshot(output_path=output_path)
                if result_str.startswith("Error") or not os.path.exists(result_str):
                    return VisionResult(
                        success=False,
                        content="",
                        error=f"Native screenshot failed: {result_str}",
                    )
                output_path = result_str

            # Crop if region specified
            if region and os.path.exists(output_path):
                try:
                    from PIL import Image
                    img = Image.open(output_path)
                    x, y, w, h = region
                    img = img.crop((x, y, x + w, y + h))
                    img.save(output_path)
                except Exception as crop_err:
                    logger.warning("crop_failed", error=str(crop_err))

            # Convert to base64
            with open(output_path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode("utf-8")

            return VisionResult(
                success=True,
                content=output_path,
                metadata={
                    "source": source,
                    "path": output_path,
                    "base64": b64,
                    "region": region,
                },
            )
        except Exception as e:
            logger.error("capture_screen_failed", error=str(e))
            return VisionResult(success=False, content="", error=str(e))

    async def ocr_screen(
        self,
        source: str = "native",
        region: tuple[int, int, int, int] | None = None,
        session_id: str = "default",
    ) -> VisionResult:
        """Extract text from screen using OCR.

        Uses easyocr if available, otherwise returns degraded result
        indicating OCR is unavailable.

        Args:
            source: "native" or "browser"
            region: optional crop region
            session_id: browser session id

        Returns:
            VisionResult with extracted text
        """
        if not self.ocr_available:
            return VisionResult(
                success=False,
                content="",
                error="OCR unavailable: easyocr not installed. Install with: pip install easyocr",
                metadata={"graceful_degradation": True},
            )

        try:
            # Capture screenshot first
            capture_result = await self.capture_screen(source, region, session_id)
            if not capture_result.success:
                return capture_result

            image_path = capture_result.metadata["path"]

            # Run OCR in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            text = await loop.run_in_executor(None, self._run_ocr, image_path)

            return VisionResult(
                success=True,
                content=text,
                metadata={
                    "source": source,
                    "path": image_path,
                    "ocr_engine": "easyocr",
                },
            )
        except Exception as e:
            logger.error("ocr_screen_failed", error=str(e))
            return VisionResult(success=False, content="", error=str(e))

    def _run_ocr(self, image_path: str) -> str:
        """Run OCR on an image (runs in thread pool)."""
        import easyocr

        reader = easyocr.Reader(["en", "ch_sim"], gpu=False, verbose=False)
        results = reader.readtext(image_path, detail=0, paragraph=True)
        return "\n".join(results) if results else "(no text detected)"

    async def describe_screen(
        self,
        source: str = "native",
        session_id: str = "default",
    ) -> VisionResult:
        """Describe what is visible on screen.

        Uses multimodal LLM if available, otherwise falls back to
        OCR-based description.

        Args:
            source: "native" or "browser"
            session_id: browser session id

        Returns:
            VisionResult with screen description
        """
        try:
            # Capture screenshot
            capture_result = await self.capture_screen(source, session_id=session_id)
            if not capture_result.success:
                return capture_result

            image_path = capture_result.metadata["path"]
            b64 = capture_result.metadata.get("base64", "")

            # Try multimodal LLM description
            description = await self._describe_with_llm(image_path, b64)
            if description:
                return VisionResult(
                    success=True,
                    content=description,
                    metadata={
                        "source": source,
                        "path": image_path,
                        "method": "llm",
                    },
                )

            # Fallback to OCR-based description
            ocr_result = await self.ocr_screen(source, session_id=session_id)
            if ocr_result.success:
                return VisionResult(
                    success=True,
                    content=f"Screen contains text:\n{ocr_result.content}",
                    metadata={
                        "source": source,
                        "path": image_path,
                        "method": "ocr_fallback",
                    },
                )

            return VisionResult(
                success=True,
                content="Screen captured but no text or description available",
                metadata={"source": source, "path": image_path, "method": "none"},
            )
        except Exception as e:
            logger.error("describe_screen_failed", error=str(e))
            return VisionResult(success=False, content="", error=str(e))

    async def _describe_with_llm(self, image_path: str, base64_image: str) -> str | None:
        """Use multimodal LLM to describe the screen."""
        try:
            from app.core.di import resolve as di_resolve
            from app.config import settings

            registry = di_resolve("ModelRegistry")
            provider = getattr(settings, "DEFAULT_LLM_PROVIDER", "openai")
            model_id = getattr(settings, "DEFAULT_VISION_MODEL", "gpt-4o")

            adapter = registry.get_or_create(
                provider=provider,
                model_id=model_id,
                api_key=getattr(settings, f"{provider.upper()}_API_KEY", ""),
                base_url=getattr(settings, f"{provider.upper()}_BASE_URL", None),
            )

            if not hasattr(adapter, "capabilities") or not adapter.capabilities.vision:
                return None

            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Describe what is visible on this screen in detail. Include UI elements, text, buttons, and their approximate positions."},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{base64_image}",
                                "detail": "high",
                            },
                        },
                    ],
                }
            ]

            result = await adapter.chat(messages=messages)
            return result.content.strip()
        except Exception as e:
            logger.debug("llm_describe_failed", error=str(e))
            return None

    async def generate_action_plan(
        self,
        goal: str,
        source: str = "native",
        session_id: str = "default",
    ) -> VisionResult:
        """Generate an action plan to achieve a goal based on current screen.

        Args:
            goal: what the agent wants to accomplish
            source: "native" or "browser"
            session_id: browser session id

        Returns:
            VisionResult with step-by-step action plan
        """
        try:
            # Get screen description
            desc_result = await self.describe_screen(source, session_id)
            if not desc_result.success:
                return desc_result

            screen_desc = desc_result.content

            # Use LLM to generate action plan
            plan = await self._plan_with_llm(goal, screen_desc)
            if plan:
                return VisionResult(
                    success=True,
                    content=plan,
                    metadata={
                        "goal": goal,
                        "source": source,
                        "screen_description": screen_desc[:500],
                    },
                )

            return VisionResult(
                success=True,
                content=f"Goal: {goal}\nScreen: {screen_desc}\n\nNo structured plan generated.",
                metadata={"goal": goal, "source": source},
            )
        except Exception as e:
            logger.error("generate_action_plan_failed", error=str(e))
            return VisionResult(success=False, content="", error=str(e))

    async def _plan_with_llm(self, goal: str, screen_desc: str) -> str | None:
        """Use LLM to generate action plan from goal and screen description."""
        try:
            from app.core.di import resolve as di_resolve
            from app.config import settings

            registry = di_resolve("ModelRegistry")
            provider = getattr(settings, "DEFAULT_LLM_PROVIDER", "openai")
            model_id = getattr(settings, "DEFAULT_LLM_MODEL", "gpt-4o")

            adapter = registry.get_or_create(
                provider=provider,
                model_id=model_id,
                api_key=getattr(settings, f"{provider.upper()}_API_KEY", ""),
                base_url=getattr(settings, f"{provider.upper()}_BASE_URL", None),
            )

            prompt = f"""Given the following screen description and goal, generate a step-by-step action plan.

Goal: {goal}

Screen Description:
{screen_desc}

Output a concise action plan with specific coordinates or element descriptions for each step.
Format:
1. Action: description
2. Action: description
..."""

            result = await adapter.chat(messages=[{"role": "user", "content": prompt}])
            return result.content.strip()
        except Exception as e:
            logger.debug("llm_plan_failed", error=str(e))
            return None

    async def find_and_click(
        self,
        text: str,
        source: str = "native",
        session_id: str = "default",
    ) -> VisionResult:
        """Find text on screen and click it.

        This is a HIGH RISK action that requires approval or FULL_AUTO mode.

        Args:
            text: text to find and click
            source: "native" or "browser"
            session_id: browser session id

        Returns:
            VisionResult with click result
        """
        try:
            # Permission check
            allowed, reason = self._check_high_risk_permission(session_id, "find_and_click")
            if not allowed:
                return VisionResult(
                    success=False,
                    content="",
                    error=f"Permission denied: {reason}",
                    metadata={"requires_approval": True},
                )

            # OCR to find text location
            ocr_result = await self.ocr_screen(source, session_id=session_id)
            if not ocr_result.success:
                return VisionResult(
                    success=False,
                    content="",
                    error=f"OCR failed: {ocr_result.error}",
                )

            # Simple text matching (in production, use more sophisticated OCR coordinate mapping)
            lines = ocr_result.content.split("\n")
            matched_line = next((line for line in lines if text.lower() in line.lower()), None)
            if not matched_line:
                return VisionResult(
                    success=False,
                    content="",
                    error=f"Text '{text}' not found on screen",
                    metadata={"ocr_text": ocr_result.content},
                )

            # For now, use center of screen as fallback
            # In production, easyocr returns bounding boxes that can be used
            x, y = self._estimate_center(source, session_id)

            if source == "browser":
                from app.tools.browser_tools import browser_click
                result_str = await browser_click(selector=f"text={text}", session_id=session_id)
            else:
                from app.tools.native_tools import click_mouse
                result_str = await click_mouse(x=x, y=y)

            return VisionResult(
                success=True,
                content=result_str,
                metadata={
                    "text": text,
                    "coordinates": (x, y),
                    "source": source,
                },
            )
        except Exception as e:
            logger.error("find_and_click_failed", error=str(e))
            return VisionResult(success=False, content="", error=str(e))

    async def find_and_type(
        self,
        text: str,
        input_text: str,
        source: str = "native",
        session_id: str = "default",
    ) -> VisionResult:
        """Find input field and type text.

        This is a HIGH RISK action that requires approval or FULL_AUTO mode.

        Args:
            text: label or placeholder to identify the input field
            input_text: text to type
            source: "native" or "browser"
            session_id: browser session id

        Returns:
            VisionResult with typing result
        """
        try:
            # Permission check
            allowed, reason = self._check_high_risk_permission(session_id, "find_and_type")
            if not allowed:
                return VisionResult(
                    success=False,
                    content="",
                    error=f"Permission denied: {reason}",
                    metadata={"requires_approval": True},
                )

            # OCR to find input field
            ocr_result = await self.ocr_screen(source, session_id=session_id)
            if not ocr_result.success:
                return VisionResult(
                    success=False,
                    content="",
                    error=f"OCR failed: {ocr_result.error}",
                )

            # Check if input field label is present
            lines = ocr_result.content.split("\n")
            has_field = any(text.lower() in line.lower() for line in lines)
            if not has_field:
                return VisionResult(
                    success=False,
                    content="",
                    error=f"Input field '{text}' not found on screen",
                    metadata={"ocr_text": ocr_result.content},
                )

            # Type the text
            if source == "browser":
                from app.tools.browser_tools import browser_type
                result_str = await browser_type(
                    selector=f"input[placeholder*='{text}'], input[name*='{text}']",
                    text=input_text,
                    session_id=session_id,
                )
            else:
                from app.tools.native_tools import type_text
                result_str = await type_text(input_text)

            return VisionResult(
                success=True,
                content=result_str,
                metadata={
                    "field_label": text,
                    "typed_length": len(input_text),
                    "source": source,
                },
            )
        except Exception as e:
            logger.error("find_and_type_failed", error=str(e))
            return VisionResult(success=False, content="", error=str(e))

    def _estimate_center(self, source: str, session_id: str) -> tuple[int, int]:
        """Estimate screen center for click fallback."""
        try:
            if source == "browser":
                # Use default browser viewport
                return (960, 540)
            # Use pyautogui to get screen size
            import pyautogui
            w, h = pyautogui.size()
            return (w // 2, h // 2)
        except Exception:
            return (960, 540)

    def _check_high_risk_permission(self, session_id: str, action: str) -> tuple[bool, str]:
        """Check permission for high-risk vision actions.

        Requires either:
        - FULL_AUTO execution mode
        - Active permission grant via approval system
        - PLAN mode with preview (returns requires_approval)
        """
        try:
            mode = get_current_agent_mode()

            # PLAN mode: require approval
            if mode == "plan":
                return False, "Action requires approval in PLAN mode"

            # Check permission system for active grant
            if permission_system and session_id:
                if permission_system.check_permission(session_id, action):
                    return True, "OK"

            # If not in FULL_AUTO and no grant, require approval
            # Note: FULL_AUTO is represented by mode == "act" in current session model
            if mode == "act":
                return True, "OK"

            return False, "Action requires FULL_AUTO mode or explicit approval"
        except Exception as e:
            logger.error("permission_check_failed", error=str(e))
            return False, str(e)


# Global pipeline instance
vision_pipeline = VisionPipeline()
