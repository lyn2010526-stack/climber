import type { NodeProps } from '@xyflow/react';
import { Handle, Position } from '@xyflow/react';
import { Bot, FileInput, FileOutput, GitBranch, Wrench } from 'lucide-react';

const definitions = {
  input: { icon: FileInput, color: 'text-blue-400' },
  llm: { icon: Bot, color: 'text-purple-400' },
  tool: { icon: Wrench, color: 'text-green-400' },
  condition: { icon: GitBranch, color: 'text-amber-400' },
  output: { icon: FileOutput, color: 'text-cyan-400' },
} as const;

type WorkflowNodeType = keyof typeof definitions;

function WorkflowNode({ data, selected, type }: NodeProps & { type: WorkflowNodeType }) {
  const definition = definitions[type];
  const Icon = definition.icon;
  const label = String(data['label'] ?? type);

  return (
    <div className={`min-w-40 rounded-xl border bg-[var(--color-bg-surface-elevated)] px-4 py-3 ${selected ? 'border-[var(--color-accent)]' : 'border-[var(--color-border-subtle)]'}`}>
      {type !== 'input' && <Handle type="target" position={Position.Left} />}
      <div className={`flex items-center gap-2 text-xs font-medium ${definition.color}`}>
        <Icon size={14} />
        <span>{label}</span>
      </div>
      {type !== 'output' && <Handle type="source" position={Position.Right} />}
    </div>
  );
}

export const nodeTypes = {
  input: (props: NodeProps) => <WorkflowNode {...props} type="input" />,
  llm: (props: NodeProps) => <WorkflowNode {...props} type="llm" />,
  tool: (props: NodeProps) => <WorkflowNode {...props} type="tool" />,
  condition: (props: NodeProps) => <WorkflowNode {...props} type="condition" />,
  output: (props: NodeProps) => <WorkflowNode {...props} type="output" />,
};

export function createWorkflowNode(type: string, position: { x: number; y: number }) {
  return {
    id: `${type}-${crypto.randomUUID()}`,
    type,
    position,
    data: { label: type.charAt(0).toUpperCase() + type.slice(1) },
  };
}
