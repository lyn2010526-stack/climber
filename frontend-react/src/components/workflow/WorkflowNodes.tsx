import type { NodeProps } from '@xyflow/react';
import {
  Position,
  Handle,
} from '@xyflow/react';
import { Bot, Wrench, GitBranch, FileInput, FileOutput, AlertTriangle } from 'lucide-react';
import { cn } from '../../lib/utils';

// ─── Custom Node Components ───

/* Reference: Flowise `CanvasNode.jsx` - border colors, selected states, version warnings */
const nodeStyles: Record<
  'input' | 'llm' | 'tool' | 'condition' | 'output',
  {
    icon: any;
    color: string;
    bg: string;
    borderHover: string;
    borderSelected: string;
  }
> = {
  input: {
    icon: FileInput,
    color: 'text-[var(--color-accent)]',
    bg: 'bg-blue-600/10',
    borderHover: 'hover:border-[var(--color-border-accent)]',
    borderSelected: 'border-blue-500',
  },
  llm: {
    icon: Bot,
    color: 'text-purple-400',
    bg: 'bg-purple-500/10',
    borderHover: 'hover:border-purple-500/40',
    borderSelected: 'border-purple-500',
  },
  tool: {
    icon: Wrench,
    color: 'text-green-400',
    bg: 'bg-green-500/10',
    borderHover: 'hover:border-green-500/40',
    borderSelected: 'border-green-500',
  },
  condition: {
    icon: GitBranch,
    color: 'text-amber-400',
    bg: 'bg-amber-500/10',
    borderHover: 'hover:border-amber-500/40',
    borderSelected: 'border-amber-500',
  },
  output: {
    icon: FileOutput,
    color: 'text-[var(--color-accent)]',
    bg: 'bg-blue-500/10',
    borderHover: 'hover:border-[var(--color-border-accent)]',
    borderSelected: 'border-blue-500',
  },
};

function NodeHeader({ style, nodeData, icon: Icon }: any) {
  return (
    <div className="flex items-center gap-2">
      <div className={`p-1.5 rounded-lg ${style.bg} ${style.color}`}>
        <Icon size={14} />
      </div>
      <span className="text-xs font-medium text-[var(--color-text-primary)] truncate">
        {nodeData['label'] || 'Node'}
      </span>
    </div>
  );
}

function NodeMeta({ nodeData, type }: any) {
  let meta = '';
  if (type === 'llm') meta = nodeData['model'] || 'GPT-4';
  else if (type === 'tool') meta = nodeData['tool_name'] || 'Select tool...';
  else if (type === 'input') meta = nodeData['description'] || 'Workflow input';
  else if (type === 'output') meta = nodeData['description'] || 'Workflow output';

  if (!meta) return null;
  return <p className="text-[10px] text-[var(--color-text-muted)] mt-1 truncate">{meta}</p>;
}

/* Reference: Flowise `CanvasNode.jsx` - selected state, version warning */
export function InputNode({ data, selected }: NodeProps) {
  const style = nodeStyles.input;
  const nodeData = data as Record<string, any>;
  const Icon = style.icon;

  return (
    <div
      className={cn(
        'px-4 py-3 rounded-xl border min-w-[160px] transition-all duration-200',
        style.bg,
        selected ? style.borderSelected : 'border-[var(--color-border-default)]',
        style.borderHover
      )}
    >
      <Handle type="source" position={Position.Right} className="!bg-blue-600 !w-2 !h-2" />
      <NodeHeader style={style} nodeData={nodeData} icon={Icon} />
      <NodeMeta nodeData={nodeData} type="input" />
    </div>
  );
}

export function LLMNode({ data, selected }: NodeProps) {
  const style = nodeStyles.llm;
  const Icon = style.icon;
  const nodeData = data as Record<string, any>;

  return (
    <div
      className={cn(
        'px-4 py-3 rounded-xl border min-w-[180px] transition-all duration-200',
        style.bg,
        selected ? style.borderSelected : 'border-[var(--color-border-default)]',
        style.borderHover
      )}
    >
      <Handle type="target" position={Position.Left} className="!bg-purple-400 !w-2 !h-2" />
      <Handle type="source" position={Position.Right} className="!bg-purple-400 !w-2 !h-2" />
      <NodeHeader style={style} nodeData={nodeData} icon={Icon} />
      <NodeMeta nodeData={nodeData} type="llm" />
      {nodeData['version_warning'] && (
        <div className="flex items-center gap-1 mt-2 text-[9px] text-amber-400">
          <AlertTriangle size={10} />
          <span>Version outdated</span>
        </div>
      )}
    </div>
  );
}

export function ToolNode({ data, selected }: NodeProps) {
  const style = nodeStyles.tool;
  const Icon = style.icon;
  const nodeData = data as Record<string, any>;

  return (
    <div
      className={cn(
        'px-4 py-3 rounded-xl border min-w-[170px] transition-all duration-200',
        style.bg,
        selected ? style.borderSelected : 'border-[var(--color-border-default)]',
        style.borderHover
      )}
    >
      <Handle type="target" position={Position.Left} className="!bg-green-500 !w-2 !h-2" />
      <Handle type="source" position={Position.Right} className="!bg-green-500 !w-2 !h-2" />
      <NodeHeader style={style} nodeData={nodeData} icon={Icon} />
      <NodeMeta nodeData={nodeData} type="tool" />
    </div>
  );
}

export function ConditionNode({ data, selected }: NodeProps) {
  const style = nodeStyles.condition;
  const Icon = style.icon;
  const nodeData = data as Record<string, any>;

  return (
    <div
      className={cn(
        'px-4 py-3 rounded-xl border min-w-[170px] transition-all duration-200',
        style.bg,
        selected ? style.borderSelected : 'border-[var(--color-border-default)]',
        style.borderHover
      )}
    >
      <Handle type="target" position={Position.Left} className="!bg-amber-500 !w-2 !h-2" />
      <Handle type="source" position={Position.Right} className="!bg-green-500 !w-2 !h-2" id="true" />
      <Handle type="source" position={Position.Bottom} className="!bg-red-500 !w-2 !h-2" id="false" />
      <NodeHeader style={style} nodeData={nodeData} icon={Icon} />
      <div className="flex items-center gap-2 mt-2 text-[9px]">
        <span className="px-1.5 py-0.5 bg-green-500/10 text-green-400 rounded">True</span>
        <span className="px-1.5 py-0.5 bg-red-500/10 text-red-400 rounded">False</span>
      </div>
    </div>
  );
}

export function OutputNode({ data, selected }: NodeProps) {
  const style = nodeStyles.output;
  const Icon = style.icon;
  const nodeData = data as Record<string, any>;

  return (
    <div
      className={cn(
        'px-4 py-3 rounded-xl border min-w-[160px] transition-all duration-200',
        style.bg,
        selected ? style.borderSelected : 'border-[var(--color-border-default)]',
        style.borderHover
      )}
    >
      <Handle type="target" position={Position.Left} className="!bg-blue-400 !w-2 !h-2" />
      <NodeHeader style={style} nodeData={nodeData} icon={Icon} />
      <NodeMeta nodeData={nodeData} type="output" />
    </div>
  );
}

export const nodeTypes = {
  input: InputNode,
  llm: LLMNode,
  tool: ToolNode,
  condition: ConditionNode,
  output: OutputNode,
};

// ─── Helper to create nodes ───

export function createWorkflowNode(type: string, position: { x: number; y: number }, data: Record<string, any> = {}) {
  return {
    id: `${type}-${Date.now()}`,
    type,
    position,
    data: { label: type.charAt(0).toUpperCase() + type.slice(1), ...data },
  };
}
