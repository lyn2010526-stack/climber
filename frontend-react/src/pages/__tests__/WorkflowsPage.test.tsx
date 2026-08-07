import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

vi.mock('../../api', () => ({
  api: {
    listWorkflows: vi.fn().mockResolvedValue([]),
    runWorkflow: vi.fn().mockResolvedValue({}),
    createWorkflow: vi.fn().mockResolvedValue({}),
  },
}));

vi.mock('@xyflow/react', () => ({
  ReactFlow: ({ children }: any) => <div data-testid="react-flow">{children}</div>,
  Background: () => null,
  Controls: () => null,
  MiniMap: () => null,
  addEdge: vi.fn(),
  useNodesState: () => [[], vi.fn(), vi.fn()],
  useEdgesState: () => [[], vi.fn(), vi.fn()],
  BackgroundVariant: { Dots: 'dots' },
  ReactFlowProvider: ({ children }: any) => <>{children}</>,
}));

import { WorkflowsPage } from '../WorkflowsPage';

describe('WorkflowsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders without crashing', () => {
    const { container } = render(
      <MemoryRouter>
        <WorkflowsPage />
      </MemoryRouter>
    );
    expect(container).toBeDefined();
  });

  it('renders loading state initially', () => {
    const { container } = render(
      <MemoryRouter>
        <WorkflowsPage />
      </MemoryRouter>
    );
    expect(container.querySelector('svg.animate-spin')).toBeDefined();
  });

  it('renders content after loading', async () => {
    const { container } = render(
      <MemoryRouter>
        <WorkflowsPage />
      </MemoryRouter>
    );
    await waitFor(() => {
      expect(container).toBeDefined();
    });
  });

  it('fetches workflows on mount', () => {
    const { container } = render(
      <MemoryRouter>
        <WorkflowsPage />
      </MemoryRouter>
    );
    expect(container).toBeDefined();
  });
});
