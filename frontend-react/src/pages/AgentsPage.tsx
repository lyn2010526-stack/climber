import { useState, useEffect } from 'react';
import { Plus, Trash2, Bot, Sparkles, ChevronRight, ChevronLeft, Check, RefreshCw, AlertCircle } from 'lucide-react';
import { api } from '../api';

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

export function AgentsPage() {
  const [agents, setAgents] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [step, setStep] = useState(1);
  const [form, setForm] = useState({
    name: '', provider: 'openai', model_id: 'gpt-4o',
    api_key: '', system_prompt: '', description: '', base_url: '',
  });
  const [tools, setTools] = useState<any[]>([]);
  const [selectedTools, setSelectedTools] = useState<string[]>([]);
  const [skills, setSkills] = useState<Skill[]>([]);
  const [selectedSkills, setSelectedSkills] = useState<string[]>([]);

  useEffect(() => {
    loadAgents();
    api.listTools().then(setTools).catch(() => {});
    api.getMarketplace().then(data => setSkills(data.skills || [])).catch(() => {});
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
    await api.createAgent({
      ...form,
      tools: selectedTools,
      skills: selectedSkills,
    });
    setShowForm(false);
    setStep(1);
    setSelectedSkills([]);
    setSelectedTools([]);
    loadAgents();
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

  const skillCategories = [...new Set(skills.map(s => s.category))];

  return (
    <div className="h-full overflow-y-auto p-8">
      <div className="max-w-4xl mx-auto">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h2 className="text-2xl font-bold text-white">智能体</h2>
            <p className="text-gray-400 text-sm mt-1.5">创建和管理自定义模型与技能的 AI 智能体</p>
          </div>
          <button
            onClick={() => { setShowForm(!showForm); setStep(1); }}
            className="flex items-center gap-2 px-5 py-2.5 bg-[#007AFF] hover:bg-[#007AFF]/90 text-white rounded-2xl text-sm font-semibold transition-all duration-200 shadow-lg shadow-blue-500/20 active:scale-[0.97]"
          >
             <Plus size={16} /> 新建智能体
          </button>
        </div>

        {/* Multi-step creation form */}
        {showForm && (
          <div className="bg-white/[0.04] border border-white/[0.08] rounded-3xl p-6 mb-6 backdrop-blur-sm">
            {/* Step indicator */}
            <div className="flex items-center gap-3 mb-6">
              {[1, 2, 3].map(s => (
                <div key={s} className="flex items-center gap-2">
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-semibold transition-all duration-200 ${
                    step >= s ? 'bg-[#007AFF] text-white shadow-lg shadow-blue-500/20' : 'bg-white/5 text-gray-500 border border-white/10'
                  }`}>
                    {step > s ? <Check size={14} /> : s}
                  </div>
                  <span className={`text-sm font-medium ${step >= s ? 'text-gray-100' : 'text-gray-500'}`}>
                     {s === 1 ? '模型' : s === 2 ? '技能' : '工具'}
                  </span>
                  {s < 3 && <div className={`w-12 h-0.5 rounded-full ${step > s ? 'bg-[#007AFF]' : 'bg-white/10'}`} />}
                </div>
              ))}
            </div>

            {/* Step 1: Model & API */}
            {step === 1 && (
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                     <label className="block text-sm font-medium text-gray-400 mb-2">智能体名称</label>
                     <input
                       placeholder="我的智能体"
                      value={form.name}
                      onChange={(e) => setForm({ ...form, name: e.target.value })}
                      className="w-full px-4 py-2.5 bg-white/5 border border-white/10 rounded-2xl text-sm text-gray-200 focus:outline-none focus:border-[#007AFF]/50 focus:bg-white/10 transition-all duration-200"
                    />
                  </div>
                  <div>
                     <label className="block text-sm font-medium text-gray-400 mb-2">提供商</label>
                    <select
                      value={form.provider}
                      onChange={(e) => {
                        const prov = PROVIDERS.find(p => p.id === e.target.value);
                        setForm({ ...form, provider: e.target.value, model_id: prov?.models[0] || '' });
                      }}
                      className="w-full px-4 py-2.5 bg-white/5 border border-white/10 rounded-2xl text-sm text-gray-200"
                    >
                      {PROVIDERS.map(p => <option key={p.id} value={p.id}>{p.label}</option>)}
                    </select>
                  </div>
                  <div>
                     <label className="block text-sm font-medium text-gray-400 mb-2">模型</label>
                    <select
                      value={form.model_id}
                      onChange={(e) => setForm({ ...form, model_id: e.target.value })}
                      className="w-full px-4 py-2.5 bg-white/5 border border-white/10 rounded-2xl text-sm text-gray-200"
                    >
                      {selectedProvider?.models.map(m => <option key={m} value={m}>{m}</option>)}
                    </select>
                  </div>
                  <div>
                     <label className="block text-sm font-medium text-gray-400 mb-2">API 密钥</label>
                     <input
                       placeholder="sk-..."
                      type="password"
                      value={form.api_key}
                      onChange={(e) => setForm({ ...form, api_key: e.target.value })}
                      className="w-full px-4 py-2.5 bg-white/5 border border-white/10 rounded-2xl text-sm text-gray-200 focus:outline-none focus:border-[#007AFF]/50 transition-all duration-200"
                    />
                  </div>
                  <div className="col-span-2">
                     <label className="block text-sm font-medium text-gray-400 mb-2">Base URL（可选）</label>
                     <input
                       placeholder="自定义端点 URL（例如：Ollama 的 http://localhost:11434）"
                      value={form.base_url}
                      onChange={(e) => setForm({ ...form, base_url: e.target.value })}
                      className="w-full px-4 py-2.5 bg-white/5 border border-white/10 rounded-2xl text-sm text-gray-200 focus:outline-none focus:border-[#007AFF]/50 transition-all duration-200"
                    />
                  </div>
                  <div className="col-span-2">
                     <label className="block text-sm font-medium text-gray-400 mb-2">系统提示词（可选）</label>
                     <textarea
                       placeholder="你是一个有用的助手..."
                      value={form.system_prompt}
                      onChange={(e) => setForm({ ...form, system_prompt: e.target.value })}
                      className="w-full px-4 py-2.5 bg-white/5 border border-white/10 rounded-2xl text-sm text-gray-200 resize-none h-20 focus:outline-none focus:border-[#007AFF]/50 transition-all duration-200"
                    />
                  </div>
                </div>
              </div>
            )}

            {/* Step 2: Skills */}
            {step === 2 && (
              <div>
                <p className="text-sm text-gray-400 mb-5">
                  选择技能以增强此智能体 — 每个技能都会添加专业知识与工具。
                </p>
                {skillCategories.map(cat => (
                  <div key={cat} className="mb-6">
                    <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">{cat}</h4>
                    <div className="grid grid-cols-2 gap-3">
                      {skills.filter(s => s.category === cat).map(skill => (
                        <button
                          key={skill.id}
                          onClick={() => toggleSkill(skill.id)}
                          className={`p-4 rounded-2xl border text-left transition-all duration-200 ${
                            selectedSkills.includes(skill.id)
                              ? 'border-[#007AFF]/50 bg-blue-500/5 shadow-sm shadow-blue-500/10'
                              : 'border-white/10 hover:border-[#007AFF]/30 bg-white/[0.02]'
                          }`}
                        >
                          <div className="flex items-center gap-2.5 mb-1.5">
                            <span className="text-lg">{skill.icon}</span>
                            <span className="font-semibold text-sm text-gray-200">{skill.name}</span>
                            {selectedSkills.includes(skill.id) && (
                              <Check size={14} className="text-[#007AFF] ml-auto" />
                            )}
                          </div>
                          <p className="text-xs text-gray-500 line-clamp-2">{skill.description}</p>
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
                <p className="text-sm text-gray-400 mb-4">
                  选择额外工具。你已选择的技能会自动启用其工具。
                </p>
                <div className="flex flex-wrap gap-2">
                  {tools.map(tool => (
                    <button
                      key={tool.name}
                      onClick={() => toggleTool(tool.name)}
                      className={`px-4 py-2 rounded-2xl text-xs font-semibold transition-all duration-200 ${
                        selectedTools.includes(tool.name)
                          ? 'bg-[#007AFF] text-white shadow-lg shadow-blue-500/20'
                          : 'bg-white/5 text-gray-400 border border-white/10 hover:border-[#007AFF]/30'
                      }`}
                    >
                      {tool.name}
                    </button>
                  ))}
                </div>
                {selectedSkills.length > 0 && (
                  <div className="mt-4 p-3 bg-blue-500/5 rounded-2xl border border-[#007AFF]/20">
                    <p className="text-xs text-blue-400">
                      {selectedSkills.length} skill(s) selected — their tools are automatically included.
                    </p>
                  </div>
                )}
              </div>
            )}

            {/* Navigation */}
            <div className="flex justify-between mt-6 pt-4 border-t border-white/10">
              {step > 1 ? (
                <button
                  onClick={() => setStep(step - 1)}
                  className="flex items-center gap-2 px-4 py-2 text-gray-400 hover:text-gray-100 text-sm transition-colors"
                >
                   <ChevronLeft size={16} /> 上一步
                </button>
              ) : <div />}
              {step < 3 ? (
                <button
                  onClick={() => setStep(step + 1)}
                  disabled={step === 1 && (!form.name || !form.api_key)}
                  className="flex items-center gap-2 px-5 py-2.5 bg-[#007AFF] hover:bg-[#007AFF]/90 text-white rounded-2xl text-sm font-semibold disabled:opacity-40 transition-all duration-200 active:scale-[0.97]"
                >
                   下一步 <ChevronRight size={16} />
                </button>
              ) : (
                <button
                  onClick={createAgent}
                  className="px-6 py-2.5 bg-[#007AFF] hover:bg-[#007AFF]/90 text-white rounded-2xl text-sm font-semibold shadow-lg shadow-blue-500/20 transition-all duration-200 active:scale-[0.97]"
                >
                   创建智能体
                </button>
              )}
            </div>
          </div>
        )}

        {/* Error state */}
        {error && (
          <div className="bg-red-500/10 border border-red-500/30 rounded-2xl p-4 mb-6 flex items-center gap-3">
            <AlertCircle size={18} className="text-red-400 shrink-0" />
            <p className="text-sm text-red-400 flex-1">{error}</p>
            <button
              onClick={loadAgents}
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-red-400 hover:bg-red-500/10 rounded-xl transition-colors"
            >
              <RefreshCw size={14} /> Retry
            </button>
          </div>
        )}

        {/* Loading skeleton */}
        {loading && (
          <div className="space-y-3">
            {[1, 2, 3].map(i => (
              <div key={i} className="bg-white/[0.04] border border-white/[0.08] rounded-2xl p-5 animate-pulse">
                <div className="flex items-center gap-4">
                  <div className="w-10 h-10 rounded-2xl bg-white/5" />
                  <div className="flex-1 space-y-2">
                    <div className="h-4 w-32 bg-white/5 rounded-xl" />
                    <div className="h-3 w-48 bg-white/5 rounded-xl" />
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
                className="bg-white/[0.04] border border-white/[0.08] rounded-2xl p-5 flex items-center gap-4 hover:border-[#007AFF]/30 transition-all duration-200 backdrop-blur-sm"
              >
                <div className="w-10 h-10 rounded-2xl bg-blue-500/10 flex items-center justify-center">
                  <Bot size={20} className="text-blue-400" />
                </div>
                <div className="flex-1">
                  <h3 className="font-semibold text-gray-200">{agent.name}</h3>
                  <p className="text-sm text-gray-500">
                    {agent.provider}:{agent.model_id}
                    {agent.tools?.length > 0 && ` | ${agent.tools.length} tools`}
                    {agent.skill_ids?.length > 0 && ` | ${agent.skill_ids.length} skills`}
                  </p>
                </div>
                <button
                  onClick={() => deleteAgent(agent.id)}
                  className="p-2 hover:bg-red-500/10 rounded-xl text-gray-400 hover:text-red-400 transition-all duration-200"
                >
                  <Trash2 size={16} />
                </button>
              </div>
            ))}
            {agents.length === 0 && !showForm && (
              <div className="text-center py-16">
                <div className="w-16 h-16 rounded-3xl bg-white/5 border border-white/10 flex items-center justify-center mx-auto mb-4">
                  <Sparkles size={28} className="text-gray-600" />
                </div>
                <p className="text-gray-500 text-sm">暂无智能体。创建你的第一个智能体开始使用。</p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
