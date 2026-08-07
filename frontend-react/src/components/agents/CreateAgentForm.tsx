import React, { useState, useCallback } from 'react';
import { ChevronRight, ChevronLeft, Check, Bot, Sparkles, Wrench, AlertCircle } from 'lucide-react';
import { cn } from '../../lib/utils';

interface FormData {
  name: string;
  provider: string;
  model_id: string;
  api_key: string;
  system_prompt: string;
  description: string;
  base_url: string;
}

interface CreateAgentFormProps {
  onSubmit: (data: FormData, tools: string[], skills: string[]) => void;
  onCancel: () => void;
  tools: Array<{ name: string; description?: string }>;
  skills: Array<{ id: string; name: string; description: string; category: string; icon?: string }>;
}

const PROVIDERS = [
  { id: 'openai', label: 'OpenAI', models: ['gpt-4o', 'gpt-4o-mini', 'o1', 'o1-mini'] },
  { id: 'anthropic', label: 'Anthropic', models: ['claude-sonnet-4-20250514', 'claude-opus-4-20250514', 'claude-3-5-haiku-latest'] },
  { id: 'google', label: 'Google', models: ['gemini-2.5-pro', 'gemini-2.5-flash', 'gemini-2.0-flash'] },
  { id: 'ollama', label: 'Ollama (本地)', models: ['llama3.3', 'qwen2.5', 'codellama', 'mistral'] },
];

const steps = [
  { id: 1, label: '模型配置', icon: Bot },
  { id: 2, label: '技能选择', icon: Sparkles },
  { id: 3, label: '工具选择', icon: Wrench },
];

