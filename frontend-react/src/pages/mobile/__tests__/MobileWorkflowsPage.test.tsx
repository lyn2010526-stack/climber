import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MobileWorkflowsPage } from '../MobileWorkflowsPage';

vi.mock('../../../api', () => ({
  api: {
    listWorkflows: vi.fn().mockResolvedValue([]),
    listWorkflowTemplates: vi.fn().mockResolvedValue([]),
    runWorkflow: vi.fn(),
    createWorkflowFromTemplate: vi.fn(),
  },
}));

describe('MobileWorkflowsPage', () => {
  it('renders page header', () => {
    render(<MobileWorkflowsPage />);
    expect(screen.getByText('工作流')).toBeDefined();
  });

  it('renders templates button and empty state', async () => {
    render(<MobileWorkflowsPage />);
    expect(screen.getByText('模板')).toBeDefined();
    expect(await screen.findByText(/暂无工作流/)).toBeDefined();
  });
});
