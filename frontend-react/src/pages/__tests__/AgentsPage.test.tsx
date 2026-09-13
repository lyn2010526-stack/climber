import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import i18n from '../../i18n';
import { AgentsPage, AgentCard, buildAgentCreatePayload } from '../AgentsPage';
import { buildAgentVisualIdentity } from '../../components/agents/agentVisualIdentity';
import { resolveAgentStatus } from '../../components/agents/AgentStatusBadge';

vi.mock('../../api', () => ({
  api: {
    listAgents: vi.fn(),
    deleteAgent: vi.fn(),
    createAgent: vi.fn(),
    listTools: vi.fn().mockResolvedValue([]),
    listSkills: vi.fn().mockResolvedValue([]),
  },
}));

import { api } from '../../api';

const configuredAgent = {
  id: 'agent-1',
  name: 'Nova Prime',
  description: 'Frontier research assistant',
  provider: 'anthropic',
  model_id: 'claude-sonnet-4-20250514',
  is_active: true,
  tool_ids: ['t1', 't2', 't3'],
  skill_ids: ['s1', 's2'],
};

const disabledAgent = {
  id: 'agent-2',
  name: 'Idle Coder',
  description: '',
  provider: 'openai',
  model_id: 'gpt-4o',
  is_active: false,
  tool_ids: [],
  skill_ids: [],
};

beforeEach(async () => {
  localStorage.setItem('i18next_lng', 'en');
  await i18n.changeLanguage('en');
  vi.mocked(api.listAgents).mockReset();
  vi.mocked(api.listAgents).mockResolvedValue([configuredAgent, disabledAgent] as any);
});

describe('AgentsPage card rendering', () => {
  it('renders tool and skill counts from real tool_ids/skill_ids fields', async () => {
    render(<AgentsPage />);
    await waitFor(() => expect(screen.getByText('Nova Prime')).toBeDefined());
    const card = screen.getByLabelText('Agent Nova Prime');
    expect(card.getAttribute('data-agent-id')).toBe('agent-1');
    expect(card.textContent).toContain('3 tools');
    expect(card.textContent).toContain('2 skills');
  });

  it('shows empty skill/tool counts as 0 for the disabled agent', async () => {
    render(<AgentsPage />);
    await waitFor(() => expect(screen.getByText('Idle Coder')).toBeDefined());
    const cards = document.querySelectorAll('[data-agent-id="agent-2"]');
    expect(cards.length).toBe(1);
    const card = cards[0] as HTMLElement;
    expect(card.textContent).toContain('0 tools');
    expect(card.textContent).toContain('0 skills');
  });

  it('renders Configured and Disabled status badges with matching data attribute', async () => {
    render(<AgentsPage />);
    await waitFor(() => expect(screen.getByText('Nova Prime')).toBeDefined());
    const configured = document.querySelector('[data-agent-status="configured"]');
    const disabled = document.querySelector('[data-agent-status="disabled"]');
    expect(configured).not.toBeNull();
    expect(configured?.textContent).toContain('Configured');
    expect(disabled).not.toBeNull();
    expect(disabled?.textContent).toContain('Disabled');
  });
});

describe('AgentCard status resolution', () => {
  it('marks incomplete when model_id or provider missing', () => {
    expect(resolveAgentStatus({ is_active: true, model_id: 'x', provider: '' })).toBe('incomplete');
    expect(resolveAgentStatus({ is_active: true, model_id: '', provider: 'openai' })).toBe('incomplete');
  });
  it('disabled wins over configured', () => {
    expect(resolveAgentStatus({ is_active: false, model_id: 'x', provider: 'openai' })).toBe('disabled');
  });
  it('same id keeps hue stable across rename; initials are deterministic per name', () => {
    const a = buildAgentVisualIdentity({ id: 'agent-1', name: 'Nova Prime', provider: 'anthropic' });
    const b = buildAgentVisualIdentity({ id: 'agent-1', name: 'Completely Different', provider: 'openai' });
    const c = buildAgentVisualIdentity({ id: 'agent-1', name: 'Nova Prime', provider: 'openai' });
    expect(a.hue).toBe(b.hue);
    expect(a.initials).toBe('NP');
    expect(b.initials).toBe('CD');
    expect(c.initials).toBe(a.initials);
  });
});

describe('AgentCard menu', () => {
  it('renders menu trigger with translated aria-label', () => {
    render(<AgentCard agent={configuredAgent} onDelete={() => {}} />);
    const menuButton = screen.getByRole('button', { name: /Open Nova Prime action menu/ });
    expect(menuButton).toBeDefined();
  });
});

describe('Create payload contract', () => {
  it('uses tool_ids/skill_ids and never legacy tools/skills keys', () => {
    const payload = buildAgentCreatePayload(
      { name: 'X', provider: 'openai', model_id: 'gpt-4o' },
      ['read_file', 'write_file'],
      ['skill-a'],
    );
    expect(payload.tool_ids).toEqual(['read_file', 'write_file']);
    expect(payload.skill_ids).toEqual(['skill-a']);
    expect('tools' in payload).toBe(false);
    expect('skills' in payload).toBe(false);
  });
});
