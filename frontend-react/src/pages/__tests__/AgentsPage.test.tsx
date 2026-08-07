import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { api } from '../../api';

vi.mock('../../api', () => ({
  api: {
    listAgents: vi.fn().mockResolvedValue([]),
    createAgent: vi.fn().mockResolvedValue({}),
    deleteAgent: vi.fn().mockResolvedValue({}),
    listTools: vi.fn().mockResolvedValue([]),
    getMarketplace: vi.fn().mockResolvedValue({ skills: [] }),
  },
}));

import { AgentsPage } from '../AgentsPage';

const mockAgents = [
  { id: 'agent-1', name: 'Test Agent', provider: 'openai', model_id: 'gpt-4o', tools: ['web_search'], skill_ids: [] },
];

const mockTools = [
  { name: 'web_search', description: 'Search the web' },
  { name: 'code_runner', description: 'Run code' },
];

const mockSkills = [
  { id: 'skill-1', name: 'Web Research', category: 'research', description: 'Research the web', icon: '🔍', tools: ['web_search'] },
];

describe('AgentsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.listAgents).mockResolvedValue([]);
    vi.mocked(api.listTools).mockResolvedValue([]);
    vi.mocked(api.getMarketplace).mockResolvedValue({ skills: [] });
  });

  it('renders without crashing', () => {
    const { container } = render(
      <MemoryRouter>
        <AgentsPage />
      </MemoryRouter>
    );
    expect(container).toBeDefined();
  });

  it('renders loading state initially', () => {
    const { container } = render(
      <MemoryRouter>
        <AgentsPage />
      </MemoryRouter>
    );
    expect(container.querySelector('.animate-spin')).toBeDefined();
  });

  it('renders page content after loading', async () => {
    render(
      <MemoryRouter>
        <AgentsPage />
      </MemoryRouter>
    );
    await waitFor(() => {
      expect(screen.getByText('Agents')).toBeDefined();
    });
  });

  it('renders empty state', async () => {
    render(
      <MemoryRouter>
        <AgentsPage />
      </MemoryRouter>
    );
    await waitFor(() => {
      expect(screen.getByText('No agents yet')).toBeDefined();
    });
  });

  it('renders agents list', async () => {
    vi.mocked(api.listAgents).mockResolvedValue(mockAgents);
    render(
      <MemoryRouter>
        <AgentsPage />
      </MemoryRouter>
    );
    await waitFor(() => {
      expect(screen.getByText('Test Agent')).toBeDefined();
    });
  });

  it('toggles create form', async () => {
    render(
      <MemoryRouter>
        <AgentsPage />
      </MemoryRouter>
    );
    await waitFor(() => {
      expect(screen.getByText('Agents')).toBeDefined();
    });
    fireEvent.click(screen.getAllByText('New Agent')[0]);
    expect(screen.getByPlaceholderText('My Agent')).toBeDefined();
  });

  it('navigates form steps', async () => {
    vi.mocked(api.listTools).mockResolvedValue(mockTools);
    render(
      <MemoryRouter>
        <AgentsPage />
      </MemoryRouter>
    );
    await waitFor(() => {
      expect(screen.getByText('Agents')).toBeDefined();
    });
    fireEvent.click(screen.getAllByText('New Agent')[0]);
    // Fill name and api key to enable next button
    fireEvent.change(screen.getByPlaceholderText('My Agent'), { target: { value: 'New Agent' } });
    fireEvent.change(screen.getByPlaceholderText('sk-...'), { target: { value: 'sk-test' } });
    fireEvent.click(screen.getByText('Next'));
    await waitFor(() => {
      expect(screen.getByText('Select skills to enhance this agent')).toBeDefined();
    });
  });

  it('creates agent', async () => {
    render(
      <MemoryRouter>
        <AgentsPage />
      </MemoryRouter>
    );
    await waitFor(() => {
      expect(screen.getByText('Agents')).toBeDefined();
    });
    fireEvent.click(screen.getAllByText('New Agent')[0]);
    fireEvent.change(screen.getByPlaceholderText('My Agent'), { target: { value: 'New Agent' } });
    fireEvent.change(screen.getByPlaceholderText('sk-...'), { target: { value: 'sk-test' } });
    // Navigate to step 3
    fireEvent.click(screen.getByText('Next'));
    fireEvent.click(screen.getByText('Next'));
    // Create
    fireEvent.click(screen.getByRole('button', { name: 'Create Agent' }));
    await waitFor(() => {
      expect(api.createAgent).toHaveBeenCalled();
    });
  });

  it('deletes an agent', async () => {
    vi.mocked(api.listAgents).mockResolvedValue(mockAgents);
    render(
      <MemoryRouter>
        <AgentsPage />
      </MemoryRouter>
    );
    await waitFor(() => {
      expect(screen.getByText('Test Agent')).toBeDefined();
    });
    // Open the agent's dropdown menu
    fireEvent.click(screen.getByLabelText('打开 Test Agent 操作菜单'));
    // Click Delete in the menu
    fireEvent.click(screen.getByText('Delete'));
    await waitFor(() => {
      expect(api.deleteAgent).toHaveBeenCalledWith('agent-1');
    });
  });

  it('renders tools in step 3', async () => {
    vi.mocked(api.listTools).mockResolvedValue(mockTools);
    render(
      <MemoryRouter>
        <AgentsPage />
      </MemoryRouter>
    );
    await waitFor(() => {
      expect(screen.getByText('Agents')).toBeDefined();
    });
    fireEvent.click(screen.getAllByText('New Agent')[0]);
    fireEvent.change(screen.getByPlaceholderText('My Agent'), { target: { value: 'New Agent' } });
    fireEvent.change(screen.getByPlaceholderText('sk-...'), { target: { value: 'sk-test' } });
    fireEvent.click(screen.getByText('Next'));
    fireEvent.click(screen.getByText('Next'));
    await waitFor(() => {
      expect(screen.getByText('web_search')).toBeDefined();
      expect(screen.getByText('code_runner')).toBeDefined();
    });
  });

  it('renders skills in step 2', async () => {
    vi.mocked(api.getMarketplace).mockResolvedValue({ skills: mockSkills });
    render(
      <MemoryRouter>
        <AgentsPage />
      </MemoryRouter>
    );
    await waitFor(() => {
      expect(screen.getByText('Agents')).toBeDefined();
    });
    fireEvent.click(screen.getAllByText('New Agent')[0]);
    fireEvent.change(screen.getByPlaceholderText('My Agent'), { target: { value: 'New Agent' } });
    fireEvent.change(screen.getByPlaceholderText('sk-...'), { target: { value: 'sk-test' } });
    fireEvent.click(screen.getByText('Next'));
    await waitFor(() => {
      expect(screen.getByText('Web Research')).toBeDefined();
    });
  });

  it('shows error state', async () => {
    vi.mocked(api.listAgents).mockRejectedValue(new Error('Load failed'));
    render(
      <MemoryRouter>
        <AgentsPage />
      </MemoryRouter>
    );
    await waitFor(() => {
      expect(screen.getByText(/Load failed/)).toBeDefined();
    });
  });
});
