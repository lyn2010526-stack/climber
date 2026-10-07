import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { beforeEach, expect, it, vi } from 'vitest';
import i18n from '../../i18n';
import { api, ApiRequestError } from '../../api';
import { INFO_CARD_ORDER, METER_ORDER, resetAnchoredStore, useAnchoredStore, type MeterSnapshot } from '../../store/anchored';
import { AnchoredInfoPanel } from './AnchoredInfoPanel';

vi.mock('../../api', async original => ({
  ...await original<typeof import('../../api')>(),
  api: {
    getCostUsage: vi.fn().mockResolvedValue({}),
    listCostRecords: vi.fn().mockResolvedValue([]),
    getMemoryContextBundle: vi.fn().mockResolvedValue({ content: '', injected_summaries: 0, memory_hits: 0, scopes: [], hits: [] }),
    listMemorySidecars: vi.fn().mockResolvedValue({ scope: 'reference', records: [] }),
    getUiRules: vi.fn(),
    putUiRules: vi.fn(),
  },
}));
vi.mock('../anchored/TaskTracePanel', () => ({ TaskTracePanel: () => null }));
vi.mock('../anchored/ArtifactPreview', () => ({ ArtifactPreview: () => null }));

const documents = (['soul', 'memory', 'project'] as const).map(kind => ({ id: kind, kind, title: kind, scope: 'user' as const, content: `${kind} server`, revision: 'a'.repeat(64) }));
beforeEach(async () => {
  vi.clearAllMocks();
  await i18n.changeLanguage('zh-CN');
  resetAnchoredStore();
  useAnchoredStore.getState().setCardOpen('ruleEditor', true);
  vi.mocked(api.getUiRules).mockResolvedValue([...documents]);
});

/** 卡片折叠开关是标题内持有 aria-controls 的按钮，动作按钮排在它之后。 */
const cardToggle = (card: string) =>
  screen.getByTestId(`anchored-card-${card}`).querySelector<HTMLButtonElement>('h3 > button[aria-controls]')!;

it('loads on opening, preserves drafts between tabs and reports successful server save', async () => {
  render(<AnchoredInfoPanel />);
  const editor = within(screen.getByTestId('anchored-rule-editor'));
  await waitFor(() => expect(editor.getByRole('textbox')).toHaveValue('soul server'));
  fireEvent.change(editor.getByRole('textbox'), { target: { value: 'draft' } });
  const tabs = editor.getAllByRole('button').filter(button => button.hasAttribute('aria-pressed'));
  fireEvent.click(tabs[1]);
  expect(editor.getByRole('textbox')).toHaveValue('memory server');
  fireEvent.click(tabs[0]);
  expect(editor.getByRole('textbox')).toHaveValue('draft');
  vi.mocked(api.putUiRules).mockResolvedValue({ ...documents[0], content: 'draft', revision: 'b'.repeat(64) });
  fireEvent.click(screen.getByRole('button', { name: /保存|Save/ }));
  await waitFor(() => expect(editor.getByRole('status')).toHaveTextContent('已保存到账户规则'));
  expect(api.putUiRules).toHaveBeenCalledWith('soul', { content: 'draft', revision: 'a'.repeat(64) });
  expect(screen.getByRole('button', { name: /保存|Save/ })).toBeDisabled();
});

it('shows conflict and retains drafts through collapse and reload before explicit retry', async () => {
  render(<AnchoredInfoPanel />);
  await waitFor(() => expect(screen.getByRole('textbox')).toHaveValue('soul server'));
  fireEvent.change(screen.getByRole('textbox'), { target: { value: 'my draft' } });
  vi.mocked(api.putUiRules).mockRejectedValue(new ApiRequestError(409, 'Conflict', { detail: 'Rule changed' }));
  fireEvent.click(screen.getByRole('button', { name: /保存|Save/ }));
  expect(await screen.findByRole('alert')).toHaveTextContent('版本冲突');
  expect(screen.getByRole('button', { name: /保存|Save/ })).toBeDisabled();
  act(() => useAnchoredStore.getState().setCardOpen('ruleEditor', false));
  act(() => useAnchoredStore.getState().setCardOpen('ruleEditor', true));
  expect(screen.getByRole('textbox')).toHaveValue('my draft');
  vi.mocked(api.getUiRules).mockResolvedValue([{ ...documents[0], content: 'other edit', revision: 'c'.repeat(64) }, ...documents.slice(1)]);
  fireEvent.click(screen.getByRole('button', { name: '重新加载最新版本' }));
  await waitFor(() => expect(screen.queryByRole('alert')).toBeNull());
  expect(screen.getByRole('textbox')).toHaveValue('my draft');
  expect(screen.getByRole('button', { name: /保存|Save/ })).toBeEnabled();
  expect(api.putUiRules).toHaveBeenCalledTimes(1);
});

