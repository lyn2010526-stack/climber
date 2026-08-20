import { beforeEach, describe, it, expect, vi } from 'vitest';
import { act, render, screen, waitFor } from '@testing-library/react';
import type { ApprovalListResponse } from '../../../api';
import { ChatInterface } from '../ChatInterface';

const apiMocks = vi.hoisted(() => ({
  listModels: vi.fn().mockResolvedValue([]),
  listPendingApprovals: vi.fn().mockResolvedValue({ requests: [], total: 0 }),
  resolvePermission: vi.fn().mockResolvedValue(undefined),
}));

vi.mock('../../../api', () => ({
  api: {
    listModels: apiMocks.listModels,
    submitFeedback: vi.fn().mockResolvedValue(undefined),
    listPendingApprovals: apiMocks.listPendingApprovals,
    resolvePermission: apiMocks.resolvePermission,
  },
}));

async function renderChatInterface(props: Partial<React.ComponentProps<typeof ChatInterface>> = {}) {
  let result: ReturnType<typeof render>;
  await act(async () => {
    result = render(
      <ChatInterface
        messages={[]}
        onSend={() => {}}
        isLoading={false}
        {...props}
      />,
    );
  });
  return result!;
}

describe('ChatInterface', () => {
  beforeEach(() => {
    apiMocks.listModels.mockResolvedValue([]);
    apiMocks.listPendingApprovals.mockResolvedValue({ requests: [], total: 0 });
    apiMocks.resolvePermission.mockResolvedValue(undefined);
  });

  it('renders without crashing with empty messages', async () => {
    await renderChatInterface({ onStop: () => {} });
    expect(screen.getByText('开始新的对话')).toBeDefined();
  });

  it('renders empty state description', async () => {
    await renderChatInterface({ onStop: () => {} });
    expect(screen.getByText('输入任何问题或任务，Climber 将为你自主执行。')).toBeDefined();
  });

  it('renders suggestions', async () => {
    await renderChatInterface({ onStop: () => {} });
    expect(screen.getByText('帮我分析代码')).toBeDefined();
  });

  it('renders reasoning, tool execution, and final answer together', async () => {
    await renderChatInterface({
      messages: [{
          id: 'assistant-1',
          role: 'assistant',
          content: '最终答案',
          reasoning: '分析过程',
          toolCalls: [{ id: 'tool-1', name: 'read_file', arguments: {}, result: 'ok', status: 'success' }],
      }],
    });

    expect(screen.getByText(/思考完成/)).toBeDefined();
    expect(screen.getByText('read_file')).toBeDefined();
    expect(screen.getByText('最终答案')).toBeDefined();
  });

  it('renders the new composer', async () => {
    await renderChatInterface();

    expect(screen.getByRole('textbox', { name: '消息输入框' })).toBeDefined();
    expect(screen.getByRole('button', { name: '添加附件' })).toBeDefined();
  });

  it('loads and displays pending approvals for the active session', async () => {
    apiMocks.listPendingApprovals.mockResolvedValueOnce({
      requests: [{
        id: 'approval-1',
        session_id: 'session-1',
        tool_name: 'write_file',
        arguments: { path: '/workspace/data/out.txt' },
        status: 'pending',
        created_at: '2026-08-19T10:00:00Z',
      }],
      total: 1,
    });

    await renderChatInterface({ sessionId: 'session-1', isLoading: true });

    await waitFor(() => {
      expect(apiMocks.listPendingApprovals).toHaveBeenCalledWith('session-1', expect.any(AbortSignal));
      expect(screen.getByRole('dialog', { name: '权限请求' })).toBeDefined();
      expect(screen.getByText('修改文件')).toBeDefined();
    });
  });

  it('ignores an old approval response after switching sessions', async () => {
    let resolveFirst: (value: ApprovalListResponse) => void = () => {};
    const firstResponse = new Promise(resolve => { resolveFirst = resolve; });
    apiMocks.listPendingApprovals
      .mockReturnValueOnce(firstResponse)
      .mockResolvedValueOnce({
        requests: [{
          id: 'approval-b',
          session_id: 'session-b',
          tool_name: 'network_request',
          arguments: { url: 'https://example.com' },
          status: 'pending',
          created_at: '2026-08-19T10:00:00Z',
        }],
        total: 1,
      });

    const view = await renderChatInterface({ sessionId: 'session-a' });
    view.rerender(
      <ChatInterface sessionId="session-b" messages={[]} onSend={() => {}} isLoading={false} />,
    );

    await screen.findByText('网络访问');
    await act(async () => {
      resolveFirst({
        requests: [{
          id: 'approval-a',
          session_id: 'session-a',
          tool_name: 'write_file',
          arguments: { path: 'old.txt' },
          status: 'pending',
          created_at: '2026-08-19T09:00:00Z',
        }],
        total: 1,
      });
    });

    expect(screen.queryByText('修改文件')).toBeNull();
    expect(screen.getByText('网络访问')).toBeDefined();
  });
});
