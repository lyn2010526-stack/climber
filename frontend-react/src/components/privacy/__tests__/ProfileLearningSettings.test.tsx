import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { ProfileLearningSettings } from '../ProfileLearningSettings';
import { SettingsPage } from '../../../pages/SettingsPage';
import type { ProfileSettings } from '../../../lib/profileApi';
import i18n from '../../../i18n/config';

vi.mock('../../../api', async (original) => {
  const mod = await original<typeof import('../../../api')>();
  // Keep the real transport (fetch is stubbed per test); only the identity
  // probe is replaced because SettingsPage must not depend on it here.
  mod.api.getCurrentUser = vi.fn().mockResolvedValue({ username: '测试用户' });
  return mod;
});
vi.mock('../LocalPinSettings', () => ({ LocalPinSettings: () => <div>本地应用锁 PIN</div> }));

const initial: ProfileSettings = {
  enabled: false, show_raw_profile: false, consent_required: true,
  consent_version: null, consented_at: null,
  notice_version: '2026-10-02-v1',
  notice: '配置的模型服务可能接收习惯摘要。画像事件不保存指令正文，不采集外部隐私数据。',
};
const fetchMock = vi.fn<typeof fetch>();
let stored: ProfileSettings;
const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), {
  status, headers: { 'Content-Type': 'application/json' },
});
const writes = () => fetchMock.mock.calls.filter(([, options]) => options?.method === 'PUT');

