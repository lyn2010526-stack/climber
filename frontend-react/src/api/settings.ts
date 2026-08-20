// Settings resource domain.
import { ApiClient } from './client';

declare module './client' {
  interface ApiClient {
    getSettings(): Promise<any>;
    updateSettings(data: Record<string, any>): Promise<any>;
  }
}

ApiClient.prototype.getSettings = function (this: ApiClient) {
  return this.request<any>('/settings/');
};

ApiClient.prototype.updateSettings = function (this: ApiClient, data: Record<string, any>) {
  return this.request<any>('/settings/', {
    method: 'PATCH',
    body: JSON.stringify(data),
  });
};
