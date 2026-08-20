export function TaskDetailPanel({
  taskDetails,
  loading,
  onClose,
}: {
  taskDetails: any;
  loading: boolean;
  onClose: () => void;
}) {
  return (
    <div className="p-4 bg-[var(--color-bg-surface-1)] border border-[var(--color-border-subtle)] rounded-2xl space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-medium text-[var(--color-text-primary)]">任务详情</h3>
        <button
          onClick={onClose}
          className="text-xs text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] transition-colors"
        >
          关闭
        </button>
      </div>
      {loading ? (
        <div className="text-xs text-[var(--color-text-muted)]">加载中...</div>
      ) : taskDetails ? (
        <div className="space-y-2">
          <div className="grid grid-cols-2 gap-2 text-[10px]">
            <div>
              <span className="text-[var(--color-text-muted)]">状态:</span>
              <span className="ml-1 text-[var(--color-text-secondary)]">{taskDetails.status}</span>
            </div>
            <div>
              <span className="text-[var(--color-text-muted)]">轮次:</span>
              <span className="ml-1 text-[var(--color-text-secondary)]">{taskDetails.current_round || 0}/{taskDetails.max_rounds || 5}</span>
            </div>
            <div>
              <span className="text-[var(--color-text-muted)]">流程类型:</span>
              <span className="ml-1 text-[var(--color-text-secondary)]">{taskDetails.process_type || 'sequential'}</span>
            </div>
            <div>
              <span className="text-[var(--color-text-muted)]">人工审批:</span>
              <span className="ml-1 text-[var(--color-text-secondary)]">{taskDetails.human_review_required ? '需要' : '不需要'}</span>
            </div>
            <div>
              <span className="text-[var(--color-text-muted)]">Token 消耗:</span>
              <span className="ml-1 text-[var(--color-text-secondary)]">{taskDetails.total_tokens || 0}</span>
            </div>
            <div>
              <span className="text-[var(--color-text-muted)]">开始时间:</span>
              <span className="ml-1 text-[var(--color-text-secondary)]">{taskDetails.started_at ? new Date(taskDetails.started_at).toLocaleString() : '-'}</span>
            </div>
          </div>
          {taskDetails.context && taskDetails.context.length > 0 && (
            <div>
              <span className="text-[10px] text-[var(--color-text-muted)]">依赖任务:</span>
              <div className="flex flex-wrap gap-1 mt-1">
                {taskDetails.context.map((ctx: string) => (
                  <span key={ctx} className="px-2 py-0.5 rounded-lg text-[9px] bg-white/[0.03] border border-[var(--color-border-subtle)] text-[var(--color-text-secondary)]">{ctx.slice(0, 8)}</span>
                ))}
              </div>
            </div>
          )}
          {taskDetails.guardrails && taskDetails.guardrails.length > 0 && (
            <div>
              <span className="text-[10px] text-[var(--color-text-muted)]">校验规则:</span>
              <div className="space-y-1 mt-1">
                {taskDetails.guardrails.map((g: any, i: number) => (
                  <div key={i} className="p-2 bg-white/[0.02] border border-[var(--color-border-subtle)] rounded-xl">
                    <p className="text-[10px] text-[var(--color-text-primary)]">{g.name}</p>
                    {g.description && <p className="text-[9px] text-[var(--color-text-muted)]">{g.description}</p>}
                  </div>
                ))}
              </div>
            </div>
          )}
          {taskDetails.final_output && (
            <div>
              <span className="text-[10px] text-[var(--color-text-muted)]">最终输出:</span>
              <pre className="mt-1 p-2 bg-[var(--color-bg-surface-2)] border border-[var(--color-border-subtle)] rounded-xl text-[10px] text-[var(--color-text-primary)] whitespace-pre-wrap overflow-x-auto max-h-48 overflow-y-auto">
                {taskDetails.final_output}
              </pre>
            </div>
          )}
          {taskDetails.structured_output && Object.keys(taskDetails.structured_output).length > 0 && (
            <div>
              <span className="text-[10px] text-[var(--color-text-muted)]">结构化输出:</span>
              <pre className="mt-1 p-2 bg-[var(--color-bg-surface-2)] border border-[var(--color-border-subtle)] rounded-xl text-[10px] text-[var(--color-text-primary)] whitespace-pre-wrap overflow-x-auto max-h-32 overflow-y-auto">
                {JSON.stringify(taskDetails.structured_output, null, 2)}
              </pre>
            </div>
          )}
        </div>
      ) : (
        <div className="text-xs text-[var(--color-text-muted)]">暂无详情</div>
      )}
    </div>
  );
}