export const CreateAgentForm: React.FC<CreateAgentFormProps> = ({
  onSubmit,
  onCancel,
  tools,
  skills,
}) => {
  const [step, setStep] = useState(1);
  const [form, setForm] = useState<FormData>({
    name: '',
    provider: 'openai',
    model_id: 'gpt-4o',
    api_key: '',
    system_prompt: '',
    description: '',
    base_url: '',
  });
  const [selectedTools, setSelectedTools] = useState<string[]>([]);
  const [selectedSkills, setSelectedSkills] = useState<string[]>([]);
  const [errors, setErrors] = useState<Partial<Record<keyof FormData, string>>>({});

  const selectedProvider = PROVIDERS.find((p) => p.id === form.provider);
  const skillCategories = [...new Set(skills.map((s) => s.category))];

  const validateStep = useCallback((currentStep: number): boolean => {
    const newErrors: Partial<Record<keyof FormData, string>> = {};
    if (currentStep === 1) {
      if (!form['name'].trim()) newErrors['name'] = '请输入智能体名称';
      if (!form['api_key'].trim()) newErrors['api_key'] = '请输入 API 密钥';
    }
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  }, [form]);

  const handleNext = useCallback(() => {
    if (validateStep(step)) {
      setStep((s) => Math.min(s + 1, 3));
    }
  }, [step, validateStep]);

  const handleSubmit = useCallback(() => {
    if (validateStep(step)) {
      onSubmit(form, selectedTools, selectedSkills);
    }
  }, [step, validateStep, onSubmit, form, selectedTools, selectedSkills]);

  const toggleTool = (name: string) => {
    setSelectedTools((prev) =>
      prev.includes(name) ? prev.filter((t) => t !== name) : [...prev, name]
    );
  };

  const toggleSkill = (skillId: string) => {
    setSelectedSkills((prev) =>
      prev.includes(skillId) ? prev.filter((s) => s !== skillId) : [...prev, skillId]
    );
  };

  const updateForm = (field: keyof FormData, value: string) => {
    setForm((prev) => ({ ...prev, [field]: value }));
    if (errors[field]) {
      setErrors((prev) => {
        const next = { ...prev };
        delete next[field];
        return next;
      });
    }
  };

  return (
    <div className="rounded-2xl border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-1)] shadow-xl shadow-black/10">
      <div className="border-b border-[var(--color-border-subtle)] px-6 py-4">
        <h3 className="text-base font-semibold text-[var(--color-text-primary)]">创建智能体</h3>
        <p className="mt-0.5 text-xs text-[var(--color-text-muted)]">配置模型、技能和工具以创建新的 AI 智能体</p>
      </div>

      {/* Step Indicator */}
      <div className="flex items-center gap-2 border-b border-[var(--color-border-subtle)] px-6 py-4">
        {steps.map((s, index) => {
          const Icon = s.icon;
          const isActive = step === s.id;
          const isCompleted = step > s.id;
          return (
            <React.Fragment key={s.id}>
              <div className="flex items-center gap-2">
                <div
                  className={cn(
                    'flex h-8 w-8 items-center justify-center rounded-lg transition-all duration-200',
                    isCompleted && 'bg-[var(--color-accent)] text-white',
                    isActive && 'bg-[var(--color-accent-subtle)] text-[var(--color-accent)] ring-1 ring-[var(--color-accent)]/30',
                    !isActive && !isCompleted && 'bg-[var(--color-bg-surface-2)] text-[var(--color-text-muted)]'
                  )}
                >
                  {isCompleted ? <Check size={14} /> : <Icon size={14} />}
                </div>
                <span
                  className={cn(
                    'text-xs font-medium transition-colors',
                    isActive && 'text-[var(--color-text-primary)]',
                    !isActive && !isCompleted && 'text-[var(--color-text-muted)]',
                    isCompleted && 'text-[var(--color-accent)]'
                  )}
                >
                  {s.label}
                </span>
              </div>
              {index < steps.length - 1 && (
                <div className={cn('h-px flex-1 rounded-full transition-colors', step > s.id ? 'bg-[var(--color-accent)]' : 'bg-[var(--color-border-subtle)]')} />
              )}
            </React.Fragment>
          );
        })}
      </div>

      {/* Step Content */}
      <div className="p-6">
        {/* Step 1: Model Config */}
        {step === 1 && (
          <div className="space-y-4">
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              <div>
                <label className="mb-1.5 block text-xs font-medium text-[var(--color-text-secondary)]">
                  智能体名称 <span className="text-[var(--color-error)]">*</span>
                </label>
                <input
                  placeholder="例如：代码助手"
                  value={form['name']}
                  onChange={(e) => updateForm('name', e.target.value)}
                  className={cn(
                    'w-full rounded-xl border bg-[var(--color-bg-surface-2)] px-3.5 py-2.5 text-sm text-[var(--color-text-primary)] placeholder:text-[var(--color-text-muted)] transition-all duration-200 focus:outline-none focus:ring-2',
                    errors['name']
                       ? 'border-[var(--color-error)]/50 focus:ring-[var(--color-error)]/30'
                       : 'border-[var(--color-border-subtle)] focus:border-[var(--color-accent)]/50 focus:ring-[var(--color-accent)]/20'
                   )}
                 />
                 {errors['name'] && (
                   <p className="mt-1 flex items-center gap-1 text-xs text-[var(--color-error)]">
                     <AlertCircle size={11} /> {errors['name']}
                   </p>
                 )}
              </div>

              <div>
                <label className="mb-1.5 block text-xs font-medium text-[var(--color-text-secondary)]">模型提供商</label>
                <select
                  value={form.provider}
                  onChange={(e) => {
                    const prov = PROVIDERS.find((p) => p.id === e.target.value);
                    setForm((prev) => ({ ...prev, provider: e.target.value, model_id: prov?.models[0] || '' }));
                  }}
                  className="w-full rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-2)] px-3.5 py-2.5 text-sm text-[var(--color-text-primary)] transition-all duration-200 focus:border-[var(--color-accent)]/50 focus:outline-none focus:ring-2 focus:ring-[var(--color-accent)]/20"
                >
                  {PROVIDERS.map((p) => (
                    <option key={p.id} value={p.id}>{p.label}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="mb-1.5 block text-xs font-medium text-[var(--color-text-secondary)]">模型</label>
                <select
                  value={form.model_id}
                  onChange={(e) => updateForm('model_id', e.target.value)}
                  className="w-full rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-2)] px-3.5 py-2.5 text-sm text-[var(--color-text-primary)] transition-all duration-200 focus:border-[var(--color-accent)]/50 focus:outline-none focus:ring-2 focus:ring-[var(--color-accent)]/20"
                >
                  {selectedProvider?.models.map((m) => (
                    <option key={m} value={m}>{m}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="mb-1.5 block text-xs font-medium text-[var(--color-text-secondary)]">
                  API 密钥 <span className="text-[var(--color-error)]">*</span>
                </label>
                <input
                  placeholder="sk-..."
                  type="password"
                  value={form['api_key']}
                  onChange={(e) => updateForm('api_key', e.target.value)}
                  className={cn(
                    'w-full rounded-xl border bg-[var(--color-bg-surface-2)] px-3.5 py-2.5 text-sm text-[var(--color-text-primary)] placeholder:text-[var(--color-text-muted)] transition-all duration-200 focus:outline-none focus:ring-2',
                    errors['api_key']
                       ? 'border-[var(--color-error)]/50 focus:ring-[var(--color-error)]/30'
                       : 'border-[var(--color-border-subtle)] focus:border-[var(--color-accent)]/50 focus:ring-[var(--color-accent)]/20'
                   )}
                 />
                 {errors['api_key'] && (
                   <p className="mt-1 flex items-center gap-1 text-xs text-[var(--color-error)]">
                     <AlertCircle size={11} /> {errors['api_key']}
                   </p>
                 )}
              </div>

              <div className="md:col-span-2">
                <label className="mb-1.5 block text-xs font-medium text-[var(--color-text-secondary)]">Base URL（可选）</label>
                <input
                  placeholder="自定义端点 URL"
                  value={form.base_url}
                  onChange={(e) => updateForm('base_url', e.target.value)}
                  className="w-full rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-2)] px-3.5 py-2.5 text-sm text-[var(--color-text-primary)] placeholder:text-[var(--color-text-muted)] transition-all duration-200 focus:border-[var(--color-accent)]/50 focus:outline-none focus:ring-2 focus:ring-[var(--color-accent)]/20"
                />
              </div>

              <div className="md:col-span-2">
                <label className="mb-1.5 block text-xs font-medium text-[var(--color-text-secondary)]">系统提示词（可选）</label>
                <textarea
                  placeholder="你是一个专业的..."
                  value={form.system_prompt}
                  onChange={(e) => updateForm('system_prompt', e.target.value)}
                  rows={3}
                  className="w-full resize-none rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-2)] px-3.5 py-2.5 text-sm text-[var(--color-text-primary)] placeholder:text-[var(--color-text-muted)] transition-all duration-200 focus:border-[var(--color-accent)]/50 focus:outline-none focus:ring-2 focus:ring-[var(--color-accent)]/20"
                />
              </div>
            </div>
          </div>
        )}

        {/* Step 2: Skills */}
        {step === 2 && (
          <div className="space-y-5">
            <p className="text-xs text-[var(--color-text-muted)]">选择技能以增强智能体能力，每个技能会自动启用相关工具。</p>
            {skillCategories.map((cat) => (
              <div key={cat}>
                <h4 className="mb-2.5 text-[10px] font-semibold uppercase tracking-wider text-[var(--color-text-muted)]">{cat}</h4>
                <div className="grid grid-cols-1 gap-2 md:grid-cols-2">
                  {skills
                    .filter((s) => s.category === cat)
                    .map((skill) => (
                      <button
                        key={skill.id}
                        onClick={() => toggleSkill(skill.id)}
                        className={cn(
                          'flex items-start gap-3 rounded-xl border p-3.5 text-left transition-all duration-200',
                          selectedSkills.includes(skill.id)
                            ? 'border-[var(--color-accent)]/40 bg-[var(--color-accent-subtle)] ring-1 ring-[var(--color-accent)]/20'
                            : 'border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-1)] hover:border-[var(--color-border-default)] hover:bg-[var(--color-bg-surface-2)]'
                        )}
                      >
                        <div className={cn(
                          'flex h-5 w-5 shrink-0 items-center justify-center rounded-md border transition-all',
                          selectedSkills.includes(skill.id)
                            ? 'border-[var(--color-accent)] bg-[var(--color-accent)] text-white'
                            : 'border-[var(--color-border-default)] bg-[var(--color-bg-surface-2)]'
                        )}>
                          {selectedSkills.includes(skill.id) && <Check size={12} />}
                        </div>
                        <div className="min-w-0 flex-1">
                          <p className="text-xs font-medium text-[var(--color-text-primary)]">{skill.name}</p>
                          <p className="mt-0.5 text-[10px] text-[var(--color-text-muted)] line-clamp-2">{skill.description}</p>
                        </div>
                      </button>
                    ))}
                </div>
              </div>
            ))}
            {skills.length === 0 && (
              <div className="flex flex-col items-center justify-center py-8">
                <Sparkles size={24} className="text-[var(--color-text-muted)]" />
                <p className="mt-2 text-xs text-[var(--color-text-muted)]">暂无可用技能</p>
              </div>
            )}
          </div>
        )}

        {/* Step 3: Tools */}
        {step === 3 && (
          <div className="space-y-4">
            <p className="text-xs text-[var(--color-text-muted)]">选择额外工具。已选技能的工具将自动启用。</p>
            <div className="flex flex-wrap gap-2">
              {tools.map((tool) => (
                <button
                  key={tool.name}
                  onClick={() => toggleTool(tool.name)}
                  className={cn(
                    'rounded-lg px-3 py-1.5 text-xs font-medium transition-all duration-200',
                    selectedTools.includes(tool.name)
                      ? 'bg-[var(--color-accent)] text-white shadow-sm shadow-[var(--color-accent)]/20'
                      : 'bg-[var(--color-bg-surface-2)] text-[var(--color-text-secondary)] ring-1 ring-[var(--color-border-subtle)] hover:ring-[var(--color-accent)]/30'
                  )}
                >
                  {tool.name}
                </button>
              ))}
            </div>
            {tools.length === 0 && (
              <div className="flex flex-col items-center justify-center py-8">
                <Wrench size={24} className="text-[var(--color-text-muted)]" />
                <p className="mt-2 text-xs text-[var(--color-text-muted)]">暂无可用工具</p>
              </div>
            )}
            {selectedSkills.length > 0 && (
              <div className="rounded-xl bg-[var(--color-accent-subtle)] p-3 ring-1 ring-[var(--color-accent)]/20">
                <p className="text-xs text-[var(--color-accent)]">
                  已选择 {selectedSkills.length} 个技能，相关工具将自动启用
                </p>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Footer Navigation */}
      <div className="flex items-center justify-between border-t border-[var(--color-border-subtle)] px-6 py-4">
        <div>
          {step > 1 ? (
            <button
              onClick={() => setStep(step - 1)}
              className="inline-flex items-center gap-1.5 rounded-lg px-3 py-2 text-xs font-medium text-[var(--color-text-secondary)] transition-colors hover:bg-[var(--color-bg-surface-2)] hover:text-[var(--color-text-primary)]"
            >
              <ChevronLeft size={14} /> 上一步
            </button>
          ) : (
            <button
              onClick={onCancel}
              className="inline-flex items-center gap-1.5 rounded-lg px-3 py-2 text-xs font-medium text-[var(--color-text-muted)] transition-colors hover:text-[var(--color-text-secondary)]"
            >
              取消
            </button>
          )}
        </div>

        <div className="flex items-center gap-2">
          {step < 3 ? (
            <button
              onClick={handleNext}
              className="inline-flex items-center gap-1.5 rounded-xl bg-[var(--color-accent)] px-4 py-2.5 text-xs font-medium text-white shadow-md shadow-[var(--color-accent)]/20 transition-all duration-200 hover:bg-[var(--color-accent-hover)] hover:shadow-lg active:scale-[0.97]"
            >
              下一步 <ChevronRight size={14} />
            </button>
          ) : (
            <button
              onClick={handleSubmit}
              className="inline-flex items-center gap-1.5 rounded-xl bg-[var(--color-accent)] px-5 py-2.5 text-xs font-medium text-white shadow-md shadow-[var(--color-accent)]/20 transition-all duration-200 hover:bg-[var(--color-accent-hover)] hover:shadow-lg active:scale-[0.97]"
            >
              <Check size={14} /> 创建智能体
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
