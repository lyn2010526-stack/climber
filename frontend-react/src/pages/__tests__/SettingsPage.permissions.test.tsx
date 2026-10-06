import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { SettingsPage } from '../SettingsPage';
import { api, type PermissionTier } from '../../api';

vi.mock('../../i18n', () => ({
  useI18n: () => ({ t: (key: string) => key }),
  useTranslation: () => ({ t: (key: string) => key }),
}));
const t = (key: string) => key;

const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), {
  status, headers: { 'Content-Type': 'application/json' },
});
const fetchMock = vi.fn<typeof fetch>();
let tier: PermissionTier;
let mode: string;

beforeEach(() => {
  localStorage.clear();
  tier = 'partial_write';
  mode = 'auto';
  fetchMock.mockReset();
  fetchMock.mockImplementation(async (url, options) => {
    if (url === '/api/v1/profile/settings') return json({
      enabled: false, show_raw_profile: false, consent_required: true,
      consent_version: null, consented_at: null,
      notice_version: '2026-10-02-v1', notice: '习惯学习告知（模拟 API）',
    });
    if (url === '/api/v1/auth/me') return json({ username: 'tester' });
    if (url === '/api/v1/auth/health') return json({ authentication_enabled: false });
    if (url === '/api/v1/reasoning/permission-tiers') return json({
      current: { tier, mode }, tiers: [], tool_states: [],
    });
    if (url === '/api/v1/permissions/config' && options?.method === 'PUT') {
      ({ tier, mode } = JSON.parse(options.body as string));
      return json({ status: 'updated', tier, mode });
    }
    throw new Error(`Unexpected request: ${String(url)}`);
  });
  vi.stubGlobal('fetch', fetchMock);
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

async function openSecurity() {
  render(<SettingsPage />);
  fireEvent.click(screen.getByRole('button', { name: /settings.security/ }));
  return screen.findByRole('button', { name: /settings.permission_level_partial/ });
}

it('selects the actual capability tier when mode differs', async () => {
  expect(await openSecurity()).toHaveAttribute('aria-pressed', 'true');
  expect(screen.getByRole('button', { name: /settings.permission_level_full/ }))
    .toHaveAttribute('aria-pressed', 'false');
});

it.each([
  ['read_only', 'plan', 'readonly'],
  ['partial_write', 'default', 'partial'],
  ['full_write', 'auto', 'full'],
] as const)('writes and reloads %s with its mode', async (nextTier, nextMode, label) => {
  await openSecurity();
  const button = screen.getByRole('button', { name: new RegExp(`settings.permission_level_${label}`) });
  fireEvent.click(button);
  await waitFor(() => expect(fetchMock).toHaveBeenCalledWith('/api/v1/permissions/config', expect.objectContaining({
    method: 'PUT', body: JSON.stringify({ tier: nextTier, mode: nextMode }),
  })));
  await waitFor(() => expect(button).toHaveAttribute('aria-pressed', 'true'));
  cleanup();
  await openSecurity();
  expect(screen.getByRole('button', { name: new RegExp(`settings.permission_level_${label}`) }))
    .toHaveAttribute('aria-pressed', 'true');
});

it('uses the returned tier to render the saved policy', async () => {
  await openSecurity();
  vi.spyOn(api, 'updatePermissionConfig').mockResolvedValue({ status: 'updated', mode: 'default', tier: 'partial_write' });
  fireEvent.click(screen.getByRole('button', { name: /settings.permission_level_full/ }));
  await waitFor(() => expect(api.updatePermissionConfig).toHaveBeenCalled());
  expect(screen.getByRole('button', { name: /settings.permission_level_partial/ }))
    .toHaveAttribute('aria-pressed', 'true');
});

it('round trips the complete policy through the API client', async () => {
  const policy = {
    tier: 'partial_write' as const, mode: 'default',
    rules: [{ decision: 'deny', tool: 'file_delete', pattern: null, description: 'Keep files' }],
    allowed_tools: ['read_file'], denied_tools: ['fetch'],
  };
  fetchMock.mockImplementation(async (url, options) => {
    expect(url).toBe('/api/v1/permissions/config');
    if (options?.method === 'PUT') {
      expect(JSON.parse(options.body as string)).toEqual(policy);
      return json({ status: 'updated', tier: policy.tier, mode: policy.mode });
    }
    return json(policy);
  });
  expect(await api.updatePermissionConfig(policy)).toEqual({ status: 'updated', tier: policy.tier, mode: policy.mode });
  expect(await api.getPermissionConfig()).toEqual(policy);
});

it('retains the current tier and shows a failed update', async () => {
  await openSecurity();
  vi.spyOn(api, 'updatePermissionConfig').mockRejectedValue(new Error('Policy update failed'));
  fireEvent.click(screen.getByRole('button', { name: /settings.permission_level_full/ }));
  expect(await screen.findByRole('alert')).toHaveTextContent('Policy update failed');
  expect(screen.getByRole('button', { name: /settings.permission_level_partial/ }))
    .toHaveAttribute('aria-pressed', 'true');
});

it('hides permission controls when the policy read is forbidden', async () => {
  vi.spyOn(api, 'getPermissionTiers').mockRejectedValue(new Error('Forbidden'));
  render(<SettingsPage />);
  fireEvent.click(screen.getByRole('button', { name: /settings.security/ }));
  await screen.findByText(t('settings_page.auth_disabled'));
  expect(screen.queryByRole('button', { name: /settings.permission_level_readonly/ })).not.toBeInTheDocument();
});
