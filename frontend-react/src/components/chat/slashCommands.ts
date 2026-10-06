/**
 * Slash command catalog and client-side resolution for the chat composer.
 *
 * Mirrors the backend registry in `app/core/slash/` (same names, same
 * argument rules). The frontend resolves commands locally for autocomplete
 * and for the "which command is this" check; execution always goes through
 * `api.runSlashCommand` (POST /api/v1/sessions/{id}/slash), which streams the
 * reply as SSE.
 */
import type { ChatStreamEvent } from '../../types/chatEvents';
import { api } from '../../api';

export interface SlashArgInfo {
  name: string;
  required: boolean;
  choices: string[] | null;
  description: string;
}

export interface SlashCommandInfo {
  name: string;
  aliases: string[];
  summary: string;
  usage: string;
  streaming: boolean;
  allowed_while_streaming: boolean;
  args: SlashArgInfo[];
}

/** Fallback catalog; refreshed from GET /api/v1/chat-commands when available. */
export const FALLBACK_COMMANDS: SlashCommandInfo[] = [
  {
    name: 'help', aliases: [], streaming: false, allowed_while_streaming: false,
    summary: 'Show available slash commands and usage.',
    usage: '/help [command]',
    args: [{ name: 'command', required: false, choices: null, description: 'Show detailed usage for one command' }],
  },
  {
    name: 'model', aliases: [], streaming: false, allowed_while_streaming: false,
    summary: 'Show or switch the session model (provider:model_id).',
    usage: '/model [provider:model_id]',
    args: [{ name: 'model_spec', required: false, choices: null, description: 'provider:model_id, e.g. openai:gpt-4o-mini' }],
  },
  {
    name: 'level', aliases: [], streaming: false, allowed_while_streaming: false,
    summary: 'Show or set the reasoning level for this session.',
    usage: '/level [auto|tree|deep|debate]',
    args: [{ name: 'level', required: false, choices: ['auto', 'tree', 'deep', 'debate'], description: 'Reasoning strategy' }],
  },
  {
    name: 'clear', aliases: [], streaming: false, allowed_while_streaming: false,
    summary: 'Clear all messages in the current session.',
    usage: '/clear',
    args: [],
  },
  {
    name: 'retry', aliases: [], streaming: true, allowed_while_streaming: false,
    summary: 'Re-run the last user message as a fresh streaming turn.',
    usage: '/retry',
    args: [],
  },
  {
    name: 'stop', aliases: ['cancel'], streaming: false, allowed_while_streaming: true,
    summary: 'Interrupt the turn that is currently running.',
    usage: '/stop',
    args: [],
  },
  {
    name: 'status', aliases: [], streaming: false, allowed_while_streaming: false,
    summary: 'Show session status, model, iteration and token counters.',
    usage: '/status',
    args: [],
  },
];

/** Extract the first token when the input starts with "/". */
export function extractCommandHead(input: string): string | null {
  const text = input.trimStart();
  if (!text.startsWith('/')) return null;
  const stripped = text.slice(1);
  if (!stripped) return '';
  const head = stripped.split(/\s+/)[0];
  return head ? head.toLowerCase() : null;
}

/** Find a command by name or alias (case-insensitive). */
export function findCommand(
  catalog: SlashCommandInfo[],
  name: string | null,
): SlashCommandInfo | undefined {
  if (!name) return undefined;
  const lowered = name.toLowerCase();
  return catalog.find(
    c => c.name === lowered || c.aliases.some(a => a.toLowerCase() === lowered),
  );
}

/**
 * True only when the input is an *exact* command invocation: the first token
 * matches a registered command. "/etc/hosts is a file" is not a command and
 * must reach the agent untouched.
 */
export function resolveCommand(
  catalog: SlashCommandInfo[],
  input: string,
): { command: SlashCommandInfo; rest: string } | null {
  const text = input.trim();
  if (!text.startsWith('/')) return null;
  const stripped = text.slice(1);
  if (!stripped) return null;
  const match = stripped.match(/^(\S+)\s*([\s\S]*)$/);
  if (!match?.[1]) return null;
  const command = findCommand(catalog, match[1]);
  if (!command) return null;
  return { command, rest: match[2] ?? '' };
}

/** Commands that can still be typed while a turn is streaming. */
export function completionsFor(
  catalog: SlashCommandInfo[],
  query: string,
  isStreaming: boolean,
): SlashCommandInfo[] {
  const q = query.toLowerCase();
  return catalog
    .filter(c => c.name.startsWith(q) || c.aliases.some(a => a.startsWith(q)))
    .filter(c => !isStreaming || c.allowed_while_streaming)
    .sort((a, b) => a.name.localeCompare(b.name));
}

/**
 * Execute a slash command and stream the reply. Local commands (help, model,
 * clear…) come back as synthetic text/done frames; retry and passthrough
 * stream genuine engine events — one consumption path for the caller.
 */
export function executeSlashCommand(
  sessionId: string,
  message: string,
  onEvent: (event: ChatStreamEvent) => void,
  options: { signal?: AbortSignal } = {},
): () => void {
  return api.runSlashCommand(sessionId, message, onEvent, options);
}

/** Interrupt the running turn before dropping the SSE connection. */
export function cancelSessionTurn(sessionId: string): void {
  api.cancelSessionTurn(sessionId);
}
