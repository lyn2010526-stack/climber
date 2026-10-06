import { readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { api, ApiRequestError } from '../api';
import { normalizeChatEvent, parseRuntimeReport, parseSessionInput, type ChatStreamEvent } from '../types/chatEvents';

// Hand-authored fixtures validate protocol handling only; they do not prove backend execution.
const fixtureItem = { id: 'input-1', client_request_id: 'request-1', kind: 'follow_up', message: 'next', status: 'queued', sequence: 1, error: null };
const frame = (event: string, data: unknown) => `event: ${event}\ndata: ${JSON.stringify(data)}\n\n`;
afterEach(() => vi.unstubAllGlobals());

async function replay(raw: string, width = 1): Promise<ChatStreamEvent[]> {
  const bytes = new TextEncoder().encode(raw);
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(new ReadableStream({
    start(controller) {
      for (let index = 0; index < bytes.length; index += width) controller.enqueue(bytes.slice(index, index + width));
      controller.close();
    },
  }))));
  const events: ChatStreamEvent[] = [];
  let stop: (() => void) | undefined;
  try {
    await new Promise<void>((resolve, reject) => {
      const timer = setTimeout(() => reject(new Error(`Protocol replay timed out; observed events: ${JSON.stringify(events)}`)), 1500);
      stop = api.chatStream('fixture-session', 'fixture message', event => {
        events.push(event);
        if (event.type === 'done' || event.type === 'error') { clearTimeout(timer); resolve(); }
      }, { idleTimeoutMs: 1000 });
    });
    await new Promise(resolve => setTimeout(resolve, 0));
    return events;
  } finally { stop?.(); }
}

