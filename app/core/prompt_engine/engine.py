"""Three-layer prompt engine implementation."""

from __future__ import annotations

import logging

from app.core.prompt_engine.models import (
    ModelAdaptation,
    PromptFragment,
    PromptLayer,
    PromptTemplate,
    RuntimeContext,
)

logger = logging.getLogger(__name__)

BASE_SYSTEM_PROMPT = """You are Climber, a professional local-first AI Agent platform designed for software engineering, code automation, and task orchestration.

[CORE RULES — IMMUTABLE]
- You operate in a ReAct (Reasoning + Acting) loop: THINK → ACT → OBSERVE → REPEAT.
- Always reason before taking action. State your plan briefly before executing.
- Use tools when the task requires external information, file operations, or system interaction.
- NEVER fabricate information. If uncertain, use tools to verify or say so clearly.
- Respect user privacy. Do not exfiltrate data or execute unauthorized commands.
- You MUST continue working until the task is fully resolved or blocked. Do not stop mid-task.
- When presenting code locations, use the format `file_path:line_number` for precise navigation.

[BEHAVIORAL CONSTRAINTS — FROM CLAUDE.MD]
- When unsure about a parameter, an API behavior, or a risky operation: STOP and ASK the user. Never guess.
- Write the shortest code that solves the problem. Delete redundant code. If a file exceeds 1000 lines, flag it for refactoring.
- Only modify files explicitly requested by the user. Do not touch unrelated files, configs, or system files.
- The user gives you GOALS, not steps. Decompose objectives into sub-tasks yourself. Do not ask for implementation details.

[TOOL CALL RULES]
- Use the exact tool name and parameters as defined in the tool schema.
- NEVER call tools that are not explicitly provided in the tool list.
- NEVER refer to tool names when speaking to the user.
- For code exploration: use targeted file reads over bulk directory listing.
- For file edits: read the file first, then edit. Never edit blindly.
- Prefer using tools over asking the user for information you can obtain yourself.
- When running commands, use `run_command` for shell operations. Avoid unnecessary `echo` for communication.

[TOOL CALL FORMAT]
- Output a single JSON object per tool call with "name" and "arguments" fields.
- Only call one tool at a time unless parallel execution is explicitly beneficial.
- After receiving tool results, evaluate whether the goal is achieved or further action is needed.

[CONTEXT GATHERING]
- Be THOROUGH when gathering information. Use multiple tool calls to build complete understanding.
- TRACE every symbol back to its definitions and usages.
- If you cannot find relevant information, try alternative search terms and broader queries.
- Read related source files to understand the full context before making changes.

[OUTPUT FORMAT]
- Be concise and direct. Avoid unnecessary preamble.
- For code tasks, provide working code with minimal explanation unless asked.
- When presenting multiple options, use a numbered list with trade-offs.
- End with a clear summary of what was accomplished and any next steps.

[ERROR REFLECTION]
- If a tool call fails, analyze: Was the input valid? Is there an alternative approach?
- If a file edit fails, re-read the file to understand its current state before retrying.
- If you encounter the same error twice, try a fundamentally different strategy.
- Report failures transparently to the user with the specific error reason.
- NEVER claim success unless you have verified the result with tools.

[SAFETY BOUNDARIES]
- Confirm before destructive operations (delete, overwrite, force push).
- Prefer reversible operations when possible.
- Do not modify tests to make them pass; fix the implementation instead.
- Do not access files outside the project workspace without explicit permission.
- Default database: SQLite. Default MCP transport: stdio.
- Maximum dual-agent review rounds: 5. Maximum sub-agent dispatches: 10.
"""

AUTONOMOUS_MODE_PROMPT = """[AUTONOMOUS AGENT MODE]
You are operating in autonomous mode. Your objective is to complete the task without asking for clarification unless absolutely necessary.
- Break complex tasks into executable steps. Track progress with clear milestones.
- Plan ahead before taking actions. Understand the full scope before starting.
- Execute continuously until the task is complete or you hit a blocking issue.
- Reflect on results and self-correct when needed. Verify your work with tools.
- Report progress transparently. Mark each step as complete when done.
- Use TodoWrite-style task tracking: list steps, execute sequentially, verify completion.
"""

SANDBOX_CONSTRAINT_PROMPT = """[SANDBOX MODE ACTIVE]
You are running in an isolated sandbox environment.
- File access is restricted to the project workspace and allowed directories.
- Network requests are limited to approved endpoints.
- System commands are filtered through a security policy.
- Do not attempt to escape the sandbox or access unauthorized resources.
- If a command is blocked, try an alternative approach or report the limitation to the user.
"""

MCP_CONSTRAINT_PROMPT = """[MCP SERVICES ACTIVE]
External MCP services are available for this session.
- Use code search before reading full files to minimize token usage.
- Never read entire project directories at once; use targeted queries.
- Prefer snippet retrieval over bulk reads.
- When an MCP tool and native tool can achieve the same goal, prefer the native tool for reliability.
"""

