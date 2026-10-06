import { api } from '../api';
import i18n from '../i18n/config';

export interface ClusterMember {
  id: string;
  agent_id: string | null;
  role: string;
  status?: string;
}

export async function getClusterMembers(groupId: string): Promise<ClusterMember[]> {
  const group = await api.getGroup(groupId);
  if (!Array.isArray(group?.members) || group.members.some((member: unknown) => (
    !member || typeof member !== 'object'
    || !('id' in member) || typeof member.id !== 'string'
    || !('agent_id' in member) || (member.agent_id !== null && typeof member.agent_id !== 'string')
    || !('role' in member) || typeof member.role !== 'string'
    || ('status' in member && typeof member.status !== 'string')
  ))) {
    throw new Error(i18n.t('api_errors.cluster_members_invalid'));
  }
  return group.members;
}
