import { Network, Play, CheckCircle2, Clock, Loader2 } from 'lucide-react';
import type { ClusterState } from './useClusterState';
import { TaskDagPanel } from './TaskDagPanel';
import { TaskDetailPanel } from './TaskDetailPanel';

export function ClusterView({ state }: { state: ClusterState }) {
  const {
    requirements, setRequirements,
    tasks, progress, creating, createCluster,
    selectedTaskId, setSelectedTaskId,
    taskDetails, setTaskDetails,
    loadingTaskDetails, handleTaskClick,
    setViewMode, loadGroups,
  } = state;

  return (
    <div className="h-full overflow-y-auto p-6">
      <div className="max-w-4xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-lg font-semibold text-[var(--color-text-primary)]">多智能体集群</h1>
            <p className="text-xs text-[var(--color-text-muted)] mt-0.5">协作式智能体流水线：规划 → 研究 → 执行 → 审计</p>
          </div>
          <button
            onClick={() => { setViewMode('groups'); loadGroups(); }}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs bg-[var(--color-bg-surface-1)] border border-[var(--color-border-subtle)] text-[var(--color-text-secondary)] rounded-xl hover:border-[var(--color-accent)]/30 transition-all duration-200"
          >
            <Network size={12} />
            智能体群组
          </button>
        </div>

        {/* Input */}
        <div className="p-4 bg-[var(--color-bg-surface-1)] border border-[var(--color-border-subtle)] rounded-2xl space-y-3">
          <textarea
            value={requirements}
            onChange={(e) => setRequirements(e.target.value)}
              placeholder="描述你想要构建的内容..."
            rows={3}
            className="w-full px-3 py-2 bg-[var(--color-bg-surface-2)] border border-[var(--color-border-subtle)] rounded-xl text-xs text-[var(--color-text-primary)] placeholder:text-[var(--color-text-muted)] focus:outline-none focus:border-[var(--color-accent)]/50 resize-none transition-all duration-200"
          />
          <div className="flex justify-end">
            <button
              onClick={createCluster}
              disabled={!requirements.trim() || creating}
              className="flex items-center gap-1.5 px-4 py-2 text-xs bg-[var(--color-accent)] text-white rounded-xl hover:bg-[var(--color-accent-hover)] disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 active:scale-[0.97]"
            >
              {creating ? <Loader2 size={12} className="animate-spin" /> : <Play size={12} />}
              {creating ? '创建中...' : '创建集群'}
            </button>
          </div>
        </div>

        {/* Progress */}
        {progress.total > 0 && (
          <div className="p-4 bg-[var(--color-bg-surface-1)] border border-[var(--color-border-subtle)] rounded-2xl">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs text-[var(--color-text-secondary)]">进度</span>
              <span className="text-xs font-medium text-[var(--color-accent)]">{progress.progress_pct}%</span>
            </div>
            <div className="h-2 bg-white/[0.06] rounded-full overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-[var(--color-accent)] to-[var(--color-accent-hover)] rounded-full transition-all duration-500"
                style={{ width: `${progress.progress_pct}%` }}
              />
            </div>
            <div className="flex items-center gap-4 mt-2 text-[10px] text-[var(--color-text-muted)]">
              <span className="flex items-center gap-1"><CheckCircle2 size={10} className="text-[var(--color-success)]" /> {progress.completed} 已完成</span>
              <span className="flex items-center gap-1"><Loader2 size={10} className="text-[var(--color-accent)]" /> {progress.running} 运行中</span>
              <span className="flex items-center gap-1"><Clock size={10} /> {progress.pending} 等待中</span>
            </div>
          </div>
        )}

        {/* Task DAG */}
        {tasks.length > 0 && (
          <TaskDagPanel tasks={tasks} selectedTaskId={selectedTaskId} onTaskClick={handleTaskClick} />
        )}

        {/* Task Detail Panel */}
        {selectedTaskId && (
          <TaskDetailPanel
            taskDetails={taskDetails}
            loading={loadingTaskDetails}
            onClose={() => { setSelectedTaskId(null); setTaskDetails(null); }}
          />
        )}

        {/* Empty State */}
        {tasks.length === 0 && (
          <div className="text-center py-12">
            <Network size={40} className="mx-auto text-[var(--color-text-muted)]/30" />
            <p className="text-sm text-[var(--color-text-muted)] mt-3">暂无活跃集群</p>
            <p className="text-xs text-[var(--color-text-muted)]/60 mt-1">在上方描述你的需求以创建一个</p>
          </div>
        )}
      </div>
    </div>
  );
}
