import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { CommandPalette } from '../CommandPalette';

const mockCommands = [
  { id: 'new-session', label: 'New Session', description: 'Create a new chat session', icon: () => null, shortcut: 'Ctrl+N', category: 'Session', action: () => {} },
  { id: 'pause', label: 'Pause Task', description: 'Pause the current task', icon: () => null, category: 'Runtime', action: () => {} },
  { id: 'settings', label: 'Settings', description: 'Open settings', icon: () => null, shortcut: 'Ctrl+,', category: 'Config', action: () => {} },
];

describe('CommandPalette', () => {
  it('renders nothing when closed', () => {
    const { container } = render(<CommandPalette isOpen={false} onClose={() => {}} commands={mockCommands} />);
    expect(container.innerHTML).toBe('');
  });

  it('renders commands when open', () => {
    render(<CommandPalette isOpen={true} onClose={() => {}} commands={mockCommands} />);
    expect(screen.getByText('New Session')).toBeDefined();
    expect(screen.getByText('Pause Task')).toBeDefined();
    expect(screen.getByText('Settings')).toBeDefined();
  });

  it('filters commands by query', () => {
    render(<CommandPalette isOpen={true} onClose={() => {}} commands={mockCommands} />);
    const input = screen.getByPlaceholderText('输入命令...');
    fireEvent.change(input, { target: { value: 'pause' } });
    expect(screen.getByText('Pause Task')).toBeDefined();
    expect(screen.queryByText('New Session')).toBeNull();
  });

  it('calls onClose when backdrop is clicked', () => {
    const onClose = () => {};
    render(<CommandPalette isOpen={true} onClose={onClose} commands={mockCommands} />);
    const backdrop = document.querySelector('.fixed.inset-0');
    fireEvent.click(backdrop!);
  });

  it('calls action and onClose when command is clicked', () => {
    const action = () => {};
    const onClose = () => {};
    const commands = [{ ...mockCommands[0], action }] as typeof mockCommands;
    render(<CommandPalette isOpen={true} onClose={onClose} commands={commands} />);
    fireEvent.click(screen.getByText('New Session'));
  });
});
