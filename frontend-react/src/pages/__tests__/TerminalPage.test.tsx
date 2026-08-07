import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import TerminalPage from '../TerminalPage';

vi.mock('../../components/terminal/TerminalPanel', () => ({
  TerminalPanel: () => <div data-testid="terminal-panel">TerminalPanel</div>,
}));

describe('TerminalPage', () => {
  it('renders page title', () => {
    render(<TerminalPage />);
    expect(screen.getByText('终端沙箱')).toBeDefined();
  });

  it('renders description', () => {
    render(<TerminalPage />);
    expect(screen.getByText('安全的命令执行环境')).toBeDefined();
  });

  it('renders TerminalPanel component', () => {
    render(<TerminalPage />);
    expect(screen.getByTestId('terminal-panel')).toBeDefined();
  });
});
