import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import i18n from '../i18n';
import { api } from '../api';
import { AuditLogPage } from './AuditLogPage';

vi.mock('../api', () => ({
  api: {
    listAuditLog: vi.fn(),
  },
}));

function entry(overrides: Partial<Record<string, unknown>> = {}) {
  return {
    id: 1,
    session_id: 'sess-1',
    user_id: 'user-1',
    action: 'agent:run',
    severity: 'info',
    details: null,
    result: 'completed',
    created_at: '2026-01-01T00:00:00Z',
    ...overrides,
  };
}

beforeEach(async () => {
  vi.resetAllMocks();
  await i18n.changeLanguage('zh-CN');
});

describe('AuditLogPage — 审计日志', () => {
  it('加载并渲染事件表格（时间/动作/严重度/会话/结果）', async () => {
    vi.mocked(api.listAuditLog).mockResolvedValue({
      entries: [
        entry(),
        entry({ id: 2, action: 'file:write', severity: 'critical', result: 'denied' }),
        entry({ id: 3, action: 'permission:check', severity: 'warning', result: null, session_id: null }),
      ],
      total: 3,
      limit: 20,
      offset: 0,
    } as any);
    render(<AuditLogPage />);
    expect(await screen.findByText('agent:run')).toBeInTheDocument();
    expect(screen.getByText('file:write')).toBeInTheDocument();
    expect(api.listAuditLog).toHaveBeenCalledWith({ limit: 20, offset: 0, action: undefined, severity: undefined });
    expect(screen.getByText('1-3 / 3')).toBeInTheDocument();
    expect(screen.getAllByText('sess-1')).toHaveLength(2);
    expect(screen.getByText('completed')).toBeInTheDocument();
  });

  it('severity 三档映射为对应徽标，未知值退回中性徽标', async () => {
    vi.mocked(api.listAuditLog).mockResolvedValue({
      entries: [
        entry({ id: 1, severity: 'info' }),
        entry({ id: 2, severity: 'warning' }),
        entry({ id: 3, severity: 'critical' }),
        entry({ id: 4, severity: 'weird' }),
      ],
      total: 4,
      limit: 20,
      offset: 0,
    } as any);
    render(<AuditLogPage />);
    await screen.findAllByText('agent:run');
    expect(screen.getAllByText('agent:run')).toHaveLength(4);
    const table = screen.getByRole('table');
    expect(within(table).getByText('info')).toBeInTheDocument();
    expect(within(table).getByText('warning')).toBeInTheDocument();
    expect(within(table).getByText('critical')).toBeInTheDocument();
    expect(within(table).getByText('weird')).toBeInTheDocument();
  });

  it('空数据显示空态', async () => {
    vi.mocked(api.listAuditLog).mockResolvedValue({ entries: [], total: 0, limit: 20, offset: 0 } as any);
    render(<AuditLogPage />);
    expect(await screen.findByText('暂无审计事件')).toBeInTheDocument();
  });

  it('请求失败时降级为错误条与重试', async () => {
    vi.mocked(api.listAuditLog).mockRejectedValueOnce(new Error('down'));
    vi.mocked(api.listAuditLog).mockResolvedValue({ entries: [entry()], total: 1, limit: 20, offset: 0 } as any);
    render(<AuditLogPage />);
    expect(await screen.findByText('审计日志加载失败')).toBeInTheDocument();
    expect(screen.getByText('无匹配条目')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '重试' }));
    expect(await screen.findByText('agent:run')).toBeInTheDocument();
    expect(api.listAuditLog).toHaveBeenCalledTimes(2);
  });

  it('提交动作过滤器时按 action 重新请求并回到第一页', async () => {
    vi.mocked(api.listAuditLog).mockResolvedValue({ entries: [entry()], total: 1, limit: 20, offset: 0 } as any);
    render(<AuditLogPage />);
    await screen.findByText('agent:run');
    fireEvent.change(screen.getByLabelText('按动作过滤，如 agent:run'), { target: { value: 'file:write' } });
    fireEvent.submit(screen.getByRole('button', { name: '应用' }).closest('form') as HTMLFormElement);
    await waitFor(() => {
      expect(api.listAuditLog).toHaveBeenLastCalledWith({ limit: 20, offset: 0, action: 'file:write', severity: undefined });
    });
  });

  it('切换严重度过滤器立即按 severity 请求', async () => {
    vi.mocked(api.listAuditLog).mockResolvedValue({ entries: [entry()], total: 1, limit: 20, offset: 0 } as any);
    render(<AuditLogPage />);
    await screen.findByText('agent:run');
    fireEvent.change(screen.getByLabelText('按严重度过滤'), { target: { value: 'critical' } });
    await waitFor(() => {
      expect(api.listAuditLog).toHaveBeenLastCalledWith({ limit: 20, offset: 0, action: undefined, severity: 'critical' });
    });
  });

  it('分页在前后页之间移动并禁用边界按钮', async () => {
    vi.mocked(api.listAuditLog).mockResolvedValue({
      entries: Array.from({ length: 20 }, (_, index) => entry({ id: index + 1 })),
      total: 25,
      limit: 20,
      offset: 0,
    } as any);
    render(<AuditLogPage />);
    expect(await screen.findByText('1-20 / 25')).toBeInTheDocument();
    const prev = screen.getByRole('button', { name: '上一页' });
    const next = screen.getByRole('button', { name: '下一页' });
    expect(prev).toBeDisabled();
    expect(next).toBeEnabled();
    fireEvent.click(next);
    await waitFor(() => {
      expect(api.listAuditLog).toHaveBeenLastCalledWith({ limit: 20, offset: 20, action: undefined, severity: undefined });
    });
    expect(await screen.findByText('21-40 / 25')).toBeInTheDocument();
  });
});
