import { useState, useEffect, useCallback } from 'react';
import { pageIcons as icons } from '../lib/icons';

const { add: Plus, delete: Trash2, agent: Bot, close: X, submenu: ChevronRight, check: Check, refresh: RefreshCw, error: AlertCircle, search: Search, more: MoreVertical, tools: Wrench, skills: Boxes, successCircle: CheckCircle2, warning: AlertTriangle, disabled: CircleSlash, helpCircle: CircleHelp, chart: SlidersHorizontal } = icons;
import { api } from '../api';
import { useTranslation } from '../i18n';
import { includesQuery } from '../lib/search';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { Badge } from '../components/ui/Badge';
import { EmptyState } from '../components/ui/EmptyState';
import { Dropdown } from '../components/ui/Dropdown';
import { ConfirmDialog } from '../components/ui/Modal';
import { PageHeader } from '../components/ui/PageHeader';
import { Card } from '../components/ui/Card';
import { SkeletonList } from '../components/ui/Skeleton';
import { resolveAgentStatus, type AgentStatus, type AgentStatusFields } from '../components/agents/AgentStatusBadge';
import { ParamControls, type ParamControlsChange, type ParamControlsValues } from '../components/agent/ParamControls';
import { toggleListItem } from '../lib/listSelection';

const PROVIDERS = [
  { id: 'openai', label: 'OpenAI', models: ['gpt-4o', 'gpt-4o-mini', 'o1', 'o1-mini'] },
  { id: 'anthropic', label: 'Anthropic', models: ['claude-sonnet-4-20250514', 'claude-opus-4-20250514', 'claude-3-5-haiku-latest'] },
  { id: 'google', label: 'Google', models: ['gemini-2.5-pro', 'gemini-2.5-flash', 'gemini-2.0-flash'] },
  { id: 'ollama', label: 'Ollama (Local)', models: ['llama3.3', 'qwen2.5', 'codellama', 'mistral'] },
];

const STATUS_FILTERS: { id: AgentStatus | 'all'; key: string }[] = [
  { id: 'all', key: 'common.all' },
  { id: 'configured', key: 'agents.status_model_configured' },
  { id: 'incomplete', key: 'agents.status_incomplete' },
  { id: 'disabled', key: 'agents.status_disabled' },
  { id: 'unreported', key: 'agents.status_unreported' },
];

const STATUS_VIEW: Record<AgentStatus, { icon: typeof CheckCircle2; key: string; tone: string }> = {
  configured: { icon: CheckCircle2, key: 'agents.status_model_configured', tone: 'text-[var(--color-text-secondary)]' },
  incomplete: { icon: AlertTriangle, key: 'agents.status_incomplete', tone: 'text-[var(--color-text-secondary)]' },
  disabled: { icon: CircleSlash, key: 'agents.status_disabled', tone: 'text-[var(--color-text-muted)]' },
  unreported: { icon: CircleHelp, key: 'agents.status_unreported', tone: 'text-[var(--color-text-disabled)]' },
};

/**
 * Sampling defaults for the runtime parameter card. They are deliberately a
 * module constant rather than an inline literal: the reset button hands this
 * exact object back to `useState`, and sharing one object keeps the "reset to
 * defaults" comparison honest.
 */
const DEFAULT_PARAMS: ParamControlsValues = {
  temperature: 0.7,
  top_p: 1,
  frequency_penalty: 0,
  presence_penalty: 0,
  max_tokens: 4096,
  response_format: 'text',
  stop: '',
};

interface Skill {
  id: string;
  name: string;
  description: string;
  category: string;
  icon?: string;
  tools?: string[];
}

function AgentStatusIndicator({ agent }: { agent: AgentStatusFields }) {
  const { t } = useTranslation();
  const status = resolveAgentStatus(agent);
  const view = STATUS_VIEW[status];
  const Icon = view.icon;
  return (
    <span
      role="status"
      data-agent-status={status}
      className={`inline-flex shrink-0 items-center gap-1.5 text-xs ${view.tone}`}
    >
      <Icon size={13} aria-hidden="true" className="shrink-0" />
      {t(view.key)}
    </span>
  );
}

