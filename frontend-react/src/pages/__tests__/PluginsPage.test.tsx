import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { PluginsPage } from '../PluginsPage';

const apiMocks = vi.hoisted(() => ({
  listPlugins: vi.fn(),
  importPlugin: vi.fn(),
  installPlugin: vi.fn(),
  uninstallPlugin: vi.fn(),
  enablePlugin: vi.fn(),
  disablePlugin: vi.fn(),
}));

vi.mock('../../api', () => ({
  api: {
    ...apiMocks,
  },
}));

describe('PluginsPage import dialog', () => {
  beforeEach(() => {
    apiMocks.listPlugins.mockReset();
    apiMocks.importPlugin.mockReset();
    apiMocks.installPlugin.mockReset();
    apiMocks.uninstallPlugin.mockReset();
    apiMocks.enablePlugin.mockReset();
    apiMocks.disablePlugin.mockReset();
    apiMocks.listPlugins.mockResolvedValue([]);
  });

  it('shows a retryable error when plugins fail to load', async () => {
    const user = userEvent.setup();
    apiMocks.listPlugins.mockRejectedValueOnce(new Error('Service unavailable'));
    render(<PluginsPage />);

    expect(await screen.findByRole('alert')).toHaveTextContent('加载插件失败');
    expect(screen.queryByText('未找到插件')).not.toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: '重试加载插件' }));

    expect(await screen.findByText('未找到插件')).toBeInTheDocument();
    expect(apiMocks.listPlugins).toHaveBeenCalledTimes(2);
  });

  it('shows an actionable error when plugin installation fails', async () => {
    const user = userEvent.setup();
    apiMocks.listPlugins.mockResolvedValueOnce([{
      id: 'plugin-1',
      name: 'Example Plugin',
      description: 'Example description',
      type: 'skill',
      source: 'marketplace',
      status: 'disabled',
      category: 'productivity',
      version: '1.0.0',
    }]);
    apiMocks.installPlugin.mockRejectedValueOnce(new Error('Install failed'));
    render(<PluginsPage />);

    await user.click(await screen.findByRole('button', { name: '安装 Example Plugin' }));

    expect(await screen.findByRole('alert')).toHaveTextContent('安装插件失败，请重试');
  });

  it('keeps the import dialog open and reports import failures', async () => {
    const user = userEvent.setup();
    apiMocks.importPlugin.mockRejectedValueOnce(new Error('Import failed'));
    render(<PluginsPage />);

    await user.click(await screen.findByRole('button', { name: '导入插件' }));
    await user.type(screen.getByRole('textbox', { name: '源地址' }), 'https://example.com/plugin.json');
    await user.click(screen.getByRole('button', { name: /^导入$/ }));

    expect(await screen.findByRole('alert')).toHaveTextContent('导入插件失败，请重试');
    expect(screen.getByRole('dialog', { name: '导入插件' })).toBeInTheDocument();
  });

  it('exposes dialog semantics and associated form labels', async () => {
    const user = userEvent.setup();
    render(<PluginsPage />);

    await user.click(await screen.findByRole('button', { name: '导入插件' }));

    expect(screen.getByRole('dialog', { name: '导入插件' })).toBeInTheDocument();
    expect(screen.getByRole('textbox', { name: '源地址' })).toBeInTheDocument();
    expect(screen.getByRole('textbox', { name: '名称（可选）' })).toBeInTheDocument();
    expect(screen.getByRole('combobox', { name: '类型' })).toBeInTheDocument();
  });

  it('closes with Escape and restores focus to the import trigger', async () => {
    const user = userEvent.setup();
    render(<PluginsPage />);
    const trigger = await screen.findByRole('button', { name: '导入插件' });

    await user.click(trigger);
    await user.keyboard('{Escape}');

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    expect(trigger).toHaveFocus();
  });
});
