import { useState, useEffect, useCallback } from 'react';
import { Plus, Trash2, Bot, Sparkles, ChevronRight, ChevronLeft, Check, RefreshCw, AlertCircle, Search, MoreVertical, Copy, Settings, Wrench, Boxes } from 'lucide-react';
import { api } from '../api';
import { Card, CardContent } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { Badge } from '../components/ui/Badge';
import { EmptyState } from '../components/ui/EmptyState';
import { Dropdown } from '../components/ui/Dropdown';
import { PageHeader } from '../components/ui/PageHeader';

const PROVIDERS = [
  { id: 'openai', label: 'OpenAI', models: ['gpt-4o', 'gpt-4o-mini', 'o1', 'o1-mini'] },
  { id: 'anthropic', label: 'Anthropic', models: ['claude-sonnet-4-20250514', 'claude-opus-4-20250514', 'claude-3-5-haiku-latest'] },
  { id: 'google', label: 'Google', models: ['gemini-2.5-pro', 'gemini-2.5-flash', 'gemini-2.0-flash'] },
  { id: 'ollama', label: 'Ollama (Local)', models: ['llama3.3', 'qwen2.5', 'codellama', 'mistral'] },
];

interface Skill {
  id: string;
  name: string;
  description: string;
  category: string;
  icon: string;
  tools: string[];
}

interface AgentCardProps {
  agent: any;
  onDelete: (id: string) => void;
}

function AgentCard({ agent, onDelete }: AgentCardProps) {
  return (
    <Card variant="default" padding="none" className="group agent-list-row">
      <CardContent className="p-3 md:p-4">
        <div className="flex items-start gap-3 md:gap-4">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-[var(--color-accent-subtle)] ring-1 ring-[var(--color-border-accent)]">
            <Bot size={18} className="text-[var(--color-accent)]" />
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-0.5">
              <h3 className="font-semibold text-sm text-[var(--color-text-primary)] truncate">{agent.name}</h3>
              <Badge variant="primary" size="xs">{agent.provider}</Badge>
            </div>
            <p className="text-xs text-[var(--color-text-muted)] truncate">{agent.model_id}</p>
            <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-[var(--color-text-muted)]">
              <span className="inline-flex items-center gap-1.5"><Wrench size={12} />{agent.tools?.length ?? 0} tools</span>
              <span className="inline-flex items-center gap-1.5"><Boxes size={12} />{agent.skill_ids?.length ?? 0} skills</span>
              {agent.model_id && <span className="inline-flex items-center gap-1.5"><span className="h-1.5 w-1.5 rounded-full bg-[var(--color-success)]" />Model configured</span>}
            </div>
          </div>
          <Dropdown
            trigger={
              <button aria-label={`打开 ${agent.name} 操作菜单`} className="flex h-9 w-9 items-center justify-center rounded-lg text-[var(--color-text-muted)] opacity-100 transition-colors hover:bg-[var(--color-bg-surface-2)] hover:text-[var(--color-text-primary)] md:opacity-0 md:group-hover:opacity-100 md:group-focus-within:opacity-100">
                <MoreVertical size={16} />
              </button>
            }
          >
            <div className="w-36 p-1">
              <button className="flex w-full items-center gap-2 rounded-[var(--radius-md)] px-3 py-2 text-xs text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-surface-2)] transition-colors">
                <Copy size={13} /> Copy Config
              </button>
              <button className="flex w-full items-center gap-2 rounded-[var(--radius-md)] px-3 py-2 text-xs text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-surface-2)] transition-colors">
                <Settings size={13} /> Edit Settings
              </button>
              <div className="my-1 h-px bg-[var(--color-border-subtle)]" />
              <button
                className="flex w-full items-center gap-2 rounded-[var(--radius-md)] px-3 py-2 text-xs text-[var(--color-error)] hover:bg-[var(--color-error-subtle)] transition-colors"
                onClick={() => onDelete(agent.id)}
              >
                <Trash2 size={13} /> Delete
              </button>
            </div>
          </Dropdown>
        </div>
      </CardContent>
    </Card>
  );
}

interface CreateAgentFormProps {
  onClose: () => void;
  onSuccess: () => void;
}

