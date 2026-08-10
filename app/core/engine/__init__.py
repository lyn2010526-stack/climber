"""Engine subpackage — pipeline-based agent execution.

Reference: OpenSquilla microkernel architecture.
The engine subpackage provides structured pipeline execution, routing decisions,
subagent management, tool rules, ensemble execution, and memory blocks —
all wired together via dependency injection.
"""

from app.core.engine.ensemble import (
    AgentMessage,
    ConsensusResult,
    EnsembleCoordinator,
    EnsembleEngine,
    MessageBus,
    MessageType,
    ModelResponse,
)
from app.core.engine.memory_blocks import (
    BlockType,
    EntityExtractor,
    MemoryBlock,
    MemoryBlockStore,
    MemoryConsolidator,
    PassageRecord,
    PersonaAwareBlockStore,
    create_persona_block,
)
from app.core.engine.memory_pressure import (
    CompressionStrategy,
    MemoryPressureConfig,
    MemoryPressureManager,
    PressureSnapshot,
)
from app.core.engine.pipeline import (
    RoutePlan,
    StepResult,
    TurnContext,
    TurnStep,
    build_pipeline_event,
    run_pipeline,
)
from app.core.engine.react_loop import ReActLoopExecutor
from app.core.engine.router_decision import (
    RouterDecisionEngine,
    RouterDecisionEvent,
    TierConfig,
)
from app.core.engine.runtime_capsule import (
    BlockingFact,
    FileCategory,
    FileState,
    RuntimeStateCapsule,
    ToolReceipt,
    WorkspaceSnapshot,
)
from app.core.engine.session import AgentSession
from app.core.engine.subagent import (
    SubagentManager,
    SubagentSpec,
    SubagentState,
    SubagentUsage,
)
from app.core.engine.tool_rules import (
    HeartbeatController,
    RulesCheckResult,
    ToolCallRecord,
    ToolRule,
    ToolRulesSolver,
    ToolRuleType,
)

__all__ = [
    # Ensemble
    "AgentMessage",
    # Session
    "AgentSession",
    # Memory Blocks
    "BlockType",
    # Runtime Capsule
    "BlockingFact",
    # Memory Pressure
    "CompressionStrategy",
    "ConsensusResult",
    "EnsembleCoordinator",
    "EnsembleEngine",
    "EntityExtractor",
    "FileCategory",
    "FileState",
    # Tool Rules
    "HeartbeatController",
    "MemoryBlock",
    "MemoryBlockStore",
    "MemoryConsolidator",
    "MemoryPressureConfig",
    "MemoryPressureManager",
    "MessageBus",
    "MessageType",
    "ModelResponse",
    "PassageRecord",
    "PersonaAwareBlockStore",
    "PressureSnapshot",
    # Pipeline
    "RoutePlan",
    # Router Decision
    "RouterDecisionEngine",
    "RouterDecisionEvent",
    "RulesCheckResult",
    "RuntimeStateCapsule",
    "StepResult",
    # Subagent
    "SubagentManager",
    "SubagentSpec",
    "SubagentState",
    "SubagentUsage",
    "TierConfig",
    "ToolCallRecord",
    "ToolReceipt",
    "ToolRule",
    "ToolRuleType",
    "ToolRulesSolver",
    "TurnContext",
    "TurnStep",
    "WorkspaceSnapshot",
    "build_pipeline_event",
    "create_persona_block",
    "run_pipeline",
]