interface AgentCardProps {
  agent: any;
  onDelete: (id: string) => Promise<boolean>;
}

export function AgentCard({ agent, onDelete }: AgentCardProps) {
  const { t } = useTranslation();
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const toolCount = agent.tool_ids?.length ?? 0;
  const skillCount = agent.skill_ids?.length ?? 0;

  const handleConfirmDelete = async () => {
    setDeleting(true);
    try {
      if (await onDelete(agent.id)) setConfirmOpen(false);
    } finally {
      setDeleting(false);
    }
  };

  return (
    <li
      aria-label={t('agents.card_aria_label', { name: agent.name })}
      data-agent-id={agent.id}
      className="flex items-center gap-3 bg-[var(--color-bg-surface-1)] px-3 py-2 md:px-4"
    >
      <Bot size={16} aria-hidden="true" className="shrink-0 text-[var(--color-text-muted)]" />
      <div className="min-w-0 flex-1">
        <div className="flex min-w-0 items-center gap-2">
          <span className="truncate text-sm font-medium text-[var(--color-text-primary)]">{agent.name}</span>
          <Badge variant="secondary" size="xs">{agent.provider}</Badge>
          <span className="hidden truncate text-xs text-[var(--color-text-muted)] sm:inline">{agent.model_id}</span>
        </div>
        {agent.description && (
          <p className="truncate text-xs text-[var(--color-text-muted)]">{agent.description}</p>
        )}
      </div>
      <div className="hidden shrink-0 items-center gap-3 text-xs text-[var(--color-text-muted)] md:flex">
        <span className="inline-flex items-center gap-1"><Wrench size={12} aria-hidden="true" />{toolCount} {t('agents.step_tools').toLocaleLowerCase()}</span>
        <span className="inline-flex items-center gap-1"><Boxes size={12} aria-hidden="true" />{skillCount} {t('agents.step_skills').toLocaleLowerCase()}</span>
        <span className="inline-flex items-center gap-1" title={`T=${agent.temperature ?? 0.7} · max_tokens=${agent.max_tokens ?? '∞'}`}>
          <SlidersHorizontal size={12} aria-hidden="true" />T{agent.temperature ?? 0.7}{agent.max_tokens ? ` · ${agent.max_tokens}` : ''}
        </span>
      </div>
      <AgentStatusIndicator agent={agent} />
      <Dropdown
        align="right"
        trigger={
           <button type="button" aria-label={t('agents.menu_aria_label', { name: agent.name })} className="flex h-11 w-11 shrink-0 items-center justify-center rounded-[var(--radius-lg)] text-[var(--color-text-muted)] transition-colors hover:bg-[var(--color-bg-surface-2)] hover:text-[var(--color-text-primary)] motion-reduce:transition-none">
            <MoreVertical size={16} aria-hidden="true" />
          </button>
        }
      >
        <div className="w-36 p-1">
          <button type="button"
            role="menuitem"
            className="flex w-full items-center gap-2 rounded-[var(--radius-md)] px-3 py-2 text-xs text-[var(--color-error)] transition-colors hover:bg-[var(--color-error-subtle)]"
            onClick={() => setConfirmOpen(true)}
          >
            <Trash2 size={13} aria-hidden="true" /> {t('common.delete')}
          </button>
        </div>
      </Dropdown>
      <ConfirmDialog
        open={confirmOpen}
        onClose={() => setConfirmOpen(false)}
        onConfirm={handleConfirmDelete}
        loading={deleting}
        variant="danger"
        title={t('agents.delete_confirm_title', { name: agent.name })}
        confirmText={t('common.delete')}
        cancelText={t('common.cancel')}
      />
    </li>
  );
}

interface CreateAgentFormProps {
  onClose: () => void;
  onSuccess: () => void;
  params: Pick<ParamControlsValues, 'temperature' | 'max_tokens'>;
}

