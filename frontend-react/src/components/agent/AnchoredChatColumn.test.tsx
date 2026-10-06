import { fireEvent, render, screen, within } from '@testing-library/react';
import { beforeEach, expect, it, vi } from 'vitest';
import i18n from '../../i18n';
import { useChat } from '../../useChat';
import { resetAnchoredStore } from '../../store/anchored';
import { AnchoredChatColumn } from './AnchoredChatColumn';

vi.mock('../../useChat', () => ({ useChat: vi.fn() }));
vi.mock('../../api', () => ({
  api: {
    getStats: vi.fn().mockResolvedValue({}),
    getPermissionConfig: vi.fn().mockResolvedValue({ mode: 'default' }),
    updatePermissionConfig: vi.fn(),
  },
}));
vi.mock('./AnchoredComposer', () => ({
  AnchoredComposer: () => <div data-testid="anchored-composer" />,
}));
vi.mock('./AnchoredMessageFlow', () => ({ AnchoredMessageFlow: () => null }));

const chat = {
  messages: [],
  isStreaming: false,
  error: null,
  sendMessage: vi.fn(),
  stopStreaming: vi.fn(),
  retry: vi.fn(),
  clear: vi.fn(),
  refresh: vi.fn(),
  isLoading: false,
  inputs: [],
  runtimeReport: null,
  submitInput: vi.fn(),
  retryInput: vi.fn(),
  resumeInputs: vi.fn(),
  resumePending: false,
  resumeFeedback: null,
  startInputs: vi.fn(),
} satisfies ReturnType<typeof useChat>;

beforeEach(async () => {
  vi.clearAllMocks();
  await i18n.changeLanguage('zh-CN');
  resetAnchoredStore();
  vi.mocked(useChat).mockReturnValue({ ...chat });
});

it('offers a separate idle queue start and hides it during streaming', () => {
  const input = { id: 'i', client_request_id: 'r', kind: 'follow_up' as const, message: 'next', status: 'queued' as const, sequence: 1 };
  vi.mocked(useChat).mockReturnValue({ ...chat, inputs: [input] });
  const { rerender } = render(<AnchoredChatColumn sessionId="a" />);
  fireEvent.click(screen.getByRole('button', { name: '启动排队任务' }));
  expect(chat.startInputs).toHaveBeenCalledTimes(1);
  expect(chat.sendMessage).not.toHaveBeenCalled();
  expect(chat.resumeInputs).not.toHaveBeenCalled();
  vi.mocked(useChat).mockReturnValue({ ...chat, inputs: [input], resumePending: true });
  rerender(<AnchoredChatColumn sessionId="a" />);
  expect(screen.getByRole('button', { name: '启动排队任务' })).toBeDisabled();
  vi.mocked(useChat).mockReturnValue({ ...chat, inputs: [input], isStreaming: true });
  rerender(<AnchoredChatColumn sessionId="a" />);
  expect(screen.queryByRole('button', { name: '启动排队任务' })).toBeNull();
});

it('requires explicit risk review and resets consent when the session changes', () => {
  const blocked = { id: 'i', client_request_id: 'r', kind: 'follow_up' as const, message: 'task', status: 'blocked' as const, sequence: 1, error: 'unknown effect' };
  vi.mocked(useChat).mockReturnValue({ ...chat, inputs: [blocked] });
  const { rerender } = render(<AnchoredChatColumn sessionId="a" />);
  const button = screen.getByRole('button', { name: '恢复安全项' });
  expect(button).toBeDisabled();
  expect(screen.getByRole('region', { name: '恢复审查' })).toHaveTextContent('副作用未知的项保留阻塞');
  fireEvent.click(screen.getByRole('checkbox'));
  expect(button).toBeEnabled();
  rerender(<AnchoredChatColumn sessionId="b" />);
  expect(screen.getByRole('checkbox')).not.toBeChecked();
  expect(button).toBeDisabled();
  fireEvent.click(screen.getByRole('checkbox'));
  fireEvent.click(button);
  expect(chat.resumeInputs).toHaveBeenCalledWith(true);
  expect(chat.sendMessage).not.toHaveBeenCalled();
});

it('shows pending and acknowledged queue-only recovery without claiming execution', () => {
  const blocked = { id: 'i', client_request_id: 'r', kind: 'follow_up' as const, message: 'task', status: 'blocked' as const, sequence: 1 };
  vi.mocked(useChat).mockReturnValue({ ...chat, inputs: [blocked], resumePending: true });
  const { rerender } = render(<AnchoredChatColumn sessionId="a" />);
  expect(screen.getByRole('button', { name: '等待恢复确认' })).toBeDisabled();
  expect(screen.getByRole('checkbox')).toBeDisabled();
  vi.mocked(useChat).mockReturnValue({ ...chat, resumeFeedback: '安全项已重新排队，执行器启动尚待确认' });
  rerender(<AnchoredChatColumn sessionId="a" />);
  expect(screen.getByText('安全项已重新排队，执行器启动尚待确认')).toBeVisible();
});

