import { useState, useCallback } from 'react';
import { Play, Pause, Square, Loader2, ChevronDown, ChevronUp, Shield, Users } from 'lucide-react';

interface TaskInputProps {
  onStart: (task?: string, maxRounds?: number, options?: TaskOptions) => void;
  onPause: () => void;
  onStop: () => void;
  status: 'idle' | 'running' | 'paused';
  disabled?: boolean;
  availableTasks?: Array<{ id: string; description: string }>;
}

export interface TaskOptions {
  processType?: 'sequential' | 'hierarchical' | 'group_chat';
  context?: string[];
  guardrails?: Array<{ name: string; description: string }>;
  humanReviewRequired?: boolean;
}

type ProcessType = 'sequential' | 'hierarchical' | 'group_chat';
type Guardrail = { name: string; description: string };

export function TaskInput({ onStart, onPause, onStop, status, disabled, availableTasks = [] }: TaskInputProps) {
  const [task, setTask] = useState('');
  const [maxRounds, setMaxRounds] = useState(5);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [processType, setProcessType] = useState<ProcessType | undefined>('sequential');
  const [selectedContext, setSelectedContext] = useState<string[]>([]);
  const [guardrails, setGuardrails] = useState<Guardrail[]>([]);
  const [guardrailName, setGuardrailName] = useState('');
  const [guardrailDesc, setGuardrailDesc] = useState('');
  const [humanReviewRequired, setHumanReviewRequired] = useState(false);

  const handleStart = useCallback(() => {
    if (!task.trim() || disabled) return;
    const options = {
      processType: processType || undefined,
      context: selectedContext,
      guardrails: guardrails.length ? guardrails : undefined,
      humanReviewRequired,
    } as TaskOptions;
    onStart(task.trim(), maxRounds, options);
    setTask('');
    setGuardrails([]);
    setSelectedContext([]);
    setHumanReviewRequired(false);
  }, [task, maxRounds, processType, selectedContext, guardrails, humanReviewRequired, onStart, disabled]);

  const addGuardrail = useCallback(() => {
    if (!guardrailName.trim()) return;
    setGuardrails(prev => [...prev, { name: guardrailName.trim(), description: guardrailDesc.trim() }]);
    setGuardrailName('');
    setGuardrailDesc('');
  }, [guardrailName, guardrailDesc]);

  const removeGuardrail = useCallback((index: number) => {
    setGuardrails(prev => (prev || []).filter((_, i) => i !== index));
  }, []);

  const toggleContextTask = useCallback((taskId: string) => {
    setSelectedContext(prev =>
      prev.includes(taskId) ? prev.filter(id => id !== taskId) : [...prev, taskId]
    );
  }, []);

  return (
    <div className="border-t border-[var(--color-border-subtle)] bg-[var(--color-bg-surface)]/30 p-3">
      {status === 'idle' ? (
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <input
              type="text"
              value={task}
              onChange={(e) => setTask(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleStart()}
              placeholder="输入任务描述，AI 将自动协作完成..."
               className="flex-1 px-3 py-2 bg-[var(--color-bg-surface-elevated)] border border-[var(--color-border-subtle)] rounded-lg text-xs text-[var(--color-text-primary)] placeholder:text-[var(--color-text-muted)] focus:outline-none focus:border-[var(--color-accent)]/50"
              disabled={disabled}
            />
            <button
              onClick={() => handleStart()}
              disabled={!task.trim() || disabled}
              className="px-3 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-1.5 text-xs"
            >
              <Play size={12} />
              Start
            </button>
          </div>

          <div className="flex items-center gap-2">
             <label className="text-[10px] text-[var(--color-text-muted)]">最大轮次:</label>
            <input
              type="number"
              value={maxRounds}
              onChange={(e) => setMaxRounds(Math.max(1, Math.min(20, parseInt(e.target.value) || 5)))}
              min={1}
              max={20}
               className="w-16 px-2 py-1 bg-[var(--color-bg-surface-elevated)] border border-[var(--color-border-subtle)] rounded text-[10px] text-[var(--color-text-primary)] focus:outline-none focus:border-[var(--color-accent)]/50"
            />
            <button
              type="button"
              onClick={() => setShowAdvanced(prev => !prev)}
               className="ml-auto flex items-center gap-1 text-[10px] text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)] transition-colors"
            >
              {showAdvanced ? <ChevronUp size={10} /> : <ChevronDown size={10} />}
              高级设置
            </button>
          </div>

          {showAdvanced && (
            <div className="space-y-3 pt-2 border-t border-[var(--color-border-subtle)]/50">
              {/* Process Type */}
              <div className="space-y-1">
                <label className="text-[10px] text-[var(--color-text-muted)]">执行流程</label>
                <select
                  value={processType}
                  onChange={(e) => setProcessType(e.target.value as ProcessType)}
                   className="w-full px-2 py-1.5 bg-[var(--color-bg-surface-elevated)] border border-[var(--color-border-subtle)] rounded text-[10px] text-[var(--color-text-primary)] focus:outline-none focus:border-[var(--color-accent)]/50"
                >
                  <option value="sequential">顺序执行（Sequential）</option>
                  <option value="hierarchical">分层管理（Hierarchical）</option>
                  <option value="group_chat">群组讨论（Group Chat）</option>
                </select>
                <p className="text-[9px] text-[var(--color-text-muted)]">
                  {processType === 'sequential' && '任务按顺序执行，每个任务获取前一个任务的输出'}
                  {processType === 'hierarchical' && 'Manager 规划子任务并分配给 Worker，最终验证输出'}
                  {processType === 'group_chat' && '多 Agent 轮询讨论，基于共识结束'}
                </p>
              </div>

              {/* Context Tasks */}
              {availableTasks.length > 0 && (
                <div className="space-y-1">
                  <label className="text-[10px] text-[var(--color-text-muted)] flex items-center gap-1">
                    <Users size={10} />
                    依赖任务（Context）
                  </label>
                  <div className="max-h-24 overflow-y-auto space-y-1">
                    {availableTasks.map(t => (
                      <label key={t.id} className="flex items-center gap-2 p-1.5 bg-[var(--color-bg-surface-elevated)]/30 rounded cursor-pointer hover:bg-[var(--color-bg-surface-elevated)]/50">
                        <input
                          type="checkbox"
                          checked={selectedContext.includes(t.id)}
                          onChange={() => toggleContextTask(t.id)}
                          className="rounded border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-elevated)] text-blue-600 focus:ring-blue-500"
                        />
                        <span className="text-[10px] text-[var(--color-text-secondary)] truncate">{t.description.slice(0, 50)}</span>
                      </label>
                    ))}
                  </div>
                </div>
              )}

              {/* Guardrails */}
              <div className="space-y-1">
                <label className="text-[10px] text-[var(--color-text-muted)] flex items-center gap-1">
                  <Shield size={10} />
                  输出校验（Guardrails）
                </label>
                <div className="flex gap-1">
                   <input
                     type="text"
                     value={guardrailName}
                     onChange={(e) => setGuardrailName(e.target.value)}
                     placeholder="校验名称"
                     className="flex-1 px-2 py-1 bg-[var(--color-bg-surface-elevated)] border border-[var(--color-border-subtle)] rounded text-[10px] text-[var(--color-text-primary)] focus:outline-none focus:border-[var(--color-accent)]/50"
                   />
                   <input
                     type="text"
                     value={guardrailDesc}
                     onChange={(e) => setGuardrailDesc(e.target.value)}
                     placeholder="校验描述"
                     className="flex-1 px-2 py-1 bg-[var(--color-bg-surface-elevated)] border border-[var(--color-border-subtle)] rounded text-[10px] text-[var(--color-text-primary)] focus:outline-none focus:border-[var(--color-accent)]/50"
                   />
                  <button
                    type="button"
                    onClick={addGuardrail}
                    disabled={!guardrailName.trim()}
                    className="px-2 py-1 bg-blue-600 text-white rounded text-[10px] disabled:opacity-50"
                  >
                    添加
                  </button>
                </div>
                {guardrails.length > 0 && (
                  <div className="space-y-1 mt-1">
                    {guardrails.map((g, i) => (
                      <div key={i} className="flex items-center justify-between p-1.5 bg-[var(--color-bg-surface-elevated)]/30 rounded">
                        <div className="flex-1 min-w-0">
                          <p className="text-[10px] text-[var(--color-text-primary)]">{g.name}</p>
                          {g.description && <p className="text-[9px] text-[var(--color-text-muted)] truncate">{g.description}</p>}
                        </div>
                        <button
                          type="button"
                          onClick={() => removeGuardrail(i)}
                          className="ml-2 text-[10px] text-red-400 hover:text-red-300"
                        >
                          移除
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Human-in-the-loop */}
              <label className="flex items-center gap-2 text-[10px] text-[var(--color-text-secondary)] cursor-pointer">
                <input
                  type="checkbox"
                  checked={humanReviewRequired}
                  onChange={(e) => setHumanReviewRequired(e.target.checked)}
                  className="rounded border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-elevated)] text-blue-600 focus:ring-blue-500"
                />
                需要人工审批（Human-in-the-loop）
              </label>
            </div>
          )}

          <div className="flex items-center gap-2">
            <span className="text-[10px] text-[var(--color-text-muted)] ml-auto">
              点击开始后，AI 将自动循环执行直到完成
            </span>
          </div>
        </div>
      ) : (
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1.5">
            <Loader2 size={12} className="text-blue-400 animate-spin" />
            <span className="text-xs text-blue-400">
              {status === 'running' ? '协作进行中...' : '已暂停'}
            </span>
          </div>
          <div className="ml-auto flex items-center gap-1.5">
            {status === 'running' ? (
              <button
                onClick={onPause}
                className="p-1.5 bg-amber-500/10 text-amber-400 rounded hover:bg-amber-500/20 transition-colors"
              >
                <Pause size={12} />
              </button>
            ) : (
              <button
                onClick={() => {}}
                className="p-1.5 bg-green-500/10 text-green-400 rounded hover:bg-green-500/20 transition-colors"
              >
                <Play size={12} />
              </button>
            )}
            <button
              onClick={onStop}
              className="p-1.5 bg-red-500/10 text-red-400 rounded hover:bg-red-500/20 transition-colors"
            >
              <Square size={12} />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
