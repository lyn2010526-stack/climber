import { useState, useCallback } from 'react';
import {
  Network, Play, CheckCircle2, Clock, Loader2,
  Bot, Shield, Search, Wrench, Plus, ArrowLeft, Hash, Users,
} from 'lucide-react';
import { GroupRoom } from '../components/group/GroupRoom';
import { CollaborationConsole } from '../components/collaboration/CollaborationConsole';
import { api } from '../api';

interface ClusterTask {
  id: string;
  role: string;
  description: string;
  status: string;
  dependencies: string[];
  process_type?: string;
  guardrails?: Array<{ name: string; description: string }>;
  final_output?: string;
  context?: string[];
  human_review_required?: boolean;
}

interface AgentGroup {
  id: string;
  name: string;
  description: string;
  status: string;
  member_count: number;
  created_at: string;
  process_type?: string;
  manager_agent_id?: string;
  manager_llm?: string;
  members?: Array<{
    id: string;
    agent_id: string;
    role: string;
    status: string;
    is_worker: boolean;
    model_provider?: string;
    model_id?: string;
    tools?: string[];
    message_count?: number;
    last_active?: string;
  }>;
}

const ROLE_ICONS: Record<string, any> = {
  planner: Bot,
  researcher: Search,
  executor: Wrench,
  auditor: Shield,
};

const ROLE_COLORS: Record<string, string> = {
  planner: 'bg-blue-600/10 text-blue-400 border-blue-500/20',
  researcher: 'bg-purple-500/10 text-purple-400 border-purple-500/20',
  executor: 'bg-green-500/10 text-green-400 border-green-500/20',
  auditor: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
};

const STATUS_ICONS: Record<string, typeof Clock> = {
  pending: Clock,
  running: Loader2,
  completed: CheckCircle2,
  failed: Clock,
};

const STATUS_COLORS: Record<string, string> = {
  pending: 'text-[var(--color-text-muted)]',
  running: 'text-blue-400',
  completed: 'text-green-400',
  failed: 'text-red-400',
};

type ViewMode = 'cluster' | 'groups' | 'group-room' | 'collab-console';

