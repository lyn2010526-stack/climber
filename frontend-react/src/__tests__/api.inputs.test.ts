import { afterEach, expect, it, vi } from 'vitest';
import { api } from '../api';
import type { ChatStreamEvent, SessionInput } from '../types/chatEvents';
import i18n from '../i18n/config';

const item: SessionInput = { id: 'input-1', client_request_id: 'request-1', kind: 'steering', message: 'correction', status: 'queued', sequence: 1 };
afterEach(() => vi.unstubAllGlobals());

it('starts queued inputs with a bodyless POST and shares normalized turn events', async () => {
  // Hand-authored protocol fixture; no model execution is involved.
  const fetchMock = vi.fn().mockResolvedValue(new Response('event: turn_started\ndata: {"input_id":"i","message":"next"}\n\nevent: text\ndata: {"content":"answer"}\n\nevent: turn_done\ndata: {}\n\nevent: done\ndata: {}\n\n'));
  vi.stubGlobal('fetch', fetchMock);
  const events: ChatStreamEvent[] = [];
  await new Promise<void>(resolve => api.startSessionInputs('session/a', event => {
    events.push(event);
    if (event.type === 'done' || event.type === 'error') resolve();
  }));
  expect(fetchMock.mock.calls[0][0]).toBe('/api/v1/sessions/session%2Fa/inputs/start');
  expect(fetchMock.mock.calls[0][1]).toMatchObject({ method: 'POST', signal: expect.any(AbortSignal) });
  expect(fetchMock.mock.calls[0][1]).not.toHaveProperty('body');
  expect(events.map(event => event.type)).toEqual(['turn_started', 'text', 'turn_done', 'done']);
});

it('surfaces queue start rejection and premature EOF', async () => {
  vi.stubGlobal('fetch', vi.fn()
    .mockResolvedValueOnce(Response.json({ detail: 'Queue is frozen' }, { status: 409 }))
    .mockResolvedValueOnce(new Response('')));
  for (const expected of [/Queue is frozen/, new RegExp(i18n.t('api_errors.chat_ended_early').replace(/[.*+?^${}()|[\]\\]/g, '\\$&'))]) {
    const event = await new Promise<ChatStreamEvent>(resolve => api.startSessionInputs('a', resolve));
    expect(event.type).toBe('error');
    if (event.type === 'error') expect(event.message).toMatch(expected);
  }
});

it('reads the direct report and resumes with explicit review using the final routes', async () => {
  const report = { completed: ['done'], executing: [], queued: ['next'], risks: ['unknown effect'] };
  const blocked = { ...item, status: 'blocked', error: 'unknown effect' };
  const fetchMock = vi.fn().mockResolvedValueOnce(Response.json(report)).mockResolvedValueOnce(Response.json({ items: [item, blocked] }));
  vi.stubGlobal('fetch', fetchMock);
  expect(await api.getSessionInputReport('session/a')).toEqual(report);
  expect(fetchMock).toHaveBeenNthCalledWith(1, '/api/v1/sessions/session%2Fa/inputs/report', expect.objectContaining({ signal: expect.any(AbortSignal) }));
  expect(await api.resumeSessionInputs('session/a', true)).toEqual([item, blocked]);
  expect(fetchMock).toHaveBeenNthCalledWith(2, '/api/v1/sessions/session%2Fa/inputs/resume', expect.objectContaining({ method: 'POST', body: '{"review_confirmed":true}', signal: expect.any(AbortSignal) }));
});

it('requires review before making a resume request and rejects malformed results', async () => {
  const fetchMock = vi.fn().mockResolvedValue(Response.json({ items: [{ ...item, status: 'invented' }] }));
  vi.stubGlobal('fetch', fetchMock);
  await expect(api.resumeSessionInputs('a', false)).rejects.toThrow(i18n.t('api_errors.review_confirmation_required'));
  expect(fetchMock).not.toHaveBeenCalled();
  await expect(api.resumeSessionInputs('a', true)).rejects.toThrow(i18n.t('api_errors.resume_input_item_invalid'));
});

it('sends only the text input contract and reads the snapshot', async () => {
  const fetchMock = vi.fn().mockResolvedValueOnce(Response.json(item)).mockResolvedValueOnce(Response.json({ items: [item] }));
  vi.stubGlobal('fetch', fetchMock);
  expect(await api.submitSessionInput('session/a', { client_request_id: 'request-1', kind: 'steering', message: 'correction' })).toEqual(item);
  expect(fetchMock).toHaveBeenNthCalledWith(1, '/api/v1/sessions/session%2Fa/inputs', expect.objectContaining({
    method: 'POST', body: JSON.stringify({ client_request_id: 'request-1', kind: 'steering', message: 'correction' }), signal: expect.any(AbortSignal),
  }));
  expect(await api.getSessionInputs('session/a')).toEqual([item]);
});

it('rejects malformed confirmations instead of displaying queued success', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(Response.json({ ...item, status: 'invented' })));
  await expect(api.submitSessionInput('a', { client_request_id: 'request-1', kind: 'steering', message: 'correction' })).rejects.toThrow(i18n.t('api_errors.input_ack_invalid'));
});

it('reports an incomplete stream when turn_done arrives without overall done', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('event: turn_done\ndata: {}\n\n')));
  const events: ChatStreamEvent[] = [];
  await new Promise<void>(resolve => {
    api.chatStream('a', 'first', event => { events.push(event); if (event.type === 'error') resolve(); });
  });
  expect(events.map(event => event.type)).toEqual(['turn_done', 'error']);
});

it('sends structured attachments without the mutually exclusive images field', async () => {
  const fetchMock = vi.fn().mockResolvedValue(new Response('event: done\ndata: {}\n\n'));
  vi.stubGlobal('fetch', fetchMock);
  const file = { kind: 'image' as const, data: 'data:image/png;base64,a', name: 'image.png', mime_type: 'image/png', size: 1 };
  await new Promise<void>(resolve => api.chatStream('a', 'image task', event => { if (event.type === 'done') resolve(); }, { attachments: [file.data], files: [file] }));
  expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual({ message: 'image task', attachments: [file] });
});
