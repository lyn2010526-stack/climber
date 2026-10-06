import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { StatusIndicator } from './StatusIndicator';

describe('StatusIndicator', () => {
  it('renders nothing when the agent is not working', () => {
    const { container } = render(<StatusIndicator isWorking={false} />);
    expect(container).toBeEmptyDOMElement();
  });

  it('renders the codex first line: bullet, label, elapsed and interrupt hint', () => {
    render(<StatusIndicator isWorking elapsedSeconds={65} />);
    const indicator = screen.getByTestId('status-indicator');
    expect(indicator).toHaveTextContent('工作中');
    expect(indicator).toHaveTextContent('(1m 05s • esc 中断)');
    expect(screen.getByTestId('status-indicator-bullet')).toHaveClass('motion-safe:animate-pulse');
  });

  it('appends the inline message after the interrupt affordance', () => {
    render(<StatusIndicator isWorking elapsedSeconds={0} inlineMessage="正在读取文件" />);
    const indicator = screen.getByTestId('status-indicator');
    expect(indicator).toHaveTextContent('(0s • esc 中断)');
    expect(indicator).toHaveTextContent('· 正在读取文件');
  });

  it('renders detail lines with the codex `└` prefix and truncation', () => {
    render(<StatusIndicator isWorking elapsedSeconds={3} detailLines={['read_file']} />);
    const details = screen.getByTestId('status-indicator-details');
    expect(details).toHaveTextContent('└ read_file');
    expect(details.querySelector('li')).toHaveClass('truncate');
  });

  it('honours an explicit label and interrupt hint', () => {
    render(<StatusIndicator isWorking elapsedSeconds={1} label="思考中" interruptHint="esc to interrupt" />);
    const indicator = screen.getByTestId('status-indicator');
    expect(indicator).toHaveTextContent('思考中');
    expect(indicator).toHaveTextContent('(1s • esc to interrupt)');
  });
});
