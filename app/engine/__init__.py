"""Engine subpackage — code-first agent, AST interpreter, and orchestration.

Provides:
- SafeExecutor: AST-walking interpreter for safe Python code execution
- CodeAgent: Agent that generates Python code as actions (smolagents-inspired)
- Planner: Periodic planning for complex tasks
- StreamOutput: Rich streaming output for code agent
- ToolCollection: Collection of tools from various sources
- Harness: Per-model prompt format emulation
- HierarchicalCrew: CrewAI-inspired multi-agent orchestration
- Guardrails: Task output validation
- Knowledge: Document ingestion for RAG
- UnifiedMemory: Composite-scoring memory system
"""

from app.engine.code_executor import SafeExecutor, ExecutionResult, ExecutionStatus
from app.engine.code_agent import CodeAgent, AgentResult, StepResult
from app.engine.planning import Planner, PlanStep, PlanStatus
from app.engine.stream_output import StreamOutput, DefaultStreamOutput, CollectingStreamOutput
from app.engine.tool_collection import ToolCollection
from app.engine.harness import Harness, HarnessRegistry

# Existing exports
from app.engine.crew_checkpoint import CheckpointManager, CrewCheckpoint
from app.engine.guardrails import (
    BaseGuardrail,
    FunctionGuardrail,
    GuardrailChain,
    GuardrailResult,
    LLMGuardrail,
    OutputPydantic,
)
from app.engine.hierarchical import HierarchicalCrew, ManagerAgent, TaskAssignment
from app.engine.knowledge import (
    CSVKnowledgeSource,
    JSONKnowledgeSource,
    KnowledgeManager,
    KnowledgeSource,
    PDFKnowledgeSource,
    TextKnowledgeSource,
)
from app.engine.tool_failure import ToolFailure, ToolFailureHandler, ToolFailurePolicy
from app.engine.unified_memory import MemoryRecord, MemoryScope, UnifiedMemory

__all__ = [
    # Code Agent
    "SafeExecutor",
    "ExecutionResult",
    "ExecutionStatus",
    "CodeAgent",
    "AgentResult",
    "StepResult",
    "Planner",
    "PlanStep",
    "PlanStatus",
    "StreamOutput",
    "DefaultStreamOutput",
    "CollectingStreamOutput",
    "ToolCollection",
    "Harness",
    "HarnessRegistry",
    # Hierarchical
    "HierarchicalCrew",
    "ManagerAgent",
    "TaskAssignment",
    # Guardrails
    "BaseGuardrail",
    "FunctionGuardrail",
    "GuardrailChain",
    "GuardrailResult",
    "LLMGuardrail",
    "OutputPydantic",
    # Knowledge
    "CSVKnowledgeSource",
    "JSONKnowledgeSource",
    "KnowledgeManager",
    "KnowledgeSource",
    "PDFKnowledgeSource",
    "TextKnowledgeSource",
    # Tool Failure
    "ToolFailure",
    "ToolFailureHandler",
    "ToolFailurePolicy",
    # Checkpoint
    "CheckpointManager",
    "CrewCheckpoint",
    # Unified Memory
    "MemoryRecord",
    "MemoryScope",
    "UnifiedMemory",
]
