import type { JsonObject, OkResult } from './common';

export type PluginStatus = 'enabled' | 'disabled' | 'installed' | 'error';

export interface PluginRecord {
  id: string;
  plugin_key?: string;
  name: string;
  description: string;
  category: string;
  version: string;
  author?: string;
  type: 'skill' | 'mcp' | 'prompt';
  source: string;
  status: PluginStatus;
  is_installed: boolean;
  is_enabled: boolean;
  icon?: string;
  config?: JsonObject;
  tools?: string[];
  tags?: string[];
  popularity?: number;
  error?: string | null;
}

export interface MarketplaceSkill {
  id: string;
  name: string;
  description: string;
  category: string;
  icon: string;
  tools: string[];
}

export type PluginMarketplace = PluginRecord[];

export interface PluginToggleResult extends OkResult {
  id: string;
  is_enabled: boolean;
  status: string;
}

export interface PluginDeleteResult extends OkResult {
  deleted: string;
}
