// Traces resource domain.
import { ApiClient } from './client';

declare module './client' {
  interface ApiClient {
    listTraces(): Promise<any>;
    getTrace(traceId: string): Promise<any>;
  }
}

ApiClient.prototype.listTraces = function (this: ApiClient) {
  return this.request<any>('/traces/');
};

ApiClient.prototype.getTrace = function (this: ApiClient, traceId: string) {
  return this.request<any>(`/traces/${traceId}`);
};