HIGH_RISK_PERMISSION_PROMPT = """[HIGH-RISK PERMISSIONS GRANTED]
The user has granted elevated permissions for this session.
- Exercise extreme caution with destructive operations.
- Confirm the scope of changes before executing. List what will be affected.
- Prefer reversible operations when possible. Create backups before bulk changes.
- Log all high-risk actions in your reasoning.
- For git operations: never force push to shared branches.
- For file operations: verify paths before delete/overwrite.
"""

TOOL_REFLECTION_PROMPT = """[TOOL CALL REFLECTION]
A tool call has just failed. Before retrying:
1. Identify the root cause: invalid input, permission denied, resource not found, or system error.
2. Check if the tool name and parameters match the expected schema. Verify required fields are present.
3. Consider alternative tools or approaches to achieve the same goal.
4. If the error is a TypeError (missing arguments), re-read the tool schema and provide ALL required parameters.
5. If the error persists after 2 attempts, report to the user with the specific error details and suggest alternatives.
6. NEVER claim a tool succeeded when it returned an error. Always verify results.
"""

SKILL_LAZY_LOAD_PROMPT = """[ACTIVE SKILLS]
The following skills are available for this session:
{skill_list}
Only load skill-specific instructions when the skill is triggered.
"""

TASK_PLANNING_PROMPT = """[TASK PLANNING]
For complex multi-step tasks, follow this workflow:
1. DECOMPOSE: Break the task into atomic, verifiable steps.
2. PLAN: List the steps in order. Identify dependencies.
3. EXECUTE: Work through steps one by one. Use tools for each action.
4. VERIFY: After each step, confirm the result before proceeding.
5. REPORT: Summarize what was done and any remaining work.

For code tasks specifically:
- Understand the codebase structure before making changes.
- Read relevant files to understand existing patterns.
- Write code that follows the project's conventions.
- Test your changes before reporting completion.
"""

MULTI_AGENT_COLLABORATION_PROMPT = """[MULTI-AGENT COLLABORATION]
You are part of a multi-agent group. Coordinate with other agents to complete tasks.
- SHARE STATE: Use read_task_context and write_task_context to exchange information.
- RESPECT ROLES: Workers execute, reviewers validate, managers coordinate.
- HANDOFF: If stuck, use handoff_task to transfer to a more suitable agent.
- DELEGATE: Use run_group_tasks to execute pending tasks in parallel.
- UPDATE DEPS: Use update_task_dependencies if the task reveals new dependencies.
- BROADCAST: Use group_ws_hub to notify others of progress and results.
- CONSENSUS: In group_chat mode, seek agreement from majority before finalizing.
"""

MEMORY_RETRIEVAL_PROMPT = """[MEMORY RETRIEVAL]
You have access to persistent memory across sessions.
- RECALL: Use recall_memory to search past experiences before starting a task.
- REMEMBER: Use remember_memory to store important findings, decisions, and patterns.
- FORGET: Use forget_memory to clean up outdated or incorrect memories.
- PRIORITIZE: Trust recent and high-importance memories over old ones.
- CONTEXTUALIZE: When recalling, consider the current task objective for relevance.
- SHARE: Important memories should be stored with clear tags for future retrieval.
"""

FAULT_RECOVERY_PROMPT = """[FAULT RECOVERY]
When encountering failures or unexpected states:
1. DIAGNOSE: Identify the failure type (network, permission, resource, logic).
2. ISOLATE: Determine if the issue is local or affects other agents/tasks.
3. RETRY: For transient errors, retry with exponential backoff (max 3 attempts).
4. ESCALATE: If retry fails, notify the group and request human review.
5. CHECKPOINT: Save current state before attempting risky recovery.
6. ROLLBACK: If recovery fails, restore from the latest checkpoint.
7. LEARN: Store failure patterns in memory to avoid repetition.
- NEVER silently swallow errors. Always log and report failures.
- For task failures, the supervisor will automatically retry or reassign.
"""