function CreateAgentForm({ onClose, onSuccess }: CreateAgentFormProps) {
  const [step, setStep] = useState(1);
  const [form, setForm] = useState({
    name: '', provider: 'openai', model_id: 'gpt-4o',
    api_key: '', system_prompt: '', description: '', base_url: '',
  });
  const [tools, setTools] = useState<any[]>([]);
  const [selectedTools, setSelectedTools] = useState<string[]>([]);
  const [skills, setSkills] = useState<Skill[]>([]);
  const [selectedSkills, setSelectedSkills] = useState<string[]>([]);
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    api.listTools().then(setTools).catch(() => {});
    api.getMarketplace().then(data => setSkills(data.skills || [])).catch(() => {});
  }, []);

  const selectedProvider = PROVIDERS.find(p => p.id === form.provider);
  const skillCategories = [...new Set(skills.map(s => s.category))];

  const toggleTool = (name: string) => {
    setSelectedTools(prev => prev.includes(name) ? prev.filter(t => t !== name) : [...prev, name]);
  };

  const toggleSkill = (skillId: string) => {
    setSelectedSkills(prev => prev.includes(skillId) ? prev.filter(s => s !== skillId) : [...prev, skillId]);
  };

  const handleCreate = async () => {
    setCreating(true);
    try {
      await api.createAgent({ ...form, tools: selectedTools, skills: selectedSkills });
      onSuccess();
    } finally {
      setCreating(false);
    }
  };

  return (
    <Card variant="default" padding="none" className="overflow-hidden">
      <div className="p-4 md:p-6 border-b border-[var(--color-border-subtle)]">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-base font-semibold text-[var(--color-text-primary)]">Create Agent</h3>
            <p className="text-xs text-[var(--color-text-muted)] mt-0.5">Configure model, skills and tools</p>
          </div>
          <button
            onClick={onClose}
            aria-label="关闭创建表单"
            className="flex h-9 w-9 items-center justify-center rounded-lg text-[var(--color-text-muted)] transition-colors hover:bg-[var(--color-bg-surface-2)] hover:text-[var(--color-text-primary)]"
          >
            <span className="text-lg leading-none">&times;</span>
          </button>
        </div>

            <div className="grid grid-cols-3 gap-2" aria-label={`创建步骤 ${step}/3`}>
          {[1, 2, 3].map(s => (
            <div key={s} className="flex items-center gap-2">
              <div className={`flex h-8 w-8 items-center justify-center rounded-lg text-xs font-semibold transition-colors duration-200 ${
                step >= s
                  ? 'bg-[var(--color-accent)] text-white shadow-[0_2px_8px_rgba(94,106,210,0.25)]'
                  : 'bg-[var(--color-bg-surface-2)] text-[var(--color-text-muted)] border border-[var(--color-border-subtle)]'
              }`}>
                {step > s ? <Check size={12} /> : s}
              </div>
              <span className={`text-xs font-medium hidden sm:inline ${step >= s ? 'text-[var(--color-text-primary)]' : 'text-[var(--color-text-muted)]'}`}>
                {s === 1 ? 'Model' : s === 2 ? 'Skills' : 'Tools'}
              </span>
            </div>
          ))}
        </div>
      </div>

      <div className="p-4 md:p-6">
        {step === 1 && (
          <div className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 md:gap-4">
              <div>
                <label className="block text-xs font-medium text-[var(--color-text-secondary)] mb-1.5">Agent Name</label>
                <Input placeholder="My Agent" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
              </div>
              <div>
                <label className="block text-xs font-medium text-[var(--color-text-secondary)] mb-1.5">Provider</label>
                <select
                  value={form.provider}
                  onChange={(e) => {
                    const prov = PROVIDERS.find(p => p.id === e.target.value);
                    setForm({ ...form, provider: e.target.value, model_id: prov?.models[0] || '' });
                  }}
                  className="flex h-10 w-full items-center justify-between rounded-[var(--radius-md)] border border-[var(--color-border-default)] bg-[var(--color-bg-surface-2)] px-3 text-sm text-[var(--color-text-primary)] transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-[var(--color-accent)]/20 focus:border-[var(--color-accent)]"
                >
                  {PROVIDERS.map(p => <option key={p.id} value={p.id}>{p.label}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-[var(--color-text-secondary)] mb-1.5">Model</label>
                <select
                  value={form.model_id}
                  onChange={(e) => setForm({ ...form, model_id: e.target.value })}
                  className="flex h-10 w-full items-center justify-between rounded-[var(--radius-md)] border border-[var(--color-border-default)] bg-[var(--color-bg-surface-2)] px-3 text-sm text-[var(--color-text-primary)] transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-[var(--color-accent)]/20 focus:border-[var(--color-accent)]"
                >
                  {selectedProvider?.models.map(m => <option key={m} value={m}>{m}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-[var(--color-text-secondary)] mb-1.5">API Key</label>
                <Input placeholder="sk-..." type="password" value={form.api_key} onChange={(e) => setForm({ ...form, api_key: e.target.value })} />
              </div>
              <div className="md:col-span-2">
                <label className="block text-xs font-medium text-[var(--color-text-secondary)] mb-1.5">Base URL (optional)</label>
                <Input placeholder="Custom endpoint URL" value={form.base_url} onChange={(e) => setForm({ ...form, base_url: e.target.value })} />
              </div>
              <div className="md:col-span-2">
                <label className="block text-xs font-medium text-[var(--color-text-secondary)] mb-1.5">System Prompt (optional)</label>
                <textarea
                  placeholder="You are a helpful assistant..."
                  value={form.system_prompt}
                  onChange={(e) => setForm({ ...form, system_prompt: e.target.value })}
                  className="w-full px-3 py-2.5 bg-[var(--color-bg-surface-2)] border border-[var(--color-border-default)] rounded-[var(--radius-md)] text-sm text-[var(--color-text-primary)] placeholder:text-[var(--color-text-muted)] focus:outline-none focus:ring-2 focus:ring-[var(--color-accent)]/20 focus:border-[var(--color-accent)] transition-all duration-200 resize-none h-20"
                />
              </div>
            </div>
          </div>
        )}

        {step === 2 && (
          <div>
            <p className="text-sm text-[var(--color-text-muted)] mb-4">Select skills to enhance this agent</p>
            {skillCategories.map(cat => (
              <div key={cat} className="mb-5">
                <h4 className="text-xs font-semibold text-[var(--color-text-muted)] uppercase tracking-wider mb-2">{cat}</h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2 md:gap-3">
                  {skills.filter(s => s.category === cat).map(skill => (
                    <button
                      key={skill.id}
                      onClick={() => toggleSkill(skill.id)}
                      className={`p-3 md:p-4 rounded-[var(--radius-md)] border text-left transition-all duration-200 focus-ring ${
                        selectedSkills.includes(skill.id)
                          ? 'border-[var(--color-accent)]/50 bg-[var(--color-accent-muted)]'
                          : 'border-[var(--color-border-subtle)] hover:border-[var(--color-accent)]/30 bg-[var(--color-bg-surface-1)]'
                      }`}
                    >
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-base">{skill.icon}</span>
                        <span className="font-medium text-sm text-[var(--color-text-primary)]">{skill.name}</span>
                        {selectedSkills.includes(skill.id) && <Check size={14} className="text-[var(--color-accent)] ml-auto" />}
                      </div>
                      <p className="text-xs text-[var(--color-text-muted)] line-clamp-2">{skill.description}</p>
                    </button>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}

        {step === 3 && (
          <div>
            <p className="text-sm text-[var(--color-text-secondary)] mb-3">Select additional tools</p>
            <div className="flex flex-wrap gap-2">
              {tools.map(tool => (
                <button
                  key={tool.name}
                  onClick={() => toggleTool(tool.name)}
                  className={`px-3 py-1.5 rounded-[var(--radius-md)] text-xs font-medium transition-all duration-200 focus-ring ${
                    selectedTools.includes(tool.name)
                      ? 'bg-[var(--color-accent)] text-white shadow-[0_2px_8px_rgba(94,106,210,0.25)]'
                      : 'bg-[var(--color-bg-surface-2)] text-[var(--color-text-secondary)] border border-[var(--color-border-subtle)] hover:border-[var(--color-accent)]/30'
                  }`}
                >
                  {tool.name}
                </button>
              ))}
            </div>
            {selectedSkills.length > 0 && (
              <div className="mt-3 p-3 bg-[var(--color-accent-muted)] rounded-[var(--radius-md)] border border-[var(--color-accent)]/20">
                <p className="text-xs text-[var(--color-accent)]">{selectedSkills.length} skills selected, tools included automatically</p>
              </div>
            )}
          </div>
        )}
      </div>

      <div className="flex justify-between p-4 md:p-6 pt-3 md:pt-4 border-t border-[var(--color-border-subtle)]">
        {step > 1 ? (
          <Button variant="ghost" size="sm" onClick={() => setStep(step - 1)}>
            <ChevronLeft size={14} /> Previous
          </Button>
        ) : <div />}
        {step < 3 ? (
          <Button
            variant="primary"
            size="sm"
            onClick={() => setStep(step + 1)}
            disabled={step === 1 && (!form.name || !form.api_key)}
          >
            Next <ChevronRight size={14} />
          </Button>
        ) : (
          <Button variant="primary" size="sm" loading={creating} onClick={handleCreate}>
            Create Agent
          </Button>
        )}
      </div>
    </Card>
  );
}

export function AgentsPage() {
  const [agents, setAgents] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');

  const loadAgents = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.listAgents();
      setAgents(data);
    } catch (e: any) {
      const detail = e.message && e.message !== 'Request failed' ? ` ${e.message}` : '';
      setError(`Unable to reach the agent service. Check that the API is running, then retry.${detail}`);
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    loadAgents();
  }, [loadAgents]);

  const deleteAgent = async (id: string) => {
    await api.deleteAgent(id);
    loadAgents();
  };

  const filteredAgents = agents.filter(a =>
    a.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    a.provider?.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="page-scroll page-transition">
      <div className="page-container">
        <PageHeader
          title="Agents"
          description="Create and manage AI agents with custom models and skills"
          icon={<Bot size={20} className="text-[var(--color-accent)]" />}
          actions={
            <Button variant="primary" size="sm" icon={<Plus size={14} />} onClick={() => setShowForm(!showForm)}>
              New Agent
            </Button>
          }
        />

        {showForm && (
          <div className="mt-4 md:mt-6">
            <CreateAgentForm onClose={() => setShowForm(false)} onSuccess={() => { setShowForm(false); loadAgents(); }} />
          </div>
        )}

        {error && (
          <div role="alert" className="mt-4 flex items-center gap-3 rounded-xl border border-[var(--color-error)]/30 bg-[var(--color-error-subtle)] p-3 md:mt-6 md:p-4">
            <AlertCircle size={18} className="text-[var(--color-error)] shrink-0" />
            <p className="text-sm text-[var(--color-error)] flex-1">{error}</p>
            <Button variant="ghost" size="sm" onClick={loadAgents} icon={<RefreshCw size={14} />}>
              Retry
            </Button>
          </div>
        )}

        {!loading && !error && agents.length > 0 && (
          <div className="mt-4 max-w-md md:mt-6">
            <Input
              placeholder="Search agents..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              leftIcon={<Search size={14} />}
              aria-label="搜索智能体"
            />
          </div>
        )}

        {loading && (
            <div className="mt-4 grid gap-2 md:mt-6" aria-busy="true" aria-label="正在加载智能体">
            {[1, 2, 3].map(i => (
              <div key={i} className="h-20 md:h-24 rounded-[var(--radius-lg)] skeleton-shimmer" style={{ animationDelay: `${i * 100}ms` }} />
            ))}
          </div>
        )}

        {!loading && !error && (
          <div className="mt-4 grid gap-2 md:mt-6" aria-live="polite">
            {filteredAgents.map(agent => (
              <AgentCard key={agent.id} agent={agent} onDelete={deleteAgent} />
            ))}
            {filteredAgents.length === 0 && !showForm && (
              <EmptyState
                className="w-full"
                icon={searchQuery ? 'search' : <Sparkles size={22} className="text-[var(--color-text-muted)]" />}
                title={searchQuery ? 'No matching agents' : 'No agents yet'}
                description={searchQuery ? 'Try another name or provider.' : 'Create your first agent to get started.'}
                action={
                  <Button
                    variant={searchQuery ? 'outline' : 'primary'}
                    size="sm"
                    onClick={() => searchQuery ? setSearchQuery('') : setShowForm(true)}
                    icon={searchQuery ? <Search size={14} /> : <Plus size={14} />}
                  >
                    {searchQuery ? 'Clear search' : 'New Agent'}
                  </Button>
                }
              />
            )}
          </div>
        )}
      </div>
    </div>
  );
}
