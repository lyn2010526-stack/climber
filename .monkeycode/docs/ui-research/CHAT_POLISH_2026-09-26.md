# Chat Core UX Research

Date: 2026-09-26

## Scope

This review covers editing, retry, streaming, stop, error, empty, long-message, tool-output, approval, IME, mobile composer, reading width, and scroll-follow behavior. The implementation work is limited to the four requested chat components and their focused tests.

## Source Evidence

### LibreChat

- Repository: `https://github.com/danny-avila/LibreChat`
- The project documents edit and resubmit as conversation branching, which means edit is a conversation action rather than an in-place text-only mutation.
- The current LibreChat release notes describe completed Markdown blocks being memoized during streaming and per-call tool results. The transferable rule is to keep the streaming row stable while incremental content changes and to expose tool results at call granularity.
- Evidence retrieved from the LibreChat release notes: `https://www.librechat.ai/changelog/v0.8.7-rc1`.

### Open WebUI

- Repository: `https://github.com/open-webui/open-webui`
- `src/lib/components/chat/Messages/ResponseMessage.svelte` keeps a local editable draft, focuses the textarea after the edit view mounts, preserves scroll position while resizing, and separates visible response content from error/status rendering.
- The same component exposes copy, feedback, edit, continue, regenerate, and branch controls only when the response lifecycle permits them. This supports keeping action availability tied to completion state.
- The content pipeline renders response content, status history, errors, citations, and code execution as separate branches. This maps to the implementation rule that a tool result, tool error, and lifecycle status need separate semantic regions.

### assistant-ui

- Repository: `https://github.com/assistant-ui/assistant-ui`
- `packages/react/src/primitives/composer/ComposerInput.tsx` tracks IME composition separately, ignores composing Enter events, supports autosize, and controls focus on run start and scroll-to-bottom.
- `packages/react/src/primitives/thread/ThreadViewport.tsx` centralizes auto-scroll and viewport registration. Its documented `autoScroll` and run/initialize/thread-switch options reinforce that following output must be conditional on the reader remaining at the bottom.
- The library keeps composer controls headless and state-driven. The relevant local adaptation is one send/stop slot, with drafts retained while a run is active.

## Applied Decisions

- Live chat tool calls now use `ToolCallVisualization`, so result-first rendering, lazy arguments, long-output reveal, and canonical pending/running/success/error/cancelled/unknown status semantics apply to the transcript.
- Edit mode has a dedicated textarea ref and restores focus after entering edit mode. IME guards remain shared with the composer.
- Approval callbacks preserve failed requests for the existing retry path and only resolve cards after the API operation succeeds. Expired requests remain locked through `FloatingPermissionDialog`.
- Scroll-follow remains opt-in based on the user's current scroll position; the jump-to-bottom control is the recovery action when the reader inspects history.

## Remaining Product-Level Gaps

- The current public `ChatInterface` contract has no explicit `onRegenerate` or branch-navigation callback, so retry remains error-row retry and edit resubmission rather than full branch-aware regeneration.
- Approval expiration depends on the API's conflict/error signal; the component has no independent countdown or server deadline field.
- Long transcript virtualization and message-level branch navigation require changes outside the permitted component scope.