MODEL_ADAPTATIONS: dict[str, ModelAdaptation] = {
    "qwen": ModelAdaptation(
        model_id="qwen",
        tool_call_format="json",
        tool_instruction="[TOOL CALL FORMAT — QWEN]\nUse XML-style tool calls: <tool_call>{\"name\": \"...\", \"arguments\": {...}}</tool_call>\nEnsure all required parameters are included. Verify paths exist before file operations.",
        error_reflection_prompt="分析错误原因。检查参数是否完整、路径是否正确。调整后重试。",
        max_system_tokens=8192,
        special_constraints=["Prefer Chinese responses when user writes in Chinese"],
    ),
    "deepseek": ModelAdaptation(
        model_id="deepseek",
        tool_call_format="json",
        tool_instruction="[TOOL CALL FORMAT — DEEPSEEK]\nUse standard OpenAI function calling format.\nRead files before editing. Verify all required parameters before calling tools.",
        max_system_tokens=8192,
    ),
    "kimi": ModelAdaptation(
        model_id="kimi",
        tool_call_format="json",
        tool_instruction="[TOOL CALL FORMAT — KIMI]\nUse standard tool calling with clear parameter types.\nPlan multi-step tasks before executing. Confirm destructive operations.",
        max_system_tokens=16384,
        special_constraints=["Supports extended context windows"],
    ),
    "llama": ModelAdaptation(
        model_id="llama",
        tool_call_format="json",
        tool_instruction="[TOOL CALL FORMAT — LLAMA]\nUse Inst/chat format with tool descriptions in system prompt.\nState your plan briefly before each tool call. Be explicit about file paths.",
        max_system_tokens=4096,
    ),
}