it('keeps the normal column free of error feedback and preserves fixed rails', () => {
  render(<AnchoredChatColumn sessionId="session-1" />);
  expect(screen.queryByRole('alert')).toBeNull();
  expect(screen.queryByRole('button', { name: /^(重试|Retry)$/ })).toBeNull();
  expect(screen.getByTestId('anchored-title-bar')).toHaveClass('h-12', 'shrink-0');
  expect(screen.getByTestId('anchored-status-rail')).toHaveClass('h-6', 'shrink-0');
});

it('shows the actual error above the composer and delegates retry to useChat', () => {
  const error = '模型服务暂时不可用\n请稍后重试';
  vi.mocked(useChat).mockReturnValue({ ...chat, error });
  render(<AnchoredChatColumn sessionId="session-1" />);
  const alert = screen.getByRole('alert');
  expect(alert.querySelector('p')?.textContent).toBe(error);
  expect(alert.nextElementSibling).toBe(screen.getByTestId('anchored-composer'));
  expect(screen.getByTestId('anchored-status-rail')).toHaveAttribute('data-agent-state', 'error');
  fireEvent.click(within(alert).getByRole('button', { name: /^(重试|Retry)$/ }));
  expect(chat.retry).toHaveBeenCalledTimes(1);
  expect(chat.retry).toHaveBeenCalledWith();
  expect(chat.sendMessage).not.toHaveBeenCalled();
});

it('disables repeated retry while streaming and removes feedback when the error clears', () => {
  vi.mocked(useChat).mockReturnValue({ ...chat, error: '连接中断' });
  const { rerender } = render(<AnchoredChatColumn sessionId="session-1" />);
  fireEvent.click(screen.getByRole('button', { name: /^(重试|Retry)$/ }));
  vi.mocked(useChat).mockReturnValue({ ...chat, error: '连接中断', isStreaming: true });
  rerender(<AnchoredChatColumn sessionId="session-1" />);
  const retry = screen.getByRole('button', { name: /^(重试|Retry)$/ });
  expect(retry).toBeDisabled();
  fireEvent.click(retry);
  fireEvent.click(retry);
  expect(chat.retry).toHaveBeenCalledTimes(1);
  vi.mocked(useChat).mockReturnValue({ ...chat, isStreaming: true });
  rerender(<AnchoredChatColumn sessionId="session-1" />);
  expect(screen.queryByRole('alert')).toBeNull();
  expect(screen.getByTestId('anchored-status-rail')).toHaveAttribute('data-agent-state', 'thinking');
});

it('disables retry without a session, matching the hook guard', () => {
  vi.mocked(useChat).mockReturnValue({ ...chat, error: '连接中断' });
  render(<AnchoredChatColumn sessionId={null} />);
  const retry = screen.getByRole('button', { name: /^(重试|Retry)$/ });
  expect(retry).toBeDisabled();
  fireEvent.click(retry);
  expect(chat.retry).not.toHaveBeenCalled();
});

it('keeps the queue collapsed and delegates uncertain submission retry with its identity', () => {
  const input = { id: 'input-1', client_request_id: 'request-1', kind: 'follow_up' as const, message: 'next task', status: 'unconfirmed' as const, sequence: 1, error: 'offline' };
  vi.mocked(useChat).mockReturnValue({ ...chat, isStreaming: true, inputs: [input] });
  const { container } = render(<AnchoredChatColumn sessionId="session-1" />);
  const queue = container.querySelector('details')!;
  expect(queue.open).toBe(false);
  expect(queue.querySelector('summary')).toHaveTextContent('输入队列 · 1 项待处理');
  fireEvent.click(screen.getByText('输入队列 · 1 项待处理'));
  expect(queue.open).toBe(true);
  fireEvent.click(screen.getByRole('button', { name: '重试确认' }));
  expect(chat.retryInput).toHaveBeenCalledWith(input);
});

it('renders only reported runtime values in four compact categories with collapsed details', () => {
  vi.mocked(useChat).mockReturnValue({ ...chat, runtimeReport: { completed: ['saved file', 'ran checks'], executing: ['reviewing'], queued: [], risks: null } });
  render(<AnchoredChatColumn sessionId="session-1" />);
  const report = screen.getByRole('region', { name: '运行报告' });
  expect(report.querySelectorAll('dt')).toHaveLength(4);
  expect(report).toHaveTextContent('已完成');
  expect(report).toHaveTextContent('执行中');
  expect(report).toHaveTextContent('已排队');
  expect(report).toHaveTextContent('风险');
  expect(report).toHaveTextContent('服务端报告为空');
  expect(report).toHaveTextContent('未上报');
  const reportDetails = report.querySelector('details')!;
  expect(reportDetails.open).toBe(false);
  fireEvent.click(within(report).getByText(/运行报告 ·/));
  expect(reportDetails.open).toBe(true);
  const details = report.querySelector('dd details')!;
  expect(details.open).toBe(false);
  fireEvent.click(within(report).getByText('saved file', { selector: 'summary' }));
  expect(details.open).toBe(true);
  expect(report).toHaveTextContent('ran checks');
});

