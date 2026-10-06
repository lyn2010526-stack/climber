import { useCallback, useEffect, useState } from 'react';
import { Plug, RefreshCw, QrCode, Play, Search, Plus, Bot } from 'lucide-react';
import {
  api,
  type DomesticIntegrationStatusOut,
  type QQBotQrOut,
  type Mem0StatusOut,
} from '../api';
import { PageHeader } from '../components/ui/PageHeader';
import { Card, CardContent } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import { Input } from '../components/ui/Input';
import { FormField } from '../components/ui/Field';
import { SkeletonList } from '../components/ui/Skeleton';
import { useI18n } from '../i18n';

function JsonBlock({ value }: { value: unknown }) {
  if (value === null || value === undefined) return null;
  return (
    <pre className="mt-3 max-h-72 overflow-auto rounded-[var(--radius-md)] bg-[var(--color-bg-surface-2)] p-3 text-xs text-[var(--color-text-secondary)] whitespace-pre-wrap break-all">
      {JSON.stringify(value, null, 2)}
    </pre>
  );
}

function SectionError({ message }: { message: string | null }) {
  if (!message) return null;
  return <p role="alert" className="mt-2 text-xs text-[var(--color-error)]">{message}</p>;
}

function parseJsonInput(raw: string): Record<string, unknown> {
  const trimmed = raw.trim();
  if (!trimmed) return {};
  const parsed: unknown = JSON.parse(trimmed);
  if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
    throw new Error('JSON object expected');
  }
  return parsed as Record<string, unknown>;
}

