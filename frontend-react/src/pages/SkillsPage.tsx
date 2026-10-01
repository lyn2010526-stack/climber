import { useState, useEffect, useCallback } from 'react';
import { Search, Package, RefreshCw, AlertCircle, Power, Wrench, CheckCircle2, CircleSlash, FileText, CircleHelp } from 'lucide-react';
import { api } from '../api';
import { useTranslation } from '../i18n';
import { includesQuery } from '../lib/search';
import { PageHeader } from '../components/ui/PageHeader';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { EmptyState } from '../components/ui/EmptyState';
import { Card } from '../components/ui/Card';
import { SkeletonList } from '../components/ui/Skeleton';

interface Skill {
  id: number;
  name: string;
  description: string;
  category: string;
  is_enabled?: boolean;
  use_count: number;
  tools: string[];
  prompt_template: string;
  path: string;
}

function SkillStatus({ enabled }: { enabled?: boolean }) {
  const { t } = useTranslation();
  return (
    <span
      role="status"
      data-skill-status={enabled === undefined ? 'unreported' : enabled ? 'enabled' : 'disabled'}
      className={`inline-flex shrink-0 items-center gap-1.5 text-xs ${enabled === undefined ? 'text-[var(--color-text-disabled)]' : enabled ? 'text-[var(--color-text-secondary)]' : 'text-[var(--color-text-muted)]'}`}
    >
      {enabled === undefined
        ? <CircleHelp size={13} aria-hidden="true" className="shrink-0" />
        : enabled
        ? <CheckCircle2 size={13} aria-hidden="true" className="shrink-0" />
        : <CircleSlash size={13} aria-hidden="true" className="shrink-0" />}
      {enabled === undefined ? t('agents.status_unreported') : enabled ? t('agents.status_configured') : t('agents.status_disabled')}
    </span>
  );
}

