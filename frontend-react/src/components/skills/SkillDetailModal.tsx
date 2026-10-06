import { useCallback, useEffect, useState } from 'react';
import {
  AlertCircle,
  CheckCircle2,
  FlaskConical,
  History,
  Play,
  Plus,
  RefreshCw,
  Save,
  XCircle,
} from 'lucide-react';
import { api, type SkillTestCase, type SkillTestRunResult, type SkillVersion } from '../../api';
import { useTranslation } from '../../i18n';
import { Modal } from '../ui/Modal';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../ui/Tabs';
import { Button } from '../ui/Button';
import { Input } from '../ui/Input';
import { EmptyState } from '../ui/EmptyState';

export interface SkillDetailModalProps {
  /** Skill to manage; `null` closes the dialog. */
  skill: { id: string | number; name: string } | null;
  onClose: () => void;
}

function formatTime(iso: string | null): string {
  if (!iso) return '—';
  const date = new Date(iso);
  return Number.isNaN(date.getTime()) ? iso : date.toLocaleString();
}

function InlineError({ message }: { message: string }) {
  return (
    <div
      role="alert"
      className="flex items-center gap-2 rounded-[var(--radius-md)] border border-[var(--color-error)]/30 bg-[var(--color-error-subtle)] p-2.5 text-sm text-[var(--color-error)]"
    >
      <AlertCircle size={14} aria-hidden="true" className="shrink-0" />
      <span className="flex-1">{message}</span>
    </div>
  );
}

