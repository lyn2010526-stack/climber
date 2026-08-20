// Platform misc resources: stats, api keys, notifications, feedback,
// reasoning, cost, scheduler, eval, search, doctor, terminal.
import type { NotificationResult, NotificationsResponse, PlatformStats, ReasoningMode } from '../types/api';
import { ApiClient } from './client';

declare module './client' {
  interface ApiClient {
    getStats(): Promise<PlatformStats>;
    listApiKeys(): Promise<any[]>;
    addApiKey(data: any): Promise<any>;
    deleteApiKey(id: string): Promise<any>;
    sendNotification(title: string, message: string): Promise<NotificationResult>;
    testNotification(): Promise<NotificationResult>;
    listNotifications(limit?: number): Promise<NotificationsResponse>;
    clearNotifications(): Promise<NotificationResult>;
    submitFeedback(messageId: string, rating: string, reason?: string): Promise<any>;
    getFeedbackStats(): Promise<{
      total: number;
      approval_rate: number;
      up_count: number;
      down_count: number;
      reason_distribution: Record<string, number>;
    }>;
    listReasoningModes(): Promise<ReasoningMode[]>;
    submitReason(task: string, mode: string, maxPaths: number, maxRefineRounds: number, coverageEnabled: boolean): Promise<any>;
    submitReasoningFeedback(traceId: string, data: { rating: number; thumbs?: string; comment?: string }): Promise<any>;
    listReasoningHistory(limit?: number): Promise<any[]>;
    getCostUsage(): Promise<any>;
    getCostBudget(): Promise<any>;
    getCostQuota(): Promise<any>;
    listSchedulerTasks(): Promise<any[]>;
    createSchedulerTask(data: any): Promise<any>;
    updateSchedulerTask(id: string, data: any): Promise<any>;
    deleteSchedulerTask(id: string): Promise<any>;
    listEvalDatasets(): Promise<any[]>;
    seedBuiltinDatasets(): Promise<any>;
    runEvalDataset(id: string): Promise<any>;
    search(query: string, limit?: number): Promise<any[]>;
    runDoctor(): Promise<any>;
    executeCommand(command: string, timeout?: number): Promise<any>;
  }
}

ApiClient.prototype.getStats = function (this: ApiClient): Promise<PlatformStats> {
  return this.request<PlatformStats>('/stats');
};

ApiClient.prototype.listApiKeys = function (this: ApiClient) {
  return this.request<any[]>('/api-keys');
};

ApiClient.prototype.addApiKey = function (this: ApiClient, data: any) {
  return this.request<any>('/api-keys', {
    method: 'POST',
    body: JSON.stringify(data),
  });
};

ApiClient.prototype.deleteApiKey = function (this: ApiClient, id: string) {
  return this.request(`/api-keys/${id}`, { method: 'DELETE' });
};

ApiClient.prototype.sendNotification = function (this: ApiClient, title: string, message: string): Promise<NotificationResult> {
  return this.request<NotificationResult>('/notifications/send', {
    method: 'POST',
    body: JSON.stringify({ title, message }),
  });
};

ApiClient.prototype.testNotification = function (this: ApiClient): Promise<NotificationResult> {
  return this.request<NotificationResult>('/notifications/test');
};

ApiClient.prototype.listNotifications = function (this: ApiClient, limit = 50): Promise<NotificationsResponse> {
  return this.request<NotificationsResponse>(`/notifications/history?limit=${limit}`);
};

ApiClient.prototype.clearNotifications = function (this: ApiClient): Promise<NotificationResult> {
  return this.request<NotificationResult>('/notifications/history', { method: 'DELETE' });
};

ApiClient.prototype.submitFeedback = function (this: ApiClient, messageId: string, rating: string, reason?: string) {
  const params = new URLSearchParams({ message_id: messageId, rating });
  if (reason) params.set('reason', reason);
  return this.request<any>(`/feedback?${params.toString()}`, { method: 'POST' });
};

ApiClient.prototype.getFeedbackStats = function (this: ApiClient) {
  return this.request<{
    total: number;
    approval_rate: number;
    up_count: number;
    down_count: number;
    reason_distribution: Record<string, number>;
  }>('/feedback/stats');
};

ApiClient.prototype.listReasoningModes = function (this: ApiClient): Promise<ReasoningMode[]> {
  return this.request<ReasoningMode[]>('/reason/modes');
};

ApiClient.prototype.submitReason = function (
  this: ApiClient,
  task: string,
  mode: string,
  maxPaths: number,
  maxRefineRounds: number,
  coverageEnabled: boolean,
): Promise<any> {
  const body = { task, mode, max_paths: maxPaths, max_refine_rounds: maxRefineRounds, coverage_enabled: coverageEnabled };

  return this.request<any>('/reason', {
    method: 'POST',
    body: JSON.stringify(body),
  });
};

ApiClient.prototype.submitReasoningFeedback = function (this: ApiClient, traceId: string, data: { rating: number; thumbs?: string; comment?: string }) {
  return this.request<any>(`/reason/${traceId}/feedback`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
};

ApiClient.prototype.listReasoningHistory = function (this: ApiClient, limit = 50) {
  return this.request<any[]>(`/reason/history?limit=${limit}`);
};

ApiClient.prototype.getCostUsage = function (this: ApiClient) {
  return this.request<any>('/cost/usage');
};

ApiClient.prototype.getCostBudget = function (this: ApiClient) {
  return this.request<any>('/cost/budget');
};

ApiClient.prototype.getCostQuota = function (this: ApiClient) {
  return this.request<any>('/cost/quota');
};

ApiClient.prototype.listSchedulerTasks = function (this: ApiClient) {
  return this.request<any[]>('/scheduler/tasks');
};

ApiClient.prototype.createSchedulerTask = function (this: ApiClient, data: any) {
  return this.request<any>('/scheduler/tasks', {
    method: 'POST',
    body: JSON.stringify(data),
  });
};

ApiClient.prototype.updateSchedulerTask = function (this: ApiClient, id: string, data: any) {
  return this.request<any>(`/scheduler/tasks/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  });
};

ApiClient.prototype.deleteSchedulerTask = function (this: ApiClient, id: string) {
  return this.request(`/scheduler/tasks/${id}`, { method: 'DELETE' });
};

ApiClient.prototype.listEvalDatasets = function (this: ApiClient) {
  return this.request<any[]>('/eval/datasets');
};

ApiClient.prototype.seedBuiltinDatasets = function (this: ApiClient) {
  return this.request<any>('/eval/datasets/seed-builtin', { method: 'POST' });
};

ApiClient.prototype.runEvalDataset = function (this: ApiClient, id: string) {
  return this.request<any>(`/eval/datasets/${id}/run`, { method: 'POST' });
};

ApiClient.prototype.search = function (this: ApiClient, query: string, limit = 20) {
  return this.request<any[]>(`/search?q=${encodeURIComponent(query)}&limit=${limit}`);
};

ApiClient.prototype.runDoctor = function (this: ApiClient) {
  return this.request<any>('/doctor');
};

ApiClient.prototype.executeCommand = function (this: ApiClient, command: string, timeout?: number) {
  return this.request<any>('/terminal/execute', {
    method: 'POST',
    body: JSON.stringify({ command, timeout }),
  });
};
