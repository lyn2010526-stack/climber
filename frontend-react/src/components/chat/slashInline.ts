import type { SlashCommandInfo } from './slashCommands';

/**
 * Inline (ghost) completion for a partially typed slash command.
 *
 * Codex prints the rest of the matched command straight after the caret and
 * accepts it with Tab; cc-haha's footer suggestions do the same above the
 * input. Climber already renders a dropdown (`SlashCommandMenu`) and already
 * maps Tab to "accept the highlighted entry", so what was missing is the
 * at-the-caret preview of what that Tab will type. This module derives it; the
 * component beside it only draws the result, and no second keyboard path is
 * introduced.
 *
 * Kept separate from the component so the React Fast Refresh boundary stays a
 * single component export.
 */

export interface InlineSlashCompletion {
  /** The literal text the user has typed, including the leading slash. */
  typed: string;
  /** The remaining characters of the best-matching command name. */
  suffix: string;
  /** The command the ghost text is completing to. */
  command: SlashCommandInfo;
}

/**
 * Derive the ghost completion for the current composer value.
 *
 * Returns `null` unless the value is a bare `/token` (no space yet), which is
 * exactly the state the dropdown owns. Command aliases never produce a ghost
 * because the canonical name is what Tab types.
 */
export function inlineSlashCompletion(
  input: string,
  catalog: SlashCommandInfo[],
  isStreaming = false,
): InlineSlashCompletion | null {
  const match = /^\/(\S*)$/.exec(input.trimStart());
  if (!match) return null;
  const head = (match[1] ?? '').toLowerCase();
  if (!head) return null;

  const candidates = catalog
    .filter((command) => !isStreaming || command.allowed_while_streaming)
    .filter((command) => command.name.toLowerCase().startsWith(head) && command.name.toLowerCase() !== head);
  if (candidates.length === 0) return null;

  candidates.sort((a, b) => a.name.localeCompare(b.name));
  const command = candidates[0]!;
  return { typed: `/${head}`, suffix: command.name.slice(head.length), command };
}
