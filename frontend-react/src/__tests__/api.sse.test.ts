import { afterEach, describe, expect, it, vi } from 'vitest';

import { api, SSEIdleTimeoutError } from '../api';

const encoder = new TextEncoder();

/**
 * A response body the test drives by hand: `push` appends a frame, `finish`
 * closes the stream and `idle` leaves it open without any traffic.
 */
function controllableStream() {
  let controller: ReadableStreamDefaultController<Uint8Array>;
  const body = new ReadableStream<Uint8Array>({
    start(c) {
      controller = c;
    },
  });
  return {
    body,
    push(frame: string) {
      controller.enqueue(encoder.encode(frame));
    },
    finish() {
      controller.close();
    },
  };
}

function frame(payload: unknown) {
  return `data: ${JSON.stringify(payload)}\n\n`;
}

function eventFrame(name: string, payload: unknown) {
  return `event: ${name}\ndata: ${JSON.stringify(payload)}\n\n`;
}

function collect() {
  const events: Array<{ type: string; delta?: string; message?: string }> = [];
  return { events, onEvent: (event: { type: string; delta?: string; message?: string }) => events.push(event) };
}

/** Lets the fetch promise chain and the stream reader settle. */
const settle = () => new Promise((resolve) => setTimeout(resolve, 0));

describe('chatStream SSE idle handling', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('handles byte-split CRLF, mixed separators, multiline JSON and UTF-8 at EOF', async () => {
    // Hand-authored SSE fixture with each byte delivered separately.
    const bytes = encoder.encode('event: text\r\ndata: {"content":"中文"}\r\n\r\nevent: text\ndata: {\ndata: "content":" next"}\n\nevent: done\r\ndata: {}');
    const body = new ReadableStream<Uint8Array>({ start(controller) {
      for (const byte of bytes) controller.enqueue(Uint8Array.of(byte));
      controller.close();
    } });
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(body)));
    const { events, onEvent } = collect();
    await new Promise<void>(resolve => api.chatStream('a', 'fixture', event => {
      onEvent(event);
      if (event.type === 'done' || event.type === 'error') resolve();
    }));
    expect(events).toEqual([{ type: 'text', delta: '中文' }, { type: 'text', delta: ' next' }, { type: 'done' }]);
  });

  it('parses AG-UI frames and finishes cleanly on a normal close', async () => {
    const stream = controllableStream();
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, status: 200, body: stream.body }));

    const { events, onEvent } = collect();
    api.chatStream('s1', 'hello', onEvent);
    await settle();

    // AG-UI 形态：事件名放在 JSON `data.type`。
    stream.push(frame({ type: 'text', content: 'hi' }));
    await settle();
    stream.finish();
    await settle();

    expect(events).toEqual([{ type: 'text', delta: 'hi' }]);
  });

  it('parses the event-line form the current backend emits', async () => {
    const stream = controllableStream();
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, status: 200, body: stream.body }));

    const { events, onEvent } = collect();
    api.chatStream('s1', 'hello', onEvent);
    await settle();

    stream.push(eventFrame('text', { content: 'legacy' }));
    await settle();
    stream.finish();
    await settle();

    expect(events).toEqual([{ type: 'text', delta: 'legacy' }]);
  });

  it('reports a stalled connection as an error instead of a silent end', async () => {
    const stream = controllableStream();
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, status: 200, body: stream.body }));

    const { events, onEvent } = collect();
    api.chatStream('s1', 'hello', onEvent, { idleTimeoutMs: 25 });
    await settle();

    stream.push(frame({ type: 'text', content: 'partial' }));
    await settle();
    expect(events).toEqual([{ type: 'text', delta: 'partial' }]);

    // No further traffic: the guard must fire and surface as an error event.
    await new Promise((resolve) => setTimeout(resolve, 60));

    const last = events[events.length - 1];
    expect(last.type).toBe('error');
    expect(last.message).toMatch(/idle/i);
  });

  it('keeps the stream alive while frames keep arriving inside the window', async () => {
    const stream = controllableStream();
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, status: 200, body: stream.body }));

    const { events, onEvent } = collect();
    api.chatStream('s1', 'hello', onEvent, { idleTimeoutMs: 60 });
    await settle();

    for (let i = 0; i < 3; i += 1) {
      stream.push(frame({ type: 'text', content: `chunk-${i}` }));
      await new Promise((resolve) => setTimeout(resolve, 20));
    }
    await new Promise((resolve) => setTimeout(resolve, 30));

    expect(events).toHaveLength(3);
    expect(events.every((event) => event.type === 'text')).toBe(true);
  });

  it('carries the threshold on the error so callers can report it', () => {
    const error = new SSEIdleTimeoutError(120_000);
    expect(error).toBeInstanceOf(Error);
    expect(error.name).toBe('SSEIdleTimeoutError');
    expect(error.idleTimeoutMs).toBe(120_000);
  });
});
