/**
 * Deterministic message fixtures for the long-list baseline.
 *
 * Every fixture is generated from a fixed seed, so a rerun on the same host
 * renders byte-identical messages: any movement in the numbers is a real change
 * rather than a different conversation.
 *
 * Note on the wire shape: `getSessionMessages` returns `{ messages }` and
 * `useChat` reads `m.id`, `m.role`, `m.content`, `m.tool_calls`,
 * `m.tool_name` and `m.created_at` off each entry, so the fixture uses those
 * exact backend field names rather than the component's prop names.
 */

/** mulberry32: small, fast, seedable. */
function mulberry32(seed: number) {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

const WORDS = [
  'climber', 'ledger', 'virtualized', 'transcript', 'commit', 'baseline',
  'renderer', 'throttle', 'hydrat', 'reconcil', 'monotonic', 'fixture',
  'deterministic', 'frame', 'backpressure', 'session', 'quantile', 'probe',
];

/**
 * A session message in the backend payload shape.
 *
 * Assistant turns carry markdown (headings, lists, a fenced code block) because
 * that is the expensive path: it goes through `MarkdownRenderer`. User turns
 * are short plain text. Tool traffic lands on every 8th assistant turn so
 * `ToolCallCard` cost is inside the corpus rather than a separate scenario.
 */
export function buildSessionMessages(count: number, seed = 20260926) {
  const rand = mulberry32(seed);
  const messages: Array<Record<string, unknown>> = [];
  const baseTime = Date.UTC(2026, 0, 1, 0, 0, 0);

  for (let i = 0; i < count; i += 1) {
    const isUser = i % 2 === 0;
    const words: string[] = [];
    const length = 6 + Math.floor(rand() * 40);
    for (let w = 0; w < length; w += 1) words.push(WORDS[Math.floor(rand() * WORDS.length)] as string);

    const content = isUser
      ? words.slice(0, 5 + Math.floor(rand() * 8)).join(' ')
      : [
        `**Turn ${i}** summary of the ledger reconciliation.`,
        '',
        `- ${words.slice(0, 6).join(' ')}`,
        `- \`${words.slice(6, 9).join('_')}\``,
        `- ${words.slice(9, 16).join(' ')}`,
        '',
        '```ts',
        `const r = ${words[0]}; // ${words[1]}`,
        `export function ${words[2]}(x: number) { return x * ${Math.floor(rand() * 100)}; }`,
        '```',
        '',
        words.slice(16).join(' '),
      ].join('\n');

    const toolCalls = !isUser && i % 8 === 6
      ? [{
        id: `tc-${i}`,
        name: 'ledger_query',
        arguments: { range: words.slice(0, 3).join(':'), limit: 100 },
        result: JSON.stringify({ rows: 100, elapsed_ms: 12 }),
        status: 'success',
      }]
      : [];

    messages.push({
      id: `m-${i}`,
      role: isUser ? 'user' : 'assistant',
      content,
      tool_calls: toolCalls,
      tool_name: null,
      created_at: new Date(baseTime + i * 60_000).toISOString(),
    });
  }

  return messages;
}

/** Serialized payload the fixture server hands to the app. */
export function buildMessagesPayload(count: number, seed?: number): string {
  return JSON.stringify({ messages: buildSessionMessages(count, seed) });
}
