import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MobileAgentsPage } from '../MobileAgentsPage';

vi.mock('../../AgentsPage', () => ({
  AgentsPage: () => <div>Agents Content</div>,
}));

describe('MobileAgentsPage', () => {
  it('renders page header', () => {
    render(<MobileAgentsPage />);
    expect(screen.getByText('智能体')).toBeDefined();
  });

  it('renders AgentsPage content', () => {
    render(<MobileAgentsPage />);
    expect(screen.getByText('Agents Content')).toBeDefined();
  });
});
