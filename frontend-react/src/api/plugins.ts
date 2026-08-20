// Plugins resource domain.
import { ApiClient } from './client';

declare module './client' {
  interface ApiClient {
    listPlugins(type?: string, status?: string): Promise<any[]>;
    getMarketplace(): Promise<any>;
    installPlugin(id: string, config?: Record<string, any>): Promise<any>;
    uninstallPlugin(id: string): Promise<any>;
    enablePlugin(id: string): Promise<any>;
    disablePlugin(id: string): Promise<any>;
    importPlugin(sourceUrl: string, name?: string, type?: string): Promise<any>;
  }
}

ApiClient.prototype.listPlugins = function (this: ApiClient, type?: string, status?: string) {
  const params = new URLSearchParams();
  if (type) params.set('type', type);
  if (status) params.set('status', status);
  const qs = params.toString();
  return this.request<any[]>(`/plugins${qs ? '?' + qs : ''}`);
};

ApiClient.prototype.getMarketplace = function (this: ApiClient) {
  return this.request<any>('/plugins/marketplace');
};

ApiClient.prototype.installPlugin = function (this: ApiClient, id: string, config?: Record<string, any>) {
  return this.request<any>(`/plugins/${id}/install`, {
    method: 'POST',
    body: JSON.stringify(config || {}),
  });
};

ApiClient.prototype.uninstallPlugin = function (this: ApiClient, id: string) {
  return this.request<any>(`/plugins/${id}/uninstall`, { method: 'POST' });
};

ApiClient.prototype.enablePlugin = function (this: ApiClient, id: string) {
  return this.request<any>(`/plugins/${id}/enable`, { method: 'POST' });
};

ApiClient.prototype.disablePlugin = function (this: ApiClient, id: string) {
  return this.request<any>(`/plugins/${id}/disable`, { method: 'POST' });
};

ApiClient.prototype.importPlugin = function (this: ApiClient, sourceUrl: string, name?: string, type?: string) {
  return this.request<any>('/plugins/import', {
    method: 'POST',
    body: JSON.stringify({ source_url: sourceUrl, name: name || '', type: type || 'mcp' }),
  });
};
