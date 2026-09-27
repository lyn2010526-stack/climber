import { CheckCircle2, CircleAlert, CircleDashed, CircleHelp, CircleSlash } from 'lucide-react';
import type { TFunction } from '../../i18n';

/**
 * The plugin lifecycle vocabulary, shared by the catalog page and the manage
 * page so a plugin reads the same in both. `unknown` is deliberately separate
 * from `installed`: a status the backend did not declare must not be painted as
 * "present on this machine".
 *
 * This module owns the whole mapping -- status to icon, to tone, to label key --
 * so a page cannot invent its own copy of the vocabulary and drift from the
 * other one. The raw value the backend sent is kept alongside the resolved
 * status in `data-plugin-status` so a test or a bug report can still name it.
 */
export type PluginViewStatus = 'enabled' | 'disabled' | 'installed' | 'error' | 'unknown';

export const PLUGIN_VIEW_TONES: Record<PluginViewStatus, string> = {
  enabled: 'text-[var(--color-text-secondary)]',
  disabled: 'text-[var(--color-text-muted)]',
  installed: 'text-[var(--color-text-muted)]',
  error: 'text-[var(--color-error)]',
  unknown: 'text-[var(--color-text-disabled)]',
};

export const PLUGIN_VIEW_ICONS = {
  enabled: CheckCircle2,
  disabled: CircleSlash,
  installed: CircleDashed,
  error: CircleAlert,
  unknown: CircleHelp,
} as const;

const PLUGIN_VIEW_LABEL_KEYS: Record<PluginViewStatus, string> = {
  enabled: 'plugins.status.enabled',
  disabled: 'plugins.status.disabled',
  installed: 'plugins.status.installed',
  error: 'plugins.status.error',
  unknown: 'plugins.status.unknown',
};

export function pluginViewLabel(status: PluginViewStatus, t: TFunction): string {
  const defaults: Record<PluginViewStatus, string> = {
    enabled: 'Enabled',
    disabled: 'Disabled',
    installed: 'Installed',
    error: 'Error',
    unknown: 'Unreported',
  };
  return t(PLUGIN_VIEW_LABEL_KEYS[status], { defaultValue: defaults[status] });
}

/**
 * The statuses the backend declares on `PluginRecord.status`
 * (app/storage/models_plugins.py). `unknown` is intentionally absent: it is the
 * result of normalisation, never a value the API is allowed to send.
 */
const REPORTED_STATUSES = new Set<string>(['enabled', 'disabled', 'installed', 'error']);

/**
 * Anything the backend has not declared lands on `unknown`. Defaulting to
 * `installed` would tell the user a plugin is present on the machine when the
 * API said nothing at all.
 */
export function normalizePluginStatus(status: string | null | undefined): PluginViewStatus {
  const value = (status ?? '').trim().toLowerCase();
  return REPORTED_STATUSES.has(value) ? (value as PluginViewStatus) : 'unknown';
}

/** Icon, tone and label for a status, resolved once for a single render site. */
export function pluginViewDescriptor(status: PluginViewStatus, t: TFunction) {
  return {
    icon: PLUGIN_VIEW_ICONS[status],
    tone: PLUGIN_VIEW_TONES[status],
    label: pluginViewLabel(status, t),
  };
}
