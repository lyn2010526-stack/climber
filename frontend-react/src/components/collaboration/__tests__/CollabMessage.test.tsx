import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { CollabMessage } from '../CollabMessage';

const mockMessage = {
  id: '1',
  memberId: 'm1',
  memberName: 'Agent 1',
  role: 'worker' as const,
  content: 'Working on the task',
  timestamp: '2024-01-01T12:00:00Z',
};

describe('CollabMessage', () => {
  it('renders without crashing', () => {
    const { container } = render(
      <CollabMessage message={mockMessage} />
    );
    expect(container).toBeDefined();
  });

  it('renders member name', () => {
    render(<CollabMessage message={mockMessage} />);
    expect(screen.getByText('Agent 1')).toBeDefined();
  });

  it('renders content', () => {
    render(<CollabMessage message={mockMessage} />);
    expect(screen.getByText('Working on the task')).toBeDefined();
  });

  it('renders role label', () => {
    render(<CollabMessage message={mockMessage} />);
    expect(screen.getByText('Worker')).toBeDefined();
  });
});