it('exposes load failures with a working retry and disabled editing', async () => {
  vi.mocked(api.getUiRules).mockRejectedValueOnce(new Error('offline'));
  render(<AnchoredInfoPanel />);
  expect(await screen.findByRole('alert')).toHaveTextContent('offline');
  expect(screen.getByRole('textbox')).toBeDisabled();
  fireEvent.click(screen.getByRole('button', { name: '重新加载规则' }));
  await waitFor(() => expect(screen.getByRole('textbox')).toBeEnabled());
  expect(screen.queryByRole('alert')).toBeNull();
});

it('renders all-zero usage trend with finite bar heights', async () => {
  render(<AnchoredInfoPanel />);
  await screen.findByDisplayValue('soul server');
  act(() => useAnchoredStore.getState().setMeter(useAnchoredStore.getState().meter, [{ input: 0, output: 0, total: 0, cacheSaved: null }]));
  const bar = screen.getByTestId('anchored-meter-trend').firstElementChild as HTMLElement;
  expect(bar.style.height).toBe('8%');
  expect(bar.title).toBe('0');
});

it('keeps five ordered compact sections and task and usage inspection collapsible', async () => {
  render(<AnchoredInfoPanel />);
  await screen.findByDisplayValue('soul server');
  const sections = INFO_CARD_ORDER.map(card => screen.getByTestId(`anchored-card-${card}`));
  expect(Array.from(screen.getByTestId('anchored-info-panel').querySelectorAll('[data-testid^="anchored-card-"]'))).toEqual(sections);
  for (const section of sections) {
    expect(within(section).getByRole('heading', { level: 3 })).toBeInTheDocument();
    expect(section).not.toHaveClass('workbench-info-card');
  }
  for (const card of ['taskBoard', 'tokenMeter']) {
    const button = cardToggle(card);
    expect(button).toHaveAttribute('aria-expanded', 'true');
    fireEvent.click(button);
    expect(button).toHaveAttribute('aria-expanded', 'false');
    expect(document.getElementById(button.getAttribute('aria-controls')!)).toBeNull();
    fireEvent.click(button);
    expect(button).toHaveAttribute('aria-expanded', 'true');
  }
});

it('keeps the continuous inspector card order per session', async () => {
  const { rerender } = render(<AnchoredInfoPanel sessionId="session-a" />);
  await screen.findByDisplayValue('soul server');
  const cards = () => Array.from(screen.getByTestId('anchored-info-panel').querySelectorAll('[data-testid^="anchored-card-"]')).map((card) => card.getAttribute('data-testid'));
  expect(cards()).toEqual(INFO_CARD_ORDER.map((card) => `anchored-card-${card}`));
  rerender(<AnchoredInfoPanel sessionId="session-b" />);
  expect(cards()).toEqual(INFO_CARD_ORDER.map((card) => `anchored-card-${card}`));
  rerender(<AnchoredInfoPanel sessionId="session-a" />);
  expect(cards()).toEqual(INFO_CARD_ORDER.map((card) => `anchored-card-${card}`));
});

it('renders the plan headers, default states and per-card actions with tokens', async () => {
  resetAnchoredStore();
  render(<AnchoredInfoPanel />);
  const openByDefault: Record<string, boolean> = {
    taskBoard: true, tokenMeter: true, subAgentTree: false, filePreview: false, ruleEditor: false, memoryArchive: false,
  };
  for (const card of INFO_CARD_ORDER) {
    expect(cardToggle(card)).toHaveAttribute('aria-expanded', String(openByDefault[card]));
  }
  // 任务看板：默认展开、三条泳道、头部新建任务动作。
  const board = screen.getByTestId('anchored-card-taskBoard');
  expect(within(board).getByRole('button', { name: '新建任务' })).toBeInTheDocument();
  for (const lane of ['pending', 'running', 'completed']) {
    expect(screen.getByTestId(`anchored-lane-${lane}`)).toBeInTheDocument();
  }
  // Token 仪表盘：两行三列六指标、头部重置动作。
  const meter = screen.getByTestId('anchored-card-tokenMeter');
  expect(within(meter).getByRole('button', { name: '重置' })).toBeInTheDocument();
  expect(meter.querySelectorAll('dd')).toHaveLength(METER_ORDER.length);
  // 子 Agent 树：默认折叠、头部全部展开动作。
  expect(within(screen.getByTestId('anchored-card-subAgentTree')).getByRole('button', { name: '全部展开' })).toBeInTheDocument();
  // 规则编辑器：默认折叠、头部保存动作。
  expect(within(screen.getByTestId('anchored-card-ruleEditor')).getByRole('button', { name: /保存|Save/ })).toBeInTheDocument();
});

