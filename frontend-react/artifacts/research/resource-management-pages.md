# Resource Management Page Research

## Scope

The Agents, Skills, MCP, and Plugins pages use dense rows so an operator can compare identity, reported lifecycle state, counts, and the next available action without opening marketing-style cards.

## Reference findings

- OpenHands keeps MCP health separate from installation state and exposes a disabled test action while a probe is running. A failed probe keeps its error and offers retry or recovery actions.
- Cline separates transport and server type, then exposes configuration details behind a disclosure. This keeps the primary list scannable while preserving operational detail.
- Dify groups MCP parameters in a focused editor and disables submit while create/update is pending.
- CopilotKit and Agno expose the agent/tool relationship through explicit runtime configuration rather than decorative summaries.

## Applied contract

- Render only fields returned by the API. Missing lifecycle fields remain visibly unknown.
- Keep server, tool, and resource information in a clear hierarchy: the server row is primary; details expose counts and returned child entries.
- Lock conflicting actions while a mutation is pending.
- Preserve the row after a failed mutation, show the failure inline, and provide a retry using the same API contract.
- Keep catalog fetch errors retryable without replacing successful rows already on screen.
