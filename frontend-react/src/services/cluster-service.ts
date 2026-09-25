import { api } from '../api';

export interface ClusterMember {
  id: string;
  agent_id: string | null;
  role: string;
}

export async function getClusterMembers(groupId: string): Promise<ClusterMember[]> {
  const group = await api.getGroup(groupId);
  if (!Array.isArray(group?.members) || group.members.some((member: unknown) => (
    !member || typeof member !== 'object'
    || !('id' in member) || typeof member.id !== 'string'
    || !('agent_id' in member) || (member.agent_id !== null && typeof member.agent_id !== 'string')
    || !('role' in member) || typeof member.role !== 'string'
  ))) {
    throw new Error('群组成员响应格式异常，请重试。');
  }
  return group.members;
}