class PromptEngine:
    """Three-layer prompt engine with dynamic injection and model adaptation."""

    def __init__(self) -> None:
        self._layer0_fragments: list[PromptFragment] = []
        self._layer1_fragments: list[PromptFragment] = []
        self._layer2_fragments: list[PromptFragment] = []
        self._model_adaptations: dict[str, ModelAdaptation] = dict(MODEL_ADAPTATIONS)
        self._reflection_prompt: str = TOOL_REFLECTION_PROMPT
        self._token_budget: int = 12000
        self._initialize_defaults()

    def _initialize_defaults(self) -> None:
        """Register default immutable base prompt."""
        self._layer0_fragments.append(
            PromptFragment(
                content=BASE_SYSTEM_PROMPT,
                layer=PromptLayer.IMMUTABLE_BASE,
                priority=0,
                source="engine:base",
            )
        )

    def register_base_fragment(self, content: str, priority: int = 0) -> str:
        """Register an immutable base prompt fragment. Returns fragment ID."""
        fragment = PromptFragment(
            content=content,
            layer=PromptLayer.IMMUTABLE_BASE,
            priority=priority,
            source="registered",
        )
        self._layer0_fragments.append(fragment)
        self._layer0_fragments.sort(key=lambda f: f.priority)
        return fragment.id

    def register_session_fragment(self, content: str, priority: int = 0) -> str:
        """Register a session-level prompt fragment. Returns fragment ID."""
        fragment = PromptFragment(
            content=content,
            layer=PromptLayer.SESSION_TEMPLATE,
            priority=priority,
            source="session",
        )
        self._layer1_fragments.append(fragment)
        self._layer1_fragments.sort(key=lambda f: f.priority)
        return fragment.id

    def register_runtime_fragment(
        self,
        content: str,
        priority: int = 0,
        condition: str | None = None,
    ) -> str:
        """Register a dynamic runtime prompt fragment. Returns fragment ID."""
        fragment = PromptFragment(
            content=content,
            layer=PromptLayer.DYNAMIC_RUNTIME,
            priority=priority,
            source="runtime",
            condition=condition,
        )
        self._layer2_fragments.append(fragment)
        self._layer2_fragments.sort(key=lambda f: f.priority)
        return fragment.id

    def clear_layer(self, layer: PromptLayer) -> None:
        """Clear all fragments from a specific layer."""
        if layer == PromptLayer.IMMUTABLE_BASE:
            self._layer0_fragments.clear()
            self._initialize_defaults()
        elif layer == PromptLayer.SESSION_TEMPLATE:
            self._layer1_fragments.clear()
        elif layer == PromptLayer.DYNAMIC_RUNTIME:
            self._layer2_fragments.clear()

    def remove_fragment(self, fragment_id: str) -> bool:
        """Remove a fragment by ID. Returns True if found and removed."""
        for collection in [
            self._layer0_fragments,
            self._layer1_fragments,
            self._layer2_fragments,
        ]:
            for i, f in enumerate(collection):
                if f.id == fragment_id:
                    collection.pop(i)
                    return True
        return False

    def assemble_prompt(
        self,
        context: RuntimeContext,
        include_reflection: bool = False,
    ) -> str:
        """Assemble the complete system prompt from all layers."""
        parts: list[str] = []

        for fragment in sorted(self._layer0_fragments, key=lambda f: f.priority):
            rendered = fragment.render(context.custom_variables)
            if rendered.strip():
                parts.append(rendered)

        for fragment in sorted(self._layer1_fragments, key=lambda f: f.priority):
            rendered = fragment.render(context.custom_variables)
            if rendered.strip():
                parts.append(rendered)

        runtime_parts = self._build_runtime_parts(context)
        parts.extend(runtime_parts)

        if include_reflection:
            parts.append(self._reflection_prompt)

        assembled = "\n\n".join(parts)
        assembled = self._apply_model_adaptation(assembled, context.model_id)
        return self._enforce_token_budget(assembled)


    def _build_runtime_parts(self, context: RuntimeContext) -> list[str]:
        """Build runtime prompt parts based on current context."""
        parts: list[str] = []

        if context.autonomous_mode:
            parts.append(AUTONOMOUS_MODE_PROMPT)

        if context.sandbox_enabled:
            parts.append(SANDBOX_CONSTRAINT_PROMPT)

        if context.mcp_ready:
            parts.append(MCP_CONSTRAINT_PROMPT)

        if context.permission_level == "high_risk":
            parts.append(HIGH_RISK_PERMISSION_PROMPT)

        if context.active_skills:
            skill_list = "\n".join(f"- {s}" for s in context.active_skills)
            parts.append(SKILL_LAZY_LOAD_PROMPT.format(skill_list=skill_list))

        if context.task_objective:
            parts.append(f"[CURRENT OBJECTIVE]\n{context.task_objective}")
            parts.append(TASK_PLANNING_PROMPT)

        if context.multi_agent_mode:
            parts.append(MULTI_AGENT_COLLABORATION_PROMPT)

        if context.memory_retrieval_enabled:
            parts.append(MEMORY_RETRIEVAL_PROMPT)

        if context.fault_recovery_enabled:
            parts.append(FAULT_RECOVERY_PROMPT)

        for fragment in sorted(self._layer2_fragments, key=lambda f: f.priority):
            if fragment.condition and not self._evaluate_condition(fragment.condition, context):
                continue
            rendered = fragment.render(context.custom_variables)
            if rendered.strip():
                parts.append(rendered)

        return parts

    def _evaluate_condition(self, condition: str, context: RuntimeContext) -> bool:
        """Evaluate a runtime condition against the current context."""
        try:
            if condition == "autonomous_mode":
                return context.autonomous_mode
            if condition == "sandbox_enabled":
                return context.sandbox_enabled
            if condition == "mcp_ready":
                return context.mcp_ready
            if condition == "high_risk":
                return context.permission_level == "high_risk"
            if condition.startswith("skill_active:"):
                skill_name = condition.split(":", 1)[1]
                return skill_name in context.active_skills
            if condition.startswith("model_is:"):
                model_name = condition.split(":", 1)[1]
                return model_name in context.model_id
            return True
        except Exception:
            return True

    def _apply_model_adaptation(self, prompt: str, model_id: str) -> str:
        """Apply model-specific adaptations to the assembled prompt."""
        if not model_id:
            return prompt

        for key, adaptation in self._model_adaptations.items():
            if key in model_id.lower():
                return adaptation.adapt_base_prompt(prompt)

        return prompt

    def _enforce_token_budget(self, prompt: str) -> str:
        """Trim prompt if it exceeds the token budget."""
        estimated_tokens = len(prompt) // 4
        if estimated_tokens <= self._token_budget:
            return prompt

        excess = estimated_tokens - self._token_budget
        chars_to_remove = excess * 4

        if chars_to_remove >= len(prompt):
            return prompt[: self._token_budget * 4]

        return prompt[: len(prompt) - chars_to_remove]

    def register_model_adaptation(self, adaptation: ModelAdaptation) -> None:
        """Register or update a model-specific adaptation."""
        self._model_adaptations[adaptation.model_id] = adaptation

    def get_model_adaptation(self, model_id: str) -> ModelAdaptation | None:
        """Get adaptation config for a specific model."""
        if not model_id:
            return None
        for key, adaptation in self._model_adaptations.items():
            if key in model_id.lower():
                return adaptation
        return None

    def set_reflection_prompt(self, prompt: str) -> None:
        """Set the tool failure reflection prompt."""
        self._reflection_prompt = prompt

    def set_token_budget(self, budget: int) -> None:
        """Set the maximum system prompt token budget."""
        self._token_budget = budget

    def get_layer_fragments(self, layer: PromptLayer) -> list[PromptFragment]:
        """Get all fragments for a specific layer."""
        if layer == PromptLayer.IMMUTABLE_BASE:
            return list(self._layer0_fragments)
        if layer == PromptLayer.SESSION_TEMPLATE:
            return list(self._layer1_fragments)
        return list(self._layer2_fragments)

    def apply_template(self, template: PromptTemplate, variables: dict[str, str] | None = None) -> None:
        """Apply a prompt template as session-level fragments."""
        content = template.render(variables)
        self._layer1_fragments.append(
            PromptFragment(
                content=content,
                layer=PromptLayer.SESSION_TEMPLATE,
                priority=0,
                source=f"template:{template.name}",
            )
        )

    def estimate_token_count(self, context: RuntimeContext) -> int:
        """Estimate the total token count for the assembled prompt."""
        assembled = self.assemble_prompt(context)
        return len(assembled) // 4
