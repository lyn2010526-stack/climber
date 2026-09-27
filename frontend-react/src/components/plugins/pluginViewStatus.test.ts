import { describe, expect, it } from 'vitest';
import { normalizePluginStatus, pluginViewLabel } from './pluginViewStatus';

describe('plugin resource status vocabulary', () => {
  it('keeps missing and unknown backend values unreported', () => {
    expect(normalizePluginStatus(undefined)).toBe('unknown');
    expect(normalizePluginStatus('')).toBe('unknown');
    expect(normalizePluginStatus('pending')).toBe('unknown');
    expect(normalizePluginStatus('installed')).toBe('installed');
  });

  it('provides an explicit label for every view status', () => {
    const translate = ((key: string, options?: { defaultValue?: string }) => options?.defaultValue ?? key) as never;
    expect(pluginViewLabel('unknown', translate)).toBe('Unreported');
    expect(pluginViewLabel('enabled', translate)).toBe('Enabled');
  });
});