export function ClusterPage() {
  const [viewMode, setViewMode] = useState<ViewMode>('cluster');
  const [activeGroupId, setActiveGroupId] = useState<string | null>(null);
  const [managingGroupId, setManagingGroupId] = useState<string | null>(null);
  const [members, setMembers] = useState<any[]>([]);
  const [showAddMember, setShowAddMember] = useState(false);
  const [memberForm, setMemberForm] = useState({ agent_id: '', role: 'participant', model_provider: '', model_id: '', tools: [] as string[] });
  const [loadingMembers, setLoadingMembers] = useState(false);
  const [availableTasks, setAvailableTasks] = useState<Array<{ id: string; description: string }>>([]);

  // Cluster state
  const [requirements, setRequirements] = useState('');
  const [tasks, setTasks] = useState<ClusterTask[]>([]);
  const [progress, setProgress] = useState({ total: 0, completed: 0, failed: 0, running: 0, pending: 0, progress_pct: 0 });
  const [creating, setCreating] = useState(false);
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null);
  const [taskDetails, setTaskDetails] = useState<any>(null);
  const [loadingTaskDetails, setLoadingTaskDetails] = useState(false);

  // Groups state
  const [groups, setGroups] = useState<AgentGroup[]>([]);
  const [showCreateGroup, setShowCreateGroup] = useState(false);
  const [groupName, setGroupName] = useState('');
  const [groupTopic, setGroupTopic] = useState('');
  const [useTemplate, setUseTemplate] = useState(false);

  const loadTaskDetails = useCallback(async (taskId: string) => {
    setLoadingTaskDetails(true);
    try {
      const data = await api.getTask(taskId);
        setTaskDetails(data);
    } catch {
      // skip
    }
    setLoadingTaskDetails(false);
  }, []);

  const handleTaskClick = useCallback((taskId: string) => {
    setSelectedTaskId(prev => {
      const newVal = prev === taskId ? null : taskId;
      if (newVal !== null && newVal !== prev) {
        loadTaskDetails(taskId);
      }
      return newVal;
    });
  }, [loadTaskDetails]);

  const createCluster = async () => {
    if (!requirements.trim()) return;
    setCreating(true);
    try {
      const res = await api.createCluster(requirements);
      if (res.plan) {
          const planTasks = res.plan.map((p: any, idx: number) => ({
            id: p.id || String(idx + 1),
            role: p.role || 'executor',
            description: p.description || p.task || '',
            status: p.status || 'pending',
            dependencies: p.dependencies || [],
            process_type: p.process_type || 'sequential',
            guardrails: p.guardrails || [],
            context: p.context || [],
            human_review_required: p.human_review_required || false,
          }));
          setTasks(planTasks);
        } else {
          // Fallback: create a group with the requirements as topic
          const groupRes = await api.createGroup({ name: requirements.slice(0, 50), topic: requirements } as any);
          if (groupRes.id) {
            setTasks([{
              id: groupRes.id,
              role: 'planner',
              description: `群组已创建：${requirements.slice(0, 80)}`,
              status: 'completed',
              dependencies: [],
              process_type: 'sequential',
              guardrails: [],
              context: [],
              human_review_required: false,
            }]);
            setProgress({ total: 1, completed: 1, failed: 0, running: 0, pending: 0, progress_pct: 100 });
          }
        }
        if (res.progress) {
          setProgress(res.progress);
        }
    } catch {
      // Show error state
      setTasks([{
        id: 'error',
        role: 'planner',
         description: '创建集群失败，请重试。',
        status: 'failed',
        dependencies: [],
        process_type: 'sequential',
        guardrails: [],
        context: [],
        human_review_required: false,
      }]);
      setProgress({ total: 1, completed: 0, failed: 1, running: 0, pending: 0, progress_pct: 0 });
    }
    setCreating(false);
  };

  const loadGroups = useCallback(async () => {
    try {
      const res = await api.listGroups();
        setGroups(res);
    } catch { /* skip */ }
  }, []);

  const createGroup = async () => {
    if (!groupName.trim()) return;
    try {
      const res = await api.createGroup({
          name: groupName,
          topic: groupTopic,
          template: useTemplate ? 'default' : undefined,
        } as any);
        if (res.id) {
        setGroupName('');
        setGroupTopic('');
        setUseTemplate(false);
        setShowCreateGroup(false);
        loadGroups();
      }
    } catch { /* skip */ }
  };

  const openGroup = async (groupId: string, mode: 'chat' | 'collab' = 'chat') => {
    setActiveGroupId(groupId);
    setViewMode(mode === 'collab' ? 'collab-console' : 'group-room');

    // Fetch available tasks for context selection
    if (mode === 'collab') {
      // Task list API not available; use empty list
      setAvailableTasks([]);
    }
  };

  const leaveGroup = () => {
    setActiveGroupId(null);
    setManagingGroupId(null);
    setViewMode('groups');
    loadGroups();
  };

  const openManageMembers = async (groupId: string) => {
    setManagingGroupId(groupId);
    setLoadingMembers(true);
    // Members API not available; use empty list
    setMembers([]);
    setLoadingMembers(false);
  };

  const addMember = async () => {
    if (!managingGroupId || !memberForm.agent_id.trim()) return;
    try {
      await api.addGroupMember(managingGroupId, memberForm);
      setMemberForm({ agent_id: '', role: 'participant', model_provider: '', model_id: '', tools: [] });
      setShowAddMember(false);
      openManageMembers(managingGroupId);
    } catch {
      // skip
    }
  };

  const removeMember = async (memberId: string) => {
    if (!managingGroupId) return;
    try {
      await api.removeGroupMember(managingGroupId, memberId);
      openManageMembers(managingGroupId);
    } catch {
      // skip
    }
  };

  // Collaboration Console View (new auto-collab mode)
  if (viewMode === 'collab-console' && activeGroupId) {
    return (
      <div className="h-full flex flex-col">
        <div className="h-10 flex items-center px-4 border-b border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-1)]">
          <button
            onClick={leaveGroup}
            className="flex items-center gap-1 text-xs text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] transition-colors"
          >
            <ArrowLeft size={14} />
            返回群组列表
          </button>
           <span className="ml-3 text-xs font-medium text-[var(--color-text-primary)]">自动协作</span>
        </div>
        <div className="flex-1 min-h-0">
          <CollaborationConsole groupId={activeGroupId} availableTasks={availableTasks} />
        </div>
      </div>
    );
  }

  // Group Room View
  if (viewMode === 'group-room' && activeGroupId) {
    return (
      <div className="h-full flex flex-col">
        <div className="h-10 flex items-center px-4 border-b border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-1)]">
          <button
            onClick={leaveGroup}
            className="flex items-center gap-1 text-xs text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] transition-colors"
          >
            <ArrowLeft size={14} />
            返回群组列表
          </button>
          <button
            onClick={() => setViewMode('collab-console')}
            className="ml-3 flex items-center gap-1 text-xs text-[var(--color-accent)] hover:text-[var(--color-accent-hover)] transition-colors"
          >
            <Wrench size={12} />
            自动协作
          </button>
        </div>
        <div className="flex-1 min-h-0">
          <GroupRoom groupId={activeGroupId} onLeave={leaveGroup} />
        </div>
      </div>
    );
  }

  // Groups List View
  if (viewMode === 'groups') {
    return (
      <div className="h-full overflow-y-auto p-6">
        <div className="max-w-4xl mx-auto space-y-6">
          {/* Header */}
          <div className="flex items-center justify-between">
            <div>
            <h1 className="text-lg font-semibold text-[var(--color-text-primary)]">智能体群组</h1>
            <p className="text-xs text-[var(--color-text-muted)] mt-0.5">多智能体协作空间</p>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setViewMode('cluster')}
                  className="px-3 py-1.5 text-xs text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] transition-colors"
              >
                集群视图
              </button>
              <button
                onClick={() => setShowCreateGroup(true)}
                className="flex items-center gap-1 px-3 py-1.5 text-xs bg-[var(--color-accent)] text-white rounded-xl hover:bg-[var(--color-accent-hover)] transition-all duration-200 active:scale-[0.97]"
              >
                <Plus size={12} />
                新建群组
              </button>
            </div>
          </div>

          {/* Create Group Form */}
          {showCreateGroup && (
            <div className="p-4 bg-[var(--color-bg-surface-1)] border border-[var(--color-border-subtle)] rounded-2xl space-y-3">
              <input
                type="text"
                value={groupName}
                onChange={(e) => setGroupName(e.target.value)}
                placeholder="群组名称..."
                className="w-full px-3 py-2 bg-[var(--color-bg-surface-2)] border border-[var(--color-border-subtle)] rounded-xl text-xs text-[var(--color-text-primary)] placeholder:text-[var(--color-text-muted)] focus:outline-none focus:border-[var(--color-accent)]/50 transition-all duration-200"
              />
              <input
                type="text"
                value={groupTopic}
                onChange={(e) => setGroupTopic(e.target.value)}
                placeholder="讨论主题（可选）..."
                className="w-full px-3 py-2 bg-[var(--color-bg-surface-2)] border border-[var(--color-border-subtle)] rounded-xl text-xs text-[var(--color-text-primary)] placeholder:text-[var(--color-text-muted)] focus:outline-none focus:border-[var(--color-accent)]/50 transition-all duration-200"
              />
              <label className="flex items-center gap-2 text-xs text-[var(--color-text-secondary)] cursor-pointer">
                <input
                  type="checkbox"
                  checked={useTemplate}
                  onChange={(e) => setUseTemplate(e.target.checked)}
                  className="rounded border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-2)] text-[var(--color-accent)] focus:ring-[var(--color-accent)]/50"
                />
                快速开始：自动添加 Planner + Executor + Reviewer 默认成员
              </label>
              <div className="flex justify-end gap-2">
                <button
                  onClick={() => { setShowCreateGroup(false); setUseTemplate(false); }}
                className="px-3 py-1.5 text-xs text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] transition-colors"
                >
                   取消
                </button>
                <button
                  onClick={createGroup}
                  disabled={!groupName.trim()}
                  className="px-3 py-1.5 text-xs bg-[var(--color-accent)] text-white rounded-xl hover:bg-[var(--color-accent-hover)] disabled:opacity-50 transition-all duration-200"
                >
                   创建
                </button>
              </div>
            </div>
          )}

          {/* Member Management Panel */}
          {managingGroupId && (
            <div className="p-4 bg-[var(--color-bg-surface-1)] border border-[var(--color-border-subtle)] rounded-2xl space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-medium text-[var(--color-text-primary)]">群组成员</h3>
                <button
                  onClick={() => setManagingGroupId(null)}
                  className="text-xs text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] transition-colors"
                >
                  关闭
                </button>
              </div>

              {loadingMembers ? (
                <div className="text-xs text-[var(--color-text-muted)]">加载中...</div>
              ) : (
                <>
                  {/* Add Member Form */}
                  {showAddMember ? (
                    <div className="p-3 bg-[var(--color-bg-surface-2)] rounded-xl space-y-2">
                      <input
                        type="text"
                        value={memberForm.agent_id}
                        onChange={(e) => setMemberForm({ ...memberForm, agent_id: e.target.value })}
                        placeholder="Agent ID"
                        className="w-full px-2 py-1.5 bg-[var(--color-bg-surface-2)] border border-[var(--color-border-subtle)] rounded-xl text-xs text-[var(--color-text-primary)]"
                      />
                      <select
                        value={memberForm.role}
                        onChange={(e) => setMemberForm({ ...memberForm, role: e.target.value })}
                        className="w-full px-2 py-1.5 bg-[var(--color-bg-surface-2)] border border-[var(--color-border-subtle)] rounded-xl text-xs text-[var(--color-text-primary)]"
                      >
                        <option value="planner">Planner</option>
                        <option value="researcher">Researcher</option>
                        <option value="executor">Executor</option>
                        <option value="auditor">Auditor</option>
                        <option value="participant">Participant</option>
                        <option value="observer">Observer</option>
                      </select>
                      <div className="flex justify-end gap-2">
                        <button
                          onClick={() => setShowAddMember(false)}
                          className="px-2 py-1 text-xs text-[var(--color-text-muted)]"
                        >
                          取消
                        </button>
                        <button
                          onClick={addMember}
                          disabled={!memberForm.agent_id.trim()}
                          className="px-2 py-1 text-xs bg-[var(--color-accent)] text-white rounded-xl disabled:opacity-50 transition-all duration-200"
                        >
                          添加
                        </button>
                      </div>
                    </div>
                  ) : (
                    <button
                      onClick={() => setShowAddMember(true)}
                      className="flex items-center gap-1 px-3 py-1.5 text-xs text-[var(--color-accent)] hover:text-[var(--color-accent-hover)] transition-colors"
                    >
                      <Plus size={12} />
                      添加成员
                    </button>
                  )}

                  {/* Members List */}
                  <div className="space-y-2">
                    {members.map((member) => (
                      <div
                        key={member.id}
                        className="flex items-center justify-between p-2 bg-white/[0.02] border border-[var(--color-border-subtle)] rounded-xl"
                      >
                        <div>
                          <span className="text-xs text-[var(--color-text-primary)]">{member.agent_id || member.id}</span>
                          <span className="ml-2 text-[10px] px-2 py-0.5 rounded-full bg-[var(--color-accent)]/10 text-[var(--color-accent)] border border-[var(--color-accent)]/20">
                            {member.role}
                          </span>
                        </div>
                        <button
                          onClick={() => removeMember(member.id)}
                          className="text-[10px] text-[var(--color-error)] hover:text-red-300 transition-colors"
                        >
                          移除
                        </button>
                      </div>
                    ))}
                    {members.length === 0 && (
                      <p className="text-xs text-[var(--color-text-muted)] text-center py-2">暂无成员</p>
                    )}
                  </div>
                </>
              )}
            </div>
          )}

          {/* Groups List */}
          {groups.length === 0 ? (
            <div className="text-center py-12">
              <Network size={40} className="mx-auto text-[var(--color-text-muted)]/30" />
               <p className="text-sm text-[var(--color-text-muted)] mt-3">暂无群组</p>
               <p className="text-xs text-[var(--color-text-muted)]/60 mt-1">创建一个群组以开始多智能体协作</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {groups.map((group) => (
                <div
                  key={group.id}
                  className="p-4 bg-[var(--color-bg-surface-1)] border border-[var(--color-border-subtle)] rounded-2xl hover:border-[var(--color-accent)]/30 transition-all duration-200"
                >
                  <div className="flex items-center gap-2">
                    <Hash size={14} className="text-[var(--color-accent)]" />
                    <span className="text-sm font-medium text-[var(--color-text-primary)]">{group.name}</span>
                    <span className={`ml-auto px-2 py-0.5 text-[10px] rounded-full ${
                      group.status === 'active' ? 'bg-[var(--color-success)]/10 text-[var(--color-success)] border border-[var(--color-success)]/20' : 'bg-white/[0.03] text-[var(--color-text-muted)] border border-[var(--color-border-subtle)]'
                    }`}>
                      {group.status}
                    </span>
                  </div>
                  {group.description && (
                    <p className="text-[11px] text-[var(--color-text-muted)] mt-2 line-clamp-2">{group.description}</p>
                  )}
                  <div className="flex items-center gap-3 mt-3 text-[10px] text-[var(--color-text-muted)]">
                    <span>{group.member_count} 名成员</span>
                    <span>{new Date(group.created_at).toLocaleDateString()}</span>
                  </div>
                  <div className="flex items-center gap-2 mt-3 pt-3 border-t border-[var(--color-border-subtle)]">
                    <button
                      onClick={() => openGroup(group.id, 'chat')}
                      className="flex items-center gap-1 px-2 py-1 text-[10px] text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] bg-white/[0.03] border border-[var(--color-border-subtle)] rounded-xl hover:bg-white/[0.06] transition-all duration-200"
                    >
                      <Users size={10} />
                      Chat
                    </button>
                    <button
                      onClick={() => openGroup(group.id, 'collab')}
                      className="flex items-center gap-1 px-2 py-1 text-[10px] text-[var(--color-accent)] bg-[var(--color-accent)]/10 hover:bg-[var(--color-accent)]/20 border border-[var(--color-accent)]/20 rounded-xl transition-all duration-200"
                    >
                      <Wrench size={10} />
                      自动协作
                    </button>
                    <button
                      onClick={() => openManageMembers(group.id)}
                      className="flex items-center gap-1 px-2 py-1 text-[10px] text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] bg-white/[0.03] border border-[var(--color-border-subtle)] rounded-xl hover:bg-white/[0.06] transition-all duration-200"
                    >
                      <Users size={10} />
                      管理
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    );
  }

  // Default: Cluster View
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
          <div className="space-y-3">
            <h2 className="text-sm font-medium text-[var(--color-text-primary)]">执行计划</h2>
            <div className="relative">
              {/* Connection line */}
              <div className="absolute left-6 top-8 bottom-8 w-px bg-[var(--color-border-subtle)]" />

              {tasks.map((task) => {
                const Icon = ROLE_ICONS[task.role] || Bot;
                const statusIcon = STATUS_ICONS[task.status] || Clock;
                const StatusIcon = statusIcon;
                const isSelected = selectedTaskId === task.id;

                return (
                  <div key={task.id} className="relative flex items-start gap-4 py-3">
                    {/* Node circle */}
                    <div className={`relative z-10 w-12 h-12 rounded-2xl border flex items-center justify-center shrink-0 cursor-pointer transition-all duration-200 ${
                      task.status === 'completed' ? 'bg-[var(--color-success)]/10 border-[var(--color-success)]/20' :
                      task.status === 'running' ? 'bg-[var(--color-accent)]/10 border-[var(--color-accent)]/20' :
                      'bg-[var(--color-bg-surface-1)] border-[var(--color-border-subtle)]'
                    }`} onClick={() => handleTaskClick(task.id)}>
                      <Icon size={18} className={
                        task.status === 'completed' ? 'text-[var(--color-success)]' :
                        task.status === 'running' ? 'text-[var(--color-accent)]' :
                        'text-[var(--color-text-muted)]'
                      } />
                    </div>

                    {/* Card */}
                    <div className={`flex-1 p-3 rounded-2xl cursor-pointer transition-all duration-200 border ${
                      isSelected ? 'bg-[var(--color-accent)]/10 border-[var(--color-accent)]/30' : 'bg-[var(--color-bg-surface-1)] border-[var(--color-border-subtle)]'
                    }`} onClick={() => handleTaskClick(task.id)}>
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className={`px-2 py-0.5 rounded-lg text-[10px] font-medium border ${ROLE_COLORS[task.role] || ROLE_COLORS['planner']}`}>
                          {task.role}
                        </span>
                        <StatusIcon size={12} className={STATUS_COLORS[task.status]} />
                        <span className="text-[10px] text-[var(--color-text-muted)] capitalize">{task.status}</span>
                        {task.process_type && task.process_type !== 'sequential' && (
                          <span className="px-2 py-0.5 rounded-lg text-[9px] bg-[var(--color-accent-secondary)]/10 text-[var(--color-accent-secondary)] border border-[var(--color-accent-secondary)]/20">
                            {task.process_type}
                          </span>
                        )}
                        {task.human_review_required && (
                          <span className="px-2 py-0.5 rounded-lg text-[9px] bg-[var(--color-warning)]/10 text-[var(--color-warning)] border border-[var(--color-warning)]/20">
                            人工审批
                          </span>
                        )}
                      </div>
                      <p className="text-xs text-[var(--color-text-primary)] mt-1.5">{task.description}</p>
                      {task.dependencies.length > 0 && (
                         <p className="text-[10px] text-[var(--color-text-muted)] mt-1">依赖：{task.dependencies.join(', ')}</p>
                      )}
                      {task.guardrails && task.guardrails.length > 0 && (
                        <div className="flex items-center gap-1 mt-1.5">
                          <Shield size={10} className="text-[var(--color-text-muted)]" />
                          <span className="text-[10px] text-[var(--color-text-muted)]">{task.guardrails.length} 个校验规则</span>
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Task Detail Panel */}
        {selectedTaskId && (
          <div className="p-4 bg-[var(--color-bg-surface-1)] border border-[var(--color-border-subtle)] rounded-2xl space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-medium text-[var(--color-text-primary)]">任务详情</h3>
              <button
                onClick={() => { setSelectedTaskId(null); setTaskDetails(null); }}
                className="text-xs text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] transition-colors"
              >
                关闭
              </button>
            </div>
            {loadingTaskDetails ? (
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
