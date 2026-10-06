import { render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it } from 'vitest';
import i18n from '../../i18n';
import type { ToolCall } from '../../useChat';
import { ToolCallCard } from './AnchoredMessageFlow';

const base: ToolCall = {
  id: 'exec-1',
  name: 'container_exec',
  arguments: { cmd: 'npm run lint' },
  status: 'success',
  result: 'line one\nline two',
};

describe('CodexExecSummary upgrade', () => {
  beforeEach(async () => {
    await i18n.changeLanguage('zh-CN');
  });

  it('puts the `└` prefix on the first output line and 4 spaces on continuations', () => {
    render(<ToolCallCard call={base} active={false} defaultExpanded={false} />);
    const first = screen.getByTestId('anchored-exec-command-continuation');
    expect(first).toHaveTextContent('└');
    expect(first).toHaveTextContent('line one');
    const second = screen.getByTestId('anchored-exec-output-line');
    expect(second).toHaveTextContent('line two');
    expect(second.textContent).not.toContain('└');
  });

  it('colours a non-zero exit badge red and an exit-1 badge dim', () => {
    const { rerender } = render(
      <ToolCallCard call={{ ...base, result: 'boom', arguments: { cmd: 'npm run lint', exit_code: 2 } }} active={false} defaultExpanded={false} />,
    );
    const badge = screen.getByTestId('anchored-exec-exit-code');
    expect(badge).toHaveTextContent('(exit 2)');
    expect(badge).toHaveClass('text-[var(--color-error)]');
    expect(badge).toHaveAttribute('data-exit-code', '2');

    rerender(
      <ToolCallCard call={{ ...base, result: 'no matches', arguments: { cmd: 'grep x', exit_code: 1 } }} active={false} defaultExpanded={false} />,
    );
    expect(screen.getByTestId('anchored-exec-exit-code')).toHaveClass('text-[var(--color-text-disabled)]');
  });

  it('reads the exit code from the result text when arguments omit it', () => {
    render(<ToolCallCard call={{ ...base, result: 'failed\n(exit 3)' }} active={false} defaultExpanded={false} />);
    expect(screen.getByTestId('anchored-exec-exit-code')).toHaveTextContent('(exit 3)');
  });

  it('renders no badge when neither arguments nor output report an exit code', () => {
    render(<ToolCallCard call={base} active={false} defaultExpanded={false} />);
    expect(screen.queryByTestId('anchored-exec-exit-code')).toBeNull();
  });
});
