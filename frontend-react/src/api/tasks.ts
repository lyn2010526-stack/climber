// Tasks resource domain.
import type { TaskDetail, TaskSummary } from '../types/api';
import { ApiClient } from './client';

declare module './client' {
  interface ApiClient {
    listTasks(params?: { status?: string; limit?: number }): Promise<TaskSummary[]>;
    getTask(taskId: string): Promise<TaskDetail>;
    createTask(data: any): Promise<any>;
    runTask(id: string, inputs?: Record<string, any>): Promise<any>;
    cancelTask(id: string): Promise<any>;
    pauseTask(id: string): Promise<any>;
    resumeTask(id: string): Promise<any>;
    stopTask(id: string): Promise<any>;
  }
}

ApiClient.prototype.listTasks = function (this: ApiClient, params?: { status?: string; limit?: number }): Promise<TaskSummary[]> {
  const qs = params ? '?' + new URLSearchParams(params as any).toString() : '';
  return this.request<TaskSummary[]>(`/tasks${qs}`);
};

ApiClient.prototype.getTask = function (this: ApiClient, taskId: string): Promise<TaskDetail> {
  return this.request<TaskDetail>(`/tasks/${taskId}`);
};

ApiClient.prototype.createTask = function (this: ApiClient, data: any) {
  return this.request<any>('/tasks', {
    method: 'POST',
    body: JSON.stringify(data),
  });
};

ApiClient.prototype.runTask = function (this: ApiClient, id: string, inputs?: Record<string, any>) {
  return this.request<any>(`/tasks/${id}/run`, {
    method: 'POST',
    body: JSON.stringify(inputs || {}),
  });
};

ApiClient.prototype.cancelTask = function (this: ApiClient, id: string) {
  return this.request<any>(`/tasks/${id}/cancel`, { method: 'POST' });
};

ApiClient.prototype.pauseTask = function (this: ApiClient, id: string) {
  return this.request<any>(`/tasks/${id}/pause`, { method: 'POST' });
};

ApiClient.prototype.resumeTask = function (this: ApiClient, id: string) {
  return this.request<any>(`/tasks/${id}/resume`, { method: 'POST' });
};

ApiClient.prototype.stopTask = function (this: ApiClient, id: string) {
  return this.request<any>(`/tasks/${id}/stop`, { method: 'POST' });
};
