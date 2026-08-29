// Plugins resource domain.
import type { JsonObject } from '../types/common';
import type { PluginDeleteResult, PluginMarketplace, PluginRecord, PluginToggleResult } from '../types/plugins';
import { ApiClient } from './client';

declare module './client' {
  interface ApiClient {
    listPlugins(type?: string, status?: string): Promise<PluginRecord[]>;
    getMarketplace(): Promise<PluginMarketplace>;
    installPlugin(id: string, config?: JsonObject): Promise<PluginRecord>;
    uninstallPlugin(id: string): Promise<PluginDeleteResult>;
    enablePlugin(id: string): Promise<PluginToggleResult>;
    disablePlugin(id: string): Promise<PluginToggleResult>;
    importPlugin(sourceUrl: string, name?: string, type?: string): Promise<PluginRecord>;
  }
}

ApiClient.prototype.listPlugins = function (this: ApiClient, type?: string, status?: string): Promise<PluginRecord[]> {
  const params = new URLSearchParams();
  if (type) params.set('type', type);
  if (status) params.set('status', status);
  const qs = params.toString();
  return this.request<PluginRecord[]>(`/plugins${qs ? '?' + qs : ''}`);
};

ApiClient.prototype.getMarketplace = function (this: ApiClient): Promise<PluginMarketplace> {
  return this.request<PluginMarketplace>('/plugins/marketplace');
};

ApiClient.prototype.installPlugin = function (this: ApiClient, id: string, config?: JsonObject): Promise<PluginRecord> {
  return this.request<PluginRecord>(`/plugins/${id}/install`, {
    method: 'POST',
    body: JSON.stringify(config || {}),
  });
};

ApiClient.prototype.uninstallPlugin = function (this: ApiClient, id: string): Promise<PluginDeleteResult> {
  return this.request<PluginDeleteResult>(`/plugins/${id}/uninstall`, { method: 'POST' });
};

ApiClient.prototype.enablePlugin = function (this: ApiClient, id: string): Promise<PluginToggleResult> {
  return this.request<PluginToggleResult>(`/plugins/${id}/enable`, { method: 'POST' });
};

ApiClient.prototype.disablePlugin = function (this: ApiClient, id: string): Promise<PluginToggleResult> {
  return this.request<PluginToggleResult>(`/plugins/${id}/disable`, { method: 'POST' });
};

ApiClient.prototype.importPlugin = function (this: ApiClient, sourceUrl: string, name?: string, type?: string): Promise<PluginRecord> {
  return this.request<PluginRecord>('/plugins/import', {
    method: 'POST',
    body: JSON.stringify({ source_url: sourceUrl, name: name || '', type: type || 'mcp' }),
  });
};
