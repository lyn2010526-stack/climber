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

from app.engine.code_agent import AgentResult, CodeAgent, StepResult
from app.engine.code_executor import ExecutionResult, ExecutionStatus, SafeExecutor

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
from app.engine.harness import Harness, HarnessRegistry
from app.engine.hierarchical import HierarchicalCrew, ManagerAgent, TaskAssignment
from app.engine.knowledge import (
    CSVKnowledgeSource,
    JSONKnowledgeSource,
    KnowledgeManager,
    KnowledgeSource,
    PDFKnowledgeSource,
    TextKnowledgeSource,
)
from app.engine.planning import Planner, PlanStatus, PlanStep
from app.engine.stream_output import CollectingStreamOutput, DefaultStreamOutput, StreamOutput
from app.engine.tool_collection import ToolCollection
from app.engine.tool_failure import ToolFailure, ToolFailureHandler, ToolFailurePolicy
from app.engine.unified_memory import MemoryRecord, MemoryScope, UnifiedMemory

__all__ = [
    "AgentResult",
    # Guardrails
    "BaseGuardrail",
    # Knowledge
    "CSVKnowledgeSource",
    # Checkpoint
    "CheckpointManager",
    "CodeAgent",
    "CollectingStreamOutput",
    "CrewCheckpoint",
    "DefaultStreamOutput",
    "ExecutionResult",
    "ExecutionStatus",
    "FunctionGuardrail",
    "GuardrailChain",
    "GuardrailResult",
    "Harness",
    "HarnessRegistry",
    # Hierarchical
    "HierarchicalCrew",
    "JSONKnowledgeSource",
    "KnowledgeManager",
    "KnowledgeSource",
    "LLMGuardrail",
    "ManagerAgent",
    # Unified Memory
    "MemoryRecord",
    "MemoryScope",
    "OutputPydantic",
    "PDFKnowledgeSource",
    "PlanStatus",
    "PlanStep",
    "Planner",
    # Code Agent
    "SafeExecutor",
    "StepResult",
    "StreamOutput",
    "TaskAssignment",
    "TextKnowledgeSource",
    "ToolCollection",
    # Tool Failure
    "ToolFailure",
    "ToolFailureHandler",
    "ToolFailurePolicy",
    "UnifiedMemory",
]
