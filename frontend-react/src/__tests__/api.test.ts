import { afterEach, describe, expect, it, vi } from 'vitest';

import { api } from '../api';

describe('ApiClient paginated lists', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    localStorage.clear();
  });

  it('returns agent items from the paginated response', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        items: [{ id: 'agent-1', name: 'Planner' }],
        total: 1,
        limit: 50,
        offset: 0,
      }),
    }));

    await expect(api.listAgents()).resolves.toEqual([
      { id: 'agent-1', name: 'Planner' },
    ]);
  });

  it('returns session items from the paginated response', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        items: [{ id: 'session-1', title: 'Investigation', status: 'idle' }],
        total: 1,
        limit: 50,
        offset: 0,
      }),
    }));

    await expect(api.listSessions()).resolves.toEqual([
      { id: 'session-1', title: 'Investigation', status: 'idle' },
    ]);
  });

  it('sends the stored bearer token with API requests', async () => {
    localStorage.setItem('auth_token', 'signed-token');
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ items: [], total: 0, limit: 50, offset: 0 }),
    });
    vi.stubGlobal('fetch', fetchMock);

    await api.listAgents();

    expect(fetchMock).toHaveBeenCalledWith('/api/v1/agents', expect.objectContaining({
      headers: expect.objectContaining({ Authorization: 'Bearer signed-token' }),
    }));
  });

  it('sends the stored bearer token with chat streams', () => {
    localStorage.setItem('auth_token', 'signed-token');
    const fetchMock = vi.fn().mockReturnValue(new Promise(() => {}));
    vi.stubGlobal('fetch', fetchMock);

    const cancel = api.chatStream('session-1', 'hello', vi.fn());

    expect(fetchMock).toHaveBeenCalledWith(
      '/api/v1/sessions/session-1/chat',
      expect.objectContaining({
        headers: expect.objectContaining({ Authorization: 'Bearer signed-token' }),
      }),
    );
    cancel();
  });

  it('uploads attachments as multipart form data', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        id: 'upl-1',
        name: 'diagram.png',
        content_type: 'image/png',
        size: 4,
        kind: 'image',
      }),
    });
    vi.stubGlobal('fetch', fetchMock);

    const file = new File(['test'], 'diagram.png', { type: 'image/png' });
    await expect(api.uploadAttachment(file)).resolves.toEqual({
      id: 'upl-1',
      name: 'diagram.png',
      content_type: 'image/png',
      size: 4,
      kind: 'image',
    });

    expect(fetchMock).toHaveBeenCalledWith('/api/v1/uploads', expect.objectContaining({
      method: 'POST',
      body: expect.any(FormData),
    }));
  });

  it('throws when an upload fails', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: false,
      status: 413,
      statusText: 'Payload Too Large',
      json: async () => ({ detail: 'File exceeds the 20MB limit' }),
    }));

    const file = new File(['test'], 'big.bin', { type: 'application/octet-stream' });
    await expect(api.uploadAttachment(file)).rejects.toThrow('File exceeds the 20MB limit');
  });

  it('sends attachment references with chat messages', () => {
    const fetchMock = vi.fn().mockReturnValue(new Promise(() => {}));
    vi.stubGlobal('fetch', fetchMock);

    const attachments = [{
      id: 'upl-1',
      name: 'diagram.png',
      content_type: 'image/png',
      size: 4,
      kind: 'image' as const,
    }];
    const cancel = api.chatStream('session-1', 'look', vi.fn(), attachments);

    const body = JSON.parse(fetchMock.mock.calls[0]?.[1]?.body as string);
    expect(body).toEqual({ message: 'look', attachments });
    cancel();
  });
});

describe('ApiClient chat streams', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    localStorage.clear();
  });

  const responseWithReads = (...reads: Array<{ done: boolean; value?: Uint8Array }>) => ({
    ok: true,
    body: {
      getReader: () => ({ read: vi.fn()
        .mockResolvedValueOnce(reads[0])
        .mockResolvedValueOnce(reads[1])
        .mockResolvedValueOnce(reads[2])
        .mockResolvedValueOnce(reads[3])
        .mockResolvedValueOnce(reads[4]) }),
    },
  });

  const sse = (payload: string) => new TextEncoder().encode(payload);

  it('emits an error when text is followed by EOF without a terminal event', async () => {
    const onEvent = vi.fn();
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(responseWithReads(
      { done: false, value: sse('event: text\ndata: "hello"\n\n') },
      { done: true },
    )));

    api.chatStream('session-1', 'hello', onEvent);
    await vi.waitFor(() => expect(onEvent).toHaveBeenCalledTimes(2));

    expect(onEvent).toHaveBeenNthCalledWith(1, { event: 'text', data: 'hello' });
    expect(onEvent).toHaveBeenNthCalledWith(2, {
      event: 'error',
      data: { detail: 'Chat stream ended before a terminal event was received' },
    });
  });

  it('does not emit an EOF error after a done event', async () => {
    const onEvent = vi.fn();
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(responseWithReads(
      { done: false, value: sse('event: done\ndata: {}\n\n') },
      { done: true },
    )));

    api.chatStream('session-1', 'hello', onEvent);
    await vi.waitFor(() => expect(onEvent).toHaveBeenCalledTimes(1));

    expect(onEvent).toHaveBeenCalledWith({ event: 'done', data: {} });
  });

  it('emits a single error when reading the stream fails', async () => {
    const onEvent = vi.fn();
    const read = vi.fn().mockRejectedValue(new Error('read failed'));
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true,
      body: { getReader: () => ({ read }) },
    }));

    api.chatStream('session-1', 'hello', onEvent);
    await vi.waitFor(() => expect(onEvent).toHaveBeenCalledTimes(1));

    expect(onEvent).toHaveBeenCalledWith({
      event: 'error',
      data: JSON.stringify({ detail: 'read failed' }),
    });
  });

  it('keeps AbortError silent', async () => {
    const onEvent = vi.fn();
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(Object.assign(new Error('aborted'), {
      name: 'AbortError',
    })));

    api.chatStream('session-1', 'hello', onEvent);
    await Promise.resolve();
    await Promise.resolve();

    expect(onEvent).not.toHaveBeenCalled();
  });
});
