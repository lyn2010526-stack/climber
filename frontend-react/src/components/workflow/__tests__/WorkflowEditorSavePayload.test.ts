import { describe, expect, it } from 'vitest';
import type { Edge, Node } from '@xyflow/react';
import { buildWorkflowSavePayload, toBranchLabel } from '../WorkflowEditor';

const nodes: Node[] = [
  { id: 'start', type: 'input', position: { x: 0, y: 0 }, data: {} },
  { id: 'check', type: 'condition', position: { x: 100, y: 0 }, data: { prompt: 'ok?' } },
  { id: 'yes', type: 'llm', position: { x: 200, y: -50 }, data: {} },
  { id: 'no', type: 'llm', position: { x: 200, y: 50 }, data: {} },
];

function edge(id: string, source: string, target: string, extra: Partial<Edge> = {}): Edge {
  return { id, source, target, ...extra } as Edge;
}

describe('buildWorkflowSavePayload', () => {
  it('sends the branch label as sourceHandle so the engine can route it', () => {
    const edges = [
      edge('e1', 'start', 'check'),
      edge('e2', 'check', 'yes', { sourceHandle: 'true' }),
      edge('e3', 'check', 'no', { sourceHandle: 'false' }),
    ];

    const payload = buildWorkflowSavePayload('demo', nodes, edges);

    expect(payload.name).toBe('demo');
    const branch = payload.edges.filter((e) => e.source === 'check');
    expect(branch).toEqual([
      { id: 'e2', source: 'check', target: 'yes', sourceHandle: 'true', condition: 'true' },
      { id: 'e3', source: 'check', target: 'no', sourceHandle: 'false', condition: 'false' },
    ]);
  });

  it('mirrors the same label into condition so both reader paths agree', () => {
    const payload = buildWorkflowSavePayload('demo', nodes, [
      edge('e2', 'check', 'yes', { sourceHandle: 'true' }),
    ]);

    expect(payload.edges[0].sourceHandle).toBe(payload.edges[0].condition);
  });

  it('falls back to a legacy edge data.condition when no handle is set', () => {
    const payload = buildWorkflowSavePayload('demo', nodes, [
      edge('e2', 'check', 'no', { data: { condition: 'false' } }),
    ]);

    expect(payload.edges[0]).toEqual({
      id: 'e2',
      source: 'check',
      target: 'no',
      sourceHandle: 'false',
      condition: 'false',
    });
  });

  it('leaves unconditional edges unlabelled instead of guessing a branch', () => {
    const payload = buildWorkflowSavePayload('demo', nodes, [
      edge('e1', 'start', 'check', { sourceHandle: null }),
    ]);

    expect(payload.edges[0].sourceHandle).toBe('');
    expect(payload.edges[0].condition).toBe('');
  });

  it('sends only the fields the workflow API stores', () => {
    const payload = buildWorkflowSavePayload('demo', nodes, []);

    expect(payload.nodes).toEqual([
      { id: 'start', type: 'input', data: {}, position: { x: 0, y: 0 } },
      { id: 'check', type: 'condition', data: { prompt: 'ok?' }, position: { x: 100, y: 0 } },
      { id: 'yes', type: 'llm', data: {}, position: { x: 200, y: -50 } },
      { id: 'no', type: 'llm', data: {}, position: { x: 200, y: 50 } },
    ]);
  });
});

describe('toBranchLabel', () => {
  it('accepts only the labels the engine understands', () => {
    expect(toBranchLabel('true')).toBe('true');
    expect(toBranchLabel('false')).toBe('false');
  });

  it('rejects everything else', () => {
    expect(toBranchLabel('TRUE')).toBe('');
    expect(toBranchLabel('yes')).toBe('');
    expect(toBranchLabel(undefined)).toBe('');
    expect(toBranchLabel(null)).toBe('');
    expect(toBranchLabel(1)).toBe('');
  });
});
