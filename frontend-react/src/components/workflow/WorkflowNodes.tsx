import type { NodeProps } from '@xyflow/react';
import {
  Position,
  Handle,
} from '@xyflow/react';
import { Bot, Wrench, GitBranch, FileInput, FileOutput, AlertTriangle, FlaskConical } from 'lucide-react';
import { cn } from '../../lib/utils';
import { useTranslation } from '../../i18n';

// Shared neutral surface; selection is independent of node type.
const neutralNodeStyle = {
  color: 'text-[var(--color-text-secondary)]',
  bg: 'bg-[var(--color-bg-surface-1)]',
  borderHover: 'hover:border-[var(--color-border-strong)]',
  borderSelected: 'border-[var(--color-accent)] ring-1 ring-[var(--color-accent)]',
};
const nodeStyles: Record<
  'input' | 'llm' | 'tool' | 'simulation' | 'condition' | 'output',
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
    ...neutralNodeStyle,
  },
  llm: {
    icon: Bot,
    ...neutralNodeStyle,
  },
  tool: {
    icon: Wrench,
    ...neutralNodeStyle,
  },
  simulation: {
    icon: FlaskConical,
    ...neutralNodeStyle,
  },
  condition: {
    icon: GitBranch,
    ...neutralNodeStyle,
  },
  output: {
    icon: FileOutput,
    ...neutralNodeStyle,
  },
};

function NodeHeader({ style, nodeData, icon: Icon }: any) {
  return (
    <div className="flex items-center gap-2">
      <div className={`shrink-0 p-1 rounded-[var(--radius-sm)] bg-[var(--color-bg-surface-2)] ${style.color}`}>
        <Icon size={14} />
      </div>
      <span className="min-w-0 text-xs font-semibold text-[var(--color-text-primary)] truncate">
        {nodeData['label'] || 'Node'}
      </span>
    </div>
  );
}

function NodeMeta({ nodeData, type }: any) {
  let meta = '';
  if (type === 'llm') meta = nodeData['model'] || 'GPT-4';
  else if (type === 'tool') meta = nodeData['tool_name'] || 'Select tool...';
  else if (type === 'simulation') meta = nodeData['tool_name'] || 'simulate_experiment';
  else if (type === 'input') meta = nodeData['description'] || 'Workflow input';
  else if (type === 'output') meta = nodeData['description'] || 'Workflow output';

  if (!meta) return null;
  return <p title={meta} className="text-xs text-[var(--color-text-secondary)] mt-2 truncate">{meta}</p>;
}

export function InputNode({ data, selected }: NodeProps) {
  const style = nodeStyles.input;
  const nodeData = data as Record<string, any>;
  const Icon = style.icon;

  return (
    <div
      className={cn(
        'px-3 py-2.5 rounded-[var(--radius-md)] border w-[200px]',
        style.bg,
        selected ? style.borderSelected : 'border-[var(--color-border-default)]',
        style.borderHover
      )}
    >
      <Handle type="source" position={Position.Right} className="!bg-[var(--color-text-muted)] !w-2 !h-2" />
      <NodeHeader style={style} nodeData={nodeData} icon={Icon} />
      <NodeMeta nodeData={nodeData} type="input" />
    </div>
  );
}

