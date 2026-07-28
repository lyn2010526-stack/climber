import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { WorkflowEditor } from '../WorkflowEditor';

describe('WorkflowEditor', () => {
  it('renders editor with default props', () => {
    const { container } = render(<WorkflowEditor />);
    expect(container.querySelector('.react-flow')).not.toBeNull();
  });

  it('renders node palette', () => {
    render(<WorkflowEditor />);
    expect(screen.getByText('Node Palette')).toBeDefined();
    expect(screen.getByText('Input')).toBeDefined();
    expect(screen.getByText('LLM')).toBeDefined();
  });

  it('renders properties panel placeholder', () => {
    render(<WorkflowEditor />);
    expect(screen.getByText('选择节点以编辑属性')).toBeDefined();
  });

  it('renders with initial nodes and edges', () => {
    const initialNodes = [{ id: '1', type: 'input', position: { x: 0, y: 0 }, data: { label: 'Start' } }];
    const initialEdges = [{ id: 'e1-2', source: '1', target: '2' }];
    const { container } = render(<WorkflowEditor initialNodes={initialNodes} initialEdges={initialEdges} />);
    expect(container.querySelector('.react-flow')).not.toBeNull();
  });
});
