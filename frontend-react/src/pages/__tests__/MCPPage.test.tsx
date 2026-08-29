import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { MCPPage } from '../MCPPage';

const apiMocks = vi.hoisted(() => ({
  listMCPServers: vi.fn(),
  listMCPCategories: vi.fn(),
  installMCPServer: vi.fn(),
  deleteMCPServer: vi.fn(),
}));

vi.mock('../../api', () => ({ api: apiMocks }));

const availableServer = {
  id: 'server-1',
  name: 'Files Server',
  description: 'File tools',
  category: 'productivity',
  author: 'Climber',
  is_builtin: false,
  is_installed: false,
  tags: ['files'],
  install_config: {},
  popularity: 5,
};

describe('MCPPage server actions', () => {
  beforeEach(() => {
    Object.values(apiMocks).forEach(mock => mock.mockReset());
    apiMocks.listMCPServers.mockResolvedValue([availableServer]);
    apiMocks.listMCPCategories.mockResolvedValue(['productivity']);
  });

  it('shows an error and re-enables install after installation fails', async () => {
    const user = userEvent.setup();
    apiMocks.installMCPServer.mockRejectedValueOnce(new Error('Install failed'));
    render(<MCPPage />);

    const installButton = await screen.findByRole('button', { name: '安装 Files Server' });
    await user.click(installButton);

    expect(await screen.findByRole('alert')).toHaveTextContent('安装 MCP 服务器失败，请重试');
    expect(installButton).toBeEnabled();
  });

  it('shows an error and keeps the server installed after uninstall fails', async () => {
    const user = userEvent.setup();
    apiMocks.listMCPServers.mockResolvedValueOnce([{ ...availableServer, is_installed: true }]);
    apiMocks.deleteMCPServer.mockRejectedValueOnce(new Error('Uninstall failed'));
    render(<MCPPage />);

    const uninstallButton = await screen.findByRole('button', { name: '卸载 Files Server' });
    await user.click(uninstallButton);

    expect(await screen.findByRole('alert')).toHaveTextContent('卸载 MCP 服务器失败，请重试');
    expect(uninstallButton).toBeEnabled();
  });
});
