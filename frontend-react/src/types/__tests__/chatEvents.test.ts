import { describe, expect, it } from 'vitest';
import { normalizeChatEvent } from '../chatEvents';

describe('normalizeChatEvent', () => {
  it('reads the event name from the event: line (current backend shape)', () => {
    const result = normalizeChatEvent({ event: 'text', data: { content: 'hi' } });
    expect(result).toEqual({ type: 'text', delta: 'hi' });
  });

  it('prefers data.type over the event: line (AG-UI shape)', () => {
    const result = normalizeChatEvent({ event: 'message', data: { type: 'text', content: 'hi' } });
    expect(result).toEqual({ type: 'text', delta: 'hi' });
  });

  it('passes through a bare string payload as the delta', () => {
    expect(normalizeChatEvent({ event: 'text', data: 'raw text' })).toEqual({ type: 'text', delta: 'raw text' });
    expect(normalizeChatEvent({ event: 'thinking', data: 'pondering' })).toEqual({ type: 'thinking', delta: 'pondering' });
  });

  it('accepts alternate delta key names', () => {
    expect(normalizeChatEvent({ event: 'text', data: { delta: 'a' } })).toEqual({ type: 'text', delta: 'a' });
    expect(normalizeChatEvent({ event: 'thinking', data: { reasoning: 'b' } })).toEqual({ type: 'thinking', delta: 'b' });
  });

  it('defaults a missing tool id and fills arguments with an empty object', () => {
    const result = normalizeChatEvent({ event: 'tool_call', data: { name: 'search' } });
    expect(result).toEqual({ type: 'tool_call', toolCall: { id: '', name: 'search', arguments: {} } });
  });

  it('names an unnamed tool call "unknown"', () => {
    const result = normalizeChatEvent({ event: 'tool_call', data: { id: 'tc-1' } });
    expect(result.type === 'tool_call' && result.toolCall.name).toBe('unknown');
  });

  it('maps tool_result result and error into separate fields', () => {
    const ok = normalizeChatEvent({ event: 'tool_result', data: { id: 'tc-1', result: 'done' } });
    expect(ok).toEqual({ type: 'tool_result', toolCallId: 'tc-1', result: 'done', error: '' });

    const failed = normalizeChatEvent({ event: 'tool_result', data: { id: 'tc-1', error: 'boom' } });
    expect(failed).toEqual({ type: 'tool_result', toolCallId: 'tc-1', result: '', error: 'boom' });
  });

  it('reads the done message id and reports its absence as undefined', () => {
    expect(normalizeChatEvent({ event: 'done', data: { message_id: 'm-9' } })).toEqual({ type: 'done', messageId: 'm-9' });
    expect(normalizeChatEvent({ event: 'done', data: {} })).toEqual({ type: 'done', messageId: undefined });
  });

  it('resolves an error message from detail, error, or message', () => {
    expect(normalizeChatEvent({ event: 'error', data: { detail: 'd' } })).toEqual({ type: 'error', message: 'd' });
    expect(normalizeChatEvent({ event: 'error', data: { error: 'e' } })).toEqual({ type: 'error', message: 'e' });
    expect(normalizeChatEvent({ event: 'error', data: { message: 'm' } })).toEqual({ type: 'error', message: 'm' });
  });

  it('falls back to a generic message when the error payload carries nothing', () => {
    expect(normalizeChatEvent({ event: 'error', data: {} })).toEqual({ type: 'error', message: 'Unknown error' });
  });

  it('classifies an unrecognised event as unknown and keeps the raw frame', () => {
    const raw = { event: 'mystery', data: { foo: 1 } };
    const result = normalizeChatEvent(raw);
    expect(result).toEqual({ type: 'unknown', raw });
  });

  it('classifies a frame with no event name at all as unknown', () => {
    expect(normalizeChatEvent({ event: '', data: { content: 'x' } }).type).toBe('unknown');
  });
});
