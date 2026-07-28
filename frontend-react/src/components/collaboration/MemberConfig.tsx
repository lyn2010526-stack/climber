import { Plus, X, Shield, Wrench } from 'lucide-react';

interface MemberConfigProps {
  members: MemberConfig[];
  onAdd: (member: MemberConfig) => void;
  onRemove: (id: string) => void;
  onUpdate: (id: string, updates: Partial<MemberConfig>) => void;
}

export interface MemberConfig {
  id: string;
  name: string;
  provider: string;
  modelId: string;
  apiKey: string;
  avatarUrl?: string;
  role: 'worker' | 'reviewer';
  reviewType?: 'code' | 'architecture' | 'security';
  tools: string[];
}

const PROVIDERS = ['openai', 'anthropic', 'google', 'ollama'];

const PROVIDER_MODELS: Record<string, string[]> = {
  openai: ['gpt-4', 'gpt-4-turbo', 'gpt-3.5-turbo', 'o1-preview'],
  anthropic: ['claude-3-opus', 'claude-3-sonnet', 'claude-3-haiku', 'claude-3.5-sonnet'],
  google: ['gemini-pro', 'gemini-ultra', 'gemini-1.5-pro'],
  ollama: ['llama3', 'mistral', 'codellama', 'qwen2'],
};

const ROLE_ICONS = {
  worker: Wrench,
  reviewer: Shield,
};

const REVIEW_TYPES = [
  { value: 'code', label: 'Code Review' },
  { value: 'architecture', label: 'Architecture Review' },
  { value: 'security', label: 'Security Review' },
];

export function MemberConfig({ members, onAdd, onRemove, onUpdate }: MemberConfigProps) {
  const handleAdd = () => {
    onAdd({
      id: crypto.randomUUID(),
      name: `Agent ${members.length + 1}`,
      provider: 'openai',
      modelId: 'gpt-4',
      apiKey: '',
      role: members.length === 0 ? 'worker' : 'reviewer',
      reviewType: 'code',
      tools: ['web_search', 'read_file', 'write_file'],
    });
  };

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
         <span className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider">
           AI 成员 ({members.length})
         </span>
        <button
          onClick={handleAdd}
          className="flex items-center gap-1 text-[10px] text-blue-400 hover:text-blue-400/80"
        >
          <Plus size={10} />
           添加
        </button>
      </div>

      <div className="space-y-2 max-h-64 overflow-y-auto">
        {members.map((member) => {
          const RoleIcon = ROLE_ICONS[member.role];
          return (
            <div key={member.id} className="p-2 bg-gray-700 rounded-lg border border-gray-700 space-y-2">
              <div className="flex items-center gap-2">
                <RoleIcon size={12} className={member.role === 'worker' ? 'text-green-400' : 'text-amber-400'} />
                <input
                  type="text"
                  value={member.name}
                  onChange={(e) => onUpdate(member.id, { name: e.target.value })}
                  className="flex-1 bg-transparent text-[11px] text-gray-100 focus:outline-none"
                />
                <select
                  value={member.role}
                  onChange={(e) => onUpdate(member.id, { role: e.target.value as 'worker' | 'reviewer' })}
                  className="bg-gray-800 text-[10px] text-gray-100 border border-gray-700 rounded px-1 py-0.5 focus:outline-none"
                >
                   <option value="worker">执行者</option>
                   <option value="reviewer">审核者</option>
                </select>
                <button
                  onClick={() => onRemove(member.id)}
                  className="text-gray-500 hover:text-red-400"
                >
                  <X size={10} />
                </button>
              </div>

              <div className="grid grid-cols-2 gap-1.5">
                <select
                  value={member.provider}
                  onChange={(e) => onUpdate(member.id, { provider: e.target.value, modelId: PROVIDER_MODELS[e.target.value]?.[0] || '' })}
                  className="bg-gray-800 text-[10px] text-gray-100 border border-gray-700 rounded px-1.5 py-1 focus:outline-none"
                >
                  {PROVIDERS.map((p) => (
                    <option key={p} value={p}>{p}</option>
                  ))}
                </select>
                <select
                  value={member.modelId}
                  onChange={(e) => onUpdate(member.id, { modelId: e.target.value })}
                  className="bg-gray-800 text-[10px] text-gray-100 border border-gray-700 rounded px-1.5 py-1 focus:outline-none"
                >
                  {(PROVIDER_MODELS[member.provider] || []).map((m) => (
                    <option key={m} value={m}>{m}</option>
                  ))}
                </select>
              </div>

              <input
                type="password"
                value={member.apiKey}
                onChange={(e) => onUpdate(member.id, { apiKey: e.target.value })}
                 placeholder="API 密钥"
                className="w-full px-2 py-1 bg-gray-800 border border-gray-700 rounded text-[10px] text-gray-100 placeholder:text-gray-500 focus:outline-none focus:border-blue-500/50"
              />

              {member.role === 'reviewer' && (
                <select
                  value={member.reviewType}
                  onChange={(e) => onUpdate(member.id, { reviewType: e.target.value as 'code' | 'architecture' | 'security' })}
                  className="w-full bg-gray-800 text-[10px] text-gray-100 border border-gray-700 rounded px-1.5 py-1 focus:outline-none"
                >
                  {REVIEW_TYPES.map((rt) => (
                    <option key={rt.value} value={rt.value}>{rt.label}</option>
                  ))}
                </select>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
