import { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import {
  ScrollText, Search, RefreshCw, AlertCircle, Plus, Copy, Trash2, Pencil,
  Download, Upload, Play, FileJson,
} from 'lucide-react';
import { api, type PromptTemplateOut } from '../api';
import { useTranslation } from '../i18n';
import { includesQuery } from '../lib/search';
import { PageHeader } from '../components/ui/PageHeader';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { EmptyState } from '../components/ui/EmptyState';
import { Card } from '../components/ui/Card';
import { SkeletonList } from '../components/ui/Skeleton';
import { Modal } from '../components/ui/Modal';
import { FormField } from '../components/ui/Field';

const textareaClass =
  'w-full rounded-[var(--radius-md)] border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-1)] px-3 py-2 text-sm text-[var(--color-text-primary)] placeholder:text-[var(--color-text-muted)] focus:border-[var(--color-accent)] focus:outline-none';

function parseVars(text: string): Record<string, string> {
  const out: Record<string, string> = {};
  for (const line of text.split('\n')) {
    const idx = line.indexOf('=');
    if (idx <= 0) continue;
    const key = line.slice(0, idx).trim();
    if (key) out[key] = line.slice(idx + 1).trim();
  }
  return out;
}

function varsToText(vars: Record<string, string>): string {
  return Object.entries(vars || {}).map(([k, v]) => `${k}=${v}`).join('\n');
}

function extractVarNames(content: string): string[] {
  const names = new Set<string>();
  for (const m of content.matchAll(/\{\{\s*([\w.-]+)\s*\}\}/g)) {
    const name = m[1];
    if (name) names.add(name);
  }
  return [...names];
}

function downloadJson(filename: string, json: string) {
  const blob = new Blob([json], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

interface EditorState {
  id: string | null;
  name: string;
  description: string;
  content: string;
  variablesText: string;
  tagsText: string;
  modelId: string;
}

const emptyEditor: EditorState = {
  id: null, name: '', description: '', content: '', variablesText: '', tagsText: '', modelId: '',
};

export function PromptTemplatesPage() {
  const { t } = useTranslation();
  const [templates, setTemplates] = useState<PromptTemplateOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedTag, setSelectedTag] = useState('');
  const [scope, setScope] = useState<'all' | 'builtin' | 'custom'>('all');
  const [busy, setBusy] = useState<string | null>(null);

  const [editor, setEditor] = useState<EditorState | null>(null);
  const [saving, setSaving] = useState(false);
  const [editorError, setEditorError] = useState<string | null>(null);

  const [renderTarget, setRenderTarget] = useState<PromptTemplateOut | null>(null);
  const [renderVars, setRenderVars] = useState<Record<string, string>>({});
  const [rendered, setRendered] = useState<string | null>(null);
  const [rendering, setRendering] = useState(false);
  const [renderError, setRenderError] = useState<string | null>(null);

  const [deleteTarget, setDeleteTarget] = useState<PromptTemplateOut | null>(null);
  const [deleting, setDeleting] = useState(false);

  const fileInputRef = useRef<HTMLInputElement>(null);

  const fetchTemplates = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.listPromptTemplates();
      setTemplates(Array.isArray(res) ? res : []);
    } catch (e: any) {
      setError(e.message || t('common.error'));
    }
    setLoading(false);
  }, [t]);

  useEffect(() => { fetchTemplates(); }, [fetchTemplates]);

  const tags = useMemo(() => [...new Set(templates.flatMap(tpl => tpl.tags || []))].sort(), [templates]);

  const filtered = templates.filter(tpl =>
    includesQuery([tpl.name, tpl.description, tpl.content, ...(tpl.tags || [])], searchQuery) &&
    (!selectedTag || (tpl.tags || []).includes(selectedTag)) &&
    (scope === 'all' || (scope === 'builtin' ? tpl.is_builtin : !tpl.is_builtin))
  );

  const openCreate = () => { setEditorError(null); setEditor({ ...emptyEditor }); };
  const openEdit = (tpl: PromptTemplateOut) => {
    setEditorError(null);
    setEditor({
      id: tpl.id,
      name: tpl.name,
      description: tpl.description || '',
      content: tpl.content,
      variablesText: varsToText(tpl.variables || {}),
      tagsText: (tpl.tags || []).join(', '),
      modelId: tpl.model_id || '',
    });
  };

  const saveEditor = async () => {
    if (!editor) return;
    setSaving(true);
    setEditorError(null);
    const payload = {
      name: editor.name.trim(),
      content: editor.content,
      description: editor.description,
      variables: parseVars(editor.variablesText),
      tags: editor.tagsText.split(',').map(s => s.trim()).filter(Boolean),
      model_id: editor.modelId.trim() || null,
    };
    try {
      if (editor.id) {
        await api.updatePromptTemplate(editor.id, payload);
      } else {
        await api.createPromptTemplate(payload);
      }
      setEditor(null);
      await fetchTemplates();
    } catch (e: any) {
      setEditorError(e.message || t('common.error'));
    } finally {
      setSaving(false);
    }
  };

  const duplicateTemplate = async (tpl: PromptTemplateOut) => {
    setBusy(`dup-${tpl.id}`);
    setError(null);
    try {
      await api.duplicatePromptTemplate(tpl.id);
      await fetchTemplates();
    } catch (e: any) {
      setError(e.message || t('common.error'));
    } finally {
      setBusy(null);
    }
  };

  const confirmDelete = async () => {
    if (!deleteTarget) return;
    setDeleting(true);
    try {
      await api.deletePromptTemplate(deleteTarget.id);
      setDeleteTarget(null);
      await fetchTemplates();
    } catch (e: any) {
      setError(e.message || t('common.error'));
      setDeleteTarget(null);
    } finally {
      setDeleting(false);
    }
  };

  const exportOne = async (tpl: PromptTemplateOut) => {
    setBusy(`exp-${tpl.id}`);
    setError(null);
    try {
      const res = await api.exportPromptTemplate(tpl.id);
      downloadJson(`prompt-template-${tpl.name || tpl.id}.json`, res.json);
    } catch (e: any) {
      setError(e.message || t('common.error'));
    } finally {
      setBusy(null);
    }
  };

  const exportAll = async () => {
    setBusy('export-all');
    setError(null);
    try {
      const res = await api.exportAllPromptTemplates();
      downloadJson('prompt-templates.json', res.json);
    } catch (e: any) {
      setError(e.message || t('common.error'));
    } finally {
      setBusy(null);
    }
  };

  const onImportFile = async (file: File) => {
    setError(null);
    try {
      const text = await file.text();
      const parsed = JSON.parse(text);
      if (Array.isArray(parsed)) {
        await api.importPromptTemplatesBulk(text);
      } else {
        await api.importPromptTemplate(text);
      }
      await fetchTemplates();
    } catch (e: any) {
      setError(e.message || t('common.error'));
    }
  };

  const openRender = (tpl: PromptTemplateOut) => {
    setRenderTarget(tpl);
    setRenderVars({ ...(tpl.variables || {}) });
    setRendered(null);
    setRenderError(null);
  };

  const runRender = async () => {
    if (!renderTarget) return;
    setRendering(true);
    setRenderError(null);
    try {
      const res = await api.renderPromptTemplate(renderTarget.id, renderVars);
      setRendered(res.rendered);
    } catch (e: any) {
      setRenderError(e.message || t('common.error'));
    } finally {
      setRendering(false);
    }
  };

  const hasFilters = Boolean(searchQuery || selectedTag || scope !== 'all');
  const showList = !loading && !error;
  const renderVarNames = renderTarget
    ? [...new Set([...extractVarNames(renderTarget.content), ...Object.keys(renderTarget.variables || {})])]
    : [];

  return (
    <div className="page-scroll page-transition">
      <div className="page-container">
        <PageHeader
          title={t('navigation.prompt_templates', { defaultValue: 'Prompt Templates' })}
          icon={<ScrollText size={20} aria-hidden="true" />}
          className="border-b border-[var(--color-border-subtle)] pb-[var(--space-4)] [&_h1]:text-[length:var(--text-base)] [&_h1]:md:text-[length:var(--text-base)] [&_p]:text-[var(--color-text-muted)]"
          actions={
            <div className="flex items-center gap-2">
              <Button variant="outline" size="sm" icon={<RefreshCw size={14} />} disabled={loading || busy !== null} onClick={fetchTemplates}>
                {t('common.refresh')}
              </Button>
              <Button variant="outline" size="sm" icon={<Upload size={14} />} disabled={busy !== null} onClick={() => fileInputRef.current?.click()}>
                {t('prompt_templates.import', { defaultValue: 'Import' })}
              </Button>
              <Button variant="outline" size="sm" icon={<Download size={14} />} disabled={busy !== null} loading={busy === 'export-all'} onClick={exportAll}>
                {t('prompt_templates.export_all', { defaultValue: 'Export all' })}
              </Button>
              <Button size="sm" icon={<Plus size={14} />} onClick={openCreate}>
                {t('prompt_templates.new', { defaultValue: 'New template' })}
              </Button>
            </div>
          }
        />

        <input
          ref={fileInputRef}
          type="file"
          accept="application/json,.json"
          className="hidden"
          aria-label={t('prompt_templates.import', { defaultValue: 'Import' })}
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) onImportFile(file);
            e.target.value = '';
          }}
        />

        <div className="space-y-4">
          {showList && templates.length > 0 && (
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
                {(['all', 'builtin', 'custom'] as const).map(s => (
                  <button
                    type="button"
                    key={s}
                    onClick={() => setScope(s)}
                    aria-pressed={scope === s}
                    className={`rounded-[var(--radius-md)] border px-2.5 py-1 text-xs font-medium transition-colors ${
                      scope === s
                        ? 'border-[var(--color-border-strong)] bg-[var(--color-bg-surface-3)] text-[var(--color-text-primary)]'
                        : 'border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-2)] text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]'
                    }`}
                  >
                    {s === 'all' ? t('common.all') : s === 'builtin'
                      ? t('prompt_templates.builtin', { defaultValue: 'Built-in' })
                      : t('prompt_templates.custom', { defaultValue: 'Custom' })}
                  </button>
                ))}
                <span className="mx-1 h-4 w-px bg-[var(--color-border-subtle)]" aria-hidden="true" />
                {tags.map(tag => (
                  <button
                    type="button"
                    key={tag}
                    onClick={() => setSelectedTag(selectedTag === tag ? '' : tag)}
                    aria-pressed={selectedTag === tag}
                    className={`rounded-[var(--radius-md)] border px-2.5 py-1 text-xs font-medium transition-colors ${
                      selectedTag === tag
                        ? 'border-[var(--color-border-strong)] bg-[var(--color-bg-surface-3)] text-[var(--color-text-primary)]'
                        : 'border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-2)] text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]'
                    }`}
                  >
                    {tag}
                  </button>
                ))}
              </div>
              <span className="shrink-0 text-xs tabular-nums text-[var(--color-text-muted)]" aria-live="polite">
                {filtered.length} / {templates.length}
              </span>
            </div>
          )}

          {error && (
            <div role="alert" className="flex items-center gap-3 rounded-[var(--radius-md)] border border-[var(--color-error)]/30 bg-[var(--color-error-subtle)] p-3">
              <AlertCircle size={16} aria-hidden="true" className="shrink-0 text-[var(--color-error)]" />
              <p className="flex-1 text-sm text-[var(--color-error)]">{error}</p>
              <Button variant="ghost" size="sm" icon={<RefreshCw size={14} />} onClick={fetchTemplates}>
                {t('common.retry')}
              </Button>
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
                icon={hasFilters ? <Search size={20} aria-hidden="true" /> : <ScrollText size={20} aria-hidden="true" />}
                title={hasFilters ? t('common.no_results') : t('common.no_data')}
                action={hasFilters ? (
                  <Button variant="outline" size="sm" onClick={() => { setSearchQuery(''); setSelectedTag(''); setScope('all'); }}>
                    {t('common.clear')}
                  </Button>
                ) : (
                  <Button size="sm" icon={<Plus size={14} />} onClick={openCreate}>
                    {t('prompt_templates.new', { defaultValue: 'New template' })}
                  </Button>
                )}
              />
            </Card>
          )}

          {showList && filtered.length > 0 && (
            <Card padding="none" className="overflow-hidden">
              <ul className="divide-y divide-[var(--color-border-subtle)]" aria-label={t('navigation.prompt_templates', { defaultValue: 'Prompt Templates' })}>
                {filtered.map(tpl => (
                  <li key={tpl.id} className="flex items-center gap-3 bg-[var(--color-bg-surface-1)] px-3 py-2 md:px-4">
                    <ScrollText size={16} aria-hidden="true" className="shrink-0 text-[var(--color-text-muted)]" />
                    <div className="min-w-0 flex-1">
                      <div className="flex min-w-0 items-center gap-2">
                        <span className="truncate text-sm font-medium text-[var(--color-text-primary)]">{tpl.name}</span>
                        {tpl.is_builtin && (
                          <span className="shrink-0 rounded-[var(--radius-sm)] border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-2)] px-1.5 py-0.5 text-[10px] font-medium text-[var(--color-text-muted)]">
                            {t('prompt_templates.builtin', { defaultValue: 'Built-in' })}
                          </span>
                        )}
                        {(tpl.tags || []).map(tag => (
                          <span key={tag} className="hidden shrink-0 rounded-[var(--radius-sm)] bg-[var(--color-bg-surface-2)] px-1.5 py-0.5 text-[10px] text-[var(--color-text-muted)] md:inline">
                            {tag}
                          </span>
                        ))}
                      </div>
                      {tpl.description && (
                        <p className="truncate text-xs text-[var(--color-text-muted)]">{tpl.description}</p>
                      )}
                    </div>
                    {tpl.model_id && (
                      <span className="hidden shrink-0 text-xs tabular-nums text-[var(--color-text-muted)] lg:inline">{tpl.model_id}</span>
                    )}
                    <div className="flex shrink-0 items-center gap-1">
                      <Button variant="ghost" size="sm" icon={<Play size={13} aria-hidden="true" />} aria-label={`${t('prompt_templates.render', { defaultValue: 'Render' })}: ${tpl.name}`} onClick={() => openRender(tpl)}>
                        {t('prompt_templates.render', { defaultValue: 'Render' })}
                      </Button>
                      <Button variant="ghost" size="sm" icon={<Copy size={13} aria-hidden="true" />} aria-label={`${t('prompt_templates.duplicate', { defaultValue: 'Duplicate' })}: ${tpl.name}`} loading={busy === `dup-${tpl.id}`} disabled={busy !== null} onClick={() => duplicateTemplate(tpl)} />
                      <Button variant="ghost" size="sm" icon={<FileJson size={13} aria-hidden="true" />} aria-label={`${t('common.export')}: ${tpl.name}`} loading={busy === `exp-${tpl.id}`} disabled={busy !== null} onClick={() => exportOne(tpl)} />
                      {!tpl.is_builtin && (
                        <>
                          <Button variant="ghost" size="sm" icon={<Pencil size={13} aria-hidden="true" />} aria-label={`${t('common.edit')}: ${tpl.name}`} onClick={() => openEdit(tpl)} />
                          <Button variant="ghost" size="sm" icon={<Trash2 size={13} aria-hidden="true" />} aria-label={`${t('common.delete')}: ${tpl.name}`} onClick={() => setDeleteTarget(tpl)} />
                        </>
                      )}
                    </div>
                  </li>
                ))}
              </ul>
            </Card>
          )}
        </div>
      </div>

      <Modal
        open={editor !== null}
        onClose={() => setEditor(null)}
        size="lg"
        title={editor?.id
          ? t('prompt_templates.edit', { defaultValue: 'Edit template' })
          : t('prompt_templates.new', { defaultValue: 'New template' })}
        footer={
          <div className="flex justify-end gap-2">
            <Button variant="outline" size="sm" onClick={() => setEditor(null)}>{t('common.cancel')}</Button>
            <Button size="sm" loading={saving} disabled={!editor?.name.trim() || !editor?.content.trim()} onClick={saveEditor}>
              {t('common.save')}
            </Button>
          </div>
        }
      >
        {editor && (
          <div className="space-y-4">
            {editorError && (
              <div role="alert" className="flex items-center gap-2 rounded-[var(--radius-md)] border border-[var(--color-error)]/30 bg-[var(--color-error-subtle)] p-3 text-sm text-[var(--color-error)]">
                <AlertCircle size={14} aria-hidden="true" className="shrink-0" />{editorError}
              </div>
            )}
            <FormField label={t('common.name')} required>
              <Input size="sm" value={editor.name} onChange={(e) => setEditor({ ...editor, name: e.target.value })} />
            </FormField>
            <FormField label={t('common.description')}>
              <Input size="sm" value={editor.description} onChange={(e) => setEditor({ ...editor, description: e.target.value })} />
            </FormField>
            <FormField label={t('prompt_templates.content', { defaultValue: 'Content' })} required hint={t('prompt_templates.content_hint', { defaultValue: 'Use {{variable}} placeholders for substitution.' })}>
              <textarea
                className={textareaClass}
                rows={8}
                value={editor.content}
                onChange={(e) => setEditor({ ...editor, content: e.target.value })}
              />
            </FormField>
            <FormField label={t('prompt_templates.variables', { defaultValue: 'Variables' })} hint={t('prompt_templates.variables_hint', { defaultValue: 'One per line: name=default value' })}>
              <textarea
                className={`${textareaClass} font-mono`}
                rows={3}
                value={editor.variablesText}
                onChange={(e) => setEditor({ ...editor, variablesText: e.target.value })}
              />
            </FormField>
            <FormField label={t('prompt_templates.tags', { defaultValue: 'Tags' })} hint={t('prompt_templates.tags_hint', { defaultValue: 'Comma separated' })}>
              <Input size="sm" value={editor.tagsText} onChange={(e) => setEditor({ ...editor, tagsText: e.target.value })} />
            </FormField>
            <FormField label={t('prompt_templates.model_id', { defaultValue: 'Model ID' })}>
              <Input size="sm" value={editor.modelId} onChange={(e) => setEditor({ ...editor, modelId: e.target.value })} />
            </FormField>
          </div>
        )}
      </Modal>

      <Modal
        open={renderTarget !== null}
        onClose={() => setRenderTarget(null)}
        size="lg"
        title={t('prompt_templates.render_title', { defaultValue: 'Render template' })}
        description={renderTarget?.name}
        footer={
          <div className="flex justify-end gap-2">
            <Button variant="outline" size="sm" onClick={() => setRenderTarget(null)}>{t('common.close')}</Button>
            <Button size="sm" icon={<Play size={13} />} loading={rendering} onClick={runRender}>
              {t('prompt_templates.render', { defaultValue: 'Render' })}
            </Button>
          </div>
        }
      >
        {renderTarget && (
          <div className="space-y-4">
            {renderVarNames.length > 0 ? (
              <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                {renderVarNames.map(name => (
                  <FormField key={name} label={name}>
                    <Input
                      size="sm"
                      value={renderVars[name] ?? ''}
                      onChange={(e) => setRenderVars({ ...renderVars, [name]: e.target.value })}
                    />
                  </FormField>
                ))}
              </div>
            ) : (
              <p className="text-sm text-[var(--color-text-muted)]">
                {t('prompt_templates.no_variables', { defaultValue: 'This template has no variables.' })}
              </p>
            )}
            {renderError && (
              <div role="alert" className="flex items-center gap-2 rounded-[var(--radius-md)] border border-[var(--color-error)]/30 bg-[var(--color-error-subtle)] p-3 text-sm text-[var(--color-error)]">
                <AlertCircle size={14} aria-hidden="true" className="shrink-0" />{renderError}
              </div>
            )}
            {rendered !== null && (
              <div>
                <p className="mb-1 text-xs font-medium text-[var(--color-text-muted)]">
                  {t('prompt_templates.rendered_output', { defaultValue: 'Rendered output' })}
                </p>
                <pre className="max-h-80 overflow-auto whitespace-pre-wrap rounded-[var(--radius-md)] border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-2)] p-3 text-sm text-[var(--color-text-primary)]">
                  {rendered}
                </pre>
              </div>
            )}
          </div>
        )}
      </Modal>

      <Modal
        open={deleteTarget !== null}
        onClose={() => setDeleteTarget(null)}
        size="sm"
        title={t('common.confirm_delete')}
        footer={
          <div className="flex justify-end gap-2">
            <Button variant="outline" size="sm" onClick={() => setDeleteTarget(null)}>{t('common.cancel')}</Button>
            <Button size="sm" loading={deleting} onClick={confirmDelete}>{t('common.delete')}</Button>
          </div>
        }
      >
        <p className="text-sm text-[var(--color-text-secondary)]">
          {t('prompt_templates.delete_confirm', { defaultValue: 'Delete template "{{name}}"? This cannot be undone.', name: deleteTarget?.name ?? '' })}
        </p>
      </Modal>
    </div>
  );
}

export default PromptTemplatesPage;
