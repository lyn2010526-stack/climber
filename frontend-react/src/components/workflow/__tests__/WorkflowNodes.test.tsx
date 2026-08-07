import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';

vi.mock('@xyflow/react', () => ({
  Handle: ({ type, position }: any) => <div data-testid={`handle-${type}`} />,
  Position: { Left: 'left', Right: 'right', Top: 'top', Bottom: 'bottom' },
  useStore: () => new Map(),
}));

import { nodeTypes, createWorkflowNode, InputNode, LLMNode, ToolNode, ConditionNode, OutputNode } from '../WorkflowNodes';

describe('WorkflowNodes', () => {
  it('exports nodeTypes', () => {
    expect(nodeTypes).toBeDefined();
    expect(nodeTypes.input).toBeDefined();
    expect(nodeTypes.llm).toBeDefined();
    expect(nodeTypes.tool).toBeDefined();
    expect(nodeTypes.condition).toBeDefined();
    expect(nodeTypes.output).toBeDefined();
  });

  it('creates input node', () => {
    const node = createWorkflowNode('input', { x: 0, y: 0 });
    expect(node).toBeDefined();
    expect(node.type).toBe('input');
  });

  it('creates llm node', () => {
    const node = createWorkflowNode('llm', { x: 100, y: 100 });
    expect(node).toBeDefined();
    expect(node.type).toBe('llm');
  });

  it('creates tool node', () => {
    const node = createWorkflowNode('tool', { x: 200, y: 200 });
    expect(node).toBeDefined();
    expect(node.type).toBe('tool');
  });

  it('creates condition node', () => {
    const node = createWorkflowNode('condition', { x: 300, y: 300 });
    expect(node).toBeDefined();
    expect(node.type).toBe('condition');
  });

  it('creates output node', () => {
    const node = createWorkflowNode('output', { x: 400, y: 400 });
    expect(node).toBeDefined();
    expect(node.type).toBe('output');
  });

  it('node has position', () => {
    const node = createWorkflowNode('input', { x: 50, y: 50 });
    expect(node.position).toEqual({ x: 50, y: 50 });
  });

  it('node has data', () => {
    const node = createWorkflowNode('llm', { x: 0, y: 0 });
    expect(node.data).toBeDefined();
  });

  it('renders InputNode', () => {
    const { container } = render(
      <InputNode id="test-1" data={{ label: 'Test Input' }} selected={false} />
    );
    expect(container).toBeDefined();
  });

  it('renders InputNode with selected state', () => {
    const { container } = render(
      <InputNode id="test-1" data={{ label: 'Test Input' }} selected={true} />
    );
    expect(container).toBeDefined();
  });

  it('renders LLMNode', () => {
    const { container } = render(
      <LLMNode id="test-2" data={{ label: 'Test LLM' }} selected={false} />
    );
    expect(container).toBeDefined();
  });

  it('renders LLMNode with version warning', () => {
    const { container } = render(
      <LLMNode id="test-2" data={{ label: 'Test LLM', version_warning: true }} selected={false} />
    );
    expect(container).toBeDefined();
  });

  it('renders LLMNode with model meta', () => {
    const { container } = render(
      <LLMNode id="test-2" data={{ label: 'Test LLM', model: 'GPT-4' }} selected={false} />
    );
    expect(container).toBeDefined();
  });

  it('renders ToolNode', () => {
    const { container } = render(
      <ToolNode id="test-3" data={{ label: 'Test Tool' }} selected={false} />
    );
    expect(container).toBeDefined();
  });

  it('renders ToolNode with tool_name meta', () => {
    const { container } = render(
      <ToolNode id="test-3" data={{ label: 'Test Tool', tool_name: 'search' }} selected={false} />
    );
    expect(container).toBeDefined();
  });

  it('renders ConditionNode', () => {
    const { container } = render(
      <ConditionNode id="test-4" data={{ label: 'Test Condition' }} selected={false} />
    );
    expect(container).toBeDefined();
  });

  it('renders ConditionNode with selected state', () => {
    const { container } = render(
      <ConditionNode id="test-4" data={{ label: 'Test Condition' }} selected={true} />
    );
    expect(container).toBeDefined();
  });

  it('renders OutputNode', () => {
    const { container } = render(
      <OutputNode id="test-5" data={{ label: 'Test Output' }} selected={false} />
    );
    expect(container).toBeDefined();
  });

  it('renders OutputNode with description', () => {
    const { container } = render(
      <OutputNode id="test-5" data={{ label: 'Test Output', format: 'json' }} selected={false} />
    );
    expect(container).toBeDefined();
  });

  it('renders OutputNode with selected state', () => {
    const { container } = render(
      <OutputNode id="test-5" data={{ label: 'Test Output' }} selected={true} />
    );
    expect(container).toBeDefined();
  });
});
