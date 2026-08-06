"""Vision tools for screen capture, OCR, and interaction.

Inspired by:
- OpenClaw: screenshot -> OCR -> action plan
- Suna: lightweight multimodal local agent execution
- Browsr: full browser automation chain

Tools:
- capture_screen: take screenshot, return base64
- ocr_screen: OCR the screen, return text
- describe_screen: describe what's on screen
- find_and_click: find text and click it (HIGH RISK)
- find_and_type: find input field and type text (HIGH RISK)
"""

from __future__ import annotations

import structlog

from app.core.vision_pipeline import vision_pipeline
from app.tools import tool

logger = structlog.get_logger()


@tool(
    description="Capture a screenshot and return base64 image. Use source='native' for desktop, source='browser' for browser.",
    parameters={
        "type": "object",
        "properties": {
            "source": {"type": "string", "description": "Screenshot source: 'native' or 'browser'", "default": "native"},
            "region": {"type": "array", "items": {"type": "integer"}, "description": "Optional crop region [x, y, width, height]", "default": []},
            "session_id": {"type": "string", "description": "Browser session id (for browser source)", "default": "default"},
        },
        "required": [],
    },
)
async def capture_screen(
    source: str = "native",
    region: list[int] | None = None,
    session_id: str = "default",
) -> str:
    """Capture a screenshot and return base64 image."""
    try:
        region_tuple = tuple(region) if region else None
        result = await vision_pipeline.capture_screen(
            source=source,
            region=region_tuple,
            session_id=session_id,
        )
        if not result.success:
            return f"Error: {result.error}"
        return f"data:image/png;base64,{result.metadata['base64']}"
    except Exception as e:
        return f"Error capturing screen: {str(e)}"


@tool(
    description="Extract text from screen using OCR. Returns extracted text.",
    parameters={
        "type": "object",
        "properties": {
            "source": {"type": "string", "description": "Screenshot source: 'native' or 'browser'", "default": "native"},
            "region": {"type": "array", "items": {"type": "integer"}, "description": "Optional crop region [x, y, width, height]", "default": []},
            "session_id": {"type": "string", "description": "Browser session id (for browser source)", "default": "default"},
        },
        "required": [],
    },
)
async def ocr_screen(
    source: str = "native",
    region: list[int] | None = None,
    session_id: str = "default",
) -> str:
    """Extract text from screen using OCR."""
    try:
        region_tuple = tuple(region) if region else None
        result = await vision_pipeline.ocr_screen(
            source=source,
            region=region_tuple,
            session_id=session_id,
        )
        if not result.success:
            return f"Error: {result.error}"
        return result.content
    except Exception as e:
        return f"Error performing OCR: {str(e)}"


@tool(
    description="Describe what is visible on screen. Returns a detailed description of UI elements, text, and layout.",
    parameters={
        "type": "object",
        "properties": {
            "source": {"type": "string", "description": "Screenshot source: 'native' or 'browser'", "default": "native"},
            "session_id": {"type": "string", "description": "Browser session id (for browser source)", "default": "default"},
        },
        "required": [],
    },
)
async def describe_screen(
    source: str = "native",
    session_id: str = "default",
) -> str:
    """Describe what is visible on screen."""
    try:
        result = await vision_pipeline.describe_screen(
            source=source,
            session_id=session_id,
        )
        if not result.success:
            return f"Error: {result.error}"
        return result.content
    except Exception as e:
        return f"Error describing screen: {str(e)}"


@tool(
    description="Find text on screen and click it. HIGH RISK - requires FULL_AUTO mode or user approval.",
    parameters={
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "Text to find and click"},
            "source": {"type": "string", "description": "Screenshot source: 'native' or 'browser'", "default": "native"},
            "session_id": {"type": "string", "description": "Browser session id (for browser source)", "default": "default"},
        },
        "required": ["text"],
    },
)
async def find_and_click(
    text: str,
    source: str = "native",
    session_id: str = "default",
) -> str:
    """Find text on screen and click it. Requires approval or FULL_AUTO mode."""
    try:
        result = await vision_pipeline.find_and_click(
            text=text,
            source=source,
            session_id=session_id,
        )
        if not result.success:
            return f"Error: {result.error}"
        return result.content
    except Exception as e:
        return f"Error finding and clicking: {str(e)}"


@tool(
    description="Find input field and type text. HIGH RISK - requires FULL_AUTO mode or user approval.",
    parameters={
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "Field label or placeholder to identify the input"},
            "input_text": {"type": "string", "description": "Text to type into the field"},
            "source": {"type": "string", "description": "Screenshot source: 'native' or 'browser'", "default": "native"},
            "session_id": {"type": "string", "description": "Browser session id (for browser source)", "default": "default"},
        },
        "required": ["text", "input_text"],
    },
)
async def find_and_type(
    text: str,
    input_text: str,
    source: str = "native",
    session_id: str = "default",
) -> str:
    """Find input field and type text. Requires approval or FULL_AUTO mode."""
    try:
        result = await vision_pipeline.find_and_type(
            text=text,
            input_text=input_text,
            source=source,
            session_id=session_id,
        )
        if not result.success:
            return f"Error: {result.error}"
        return result.content
    except Exception as e:
        return f"Error finding and typing: {str(e)}"
