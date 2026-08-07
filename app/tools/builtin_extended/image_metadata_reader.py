"""Read image EXIF metadata."""

from __future__ import annotations

from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class ImageMetadataReaderTool:
    """Implementation of image_metadata_reader tool."""

    def execute(self, **kwargs: Any) -> dict[str, Any]:
        """Execute the image_metadata_reader tool."""
        logger.info("image_metadata_reader_execute", kwargs=kwargs)
        return {"tool": "image_metadata_reader", "action": "execute"}

    def validate(self, **kwargs: Any) -> dict[str, Any]:
        """Validate the image_metadata_reader tool."""
        logger.info("image_metadata_reader_validate", kwargs=kwargs)
        return {"tool": "image_metadata_reader", "action": "validate"}

    def configure(self, **kwargs: Any) -> dict[str, Any]:
        """Configure the image_metadata_reader tool."""
        logger.info("image_metadata_reader_configure", kwargs=kwargs)
        return {"tool": "image_metadata_reader", "action": "configure"}

    def get_schema(self, **kwargs: Any) -> dict[str, Any]:
        """Get_schema the image_metadata_reader tool."""
        logger.info("image_metadata_reader_get_schema", kwargs=kwargs)
        return {"tool": "image_metadata_reader", "action": "get_schema"}

    def get_info(self, **kwargs: Any) -> dict[str, Any]:
        """Get_info the image_metadata_reader tool."""
        logger.info("image_metadata_reader_get_info", kwargs=kwargs)
        return {"tool": "image_metadata_reader", "action": "get_info"}

    @staticmethod
    def get_capabilities() -> dict[str, Any]:
        """Return tool capabilities."""
        return {
            "name": "image_metadata_reader",
            "description": "Read image EXIF metadata",
            "version": "1.0.0",
            "category": "image",
        }


def image_metadata_reader(**kwargs: Any) -> dict[str, Any]:
    """Execute image_metadata_reader with given parameters."""
    tool = ImageMetadataReaderTool()
    return tool.execute(**kwargs)
