import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import i18n from '../../i18n';
import { api } from '../../api';
import { MemoryArchivePanel } from './MemoryArchivePanel';

vi.mock('../../api', () => ({
  api: {
    getMemoryContextBundle: vi.fn(),
    listMemorySidecars: vi.fn(),
  },
}));

const bundle = {
  content: '## Archived Memory Context',
  injected_summaries: 2,
  memory_hits: 0,
  scopes: [
    { scope: 'reference', abstract: 'OAuth 2.0 protects the API surface.', overview: '' },
    { scope: 'memories', abstract: 'User prefers concise replies.', overview: 'Overview of stored preferences.' },
  ],
  hits: [],
};

beforeEach(async () => {
  vi.resetAllMocks();
  await i18n.changeLanguage('zh-CN');
  vi.mocked(api.getMemoryContextBundle).mockResolvedValue(bundle);
});

describe('MemoryArchivePanel — 记忆归档', () => {
  it('渲染 L0 摘要条目列表与隐私门槛文案', async () => {
    render(<MemoryArchivePanel />);
    const abstract = await screen.findByText('OAuth 2.0 protects the API surface.');
    expect(abstract).toBeInTheDocument();
    expect(screen.getByText('User prefers concise replies.')).toBeInTheDocument();
    expect(screen.getByText(/归档前不会上传任何内容/)).toBeInTheDocument();
    expect(screen.getAllByRole('button', { name: /reference|memories/ })).toHaveLength(2);
  });

  it('点击 scope 展开并按需加载 L2 明细', async () => {
    const user = userEvent.setup();
    vi.mocked(api.listMemorySidecars).mockResolvedValue({
      scope: 'reference',
      records: [
        { id: 'sc-1', level: 0, scope: 'reference', body: 'L0 abstract body', generated_by: 'rule', updated_at: '2026-01-01T00:00:00Z' },
        { id: 'sc-2', level: 1, scope: 'reference', body: 'L1 overview body', generated_by: 'llm', updated_at: null },
      ],
    });
    render(<MemoryArchivePanel />);
    await screen.findByText('OAuth 2.0 protects the API surface.');
    expect(api.listMemorySidecars).not.toHaveBeenCalled();
    await user.click(screen.getByRole('button', { name: /reference/ }));
    expect(api.listMemorySidecars).toHaveBeenCalledWith('reference');
    expect(await screen.findByText('L0 abstract body')).toBeInTheDocument();
    expect(screen.getByText('L1 overview body')).toBeInTheDocument();
    expect(screen.getByText('L0 摘要')).toBeInTheDocument();
    expect(screen.getByText('L1 概览')).toBeInTheDocument();
  });

  it('再次点击收起，明细缓存不重复请求', async () => {
    const user = userEvent.setup();
    vi.mocked(api.listMemorySidecars).mockResolvedValue({ scope: 'reference', records: [] });
    render(<MemoryArchivePanel />);
    await screen.findByText('OAuth 2.0 protects the API surface.');
    const trigger = screen.getByRole('button', { name: /reference/ });
    await user.click(trigger);
    expect(await screen.findByText('无明细记录')).toBeInTheDocument();
    await user.click(trigger);
    expect(screen.queryByText('无明细记录')).not.toBeInTheDocument();
    await user.click(trigger);
    expect(await screen.findByText('无明细记录')).toBeInTheDocument();
    expect(api.listMemorySidecars).toHaveBeenCalledTimes(1);
  });

  it('bundle 为空时显示空态与隐私文案', async () => {
    vi.mocked(api.getMemoryContextBundle).mockResolvedValue({
      content: '', injected_summaries: 0, memory_hits: 0, scopes: [], hits: [],
    });
    render(<MemoryArchivePanel />);
    expect(await screen.findByText('暂无已归档记忆')).toBeInTheDocument();
    expect(screen.getByText(/归档前不会上传任何内容/)).toBeInTheDocument();
  });

  it('请求失败时优雅降级为不可用文案', async () => {
    vi.mocked(api.getMemoryContextBundle).mockRejectedValue(new Error('down'));
    render(<MemoryArchivePanel />);
    expect(await screen.findByText('记忆归档暂不可用')).toBeInTheDocument();
  });

  it('L1 overview 与 L0 摘要同层呈现', async () => {
    const user = userEvent.setup();
    vi.mocked(api.listMemorySidecars).mockResolvedValue({ scope: 'memories', records: [] });
    render(<MemoryArchivePanel />);
    await screen.findByText('User prefers concise replies.');
    await user.click(screen.getByRole('button', { name: /memories/ }));
    await waitFor(() => expect(screen.getByText('Overview of stored preferences.')).toBeInTheDocument());
  });
});
