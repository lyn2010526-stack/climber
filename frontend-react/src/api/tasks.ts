// Tasks resource domain.
import type { TaskDetail, TaskSummary } from '../types/api';
import type { CreatedTask, CreateTaskInput, TaskActionResult, TaskRunInputs } from '../types/tasks';
import { ApiClient } from './client';

declare module './client' {
  interface ApiClient {
    listTasks(params?: { status?: string; limit?: number }): Promise<TaskSummary[]>;
    getTask(taskId: string): Promise<TaskDetail>;
    createTask(data: CreateTaskInput): Promise<CreatedTask>;
    runTask(id: string, inputs?: TaskRunInputs): Promise<TaskActionResult>;
    cancelTask(id: string): Promise<TaskActionResult>;
    pauseTask(id: string): Promise<TaskActionResult>;
    resumeTask(id: string): Promise<TaskActionResult>;
    stopTask(id: string): Promise<TaskActionResult>;
  }
}

ApiClient.prototype.listTasks = function (this: ApiClient, params?: { status?: string; limit?: number }): Promise<TaskSummary[]> {
  const searchParams = new URLSearchParams();
  if (params?.status) searchParams.set('status', params.status);
  if (params?.limit !== undefined) searchParams.set('limit', String(params.limit));
  const qs = params ? `?${searchParams.toString()}` : '';
  return this.request<TaskSummary[]>(`/tasks${qs}`);
};

ApiClient.prototype.getTask = function (this: ApiClient, taskId: string): Promise<TaskDetail> {
  return this.request<TaskDetail>(`/tasks/${taskId}`);
};

ApiClient.prototype.createTask = function (this: ApiClient, data: CreateTaskInput): Promise<CreatedTask> {
  return this.request<CreatedTask>('/tasks', {
    method: 'POST',
    body: JSON.stringify(data),
  });
};

ApiClient.prototype.runTask = function (this: ApiClient, id: string, inputs?: TaskRunInputs): Promise<TaskActionResult> {
  return this.request<TaskActionResult>(`/tasks/${id}/run`, {
    method: 'POST',
    body: JSON.stringify(inputs || {}),
  });
};

ApiClient.prototype.cancelTask = function (this: ApiClient, id: string): Promise<TaskActionResult> {
  return this.request<TaskActionResult>(`/tasks/${id}/cancel`, { method: 'POST' });
};

ApiClient.prototype.pauseTask = function (this: ApiClient, id: string): Promise<TaskActionResult> {
  return this.request<TaskActionResult>(`/tasks/${id}/pause`, { method: 'POST' });
};

ApiClient.prototype.resumeTask = function (this: ApiClient, id: string): Promise<TaskActionResult> {
  return this.request<TaskActionResult>(`/tasks/${id}/resume`, { method: 'POST' });
};

ApiClient.prototype.stopTask = function (this: ApiClient, id: string): Promise<TaskActionResult> {
  return this.request<TaskActionResult>(`/tasks/${id}/stop`, { method: 'POST' });
};