it('registers a new task into the pending lane from the card header and moves it on drop', async () => {
  class MockDataTransfer {
    data: Record<string, string> = {};
    effectAllowed = 'none';
    setData(format: string, value: string) { this.data[format] = value; }
    getData(format: string) { return this.data[format] ?? ''; }
  }
  render(<AnchoredInfoPanel />);
  await screen.findByDisplayValue('soul server');
  fireEvent.click(screen.getByRole('button', { name: '新建任务' }));
  const task = useAnchoredStore.getState().tasks[0];
  expect(task.lane).toBe('pending');
  const card = screen.getByTestId(`anchored-task-${task.id}`);
  const running = screen.getByTestId('anchored-lane-running');
  const dataTransfer = new MockDataTransfer();
  fireEvent.dragStart(card, { dataTransfer });
  fireEvent.dragOver(running, { dataTransfer });
  fireEvent.drop(running, { dataTransfer });
  expect(useAnchoredStore.getState().tasks[0].lane).toBe('running');
  expect(within(screen.getByTestId(`anchored-task-${task.id}`)).getByText('执行中')).toBeInTheDocument();
});

it('shows a blocked task card with error border and reason', async () => {
  act(() => useAnchoredStore.setState({
    tasks: [{ id: 'blocked', name: 'blocked task', lane: 'pending', blockedReason: '等待工具审批', updatedAt: Date.now() }],
  }));
  render(<AnchoredInfoPanel />);
  await screen.findByDisplayValue('soul server');
  const card = screen.getByTestId('anchored-task-blocked');
  expect(card).toHaveClass('min-h-[64px]');
  expect(within(card).getByText('等待工具审批')).toBeInTheDocument();
  expect(card.className).toContain('--color-error');
});

it('preserves six zero metrics, mixed reported trend and meter state across collapse', async () => {
  render(<AnchoredInfoPanel />);
  await screen.findByDisplayValue('soul server');
  const meter = Object.fromEntries(METER_ORDER.map(({ key }) => [key, 0])) as unknown as MeterSnapshot;
  act(() => useAnchoredStore.getState().setMeter(meter, [
    { input: 0, output: 0, total: 0, cacheSaved: null },
    { input: null, output: null, total: null, cacheSaved: null },
    { input: 3, output: 7, total: 10, cacheSaved: null },
  ]));
  const section = screen.getByTestId('anchored-card-tokenMeter');
  expect(Array.from(section.querySelectorAll('dd')).map(item => item.textContent)).toEqual(['0', '0', '0%', '0', '0', '0']);
  const bars = screen.getByTestId('anchored-meter-trend').children;
  expect(bars).toHaveLength(2);
  expect((bars[0] as HTMLElement).style.height).toBe('8%');
  expect((bars[1] as HTMLElement).style.height).toBe('100%');
  fireEvent.click(cardToggle('tokenMeter'));
  fireEvent.click(cardToggle('tokenMeter'));
  expect(screen.getByTestId('anchored-meter-trend').children).toHaveLength(2);
});

it('expands reported local tree detail and keeps absent result and error unreported', async () => {
  act(() => useAnchoredStore.setState({ subAgentTree: [{ id: 'node', name: 'reported child', status: 'success', durationMs: 0, detail: 'real objective', children: [] }], cardsOpen: { ...useAnchoredStore.getState().cardsOpen, subAgentTree: true } }));
  render(<AnchoredInfoPanel />);
  await screen.findByDisplayValue('soul server');
  const summary = screen.getByText('reported child').closest('summary')!;
  expect(summary).toHaveTextContent('0.0s');
  expect(summary.closest('details')).not.toHaveAttribute('open');
  fireEvent.click(summary);
  expect(summary.closest('details')).toHaveAttribute('open');
  expect(within(summary.closest('details')!).getByText('real objective')).toBeInTheDocument();
  expect(within(summary.closest('details')!).getAllByText('未上报')).toHaveLength(2);
});
