import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import ApprovalsPage from '../ApprovalsPage';

describe('ApprovalsPage', () => {
  it('renders page title', () => {
    render(<ApprovalsPage />);
    expect(screen.getByText('审批队列')).toBeDefined();
  });

  it('renders description', () => {
    render(<ApprovalsPage />);
    expect(screen.getByText('待人工审批的工具调用')).toBeDefined();
  });

  it('renders empty state message', () => {
    render(<ApprovalsPage />);
    expect(screen.getByText('暂无待审批项')).toBeDefined();
  });
});
