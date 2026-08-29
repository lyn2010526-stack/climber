// Groups / cluster resource domain.
import type { GroupSummary } from '../types/api';
import type {
  AddedGroupMember,
  AddGroupMemberInput,
  ClusterCreateResult,
  ClusterStatus,
  CreateGroupInput,
  GroupMessagesResponse,
  RemoveGroupMemberResult,
} from '../types/groups';
import { ApiClient } from './client';

declare module './client' {
  interface ApiClient {
    createCluster(requirements: string): Promise<ClusterCreateResult>;
    getClusterStatus(): Promise<ClusterStatus>;
    listGroups(): Promise<GroupSummary[]>;
    createGroup(data: CreateGroupInput): Promise<GroupSummary>;
    getGroup(id: string): Promise<GroupSummary>;
    addGroupMember(groupId: string, data: AddGroupMemberInput): Promise<AddedGroupMember>;
    removeGroupMember(groupId: string, memberId: string): Promise<RemoveGroupMemberResult>;
    listGroupMessages(groupId: string, limit?: number): Promise<GroupMessagesResponse>;
  }
}

ApiClient.prototype.createCluster = function (this: ApiClient, requirements: string): Promise<ClusterCreateResult> {
  return this.request<ClusterCreateResult>('/cluster/create', {
    method: 'POST',
    body: JSON.stringify({ requirements }),
  });
};

ApiClient.prototype.getClusterStatus = function (this: ApiClient): Promise<ClusterStatus> {
  return this.request<ClusterStatus>('/cluster/status');
};

ApiClient.prototype.listGroups = function (this: ApiClient): Promise<GroupSummary[]> {
  return this.request<GroupSummary[]>('/groups/');
};

ApiClient.prototype.createGroup = function (this: ApiClient, data: CreateGroupInput): Promise<GroupSummary> {
  return this.request<GroupSummary>('/groups/', {
    method: 'POST',
    body: JSON.stringify(data),
  });
};

ApiClient.prototype.getGroup = function (this: ApiClient, id: string): Promise<GroupSummary> {
  return this.request<GroupSummary>(`/groups/${id}`);
};

ApiClient.prototype.addGroupMember = function (this: ApiClient, groupId: string, data: AddGroupMemberInput): Promise<AddedGroupMember> {
  return this.request<AddedGroupMember>(`/groups/${groupId}/members`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
};

ApiClient.prototype.removeGroupMember = function (this: ApiClient, groupId: string, memberId: string): Promise<RemoveGroupMemberResult> {
  return this.request<RemoveGroupMemberResult>(`/groups/${groupId}/members/${memberId}`, { method: 'DELETE' });
};

ApiClient.prototype.listGroupMessages = function (this: ApiClient, groupId: string, limit = 50): Promise<GroupMessagesResponse> {
  return this.request<GroupMessagesResponse>(`/groups/${groupId}/messages?limit=${limit}`);
};
