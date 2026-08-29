// Workflows resource domain.
import type { WorkflowSummary, WorkflowTemplate } from '../types/api';
import type { CreateWorkflowInput, UpdateWorkflowInput, WorkflowRunResult } from '../types/workflows';
import { ApiClient } from './client';

declare module './client' {
  interface ApiClient {
    listWorkflows(): Promise<WorkflowSummary[]>;
    listWorkflowTemplates(): Promise<WorkflowTemplate[]>;
    createWorkflowFromTemplate(templateId: string): Promise<WorkflowSummary>;
    createWorkflow(data: CreateWorkflowInput): Promise<WorkflowSummary>;
    updateWorkflow(id: string, data: UpdateWorkflowInput): Promise<WorkflowSummary>;
    runWorkflow(id: string, inputs?: Record<string, string>): Promise<WorkflowRunResult>;
  }
}

ApiClient.prototype.listWorkflows = function (this: ApiClient): Promise<WorkflowSummary[]> {
  return this.request<WorkflowSummary[]>('/workflows/');
};

ApiClient.prototype.listWorkflowTemplates = function (this: ApiClient): Promise<WorkflowTemplate[]> {
  return this.request<WorkflowTemplate[]>('/workflows/templates');
};

ApiClient.prototype.createWorkflowFromTemplate = function (this: ApiClient, templateId: string): Promise<WorkflowSummary> {
  return this.request<WorkflowSummary>(`/workflows/templates/${templateId}`, {
    method: 'POST',
  });
};

ApiClient.prototype.createWorkflow = function (this: ApiClient, data: CreateWorkflowInput): Promise<WorkflowSummary> {
  return this.request<WorkflowSummary>('/workflows/', {
    method: 'POST',
    body: JSON.stringify(data),
  });
};

ApiClient.prototype.updateWorkflow = function (this: ApiClient, id: string, data: UpdateWorkflowInput): Promise<WorkflowSummary> {
  return this.request<WorkflowSummary>(`/workflows/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  });
};

ApiClient.prototype.runWorkflow = function (this: ApiClient, id: string, inputs?: Record<string, string>): Promise<WorkflowRunResult> {
  return this.request<WorkflowRunResult>(`/workflows/${id}/run`, {
    method: 'POST',
    body: JSON.stringify(inputs || {}),
  });
};
