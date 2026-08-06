import { useState, useCallback } from 'react';
import {
  Network, Play, CheckCircle2, Clock, Loader2,
  Bot, Shield, Search, Wrench, Plus, ArrowLeft, Hash, Users, X,
} from 'lucide-react';
import { GroupRoom } from '../components/group/GroupRoom';
import { CollaborationConsole } from '../components/collaboration/CollaborationConsole';
import { api } from '../api';
import { PageHeader } from '../components/ui/PageHeader';
import { Card, CardContent } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import { Input } from '../components/ui/Input';
import { EmptyState } from '../components/ui/EmptyState';
import { SkeletonList } from '../components/ui/Skeleton';

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
  planner: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
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

function TaskCard({ task, isSelected, onClick, loading }: { task: ClusterTask; isSelected: boolean; onClick: () => void; loading: boolean }) {
  const StatusIcon = STATUS_ICONS[task.status] || Clock;
  const statusColor = STATUS_COLORS[task.status] || 'text-[var(--color-text-muted)]';

  return (
    <button
      onClick={onClick}
      className={`w-full text-left p-4 rounded-xl border transition-all duration-200 group ${
        isSelected
          ? 'bg-[var(--color-accent)]/5 border-[var(--color-accent)]/30'
          : 'bg-[var(--color-bg-surface-1)] border-[var(--color-border-subtle)] hover:border-[var(--color-accent)]/20 hover:bg-[var(--color-bg-surface-2)]'
      }`}
    >
      <div className="flex items-start gap-3">
        <div className={`p-2 rounded-lg ${task.status === 'completed' ? 'bg-[var(--color-success)]/10' : task.status === 'running' ? 'bg-blue-500/10' : 'bg-[var(--color-bg-surface-2)]'}`}>
          <StatusIcon size={16} className={`${statusColor} ${task.status === 'running' ? 'animate-spin' : ''}`} />
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm text-[var(--color-text-primary)] truncate font-medium">{task.description}</p>
          <div className="flex items-center gap-2 mt-2">
            <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium border ${ROLE_COLORS[task.role] || 'bg-[var(--color-bg-surface-2)] text-[var(--color-text-muted)] border-[var(--color-border-subtle)]'}`}>
              {task.role}
            </span>
            <span className={`text-[10px] font-medium ${statusColor}`}>{task.status}</span>
          </div>
        </div>
        {loading && <Loader2 size={14} className="text-[var(--color-accent)] animate-spin shrink-0 mt-1" />}
      </div>
    </button>
  );
}

function TaskDetailsPanel({ taskId, details, loading }: { taskId: string; details: any; loading: boolean }) {
  if (loading) {
    return (
      <Card variant="default">
        <CardContent className="p-6">
          <SkeletonList count={3} />
        </CardContent>
      </Card>
    );
  }

  if (!details) {
    return (
      <Card variant="default">
        <CardContent className="p-6 text-center">
          <p className="text-sm text-[var(--color-text-muted)]">点击任务查看详情</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card variant="default">
      <CardContent className="p-6">
        <h3 className="text-sm font-semibold text-[var(--color-text-primary)] mb-3">任务详情</h3>
        <div className="space-y-2 text-xs">
          <div className="flex justify-between">
            <span className="text-[var(--color-text-muted)]">ID</span>
            <span className="text-[var(--color-text-primary)] font-mono">{taskId}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-[var(--color-text-muted)]">状态</span>
            <span className="text-[var(--color-text-primary)]">{details.status || '-'}</span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function ProgressBar({ progress }: { progress: { total: number; completed: number; failed: number; running: number; pending: number; progress_pct: number } }) {
  const { total, completed, failed, running, progress_pct } = progress;

  return (
    <Card variant="default" className="mb-6">
      <CardContent className="p-4">
        <div className="flex items-center justify-between mb-3">
          <span className="text-xs text-[var(--color-text-muted)]">执行进度</span>
          <span className="text-sm font-semibold text-[var(--color-text-primary)]">{progress_pct}%</span>
        </div>
        <div className="w-full h-2 bg-[var(--color-bg-surface-3)] rounded-full overflow-hidden mb-3">
          <div
            className="h-full bg-[var(--color-accent)] rounded-full transition-all duration-500"
            style={{ width: `${progress_pct}%` }}
          />
        </div>
        <div className="flex items-center gap-4 text-xs text-[var(--color-text-muted)]">
          <span>总计 {total}</span>
          <span className="text-[var(--color-success)]">{completed} 完成</span>
          <span className="text-blue-400">{running} 运行中</span>
          <span className="text-[var(--color-error)]">{failed} 失败</span>
        </div>
      </CardContent>
    </Card>
  );
}

export function ClusterPage() {
  const [viewMode, setViewMode] = useState<ViewMode>('cluster');
  const [activeGroupId, setActiveGroupId] = useState<string | null>(null);
  const [managingGroupId, setManagingGroupId] = useState<string | null>(null);
  const [members, setMembers] = useState<any[]>([]);
  const [showAddMember, setShowAddMember] = useState(false);
  const [memberForm, setMemberForm] = useState({ agent_id: '', role: 'participant', model_provider: '', model_id: '', tools: [] as string[] });
  const [loadingMembers, setLoadingMembers] = useState(false);
  const [availableTasks, setAvailableTasks] = useState<Array<{ id: string; description: string }>>([]);

  const [requirements, setRequirements] = useState('');
  const [tasks, setTasks] = useState<ClusterTask[]>([]);
  const [progress, setProgress] = useState({ total: 0, completed: 0, failed: 0, running: 0, pending: 0, progress_pct: 0 });
  const [creating, setCreating] = useState(false);
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null);
  const [taskDetails, setTaskDetails] = useState<any>(null);
  const [loadingTaskDetails, setLoadingTaskDetails] = useState(false);

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
    } catch { /* skip */ }
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
    if (mode === 'collab') {
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
    } catch { /* skip */ }
  };

  const removeMember = async (memberId: string) => {
    if (!managingGroupId) return;
    try {
      await api.removeGroupMember(managingGroupId, memberId);
      openManageMembers(managingGroupId);
    } catch { /* skip */ }
  };

  if (viewMode === 'collab-console' && activeGroupId) {
    return (
      <div className="h-full flex flex-col">
        <div className="h-12 flex items-center px-4 border-b border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-1)] shrink-0">
          <button
            onClick={leaveGroup}
            className="flex items-center gap-1.5 text-xs text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] transition-colors"
          >
            <ArrowLeft size={14} />
            返回群组列表
          </button>
          <span className="ml-3 text-xs font-semibold text-[var(--color-text-primary)]">自动协作</span>
        </div>
        <div className="flex-1 min-h-0">
          <CollaborationConsole groupId={activeGroupId} availableTasks={availableTasks} />
        </div>
      </div>
    );
  }

  if (viewMode === 'group-room' && activeGroupId) {
    return (
      <div className="h-full flex flex-col">
        <div className="h-12 flex items-center px-4 border-b border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-1)] shrink-0">
          <button
            onClick={leaveGroup}
            className="flex items-center gap-1.5 text-xs text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] transition-colors"
          >
            <ArrowLeft size={14} />
            返回群组列表
          </button>
          <button
            onClick={() => setViewMode('collab-console')}
            className="ml-3 flex items-center gap-1.5 text-xs text-[var(--color-accent)] hover:text-[var(--color-accent-hover)] transition-colors"
          >
            <Wrench size={14} />
            自动协作
          </button>
        </div>
        <div className="flex-1 min-h-0">
          <GroupRoom groupId={activeGroupId} onLeave={leaveGroup} />
        </div>
      </div>
    );
  }

  if (viewMode === 'groups') {
    return (
      <div className="h-full overflow-y-auto page-transition">
        <div className="p-4 md:p-6 lg:p-8 max-w-4xl mx-auto">
          <PageHeader
            title="智能体群组"
            description="多智能体协作空间"
            icon={<Network size={20} />}
            actions={
              <div className="flex items-center gap-2">
                <Button variant="ghost" size="sm" onClick={() => setViewMode('cluster')}>
                  集群视图
                </Button>
                <Button variant="primary" size="sm" icon={<Plus size={14} />} onClick={() => setShowCreateGroup(true)}>
                  新建群组
                </Button>
              </div>
            }
          />

          {showCreateGroup && (
            <Card variant="default" className="mb-6">
              <CardContent className="p-5 space-y-3">
                <Input
                  value={groupName}
                  onChange={(e) => setGroupName(e.target.value)}
                  placeholder="群组名称..."
                />
                <Input
                  value={groupTopic}
                  onChange={(e) => setGroupTopic(e.target.value)}
                  placeholder="讨论主题（可选）..."
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
                <div className="flex justify-end gap-2 pt-1">
                  <Button variant="ghost" size="sm" onClick={() => { setShowCreateGroup(false); setUseTemplate(false); }}>
                    取消
                  </Button>
                  <Button variant="primary" size="sm" onClick={createGroup} disabled={!groupName.trim()}>
                    创建
                  </Button>
                </div>
              </CardContent>
            </Card>
          )}

          {managingGroupId && (
            <Card variant="default" className="mb-6">
              <CardContent className="p-5">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-sm font-semibold text-[var(--color-text-primary)]">群组成员</h3>
                  <Button variant="ghost" size="icon" onClick={() => setManagingGroupId(null)}>
                    <X size={16} />
                  </Button>
                </div>

                {loadingMembers ? (
                  <SkeletonList count={2} />
                ) : (
                  <>
                    {showAddMember ? (
                      <div className="p-4 bg-[var(--color-bg-surface-2)] rounded-xl space-y-3 mb-4">
                        <Input
                          value={memberForm.agent_id}
                          onChange={(e) => setMemberForm({ ...memberForm, agent_id: e.target.value })}
                          placeholder="Agent ID"
                        />
                        <select
                          value={memberForm.role}
                          onChange={(e) => setMemberForm({ ...memberForm, role: e.target.value })}
                          className="w-full px-3 py-2 bg-[var(--color-bg-surface-3)] border border-[var(--color-border-subtle)] rounded-xl text-xs text-[var(--color-text-primary)] focus:outline-none focus:border-[var(--color-accent)]/50"
                        >
                          <option value="planner">Planner</option>
                          <option value="researcher">Researcher</option>
                          <option value="executor">Executor</option>
                          <option value="auditor">Auditor</option>
                          <option value="participant">Participant</option>
                          <option value="observer">Observer</option>
                        </select>
                        <div className="flex justify-end gap-2">
                          <Button variant="ghost" size="sm" onClick={() => setShowAddMember(false)}>取消</Button>
                          <Button variant="primary" size="sm" onClick={addMember} disabled={!memberForm.agent_id.trim()}>添加</Button>
                        </div>
                      </div>
                    ) : (
                      <Button variant="outline" size="sm" icon={<Plus size={14} />} onClick={() => setShowAddMember(true)} className="mb-4">
                        添加成员
                      </Button>
                    )}

                    <div className="space-y-2">
                      {members.map((member) => (
                        <div key={member.id} className="flex items-center justify-between p-3 bg-[var(--color-bg-surface-2)] rounded-xl border border-[var(--color-border-subtle)]">
                          <div className="flex items-center gap-2">
                            <span className="text-xs text-[var(--color-text-primary)]">{member.agent_id || member.id}</span>
                            <Badge variant="primary" size="xs">{member.role}</Badge>
                          </div>
                          <Button variant="ghost" size="xs" onClick={() => removeMember(member.id)} className="text-[var(--color-error)]">
                            移除
                          </Button>
                        </div>
                      ))}
                      {members.length === 0 && (
                        <p className="text-xs text-[var(--color-text-muted)] text-center py-4">暂无成员</p>
                      )}
                    </div>
                  </>
                )}
              </CardContent>
            </Card>
          )}

          {groups.length === 0 ? (
            <EmptyState
              icon="file"
              title="暂无群组"
              description="创建一个群组以开始多智能体协作"
            />
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 stagger-children">
              {groups.map((group) => (
                <Card key={group.id} variant="default" className="hover-lift">
                  <CardContent className="p-5">
                    <div className="flex items-center gap-2 mb-3">
                      <div className="p-1.5 rounded-lg bg-[var(--color-accent)]/10 border border-[var(--color-accent)]/20">
                        <Hash size={14} className="text-[var(--color-accent)]" />
                      </div>
                      <span className="text-sm font-semibold text-[var(--color-text-primary)] truncate flex-1">{group.name}</span>
                      <Badge variant={group.status === 'active' ? 'success' : 'default'} size="xs">
                        {group.status}
                      </Badge>
                    </div>
                    {group.description && (
                      <p className="text-xs text-[var(--color-text-muted)] line-clamp-2 mb-3">{group.description}</p>
                    )}
                    <div className="flex items-center gap-3 text-[10px] text-[var(--color-text-muted)] mb-4">
                      <span className="flex items-center gap-1"><Users size={10} /> {group.member_count} 名成员</span>
                      <span>{new Date(group.created_at).toLocaleDateString()}</span>
                    </div>
                    <div className="flex items-center gap-2 pt-3 border-t border-[var(--color-border-subtle)]">
                      <Button variant="outline" size="xs" onClick={() => openGroup(group.id, 'chat')}>
                        进入聊天
                      </Button>
                      <Button variant="ghost" size="xs" onClick={() => openGroup(group.id, 'collab')}>
                        自动协作
                      </Button>
                      <Button variant="ghost" size="xs" onClick={() => openManageMembers(group.id)}>
                        成员
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="h-full overflow-y-auto page-transition">
      <div className="p-4 md:p-6 lg:p-8 max-w-4xl mx-auto">
        <PageHeader
          title="集群"
          description="输入需求，自动分解为多智能体协作任务"
          icon={<Network size={20} />}
          actions={
            <Button variant="ghost" size="sm" onClick={() => { setViewMode('groups'); loadGroups(); }}>
              群组列表
            </Button>
          }
        />

        <Card variant="default" className="mb-6">
          <CardContent className="p-5">
            <div className="flex gap-3">
              <textarea
                value={requirements}
                onChange={(e) => setRequirements(e.target.value)}
                placeholder="描述您的需求，智能体集群将自动分解并执行..."
                className="flex-1 px-4 py-3 bg-[var(--color-bg-surface-2)] border border-[var(--color-border-subtle)] rounded-xl text-sm text-[var(--color-text-primary)] placeholder:text-[var(--color-text-muted)] focus:outline-none focus:border-[var(--color-accent)]/50 transition-all duration-200 resize-none min-h-[80px]"
                rows={3}
              />
            </div>
            <div className="flex justify-end mt-3">
              <Button
                variant="primary"
                onClick={createCluster}
                disabled={!requirements.trim()}
                loading={creating}
                icon={<Play size={14} />}
              >
                创建集群
              </Button>
            </div>
          </CardContent>
        </Card>

        {progress.total > 0 && <ProgressBar progress={progress} />}

        {tasks.length === 0 && !creating && (
          <EmptyState
            icon="file"
            title="暂无任务"
            description="输入需求并点击「创建集群」开始"
          />
        )}

        {tasks.length > 0 && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            <div className="lg:col-span-2 space-y-3">
              {tasks.map((task) => (
                <TaskCard
                  key={task.id}
                  task={task}
                  isSelected={selectedTaskId === task.id}
                  onClick={() => handleTaskClick(task.id)}
                  loading={loadingTaskDetails && selectedTaskId === task.id}
                />
              ))}
            </div>
            <div>
              <TaskDetailsPanel
                taskId={selectedTaskId || ''}
                details={taskDetails}
                loading={loadingTaskDetails}
              />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