export function LLMNode({ data, selected }: NodeProps) {
  const { t } = useTranslation();
  const style = nodeStyles.llm;
  const Icon = style.icon;
  const nodeData = data as Record<string, any>;

  return (
    <div
      className={cn(
        'px-3 py-2.5 rounded-[var(--radius-md)] border w-[200px]',
        style.bg,
        selected ? style.borderSelected : 'border-[var(--color-border-default)]',
        style.borderHover
      )}
    >
      <Handle type="target" position={Position.Left} className="!bg-[var(--color-text-muted)] !w-2 !h-2" />
      <Handle type="source" position={Position.Right} className="!bg-[var(--color-text-muted)] !w-2 !h-2" />
      <NodeHeader style={style} nodeData={nodeData} icon={Icon} />
      <NodeMeta nodeData={nodeData} type="llm" />
      {nodeData['version_warning'] && (
        <div className="flex items-center gap-1 mt-2 text-xs text-[var(--color-warning)]">
          <AlertTriangle size={10} />
          <span>{t('common.version_outdated')}</span>
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
        'px-3 py-2.5 rounded-[var(--radius-md)] border w-[200px]',
        style.bg,
        selected ? style.borderSelected : 'border-[var(--color-border-default)]',
        style.borderHover
      )}
    >
      <Handle type="target" position={Position.Left} className="!bg-[var(--color-text-muted)] !w-2 !h-2" />
      <Handle type="source" position={Position.Right} className="!bg-[var(--color-text-muted)] !w-2 !h-2" />
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
        'px-3 py-2.5 rounded-[var(--radius-md)] border w-[200px]',
        style.bg,
        selected ? style.borderSelected : 'border-[var(--color-border-default)]',
        style.borderHover
      )}
    >
      <Handle type="target" position={Position.Left} className="!bg-[var(--color-text-muted)] !w-2 !h-2" />
      <Handle type="source" position={Position.Right} className="!bg-[var(--color-text-muted)] !w-2 !h-2" id="true" />
      <Handle type="source" position={Position.Bottom} className="!bg-[var(--color-text-muted)] !w-2 !h-2" id="false" />
      <NodeHeader style={style} nodeData={nodeData} icon={Icon} />
      <div className="flex items-center justify-between mt-2 border-t border-[var(--color-border-subtle)] pt-2 text-xs text-[var(--color-text-secondary)]">
        <span>False</span>
        <span>True</span>
      </div>
    </div>
  );
}

export function SimulationNode({ data, selected }: NodeProps) {
  const style = nodeStyles.simulation;
  const Icon = style.icon;
  const nodeData = data as Record<string, any>;

  return (
    <div
      className={cn(
        'px-3 py-2.5 rounded-[var(--radius-md)] border w-[200px]',
        style.bg,
        selected ? style.borderSelected : 'border-[var(--color-border-default)]',
        style.borderHover
      )}
    >
      <Handle type="target" position={Position.Left} className="!bg-[var(--color-text-muted)] !w-2 !h-2" />
      <Handle type="source" position={Position.Right} className="!bg-[var(--color-text-muted)] !w-2 !h-2" />
      <NodeHeader style={style} nodeData={nodeData} icon={Icon} />
      <NodeMeta nodeData={nodeData} type="simulation" />
      {(nodeData['schema'] || nodeData['max_rounds']) && (
        <div className="flex items-center gap-2 mt-2 text-xs">
          {nodeData['schema'] && (
            <span className="px-1.5 py-0.5 bg-[var(--color-bg-surface-2)] text-[var(--color-text-secondary)] rounded">Schema</span>
          )}
          {nodeData['max_rounds'] && (
            <span className="px-1.5 py-0.5 bg-[var(--color-bg-surface-2)] text-[var(--color-text-secondary)] rounded">R{nodeData['max_rounds']}</span>
          )}
        </div>
      )}
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
        'px-3 py-2.5 rounded-[var(--radius-md)] border w-[200px]',
        style.bg,
        selected ? style.borderSelected : 'border-[var(--color-border-default)]',
        style.borderHover
      )}
    >
      <Handle type="target" position={Position.Left} className="!bg-[var(--color-text-muted)] !w-2 !h-2" />
      <NodeHeader style={style} nodeData={nodeData} icon={Icon} />
      <NodeMeta nodeData={nodeData} type="output" />
    </div>
  );
}

export const nodeTypes = {
  input: InputNode,
  llm: LLMNode,
  tool: ToolNode,
  simulation: SimulationNode,
  condition: ConditionNode,
  output: OutputNode,
};

let nodeSequence = 0;

export function createWorkflowNode(type: string, position: { x: number; y: number }, data: Record<string, any> = {}) {
  nodeSequence += 1;
  return {
    // A monotonic suffix keeps ids unique even when two nodes are created in
    // the same millisecond (e.g. rapid double-add), which Date.now() alone does not (R12-H03).
    id: `${type}-${Date.now()}-${nodeSequence}`,
    type,
    position,
    data: { label: type.charAt(0).toUpperCase() + type.slice(1), ...data },
  };
}
