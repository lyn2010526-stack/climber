import { render, screen, within } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import i18n from '../../../i18n/config';
import { useWorkspaceStore, type Session } from '../../../store/workspace';
import { INFO_CARD_ORDER, resetAnchoredStore } from '../../../store/anchored';
import { ControlBar } from '../ControlBar';
import { AnchoredInfoPanel } from '../AnchoredInfoPanel';

vi.mock('../../../api', () => ({
  api: {
    listSessions: vi.fn().mockResolvedValue([]),
    createSession: vi.fn(),
    deleteSession: vi.fn(),
    listAgents: vi.fn().mockResolvedValue([]),
    listModels: vi.fn().mockResolvedValue([]),
    getCostUsage: vi.fn().mockResolvedValue({}),
    listCostRecords: vi.fn().mockResolvedValue([]),
    getMemoryContextBundle: vi.fn().mockResolvedValue({
      content: '', injected_summaries: 0, memory_hits: 0, scopes: [], hits: [],
    }),
    listMemorySidecars: vi.fn().mockResolvedValue({ scope: 'reference', records: [] }),
    listTasks: vi.fn().mockResolvedValue([]),
    listTraces: vi.fn().mockResolvedValue([]),
    getTask: vi.fn().mockResolvedValue(null),
    getPermissionConfig: vi.fn().mockResolvedValue({ mode: 'sandbox' }),
  },
}));
// The two child surfaces fetch on their own; the card shell is what this file
// checks, so they are stubbed out to keep the panel deterministic.
vi.mock('../../anchored/TaskTracePanel', () => ({ TaskTracePanel: () => null }));
vi.mock('../../anchored/ArtifactPreview', () => ({ ArtifactPreview: () => null }));

const CSS_PATH = resolve(process.cwd(), 'src/components/workspace/codex-suite.css');
const css = readFileSync(CSS_PATH, 'utf-8');

const makeSession = (overrides: Partial<Session> = {}): Session => ({
  id: 's1',
  title: '会话 Alpha',
  status: 'idle',
  messages: [],
  activeSkills: [],
  activeTools: [],
  modelConfig: { provider: 'openai', modelId: 'gpt-4o', temperature: 0.7, maxTokens: 4096 },
  tokenUsage: { used: 0, limit: 200000 },
  createdAt: Date.now(),
  ...overrides,
});

afterEach(() => vi.unstubAllGlobals());

beforeEach(async () => {
  vi.clearAllMocks();
  await i18n.changeLanguage('zh-CN');
  resetAnchoredStore();
  vi.stubGlobal('fetch', vi.fn(async (url: string) => {
    if (url === '/api/v1/auth/me') return Response.json({ id: 'owner-a' });
    if (url === '/api/v1/api-keys') return Response.json([]);
    if (url.startsWith('/api/v1/models/discover?')) {
      return Response.json({ credential_id: '', provider: 'openai', source: 'provider_api', status: 'ok', models: [] });
    }
    return Response.json({}, { status: 200 });
  }));
  useWorkspaceStore.setState({
    sessions: [],
    sessionsLoaded: false,
    loadingSessions: false,
    activeSessionId: null,
    rightPanelTab: 'config',
    rightPanelOpen: true,
    focusMode: false,
    expertMode: false,
    permissionMode: 'sandbox',
    autonomyLevel: 3,
    tasks: [],
    snapshots: [],
  });
});

describe('codex-suite token contract', () => {
  it('keeps the surface language on tokens rather than colour literals', () => {
    expect(css).not.toMatch(/#[0-9a-fA-F]{3,8}\b/);
    expect(css).not.toMatch(/\brgba?\(/);
  });

  it('keeps every transition inside the 200ms interaction window', () => {
    const durations = [...css.matchAll(/(\d+)ms/g)].map(match => Number(match[1]));
    expect(durations.length).toBeGreaterThan(0);
    expect(Math.max(...durations)).toBeLessThanOrEqual(200);
  });

  it('honours reduced motion for each animated surface', () => {
    const block = css.slice(css.indexOf('prefers-reduced-motion'));
    for (const cls of ['.cx-card', '.cx-row', '.cx-btn', '.cx-bar-btn', '.cx-chip', '.cx-input', '.cx-select']) {
      expect(block, cls).toContain(cls);
    }
  });
});

describe('ControlBar workbench language', () => {
  it('renders bar buttons and a 13px session title', () => {
    useWorkspaceStore.setState({ sessions: [makeSession()], activeSessionId: 's1' });
    render(<ControlBar />);

    const stop = screen.getByRole('button', { name: '停止生成' });
    expect(stop).toHaveClass('cx-bar-btn');
    expect(stop.className).toContain('cx-bar-btn-danger');

    expect(screen.getByText('会话 Alpha')).toHaveClass('text-[13px]');
  });
});

describe('AnchoredInfoPanel workbench language', () => {
  it('wraps all six cards in the shared surface with a title and subtitle', () => {
    render(<AnchoredInfoPanel />);

    for (const card of INFO_CARD_ORDER) {
      const shell = screen.getByTestId(`anchored-card-${card}`);
      expect(shell).toHaveClass('cx-card');
      expect(shell.querySelector('.cx-card-title')).not.toBeNull();
      expect(shell.querySelector('.cx-card-sub')).not.toBeNull();
    }

    const memory = screen.getByTestId('anchored-card-memoryArchive');
    expect(within(memory).getByText('记忆归档')).toHaveClass('cx-card-title');
    expect(within(memory).getByText('L0 摘要与按需明细')).toHaveClass('cx-card-sub');
  });
});
