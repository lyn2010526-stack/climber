import { useState, useCallback } from 'react';
import { api } from '../../api';
import type { AgentGroup, ClusterTask } from './types';

export interface ClusterProgress {
  total: number;
  completed: number;
  failed: number;
  running: number;
  pending: number;
  progress_pct: number;
}

export function useClusterState() {
  const [viewMode, setViewMode] = useState<'cluster' | 'groups' | 'group-room' | 'collab-console'>('cluster');
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
  const [progress, setProgress] = useState<ClusterProgress>({ total: 0, completed: 0, failed: 0, running: 0, pending: 0, progress_pct: 0 });
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

  return {
    // view state
    viewMode, setViewMode,
    activeGroupId,
    // member management
    managingGroupId, setManagingGroupId,
    members, loadingMembers, showAddMember, setShowAddMember,
    memberForm, setMemberForm,
    addMember, removeMember, openManageMembers,
    availableTasks,
    // cluster
    requirements, setRequirements,
    tasks, progress, creating,
    createCluster,
    selectedTaskId, setSelectedTaskId,
    taskDetails, setTaskDetails,
    loadingTaskDetails,
    handleTaskClick,
    // groups
    groups, loadGroups,
    showCreateGroup, setShowCreateGroup,
    groupName, setGroupName,
    groupTopic, setGroupTopic,
    useTemplate, setUseTemplate,
    createGroup,
    openGroup, leaveGroup,
  };
}

export type ClusterState = ReturnType<typeof useClusterState>;
