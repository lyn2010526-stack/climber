import { useState, useMemo } from 'react';
import { Bot, Play, Pause, Trash2, Plus, Database } from 'lucide-react';
import {
  IOSPage,
  IOSListGroup,
  IOSListItem,
  IOSSegmentedControl,
  IOSSearchBar,
  IOSFab,
  IOSBadge,
  IOSConfirmDialog,
  toast,
} from '../components/ios';
import { cn } from '../lib/utils';

type AgentStatus = 'running' | 'paused' | 'error';

interface Agent {
  id: string;
  name: string;
  description: string;
  status: AgentStatus;
}

const initialAgents: Agent[] = [
  { id: '1', name: '代码助手', description: '帮助编写和审查代码', status: 'running' },
  { id: '2', name: '数据分析师', description: '执行数据查询和分析任务', status: 'running' },
  { id: '3', name: '文档生成器', description: '自动生成项目文档', status: 'paused' },
  { id: '4', name: 'API 测试员', description: '测试接口可用性和性能', status: 'error' },
  { id: '5', name: '通用助手', description: '处理多种通用任务', status: 'running' },
];

const statusBadgeVariant: Record<AgentStatus, 'success' | 'warning' | 'error'> = {
  running: 'success',
  paused: 'warning',
  error: 'error',
};

const statusLabel: Record<AgentStatus, string> = {
  running: '运行中',
  paused: '已暂停',
  error: '错误',
};

const statusFilters = [
  { value: 'all', label: '全部' },
  { value: 'running', label: '运行中' },
  { value: 'paused', label: '已暂停' },
  { value: 'error', label: '错误' },
];

export default function AgentsPageIOS() {
  const [agents, setAgents] = useState<Agent[]>(initialAgents);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [deleteTarget, setDeleteTarget] = useState<Agent | null>(null);

  const filteredAgents = useMemo(() => {
    return agents.filter((agent) => {
      const matchesSearch =
        agent.name.toLowerCase().includes(search.toLowerCase()) ||
        agent.description.toLowerCase().includes(search.toLowerCase());
      const matchesStatus = statusFilter === 'all' || agent.status === statusFilter;
      return matchesSearch && matchesStatus;
    });
  }, [agents, search, statusFilter]);

  const stats = useMemo(() => {
    const total = agents.length;
    const running = agents.filter((a) => a.status === 'running').length;
    const paused = agents.filter((a) => a.status === 'paused').length;
    return { total, running, paused };
  }, [agents]);

  function toggleStatus(agent: Agent) {
    const newStatus: AgentStatus = agent.status === 'running' ? 'paused' : 'running';
    setAgents((prev) =>
      prev.map((a) => (a.id === agent.id ? { ...a, status: newStatus } : a))
    );
    toast.success(`${agent.name} 已${newStatus === 'running' ? '启动' : '暂停'}`);
  }

  function confirmDelete() {
    if (!deleteTarget) return;
    setAgents((prev) => prev.filter((a) => a.id !== deleteTarget.id));
    toast.success(`${deleteTarget.name} 已删除`);
    setDeleteTarget(null);
  }

  return (
    <IOSPage className="flex flex-col gap-5 pb-24">
      <div className="px-4 pt-2">
        <h1 className="ios-title-1">Agent 管理</h1>
        <p className="ios-subhead text-[var(--color-text-muted)] mt-1">
          管理和监控所有 AI Agent 的运行状态
        </p>
      </div>

      <div className="px-4 flex gap-3">
        <div className="ios-card flex-1 p-4">
          <p className="ios-title-2">{stats.total}</p>
          <p className="ios-caption text-[var(--color-text-muted)]">总 Agent</p>
        </div>
        <div className="ios-card flex-1 p-4">
          <p className="ios-title-2 text-[var(--color-success)]">{stats.running}</p>
          <p className="ios-caption text-[var(--color-text-muted)]">运行中</p>
        </div>
        <div className="ios-card flex-1 p-4">
          <p className="ios-title-2 text-[var(--color-warning)]">{stats.paused}</p>
          <p className="ios-caption text-[var(--color-text-muted)]">已暂停</p>
        </div>
      </div>

      <div className="px-4">
        <IOSSearchBar
          value={search}
          onChange={setSearch}
          placeholder="搜索 Agent..."
        />
      </div>

      <div className="px-4">
        <IOSSegmentedControl
          options={statusFilters}
          value={statusFilter}
          onChange={setStatusFilter}
        />
      </div>

      {filteredAgents.length === 0 ? (
        <div className="ios-empty-state flex flex-col items-center justify-center py-16">
          <Database size={48} className="text-[var(--color-text-muted)] mb-3" />
          <p className="ios-body text-[var(--color-text-muted)]">未找到匹配的 Agent</p>
        </div>
      ) : (
        <IOSListGroup>
          {filteredAgents.map((agent) => (
            <IOSListItem
              key={agent.id}
              icon={<Bot size={18} className="text-white" />}
              iconBg="var(--color-accent)"
              title={agent.name}
              showChevron={false}
              detail={
                <div className="flex flex-col items-end gap-1.5">
                  <span className="ios-caption text-[var(--color-text-muted)]">
                    {agent.description}
                  </span>
                  <div className="flex items-center gap-2">
                    <IOSBadge variant={statusBadgeVariant[agent.status]}>
                      {statusLabel[agent.status]}
                    </IOSBadge>
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        toggleStatus(agent);
                      }}
                      className="p-1.5 rounded-full bg-[var(--color-bg-surface-2)] text-[var(--color-text-primary)] active:bg-[var(--color-bg-surface-3)] transition-colors"
                    >
                      {agent.status === 'running' ? (
                        <Pause size={14} />
                      ) : (
                        <Play size={14} />
                      )}
                    </button>
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        setDeleteTarget(agent);
                      }}
                      className="p-1.5 rounded-full bg-[var(--color-bg-surface-2)] text-[var(--color-error)] active:bg-[var(--color-error-subtle)] transition-colors"
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                </div>
              }
            />
          ))}
        </IOSListGroup>
      )}

      <IOSFab icon={<Plus size={20} />} label="创建 Agent" onClick={() => {}} />

      <IOSConfirmDialog
        open={deleteTarget !== null}
        onOpenChange={(open) => {
          if (!open) setDeleteTarget(null);
        }}
        title="删除 Agent"
        description={`确定要删除「${deleteTarget?.name ?? ''}」吗？此操作不可撤销。`}
        confirmText="删除"
        cancelText="取消"
        danger
        onConfirm={confirmDelete}
      />
    </IOSPage>
  );
}
