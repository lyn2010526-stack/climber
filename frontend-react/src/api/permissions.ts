// Permissions / approvals resource domain.
import { ApiClient } from './client';

export interface ApprovalRequest {
  id: string;
  session_id: string;
  tool_name: string;
  arguments: Record<string, unknown>;
  status: 'pending' | 'approved' | 'rejected' | 'expired';
  created_at: string;
  resolved_at?: string | null;
  resolved_by?: string | null;
  reason?: string | null;
}

export interface ApprovalListResponse {
  requests: ApprovalRequest[];
  total: number;
}

declare module './client' {
  interface ApiClient {
    listPendingApprovals(sessionId: string, signal?: AbortSignal): Promise<ApprovalListResponse>;
    resolvePermission(toolCallId: string, decision: 'allow' | 'deny'): Promise<any>;
    getPermissionConfig(): Promise<any>;
    updatePermissionConfig(data: { mode?: string; rules?: unknown[]; allowed_tools?: string[]; denied_tools?: string[] }): Promise<any>;
  }
}

ApiClient.prototype.listPendingApprovals = async function (this: ApiClient, sessionId: string, signal?: AbortSignal): Promise<ApprovalListResponse> {
  const query = new URLSearchParams({ session_id: sessionId });
  const options = signal ? { signal } : {};
  return this.request<ApprovalListResponse>(`/approvals/pending?${query}`, options, false);
};

ApiClient.prototype.resolvePermission = function (this: ApiClient, toolCallId: string, decision: 'allow' | 'deny') {
  return this.request<any>(`/permissions/resolve`, {
    method: 'POST',
    body: JSON.stringify({ tool_call_id: toolCallId, decision }),
  });
};

ApiClient.prototype.getPermissionConfig = function (this: ApiClient) {
  return this.request<any>('/permissions/config');
};

ApiClient.prototype.updatePermissionConfig = function (this: ApiClient, data: { mode?: string; rules?: unknown[]; allowed_tools?: string[]; denied_tools?: string[] }) {
  return this.request<any>('/permissions/config', {
    method: 'PUT',
    body: JSON.stringify(data),
  });
};
