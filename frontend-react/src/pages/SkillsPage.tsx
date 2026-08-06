import { useState, useEffect } from 'react';
import { Search, Package, RefreshCw, AlertCircle, Power, PowerOff } from 'lucide-react';
import { api } from '../api';
import { PageHeader } from '../components/ui/PageHeader';
import { Card, CardContent } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import { Input } from '../components/ui/Input';
import { EmptyState } from '../components/ui/EmptyState';
import { SkeletonCard } from '../components/ui/Skeleton';

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
    const fetchSkills = async () => {
      setLoading(true);
      setError(null);
      try {
        const res = await api.listSkills();
        setSkills((res as any).skills || []);
      } catch (e: any) {
        setError(e.message || '加载技能失败');
      }
      setLoading(false);
    };
    fetchSkills();
  }, []);

  const categories = [...new Set(skills.map(s => s.category))];
  const filtered = skills.filter(s => {
    const matchSearch = !searchQuery || s.name.toLowerCase().includes(searchQuery.toLowerCase()) || s.description.toLowerCase().includes(searchQuery.toLowerCase());
    const matchCat = !selectedCategory || s.category === selectedCategory;
    return matchSearch && matchCat;
  });

  const grouped: Record<string, Skill[]> = {};
  for (const skill of filtered) {
    if (!grouped[skill.category]) grouped[skill.category] = [];
    grouped[skill.category]!.push(skill);
  }

  const toggleSkill = async (skill: Skill) => {
    setToggling(`skill-${skill.id}`);
    try {
      await api.updateSkill(String(skill.id), { enabled: !skill.is_enabled });
      setSkills(prev => prev.map(s => s.id === skill.id ? { ...s, is_enabled: !s.is_enabled } : s));
    } catch { /* ignore */ } finally {
      setToggling(null);
    }
  };

  return (
    <div className="h-full overflow-y-auto page-transition">
      <div className="p-4 md:p-6 lg:p-8 max-w-6xl mx-auto">
        <PageHeader
          title="技能中心"
          description="发现并管理本地技能包，扩展智能体能力"
          icon={<Package size={20} />}
        />

        <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3 mb-6">
          <div className="w-full sm:max-w-xs">
            <Input
              placeholder="搜索技能..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              icon={<Search size={16} />}
            />
          </div>
          <div className="flex gap-2 flex-wrap">
            <button
              onClick={() => setSelectedCategory('')}
              className={`px-4 py-2 rounded-xl text-xs font-semibold transition-all duration-200 border ${
                !selectedCategory
                  ? 'bg-[var(--color-accent)] text-white border-[var(--color-accent)] shadow-lg shadow-[var(--color-accent)]/20'
                  : 'text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-2)]'
              }`}
            >
              全部
            </button>
            {categories.map(cat => (
              <button
                key={cat}
                onClick={() => setSelectedCategory(cat)}
                className={`px-4 py-2 rounded-xl text-xs font-semibold transition-all duration-200 border ${
                  selectedCategory === cat
                    ? 'bg-[var(--color-accent)] text-white border-[var(--color-accent)] shadow-lg shadow-[var(--color-accent)]/20'
                    : 'text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-2)]'
                }`}
              >
                {CATEGORY_LABELS[cat] || cat}
              </button>
            ))}
          </div>
        </div>

        {error && (
          <Card variant="default" className="mb-6 border-[var(--color-error)]/30">
            <CardContent className="p-4 flex items-center gap-3">
              <AlertCircle size={18} className="text-[var(--color-error)] shrink-0" />
              <p className="text-sm text-[var(--color-error)] flex-1">{error}</p>
              <Button variant="outline" size="sm" icon={<RefreshCw size={14} />} onClick={() => window.location.reload()}>
                重试
              </Button>
            </CardContent>
          </Card>
        )}

        {loading && (
          <div className="space-y-6">
            {[1, 2].map(i => (
              <div key={i}>
                <div className="h-5 w-24 bg-[var(--color-bg-surface-2)] rounded-xl mb-4" />
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {[1, 2].map(j => <SkeletonCard key={j} />)}
                </div>
              </div>
            ))}
          </div>
        )}

        {!loading && !error && filtered.length === 0 && (
          <EmptyState
            icon="file"
            title="未找到匹配的技能"
            description="尝试其他搜索关键词或分类"
          />
        )}

        {!loading && !error && filtered.length > 0 && (
          <div className="space-y-8 stagger-children">
            {Object.entries(grouped).map(([category, items]) => (
              <div key={category}>
                <h3 className="text-xs font-semibold text-[var(--color-text-muted)] uppercase tracking-wider mb-4">
                  {CATEGORY_LABELS[category] || category}
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {items.map(skill => (
                    <Card key={skill.id} variant="default" className="hover-lift">
                      <CardContent className="p-5">
                        <div className="flex items-start justify-between gap-3">
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 mb-1">
                              <h4 className="text-sm font-semibold text-[var(--color-text-primary)] truncate">{skill.name}</h4>
                              <Badge variant="default" size="xs">{skill.category}</Badge>
                            </div>
                            <p className="text-xs text-[var(--color-text-muted)] line-clamp-2 mb-3">{skill.description}</p>
                            <div className="flex items-center gap-3 text-[11px] text-[var(--color-text-muted)]">
                              <span>使用 {skill.use_count} 次</span>
                              {skill.tools.length > 0 && <span>{skill.tools.length} 工具</span>}
                              <span className="truncate">{skill.path.split('/').pop()}</span>
                            </div>
                          </div>
                          <button
                            onClick={() => toggleSkill(skill)}
                            disabled={toggling === `skill-${skill.id}`}
                            className={`shrink-0 w-8 h-8 rounded-xl flex items-center justify-center transition-all duration-200 border ${
                              skill.is_enabled
                                ? 'bg-[var(--color-success)]/10 text-[var(--color-success)] border-[var(--color-success)]/20 hover:bg-[var(--color-success)]/20'
                                : 'bg-[var(--color-bg-surface-2)] text-[var(--color-text-muted)] border-[var(--color-border-subtle)] hover:bg-[var(--color-bg-surface-3)]'
                            }`}
                            title={skill.is_enabled ? '禁用' : '启用'}
                          >
                            {skill.is_enabled ? <Power size={14} /> : <PowerOff size={14} />}
                          </button>
                        </div>
                      </CardContent>
                    </Card>
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
