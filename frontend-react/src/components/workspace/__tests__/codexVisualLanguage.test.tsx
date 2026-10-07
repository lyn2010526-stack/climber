import { render, screen, within } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import i18n from '../../../i18n/config';
import { useWorkspaceStore, type Session } from '../../../store/workspace';
import { INFO_CARD_ORDER, resetAnchoredStore } from '../../../store/anchored';
import { ControlBar } from '../ControlBar';
import { AnchoredInfoPanel } from '../AnchoredInfoPanel';

vi.mock('../../../api', () => ({ api: {
  listSessions: vi.fn().mockResolvedValue([]), createSession: vi.fn(), deleteSession: vi.fn(),
  listAgents: vi.fn().mockResolvedValue([]), listModels: vi.fn().mockResolvedValue([]),
  getCostUsage: vi.fn().mockResolvedValue({}), listCostRecords: vi.fn().mockResolvedValue([]),
  getMemoryContextBundle: vi.fn().mockResolvedValue({ content: '', injected_summaries: 0, memory_hits: 0, scopes: [], hits: [] }),
  listMemorySidecars: vi.fn().mockResolvedValue({ scope: 'reference', records: [] }),
  listTasks: vi.fn().mockResolvedValue([]), listTraces: vi.fn().mockResolvedValue([]),
  getTask: vi.fn().mockResolvedValue(null), getPermissionConfig: vi.fn().mockResolvedValue({ mode: 'sandbox' }),
} }));
vi.mock('../../anchored/TaskTracePanel', () => ({ TaskTracePanel: () => null }));
vi.mock('../../anchored/ArtifactPreview', () => ({ ArtifactPreview: () => null }));

const css = readFileSync(resolve(process.cwd(), 'src/components/workspace/codex-suite.css'), 'utf-8');
const makeSession = (overrides: Partial<Session> = {}): Session => ({
  id: 's1', title: '会话 Alpha', status: 'idle', messages: [], activeSkills: [], activeTools: [],
  modelConfig: { provider: 'openai', modelId: 'gpt-4o', temperature: 0.7, maxTokens: 4096 },
  tokenUsage: { used: 0, limit: 200000 }, createdAt: Date.now(), ...overrides,
});

beforeEach(async () => {
  vi.clearAllMocks();
  await i18n.changeLanguage('zh-CN');
  resetAnchoredStore();
  vi.stubGlobal('fetch', vi.fn(async () => Response.json({})));
  useWorkspaceStore.setState({ sessions: [], sessionsLoaded: false, loadingSessions: false, activeSessionId: null, rightPanelTab: 'config', rightPanelOpen: true, focusMode: false, expertMode: false, permissionMode: 'sandbox', autonomyLevel: 3, tasks: [], snapshots: [] });
});
afterEach(() => vi.unstubAllGlobals());

describe('Codex visual language', () => {
  it('keeps the surface tokenized and motion bounded', () => {
    expect(css).not.toMatch(/#[0-9a-fA-F]{3,8}\b/);
    expect(css).not.toMatch(/\brgba?\(/);
    const durations = [...css.matchAll(/(\d+)ms/g)].map((match) => Number(match[1]));
    expect(Math.max(...durations)).toBeLessThanOrEqual(200);
    const motionBlock = css.slice(css.indexOf('prefers-reduced-motion'));
    for (const cls of ['.cx-card', '.cx-row', '.cx-btn', '.cx-bar-btn', '.cx-chip', '.cx-input', '.cx-select']) expect(motionBlock).toContain(cls);
  });

  it('renders Codex-style control and inspector surfaces', () => {
    useWorkspaceStore.setState({ sessions: [makeSession()], activeSessionId: 's1' });
    render(<ControlBar />);
    expect(screen.getByRole('button', { name: '停止生成' })).toHaveClass('cx-bar-btn');
    expect(screen.getByText('会话 Alpha')).toHaveClass('text-[13px]');

    render(<AnchoredInfoPanel />);
    for (const card of INFO_CARD_ORDER) {
      const shell = screen.getByTestId(`anchored-card-${card}`);
      expect(shell).toHaveClass('cx-card');
      expect(shell.querySelector('.cx-card-title')).not.toBeNull();
      expect(shell.querySelector('.cx-card-sub')).not.toBeNull();
    }
    const memory = screen.getByTestId('anchored-card-memoryArchive');
    expect(within(memory).getByText('记忆归档')).toHaveClass('cx-card-title');
  });
});
