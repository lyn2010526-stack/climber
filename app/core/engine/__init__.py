"""Engine subpackage — pipeline-based agent execution.

Reference: OpenSquilla microkernel architecture.
The engine subpackage provides structured pipeline execution, routing decisions,
subagent management, tool rules, ensemble execution, and memory blocks —
all wired together via dependency injection.
"""

from app.core.engine.react_loop import ReActLoopExecutor
from app.core.engine.session import AgentSession
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
    ToolRuleType,
    ToolRulesSolver,
)

__all__ = [
    # Session
    "AgentSession",
    # Pipeline
    "RoutePlan",
    "StepResult",
    "TurnContext",
    "TurnStep",
    "build_pipeline_event",
    "run_pipeline",
    # Router Decision
    "RouterDecisionEngine",
    "RouterDecisionEvent",
    "TierConfig",
    # Subagent
    "SubagentManager",
    "SubagentSpec",
    "SubagentState",
    "SubagentUsage",
    # Tool Rules
    "HeartbeatController",
    "RulesCheckResult",
    "ToolCallRecord",
    "ToolRule",
    "ToolRuleType",
    "ToolRulesSolver",
    # Memory Pressure
    "CompressionStrategy",
    "MemoryPressureConfig",
    "MemoryPressureManager",
    "PressureSnapshot",
    # Runtime Capsule
    "BlockingFact",
    "FileCategory",
    "FileState",
    "RuntimeStateCapsule",
    "ToolReceipt",
    "WorkspaceSnapshot",
    # Ensemble
    "AgentMessage",
    "ConsensusResult",
    "EnsembleCoordinator",
    "EnsembleEngine",
    "MessageBus",
    "MessageType",
    "ModelResponse",
    # Memory Blocks
    "BlockType",
    "EntityExtractor",
    "MemoryBlock",
    "MemoryBlockStore",
    "MemoryConsolidator",
    "PassageRecord",
    "PersonaAwareBlockStore",
    "create_persona_block",
]
