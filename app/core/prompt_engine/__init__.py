"""Three-layer prompt engine for Climber.

Layer 0: Immutable base prompt (cannot be overridden)
Layer 1: Session template (user-editable)
Layer 2: Dynamic runtime prompt (auto-injected by system)
"""

from app.core.prompt_engine.engine import PromptEngine
from app.core.prompt_engine.models import (
    ModelAdaptation,
    PromptFragment,
    PromptLayer,
    PromptTemplate,
)
from app.core.prompt_engine.template_repository import PromptTemplateRepository

__all__ = [
    "ModelAdaptation",
    "PromptEngine",
    "PromptFragment",
    "PromptLayer",
    "PromptTemplate",
    "PromptTemplateRepository",
]
