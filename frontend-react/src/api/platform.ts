// Platform misc resources: stats, api keys, notifications, feedback,
// reasoning, cost, scheduler, eval, search, doctor, terminal.
import type { NotificationResult, NotificationsResponse, PlatformStats, ReasoningMode } from '../types/api';
import type { OkResult } from '../types/common';
import type {
  ApiKeyRecord,
  CommandResult,
  CostBudget,
  CostQuota,
  CostUsage,
  CreateApiKeyInput,
  CreateSchedulerTaskInput,
  DeletedResourceResult,
  DoctorReport,
  EvalDataset,
  EvalRun,
  FeedbackResult,
  FeedbackStats,
  ReasoningFeedbackInput,
  ReasoningFeedbackResult,
  ReasoningHistoryItem,
  ReasoningResult,
  SchedulerTask,
  SearchResult,
  SeedDatasetsResult,
  UpdateSchedulerTaskInput,
} from '../types/platform';
import { ApiClient } from './client';

declare module './client' {
  interface ApiClient {
    getStats(): Promise<PlatformStats>;
    listApiKeys(): Promise<ApiKeyRecord[]>;
    addApiKey(data: CreateApiKeyInput): Promise<ApiKeyRecord>;
    deleteApiKey(id: string): Promise<OkResult>;
    sendNotification(title: string, message: string): Promise<NotificationResult>;
    testNotification(): Promise<NotificationResult>;
    listNotifications(limit?: number): Promise<NotificationsResponse>;
    clearNotifications(): Promise<NotificationResult>;
    submitFeedback(messageId: string, rating: string, reason?: string): Promise<FeedbackResult>;
    getFeedbackStats(): Promise<FeedbackStats>;
    listReasoningModes(): Promise<ReasoningMode[]>;
    submitReason(task: string, mode: string, maxPaths: number, maxRefineRounds: number, coverageEnabled: boolean): Promise<ReasoningResult>;
    submitReasoningFeedback(traceId: string, data: ReasoningFeedbackInput): Promise<ReasoningFeedbackResult>;
    listReasoningHistory(limit?: number): Promise<ReasoningHistoryItem[]>;
    getCostUsage(): Promise<CostUsage>;
    getCostBudget(): Promise<CostBudget>;
    getCostQuota(): Promise<CostQuota>;
    listSchedulerTasks(): Promise<SchedulerTask[]>;
    createSchedulerTask(data: CreateSchedulerTaskInput): Promise<SchedulerTask>;
    updateSchedulerTask(id: string, data: UpdateSchedulerTaskInput): Promise<SchedulerTask>;
    deleteSchedulerTask(id: string): Promise<DeletedResourceResult>;
    listEvalDatasets(): Promise<EvalDataset[]>;
    seedBuiltinDatasets(): Promise<SeedDatasetsResult>;
    runEvalDataset(id: string): Promise<EvalRun>;
    search(query: string, limit?: number): Promise<SearchResult[]>;
    runDoctor(): Promise<DoctorReport>;
    executeCommand(command: string, timeout?: number): Promise<CommandResult>;
  }
}

ApiClient.prototype.getStats = function (this: ApiClient): Promise<PlatformStats> {
  return this.request<PlatformStats>('/stats');
};

ApiClient.prototype.listApiKeys = function (this: ApiClient) {
  return this.request<ApiKeyRecord[]>('/api-keys');
};

ApiClient.prototype.addApiKey = function (this: ApiClient, data: CreateApiKeyInput) {
  return this.request<ApiKeyRecord>('/api-keys', {
    method: 'POST',
    body: JSON.stringify(data),
  });
};

ApiClient.prototype.deleteApiKey = function (this: ApiClient, id: string) {
  return this.request<OkResult>(`/api-keys/${id}`, { method: 'DELETE' });
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
  return this.request<FeedbackResult>(`/feedback?${params.toString()}`, { method: 'POST' });
};

ApiClient.prototype.getFeedbackStats = function (this: ApiClient) {
  return this.request<FeedbackStats>('/feedback/stats');
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
): Promise<ReasoningResult> {
  const body = { task, mode, max_paths: maxPaths, max_refine_rounds: maxRefineRounds, coverage_enabled: coverageEnabled };

  return this.request<ReasoningResult>('/reason', {
    method: 'POST',
    body: JSON.stringify(body),
  });
};

ApiClient.prototype.submitReasoningFeedback = function (this: ApiClient, traceId: string, data: ReasoningFeedbackInput) {
  return this.request<ReasoningFeedbackResult>(`/reason/${traceId}/feedback`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
};

ApiClient.prototype.listReasoningHistory = function (this: ApiClient, limit = 50) {
  return this.request<ReasoningHistoryItem[]>(`/reason/history?limit=${limit}`);
};

ApiClient.prototype.getCostUsage = function (this: ApiClient) {
  return this.request<CostUsage>('/cost/usage');
};

ApiClient.prototype.getCostBudget = function (this: ApiClient) {
  return this.request<CostBudget>('/cost/budget');
};

ApiClient.prototype.getCostQuota = function (this: ApiClient) {
  return this.request<CostQuota>('/cost/quota');
};

ApiClient.prototype.listSchedulerTasks = function (this: ApiClient) {
  return this.request<SchedulerTask[]>('/scheduler/tasks');
};

ApiClient.prototype.createSchedulerTask = function (this: ApiClient, data: CreateSchedulerTaskInput) {
  return this.request<SchedulerTask>('/scheduler/tasks', {
    method: 'POST',
    body: JSON.stringify(data),
  });
};

ApiClient.prototype.updateSchedulerTask = function (this: ApiClient, id: string, data: UpdateSchedulerTaskInput) {
  return this.request<SchedulerTask>(`/scheduler/tasks/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  });
};

ApiClient.prototype.deleteSchedulerTask = function (this: ApiClient, id: string) {
  return this.request<DeletedResourceResult>(`/scheduler/tasks/${id}`, { method: 'DELETE' });
};

ApiClient.prototype.listEvalDatasets = function (this: ApiClient) {
  return this.request<EvalDataset[]>('/eval/datasets');
};

ApiClient.prototype.seedBuiltinDatasets = function (this: ApiClient) {
  return this.request<SeedDatasetsResult>('/eval/datasets/seed-builtin', { method: 'POST' });
};

ApiClient.prototype.runEvalDataset = function (this: ApiClient, id: string) {
  return this.request<EvalRun>(`/eval/datasets/${id}/run`, { method: 'POST' });
};

ApiClient.prototype.search = function (this: ApiClient, query: string, limit = 20) {
  return this.request<SearchResult[]>(`/search?q=${encodeURIComponent(query)}&limit=${limit}`);
};

ApiClient.prototype.runDoctor = function (this: ApiClient) {
  return this.request<DoctorReport>('/doctor');
};

ApiClient.prototype.executeCommand = function (this: ApiClient, command: string, timeout?: number) {
  return this.request<CommandResult>('/terminal/execute', {
    method: 'POST',
    body: JSON.stringify({ command, timeout }),
  });
};
