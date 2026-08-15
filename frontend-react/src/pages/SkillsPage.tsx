import { useState, useEffect, useMemo, useCallback } from 'react';
import { Search, Package, RefreshCw, AlertCircle, Power, PowerOff } from 'lucide-react';
import { api } from '../api';

interface Skill {
  id: number;
  name: string;
  description: string;
  category: string;
  is_enabled: boolean;
  use_count: number;
  tools: string[];
  prompt_template: string;
  path: string;
}

const CATEGORY_LABELS: Record<string, string> = {
  core: '核心引擎',
  engineering: '工程开发',
  quality: '质量保障',
  knowledge: '知识分析',
  productivity: '效率工具',
  research: '研究分析',
  general: '通用',
};

export function SkillsPage() {
  const [skills, setSkills] = useState<Skill[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('');
  const [toggling, setToggling] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();

    const fetchSkills = async () => {
      setLoading(true);
      setError(null);
      try {
        const res = await api.listSkills();
        if (controller.signal.aborted) return;
        setSkills((res as any).skills || []);
      } catch (e: any) {
        if (!controller.signal.aborted) {
          setError(e.message || '加载技能失败');
        }
      }
      if (!controller.signal.aborted) {
        setLoading(false);
      }
    };
    fetchSkills();

    return () => {
      controller.abort();
    };
  }, []);

  const categories = useMemo(() => [...new Set(skills.map(s => s.category))], [skills]);

  const filtered = useMemo(() => {
    if (!searchQuery && !selectedCategory) return skills;
    return skills.filter(s => {
      const matchSearch = !searchQuery || s.name.toLowerCase().includes(searchQuery.toLowerCase()) || s.description.toLowerCase().includes(searchQuery.toLowerCase());
      const matchCat = !selectedCategory || s.category === selectedCategory;
      return matchSearch && matchCat;
    });
  }, [skills, searchQuery, selectedCategory]);

  const grouped = useMemo(() => {
    const result: Record<string, Skill[]> = {};
    for (const skill of filtered) {
      if (!result[skill.category]) result[skill.category] = [];
      result[skill.category]!.push(skill);
    }
    return result;
  }, [filtered]);

  const toggleSkill = useCallback(async (skill: Skill) => {
    const key = `skill-${skill.id}`;
    setToggling(key);
    try {
      await api.updateSkill(String(skill.id), { enabled: !skill.is_enabled });
      setSkills(prev => prev.map(s => s.id === skill.id ? { ...s, is_enabled: !s.is_enabled } : s));
    } catch {
      // ignore
    } finally {
      setToggling(null);
    }
  }, []);

  return (
    <div className="h-full overflow-y-auto p-8">
      <div className="max-w-6xl mx-auto">
        <div className="mb-8">
          <h2 className="text-2xl font-bold text-[var(--color-text-primary)]">技能中心</h2>
          <p className="text-[var(--color-text-secondary)] text-sm mt-1.5">
            发现并管理本地技能包，扩展智能体能力。
          </p>
        </div>

        <div className="flex items-center gap-3 mb-6">
          <div className="relative flex-1 max-w-md">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--color-text-muted)]" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="搜索技能..."
              className="w-full pl-9 pr-4 py-2.5 bg-white/[0.03] border border-[var(--color-border-subtle)] rounded-2xl text-sm text-[var(--color-text-primary)] placeholder:text-[var(--color-text-muted)] focus:outline-none focus:border-[var(--color-accent)]/50 transition-all duration-200"
            />
          </div>
          <div className="flex gap-2 flex-wrap">
            <button
              onClick={() => setSelectedCategory('')}
              className={`px-4 py-2 rounded-2xl text-xs font-semibold transition-all duration-200 border ${
                !selectedCategory
                  ? 'bg-[var(--color-accent)] text-white border-[var(--color-accent)] shadow-lg shadow-[var(--color-accent)]/20'
                  : 'text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] border-[var(--color-border-subtle)] bg-white/[0.03]'
              }`}
            >
              全部
            </button>
            {categories.map(cat => (
              <button
                key={cat}
                onClick={() => setSelectedCategory(cat)}
                className={`px-4 py-2 rounded-2xl text-xs font-semibold transition-all duration-200 border ${
                  selectedCategory === cat
                    ? 'bg-[var(--color-accent)] text-white border-[var(--color-accent)] shadow-lg shadow-[var(--color-accent)]/20'
                    : 'text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] border-[var(--color-border-subtle)] bg-white/[0.03]'
                }`}
              >
                {CATEGORY_LABELS[cat] || cat}
              </button>
            ))}
          </div>
        </div>

        {error && (
          <div className="bg-[var(--color-error)]/10 border border-[var(--color-error)]/30 rounded-2xl p-4 mb-6 flex items-center gap-3">
            <AlertCircle size={18} className="text-[var(--color-error)] shrink-0" />
            <p className="text-sm text-[var(--color-error)] flex-1">{error}</p>
            <button
              onClick={() => window.location.reload()}
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-[var(--color-error)] hover:bg-[var(--color-error)]/10 rounded-xl transition-colors"
            >
              <RefreshCw size={14} /> 重试
            </button>
          </div>
        )}

        {loading && (
          <div className="space-y-6">
            {[1, 2].map(i => (
              <div key={i} className="animate-pulse">
                <div className="h-5 w-24 bg-white/5 rounded-xl mb-4" />
                <div className="grid grid-cols-2 gap-4">
                  {[1, 2].map(j => (
                    <div key={j} className="border border-[var(--color-border-subtle)] rounded-2xl p-5">
                      <div className="flex items-start gap-3">
                        <div className="w-5 h-5 rounded bg-white/5" />
                        <div className="flex-1 space-y-2">
                          <div className="flex items-center gap-2">
                            <div className="h-6 w-6 bg-white/5 rounded-xl" />
                            <div className="h-4 w-24 bg-white/5 rounded-xl" />
                          </div>
                          <div className="h-3 w-full bg-white/5 rounded-xl" />
                          <div className="h-3 w-3/4 bg-white/5 rounded-xl" />
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}

        {!loading && !error && filtered.length === 0 && (
          <div className="text-center py-16">
            <div className="w-16 h-16 rounded-3xl bg-white/5 border border-[var(--color-border-subtle)] flex items-center justify-center mx-auto mb-4">
              <Package size={28} className="text-[var(--color-text-muted)]" />
            </div>
            <p className="text-[var(--color-text-muted)] text-sm">未找到匹配的技能。</p>
          </div>
        )}

        {!loading && !error && filtered.length > 0 && (
          <div className="space-y-8">
            {Object.entries(grouped).map(([category, items]) => (
              <div key={category}>
                <h3 className="text-xs font-semibold text-[var(--color-text-muted)] uppercase tracking-wider mb-4">
                  {CATEGORY_LABELS[category] || category}
                </h3>
                <div className="grid grid-cols-2 gap-4">
                  {items.map(skill => (
                    <div
                      key={skill.id}
                      className="border border-[var(--color-border-subtle)] rounded-2xl p-5 bg-[var(--color-bg-surface-1)] hover:border-[var(--color-accent)]/30 transition-all duration-200"
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-1">
                            <h4 className="text-sm font-semibold text-[var(--color-text-primary)] truncate">{skill.name}</h4>
                            <span className="text-[10px] text-[var(--color-text-muted)] px-2 py-0.5 bg-white/[0.03] border border-[var(--color-border-subtle)] rounded-full shrink-0">
                              {skill.category}
                            </span>
                          </div>
                          <p className="text-xs text-[var(--color-text-muted)] line-clamp-2 mb-3">{skill.description}</p>
                          <div className="flex items-center gap-3 text-[11px] text-[var(--color-text-muted)]">
                            <span>使用 {skill.use_count} 次</span>
                            {skill.tools.length > 0 && <span>· {skill.tools.length} 工具</span>}
                            <span className="truncate">{skill.path.split('/').pop()}</span>
                          </div>
                        </div>
                        <button
                          onClick={() => toggleSkill(skill)}
                          disabled={toggling === `skill-${skill.id}`}
                          className={`shrink-0 w-8 h-8 rounded-xl flex items-center justify-center transition-all duration-200 ${
                            skill.is_enabled
                              ? 'bg-[var(--color-success)]/10 text-[var(--color-success)] hover:bg-[var(--color-success)]/20'
                              : 'bg-white/[0.03] text-[var(--color-text-muted)] hover:bg-white/[0.06]'
                          }`}
                          title={skill.is_enabled ? '禁用' : '启用'}
                        >
                          {skill.is_enabled ? <Power size={14} /> : <PowerOff size={14} />}
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
