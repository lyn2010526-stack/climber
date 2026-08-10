"""Context compression strategies.

This module provides a convenience wrapper around the canonical
implementation in app.core.compressor. For new code, import directly
from app.core.compressor instead.
"""

from __future__ import annotations

from app.core import CompressionStrategy, ContextConfig
from app.core.compressor import ContextCompressor, estimate_tokens

__all__ = ["CompressionStrategy", "ContextCompressor", "estimate_tokens"]

_default_config = ContextConfig(
    max_tokens=8000,
    compression_strategy=CompressionStrategy.SLIDING,
    keep_recent_messages=10,
)
context_compressor = ContextCompressor(_default_config)