describe('FIXTURE: final SSE and queue contract (independent)', () => {
  it('preserves multi-turn order and UTF-8 across single-byte transport chunks', async () => {
    const frames = [
      ['turn_started', { input_id: null, message: 'first' }],
      ['text', { content: '\u4f60\u597d' }],
      ['turn_done', { input_id: null, turn_id: 'turn-1', message_id: 'message-1', status: 'completed' }],
      ['input_status', { item: { ...fixtureItem, status: 'started' } }],
      ['turn_started', { input_id: fixtureItem.id, message: 'next' }],
      ['turn_done', { input_id: fixtureItem.id, turn_id: 'turn-2', message_id: 'message-2', status: 'completed' }],
      ['input_status', { item: { ...fixtureItem, status: 'completed' } }],
      ['runtime_report', { completed: ['next'], executing: [], queued: [], risks: [] }],
      ['done', { message_id: 'message-2', status: 'completed', content: 'final' }],
    ] as const;
    const events = await replay(frames.map(([name, data]) => frame(name, data)).join(''));
    expect(events).toEqual(frames.map(([event, data]) => normalizeChatEvent({ event, data })));
    expect(events[1]).toEqual({ type: 'text', delta: '\u4f60\u597d' });
    expect(events.filter(event => event.type === 'done')).toHaveLength(1);
  });

  it('surfaces premature EOF after turn_done as an error', async () => {
    const events = await replay(frame('turn_started', { input_id: 'input-1', message: 'next' }) + frame('turn_done', { status: 'completed' }));
    expect(events.map(event => event.type)).toEqual(['turn_started', 'turn_done', 'error']);
    // The message text comes from the display locale (api_errors.chat_ended_early),
    // so the fixture only pins the fact that an error event was emitted.
    expect(events.at(-1)).toEqual({ type: 'error', message: expect.any(String) });
  });

  it('keeps blocked input and runtime risks before final stopped event', async () => {
    const item = { ...fixtureItem, status: 'blocked', error: 'Execution stopped' };
    const events = await replay(frame('input_status', { item }) + frame('runtime_report', { completed: [], executing: [], queued: [], risks: ['Execution stopped'] }) + frame('done', { status: 'stopped' }));
    expect(events[0]).toEqual({ type: 'input_status', item });
    expect(events[1]).toEqual({ type: 'runtime_report', report: { completed: [], executing: [], queued: [], risks: ['Execution stopped'] } });
    expect(events[2]).toMatchObject({ type: 'done', status: 'stopped' });
  });

  it('accepts a final LF frame without a trailing blank line', async () => {
    expect(await replay(frame('text', { content: 'partial' }) + 'event: done\ndata: {"status":"completed"}')).toEqual([
      { type: 'text', delta: 'partial' }, { type: 'done', messageId: undefined, status: 'completed' },
    ]);
  });

  it('parses CRLF-delimited SSE as separate events (standards compatibility probe)', async () => {
    const raw = (frame('text', { content: 'first' }) + frame('done', { status: 'completed' })).replaceAll('\n', '\r\n');
    expect(await replay(raw, 7)).toEqual([{ type: 'text', delta: 'first' }, { type: 'done', messageId: undefined, status: 'completed' }]);
  });

  it('accepts each final queue status and rejects invalid envelope fields', () => {
    for (const status of ['queued', 'applied', 'started', 'completed', 'blocked', 'failed']) {
      expect(parseSessionInput({ ...fixtureItem, status })).toEqual({ ...fixtureItem, status });
    }
    for (const change of [{ status: 'invented' }, { kind: 'chat' }, { id: null }, { client_request_id: null }, { sequence: '1' }]) {
      expect(parseSessionInput({ ...fixtureItem, ...change })).toBeNull();
    }
    expect(normalizeChatEvent({ event: 'input_status', data: { item: { ...fixtureItem, status: 'invented' } } }).type).toBe('unknown');
    expect(parseRuntimeReport({ completed: [], executing: ['now'], queued: null, risks: [1] })).toEqual({ completed: [], executing: ['now'], queued: null, risks: null });
  });

  it('preserves queue HTTP conflict status and backend detail', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(Response.json({ detail: 'client_request_id already used with different input' }, { status: 409 })));
    await expect(api.submitSessionInput('session/a', { client_request_id: 'r', kind: 'steering', message: 'new' })).rejects.toMatchObject({ name: 'ApiRequestError', status: 409, message: 'client_request_id already used with different input' });
    expect(new ApiRequestError(409, 'conflict').status).toBe(409);
  });

  it('gates resume locally and rejects malformed queue snapshot', async () => {
    const fetchMock = vi.fn().mockResolvedValue(Response.json({ items: [{ ...fixtureItem, status: 'invented' }] }));
    vi.stubGlobal('fetch', fetchMock);
    await expect(api.resumeSessionInputs('session/a', false)).rejects.toThrow();
    expect(fetchMock).not.toHaveBeenCalled();
    await expect(api.getSessionInputs('session/a')).rejects.toThrow();
    expect(fetchMock).toHaveBeenCalledWith('/api/v1/sessions/session%2Fa/inputs', expect.objectContaining({ signal: expect.any(AbortSignal) }));
  });

  it('resumes reviewed safe items while preserving blocked items with unknown effects', async () => {
    const blocked = { ...fixtureItem, id: 'unsafe-input', sequence: 2, status: 'blocked', error: 'Unknown effects; manual review required' };
    const report = { completed: [], executing: [], queued: ['next'], risks: [blocked.error] };
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(Response.json({ items: [fixtureItem, blocked] }))
      .mockResolvedValueOnce(Response.json(report));
    vi.stubGlobal('fetch', fetchMock);
    expect(await api.resumeSessionInputs('session/a', true)).toEqual([fixtureItem, blocked]);
    expect(fetchMock).toHaveBeenNthCalledWith(1, '/api/v1/sessions/session%2Fa/inputs/resume', expect.objectContaining({ method: 'POST', body: '{"review_confirmed":true}', signal: expect.any(AbortSignal) }));
    expect(await api.getSessionInputReport('session/a')).toEqual(report);
  });
});

const recordingPath = process.env.ACCEPTANCE_RECORDINGS;
describe.skipIf(!recordingPath)('LIVE RECORDING REPLAY: backend local slash SSE (not model execution)', () => {
  it('replays recorded backend bytes through production chatStream with independent normalization', async () => {
    const recordings = JSON.parse(readFileSync(recordingPath!, 'utf8'));
    expect(recordings.length).toBeGreaterThanOrEqual(2);
    for (const recording of recordings) {
      expect(recording.source).toBe('live-backend-local-slash');
      expect(recording.contentType).toContain('text/event-stream');
      expect(createHash('sha256').update(recording.raw).digest('hex')).toBe(recording.sha256);
      const expected = recording.raw.trim().split('\n\n').map((block: string) => {
        const lines = block.split('\n');
        return normalizeChatEvent({ event: lines.find(line => line.startsWith('event:'))!.slice(6).trim(), data: JSON.parse(lines.find(line => line.startsWith('data:'))!.slice(5)) });
      });
      expect(await replay(recording.raw, 1)).toEqual(expected);
      expect(expected).toEqual(recording.expected);
    }
  });
});
