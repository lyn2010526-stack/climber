import type { Message, ToolCall } from '../../useChat';

export interface DeliverableEntry {
  readonly path: string;
  readonly added: number;
  readonly removed: number;
  readonly kind: 'file' | 'website';
}

const FILE_TOKENS = ['edit', 'write', 'patch', 'replace', 'create', 'insert', 'append', 'apply'];
const WEBSITE_TOKENS = ['deploy', 'publish', 'preview', 'website', 'site', 'artifact', 'serve'];

function toolTokens(name: string): string[] {
  return name.toLowerCase().split(/[^a-z\d]+/).filter(Boolean);
}

function matchesAny(name: string, tokens: readonly string[]): boolean {
  const own = toolTokens(name);
  return tokens.some(token => own.includes(token));
}

/** 文件变更工具：write / edit / patch / apply 等，参数里带目标路径。 */
export function isFileMutationTool(name: string): boolean {
  return matchesAny(name, FILE_TOKENS);
}

/** 网页交付工具：deploy / preview / publish / serve 等。 */
export function isWebsiteTool(name: string): boolean {
  return matchesAny(name, WEBSITE_TOKENS);
}

export function readToolPath(args: Record<string, unknown>): string | undefined {
  const path = args.file_path ?? args.path ?? args.filename;
  return typeof path === 'string' && path.trim() !== '' ? path.trim() : undefined;
}

function countLines(text: unknown): number {
  if (typeof text !== 'string' || text.trim() === '') return 0;
  const body = text.endsWith('\n') ? text.slice(0, -1) : text;
  return body === '' ? 0 : body.split('\n').length;
}

function readStringArg(args: Record<string, unknown>, keys: readonly string[]): string | undefined {
  for (const key of keys) {
    const value = args[key];
    if (typeof value === 'string') return value;
  }
  return undefined;
}

const URL_PATTERN = /https?:\/\/[^\s"'<>\\]+/gi;

/** 从 unified diff 结果文本粗计增删行，跳过分隔行。 */
function diffCounts(result: string | undefined): { added: number; removed: number } {
  if (!result) return { added: 0, removed: 0 };
  let added = 0;
  let removed = 0;
  for (const line of result.split('\n')) {
    if (line.startsWith('+') && !line.startsWith('+++')) added += 1;
    else if (line.startsWith('-') && !line.startsWith('---')) removed += 1;
  }
  return { added, removed };
}

function websiteUrlFromArgs(args: Record<string, unknown>): string | undefined {
  const url = args.url ?? args.href ?? args.preview_url ?? args.website_url;
  return typeof url === 'string' && /^https?:\/\//i.test(url.trim()) ? url.trim() : undefined;
}

function websiteUrlsFromResult(result: string | undefined): string[] {
  if (!result) return [];
  const urls = result.match(URL_PATTERN) ?? [];
  return [...new Set(urls.map(url => url.replace(/[),.;]+$/g, '')))];
}

/** 单个工具调用 → 交付物条目；失败或不可识别的调用产出空数组。 */
export function entriesForToolCall(call: ToolCall): DeliverableEntry[] {
  if (call.error) return [];
  const args = call.arguments ?? {};
  const path = readToolPath(args);
  if (isFileMutationTool(call.name) && path) {
    const addedText = readStringArg(args, ['new_string', 'new_text', 'content', 'new_value']);
    const removedText = readStringArg(args, ['old_string', 'old_text']);
    const diff = addedText === undefined && removedText === undefined
      ? diffCounts(call.result)
      : { added: countLines(addedText), removed: countLines(removedText) };
    return [{ path, added: diff.added, removed: diff.removed, kind: 'file' }];
  }
  if (isWebsiteTool(call.name)) {
    const url = websiteUrlFromArgs(args);
    const urls = url ? [url] : websiteUrlsFromResult(call.result);
    return urls.map(candidate => ({ path: candidate, added: 0, removed: 0, kind: 'website' }));
  }
  return [];
}

/** 按 path+kind 合并多次写入同一文件的计数。 */
export function mergeDeliverables(entries: readonly DeliverableEntry[]): DeliverableEntry[] {
  const merged = new Map<string, DeliverableEntry>();
  for (const entry of entries) {
    const key = `${entry.kind}:${entry.path}`;
    const prev = merged.get(key);
    if (prev) {
      merged.set(key, { ...prev, added: prev.added + entry.added, removed: prev.removed + entry.removed });
    } else {
      merged.set(key, entry);
    }
  }
  return [...merged.values()];
}

export function isWebsiteEntry(entry: DeliverableEntry): boolean {
  return entry.kind === 'website' || /^https?:\/\//i.test(entry.path);
}

/**
 * 聚合消息流中最近一个产出交付物的回合。每个 assistant 消息代表一轮，倒序找到
 * 第一个有交付物的回合；没有产出返回 null（卡片整体隐藏）。
 */
export function selectTurnDeliverables(messages: readonly Message[]): DeliverableEntry[] | null {
  for (let i = messages.length - 1; i >= 0; i -= 1) {
    const message = messages[i];
    if (!message || message.role !== 'assistant') continue;
    const entries = mergeDeliverables((message.toolCalls ?? []).flatMap(entriesForToolCall));
    if (entries.length > 0) return entries;
  }
  return null;
}