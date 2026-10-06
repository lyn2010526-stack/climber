# Climber Prompt System

Climber now has a pure-Python prompt layer at `app/core/prompts/`. It is a
runtime contract for prompt assembly, rather than a collection of advisory
Markdown files.

## Structure

- `core.system`: immutable safety, workflow, tool, progress, validation, and
  safe-output sections.
- `task.type`: task-specific guidance for implementation, review, and research.
- `TOOL_CONTRACT_VERSION`: compatibility boundary for tool names, arguments, and
  result verification.
- Model adaptation: small format constraints selected by model family.
- Progress and recovery: user-visible status summaries with private reasoning
  excluded from output.

The design extracts recurring engineering patterns from public project
documentation. It does not copy prompt text or claim that every implementation
detail in those projects is authentic.

## Public sources and extracted structure

| Project | Public URL | Extracted structure |
| --- | --- | --- |
| Cursor | https://docs.cursor.com/context/rules | repository-scoped rules and durable instruction layers |
| Claude Code | https://docs.anthropic.com/en/docs/claude-code/memory | project memory, scoped instructions, tool-oriented workflow |
| Devin | https://devin.ai/ | task decomposition, execution loop, verification-oriented delivery |
| OpenHands | https://github.com/All-Hands-AI/OpenHands | agent action/observation loop, runtime tool boundary |
| SWE-agent | https://github.com/SWE-agent/SWE-agent | issue context, structured actions, test-based validation |
| Aider | https://aider.chat/docs/ | repository context, edit constraints, model-specific formats |
| Manus | https://manus.im/ | planning, persistent task state, progress-oriented execution |
| Perplexity | https://docs.perplexity.ai/ | source-grounded answers and citation-aware research |
| Kilo Code | https://github.com/Kilo-Org/kilocode | mode-specific behavior and tool-enabled coding workflow |
| LangGraph | https://langchain-ai.github.io/langgraph/ | stateful graph steps, checkpoints, interrupts, recovery |

These links are source references for structure and vocabulary. The built-in
texts are Climber-authored synthesis.

## Version policy

Versions use semantic version strings. Only `active` versions resolve through
`resolve_active_prompt`; `deprecated` versions remain listable for audit and
are rejected when explicitly requested. This gives callers a safe rollback
boundary: promote a tested historical version by changing its registry status,
then deploy the change as a normal code review. Prompt contracts are validated
before injection, and tool contract changes require a compatible version bump.

## Call surface

```python
from app.core.prompts import build_injected_prompt, list_versions

bundle = build_injected_prompt(task_type="implementation", model_id="deepseek")
system_prompt = bundle["system_prompt"]
safe_metadata = bundle["metadata"]
versions = list_versions("core.system")
```

The application integration point is the existing model request assembly path:
call `build_injected_prompt` immediately before constructing the model request,
prepend its `system_prompt` as the mandatory system message, and forward only
the returned safe metadata to progress/event APIs. A later integration should
live in `app/core/prompt_engine/engine.py` or the single model dispatch adapter,
while preserving existing API, storage, and frontend boundaries.
