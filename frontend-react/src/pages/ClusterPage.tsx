import { useState, useCallback } from 'react';
import {
  Network, Play, CheckCircle2, Clock, Loader2,
  Bot, Shield, Search, Wrench, Plus, ArrowLeft, Hash, Users,
} from 'lucide-react';
import { GroupRoom } from '../components/group/GroupRoom';
import { CollaborationConsole } from '../components/collaboration/CollaborationConsole';

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
  pending: 'text-gray-500',
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
      const res = await fetch(`/api/v1/tasks/${taskId}`);
      if (res.ok) {
        const data = await res.json();
        setTaskDetails(data);
      }
    } catch {
      // skip
    }
    setLoadingTaskDetails(false);
  }, []);

  const handleTaskClick = useCallback((taskId: string) => {
    setSelectedTaskId(prev => prev === taskId ? null : taskId);
    if (selectedTaskId !== taskId) {
      loadTaskDetails(taskId);
    }
  }, [selectedTaskId, loadTaskDetails]);

  const createCluster = async () => {
    if (!requirements.trim()) return;
    setCreating(true);
    try {
      const res = await fetch('/api/v1/cluster/create', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ requirements }),
      });
      if (res.ok) {
        const data = await res.json();
        if (data.plan) {
          const planTasks = data.plan.map((p: any, idx: number) => ({
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
        }
        if (data.progress) {
          setProgress(data.progress);
        }
      } else {
        // Fallback: create a group with the requirements as topic
        const groupRes = await fetch('/api/v1/groups/', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ name: requirements.slice(0, 50), topic: requirements, agent_ids: [] }),
        });
        if (groupRes.ok) {
          const groupData = await groupRes.json();
          setTasks([{
            id: groupData.id,
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
      const res = await fetch('/api/v1/groups/');
      if (res.ok) {
        const data = await res.json();
        setGroups(data);
      }
    } catch { /* skip */ }
  }, []);

  const createGroup = async () => {
    if (!groupName.trim()) return;
    try {
      const res = await fetch('/api/v1/groups/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          name: groupName,
          topic: groupTopic,
          agent_ids: [],
          template: useTemplate ? 'default' : undefined,
        }),
      });
      if (res.ok) {
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
      try {
        const res = await fetch(`/api/v1/groups/${groupId}/tasks?limit=20`);
        if (res.ok) {
          const data = await res.json();
          setAvailableTasks((data.tasks || []).map((t: any) => ({ id: t.id, description: t.description })));
        }
      } catch {
        // skip
      }
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
    try {
      const res = await fetch(`/api/v1/groups/${groupId}/members`);
      if (res.ok) {
        const data = await res.json();
        setMembers(data.members || []);
      }
      const msgRes = await fetch(`/api/v1/groups/${groupId}/messages?limit=50`);
      if (msgRes.ok) {
        await msgRes.json();
      }
    } catch {
      // skip
    }
    setLoadingMembers(false);
  };

  const addMember = async () => {
    if (!managingGroupId || !memberForm.agent_id.trim()) return;
    try {
      await fetch(`/api/v1/groups/${managingGroupId}/members`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(memberForm),
      });
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
      await fetch(`/api/v1/groups/${managingGroupId}/members/${memberId}`, { method: 'DELETE' });
      openManageMembers(managingGroupId);
    } catch {
      // skip
    }
  };

  // Collaboration Console View (new auto-collab mode)
  if (viewMode === 'collab-console' && activeGroupId) {
    return (
      <div className="h-full flex flex-col">
        <div className="h-10 flex items-center px-4 border-b border-gray-700 bg-gray-800/50">
          <button
            onClick={leaveGroup}
            className="flex items-center gap-1 text-xs text-gray-500 hover:text-gray-200 transition-colors"
          >
            <ArrowLeft size={14} />
            返回群组列表
          </button>
           <span className="ml-3 text-xs font-medium text-gray-200">自动协作</span>
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
        <div className="h-10 flex items-center px-4 border-b border-gray-700 bg-gray-800/50">
          <button
            onClick={leaveGroup}
            className="flex items-center gap-1 text-xs text-gray-500 hover:text-gray-200 transition-colors"
          >
            <ArrowLeft size={14} />
            返回群组列表
          </button>
          <button
            onClick={() => setViewMode('collab-console')}
            className="ml-3 flex items-center gap-1 text-xs text-blue-400 hover:text-blue-300 transition-colors"
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
            <h1 className="text-lg font-semibold text-gray-200">智能体群组</h1>
            <p className="text-xs text-gray-500 mt-0.5">多智能体协作空间</p>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setViewMode('cluster')}
                  className="px-3 py-1.5 text-xs text-gray-500 hover:text-gray-200 transition-colors"
              >
                集群视图
              </button>
              <button
                onClick={() => setShowCreateGroup(true)}
                className="flex items-center gap-1 px-3 py-1.5 text-xs bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
              >
                <Plus size={12} />
                新建群组
              </button>
            </div>
          </div>

          {/* Create Group Form */}
          {showCreateGroup && (
            <div className="p-4 bg-gray-800/50 border border-gray-700 rounded-xl space-y-3">
              <input
                type="text"
                value={groupName}
                onChange={(e) => setGroupName(e.target.value)}
                placeholder="群组名称..."
                className="w-full px-3 py-2 bg-gray-700 border border-gray-700 rounded-lg text-xs text-gray-200 placeholder:text-gray-500 focus:outline-none focus:border-blue-500/50"
              />
              <input
                type="text"
                value={groupTopic}
                onChange={(e) => setGroupTopic(e.target.value)}
                placeholder="讨论主题（可选）..."
                className="w-full px-3 py-2 bg-gray-700 border border-gray-700 rounded-lg text-xs text-gray-200 placeholder:text-gray-500 focus:outline-none focus:border-blue-500/50"
              />
              <label className="flex items-center gap-2 text-xs text-gray-400 cursor-pointer">
                <input
                  type="checkbox"
                  checked={useTemplate}
                  onChange={(e) => setUseTemplate(e.target.checked)}
                  className="rounded border-gray-600 bg-gray-700 text-blue-600 focus:ring-blue-500"
                />
                快速开始：自动添加 Planner + Executor + Reviewer 默认成员
              </label>
              <div className="flex justify-end gap-2">
                <button
                  onClick={() => { setShowCreateGroup(false); setUseTemplate(false); }}
                className="px-3 py-1.5 text-xs text-gray-500 hover:text-gray-200 transition-colors"
                >
                   取消
                </button>
                <button
                  onClick={createGroup}
                  disabled={!groupName.trim()}
                  className="px-3 py-1.5 text-xs bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
                >
                   创建
                </button>
              </div>
            </div>
          )}

          {/* Member Management Panel */}
          {managingGroupId && (
            <div className="p-4 bg-gray-800/50 border border-gray-700 rounded-xl space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-medium text-gray-200">群组成员</h3>
                <button
                  onClick={() => setManagingGroupId(null)}
                  className="text-xs text-gray-500 hover:text-gray-200"
                >
                  关闭
                </button>
              </div>

              {loadingMembers ? (
                <div className="text-xs text-gray-500">加载中...</div>
              ) : (
                <>
                  {/* Add Member Form */}
                  {showAddMember ? (
                    <div className="p-3 bg-gray-700/50 rounded-lg space-y-2">
                      <input
                        type="text"
                        value={memberForm.agent_id}
                        onChange={(e) => setMemberForm({ ...memberForm, agent_id: e.target.value })}
                        placeholder="Agent ID"
                        className="w-full px-2 py-1.5 bg-gray-700 border border-gray-600 rounded text-xs text-gray-200"
                      />
                      <select
                        value={memberForm.role}
                        onChange={(e) => setMemberForm({ ...memberForm, role: e.target.value })}
                        className="w-full px-2 py-1.5 bg-gray-700 border border-gray-600 rounded text-xs text-gray-200"
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
                          className="px-2 py-1 text-xs text-gray-500"
                        >
                          取消
                        </button>
                        <button
                          onClick={addMember}
                          disabled={!memberForm.agent_id.trim()}
                          className="px-2 py-1 text-xs bg-blue-600 text-white rounded disabled:opacity-50"
                        >
                          添加
                        </button>
                      </div>
                    </div>
                  ) : (
                    <button
                      onClick={() => setShowAddMember(true)}
                      className="flex items-center gap-1 px-3 py-1.5 text-xs text-blue-400 hover:text-blue-300"
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
                        className="flex items-center justify-between p-2 bg-gray-700/30 rounded-lg"
                      >
                        <div>
                          <span className="text-xs text-gray-200">{member.agent_id || member.id}</span>
                          <span className="ml-2 text-[10px] px-2 py-0.5 rounded-full bg-blue-500/10 text-blue-400">
                            {member.role}
                          </span>
                        </div>
                        <button
                          onClick={() => removeMember(member.id)}
                          className="text-[10px] text-red-400 hover:text-red-300"
                        >
                          移除
                        </button>
                      </div>
                    ))}
                    {members.length === 0 && (
                      <p className="text-xs text-gray-500 text-center py-2">暂无成员</p>
                    )}
                  </div>
                </>
              )}
            </div>
          )}

          {/* Groups List */}
          {groups.length === 0 ? (
            <div className="text-center py-12">
              <Network size={40} className="mx-auto text-gray-500/30" />
               <p className="text-sm text-gray-500 mt-3">暂无群组</p>
               <p className="text-xs text-gray-500/60 mt-1">创建一个群组以开始多智能体协作</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {groups.map((group) => (
                <div
                  key={group.id}
                  className="p-4 bg-gray-800/50 border border-gray-700 rounded-xl hover:border-blue-500/30 transition-colors"
                >
                  <div className="flex items-center gap-2">
                    <Hash size={14} className="text-blue-400" />
                    <span className="text-sm font-medium text-gray-200">{group.name}</span>
                    <span className={`ml-auto px-2 py-0.5 text-[10px] rounded-full ${
                      group.status === 'active' ? 'bg-green-500/10 text-green-400' : 'bg-gray-700 text-gray-500'
                    }`}>
                      {group.status}
                    </span>
                  </div>
                  {group.description && (
                    <p className="text-[11px] text-gray-500 mt-2 line-clamp-2">{group.description}</p>
                  )}
                  <div className="flex items-center gap-3 mt-3 text-[10px] text-gray-500">
                    <span>{group.member_count} 名成员</span>
                    <span>{new Date(group.created_at).toLocaleDateString()}</span>
                  </div>
                    <div className="flex items-center gap-2 mt-3 pt-3 border-t border-gray-700">
                    <button
                      onClick={() => openGroup(group.id, 'chat')}
                      className="flex items-center gap-1 px-2 py-1 text-[10px] text-gray-500 hover:text-gray-200 bg-gray-700 rounded transition-colors"
                    >
                      <Users size={10} />
                      Chat
                    </button>
                    <button
                      onClick={() => openGroup(group.id, 'collab')}
                      className="flex items-center gap-1 px-2 py-1 text-[10px] text-blue-400 bg-blue-600/10 hover:bg-blue-600/20 rounded transition-colors"
                    >
                      <Wrench size={10} />
                      自动协作
                    </button>
                    <button
                      onClick={() => openManageMembers(group.id)}
                      className="flex items-center gap-1 px-2 py-1 text-[10px] text-gray-500 hover:text-gray-200 bg-gray-700 rounded transition-colors"
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
            <h1 className="text-lg font-semibold text-gray-200">多智能体集群</h1>
            <p className="text-xs text-gray-500 mt-0.5">协作式智能体流水线：规划 → 研究 → 执行 → 审计</p>
          </div>
          <button
            onClick={() => { setViewMode('groups'); loadGroups(); }}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs bg-gray-800/50 border border-gray-700 text-gray-400 rounded-lg hover:border-blue-500/30 transition-colors"
          >
            <Network size={12} />
            智能体群组
          </button>
        </div>

        {/* Input */}
        <div className="p-4 bg-gray-800/50 border border-gray-700 rounded-xl space-y-3">
          <textarea
            value={requirements}
            onChange={(e) => setRequirements(e.target.value)}
              placeholder="描述你想要构建的内容..."
            rows={3}
            className="w-full px-3 py-2 bg-gray-700 border border-gray-700 rounded-lg text-xs text-gray-200 placeholder:text-gray-500 focus:outline-none focus:border-blue-500/50 resize-none"
          />
          <div className="flex justify-end">
            <button
              onClick={createCluster}
              disabled={!requirements.trim() || creating}
              className="flex items-center gap-1.5 px-4 py-2 text-xs bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {creating ? <Loader2 size={12} className="animate-spin" /> : <Play size={12} />}
              {creating ? '创建中...' : '创建集群'}
            </button>
          </div>
        </div>

        {/* Progress */}
        {progress.total > 0 && (
          <div className="p-4 bg-gray-800/50 border border-gray-700 rounded-xl">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs text-gray-400">进度</span>
              <span className="text-xs font-medium text-blue-400">{progress.progress_pct}%</span>
            </div>
            <div className="h-2 bg-gray-700 rounded-full overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-blue-600 to-blue-400 rounded-full transition-all duration-500"
                style={{ width: `${progress.progress_pct}%` }}
              />
            </div>
            <div className="flex items-center gap-4 mt-2 text-[10px] text-gray-500">
              <span className="flex items-center gap-1"><CheckCircle2 size={10} className="text-green-400" /> {progress.completed} 已完成</span>
              <span className="flex items-center gap-1"><Loader2 size={10} className="text-blue-400" /> {progress.running} 运行中</span>
              <span className="flex items-center gap-1"><Clock size={10} /> {progress.pending} 等待中</span>
            </div>
          </div>
        )}

        {/* Task DAG */}
        {tasks.length > 0 && (
          <div className="space-y-3">
            <h2 className="text-sm font-medium text-gray-200">执行计划</h2>
            <div className="relative">
              {/* Connection line */}
              <div className="absolute left-6 top-8 bottom-8 w-px bg-gray-700" />

              {tasks.map((task) => {
                const Icon = ROLE_ICONS[task.role] || Bot;
                const statusIcon = STATUS_ICONS[task.status] || Clock;
                const StatusIcon = statusIcon;
                const isSelected = selectedTaskId === task.id;

                return (
                  <div key={task.id} className="relative flex items-start gap-4 py-3">
                    {/* Node circle */}
                    <div className={`relative z-10 w-12 h-12 rounded-xl border flex items-center justify-center shrink-0 cursor-pointer ${
                      task.status === 'completed' ? 'bg-green-500/10 border-green-500/20' :
                      task.status === 'running' ? 'bg-blue-600/10 border-blue-500/20' :
                      'bg-gray-800/50 border-gray-700'
                    }`} onClick={() => handleTaskClick(task.id)}>
                      <Icon size={18} className={
                        task.status === 'completed' ? 'text-green-400' :
                        task.status === 'running' ? 'text-blue-400' :
                        'text-gray-500'
                      } />
                    </div>

                    {/* Card */}
                    <div className={`flex-1 p-3 rounded-xl cursor-pointer transition-colors ${
                      isSelected ? 'bg-blue-900/20 border border-blue-500/30' : 'bg-gray-800/50 border border-gray-700'
                    }`} onClick={() => handleTaskClick(task.id)}>
                      <div className="flex items-center gap-2">
                        <span className={`px-2 py-0.5 rounded text-[10px] font-medium border ${ROLE_COLORS[task.role] || ROLE_COLORS['planner']}`}>
                          {task.role}
                        </span>
                        <StatusIcon size={12} className={STATUS_COLORS[task.status]} />
                        <span className="text-[10px] text-gray-500 capitalize">{task.status}</span>
                        {task.process_type && task.process_type !== 'sequential' && (
                          <span className="px-2 py-0.5 rounded text-[9px] bg-purple-500/10 text-purple-400 border border-purple-500/20">
                            {task.process_type}
                          </span>
                        )}
                        {task.human_review_required && (
                          <span className="px-2 py-0.5 rounded text-[9px] bg-amber-500/10 text-amber-400 border border-amber-500/20">
                            人工审批
                          </span>
                        )}
                      </div>
                      <p className="text-xs text-gray-200 mt-1.5">{task.description}</p>
                      {task.dependencies.length > 0 && (
                         <p className="text-[10px] text-gray-500 mt-1">依赖：{task.dependencies.join(', ')}</p>
                      )}
                      {task.guardrails && task.guardrails.length > 0 && (
                        <div className="flex items-center gap-1 mt-1.5">
                          <Shield size={10} className="text-gray-500" />
                          <span className="text-[10px] text-gray-500">{task.guardrails.length} 个校验规则</span>
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
          <div className="p-4 bg-gray-800/50 border border-gray-700 rounded-xl space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-medium text-gray-200">任务详情</h3>
              <button
                onClick={() => { setSelectedTaskId(null); setTaskDetails(null); }}
                className="text-xs text-gray-500 hover:text-gray-200"
              >
                关闭
              </button>
            </div>
            {loadingTaskDetails ? (
              <div className="text-xs text-gray-500">加载中...</div>
            ) : taskDetails ? (
              <div className="space-y-2">
                <div className="grid grid-cols-2 gap-2 text-[10px]">
                  <div>
                    <span className="text-gray-500">状态:</span>
                    <span className="ml-1 text-gray-300">{taskDetails.status}</span>
                  </div>
                  <div>
                    <span className="text-gray-500">轮次:</span>
                    <span className="ml-1 text-gray-300">{taskDetails.current_round || 0}/{taskDetails.max_rounds || 5}</span>
                  </div>
                  <div>
                    <span className="text-gray-500">流程类型:</span>
                    <span className="ml-1 text-gray-300">{taskDetails.process_type || 'sequential'}</span>
                  </div>
                  <div>
                    <span className="text-gray-500">人工审批:</span>
                    <span className="ml-1 text-gray-300">{taskDetails.human_review_required ? '需要' : '不需要'}</span>
                  </div>
                  <div>
                    <span className="text-gray-500">Token 消耗:</span>
                    <span className="ml-1 text-gray-300">{taskDetails.total_tokens || 0}</span>
                  </div>
                  <div>
                    <span className="text-gray-500">开始时间:</span>
                    <span className="ml-1 text-gray-300">{taskDetails.started_at ? new Date(taskDetails.started_at).toLocaleString() : '-'}</span>
                  </div>
                </div>
                {taskDetails.context && taskDetails.context.length > 0 && (
                  <div>
                    <span className="text-[10px] text-gray-500">依赖任务:</span>
                    <div className="flex flex-wrap gap-1 mt-1">
                      {taskDetails.context.map((ctx: string) => (
                        <span key={ctx} className="px-2 py-0.5 rounded text-[9px] bg-gray-700 text-gray-300">{ctx.slice(0, 8)}</span>
                      ))}
                    </div>
                  </div>
                )}
                {taskDetails.guardrails && taskDetails.guardrails.length > 0 && (
                  <div>
                    <span className="text-[10px] text-gray-500">校验规则:</span>
                    <div className="space-y-1 mt-1">
                      {taskDetails.guardrails.map((g: any, i: number) => (
                        <div key={i} className="p-2 bg-gray-700/30 rounded">
                          <p className="text-[10px] text-gray-200">{g.name}</p>
                          {g.description && <p className="text-[9px] text-gray-500">{g.description}</p>}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
                {taskDetails.final_output && (
                  <div>
                    <span className="text-[10px] text-gray-500">最终输出:</span>
                    <pre className="mt-1 p-2 bg-gray-900/50 rounded text-[10px] text-gray-300 whitespace-pre-wrap overflow-x-auto max-h-48 overflow-y-auto">
                      {taskDetails.final_output}
                    </pre>
                  </div>
                )}
                {taskDetails.structured_output && Object.keys(taskDetails.structured_output).length > 0 && (
                  <div>
                    <span className="text-[10px] text-gray-500">结构化输出:</span>
                    <pre className="mt-1 p-2 bg-gray-900/50 rounded text-[10px] text-gray-300 whitespace-pre-wrap overflow-x-auto max-h-32 overflow-y-auto">
                      {JSON.stringify(taskDetails.structured_output, null, 2)}
                    </pre>
                  </div>
                )}
              </div>
            ) : (
              <div className="text-xs text-gray-500">暂无详情</div>
            )}
          </div>
        )}

        {/* Empty State */}
        {tasks.length === 0 && (
          <div className="text-center py-12">
            <Network size={40} className="mx-auto text-gray-500/30" />
            <p className="text-sm text-gray-500 mt-3">暂无活跃集群</p>
            <p className="text-xs text-gray-500/60 mt-1">在上方描述你的需求以创建一个</p>
          </div>
        )}
      </div>
    </div>
  );
}
