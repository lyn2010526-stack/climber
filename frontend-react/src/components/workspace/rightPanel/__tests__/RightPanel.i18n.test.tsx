import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';
import { act, cleanup, fireEvent, render, screen, within } from '@testing-library/react';
import i18n from '../../../../i18n/config';
import { useWorkspaceStore, type Session } from '../../../../store/workspace';
import { ControlBar } from '../../ControlBar';
import { RightPanel } from '../../RightPanel';
import { warmSectionChunks } from './warmSectionChunks';

vi.mock('../../../../api', () => ({
  api: {
    getClusterStatus: vi.fn().mockResolvedValue({ plan: [] }),
    listTraces: vi.fn().mockResolvedValue({ traces: [] }),
    listDocuments: vi.fn().mockResolvedValue([]),
    getSessionMessages: vi.fn().mockResolvedValue([]),
    getPermissionConfig: vi.fn().mockResolvedValue({ mode: 'sandbox' }),
  },
}));

const originalLanguage = i18n.language;

beforeAll(warmSectionChunks);

beforeEach(() => {
  // The panel remembers its arrangement per conversation, so each case starts
  // from a clean slate instead of inheriting the previous language's layout.
  localStorage.clear();
});

afterEach(async () => {
  cleanup();
  await i18n.changeLanguage(originalLanguage);
});

describe('right panel with production i18n', () => {
  it.each([
    { language: 'en', title: 'Run inspector', groups: ['Session', 'Execution', 'Reasoning', 'Changes & files', 'Tool activity'],
      trace: 'Trace', emptyTrace: 'No trace data', provider: 'Provider', status: 'Session status', paused: 'Paused',
      sandbox: 'Sandbox mode', isolation: 'File isolation', projectOnly: 'Project only', collapse: 'Collapse all',
      noSession: 'No session selected', hint: 'Select or create a session to see the run summary' },
    { language: 'zh-CN', title: '运行面板', groups: ['会话', '执行过程', '推理', '变更与文件', '工具活动'],
      trace: '链路', emptyTrace: '暂无追踪数据', provider: '提供商', status: '会话状态', paused: '已暂停',
      sandbox: '沙箱模式', isolation: '文件隔离', projectOnly: '仅项目内', collapse: '全部折叠',
      noSession: '未选择会话', hint: '选择或新建会话后显示运行摘要' },
  ])('renders translated content and data-backed status in $language', async (text) => {
    await i18n.changeLanguage(text.language);
    const session: Session = {
      id: 'i18n-session', title: 'Test run', status: 'paused', messages: [],
      activeSkills: [], activeTools: [], createdAt: 1,
      modelConfig: { provider: 'openai', modelId: 'test-model', temperature: 0.7, maxTokens: 4096 },
      tokenUsage: { used: 5000, limit: 10000 },
    };
    useWorkspaceStore.setState({
      sessions: [session], activeSessionId: session.id, rightPanelOpen: true, rightPanelTab: 'config',
    });
    const view = await act(async () => render(<><ControlBar /><RightPanel /></>));
    const panel = within(screen.getByRole('complementary', { name: text.title }));
    // The bar reveals the inspector; every group is reached inside it, so each
    // group label names exactly one control on screen.
    expect(screen.getAllByRole('button', { name: text.title })).toHaveLength(1);
    for (const group of text.groups) {
      expect(screen.getAllByRole('button', { name: group })).toHaveLength(1);
    }
    expect(await panel.findByText(text.provider)).toBeInTheDocument();
    expect(panel.queryByText(text.status)).not.toBeInTheDocument();
    expect(panel.getAllByText(text.paused)).toHaveLength(1);
    expect(panel.getAllByText('5000 / 10000')).toHaveLength(1);
    for (const claim of [text.sandbox, text.isolation, text.projectOnly]) {
      expect(panel.queryByText(claim)).not.toBeInTheDocument();
    }
    fireEvent.click(panel.getByRole('button', { name: text.groups[1] }));
    fireEvent.click(panel.getByRole('tab', { name: text.trace }));
    expect(await panel.findByText(text.emptyTrace)).toBeInTheDocument();
    fireEvent.click(panel.getByRole('button', { name: text.groups[1] }));
    expect(panel.getByRole('button', { name: text.groups[0] })).toHaveAttribute('aria-expanded', 'false');

    view.unmount();
    useWorkspaceStore.setState({ sessions: [], activeSessionId: null });
    await act(async () => { render(<><ControlBar /><RightPanel /></>); });
    expect(screen.getByText(text.noSession)).toBeInTheDocument();
    const activity = screen.getAllByRole('button', { name: text.groups[4] })[0];
    expect(activity).toBeDisabled();
    expect(activity).toHaveAttribute('title', text.hint);
  });
});
