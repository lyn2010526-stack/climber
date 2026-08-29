import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { WorkflowsPage } from '../WorkflowsPage';

const apiMocks = vi.hoisted(() => ({
  listWorkflows: vi.fn(),
  listWorkflowTemplates: vi.fn(),
}));

vi.mock('../../api', () => ({
  api: {
    ...apiMocks,
    runWorkflow: vi.fn(),
    createWorkflowFromTemplate: vi.fn(),
  },
}));

vi.mock('../../components/workflow/WorkflowEditor', () => ({
  WorkflowEditor: () => <div>工作流编辑器</div>,
}));

describe('WorkflowsPage', () => {
  beforeEach(() => {
    apiMocks.listWorkflows.mockResolvedValue([]);
    apiMocks.listWorkflowTemplates.mockResolvedValue([]);
  });

  it('opens the editor when creating a workflow', async () => {
    const user = userEvent.setup();
    render(<WorkflowsPage />);

    await user.click(await screen.findByRole('button', { name: '新建工作流' }));

    expect(screen.getByRole('heading', { name: '新建工作流' })).toBeInTheDocument();
    expect(screen.getByText('工作流编辑器')).toBeInTheDocument();
  });
});