function QQBotCard() {
  const { t } = useI18n();
  const [status, setStatus] = useState<DomesticIntegrationStatusOut | null>(null);
  const [statusError, setStatusError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [qr, setQr] = useState<QQBotQrOut | null>(null);
  const [qrBusy, setQrBusy] = useState(false);
  const [qrError, setQrError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setStatusError(null);
    try {
      setStatus(await api.getDomesticIntegrationStatus());
    } catch (e) {
      setStatusError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  const handleQr = async () => {
    setQrBusy(true);
    setQrError(null);
    try {
      setQr(await api.createQQBotQr());
    } catch (e) {
      setQrError(e instanceof Error ? e.message : String(e));
    } finally {
      setQrBusy(false);
    }
  };

  const webhookUrl = `${window.location.origin}/api/v1/integrations/domestic/qqbot/webhook`;
  const provider = status?.provider;

  return (
    <Card variant="default" padding="none">
      <div className="px-4 py-4 border-b border-[var(--color-border-subtle)] flex items-center justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold text-[var(--color-text-primary)]">{t('integrations_page.qqbot.title', { defaultValue: 'QQBot' })}</h3>
          <p className="text-xs text-[var(--color-text-muted)] mt-1">{t('integrations_page.qqbot.desc', { defaultValue: 'Webhook endpoint and binding QR token for the domestic QQBot adapter.' })}</p>
        </div>
        {provider && (
          <Badge variant={provider.enabled ? 'success' : 'secondary'}>
            {provider.enabled
              ? t('integrations_page.enabled', { defaultValue: 'Enabled' })
              : t('integrations_page.disabled', { defaultValue: 'Disabled' })}
          </Badge>
        )}
      </div>
      <CardContent className="p-4 space-y-4">
        {loading ? (
          <SkeletonList count={1} />
        ) : statusError ? (
          <>
            <SectionError message={statusError} />
            <Button size="sm" variant="outline" onClick={() => void load()} icon={<RefreshCw size={14} />}>{t('common.retry')}</Button>
          </>
        ) : (
          <>
            {provider && (
              <div className="text-xs text-[var(--color-text-muted)] space-y-1">
                <div>{t('integrations_page.qqbot.mode', { defaultValue: 'Mode' })}: <span className="text-[var(--color-text-secondary)]">{provider.mode}</span></div>
                {provider.reason && <div>{t('integrations_page.qqbot.reason', { defaultValue: 'Reason' })}: <span className="text-[var(--color-text-secondary)]">{provider.reason}</span></div>}
              </div>
            )}
            <FormField label={t('integrations_page.qqbot.webhook_url', { defaultValue: 'Webhook URL' })}>
              <Input readOnly value={webhookUrl} aria-label={t('integrations_page.qqbot.webhook_url', { defaultValue: 'Webhook URL' })} onFocus={(e) => e.target.select()} />
            </FormField>
            <div>
              <Button size="sm" onClick={() => void handleQr()} loading={qrBusy} icon={<QrCode size={14} />}>
                {t('integrations_page.qqbot.get_qr', { defaultValue: 'Get binding QR token' })}
              </Button>
              <SectionError message={qrError} />
              {qr && (
                <div className="mt-3 text-xs space-y-1">
                  {qr.status !== 'ok' ? (
                    <p className="text-[var(--color-text-muted)]">
                      {t('integrations_page.qqbot.qr_disabled', { defaultValue: 'Provider disabled' })}
                      {qr.reason ? `: ${qr.reason}` : ''}
                    </p>
                  ) : (
                    <>
                      <div className="text-[var(--color-text-secondary)] break-all">
                        {t('integrations_page.qqbot.token', { defaultValue: 'Token' })}: <code className="font-mono">{qr.token}</code>
                      </div>
                      {qr.expires_at && (
                        <div className="text-[var(--color-text-muted)]">
                          {t('integrations_page.qqbot.expires_at', { defaultValue: 'Expires at' })}: {qr.expires_at}
                        </div>
                      )}
                    </>
                  )}
                </div>
              )}
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}

function LangGraphCard() {
  const { t } = useI18n();
  const [graphs, setGraphs] = useState<string[]>([]);
  const [graphsStatus, setGraphsStatus] = useState<string | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [graphName, setGraphName] = useState('');
  const [inputs, setInputs] = useState('{}');
  const [config, setConfig] = useState('{}');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<unknown>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setLoadError(null);
    try {
      const out = await api.listLangGraphGraphs();
      setGraphs(out.graphs);
      setGraphsStatus(out.status);
      if (out.graphs.length > 0) setGraphName(prev => prev || (out.graphs[0] ?? ''));
    } catch (e) {
      setLoadError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  const handleInvoke = async () => {
    if (!graphName.trim() || busy) return;
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      const out = await api.invokeLangGraph(graphName.trim(), {
        inputs: parseJsonInput(inputs),
        config: parseJsonInput(config),
      });
      setResult(out.result);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Card variant="default" padding="none">
      <div className="px-4 py-4 border-b border-[var(--color-border-subtle)] flex items-center justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold text-[var(--color-text-primary)]">LangGraph</h3>
          <p className="text-xs text-[var(--color-text-muted)] mt-1">{t('integrations_page.langgraph.desc', { defaultValue: 'List registered graphs and invoke one with JSON inputs. Invocation requires admin.' })}</p>
        </div>
        {graphsStatus && (
          <Badge variant={graphsStatus === 'ok' ? 'success' : 'warning'}>{graphsStatus}</Badge>
        )}
      </div>
      <CardContent className="p-4 space-y-4">
        {loading ? (
          <SkeletonList count={1} />
        ) : loadError ? (
          <>
            <SectionError message={loadError} />
            <Button size="sm" variant="outline" onClick={() => void load()} icon={<RefreshCw size={14} />}>{t('common.retry')}</Button>
          </>
        ) : (
          <>
            <FormField label={t('integrations_page.langgraph.graph', { defaultValue: 'Graph' })}>
              {graphs.length > 0 ? (
                <select
                  value={graphName}
                  onChange={(e) => setGraphName(e.target.value)}
                  aria-label={t('integrations_page.langgraph.graph', { defaultValue: 'Graph' })}
                  className="w-full rounded-[var(--radius-md)] border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-1)] px-3 py-2 text-sm text-[var(--color-text-primary)]"
                >
                  {graphs.map(name => <option key={name} value={name}>{name}</option>)}
                </select>
              ) : (
                <Input value={graphName} onChange={(e) => setGraphName(e.target.value)} placeholder={t('integrations_page.langgraph.graph_placeholder', { defaultValue: 'Graph name' })} />
              )}
            </FormField>
            <FormField label={t('integrations_page.langgraph.inputs', { defaultValue: 'Inputs (JSON object)' })}>
              <textarea
                value={inputs}
                onChange={(e) => setInputs(e.target.value)}
                rows={3}
                aria-label={t('integrations_page.langgraph.inputs', { defaultValue: 'Inputs (JSON object)' })}
                className="w-full rounded-[var(--radius-md)] border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-1)] px-3 py-2 font-mono text-xs text-[var(--color-text-primary)]"
              />
            </FormField>
            <FormField label={t('integrations_page.langgraph.config', { defaultValue: 'Config (JSON object)' })}>
              <textarea
                value={config}
                onChange={(e) => setConfig(e.target.value)}
                rows={2}
                aria-label={t('integrations_page.langgraph.config', { defaultValue: 'Config (JSON object)' })}
                className="w-full rounded-[var(--radius-md)] border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-1)] px-3 py-2 font-mono text-xs text-[var(--color-text-primary)]"
              />
            </FormField>
            <Button size="sm" onClick={() => void handleInvoke()} loading={busy} disabled={!graphName.trim()} icon={<Play size={14} />}>
              {t('integrations_page.langgraph.invoke', { defaultValue: 'Invoke' })}
            </Button>
            <SectionError message={error} />
            <JsonBlock value={result} />
          </>
        )}
      </CardContent>
    </Card>
  );
}

function Mem0Card() {
  const { t } = useI18n();
  const [status, setStatus] = useState<Mem0StatusOut | null>(null);
  const [statusError, setStatusError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const [query, setQuery] = useState('');
  const [limit, setLimit] = useState('10');
  const [searchBusy, setSearchBusy] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);
  const [searchResults, setSearchResults] = useState<unknown[] | null>(null);

  const [content, setContent] = useState('');
  const [metadata, setMetadata] = useState('{}');
  const [addBusy, setAddBusy] = useState(false);
  const [addError, setAddError] = useState<string | null>(null);
  const [addedId, setAddedId] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setStatusError(null);
    try {
      setStatus(await api.getMem0Status());
    } catch (e) {
      setStatusError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  const handleSearch = async () => {
    if (!query.trim() || searchBusy) return;
    setSearchBusy(true);
    setSearchError(null);
    setSearchResults(null);
    try {
      const parsedLimit = Number.parseInt(limit, 10);
      const out = await api.mem0Search({ query: query.trim(), limit: Number.isFinite(parsedLimit) ? parsedLimit : 10 });
      setSearchResults(out.results);
    } catch (e) {
      setSearchError(e instanceof Error ? e.message : String(e));
    } finally {
      setSearchBusy(false);
    }
  };

  const handleAdd = async () => {
    if (!content.trim() || addBusy) return;
    setAddBusy(true);
    setAddError(null);
    setAddedId(null);
    try {
      const out = await api.mem0Add({ content: content.trim(), metadata: parseJsonInput(metadata) });
      setAddedId(out.memory_id);
      setContent('');
    } catch (e) {
      setAddError(e instanceof Error ? e.message : String(e));
    } finally {
      setAddBusy(false);
    }
  };

  return (
    <Card variant="default" padding="none">
      <div className="px-4 py-4 border-b border-[var(--color-border-subtle)] flex items-center justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold text-[var(--color-text-primary)]">Mem0</h3>
          <p className="text-xs text-[var(--color-text-muted)] mt-1">{t('integrations_page.mem0.desc', { defaultValue: 'Search and write memories under your own namespace.' })}</p>
        </div>
        {status && (
          <Badge variant={status.available ? 'success' : 'warning'}>
            {status.available
              ? t('integrations_page.mem0.available', { defaultValue: 'Available' })
              : t('integrations_page.mem0.unavailable', { defaultValue: 'Unavailable' })}
          </Badge>
        )}
      </div>
      <CardContent className="p-4 space-y-5">
        {loading ? (
          <SkeletonList count={1} />
        ) : statusError ? (
          <>
            <SectionError message={statusError} />
            <Button size="sm" variant="outline" onClick={() => void load()} icon={<RefreshCw size={14} />}>{t('common.retry')}</Button>
          </>
        ) : (
          <>
            <div className="space-y-3">
              <h4 className="text-xs font-semibold text-[var(--color-text-secondary)]">{t('integrations_page.mem0.search_title', { defaultValue: 'Search memories' })}</h4>
              <div className="flex flex-col sm:flex-row gap-2">
                <Input value={query} onChange={(e) => setQuery(e.target.value)} placeholder={t('integrations_page.mem0.query_placeholder', { defaultValue: 'Query' })} aria-label={t('integrations_page.mem0.query_placeholder', { defaultValue: 'Query' })} className="flex-1" />
                <Input value={limit} onChange={(e) => setLimit(e.target.value)} inputMode="numeric" aria-label={t('integrations_page.mem0.limit', { defaultValue: 'Limit' })} className="sm:w-24" />
                <Button size="sm" onClick={() => void handleSearch()} loading={searchBusy} disabled={!query.trim()} icon={<Search size={14} />}>
                  {t('common.search', { defaultValue: 'Search' })}
                </Button>
              </div>
              <SectionError message={searchError} />
              {searchResults && (
                searchResults.length === 0 ? (
                  <p className="text-xs text-[var(--color-text-muted)]">{t('integrations_page.mem0.no_results', { defaultValue: 'No results.' })}</p>
                ) : (
                  <JsonBlock value={searchResults} />
                )
              )}
            </div>
            <div className="space-y-3 border-t border-[var(--color-border-subtle)] pt-4">
              <h4 className="text-xs font-semibold text-[var(--color-text-secondary)]">{t('integrations_page.mem0.add_title', { defaultValue: 'Add a memory' })}</h4>
              <FormField label={t('integrations_page.mem0.content', { defaultValue: 'Content' })}>
                <textarea
                  value={content}
                  onChange={(e) => setContent(e.target.value)}
                  rows={3}
                  aria-label={t('integrations_page.mem0.content', { defaultValue: 'Content' })}
                  className="w-full rounded-[var(--radius-md)] border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-1)] px-3 py-2 text-sm text-[var(--color-text-primary)]"
                />
              </FormField>
              <FormField label={t('integrations_page.mem0.metadata', { defaultValue: 'Metadata (JSON object)' })}>
                <textarea
                  value={metadata}
                  onChange={(e) => setMetadata(e.target.value)}
                  rows={2}
                  aria-label={t('integrations_page.mem0.metadata', { defaultValue: 'Metadata (JSON object)' })}
                  className="w-full rounded-[var(--radius-md)] border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-1)] px-3 py-2 font-mono text-xs text-[var(--color-text-primary)]"
                />
              </FormField>
              <Button size="sm" onClick={() => void handleAdd()} loading={addBusy} disabled={!content.trim()} icon={<Plus size={14} />}>
                {t('integrations_page.mem0.add', { defaultValue: 'Add memory' })}
              </Button>
              <SectionError message={addError} />
              {addedId && (
                <p className="text-xs text-[var(--color-success)]">
                  {t('integrations_page.mem0.added', { defaultValue: 'Memory added' })}: <code className="font-mono">{addedId}</code>
                </p>
              )}
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}

function AgentRunCard() {
  const { t } = useI18n();
  const [prompt, setPrompt] = useState('');
  const [systemPrompt, setSystemPrompt] = useState('');
  const [model, setModel] = useState('gpt-4');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<{ content: string; confidence: number | null; tool_calls: unknown[]; metadata: Record<string, unknown> } | null>(null);

  const handleRun = async () => {
    if (!prompt.trim() || busy) return;
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      const out = await api.runIntegrationAgent({
        prompt: prompt.trim(),
        ...(systemPrompt.trim() ? { system_prompt: systemPrompt.trim() } : {}),
        ...(model.trim() ? { model: model.trim() } : {}),
      });
      setResult(out);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Card variant="default" padding="none">
      <div className="px-4 py-4 border-b border-[var(--color-border-subtle)]">
        <h3 className="text-sm font-semibold text-[var(--color-text-primary)]">{t('integrations_page.agent_run.title', { defaultValue: 'Agent Run' })}</h3>
        <p className="text-xs text-[var(--color-text-muted)] mt-1">{t('integrations_page.agent_run.desc', { defaultValue: 'Run a Pydantic-AI agent with a prompt. Requires admin.' })}</p>
      </div>
      <CardContent className="p-4 space-y-3">
        <FormField label={t('integrations_page.agent_run.prompt', { defaultValue: 'Prompt' })} required>
          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            rows={3}
            aria-label={t('integrations_page.agent_run.prompt', { defaultValue: 'Prompt' })}
            className="w-full rounded-[var(--radius-md)] border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-1)] px-3 py-2 text-sm text-[var(--color-text-primary)]"
          />
        </FormField>
        <FormField label={t('integrations_page.agent_run.system_prompt', { defaultValue: 'System prompt (optional)' })}>
          <textarea
            value={systemPrompt}
            onChange={(e) => setSystemPrompt(e.target.value)}
            rows={2}
            aria-label={t('integrations_page.agent_run.system_prompt', { defaultValue: 'System prompt (optional)' })}
            className="w-full rounded-[var(--radius-md)] border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-1)] px-3 py-2 text-sm text-[var(--color-text-primary)]"
          />
        </FormField>
        <FormField label={t('integrations_page.agent_run.model', { defaultValue: 'Model' })}>
          <Input value={model} onChange={(e) => setModel(e.target.value)} aria-label={t('integrations_page.agent_run.model', { defaultValue: 'Model' })} />
        </FormField>
        <Button size="sm" onClick={() => void handleRun()} loading={busy} disabled={!prompt.trim()} icon={<Bot size={14} />}>
          {t('integrations_page.agent_run.run', { defaultValue: 'Run agent' })}
        </Button>
        <SectionError message={error} />
        {result && (
          <div className="mt-2 space-y-2">
            <div className="rounded-[var(--radius-md)] bg-[var(--color-bg-surface-2)] p-3 text-sm text-[var(--color-text-primary)] whitespace-pre-wrap break-all">
              {result.content}
            </div>
            <div className="text-xs text-[var(--color-text-muted)]">
              {t('integrations_page.agent_run.confidence', { defaultValue: 'Confidence' })}: {result.confidence ?? '—'}
            </div>
            {Array.isArray(result.tool_calls) && result.tool_calls.length > 0 && (
              <>
                <div className="text-xs font-semibold text-[var(--color-text-secondary)]">{t('integrations_page.agent_run.tool_calls', { defaultValue: 'Tool calls' })}</div>
                <JsonBlock value={result.tool_calls} />
              </>
            )}
            {result.metadata && Object.keys(result.metadata).length > 0 && (
              <>
                <div className="text-xs font-semibold text-[var(--color-text-secondary)]">{t('integrations_page.agent_run.metadata', { defaultValue: 'Metadata' })}</div>
                <JsonBlock value={result.metadata} />
              </>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export function IntegrationsPage() {
  const { t } = useI18n();
  return (
    <div className="h-full overflow-y-auto page-transition">
      <div className="p-4 md:p-6 max-w-4xl mx-auto">
        <PageHeader
          title={t('integrations_page.title', { defaultValue: 'Integrations' })}
          icon={<Plug size={20} />}
          className="border-b border-[var(--color-border-subtle)] pb-[var(--space-4)] [&_h1]:text-[length:var(--text-base)] [&_h1]:md:text-[length:var(--text-base)] [&_p]:text-[var(--color-text-muted)]"
        />
        <div className="mt-4 space-y-4">
          <QQBotCard />
          <LangGraphCard />
          <Mem0Card />
          <AgentRunCard />
        </div>
      </div>
    </div>
  );
}

export default IntegrationsPage;
