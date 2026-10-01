/**
 * The thinking stream, re-exported from its canonical implementation in
 * `../chat/ThinkingDetails`.
 *
 * The canonical component lives beside the transcript surfaces it renders
 * into, and its import path is stable for the consumers that already render
 * it. This bridge exists so a surface that reaches the thinking stream
 * through `components/agent` (the agent workbench layer, including the mobile
 * chat) has one import root for the agent's visualization vocabulary — the
 * same directory that owns `ToolCallCard` and `ThinkingIndicator` — without a
 * second implementation drifting apart.
 */
export { ThinkingDetails, default } from '../chat/ThinkingDetails';
