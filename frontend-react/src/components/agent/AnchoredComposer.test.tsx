// Spec update: composer permission/skills/attachment copy now comes from i18n
// (`anchored.composer.*`), so assertions read the English default locale instead
// of hardcoded Chinese strings (R12-H07/R12-H08 mixed-language fix).
import { act, cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { resetAnchoredStore, useAnchoredStore } from '../../store/anchored';
import { AnchoredComposer } from './AnchoredComposer';

// Stub only HTTP responses; exercise the real controls and API request paths.
const fetchResponse = vi.fn<typeof fetch>();
const onSend = vi.fn();
const onStop = vi.fn();

beforeEach(() => {
  vi.clearAllMocks();
  localStorage.clear();
  resetAnchoredStore();
  vi.stubGlobal('fetch', fetchResponse);
  fetchResponse.mockImplementation(async (input) => {
    const url = String(input);
    if (url.endsWith('/chat-commands')) return Response.json({ commands: [] });
    if (url.endsWith('/models')) {
      return Response.json([{ provider: 'test-provider', model_id: 'next-model', label: 'Next model' }]);
    }
    if (url.endsWith('/slash')) {
      return new Response('event: done\ndata: {"type":"done","payload":{"provider":"test-provider","model_id":"next-model"}}\n\n', {
        headers: { 'Content-Type': 'text/event-stream' },
      });
    }
    if (url.endsWith('/reasoning-level')) return Response.json({ session_id: 'session-1', level: 'medium' });
    if (url.endsWith('/permissions/config')) return Response.json({ mode: 'default' });
    if (url.includes('/permissions/')) return Response.json({ ok: true });
    if (url.endsWith('/skills')) return Response.json([{ id: 'skill-1', name: 'Review', is_enabled: false }, { id: 'unknown', name: 'Unknown' }]);
    if (url.endsWith('/skills/skill-1/enable')) return Response.json({ ok: true, is_enabled: true });
    if (url.includes('/sessions/')) {
      return Response.json({ id: 'session-1', provider: 'test-provider', model_id: 'current-model' });
    }
    throw new Error(`Unexpected request: ${url}`);
  });
});

it('restores text across keyed session mounts without leaking a draft to another session', () => {
  const view = render(<AnchoredComposer key="A" sessionId="A" isStreaming={false} onSend={onSend} onStop={onStop} />);
  fireEvent.change(screen.getByRole('textbox'), { target: { value: 'draft A' } });
  view.rerender(<AnchoredComposer key="B" sessionId="B" isStreaming={false} onSend={onSend} onStop={onStop} />);
  expect(screen.getByRole('textbox')).toHaveValue('');
  fireEvent.change(screen.getByRole('textbox'), { target: { value: 'draft B' } });
  view.rerender(<AnchoredComposer key="A" sessionId="A" isStreaming={false} onSend={onSend} onStop={onStop} />);
  expect(screen.getByRole('textbox')).toHaveValue('draft A');
});

function controlledReaders() {
  const readers: Array<{ result: string; onload: (() => void) | null; onerror: (() => void) | null }> = [];
  vi.stubGlobal('FileReader', class {
    result = 'data:text/plain;base64,bm90ZXM=';
    onload: (() => void) | null = null;
    onerror: (() => void) | null = null;
    readAsDataURL() { readers.push(this); }
  });
  return readers;
}

it('blocks ordinary submit while reading, reports failures and allows removal', async () => {
  const readers = controlledReaders();
  const { container } = render(composer());
  await loadedControls();
  fireEvent.change(screen.getByRole('textbox'), { target: { value: 'draft' } });
  fireEvent.change(container.querySelector('input[type="file"].hidden')!, { target: { files: [new File(['notes'], 'notes.txt', { type: 'text/plain' })] } });
  expect(screen.getByRole('button', { name: /发送|Send/i })).toBeDisabled();
  fireEvent.keyDown(screen.getByRole('textbox'), { key: 'Enter' });
  expect(onSend).not.toHaveBeenCalled();
  await act(async () => readers[0].onerror?.());
  expect(screen.getByText('Attachment failed to load. Remove it and pick again.')).toBeInTheDocument();
  expect(screen.getByRole('textbox')).toHaveValue('draft');
  fireEvent.click(screen.getByRole('button', { name: 'Remove notes.txt' }));
  expect(screen.getByRole('button', { name: /发送|Send/i })).toBeEnabled();
});

it('ignores an old read after leaving and returning to the same session', async () => {
  const readers = controlledReaders();
  const view = render(composer());
  await loadedControls();
  fireEvent.change(screen.getByTestId('image-attachment-input'), { target: { files: [new File(['old'], 'old.txt', { type: 'text/plain' })] } });
  view.rerender(composer(false, 'session-2'));
  view.rerender(composer());
  fireEvent.change(screen.getByTestId('image-attachment-input'), { target: { files: [new File(['new'], 'new.txt', { type: 'text/plain' })] } });
  await act(async () => readers[0].onload?.());
  expect(screen.getByTestId('image-preview-chip')).toHaveTextContent('new.txt');
  expect(screen.getByTestId('image-preview-chip')).toHaveAttribute('data-status', 'reading');
  await act(async () => readers[1].onload?.());
  expect(screen.getByTestId('image-preview-chip')).toHaveAttribute('data-status', 'ready');
});

it('does not resurrect removed attachments when a late read completes', async () => {
  const readers = controlledReaders();
  render(composer());
  await loadedControls();
  fireEvent.change(screen.getByTestId('image-attachment-input'), { target: { files: [new File(['old'], 'old.txt', { type: 'text/plain' })] } });
  fireEvent.click(screen.getByRole('button', { name: 'Remove old.txt' }));
  await act(async () => readers[0].onload?.());
  expect(screen.queryByTestId('image-preview-chip')).toBeNull();
});

it('keeps text and attachments when the ordinary send callback throws', async () => {
  const view = render(composer());
  await loadedControls();
  fireEvent.change(screen.getByTestId('image-attachment-input'), { target: { files: [new File(['notes'], 'notes.txt', { type: 'text/plain' })] } });
  await waitFor(() => expect(screen.getByTestId('image-preview-chip')).toHaveAttribute('data-status', 'ready'));
  onSend.mockImplementationOnce(() => { throw new Error('local callback failed'); });
  fireEvent.change(screen.getByRole('textbox'), { target: { value: 'preserved' } });
  fireEvent.keyDown(screen.getByRole('textbox'), { key: 'Enter' });
  expect(screen.getByRole('alert')).toHaveTextContent('local callback failed');
  expect(screen.getByRole('textbox')).toHaveValue('preserved');
  expect(screen.getByTestId('image-preview-chip')).toHaveAttribute('data-status', 'ready');
  view.rerender(composer(false, 'session-2'));
  expect(screen.queryByRole('button', { name: '恢复上次发送草稿' })).toBeNull();
  view.rerender(composer());
  expect(screen.getByRole('textbox')).toHaveValue('preserved');
  await loadedControls();
});

it('reports size rejection from the shared attachment bar and ignores completion after unmount', async () => {
  const readers = controlledReaders();
  const view = render(composer());
  await loadedControls();
  const oversized = new File(['x'], 'huge.txt', { type: 'text/plain' });
  Object.defineProperty(oversized, 'size', { value: 6 * 1024 * 1024 });
  fireEvent.change(screen.getByTestId('image-attachment-input'), { target: { files: [oversized] } });
  expect(screen.getByRole('alert')).toHaveTextContent('larger than 5.0 MB');
  fireEvent.change(screen.getByTestId('image-attachment-input'), { target: { files: [new File(['notes'], 'notes.txt', { type: 'text/plain' })] } });
  view.unmount();
  render(composer());
  await act(async () => readers[0].onload?.());
  expect(screen.queryByTestId('image-preview-chip')).toBeNull();
});

it.each(['picker', 'bar', 'paste'])('ignores late attachment reads after session switching through %s', async (entry) => {
  const readers = controlledReaders();
  const { container, rerender } = render(composer());
  await loadedControls();
  const files = [new File(['one'], 'one.txt', { type: 'text/plain' }), new File(['two'], 'two.txt', { type: 'text/plain' })];
  if (entry === 'paste') fireEvent.paste(document, { clipboardData: { files } });
  else fireEvent.change(entry === 'bar' ? screen.getByTestId('image-attachment-input') : container.querySelector('input[type="file"].hidden')!, { target: { files } });
  rerender(composer(false, 'session-2'));
  fireEvent.change(screen.getByRole('textbox'), { target: { value: 'B draft' } });
  await act(async () => { for (const reader of readers) reader.onload?.(); });
  expect(screen.queryByTestId('image-preview-chip')).toBeNull();
  expect(screen.getByRole('textbox')).toHaveValue('B draft');
  expect(readers).toHaveLength(entry === 'picker' ? 1 : 2);
});

it('retains a recoverable ordinary-send snapshot without persisting attachment data or replacing new text', async () => {
  const { container } = render(composer());
  await loadedControls();
  fireEvent.change(container.querySelector('input[type="file"].hidden')!, { target: { files: [new File(['notes'], 'notes.txt', { type: 'text/plain' })] } });
  await waitFor(() => expect(screen.getByTestId('image-preview-chip')).toHaveAttribute('data-status', 'ready'));
  const textbox = screen.getByRole('textbox');
  fireEvent.change(textbox, { target: { value: ' original draft ' } });
  fireEvent.keyDown(textbox, { key: 'Enter' });
  const restore = screen.getByRole('button', { name: '恢复上次发送草稿' });
  fireEvent.change(textbox, { target: { value: 'new text' } });
  expect(restore).toBeDisabled();
  fireEvent.click(restore);
  expect(textbox).toHaveValue('new text');
  fireEvent.change(textbox, { target: { value: '' } });
  fireEvent.click(restore);
  expect(textbox).toHaveValue(' original draft ');
  expect(screen.getByTestId('image-preview-chip')).toHaveAttribute('data-status', 'ready');
  expect(onSend).toHaveBeenCalledOnce();
  const stored = Array.from({ length: localStorage.length }, (_, i) => localStorage.getItem(localStorage.key(i)!)).join('');
  expect(stored).not.toContain('data:');
});

it('reports rejected files and enforces the limit across a multi-file picker batch', async () => {
  const readers = controlledReaders();
  const { container } = render(composer());
  await loadedControls();
  const picker = container.querySelector('input[type="file"].hidden')!;
  fireEvent.change(picker, { target: { files: [new File(['x'], 'bad.exe', { type: 'application/octet-stream' })] } });
  expect(screen.getByRole('alert')).toHaveTextContent('Unsupported attachment type');
  const files = Array.from({ length: 5 }, (_, i) => new File(['x'], `${i}.txt`, { type: 'text/plain' }));
  fireEvent.change(picker, { target: { files } });
  for (let i = 0; i < 4; i++) await act(async () => readers[i].onload?.());
  expect(readers).toHaveLength(4);
  expect(screen.getAllByTestId('image-preview-chip')).toHaveLength(4);
  expect(screen.getByRole('alert')).toHaveTextContent('At most 4 attachments');
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  resetAnchoredStore();
});

function composer(isStreaming = false, sessionId: string | null = 'session-1') {
  return <AnchoredComposer sessionId={sessionId} isStreaming={isStreaming} onSend={onSend} onStop={onStop} />;
}

async function loadedControls() {
  const model = await screen.findByRole('button', { name: 'test-provider:current-model' });
  const thinking = screen.getByRole('group', { name: /思考等级|Thinking/i });
  await waitFor(() => expect(within(thinking).getAllByRole('button')[1]).toHaveAttribute('aria-pressed', 'true'));
  return { model, thinking };
}

it('shows compact controls directly and uses the existing model and thinking API paths', async () => {
  render(composer());
  const { model, thinking } = await loadedControls();
  expect(model).toHaveClass('h-7');
  expect(screen.getByTestId('anchored-composer')).toContainElement(thinking);
  fireEvent.click(model);
  fireEvent.click(await screen.findByRole('option', { name: 'Next model' }));
  await screen.findByRole('button', { name: 'test-provider:next-model' });
  expect(fetchResponse).toHaveBeenCalledWith('/api/v1/sessions/session-1/slash', expect.objectContaining({
    method: 'POST',
    body: JSON.stringify({ message: '/model test-provider:next-model' }),
  }));
  fireEvent.click(within(thinking).getAllByRole('button')[2]);
  await waitFor(() => expect(fetchResponse).toHaveBeenCalledWith(
    '/api/v1/reasoning/sessions/session-1/reasoning-level',
    expect.objectContaining({ method: 'PUT', body: JSON.stringify({ level: 'high' }) }),
  ));
});

it('disables both controls during a run and retains their session state after stopping', async () => {
  const { rerender } = render(composer());
  const { model, thinking } = await loadedControls();
  rerender(composer(true));
  expect(model).toBeDisabled();
  for (const button of within(thinking).getAllByRole('button')) expect(button).toBeDisabled();
  const requestCount = fetchResponse.mock.calls.length;
  const user = userEvent.setup();
  await user.click(model);
  await user.click(within(thinking).getAllByRole('button')[2]);
  expect(fetchResponse).toHaveBeenCalledTimes(requestCount);
  expect(screen.queryByRole('listbox')).toBeNull();
  expect(screen.getByRole('textbox')).toBeEnabled();
  fireEvent.click(screen.getByRole('button', { name: /停止|Stop/i }));
  expect(onStop).toHaveBeenCalledOnce();
  rerender(composer());
  expect(model).toBeEnabled();
  expect(model).toHaveTextContent('test-provider:current-model');
  expect(within(thinking).getAllByRole('button')[1]).toHaveAttribute('aria-pressed', 'true');
  for (const button of within(thinking).getAllByRole('button')) expect(button).toBeEnabled();
  expect(fetchResponse.mock.calls.filter(([url]) => String(url).endsWith('/sessions/session-1'))).toHaveLength(1);
});

it('keeps model and thinking controls disabled without a session', () => {
  render(composer(false, null));
  expect(screen.getByRole('button', { name: /^(模型|Model)$/i })).toBeDisabled();
  const thinking = screen.getByRole('group', { name: /思考等级|Thinking/i });
  for (const button of within(thinking).getAllByRole('button')) expect(button).toBeDisabled();
  expect(fetchResponse.mock.calls.some(([url]) => String(url).includes('/sessions/'))).toBe(false);
});

it('uses a filled-block composer surface with the Codex prompt glyph and visible model and thinking controls', async () => {
  render(composer());
  const { model, thinking } = await loadedControls();
  const surface = screen.getByTestId('anchored-composer-surface');
  expect(screen.getByTestId('anchored-composer')).toHaveClass('mx-auto', 'max-w-[832px]');
  expect(surface).toHaveClass('rounded-[var(--radius-xl)]', 'bg-[var(--color-bg-surface-2)]');
  expect(surface.className).not.toMatch(/\bborder\b/);
  const prompt = screen.getByTestId('anchored-composer-prompt');
  expect(prompt).toHaveTextContent('›');
  expect(prompt).toHaveClass('font-bold');
  expect(prompt.compareDocumentPosition(screen.getByRole('textbox')) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  expect(surface).toContainElement(model);
  expect(surface).toContainElement(thinking);
});

it('reads and writes real permissions and prevents duplicate writes until acknowledgement', async () => {
  render(composer());
  await loadedControls();
  await screen.findByRole('button', { name: 'Permission settings' });
  fireEvent.click(screen.getByRole('button', { name: 'Permission settings' }));
  const plan = await screen.findByRole('radio', { name: '计划' });
  let acknowledge!: (response: Response) => void;
  fetchResponse.mockImplementationOnce(() => new Promise(resolve => { acknowledge = resolve; }));
  fireEvent.click(plan);
  expect(plan).toBeDisabled();
  fireEvent.click(plan);
  expect(fetchResponse.mock.calls.filter(([, init]) => init?.method === 'PUT' && init.body === JSON.stringify({ mode: 'plan' }))).toHaveLength(1);
  expect(screen.getByRole('button', { name: 'Permission settings' })).toHaveTextContent('Waiting for confirmation');
  await act(async () => acknowledge(Response.json({ mode: 'plan' })));
  expect(plan).toHaveAttribute('aria-checked', 'true');
  expect(plan).toBeEnabled();
});

it('reports permission load failure and retries without fabricating a mode', async () => {
  const defaultResponse = fetchResponse.getMockImplementation()!;
  let failed = false;
  fetchResponse.mockImplementation(async (input, init) => {
    if (String(input).endsWith('/permissions/config') && !failed) {
      failed = true;
      return Response.json({ detail: 'permissions offline' }, { status: 503 });
    }
    return defaultResponse(input, init);
  });
  render(composer());
  fireEvent.click(screen.getByRole('button', { name: 'Permission settings' }));
  await screen.findByText(/permissions offline/);
  expect(screen.queryByRole('radiogroup')).toBeNull();
  fireEvent.click(screen.getByRole('button', { name: '重试读取' }));
  await screen.findByRole('radio', { name: '默认' });
});

it('opens the real skill catalog lazily and confirms switches with backend state', async () => {
  render(composer());
  await loadedControls();
  expect(fetchResponse.mock.calls.some(([url]) => String(url).endsWith('/skills'))).toBe(false);
  fireEvent.click(screen.getByRole('button', { name: 'Skills' }));
  const toggle = await screen.findByRole('switch', { name: 'Review' });
  expect(toggle).toHaveAttribute('aria-checked', 'false');
  expect(screen.queryByRole('switch', { name: 'Unknown' })).toBeNull();
  expect(screen.getByRole('link', { name: 'Open skills page' })).toHaveAttribute('href', '#skills');
  fireEvent.click(toggle);
  await waitFor(() => expect(toggle).toHaveAttribute('aria-checked', 'true'));
  expect(fetchResponse).toHaveBeenCalledWith('/api/v1/skills/skill-1/enable', expect.objectContaining({ method: 'POST' }));
});

it('retains reported skill state on failure, offers retry and locks configuration during streaming', async () => {
  const view = render(composer());
  await loadedControls();
  fireEvent.click(screen.getByRole('button', { name: 'Skills' }));
  const toggle = await screen.findByRole('switch', { name: 'Review' });
  fetchResponse.mockResolvedValueOnce(Response.json({ detail: 'update failed' }, { status: 503 }));
  fireEvent.click(toggle);
  await screen.findByRole('alert');
  expect(toggle).toHaveAttribute('aria-checked', 'false');
  fireEvent.click(screen.getByRole('button', { name: 'Reload' }));
  await screen.findByRole('switch', { name: 'Review' });
  expect(screen.queryByRole('alert')).toBeNull();
  view.rerender(composer(true));
  expect(screen.getByRole('switch', { name: 'Review' })).toBeDisabled();
  fireEvent.keyDown(screen.getByRole('switch', { name: 'Review' }), { key: 'Escape' });
  fireEvent.click(screen.getByRole('button', { name: 'Permission settings' }));
  for (const radio of await screen.findAllByRole('radio')) expect(radio).toBeDisabled();
});

it('preserves keyboard submission, multiline input and file attachments', async () => {
  const { container } = render(composer());
  await loadedControls();
  const textbox = screen.getByRole('textbox');
  fireEvent.change(textbox, { target: { value: 'plain message' } });
  fireEvent.keyDown(textbox, { key: 'Enter', shiftKey: true });
  expect(onSend).not.toHaveBeenCalled();
  fireEvent.keyDown(textbox, { key: 'Enter' });
  expect(onSend).toHaveBeenCalledWith('plain message');
  expect(textbox).toHaveValue('');
  const file = new File(['attachment contents'], 'notes.txt', { type: 'text/plain' });
  fireEvent.change(container.querySelector('input[type="file"].hidden')!, { target: { files: [file] } });
  await waitFor(() => expect(screen.getByTestId('image-preview-chip')).toHaveAttribute('data-status', 'ready'));
  fireEvent.change(textbox, { target: { value: 'with attachment' } });
  fireEvent.keyDown(textbox, { key: 'Enter' });
  await waitFor(() => expect(onSend).toHaveBeenLastCalledWith('with attachment', [], [expect.objectContaining({
    kind: 'file', name: 'notes.txt', mime_type: 'text/plain', size: file.size,
    data: expect.stringMatching(/^data:/),
  })]));
});

it('keeps approval actions usable above the input while configuration controls are disabled', async () => {
  useAnchoredStore.getState().pushPopup({
    kind: 'approval', title: 'Approve tool', payload: { toolCallId: 'tool-1' }, confirmLabel: 'Approve',
  });
  render(composer(true));
  await loadedControls();
  const popup = screen.getByRole('dialog', { name: 'Approve tool' });
  const approve = within(popup).getByRole('button', { name: 'Approve' });
  expect(approve).toBeEnabled();
  fireEvent.click(approve);
  await waitFor(() => expect(screen.queryByRole('dialog')).toBeNull());
  expect(fetchResponse).toHaveBeenCalledWith('/api/v1/permissions/resolve', expect.objectContaining({
    method: 'POST', body: JSON.stringify({ tool_call_id: 'tool-1', decision: 'allow' }),
  }));
});

function sendCommand(command: string) {
  const textbox = screen.getByRole('textbox');
  fireEvent.change(textbox, { target: { value: command } });
  fireEvent.click(screen.getByRole('button', { name: /发送|Send/i }));
}

it('shows the catalog and supports wrapping, completion, dismissal and IME without executing', async () => {
  render(composer());
  await loadedControls();
  const textbox = screen.getByRole('textbox');
  fireEvent.change(textbox, { target: { value: '/' } });
  const menu = screen.getByRole('listbox');
  const options = within(menu).getAllByRole('option');
  expect(options).toHaveLength(7);
  expect(options[0]).toHaveAttribute('aria-selected', 'true');
  fireEvent.keyDown(textbox, { key: 'ArrowUp' });
  expect(options[6]).toHaveAttribute('aria-selected', 'true');
  fireEvent.keyDown(textbox, { key: 'ArrowDown' });
  expect(options[0]).toHaveAttribute('aria-selected', 'true');
  fireEvent.compositionStart(textbox);
  fireEvent.keyDown(textbox, { key: 'Enter' });
  expect(textbox).toHaveValue('/');
  fireEvent.compositionEnd(textbox);
  fireEvent.keyDown(textbox, { key: 'Tab' });
  expect(textbox).toHaveValue('/clear ');
  expect(screen.queryByRole('listbox')).toBeNull();
  fireEvent.change(textbox, { target: { value: '/he' } });
  fireEvent.keyDown(textbox, { key: 'Enter' });
  expect(textbox).toHaveValue('/help ');
  expect(onSend).not.toHaveBeenCalled();
  expect(fetchResponse.mock.calls.some(([url]) => String(url).endsWith('/slash'))).toBe(false);
  fireEvent.change(textbox, { target: { value: '/' } });
  fireEvent.keyDown(textbox, { key: 'Escape' });
  expect(screen.queryByRole('listbox')).toBeNull();
  expect(textbox).toHaveValue('/');
});

it('renders bounded server text above the input and never forwards commands to chat', async () => {
  render(composer());
  await loadedControls();
  fetchResponse.mockResolvedValueOnce(new Response(`event: text\ndata: ${JSON.stringify({ content: 'x'.repeat(9000) + 'command output' })}\n\nevent: done\ndata: {}\n\n`));
  sendCommand('/help');
  const feedback = await screen.findByRole('status');
  await waitFor(() => expect(feedback).toHaveTextContent('命令响应已结束'));
  expect(feedback).toHaveTextContent('command output');
  expect(feedback.textContent!.length).toBeLessThan(8200);
  expect(feedback).toHaveClass('overflow-y-auto');
  expect(feedback.compareDocumentPosition(screen.getByRole('textbox')) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  expect(fetchResponse).toHaveBeenCalledWith('/api/v1/sessions/session-1/slash', expect.objectContaining({
    method: 'POST', body: JSON.stringify({ message: '/help' }), signal: expect.any(AbortSignal),
  }));
  expect(onSend).not.toHaveBeenCalled();
});

it.each([
  ['SSE error', () => new Response('event: error\ndata: {"error":"command rejected"}\n\nevent: done\ndata: {}\n\n'), 'command rejected'],
  ['HTTP error', () => Response.json({ detail: 'permission denied' }, { status: 403 }), 'permission denied'],
  ['truncated stream', () => new Response('event: text\ndata: {"content":"partial"}\n\n'), 'without a completion event'],
  ['empty response', () => new Response(null), 'empty response body'],
])('reports %s with retry and preserves error after done', async (_name, response, message) => {
  render(composer());
  await loadedControls();
  fetchResponse.mockResolvedValueOnce(response());
  sendCommand('/status');
  const feedback = await screen.findByRole('alert');
  expect(feedback).toHaveTextContent(message);
  expect(feedback).toHaveTextContent('命令错误');
  fireEvent.click(within(feedback).getByRole('button', { name: '重试' }));
  await waitFor(() => expect(screen.getByRole('status')).toHaveTextContent('命令响应已结束'));
  expect(onSend).not.toHaveBeenCalled();
});

it('identifies streaming command feedback without claiming a chat run', async () => {
  render(composer());
  await loadedControls();
  sendCommand('/retry');
  await waitFor(() => expect(screen.getByRole('status')).toHaveTextContent('命令响应已结束'));
  expect(screen.getByRole('status')).toHaveTextContent('完整运行详情尚未接入聊天消息流');
  expect(onSend).not.toHaveBeenCalled();
  expect(onStop).not.toHaveBeenCalled();
});

it.each(['session', 'unmount', 'dismiss'] as const)('aborts slash reception on %s and ignores late frames', async (action) => {
  const { rerender, unmount } = render(composer());
  await loadedControls();
  let finish!: (response: Response) => void;
  fetchResponse.mockImplementationOnce(() => new Promise((resolve) => { finish = resolve; }));
  sendCommand('/help');
  const request = fetchResponse.mock.calls.find(([url]) => String(url).endsWith('/slash'))!;
  const signal = request[1]!.signal!;
  expect(signal.aborted).toBe(false);
  expect(screen.getByRole('status')).toHaveTextContent('等待命令响应');
  if (action === 'session') rerender(composer(false, 'session-2'));
  if (action === 'unmount') unmount();
  if (action === 'dismiss') fireEvent.click(screen.getByRole('button', { name: '取消接收' }));
  expect(signal.aborted).toBe(true);
  finish(new Response('event: text\ndata: {"content":"stale response"}\n\nevent: done\ndata: {}\n\n'));
  await waitFor(() => expect(screen.queryByText(/stale response/)).toBeNull());
  expect(screen.queryByRole('status')).toBeNull();
});

it('reports missing sessions locally and preserves plain slash paths as chat input', () => {
  render(composer(false, null));
  sendCommand('/help');
  expect(screen.getByRole('alert')).toHaveTextContent('请先选择会话');
  expect(fetchResponse.mock.calls.some(([url]) => String(url).endsWith('/slash'))).toBe(false);
  sendCommand('/etc/hosts is a file');
  expect(onSend).toHaveBeenCalledWith('/etc/hosts is a file');
});

it('filters commands while streaming and keeps stop on the slash endpoint', async () => {
  render(composer(true));
  await loadedControls();
  const textbox = screen.getByRole('textbox');
  fireEvent.change(textbox, { target: { value: '/' } });
  expect(screen.getAllByRole('option')).toHaveLength(1);
  fireEvent.keyDown(textbox, { key: 'Tab' });
  expect(textbox).toHaveValue('/stop ');
  fireEvent.keyDown(textbox, { key: 'Enter' });
  await waitFor(() => expect(screen.getByRole('status')).toHaveTextContent('命令响应已结束'));
  expect(onSend).not.toHaveBeenCalled();
  expect(fetchResponse).toHaveBeenCalledWith('/api/v1/sessions/session-1/slash', expect.objectContaining({ body: JSON.stringify({ message: '/stop' }) }));
});

it('offers both running input actions, preserves draft on failure and reuses the request id', async () => {
  const sendInput = vi.fn().mockResolvedValueOnce(false).mockResolvedValueOnce(true);
  render(<AnchoredComposer sessionId="session-1" isStreaming onSend={onSend} onStop={onStop} onSubmitInput={sendInput} />);
  await loadedControls();
  const textbox = screen.getByRole('textbox');
  fireEvent.change(textbox, { target: { value: 'next task' } });
  fireEvent.click(screen.getByRole('button', { name: 'Follow up' }));
  await screen.findByRole('alert');
  expect(textbox).toHaveValue('next task');
  const requestId = sendInput.mock.calls[0][2];
  fireEvent.click(screen.getByRole('button', { name: 'Follow up' }));
  await waitFor(() => expect(textbox).toHaveValue(''));
  expect(sendInput).toHaveBeenLastCalledWith('next task', 'follow_up', requestId);
  fireEvent.change(textbox, { target: { value: 'correction' } });
  fireEvent.compositionStart(textbox);
  fireEvent.keyDown(textbox, { key: 'Enter' });
  expect(sendInput).toHaveBeenCalledTimes(2);
  fireEvent.compositionEnd(textbox);
  fireEvent.keyDown(textbox, { key: 'Enter', keyCode: 229 });
  expect(sendInput).toHaveBeenCalledTimes(2);
  fireEvent.keyDown(textbox, { key: 'Enter' });
  await waitFor(() => expect(sendInput).toHaveBeenCalledTimes(3));
  expect(sendInput.mock.calls[2].slice(0, 2)).toEqual(['correction', 'steering']);
  expect(onSend).not.toHaveBeenCalled();
});

it('shows pending confirmation and blocks attachments for both running actions', async () => {
  let confirm!: (confirmed: boolean) => void;
  const sendInput = vi.fn(() => new Promise<boolean>(resolve => { confirm = resolve; }));
  const { container } = render(<AnchoredComposer sessionId="session-1" isStreaming onSend={onSend} onStop={onStop} onSubmitInput={sendInput} />);
  await loadedControls();
  const textbox = screen.getByRole('textbox');
  fireEvent.change(textbox, { target: { value: 'correction' } });
  fireEvent.click(screen.getByRole('button', { name: 'Direction override' }));
  expect(screen.getByText('Waiting for confirmation')).toBeInTheDocument();
  expect(textbox).toHaveValue('correction');
  expect(screen.getByRole('button', { name: 'Follow up' })).toBeDisabled();
  confirm(true);
  await waitFor(() => expect(textbox).toHaveValue(''));
  fireEvent.change(container.querySelector('input[type="file"].hidden')!, { target: { files: [new File(['text'], 'note.txt', { type: 'text/plain' })] } });
  await waitFor(() => expect(screen.getByTestId('image-preview-chip')).toHaveAttribute('data-status', 'ready'));
  fireEvent.change(textbox, { target: { value: 'with file' } });
  expect(screen.getByRole('button', { name: 'Direction override' })).toBeDisabled();
  expect(screen.getByRole('button', { name: 'Follow up' })).toBeDisabled();
  fireEvent.keyDown(textbox, { key: 'Enter' });
  expect(sendInput).toHaveBeenCalledOnce();
});