export function buildAgentCreatePayload(
  form: Record<string, any>,
  selectedTools: string[],
  selectedSkills: string[],
  params?: Pick<ParamControlsValues, 'temperature' | 'max_tokens'>,
) {
  return {
    ...form,
    tool_ids: selectedTools,
    skill_ids: selectedSkills,
    temperature: params?.temperature ?? 0.7,
    max_tokens: params?.max_tokens ?? null,
  };
}

const selectClass = 'flex h-[var(--control-height-md)] w-full items-center justify-between rounded-[var(--radius-md)] border border-[var(--color-border-default)] bg-[var(--color-bg-surface-2)] px-3 text-sm text-[var(--color-text-primary)] transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-[var(--color-accent)]/20 focus:border-[var(--color-accent)]';

function CreateAgentForm({ onClose, onSuccess, params }: CreateAgentFormProps) {
  const { t } = useTranslation();
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
  const [createError, setCreateError] = useState<string | null>(null);
  // A failing catalog read and an empty catalog are different facts. Reporting
  // the failure (with a retry) instead of "no data" stops the tools/skills
  // picker from silently looking empty while the backend is down (R12-H58).
  const [catalogLoading, setCatalogLoading] = useState(true);
  const [catalogError, setCatalogError] = useState(false);

  const loadCatalog = useCallback(async () => {
    setCatalogLoading(true);
    setCatalogError(false);
    try {
      const [toolData, skillData] = await Promise.all([api.listTools(), api.listSkills()]);
      setTools(toolData);
      const skillResponse: any = skillData;
      setSkills(Array.isArray(skillResponse) ? skillResponse : (skillResponse?.skills ?? []));
    } catch {
      setCatalogError(true);
    } finally {
      setCatalogLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadCatalog();
  }, [loadCatalog]);

  const selectedProvider = PROVIDERS.find(p => p.id === form.provider);
  const skillCategories = [...new Set(skills.map(s => s.category))];

  const toggleTool = (name: string) => {
    setSelectedTools(prev => toggleListItem(prev, name));
  };

  const toggleSkill = (skillId: string) => {
    setSelectedSkills(prev => toggleListItem(prev, skillId));
  };

  const handleCreate = async () => {
    setCreating(true);
    setCreateError(null);
    try {
      await api.createAgent(buildAgentCreatePayload(form, selectedTools, selectedSkills, params));
      onSuccess();
    } catch (e) {
      setCreateError(e instanceof Error ? e.message : t('common.error'));
    } finally {
      setCreating(false);
    }
  };

  return (
    <section className="overflow-hidden rounded-[var(--radius-md)] border border-[var(--color-border-default)] bg-[var(--color-bg-surface-1)]">
      <div className="flex items-center justify-between border-b border-[var(--color-border-subtle)] px-4 py-3">
        <div>
          <h2 className="text-sm font-semibold text-[var(--color-text-primary)]">{t('agents.form_title')}</h2>
          <p className="mt-0.5 text-xs text-[var(--color-text-muted)]">{t('agents.form_subtitle')}</p>
        </div>
        <button type="button"
          onClick={onClose}
          aria-label={t('agents.close_form_aria_label')}
          className="flex h-8 w-8 items-center justify-center rounded-[var(--radius-lg)] text-[var(--color-text-muted)] transition-colors hover:bg-[var(--color-bg-surface-2)] hover:text-[var(--color-text-primary)] motion-reduce:transition-none"
        >
          <X size={16} aria-hidden="true" />
        </button>
      </div>

      <div className="grid grid-cols-3 gap-2 border-b border-[var(--color-border-subtle)] px-4 py-3" aria-label={t('agents.create_steps_aria_label', { step })}>
        {[1, 2, 3].map(s => (
          <div key={s} className="flex items-center gap-2">
            <span className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-[var(--radius-pill)] border text-xs font-semibold ${
              step >= s
                ? 'border-[var(--color-border-strong)] bg-[var(--color-bg-surface-3)] text-[var(--color-text-primary)]'
                : 'border-[var(--color-border-subtle)] text-[var(--color-text-muted)]'
            }`}>
              {step > s ? <Check size={12} aria-hidden="true" /> : s}
            </span>
            <span className={`hidden truncate text-xs font-medium sm:inline ${step >= s ? 'text-[var(--color-text-primary)]' : 'text-[var(--color-text-muted)]'}`}>
              {s === 1 ? t('agents.step_model') : s === 2 ? t('agents.step_skills') : t('agents.step_tools')}
            </span>
          </div>
        ))}
      </div>

      <div className="p-4">
        {createError && <p role="alert" className="mb-3 text-sm text-[var(--color-error)]">{createError}</p>}
        {step === 1 && (
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2 md:gap-4">
            <div>
              <label className="mb-1.5 block text-[length:var(--text-sm)] font-medium text-[var(--color-text-secondary)]">{t('agents.field_name')}</label>
              <Input placeholder={t('agents.field_name_placeholder')} value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
            </div>
            <div>
              <label className="mb-1.5 block text-[length:var(--text-sm)] font-medium text-[var(--color-text-secondary)]">{t('agents.field_provider')}</label>
              <select
                value={form.provider}
                onChange={(e) => {
                  const prov = PROVIDERS.find(p => p.id === e.target.value);
                  setForm({ ...form, provider: e.target.value, model_id: prov?.models[0] || '' });
                }}
                className={selectClass}
              >
                {PROVIDERS.map(p => <option key={p.id} value={p.id}>{p.label}</option>)}
              </select>
            </div>
            <div>
              <label className="mb-1.5 block text-[length:var(--text-sm)] font-medium text-[var(--color-text-secondary)]">{t('agents.field_model')}</label>
              <select
                value={form.model_id}
                onChange={(e) => setForm({ ...form, model_id: e.target.value })}
                className={selectClass}
              >
                {selectedProvider?.models.map(m => <option key={m} value={m}>{m}</option>)}
              </select>
            </div>
            <div>
              <label className="mb-1.5 block text-[length:var(--text-sm)] font-medium text-[var(--color-text-secondary)]">{t('agents.field_api_key')}</label>
              <Input placeholder="sk-..." type="password" value={form.api_key} onChange={(e) => setForm({ ...form, api_key: e.target.value })} />
            </div>
            <div className="md:col-span-2">
              <label className="mb-1.5 block text-[length:var(--text-sm)] font-medium text-[var(--color-text-secondary)]">{t('agents.field_base_url')}</label>
              <Input placeholder={t('agents.field_base_url_placeholder')} value={form.base_url} onChange={(e) => setForm({ ...form, base_url: e.target.value })} />
            </div>
            <div className="md:col-span-2">
              <label className="mb-1.5 block text-[length:var(--text-sm)] font-medium text-[var(--color-text-secondary)]">{t('agents.field_system_prompt')}</label>
              <textarea
                placeholder={t('agents.field_system_prompt_placeholder')}
                value={form.system_prompt}
                onChange={(e) => setForm({ ...form, system_prompt: e.target.value })}
                className="h-20 w-full resize-none rounded-[var(--radius-md)] border border-[var(--color-border-default)] bg-[var(--color-bg-surface-2)] px-3 py-2.5 text-sm text-[var(--color-text-primary)] transition-all duration-200 placeholder:text-[var(--color-text-muted)] focus:border-[var(--color-accent)] focus:outline-none focus:ring-2 focus:ring-[var(--color-accent)]/20"
              />
            </div>
          </div>
        )}

        {step === 2 && (
          <div>
            <p className="mb-3 text-sm text-[var(--color-text-muted)]">{t('agents.select_skills')}</p>
            {catalogLoading ? <p className="text-xs text-[var(--color-text-muted)]">{t('common.loading')}</p>
              : catalogError ? <p role="alert" className="text-sm text-[var(--color-error)]">{t('agents.catalog_load_failed')}<button type="button" className="ml-2 underline" onClick={loadCatalog}>{t('common.retry')}</button></p>
              : skillCategories.length === 0 && <p className="text-xs text-[var(--color-text-muted)]">{t('common.no_data')}</p>}
            {skillCategories.map(cat => (
              <div key={cat} className="mb-4 last:mb-0">
                <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-[var(--color-text-muted)]">{cat}</h3>
                <div className="grid grid-cols-1 gap-2 md:grid-cols-2 md:gap-3">
                  {skills.filter(s => s.category === cat).map(skill => (
                    <button type="button"
                      key={skill.id}
                      aria-pressed={selectedSkills.includes(skill.id)}
                      onClick={() => toggleSkill(skill.id)}
                      className={`rounded-[var(--radius-md)] border p-2.5 text-left transition-colors ${
                        selectedSkills.includes(skill.id)
                          ? 'border-[var(--color-border-strong)] bg-[var(--color-bg-surface-3)]'
                          : 'border-[var(--color-border-subtle)] hover:border-[var(--color-border-strong)]'
                      }`}
                    >
                      <span className="flex items-center gap-2">
                        <Boxes size={14} aria-hidden="true" className="shrink-0 text-[var(--color-text-muted)]" />
                        <span className="truncate text-sm font-medium text-[var(--color-text-primary)]">{skill.name}</span>
                        {selectedSkills.includes(skill.id) && <Check size={13} aria-hidden="true" className="ml-auto shrink-0 text-[var(--color-text-primary)]" />}
                      </span>
                      <span className="mt-0.5 line-clamp-2 block text-xs text-[var(--color-text-muted)]">{skill.description}</span>
                    </button>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}

        {step === 3 && (
          <div>
            <p className="mb-3 text-sm text-[var(--color-text-secondary)]">{t('agents.select_tools')}</p>
            {catalogLoading ? <p className="text-xs text-[var(--color-text-muted)]">{t('common.loading')}</p>
              : catalogError ? <p role="alert" className="text-sm text-[var(--color-error)]">{t('agents.catalog_load_failed')}<button type="button" className="ml-2 underline" onClick={loadCatalog}>{t('common.retry')}</button></p>
              : tools.length === 0 && <p className="text-xs text-[var(--color-text-muted)]">{t('common.no_data')}</p>}
            <div className="flex flex-wrap gap-2">
              {tools.map(tool => (
                <button type="button"
                  key={tool.name}
                  aria-pressed={selectedTools.includes(tool.name)}
                  onClick={() => toggleTool(tool.name)}
                  className={`rounded-[var(--radius-md)] border px-3 py-1.5 text-xs font-medium transition-colors ${
                    selectedTools.includes(tool.name)
                      ? 'border-[var(--color-border-strong)] bg-[var(--color-bg-surface-3)] text-[var(--color-text-primary)]'
                      : 'border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-2)] text-[var(--color-text-secondary)] hover:border-[var(--color-border-strong)]'
                  }`}
                >
                  {tool.name}
                </button>
              ))}
            </div>
            {selectedSkills.length > 0 && (
              <p className="mt-3 rounded-[var(--radius-md)] border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-2)] px-3 py-2 text-xs text-[var(--color-text-secondary)]">
                {t('agents.step_skills')}: {selectedSkills.length} · {t('common.selected')}
              </p>
            )}
          </div>
        )}
      </div>

      <div className="flex items-center justify-between border-t border-[var(--color-border-subtle)] px-4 py-3">
        {step > 1 ? (
          <Button variant="ghost" size="sm" onClick={() => setStep(step - 1)}>
            {t('agents.previous')}
          </Button>
        ) : <div />}
        {step < 3 ? (
          <Button
            variant="primary"
            size="sm"
            onClick={() => setStep(step + 1)}
            disabled={step === 1 && (!form.name || (form.provider !== 'ollama' && !form.api_key))}
            icon={<ChevronRight size={14} />}
          >
            {t('agents.next')}
          </Button>
        ) : (
          <Button variant="primary" size="sm" loading={creating} onClick={handleCreate}>
            {t('agents.create_agent')}
          </Button>
        )}
      </div>
    </section>
  );
}

export function AgentsPage() {
  const { t } = useTranslation();
  const [agents, setAgents] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<AgentStatus | 'all'>('all');
  // Sampling parameters live in page state for this session. `PATCH
  // /settings/` validates its payload down to `autonomous_agent_mode`,
  // `token_throttle_mcp_enabled` and `notifications`, so there is no field to
  // persist any of these into yet; writing them through would report a save
  // the backend never performed.
  const [params, setParams] = useState<ParamControlsValues>(DEFAULT_PARAMS);
  const [paramsDirty, setParamsDirty] = useState(false);

  const handleParamChange = useCallback<ParamControlsChange>((key, value) => {
    setParamsDirty(true);
    setParams((previous) => ({ ...previous, [key]: value }));
  }, []);

  const resetParams = useCallback(() => {
    setParams(DEFAULT_PARAMS);
    setParamsDirty(false);
  }, []);

  const loadAgents = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.listAgents();
      setAgents(data);
    } catch (e: any) {
      const detail = e.message && e.message !== 'Request failed' ? ` ${e.message}` : '';
      setError(`${t('common.network_error')}.${detail}`);
    }
    setLoading(false);
  }, [t]);

  useEffect(() => {
    loadAgents();
  }, [loadAgents]);

  const deleteAgent = async (id: string): Promise<boolean> => {
    setError(null);
    try {
      await api.deleteAgent(id);
      await loadAgents();
      return true;
    } catch (e: any) {
      const detail = e?.message && e.message !== 'Request failed' ? ` ${e.message}` : '';
      setError(t('agents.delete_failed') + detail);
      return false;
    }
  };

  const statusCounts = (status: AgentStatus | 'all') =>
    status === 'all'
      ? agents.length
      : agents.filter(a => resolveAgentStatus(a) === status).length;

  const filteredAgents = agents.filter(agent =>
    includesQuery([agent.name, agent.provider, agent.model_id, agent.description], searchQuery) &&
    (statusFilter === 'all' || resolveAgentStatus(agent) === statusFilter)
  );

  const showList = !loading && (!error || agents.length > 0);

  return (
    <div className="page-scroll page-transition">
      <div className="page-container">
        <PageHeader
          title={t('agents.title')}
          icon={<Bot size={20} aria-hidden="true" />}
          className="border-b border-[var(--color-border-subtle)] pb-[var(--space-4)] [&_h1]:text-[length:var(--text-base)] [&_h1]:md:text-[length:var(--text-base)] [&_p]:text-[var(--color-text-muted)]"
          actions={
            <>
              <Button variant="outline" size="sm" icon={<RefreshCw size={14} />} disabled={loading} onClick={loadAgents}>
                {t('common.refresh')}
              </Button>
              <Button variant="primary" size="sm" icon={<Plus size={14} />} onClick={() => setShowForm(true)} disabled={showForm}>
                {t('agents.new_agent')}
              </Button>
            </>
          }
        />

        <div className="space-y-4">
        {showForm && (
          <div>
            <CreateAgentForm onClose={() => setShowForm(false)} onSuccess={() => { setShowForm(false); loadAgents(); }} params={params} />
          </div>
        )}

        {error && (
          <div role="alert" className="flex items-center gap-3 rounded-[var(--radius-md)] border border-[var(--color-error)]/30 bg-[var(--color-error-subtle)] p-3">
            <AlertCircle size={16} aria-hidden="true" className="shrink-0 text-[var(--color-error)]" />
            <p className="flex-1 text-sm text-[var(--color-error)]">{error}</p>
            <Button variant="ghost" size="sm" onClick={loadAgents} icon={<RefreshCw size={14} />}>
              {t('agents.retry')}
            </Button>
          </div>
        )}

        <Card variant="default" padding="none" data-testid="agents-runtime-params">
          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[var(--color-border-subtle)] px-4 py-3">
            <div className="min-w-0">
              <h2 className="text-sm font-semibold text-[var(--color-text-primary)]">{t('agents.config')}</h2>
              <p className="mt-0.5 text-xs text-[var(--color-text-muted)]">
                {t('agents.params_saved_note', {
                  defaultValue: 'Temperature and Max tokens take effect and are saved with the agent on creation; the other parameters are not supported yet.',
                })}
              </p>
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={resetParams}
              disabled={!paramsDirty}
              data-testid="agents-runtime-params-reset"
            >
              {t('common.reset')}
            </Button>
          </div>
          <div className="p-4">
            <ParamControls value={params} onChange={handleParamChange} supportedKeys={['temperature', 'max_tokens']} data-testid="agents-params" />
          </div>
        </Card>

        {!loading && agents.length > 0 && (
          <div className="flex flex-wrap items-center gap-3">
            <div className="w-full max-w-xs">
              <Input
                size="sm"
                placeholder={t('agents.search_placeholder')}
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                leftIcon={<Search size={14} aria-hidden="true" />}
                aria-label={t('agents.search_aria_label')}
              />
            </div>
            <div className="flex flex-wrap items-center gap-1" role="group" aria-label={t('common.filter')}>
              {STATUS_FILTERS.map(option => (
                <button
                  key={option.id}
                  type="button"
                  onClick={() => setStatusFilter(option.id)}
                  aria-pressed={statusFilter === option.id}
                  className={`rounded-[var(--radius-md)] border px-2.5 py-1 text-xs font-medium transition-colors ${
                    statusFilter === option.id
                      ? 'border-[var(--color-border-strong)] bg-[var(--color-bg-surface-3)] text-[var(--color-text-primary)]'
                      : 'border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-2)] text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]'
                  }`}
                >
                  {t(option.key)} <span className="tabular-nums text-[var(--color-text-muted)]">{statusCounts(option.id)}</span>
                </button>
              ))}
            </div>
            <span className="shrink-0 text-xs tabular-nums text-[var(--color-text-muted)]" aria-live="polite">
              {filteredAgents.length} / {agents.length}
            </span>
          </div>
        )}

        {loading && (
          <div aria-busy="true" aria-label={t('agents.loading_aria_label')}>
            <SkeletonList count={3} />
          </div>
        )}

        {showList && filteredAgents.length > 0 && (
          <Card padding="none" className="overflow-hidden">
            <ul
              className="divide-y divide-[var(--color-border-subtle)]"
              aria-live="polite"
              aria-label={t('agents.resources')}
            >
              {filteredAgents.map(agent => (
                <AgentCard key={agent.id} agent={agent} onDelete={deleteAgent} />
              ))}
            </ul>
          </Card>
        )}

        {showList && filteredAgents.length === 0 && (
          <Card padding="none" className="overflow-hidden">
            <EmptyState
              className="w-full"
              icon={<Search size={20} aria-hidden="true" />}
              title={searchQuery || statusFilter !== 'all' ? t('agents.no_matching') : t('agents.no_agents')}
              description={searchQuery || statusFilter !== 'all' ? t('agents.try_another') : t('agents.create_first')}
              action={
                searchQuery || statusFilter !== 'all' ? (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => { setSearchQuery(''); setStatusFilter('all'); }}
                    icon={<Search size={14} aria-hidden="true" />}
                  >
                    {t('agents.clear_search')}
                  </Button>
                ) : (
                  <Button variant="primary" size="sm" onClick={() => setShowForm(true)} icon={<Plus size={14} aria-hidden="true" />}>
                    {t('agents.new_agent')}
                  </Button>
                )
              }
            />
          </Card>
        )}
        </div>
      </div>
    </div>
  );
}
