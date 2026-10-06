"""Project-owned controls; model credentials come from the current session."""

from __future__ import annotations

import math
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class OptimizerConfig:
    enabled: bool = False
    confidence_threshold: float = 0.45
    max_input_chars: int = 2000
    timeout_seconds: float = 5.0
    max_tokens: int = 512

    @classmethod
    def from_env(cls) -> OptimizerConfig:
        def number(name: str, default: float, minimum: float, maximum: float) -> float:
            try:
                value = float(os.getenv(name, str(default)))
                return value if math.isfinite(value) and minimum <= value <= maximum else default
            except ValueError:
                return default

        return cls(
            enabled=os.getenv("USER_PROMPT_OPT_MODE", "off").strip().lower() == "auto",
            confidence_threshold=number("USER_PROMPT_OPT_CONFIDENCE_THRESHOLD", 0.45, 0, 1),
            max_input_chars=int(number("USER_PROMPT_OPT_MAX_INPUT_CHARS", 2000, 1, 8000)),
            timeout_seconds=number("USER_PROMPT_OPT_TIMEOUT_SECONDS", 5, 0.01, 20),
            max_tokens=int(number("USER_PROMPT_OPT_MAX_TOKENS", 512, 64, 1024)),
        )
