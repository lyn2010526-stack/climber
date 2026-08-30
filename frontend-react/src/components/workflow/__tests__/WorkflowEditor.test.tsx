import { beforeEach, describe, it, expect, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { WorkflowEditor } from '../WorkflowEditor';

const apiMocks = vi.hoisted(() => ({
  createWorkflow: vi.fn(),
  getWorkflowNodeTypes: vi.fn(),
  runWorkflowNode: vi.fn(),
}));

vi.mock('../../../api', () => ({
  api: apiMocks,
}));

const nodeTypes = [
  { type: 'input', label: 'Input', description: 'Input values', color: '#2563eb', inputs: [], outputs: [{ id: 'value', label: 'Value', data_type: 'any', required: false }] },
  { type: 'code', label: 'Code', description: 'Run code', color: '#0d9488', inputs: [{ id: 'input', label: 'Input', data_type: 'any', required: false }], outputs: [{ id: 'result', label: 'Result', data_type: 'any', required: false }] },
];

describe('WorkflowEditor', () => {
  beforeEach(() => {
    apiMocks.getWorkflowNodeTypes.mockReset().mockResolvedValue(nodeTypes);
    apiMocks.createWorkflow.mockReset().mockResolvedValue({ id: 'workflow-1' });
    apiMocks.runWorkflowNode.mockReset().mockResolvedValue({
      node_id: 'code-1', status: 'completed', output: { result: 'ok' }, error: '', execution_time_ms: 1,
    });
  });

  it('renders editor with default props', async () => {
    const { container } = render(<WorkflowEditor />);
    expect(container.querySelector('.react-flow')).not.toBeNull();
    await screen.findByText('Input');
  });

  it('renders the node palette from backend metadata', async () => {
    render(<WorkflowEditor />);
    expect(screen.getByText('Node Palette')).toBeDefined();
    expect(await screen.findByText('Input')).toBeDefined();
    expect(await screen.findByText('Code')).toBeDefined();
  });

  it('renders properties panel placeholder', async () => {
    render(<WorkflowEditor />);
    expect(screen.getByText('选择节点以编辑属性')).toBeDefined();
    await screen.findByText('Input');
  });

  it('renders with initial nodes and edges', async () => {
    const initialNodes = [{ id: '1', type: 'input', position: { x: 0, y: 0 }, data: { label: 'Start' } }];
    const initialEdges = [{ id: 'e1-2', source: '1', target: '2' }];
    const { container } = render(<WorkflowEditor initialNodes={initialNodes} initialEdges={initialEdges} />);
    expect(container.querySelector('.react-flow')).not.toBeNull();
    await screen.findAllByText('Input values');
  });

  it('marks unavailable node types without dropping the node', async () => {
    render(<WorkflowEditor initialNodes={[
      { id: 'missing-1', type: 'plugin.missing', position: { x: 0, y: 0 }, data: { label: 'Missing plugin' } },
    ]} />);

    expect(await screen.findByText('Unavailable: plugin.missing')).toBeDefined();
    expect(screen.getByText('Missing plugin')).toBeDefined();
  });

  it('runs the selected node from the editor toolbar', async () => {
    render(<WorkflowEditor initialNodes={[
      { id: 'code-1', type: 'code', position: { x: 0, y: 0 }, data: { label: 'Code' } },
    ]} />);

    await screen.findByText('Input');
    fireEvent.click(screen.getByTestId('rf__node-code-1'));
    fireEvent.click(screen.getByRole('button', { name: 'Run selected node' }));

    await waitFor(() => expect(apiMocks.runWorkflowNode).toHaveBeenCalledWith(
      expect.objectContaining({ id: 'code-1', type: 'code' }),
      {},
    ));
  });

  it('does not persist transient node execution state', async () => {
    render(<WorkflowEditor initialNodes={[
      { id: 'code-1', type: 'code', position: { x: 0, y: 0 }, data: { label: 'Code' } },
    ]} />);

    await screen.findByText('Input');
    fireEvent.click(screen.getByTestId('rf__node-code-1'));
    fireEvent.click(screen.getByRole('button', { name: 'Run selected node' }));
    await waitFor(() => expect(apiMocks.runWorkflowNode).toHaveBeenCalled());
    fireEvent.click(screen.getByRole('button', { name: 'Save' }));

    await waitFor(() => expect(apiMocks.createWorkflow).toHaveBeenCalled());
    const payload = apiMocks.createWorkflow.mock.calls[0]![0];
    expect(payload.nodes[0].data).toEqual({ label: 'Code' });
  });
});
