import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { AgentsPage } from '../AgentsPage';

const apiMocks = vi.hoisted(() => ({
  listAgents: vi.fn(),
  listTools: vi.fn(),
  listModels: vi.fn(),
  listSkills: vi.fn(),
}));

vi.mock('../../api', () => ({
  api: {
    ...apiMocks,
    createAgent: vi.fn(),
    deleteAgent: vi.fn(),
  },
}));

describe('AgentsPage creation form', () => {
  beforeEach(() => {
    apiMocks.listAgents.mockResolvedValue([]);
    apiMocks.listTools.mockResolvedValue([]);
    apiMocks.listModels.mockResolvedValue([]);
    apiMocks.listSkills.mockResolvedValue([]);
  });

  it('associates every model configuration label with its control', async () => {
    const user = userEvent.setup();
    render(<AgentsPage />);

    await user.click(await screen.findByRole('button', { name: '新建智能体' }));

    expect(screen.getByRole('textbox', { name: '智能体名称' })).toBeInTheDocument();
    expect(screen.getByRole('combobox', { name: '提供商' })).toBeInTheDocument();
    expect(screen.getByRole('combobox', { name: '模型' })).toBeInTheDocument();
    expect(screen.getByLabelText('API 密钥')).toHaveAttribute('type', 'password');
    expect(screen.getByRole('textbox', { name: 'Base URL（可选）' })).toBeInTheDocument();
    expect(screen.getByRole('textbox', { name: '系统提示词（可选）' })).toBeInTheDocument();
  });

  it('loads models and skills from the catalog for agent creation', async () => {
    apiMocks.listModels.mockResolvedValue([
      { provider: 'custom', model_id: 'model-x', label: 'Model X' },
    ]);
    apiMocks.listSkills.mockResolvedValue([
      { id: 'skill-x', name: 'Research', description: 'Research skill', category: 'research', tools: [] },
    ]);
    const user = userEvent.setup();
    render(<AgentsPage />);

    await user.click(await screen.findByRole('button', { name: '新建智能体' }));
    expect(screen.getByRole('option', { name: 'Model X' })).toBeInTheDocument();
    await user.type(screen.getByRole('textbox', { name: '智能体名称' }), 'Research agent');
    await user.type(screen.getByLabelText('API 密钥'), 'test-key');
    await user.click(screen.getByRole('button', { name: /下一步/ }));
    expect(await screen.findByText('Research')).toBeInTheDocument();
  });

  it('shows a recoverable error when creation fails', async () => {
    const createAgent = vi.mocked((await import('../../api')).api.createAgent);
    createAgent.mockRejectedValueOnce(new Error('创建失败'));
    const user = userEvent.setup();
    render(<AgentsPage />);

    await user.click(await screen.findByRole('button', { name: '新建智能体' }));
    await user.type(screen.getByRole('textbox', { name: '智能体名称' }), 'Test agent');
    await user.type(screen.getByLabelText('API 密钥'), 'test-key');
    await user.click(screen.getByRole('button', { name: /下一步/ }));
    await user.click(screen.getByRole('button', { name: /下一步/ }));
    await user.click(screen.getByRole('button', { name: '创建智能体' }));

    expect(await screen.findByText('创建失败')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '创建智能体' })).toBeInTheDocument();
  });

  it('sends selected skills and tools using the agent API contract', async () => {
    const createAgent = vi.mocked((await import('../../api')).api.createAgent);
    createAgent.mockResolvedValueOnce({ id: 'agent-1' });
    apiMocks.listTools.mockResolvedValue([{ name: 'search' }]);
    apiMocks.listSkills.mockResolvedValue([
      { id: 'skill-x', name: 'Research', description: 'Research skill', category: 'research', tools: [] },
    ]);
    const user = userEvent.setup();
    render(<AgentsPage />);

    await user.click(await screen.findByRole('button', { name: '新建智能体' }));
    await user.type(screen.getByRole('textbox', { name: '智能体名称' }), 'Test agent');
    await user.type(screen.getByLabelText('API 密钥'), 'test-key');
    await user.click(screen.getByRole('button', { name: /下一步/ }));
    await user.click(screen.getByRole('button', { name: /Research Research skill/ }));
    await user.click(screen.getByRole('button', { name: /下一步/ }));
    await user.click(screen.getByRole('button', { name: 'search' }));
    await user.click(screen.getByRole('button', { name: '创建智能体' }));

    expect(createAgent).toHaveBeenCalledWith(expect.objectContaining({
      tool_ids: ['search'],
      skill_ids: ['skill-x'],
    }));
  });
});
