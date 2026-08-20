// Groups / cluster resource domain.
import type { GroupSummary } from '../types/api';
import { ApiClient } from './client';

declare module './client' {
  interface ApiClient {
    createCluster(requirements: string): Promise<any>;
    getClusterStatus(): Promise<any>;
    listGroups(): Promise<GroupSummary[]>;
    createGroup(data: { name: string; description?: string; topic?: string }): Promise<any>;
    getGroup(id: string): Promise<GroupSummary>;
    addGroupMember(groupId: string, data: Record<string, any>): Promise<any>;
    removeGroupMember(groupId: string, memberId: string): Promise<any>;
    listGroupMessages(groupId: string, limit?: number): Promise<any>;
  }
}

ApiClient.prototype.createCluster = function (this: ApiClient, requirements: string) {
  return this.request<any>('/cluster/create', {
    method: 'POST',
    body: JSON.stringify({ requirements }),
  });
};

ApiClient.prototype.getClusterStatus = function (this: ApiClient) {
  return this.request<any>('/cluster/status');
};

ApiClient.prototype.listGroups = function (this: ApiClient): Promise<GroupSummary[]> {
  return this.request<GroupSummary[]>('/groups/');
};

ApiClient.prototype.createGroup = function (this: ApiClient, data: { name: string; description?: string; topic?: string }) {
  return this.request<any>('/groups/', {
    method: 'POST',
    body: JSON.stringify(data),
  });
};

ApiClient.prototype.getGroup = function (this: ApiClient, id: string): Promise<GroupSummary> {
  return this.request<GroupSummary>(`/groups/${id}`);
};

ApiClient.prototype.addGroupMember = function (this: ApiClient, groupId: string, data: Record<string, any>) {
  return this.request<any>(`/groups/${groupId}/members`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
};

ApiClient.prototype.removeGroupMember = function (this: ApiClient, groupId: string, memberId: string) {
  return this.request<any>(`/groups/${groupId}/members/${memberId}`, { method: 'DELETE' });
};

ApiClient.prototype.listGroupMessages = function (this: ApiClient, groupId: string, limit = 50) {
  return this.request<any>(`/groups/${groupId}/messages?limit=${limit}`);
};
