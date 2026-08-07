import {
  BaseEdge,
  EdgeLabelRenderer,
  getBezierPath,
  type EdgeProps,
} from '@xyflow/react';
import { X } from 'lucide-react';
import { cn } from '../../lib/utils';

interface WorkflowEdgeData {
  label?: string;
  animated?: boolean;
  condition?: string;
}

export function WorkflowEdge({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  data,
  selected,
}: EdgeProps) {
  const [edgePath, labelX, labelY] = getBezierPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    targetPosition,
  });

  const edgeData = (data || {}) as WorkflowEdgeData;
  const isConditionTrue = edgeData.condition === 'true';
  const isConditionFalse = edgeData.condition === 'false';

  const strokeColor = isConditionTrue
    ? 'stroke-emerald-500/60'
    : isConditionFalse
      ? 'stroke-red-500/60'
      : selected
        ? 'stroke-blue-400'
        : 'stroke-white/15';

  const strokeWidth = selected ? 2.5 : 1.5;

  return (
    <>
      <BaseEdge
        id={id}
        path={edgePath}
        className={cn(
          strokeColor,
          'transition-all duration-200',
          edgeData.animated && 'animate-flow-edge'
        )}
        style={{
          strokeWidth,
          strokeDasharray: edgeData.animated ? '5 5' : undefined,
        }}
      />

      {selected && (
        <EdgeLabelRenderer>
          <div
            className="absolute pointer-events-auto"
            style={{
              transform: `translate(-50%, -50%) translate(${labelX}px, ${labelY}px)`,
            }}
          >
            <button
              onClick={(e) => {
                e.stopPropagation();
                const event = new CustomEvent('remove-edge', { detail: { id } });
                window.dispatchEvent(event);
              }}
              className={cn(
                'w-5 h-5 rounded-full flex items-center justify-center',
                'bg-red-500/90 hover:bg-red-500 text-white',
                'shadow-lg shadow-red-500/20 transition-all duration-150',
                'hover:scale-110 active:scale-95'
              )}
            >
              <X size={10} strokeWidth={3} />
            </button>
          </div>
        </EdgeLabelRenderer>
      )}

      {edgeData.label && (
        <EdgeLabelRenderer>
          <div
            className={cn(
              'absolute px-2 py-0.5 rounded-md text-[10px] font-medium',
              'bg-[var(--color-bg-surface-elevated)] border border-[var(--color-border-subtle)]',
              'text-[var(--color-text-secondary)] whitespace-nowrap',
              'pointer-events-none'
            )}
            style={{
              transform: `translate(-50%, -50%) translate(${labelX}px, ${labelY}px)`,
            }}
          >
            {edgeData.label}
          </div>
        </EdgeLabelRenderer>
      )}
    </>
  );
}
