import { useState, useEffect } from 'react';
import { Plus, Trash2, Bot, Sparkles, ChevronRight, ChevronLeft, Check, RefreshCw, AlertCircle } from 'lucide-react';
import { api } from '../api';
import type { ModelSummary, SkillSummary } from '../types/api';

const PROVIDERS = [
  { id: 'openai', label: 'OpenAI', models: ['gpt-4o', 'gpt-4o-mini', 'o1', 'o1-mini'] },
  { id: 'anthropic', label: 'Anthropic', models: ['claude-sonnet-4-20250514', 'claude-opus-4-20250514', 'claude-3-5-haiku-latest'] },
  { id: 'google', label: 'Google', models: ['gemini-2.5-pro', 'gemini-2.5-flash', 'gemini-2.0-flash'] },
  { id: 'ollama', label: 'Ollama (Local)', models: ['llama3.3', 'qwen2.5', 'codellama', 'mistral'] },
];

export function AgentsPage() {
  const [agents, setAgents] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);
  const [step, setStep] = useState(1);
  const [form, setForm] = useState({
    name: '', provider: 'openai', model_id: 'gpt-4o',
    api_key: '', system_prompt: '', description: '', base_url: '',
  });
  const [tools, setTools] = useState<any[]>([]);
  const [selectedTools, setSelectedTools] = useState<string[]>([]);
  const [models, setModels] = useState<ModelSummary[]>([]);
  const [skills, setSkills] = useState<SkillSummary[]>([]);
  const [selectedSkills, setSelectedSkills] = useState<string[]>([]);

  useEffect(() => {
    loadAgents();
    api.listTools().then(setTools).catch(() => undefined);
    api.listModels().then((data) => {
      setModels(data);
      const first = data[0];
      if (first?.provider && (first.model_id || first.id)) {
        setForm(current => ({
          ...current,
          provider: first.provider || current.provider,
          model_id: first.model_id || first.id || current.model_id,
        }));
      }
    }).catch(() => undefined);
    api.listSkills().then(setSkills).catch(() => undefined);
  }, []);

  const loadAgents = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.listAgents();
      setAgents(data);
    } catch (e: any) {
      setError(e.message || '加载智能体失败');
    }
    setLoading(false);
  };

  const createAgent = async () => {
    if (creating) return;
    setCreating(true);
    setCreateError(null);
    try {
      await api.createAgent({
        ...form,
        tool_ids: selectedTools,
        skill_ids: selectedSkills,
      });
      setShowForm(false);
      setStep(1);
      setSelectedSkills([]);
      setSelectedTools([]);
      await loadAgents();
    } catch (e: unknown) {
      setCreateError(e instanceof Error ? e.message : '创建智能体失败');
    } finally {
      setCreating(false);
    }
  };

  const deleteAgent = async (id: string) => {
    await api.deleteAgent(id);
    loadAgents();
  };

  const toggleTool = (name: string) => {
    setSelectedTools(prev =>
      prev.includes(name) ? prev.filter(t => t !== name) : [...prev, name]
    );
  };

  const toggleSkill = (skillId: string) => {
    setSelectedSkills(prev =>
      prev.includes(skillId) ? prev.filter(s => s !== skillId) : [...prev, skillId]
    );
  };

  const selectedProvider = PROVIDERS.find(p => p.id === form.provider);

  const catalogModels = models.filter(model => model.provider === form.provider);
  const modelOptions = catalogModels.length > 0
    ? catalogModels
    : (selectedProvider?.models || []).map(model_id => ({ model_id, name: model_id }));
  const providerOptions = [...new Set([
    ...PROVIDERS.map(provider => provider.id),
    ...models.map(model => model.provider).filter((provider): provider is string => Boolean(provider)),
  ])];

  const skillCategories = [...new Set(skills.map(s => s.category))];

  return (
    <div className="h-full overflow-y-auto p-4 md:p-6 lg:p-8">
      <div className="max-w-4xl mx-auto">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between mb-8">
          <div>
            <h2 className="text-2xl font-bold text-[var(--color-text-primary)]">智能体</h2>
            <p className="text-[var(--color-text-secondary)] text-sm mt-1.5">创建和管理自定义模型与技能的 AI 智能体</p>
          </div>
                       <button
             onClick={() => { setShowForm(!showForm); setStep(1); setCreateError(null); }}
            className="flex items-center gap-2 rounded-lg bg-[var(--color-accent)] px-5 py-2.5 text-sm font-semibold text-white transition-colors duration-150 hover:bg-[var(--color-accent-hover)] active:translate-y-px"
          >
             <Plus size={16} /> 新建智能体
          </button>
        </div>

        {/* Multi-step creation form */}
         {showForm && (
           <div className="mb-6 rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-1)] p-6">
             {createError && (
               <div role="alert" className="mb-5 flex items-center gap-3 rounded-lg border border-[var(--color-error)]/30 bg-[var(--color-error-subtle)] p-3">
                 <AlertCircle size={16} className="shrink-0 text-[var(--color-error)]" />
                 <p className="flex-1 text-sm text-[var(--color-error)]">{createError}</p>
                 <button type="button" onClick={() => setCreateError(null)} className="text-xs text-[var(--color-error)] hover:underline">关闭</button>
               </div>
             )}
            {/* Step indicator */}
            <div className="flex items-center gap-3 mb-6">
              {[1, 2, 3].map(s => (
                <div key={s} className="flex items-center gap-2">
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-semibold transition-all duration-200 ${
                    step >= s ? 'bg-[var(--color-accent)] text-white' : 'bg-[var(--color-bg-surface-2)] text-[var(--color-text-muted)] border border-[var(--color-border-subtle)]'
                  }`}>
                    {step > s ? <Check size={14} /> : s}
                  </div>
                  <span className={`text-sm font-medium ${step >= s ? 'text-[var(--color-text-primary)]' : 'text-[var(--color-text-muted)]'}`}>
                     {s === 1 ? '模型' : s === 2 ? '技能' : '工具'}
                  </span>
                  {s < 3 && <div className={`w-12 h-0.5 rounded-full ${step > s ? 'bg-[var(--color-accent)]' : 'bg-[var(--color-border-subtle)]'}`} />}
                </div>
              ))}
            </div>

            {/* Step 1: Model & API */}
            {step === 1 && (
              <div className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                     <label htmlFor="agent-name" className="block text-sm font-medium text-[var(--color-text-secondary)] mb-2">智能体名称</label>
                     <input
                       id="agent-name"
                        placeholder="我的智能体"
                       value={form.name}
                       onChange={(e) => setForm({ ...form, name: e.target.value })}
                        className="w-full rounded-lg border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-2)] px-4 py-2.5 text-sm text-[var(--color-text-primary)] transition-colors duration-150 focus:border-[var(--color-border-accent)] focus:outline-none"
                     />
                   </div>
                   <div>
                     <label htmlFor="agent-provider" className="block text-sm font-medium text-[var(--color-text-secondary)] mb-2">提供商</label>
                     <select
                       id="agent-provider"
                      value={form.provider}
                      onChange={(e) => {
                        const prov = PROVIDERS.find(p => p.id === e.target.value);
                        setForm({ ...form, provider: e.target.value, model_id: prov?.models[0] || '' });
                      }}
                       className="w-full rounded-lg border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-2)] px-4 py-2.5 text-sm text-[var(--color-text-primary)]"
                    >
                      {providerOptions.map(provider => (
                        <option key={provider} value={provider}>
                          {PROVIDERS.find(item => item.id === provider)?.label || provider}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div>
                     <label htmlFor="agent-model" className="block text-sm font-medium text-[var(--color-text-secondary)] mb-2">模型</label>
                     <select
                       id="agent-model"
                      value={form.model_id}
                      onChange={(e) => setForm({ ...form, model_id: e.target.value })}
                       className="w-full rounded-lg border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-2)] px-4 py-2.5 text-sm text-[var(--color-text-primary)]"
                    >
                       {modelOptions.map(modelOption => {
                         const value = modelOption.model_id || ('id' in modelOption ? modelOption.id : '') || '';
                         return <option key={value} value={value}>{modelOption.name || (modelOption as ModelSummary & { label?: string }).label || value}</option>;
                       })}
                    </select>
                  </div>
                  <div>
                     <label htmlFor="agent-api-key" className="block text-sm font-medium text-[var(--color-text-secondary)] mb-2">API 密钥</label>
                     <input
                       id="agent-api-key"
                        placeholder="sk-..."
                       type="password"
                       value={form.api_key}
                       onChange={(e) => setForm({ ...form, api_key: e.target.value })}
                        className="w-full rounded-lg border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-2)] px-4 py-2.5 text-sm text-[var(--color-text-primary)] transition-colors duration-150 focus:border-[var(--color-border-accent)] focus:outline-none"
                     />
                   </div>
                    <div className="md:col-span-2">
                       <label htmlFor="agent-base-url" className="block text-sm font-medium text-[var(--color-text-secondary)] mb-2">Base URL（可选）</label>
                       <input
                         id="agent-base-url"
                        placeholder="自定义端点 URL（例如：Ollama 的 http://localhost:11434）"
                       value={form.base_url}
                       onChange={(e) => setForm({ ...form, base_url: e.target.value })}
                       className="w-full rounded-lg border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-2)] px-4 py-2.5 text-sm text-[var(--color-text-primary)] transition-colors duration-150 focus:border-[var(--color-border-accent)] focus:outline-none"
                     />
                   </div>
                    <div className="md:col-span-2">
                       <label htmlFor="agent-system-prompt" className="block text-sm font-medium text-[var(--color-text-secondary)] mb-2">系统提示词（可选）</label>
                       <textarea
                         id="agent-system-prompt"
                        placeholder="你是一个有用的助手..."
                       value={form.system_prompt}
                       onChange={(e) => setForm({ ...form, system_prompt: e.target.value })}
                       className="h-20 w-full resize-none rounded-lg border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-2)] px-4 py-2.5 text-sm text-[var(--color-text-primary)] transition-colors duration-150 focus:border-[var(--color-border-accent)] focus:outline-none"
                     />
                   </div>
                </div>
              </div>
            )}

            {/* Step 2: Skills */}
            {step === 2 && (
              <div>
                <p className="text-sm text-[var(--color-text-muted)] mb-5">
                   选择技能以增强此智能体 — 每个技能都会添加专业知识与工具。
                </p>
                {skillCategories.map(cat => (
                  <div key={cat} className="mb-6">
                    <h4 className="text-xs font-semibold text-[var(--color-text-muted)] uppercase tracking-wider mb-3">{cat}</h4>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                      {skills.filter(s => s.category === cat).map(skill => (
                        <button
                          key={skill.id}
                          onClick={() => toggleSkill(skill.id)}
                          className={`rounded-lg border p-4 text-left transition-colors duration-150 ${
                            selectedSkills.includes(skill.id)
                              ? 'border-[var(--color-accent)]/50 bg-[var(--color-accent)]/5 shadow-sm shadow-[var(--color-accent)]/10'
                              : 'border-[var(--color-border-subtle)] hover:border-[var(--color-accent)]/30 bg-[var(--color-bg-surface-1)]'
                          }`}
                        >
                          <div className="flex items-center gap-2.5 mb-1.5">
                             <span className="text-lg" aria-hidden="true">{skill.category === 'research' ? 'R' : 'S'}</span>
                            <span className="font-semibold text-sm text-[var(--color-text-primary)]">{skill.name}</span>
                            {selectedSkills.includes(skill.id) && (
                              <Check size={14} className="text-[var(--color-accent)] ml-auto" />
                            )}
                          </div>
                          <p className="text-xs text-[var(--color-text-muted)] line-clamp-2">{skill.description}</p>
                        </button>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* Step 3: Tools */}
            {step === 3 && (
              <div>
                <p className="text-sm text-[var(--color-text-secondary)] mb-4">
                   选择额外工具。你已选择的技能会自动启用其工具。
                </p>
                <div className="flex flex-wrap gap-2">
                  {tools.map(tool => (
                    <button
                      key={tool.name}
                      onClick={() => toggleTool(tool.name)}
                      className={`rounded-lg px-4 py-2 text-xs font-semibold transition-colors duration-150 ${
                        selectedTools.includes(tool.name)
                          ? 'bg-[var(--color-accent)] text-white'
                          : 'bg-[var(--color-bg-surface-2)] text-[var(--color-text-secondary)] border border-[var(--color-border-subtle)] hover:border-[var(--color-border-accent)]'
                      }`}
                    >
                      {tool.name}
                    </button>
                  ))}
                </div>
                {selectedSkills.length > 0 && (
                  <div className="mt-4 rounded-lg border border-[var(--color-border-accent)] bg-[var(--color-accent-subtle)] p-3">
                    <p className="text-xs text-[var(--color-accent)]">
                      {selectedSkills.length} skill(s) selected — their tools are automatically included.
                    </p>
                  </div>
                )}
              </div>
            )}

            {/* Navigation */}
            <div className="flex justify-between mt-6 pt-4 border-t border-[var(--color-border-subtle)]">
              {step > 1 ? (
                <button
                  onClick={() => setStep(step - 1)}
                  className="flex items-center gap-2 px-4 py-2 text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] text-sm transition-colors"
                >
                   <ChevronLeft size={16} /> 上一步
                </button>
              ) : <div />}
              {step < 3 ? (
                <button
                  onClick={() => setStep(step + 1)}
                  disabled={step === 1 && (!form.name || !form.api_key)}
                  className="flex items-center gap-2 rounded-lg bg-[var(--color-accent)] px-5 py-2.5 text-sm font-semibold text-white transition-colors duration-150 hover:bg-[var(--color-accent-hover)] disabled:opacity-40 active:translate-y-px"
                >
                   下一步 <ChevronRight size={16} />
                </button>
              ) : (
                 <button
                   onClick={createAgent}
                   disabled={creating}
                   className="rounded-lg bg-[var(--color-accent)] px-6 py-2.5 text-sm font-semibold text-white transition-colors duration-150 hover:bg-[var(--color-accent-hover)] active:translate-y-px"
                 >
                    {creating ? '创建中...' : '创建智能体'}
                </button>
              )}
            </div>
          </div>
        )}

        {/* Error state */}
        {error && (
          <div className="mb-6 flex items-center gap-3 rounded-lg border border-[var(--color-error)]/30 bg-[var(--color-error-subtle)] p-4">
            <AlertCircle size={18} className="text-[var(--color-error)] shrink-0" />
            <p className="text-sm text-[var(--color-error)] flex-1">{error}</p>
            <button
              onClick={loadAgents}
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-[var(--color-error)] hover:bg-[var(--color-error)]/10 rounded-xl transition-colors"
            >
              <RefreshCw size={14} /> Retry
            </button>
          </div>
        )}

        {/* Loading skeleton */}
        {loading && (
          <div className="space-y-3">
            {[1, 2, 3].map(i => (
              <div key={i} className="animate-pulse rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-1)] p-5">
                <div className="flex items-center gap-4">
                  <div className="h-10 w-10 rounded-lg bg-[var(--color-bg-surface-3)]" />
                  <div className="flex-1 space-y-2">
                    <div className="h-4 w-32 rounded bg-[var(--color-bg-surface-3)]" />
                    <div className="h-3 w-48 rounded bg-[var(--color-bg-surface-3)]" />
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Agent list */}
        {!loading && !error && (
          <div className="space-y-3">
            {agents.map(agent => (
              <div
                key={agent.id}
                className="flex items-center gap-4 rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-1)] p-5 transition-colors duration-150 hover:border-[var(--color-border-default)]"
              >
                <div className="flex h-10 w-10 items-center justify-center rounded-lg border border-[var(--color-border-accent)] bg-[var(--color-accent-subtle)]">
                  <Bot size={20} className="text-[var(--color-accent)]" />
                </div>
                <div className="flex-1">
                  <h3 className="font-semibold text-[var(--color-text-primary)]">{agent.name}</h3>
                  <p className="text-sm text-[var(--color-text-muted)]">
                    {agent.provider}:{agent.model_id}
                    {agent.tools?.length > 0 && ` | ${agent.tools.length} tools`}
                    {agent.skill_ids?.length > 0 && ` | ${agent.skill_ids.length} skills`}
                  </p>
                </div>
                <button
                  onClick={() => deleteAgent(agent.id)}
                  className="p-2 hover:bg-[var(--color-error)]/10 rounded-xl text-[var(--color-text-muted)] hover:text-[var(--color-error)] transition-all duration-200"
                >
                  <Trash2 size={16} />
                </button>
              </div>
            ))}
            {agents.length === 0 && !showForm && (
              <div className="text-center py-16">
                <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-2)]">
                  <Sparkles size={28} className="text-[var(--color-text-muted)]" />
                </div>
                <p className="text-[var(--color-text-muted)] text-sm">暂无智能体。创建你的第一个智能体开始使用。</p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
