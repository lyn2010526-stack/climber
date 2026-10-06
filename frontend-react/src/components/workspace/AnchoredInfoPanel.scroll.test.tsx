import { act, fireEvent, render, screen } from '@testing-library/react';
import { beforeEach, expect, it, vi } from 'vitest';
import i18n from '../../i18n';
import { INFO_CARD_ORDER, resetAnchoredStore } from '../../store/anchored';
import { AnchoredInfoPanel } from './AnchoredInfoPanel';

vi.mock('../../api', () => ({ api: {
  getCostUsage: vi.fn().mockResolvedValue({}),
  listCostRecords: vi.fn().mockResolvedValue([]),
  getMemoryContextBundle: vi.fn().mockResolvedValue({ content: '', injected_summaries: 0, memory_hits: 0, scopes: [], hits: [] }),
  listMemorySidecars: vi.fn().mockResolvedValue({ scope: 'reference', records: [] }),
} }));
vi.mock('../anchored/TaskTracePanel', () => ({ TaskTracePanel: () => null }));
vi.mock('../anchored/ArtifactPreview', () => ({ ArtifactPreview: () => null }));

const rafFlush = () => new Promise<void>((resolve) => requestAnimationFrame(() => resolve()));

beforeEach(async () => {
  vi.clearAllMocks();
  await i18n.changeLanguage('zh-CN');
  resetAnchoredStore();
});

it('renders a sticky segmented reading progress above the six info cards', async () => {
  render(<AnchoredInfoPanel />);
  const bar = screen.getByRole('progressbar', { name: '信息面板阅读进度' });
  expect(bar).toHaveAttribute('aria-valuemin', '0');
  expect(bar).toHaveAttribute('aria-valuemax', '100');
  await act(async () => {
    await rafFlush();
  });
  expect(bar).toHaveAttribute('aria-valuenow', '0');
  const states = [...bar.querySelectorAll('span')].map((span) => span.getAttribute('data-state'));
  expect(states).toHaveLength(INFO_CARD_ORDER.length);
  expect(states[0]).toBe('active');
  expect(states.slice(1)).toEqual(new Array(5).fill('idle'));
});

it('maps panel scroll position onto the reading progress segments', async () => {
  render(<AnchoredInfoPanel />);
  const panel = screen.getByTestId('anchored-info-panel');
  vi.spyOn(panel, 'scrollHeight', 'get').mockReturnValue(1000);
  vi.spyOn(panel, 'clientHeight', 'get').mockReturnValue(300);
  panel.scrollTop = 350;
  await act(async () => {
    fireEvent.scroll(panel);
    await rafFlush();
  });
  const bar = screen.getByRole('progressbar', { name: '信息面板阅读进度' });
  expect(bar).toHaveAttribute('aria-valuenow', '50');
  const states = [...bar.querySelectorAll('span')].map((span) => span.getAttribute('data-state'));
  expect(states).toEqual(['passed', 'passed', 'passed', 'active', 'idle', 'idle']);
});

it('keeps info cards visible without an intersection observer', () => {
  render(<AnchoredInfoPanel />);
  for (const card of INFO_CARD_ORDER) {
    const shell = screen.getByTestId(`anchored-card-${card}`);
    expect(shell).toBeInTheDocument();
    expect(shell.parentElement?.style.opacity).toBe('');
  }
});

it('stagger-reveals the task board lanes', () => {
  render(<AnchoredInfoPanel />);
  const lanes = screen.getByTestId('anchored-task-board-lanes');
  expect(lanes).toContainElement(screen.getByTestId('anchored-lane-pending'));
  expect(lanes).toContainElement(screen.getByTestId('anchored-lane-running'));
  expect(lanes).toContainElement(screen.getByTestId('anchored-lane-completed'));
  expect(screen.getByTestId('anchored-lane-running').style.transitionDelay).toBe('');
});

it('renders the parallax decoration as an aria-hidden accent strip', async () => {
  render(<AnchoredInfoPanel />);
  const decor = screen.getByTestId('anchored-info-panel-decor');
  expect(decor).toHaveAttribute('aria-hidden', 'true');
  expect(decor.parentElement).toHaveAttribute('aria-hidden', 'true');
  expect(decor.style.background).toContain('linear-gradient');
  expect(decor.style.background).toContain('var(--color-accent-subtle)');
  await act(async () => {
    await rafFlush();
  });
  expect(decor.style.transform).toBe('translate3d(0, 0.00px, 0)');
});
