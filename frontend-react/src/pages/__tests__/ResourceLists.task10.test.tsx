import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import i18n from '../../i18n';
import { api } from '../../api';
import { AgentsPage } from '../AgentsPage';
import { SkillsPage } from '../SkillsPage';

vi.mock('../../api', () => ({ api: {
  listAgents: vi.fn(), deleteAgent: vi.fn(), createAgent: vi.fn(),
  listTools: vi.fn(), listSkills: vi.fn(), updateSkill: vi.fn(),
} }));

const agent = { id: 'a1', name: 'Builder', provider: 'ollama', model_id: 'llama3.3', tool_ids: [], skill_ids: [] };
const skills = [
  { id: 1, name: 'Review', description: 'Inspect changes', category: 'quality', is_enabled: true, use_count: 3, tools: ['read'], path: '/skills/review' },
  { id: 2, name: 'Research', description: 'Find evidence', category: 'research', is_enabled: false, use_count: 0, tools: [], path: '/skills/research' },
];

beforeEach(async () => {
  vi.resetAllMocks();
  await i18n.changeLanguage('en');
  vi.mocked(api.listAgents).mockResolvedValue([agent] as any);
  vi.mocked(api.listSkills).mockResolvedValue({ skills } as any);
  vi.mocked(api.listTools).mockResolvedValue([]);
});

describe('Task 10 resource lists', () => {
  it('combines skill category and search filters and clears empty results', async () => {
    render(<SkillsPage />);
    await screen.findByText('Review');
    fireEvent.click(screen.getByRole('button', { name: 'quality' }));
    expect(screen.queryByText('Research')).toBeNull();
    fireEvent.change(screen.getByRole('textbox', { name: 'Search' }), { target: { value: 'evidence' } });
    expect(screen.getByText('No results')).toBeDefined();
    fireEvent.click(screen.getByRole('button', { name: 'Clear' }));
    expect(screen.getAllByRole('listitem')).toHaveLength(2);
  });

  it('preserves enabled state on update failure and retries the same payload', async () => {
    vi.mocked(api.updateSkill).mockRejectedValueOnce(new Error('Update unavailable')).mockResolvedValueOnce({} as any);
    render(<SkillsPage />);
    fireEvent.click(await screen.findByRole('button', { name: 'Deactivate: Review' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Update unavailable');
    expect(api.updateSkill).toHaveBeenCalledWith('1', { enabled: false });
    fireEvent.click(screen.getByRole('button', { name: 'Deactivate: Review' }));
    await screen.findByRole('button', { name: 'Activate: Review' });
    expect(screen.queryByRole('alert')).toBeNull();
  });

  it('retries a failed skill fetch without reloading the document', async () => {
    vi.mocked(api.listSkills).mockRejectedValueOnce(new Error('Offline'));
    render(<SkillsPage />);
    await screen.findByText('Offline');
    fireEvent.click(screen.getByRole('button', { name: 'Retry' }));
    await screen.findByText('Review');
    expect(api.listSkills).toHaveBeenCalledTimes(2);
  });

  it('filters agents by provider and keeps a failed delete confirmation open', async () => {
    const user = userEvent.setup();
    vi.mocked(api.deleteAgent).mockRejectedValueOnce(new Error('Delete unavailable'));
    render(<AgentsPage />);
    await screen.findByText('Builder');
    fireEvent.change(screen.getByRole('textbox', { name: 'Search agents' }), { target: { value: 'ollama' } });
    expect(screen.getByLabelText('Agent Builder')).toBeDefined();
    await user.click(screen.getByRole('button', { name: 'Open Builder action menu' }));
    await user.click(screen.getByRole('menuitem', { name: 'Delete' }));
    const dialog = screen.getByRole('dialog');
    expect(api.deleteAgent).not.toHaveBeenCalled();
    await user.click(within(dialog).getByRole('button', { name: 'Delete' }));
    await waitFor(() => expect(api.deleteAgent).toHaveBeenCalledWith('a1'));
    expect(await screen.findByRole('alert')).toHaveTextContent('Delete unavailable');
    expect(screen.getByRole('dialog')).toBeDefined();
    expect(screen.getByLabelText('Agent Builder')).toBeDefined();
  });

  it('keeps create fields after failure and submits the original create contract', async () => {
    vi.mocked(api.createAgent).mockRejectedValueOnce(new Error('Create unavailable'));
    render(<AgentsPage />);
    await screen.findByText('Builder');
    fireEvent.click(screen.getByRole('button', { name: 'New Agent' }));
    fireEvent.change(screen.getByPlaceholderText('My Agent'), { target: { value: 'Local agent' } });
    fireEvent.change(screen.getAllByRole('combobox')[0]!, { target: { value: 'ollama' } });
    fireEvent.click(screen.getByRole('button', { name: /Next/ }));
    fireEvent.click(screen.getByRole('button', { name: /Next/ }));
    fireEvent.click(screen.getByRole('button', { name: 'Create Agent' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Create unavailable');
    expect(api.createAgent).toHaveBeenCalledWith(expect.objectContaining({ name: 'Local agent', provider: 'ollama', tool_ids: [], skill_ids: [] }));
    expect(screen.getByRole('button', { name: 'Create Agent' })).toBeEnabled();
  });

  it('deletes only after confirmation and refreshes the agent list', async () => {
    const user = userEvent.setup();
    vi.mocked(api.deleteAgent).mockResolvedValue({} as any);
    render(<AgentsPage />);
    await screen.findByText('Builder');
    await user.click(screen.getByRole('button', { name: 'Open Builder action menu' }));
    await user.click(screen.getByRole('menuitem', { name: 'Delete' }));
    await user.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'Cancel' }));
    expect(api.deleteAgent).not.toHaveBeenCalled();
    await user.click(screen.getByRole('button', { name: 'Open Builder action menu' }));
    await user.click(screen.getByRole('menuitem', { name: 'Delete' }));
    vi.mocked(api.listAgents).mockResolvedValue([]);
    await user.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'Delete' }));
    await screen.findByText('No agents yet');
    expect(api.deleteAgent).toHaveBeenCalledWith('a1');
    expect(api.listAgents).toHaveBeenCalledTimes(2);
  });

  it('uses existing Chinese translations for resource actions', async () => {
    await i18n.changeLanguage('zh-CN');
    render(<SkillsPage />);
    await screen.findByText('Review');
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(i18n.t('navigation.skills'));
    expect(screen.getByRole('button', { name: `${i18n.t('agents.deactivate')}: Review` })).toBeDefined();
  });
});
