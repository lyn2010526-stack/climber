// Workflows resource domain.
import type { WorkflowSummary, WorkflowTemplate } from '../types/api';
import { ApiClient } from './client';

declare module './client' {
  interface ApiClient {
    listWorkflows(): Promise<WorkflowSummary[]>;
    listWorkflowTemplates(): Promise<WorkflowTemplate[]>;
    createWorkflowFromTemplate(templateId: string): Promise<WorkflowSummary>;
    createWorkflow(data: any): Promise<any>;
    updateWorkflow(id: string, data: any): Promise<any>;
    runWorkflow(id: string, inputs?: Record<string, string>): Promise<any>;
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

ApiClient.prototype.createWorkflow = function (this: ApiClient, data: any) {
  return this.request<any>('/workflows/', {
    method: 'POST',
    body: JSON.stringify(data),
  });
};

ApiClient.prototype.updateWorkflow = function (this: ApiClient, id: string, data: any) {
  return this.request<any>(`/workflows/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  });
};

ApiClient.prototype.runWorkflow = function (this: ApiClient, id: string, inputs?: Record<string, string>) {
  return this.request<any>(`/workflows/${id}/run`, {
    method: 'POST',
    body: JSON.stringify(inputs || {}),
  });
};