// Mock HTTP responses only: these tests do not contact a backend or verify database persistence.
describe('习惯学习设置（模拟 API 定向测试）', () => {
  beforeEach(async () => {
    await i18n.changeLanguage('zh-CN');
    localStorage.clear();
    stored = { ...initial };
    fetchMock.mockReset();
    fetchMock.mockImplementation(async (url, options) => {
      expect(url).toBe('/api/v1/profile/settings');
      if (options?.method === 'PUT') {
        const body = JSON.parse(options.body as string);
        stored = { ...stored, ...body, consent_required: body.enabled ? false : stored.consent_required };
      }
      return json(stored);
    });
    vi.stubGlobal('fetch', fetchMock);
  });

  afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

  async function openConsent() {
    render(<ProfileLearningSettings />);
    fireEvent.click(await screen.findByRole('button', { name: '开启习惯学习' }));
    return screen.getByRole('checkbox');
  }

  it('在 SettingsPage 现有隐私锁旁显示入口，仅请求设置', async () => {
    render(<SettingsPage />);
    expect(screen.getByText('本地应用锁 PIN')).toBeInTheDocument();
    await screen.findByRole('button', { name: '开启习惯学习' });
    expect(screen.getByText(initial.notice)).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /清除|画像/ })).not.toBeInTheDocument();
    expect(fetchMock.mock.calls.every(([url]) => url === '/api/v1/profile/settings')).toBe(true);
    expect(writes()).toHaveLength(0);
  });

  it('首次启用须主动勾选，确认后提交服务器告知版本并隐藏原始画像', async () => {
    const checkbox = await openConsent();
    const submit = screen.getByRole('button', { name: '同意并开启' });
    expect(checkbox).not.toBeChecked();
    expect(submit).toBeDisabled();
    fireEvent.submit(submit.closest('form')!);
    expect(writes()).toHaveLength(0);
    fireEvent.click(checkbox);
    fireEvent.click(submit);
    await screen.findByText('习惯学习已开启，原始画像保持隐藏。');
    expect(JSON.parse(writes()[0][1]!.body as string)).toEqual({
      enabled: true, consent_version: initial.notice_version, show_raw_profile: false,
    });
  });

  it('取消同意不会保存，再次打开保持未勾选', async () => {
    fireEvent.click(await openConsent());
    fireEvent.click(screen.getByRole('button', { name: '取消' }));
    expect(writes()).toHaveLength(0);
    fireEvent.click(screen.getByRole('button', { name: '开启习惯学习' }));
    expect(screen.getByRole('checkbox')).not.toBeChecked();
  });

  it('关闭只提交停用与隐藏设置，保留同意记录，不调用清除接口', async () => {
    stored = { ...stored, enabled: true, consent_required: false, consent_version: initial.notice_version, consented_at: '2026-10-02T12:00:00Z' };
    render(<ProfileLearningSettings />);
    fireEvent.click(await screen.findByRole('button', { name: '关闭习惯学习' }));
    await screen.findByText('习惯学习已关闭，已有数据保留。');
    expect(JSON.parse(writes()[0][1]!.body as string)).toEqual({ enabled: false, show_raw_profile: false });
    expect(stored.consented_at).toBe('2026-10-02T12:00:00Z');
  });

  it('已同意当前版本时可以重新启用，刷新后读取保存状态', async () => {
    stored = { ...stored, consent_required: false, consent_version: initial.notice_version, consented_at: '2026-10-02T12:00:00Z' };
    render(<ProfileLearningSettings />);
    fireEvent.click(await screen.findByRole('button', { name: '开启习惯学习' }));
    await screen.findByRole('button', { name: '关闭习惯学习' });
    expect(JSON.parse(writes()[0][1]!.body as string)).toEqual({ enabled: true, show_raw_profile: false });
    cleanup();
    render(<ProfileLearningSettings />);
    await screen.findByRole('button', { name: '关闭习惯学习' });
    expect(screen.queryByRole('checkbox')).not.toBeInTheDocument();
  });

  it('告知版本更新后重新取得明确同意，使用新的服务器版本', async () => {
    stored = { ...stored, consent_version: 'old-version', notice_version: 'next-version' };
    fireEvent.click(await openConsent());
    fireEvent.click(screen.getByRole('button', { name: '同意并开启' }));
    await screen.findByRole('button', { name: '关闭习惯学习' });
    expect(JSON.parse(writes()[0][1]!.body as string).consent_version).toBe('next-version');
  });

  it.each([401, 403, 500])('加载失败（%s）时禁止启用，支持重新加载', async (status) => {
    fetchMock.mockResolvedValueOnce(json({ detail: 'unavailable' }, status));
    render(<ProfileLearningSettings />);
    await screen.findByRole('alert');
    expect(screen.queryByRole('button', { name: '开启习惯学习' })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '重新加载习惯学习设置' }));
    await screen.findByRole('button', { name: '开启习惯学习' });
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });

  it('保存失败时保持原状态和同意选项，可再次提交', async () => {
    fireEvent.click(await openConsent());
    fetchMock.mockResolvedValueOnce(json({ detail: 'Forbidden' }, 403));
    fireEvent.click(screen.getByRole('button', { name: '同意并开启' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('保存失败，当前状态保持不变');
    expect(screen.getByText('当前状态：已关闭')).toBeInTheDocument();
    expect(screen.getByRole('checkbox')).toBeChecked();
    fireEvent.click(screen.getByRole('button', { name: '同意并开启' }));
    await screen.findByRole('button', { name: '关闭习惯学习' });
  });

  it('停用失败时仍显示已开启', async () => {
    stored = { ...stored, enabled: true, consent_required: false };
    render(<ProfileLearningSettings />);
    const button = await screen.findByRole('button', { name: '关闭习惯学习' });
    fetchMock.mockRejectedValueOnce(new Error('network offline'));
    fireEvent.click(button);
    await screen.findByRole('alert');
    expect(screen.getByText('当前状态：已开启')).toBeInTheDocument();
    expect(button).toBeEnabled();
  });

  it('保存期间禁用操作，防止重复提交', async () => {
    fireEvent.click(await openConsent());
    let resolve!: (response: Response) => void;
    fetchMock.mockImplementationOnce(() => new Promise<Response>((done) => { resolve = done; }));
    const button = screen.getByRole('button', { name: '同意并开启' });
    fireEvent.click(button);
    expect(button).toBeDisabled();
    expect(screen.getByRole('checkbox')).toBeDisabled();
    expect(screen.getByRole('button', { name: '取消' })).toBeDisabled();
    fireEvent.click(button);
    expect(writes()).toHaveLength(1);
    resolve(json({ ...stored, enabled: true, consent_required: false }));
    await waitFor(() => expect(screen.getByRole('button', { name: '关闭习惯学习' })).toBeEnabled());
  });

  it('设置 API 携带项目认证令牌', async () => {
    localStorage.setItem('auth_token', 'mock-project-token');
    render(<ProfileLearningSettings />);
    await screen.findByRole('button', { name: '开启习惯学习' });
    expect(fetchMock).toHaveBeenCalledWith('/api/v1/profile/settings', expect.objectContaining({
      headers: expect.objectContaining({ Authorization: 'Bearer mock-project-token' }),
    }));
  });
});
