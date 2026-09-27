import { fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import i18n from '../../i18n';
import { ToolCallVisualization, type ToolCall } from './ToolCallVisualization';
import { RESULT_PREVIEW_LIMIT, selectOutputText } from './toolOutput';
import { AUTO_EXPAND_TOOLS_KEY } from './toolExpansion';

const call: ToolCall = {
  id: 'call-1',
  name: 'run_command',
  arguments: { command: 'npm test' },
  result: 'Passed',
  status: 'success',
};

const argsLabel = () => i18n.t('tool_call.arguments');
const resultLabel = () => i18n.t('tool_call.result');
const autoExpand = () => i18n.t('tool_call.auto_expand');
/** The output block, which is the card body and carries the result as its label. */
const outputBlock = () => screen.getByLabelText(resultLabel());
const cardOf = (name: RegExp | string) => screen.getByRole('button', { name });

beforeEach(async () => {
  localStorage.clear();
  await i18n.changeLanguage('en');
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe('expansion state has three layers', () => {
  it('keeps a card the user closed closed when the global preference turns on', () => {
    const { rerender } = render(<ToolCallVisualization calls={[call, { ...call, id: 'call-2' }]} />);
    const [mine, untouched] = screen.getAllByRole('button', { name: /run_command/ });
    expect(mine).toHaveAttribute('aria-expanded', 'false');

    // Opening and closing it is a decision of record, and nothing passive
    // takes it back.
    fireEvent.click(mine);
    expect(mine).toHaveAttribute('aria-expanded', 'true');
    fireEvent.click(mine);
    expect(mine).toHaveAttribute('aria-expanded', 'false');

    fireEvent.click(screen.getByRole('button', { name: autoExpand() }));
    rerender(<ToolCallVisualization calls={[call, { ...call, id: 'call-2' }]} />);
    expect(mine).toHaveAttribute('aria-expanded', 'false');
    // The preference still opens the card nobody has an opinion about.
    expect(untouched).toHaveAttribute('aria-expanded', 'true');
  });

  it('opens a card the preference reached, even after a re-render', () => {
    const { rerender } = render(<ToolCallVisualization calls={[call, { ...call, id: 'call-2' }]} />);
    fireEvent.click(screen.getByRole('button', { name: autoExpand() }));
    rerender(<ToolCallVisualization calls={[{ ...call, status: 'success' }, { ...call, id: 'call-2' }]} />);
    expect(screen.getAllByRole('button', { name: /run_command/ }).every(row => row.getAttribute('aria-expanded') === 'true')).toBe(true);
  });

  it('records the preference for the next session and starts it off', () => {
    expect(localStorage.getItem(AUTO_EXPAND_TOOLS_KEY)).toBeNull();
    const { unmount } = render(<ToolCallVisualization calls={[call]} />);
    const toggle = screen.getByRole('button', { name: autoExpand() });
    expect(toggle).toHaveAttribute('aria-pressed', 'false');
    fireEvent.click(toggle);
    expect(toggle).toHaveAttribute('aria-pressed', 'true');
    expect(localStorage.getItem(AUTO_EXPAND_TOOLS_KEY)).toBe('true');

    unmount();
    render(<ToolCallVisualization calls={[call]} />);
    expect(screen.getByRole('button', { name: autoExpand() })).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByRole('button', { name: /run_command/ })).toHaveAttribute('aria-expanded', 'true');
  });

  it('expands every card on demand and collapses them all again', () => {
    render(<ToolCallVisualization calls={[call, { ...call, id: 'call-2' }]} />);
    fireEvent.click(screen.getByRole('button', { name: i18n.t('tool_call.expand_all') }));
    const rows = screen.getAllByRole('button', { name: /run_command/ });
    expect(rows.map(row => row.getAttribute('aria-expanded'))).toEqual(['true', 'true']);

    fireEvent.click(screen.getByRole('button', { name: i18n.t('tool_call.collapse_all') }));
    expect(screen.getAllByRole('button', { name: /run_command/ }).map(row => row.getAttribute('aria-expanded'))).toEqual(['false', 'false']);
  });

  it('lets an explicit expand-all overrule a card the user had closed', () => {
    render(<ToolCallVisualization calls={[call]} />);
    const card = cardOf(/run_command/);
    fireEvent.click(card);
    fireEvent.click(card);
    expect(card).toHaveAttribute('aria-expanded', 'false');
    // Asking for all of them is a decision too, and it lands last.
    fireEvent.click(screen.getByRole('button', { name: i18n.t('tool_call.expand_all') }));
    expect(card).toHaveAttribute('aria-expanded', 'true');
  });
});

describe('the output is the body, the arguments are context', () => {
  it('shows the result as soon as the card opens and folds the arguments away', () => {
    render(<ToolCallVisualization calls={[call]} defaultExpanded />);
    expect(outputBlock()).toHaveTextContent('Passed');
    const params = screen.getByRole('button', { name: `${argsLabel()} (1)` });
    expect(params).toHaveAttribute('aria-expanded', 'false');
    expect(screen.queryByText(/"command"/)).toBeNull();
    expect(screen.queryByRole('button', { name: resultLabel() })).toBeNull();

    fireEvent.click(params);
    expect(screen.getByText(/"command"/)).toHaveTextContent('npm test');
  });

  it('drops the argument section when the call passed nothing', () => {
    render(<ToolCallVisualization calls={[{ ...call, arguments: {} }]} defaultExpanded />);
    expect(screen.queryByRole('button', { name: argsLabel() })).toBeNull();
    expect(screen.getByText('Passed')).toBeVisible();
  });

  it('keeps the error as its own branch next to the output', () => {
    render(<ToolCallVisualization calls={[{ ...call, status: 'error', error: 'exit code 1' }]} defaultExpanded />);
    expect(screen.getByText('exit code 1')).toBeVisible();
    expect(screen.getByText('Passed')).toBeVisible();
    const errorBlock = screen.getByLabelText(i18n.t('tool_call.error_detail'));
    expect(errorBlock).toHaveClass('text-[var(--color-error)]');
  });
});

describe('a folded card costs nothing', () => {
  it('never serializes the arguments while the card is closed', () => {
    const serialize = vi.spyOn(JSON, 'stringify');
    render(<ToolCallVisualization calls={[call]} />);
    const card = cardOf(/run_command/);
    // Collapsed: no argument block, so no decode of the payload at all.
    expect(screen.queryByLabelText(argsLabel())).toBeNull();
    expect(serialize).not.toHaveBeenCalledWith(call.arguments, null, 2);

    fireEvent.click(card);
    expect(serialize).not.toHaveBeenCalledWith(call.arguments, null, 2);
    fireEvent.click(screen.getByRole('button', { name: `${argsLabel()} (1)` }));
    expect(serialize).toHaveBeenCalledWith(call.arguments, null, 2);

    // Closing the card drops the payload again rather than keeping it around.
    fireEvent.click(card);
    expect(screen.queryByText(/"command"/)).toBeNull();
  });
});

describe('a very long output is clipped, and says so honestly', () => {
  const long = 'y'.repeat(RESULT_PREVIEW_LIMIT + 2000);
  const showAll = () => i18n.t('tool_call.show_all', { count: long.length.toLocaleString() });

  it('clips at the limit and reports the real length', () => {
    render(<ToolCallVisualization calls={[{ ...call, result: long }]} defaultExpanded />);
    expect(outputBlock().textContent).toHaveLength(RESULT_PREVIEW_LIMIT);
    expect(screen.getByRole('button', { name: showAll() })).toBeVisible();

    fireEvent.click(screen.getByRole('button', { name: showAll() }));
    expect(outputBlock().textContent).toHaveLength(long.length);
    expect(screen.queryByRole('button', { name: showAll() })).toBeNull();
  });

  it('returns to the clipped form when the card is folded again', () => {
    render(<ToolCallVisualization calls={[{ ...call, result: long }]} defaultExpanded />);
    fireEvent.click(screen.getByRole('button', { name: showAll() }));
    const card = cardOf(/run_command/);
    fireEvent.click(card);
    fireEvent.click(card);
    expect(outputBlock().textContent).toHaveLength(RESULT_PREVIEW_LIMIT);
    expect(screen.getByRole('button', { name: showAll() })).toBeVisible();
  });

  it('leaves an output at the limit untouched', () => {
    expect(selectOutputText('z'.repeat(RESULT_PREVIEW_LIMIT), false)).toEqual({
      text: 'z'.repeat(RESULT_PREVIEW_LIMIT),
      truncated: false,
      fullLength: RESULT_PREVIEW_LIMIT,
    });
    expect(selectOutputText(long, false).truncated).toBe(true);
    expect(selectOutputText(long, true).text).toHaveLength(long.length);
  });
});