export function SkillsPage() {
  const { t } = useTranslation();
  const [skills, setSkills] = useState<Skill[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('');
  const [toggling, setToggling] = useState<string | null>(null);
  const [toggleError, setToggleError] = useState<string | null>(null);

  const fetchSkills = useCallback(async () => {
    setLoading(true);
    setError(null);
    setToggleError(null);
    try {
      const res = await api.listSkills();
      setSkills(Array.isArray(res) ? res : (res as any).skills || []);
    } catch (e: any) {
      setError(e.message || t('common.error'));
    }
    setLoading(false);
  }, [t]);
  useEffect(() => {
    fetchSkills();
  }, [fetchSkills]);

  const categories = [...new Set(skills.map(s => s.category).filter(Boolean))];

  const filtered = skills.filter(skill =>
    includesQuery([skill.name, skill.description, skill.path], searchQuery) &&
    (!selectedCategory || skill.category === selectedCategory)
  );

  const toggleSkill = async (skill: Skill) => {
    setToggling(`skill-${skill.id}`);
    setToggleError(null);
    try {
      await api.updateSkill(String(skill.id), { enabled: !skill.is_enabled });
      setSkills(prev => prev.map(s => s.id === skill.id ? { ...s, is_enabled: !s.is_enabled } : s));
    } catch (e) {
      setToggleError(e instanceof Error ? e.message : t('common.error'));
    } finally {
      setToggling(null);
    }
  };

  const hasFilters = Boolean(searchQuery || selectedCategory);
  const showList = !loading && !error;

  return (
    <div className="page-scroll page-transition">
      <div className="page-container">
        <PageHeader
          title={t('navigation.skills')}
          icon={<Package size={20} aria-hidden="true" />}
          actions={
            <Button variant="outline" size="sm" icon={<RefreshCw size={14} />} disabled={loading || toggling !== null} onClick={fetchSkills}>
              {t('common.refresh')}
            </Button>
          }
        />

        <div className="space-y-4">
        {showList && skills.length > 0 && (
          <div className="flex flex-wrap items-center gap-3">
            <div className="w-full max-w-xs">
              <Input
                size="sm"
                placeholder={t('common.search')}
                aria-label={t('common.search')}
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                icon={<Search size={14} aria-hidden="true" />}
              />
            </div>
            <div className="flex flex-wrap items-center gap-1" role="group" aria-label={t('common.filter')}>
              <button
                type="button"
                onClick={() => setSelectedCategory('')}
                aria-pressed={!selectedCategory}
                className={`rounded-[var(--radius-md)] border px-2.5 py-1 text-xs font-medium transition-colors ${
                  !selectedCategory
                    ? 'border-[var(--color-border-strong)] bg-[var(--color-bg-surface-3)] text-[var(--color-text-primary)]'
                    : 'border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-2)] text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]'
                }`}
              >
                {t('common.all')}
              </button>
              {categories.map(cat => (
                <button
                  type="button"
                  key={cat}
                  onClick={() => setSelectedCategory(cat)}
                  aria-pressed={selectedCategory === cat}
                  className={`rounded-[var(--radius-md)] border px-2.5 py-1 text-xs font-medium transition-colors ${
                    selectedCategory === cat
                      ? 'border-[var(--color-border-strong)] bg-[var(--color-bg-surface-3)] text-[var(--color-text-primary)]'
                      : 'border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-2)] text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]'
                  }`}
                >
                  {cat}
                </button>
              ))}
            </div>
            <span className="shrink-0 text-xs tabular-nums text-[var(--color-text-muted)]" aria-live="polite">
              {filtered.length} / {skills.length}
            </span>
          </div>
        )}

        {(error || toggleError) && (
          <div role="alert" className="flex items-center gap-3 rounded-[var(--radius-md)] border border-[var(--color-error)]/30 bg-[var(--color-error-subtle)] p-3">
            <AlertCircle size={16} aria-hidden="true" className="shrink-0 text-[var(--color-error)]" />
            <p className="flex-1 text-sm text-[var(--color-error)]">{error || toggleError}</p>
            {error && (
              <Button variant="ghost" size="sm" icon={<RefreshCw size={14} />} onClick={fetchSkills}>
                {t('common.retry')}
              </Button>
            )}
          </div>
        )}

        {loading && (
          <div aria-busy="true" aria-label={t('common.loading')}>
            <SkeletonList count={3} />
          </div>
        )}

        {showList && filtered.length === 0 && (
          <Card padding="none" className="overflow-hidden">
            <EmptyState
              className="w-full"
              icon={hasFilters ? <Search size={20} aria-hidden="true" /> : <Package size={20} aria-hidden="true" />}
              title={hasFilters ? t('common.no_results') : t('common.no_data')}
              action={hasFilters ? (
                <Button variant="outline" size="sm" onClick={() => { setSearchQuery(''); setSelectedCategory(''); }}>
                  {t('common.clear')}
                </Button>
              ) : undefined}
            />
          </Card>
        )}

        {showList && filtered.length > 0 && (
          <Card padding="none" className="overflow-hidden">
            <ul className="divide-y divide-[var(--color-border-subtle)]" aria-label={t('navigation.skills')}>
            {filtered.map(skill => {
              const fileName = (skill.path || '').split('/').filter(Boolean).pop();
              return (
                <li key={skill.id} className="flex items-center gap-3 bg-[var(--color-bg-surface-1)] px-3 py-2 md:px-4">
                  <Package size={16} aria-hidden="true" className="shrink-0 text-[var(--color-text-muted)]" />
                  <div className="min-w-0 flex-1">
                    <div className="flex min-w-0 items-center gap-2">
                      <span className="truncate text-sm font-medium text-[var(--color-text-primary)]">{skill.name}</span>
                      {fileName && (
                        <span className="hidden shrink-0 items-center gap-1 text-xs text-[var(--color-text-muted)] lg:inline-flex">
                          <FileText size={11} aria-hidden="true" />{fileName}
                        </span>
                      )}
                    </div>
                    {skill.description && (
                      <p className="truncate text-xs text-[var(--color-text-muted)]">{skill.description}</p>
                    )}
                  </div>
                  <div className="hidden shrink-0 items-center gap-3 text-xs text-[var(--color-text-muted)] md:flex">
                    <span className="tabular-nums">{t('common.count')}: {skill.use_count}</span>
                    <span className="inline-flex items-center gap-1 tabular-nums"><Wrench size={12} aria-hidden="true" />{skill.tools?.length ?? 0}</span>
                  </div>
                  <SkillStatus enabled={skill.is_enabled} />
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => toggleSkill(skill)}
                    disabled={toggling !== null || skill.is_enabled === undefined}
                    loading={toggling === `skill-${skill.id}`}
                    aria-label={skill.is_enabled === undefined ? `${t('agents.status_unreported')}: ${skill.name}` : `${skill.is_enabled ? t('agents.deactivate') : t('agents.activate')}: ${skill.name}`}
                    icon={skill.is_enabled ? <Power size={13} aria-hidden="true" /> : undefined}
                  >
                    {skill.is_enabled === undefined ? t('agents.status_unreported') : skill.is_enabled ? t('agents.deactivate') : t('agents.activate')}
                  </Button>
                </li>
              );
            })}
          </ul>
          </Card>
        )}
        </div>
      </div>
    </div>
  );
}