it('starts the conversation from an example card through the composer send contract', () => {
  render(<AnchoredChatColumn sessionId="session-1" />);
  const welcome = screen.getByTestId('anchored-welcome');
  expect(within(welcome).getByRole('heading')).toBeVisible();
  const card = screen.getByTestId('chat-example-plan');
  fireEvent.click(card);
  expect(chat.sendMessage).toHaveBeenCalledWith(i18n.t('anchored.welcome.example_plan'));
  expect(chat.retry).not.toHaveBeenCalled();
});

it('disables the example cards without a session, matching the hook guard', () => {
  render(<AnchoredChatColumn sessionId={null} />);
  const card = screen.getByTestId('chat-example-plan');
  expect(card).toBeDisabled();
  fireEvent.click(card);
  expect(chat.sendMessage).not.toHaveBeenCalled();
});

it('centers the conversation at 800px and shows the actual tool status once in the title', () => {
  vi.mocked(useChat).mockReturnValue({ ...chat, isStreaming: true, messages: [{ id: 'assistant', role: 'assistant', content: '', timestamp: Date.now(), toolCalls: [{ id: 'tool', name: 'read_file', arguments: {}, status: 'running' }] }] });
  render(<AnchoredChatColumn sessionId="session-1" />);
  expect(screen.getByTestId('anchored-conversation')).toHaveClass('mx-auto', 'max-w-[800px]');
  const title = screen.getByTestId('anchored-title-bar');
  expect(screen.getByTestId('anchored-pipeline-stage')).toHaveTextContent(/执行工具|Running tool/);
  expect(within(title).queryByText(/思考中|Thinking/)).toBeNull();
});

it('keeps the runtime report absent until the backend reports it', () => {
  render(<AnchoredChatColumn sessionId="session-1" />);
  expect(screen.queryByRole('region', { name: '运行报告' })).toBeNull();
});

const viewLabel = (key: 'content_view.rendered' | 'content_view.raw', fallback: string) =>
  i18n.t(key, { defaultValue: fallback });

it('offers the raw payload of a reported run report and switches back to the rendered view', () => {
  vi.mocked(useChat).mockReturnValue({ ...chat, runtimeReport: { completed: ['saved file'], executing: ['reviewing'], queued: [], risks: ['stale index'] } });
  render(<AnchoredChatColumn sessionId="session-1" />);
  const report = screen.getByRole('region', { name: '运行报告' });
  const renderedTab = within(report).getByRole('tab', { name: viewLabel('content_view.rendered', 'Rendered') });
  const rawTab = within(report).getByRole('tab', { name: viewLabel('content_view.raw', 'Raw') });

  expect(renderedTab).toHaveAttribute('aria-selected', 'true');
  expect(within(report).getByText(/运行报告 ·/)).toBeVisible();
  expect(within(report).queryByTestId('raw-payload')).toBeNull();

  fireEvent.click(rawTab);
  expect(rawTab).toHaveAttribute('aria-selected', 'true');
  expect(within(report).getByTestId('raw-payload')).toHaveTextContent('"stale index"');
  expect(within(report).queryByText(/运行报告 ·/)).toBeNull();

  fireEvent.click(renderedTab);
  expect(within(report).getByText(/运行报告 ·/)).toBeVisible();
  expect(within(report).queryByTestId('raw-payload')).toBeNull();
});

it('keeps the run report plain when the backend reported no payload at all', () => {
  vi.mocked(useChat).mockReturnValue({ ...chat, runtimeReport: { completed: null, executing: null, queued: [], risks: null } });
  render(<AnchoredChatColumn sessionId="session-1" />);
  const report = screen.getByRole('region', { name: '运行报告' });
  expect(within(report).queryByRole('tab')).toBeNull();
  expect(within(report).queryByTestId('raw-payload')).toBeNull();
  expect(report).toHaveTextContent('未上报');
  expect(report).toHaveTextContent('服务端报告为空');
});

it('returns the run report to the rendered view when the session changes', () => {
  vi.mocked(useChat).mockReturnValue({ ...chat, runtimeReport: { completed: ['saved file'], executing: null, queued: null, risks: null } });
  const { rerender } = render(<AnchoredChatColumn sessionId="session-1" />);
  const report = screen.getByRole('region', { name: '运行报告' });
  fireEvent.click(within(report).getByRole('tab', { name: viewLabel('content_view.raw', 'Raw') }));
  expect(within(report).getByTestId('raw-payload')).toBeVisible();

  rerender(<AnchoredChatColumn sessionId="session-2" />);
  expect(within(screen.getByRole('region', { name: '运行报告' })).getByText(/运行报告 ·/)).toBeVisible();
  expect(screen.queryByTestId('raw-payload')).toBeNull();
});