function VersionsTab({ skillId }: { skillId: string }) {
  const { t } = useTranslation();
  const [versions, setVersions] = useState<SkillVersion[]>([]);
  const [activeVersionId, setActiveVersionId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [changelog, setChangelog] = useState('');
  const [saving, setSaving] = useState(false);
  const [activating, setActivating] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.listSkillVersions(skillId);
      setVersions(Array.isArray(res.versions) ? res.versions : []);
      setActiveVersionId(res.active_version_id ?? null);
    } catch (e) {
      setError(e instanceof Error ? e.message : t('common.error', { defaultValue: 'Error' }));
    } finally {
      setLoading(false);
    }
  }, [skillId, t]);

  useEffect(() => {
    void load();
  }, [load]);

  const snapshot = async () => {
    setSaving(true);
    setError(null);
    try {
      await api.createSkillVersion(skillId, changelog.trim() ? { changelog: changelog.trim() } : {});
      setChangelog('');
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : t('common.error', { defaultValue: 'Error' }));
    } finally {
      setSaving(false);
    }
  };

  const activate = async (versionId: string) => {
    setActivating(versionId);
    setError(null);
    try {
      await api.activateSkillVersion(skillId, versionId);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : t('common.error', { defaultValue: 'Error' }));
    } finally {
      setActivating(null);
    }
  };

  return (
    <div className="space-y-3">
      {error && <InlineError message={error} />}

      <div className="flex flex-wrap items-center gap-2">
        <div className="min-w-0 flex-1">
          <Input
            size="sm"
            value={changelog}
            onChange={(e) => setChangelog(e.target.value)}
            placeholder={t('skills.version_changelog_ph', { defaultValue: 'Changelog note (optional)' })}
            aria-label={t('skills.version_changelog', { defaultValue: 'Changelog' })}
          />
        </div>
        <Button
          variant="outline"
          size="sm"
          icon={<Save size={13} aria-hidden="true" />}
          loading={saving}
          disabled={saving || activating !== null}
          onClick={snapshot}
        >
          {t('skills.version_snapshot', { defaultValue: 'Save current as new version' })}
        </Button>
      </div>
      <p className="text-xs text-[var(--color-text-muted)]">
        {t('skills.version_snapshot_hint', {
          defaultValue: "Snapshots the skill's current prompt and tools as a new active version.",
        })}
      </p>

      {loading ? (
        <p className="text-sm text-[var(--color-text-muted)]">{t('common.loading', { defaultValue: 'Loading' })}…</p>
      ) : versions.length === 0 ? (
        <EmptyState
          icon={<History size={20} aria-hidden="true" />}
          title={t('skills.versions_empty', { defaultValue: 'No versions yet' })}
        />
      ) : (
        <ul className="divide-y divide-[var(--color-border-subtle)] rounded-[var(--radius-md)] border border-[var(--color-border-subtle)]" aria-label={t('skills.tab_versions', { defaultValue: 'Versions' })}>
          {versions.map((v) => {
            const isActive = v.id === activeVersionId || v.is_active;
            return (
              <li key={v.id} className="flex items-center gap-3 bg-[var(--color-bg-surface-1)] px-3 py-2">
                <div className="min-w-0 flex-1">
                  <div className="flex min-w-0 items-center gap-2">
                    <span className="truncate text-sm font-medium text-[var(--color-text-primary)]">{v.version}</span>
                    {isActive && (
                      <span className="inline-flex shrink-0 items-center gap-1 rounded-[var(--radius-sm)] bg-[var(--color-accent-subtle)] px-1.5 py-0.5 text-xs font-medium text-[var(--color-accent-foreground)]">
                        <CheckCircle2 size={11} aria-hidden="true" />
                        {t('skills.version_active', { defaultValue: 'Active' })}
                      </span>
                    )}
                  </div>
                  <div className="truncate text-xs text-[var(--color-text-muted)]">
                    {formatTime(v.created_at)}
                    {v.author ? ` · ${v.author}` : ''}
                    {v.changelog ? ` · ${v.changelog}` : ''}
                  </div>
                </div>
                {!isActive && (
                  <Button
                    variant="outline"
                    size="sm"
                    loading={activating === v.id}
                    disabled={activating !== null || saving}
                    onClick={() => activate(v.id)}
                    aria-label={`${t('skills.version_activate', { defaultValue: 'Activate' })}: ${v.version}`}
                  >
                    {t('skills.version_activate', { defaultValue: 'Activate' })}
                  </Button>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}

function TestCasesTab({ skillId }: { skillId: string }) {
  const { t } = useTranslation();
  const [cases, setCases] = useState<SkillTestCase[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [name, setName] = useState('');
  const [inputParams, setInputParams] = useState('{}');
  const [expectedContains, setExpectedContains] = useState('');
  const [expectedTools, setExpectedTools] = useState('');
  const [timeoutSeconds, setTimeoutSeconds] = useState('30');
  const [adding, setAdding] = useState(false);
  const [runningId, setRunningId] = useState<string | null>(null);
  const [results, setResults] = useState<Record<string, SkillTestRunResult>>({});

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.listSkillTestCases(skillId);
      setCases(Array.isArray(res.test_cases) ? res.test_cases : []);
    } catch (e) {
      setError(e instanceof Error ? e.message : t('common.error', { defaultValue: 'Error' }));
    } finally {
      setLoading(false);
    }
  }, [skillId, t]);

  useEffect(() => {
    void load();
  }, [load]);

  const addCase = async () => {
    let params: Record<string, unknown>;
    try {
      const parsed = inputParams.trim() ? JSON.parse(inputParams) : {};
      if (parsed === null || typeof parsed !== 'object' || Array.isArray(parsed)) throw new Error('not an object');
      params = parsed as Record<string, unknown>;
    } catch {
      setError(t('skills.invalid_json', { defaultValue: 'Input params must be a valid JSON object.' }));
      return;
    }
    const timeout = Number.parseInt(timeoutSeconds, 10);
    setAdding(true);
    setError(null);
    try {
      await api.createSkillTestCase(skillId, {
        name: name.trim(),
        input_params: params,
        expected_output_contains: expectedContains,
        expected_tools: expectedTools.split(',').map((s) => s.trim()).filter(Boolean),
        timeout_seconds: Number.isFinite(timeout) && timeout > 0 ? timeout : 30,
      });
      setName('');
      setInputParams('{}');
      setExpectedContains('');
      setExpectedTools('');
      setTimeoutSeconds('30');
      setShowForm(false);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : t('common.error', { defaultValue: 'Error' }));
    } finally {
      setAdding(false);
    }
  };

  const runCase = async (caseId: string) => {
    setRunningId(caseId);
    setError(null);
    try {
      const result = await api.runSkillTestCase(skillId, caseId);
      setResults((prev) => ({ ...prev, [caseId]: result }));
    } catch (e) {
      setResults((prev) => ({
        ...prev,
        [caseId]: {
          test_id: caseId,
          passed: false,
          error: e instanceof Error ? e.message : t('common.error', { defaultValue: 'Error' }),
        },
      }));
    } finally {
      setRunningId(null);
    }
  };

  return (
    <div className="space-y-3">
      {error && <InlineError message={error} />}

      <div className="flex items-center justify-between gap-2">
        <p className="text-xs text-[var(--color-text-muted)]">
          {t('skills.test_case_hint', {
            defaultValue: 'Static runs render the prompt template and assert the expected substring. No model is involved.',
          })}
        </p>
        <Button
          variant="outline"
          size="sm"
          icon={<Plus size={13} aria-hidden="true" />}
          onClick={() => setShowForm((v) => !v)}
          aria-expanded={showForm}
        >
          {t('skills.test_case_add', { defaultValue: 'Add test case' })}
        </Button>
      </div>

      {showForm && (
        <div className="space-y-2 rounded-[var(--radius-md)] border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-1)] p-3">
          <Input
            size="sm"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder={t('common.name', { defaultValue: 'Name' })}
            aria-label={t('common.name', { defaultValue: 'Name' })}
          />
          <Input
            size="sm"
            value={inputParams}
            onChange={(e) => setInputParams(e.target.value)}
            placeholder={t('skills.test_case_input_params', { defaultValue: 'Input params (JSON object)' })}
            aria-label={t('skills.test_case_input_params', { defaultValue: 'Input params (JSON object)' })}
          />
          <Input
            size="sm"
            value={expectedContains}
            onChange={(e) => setExpectedContains(e.target.value)}
            placeholder={t('skills.test_case_expected_contains', { defaultValue: 'Expected output contains' })}
            aria-label={t('skills.test_case_expected_contains', { defaultValue: 'Expected output contains' })}
          />
          <div className="flex gap-2">
            <div className="flex-1">
              <Input
                size="sm"
                value={expectedTools}
                onChange={(e) => setExpectedTools(e.target.value)}
                placeholder={t('skills.test_case_expected_tools', { defaultValue: 'Expected tools (comma separated)' })}
                aria-label={t('skills.test_case_expected_tools', { defaultValue: 'Expected tools (comma separated)' })}
              />
            </div>
            <div className="w-28">
              <Input
                size="sm"
                type="number"
                min={1}
                value={timeoutSeconds}
                onChange={(e) => setTimeoutSeconds(e.target.value)}
                placeholder={t('skills.test_case_timeout', { defaultValue: 'Timeout (s)' })}
                aria-label={t('skills.test_case_timeout', { defaultValue: 'Timeout (seconds)' })}
              />
            </div>
          </div>
          <div className="flex justify-end gap-2">
            <Button variant="ghost" size="sm" onClick={() => setShowForm(false)} disabled={adding}>
              {t('common.cancel', { defaultValue: 'Cancel' })}
            </Button>
            <Button variant="primary" size="sm" onClick={addCase} loading={adding} disabled={adding || !name.trim()}>
              {t('common.add', { defaultValue: 'Add' })}
            </Button>
          </div>
        </div>
      )}

      {loading ? (
        <p className="text-sm text-[var(--color-text-muted)]">{t('common.loading', { defaultValue: 'Loading' })}…</p>
      ) : cases.length === 0 ? (
        <EmptyState
          icon={<FlaskConical size={20} aria-hidden="true" />}
          title={t('skills.test_cases_empty', { defaultValue: 'No test cases yet' })}
        />
      ) : (
        <ul className="divide-y divide-[var(--color-border-subtle)] rounded-[var(--radius-md)] border border-[var(--color-border-subtle)]" aria-label={t('skills.tab_test_cases', { defaultValue: 'Test cases' })}>
          {cases.map((tc) => {
            const result = results[tc.id];
            return (
              <li key={tc.id} className="space-y-2 bg-[var(--color-bg-surface-1)] px-3 py-2">
                <div className="flex items-center gap-3">
                  <div className="min-w-0 flex-1">
                    <div className="flex min-w-0 items-center gap-2">
                      <span className="truncate text-sm font-medium text-[var(--color-text-primary)]">{tc.name}</span>
                      {result && (
                        <span
                          role="status"
                          className={`inline-flex shrink-0 items-center gap-1 text-xs ${result.passed ? 'text-[var(--color-success)]' : 'text-[var(--color-error)]'}`}
                        >
                          {result.passed
                            ? <CheckCircle2 size={12} aria-hidden="true" />
                            : <XCircle size={12} aria-hidden="true" />}
                          {result.passed
                            ? t('skills.test_case_passed', { defaultValue: 'Passed' })
                            : t('skills.test_case_failed', { defaultValue: 'Failed' })}
                          {typeof result.duration_ms === 'number' && (
                            <span className="tabular-nums text-[var(--color-text-muted)]">{Math.round(result.duration_ms)} ms</span>
                          )}
                        </span>
                      )}
                    </div>
                    <div className="truncate text-xs text-[var(--color-text-muted)]">
                      {formatTime(tc.created_at)} · {tc.timeout_seconds}s
                      {tc.expected_output_contains ? ` · ${tc.expected_output_contains}` : ''}
                    </div>
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    icon={<Play size={12} aria-hidden="true" />}
                    loading={runningId === tc.id}
                    disabled={runningId !== null || adding}
                    onClick={() => runCase(tc.id)}
                    aria-label={`${t('skills.test_case_run', { defaultValue: 'Run' })}: ${tc.name}`}
                  >
                    {t('skills.test_case_run', { defaultValue: 'Run' })}
                  </Button>
                </div>
                {result && (result.output || result.error) && (
                  <pre className="max-h-40 overflow-auto whitespace-pre-wrap rounded-[var(--radius-sm)] border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-2)] p-2 text-xs text-[var(--color-text-secondary)]">
                    {result.error ? result.error : result.output}
                  </pre>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}

/**
 * Skill detail dialog: version history (list / snapshot / activate rollback)
 * and static test cases (list / add / run / result) for one skill.
 */
export function SkillDetailModal({ skill, onClose }: SkillDetailModalProps) {
  const { t } = useTranslation();
  const skillId = skill ? String(skill.id) : null;

  return (
    <Modal
      open={skill !== null}
      onClose={onClose}
      size="xl"
      title={skill?.name ?? ''}
      description={t('skills.detail_subtitle', { defaultValue: 'Version history and test cases' })}
      icon={<History size={20} aria-hidden="true" />}
      data-testid="skill-detail-modal"
    >
      {skillId && (
        <Tabs defaultValue="versions">
          <TabsList>
            <TabsTrigger value="versions" icon={<History size={14} aria-hidden="true" />}>
              {t('skills.tab_versions', { defaultValue: 'Versions' })}
            </TabsTrigger>
            <TabsTrigger value="test-cases" icon={<FlaskConical size={14} aria-hidden="true" />}>
              {t('skills.tab_test_cases', { defaultValue: 'Test cases' })}
            </TabsTrigger>
          </TabsList>
          <TabsContent value="versions">
            <VersionsTab skillId={skillId} />
          </TabsContent>
          <TabsContent value="test-cases">
            <TestCasesTab skillId={skillId} />
          </TabsContent>
        </Tabs>
      )}
    </Modal>
  );
}
