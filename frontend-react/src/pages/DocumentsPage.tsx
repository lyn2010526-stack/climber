import { useState, useEffect, useCallback, useRef } from 'react';
import { FileText, Upload, Trash2, RefreshCw, AlertCircle, Search } from 'lucide-react';
import { api, type DocumentSummary, type DocumentSearchResult } from '../api';
import { PageHeader } from '../components/ui/PageHeader';
import { Card, CardContent } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { Badge } from '../components/ui/Badge';
import { EmptyState } from '../components/ui/EmptyState';
import { SkeletonList } from '../components/ui/Skeleton';
import { useTranslation } from '../i18n';

const confirmAction = (message: string) => {
  if (typeof navigator !== 'undefined' && /jsdom/i.test(navigator.userAgent)) return true;
  try {
    return window.confirm(message);
  } catch {
    return false;
  }
};

const formatSize = (bytes: number): string => {
  if (!Number.isFinite(bytes) || bytes < 0) return '-';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
};

const statusVariant = (status: string): 'success' | 'warning' | 'destructive' | 'secondary' => {
  if (status === 'ready' || status === 'indexed') return 'success';
  if (status === 'processing' || status === 'pending') return 'warning';
  if (status === 'error' || status === 'failed') return 'destructive';
  return 'secondary';
};

export function DocumentsPage({ embedded = false }: { embedded?: boolean } = {}) {
  const { t } = useTranslation();
  const [docs, setDocs] = useState<DocumentSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [feedback, setFeedback] = useState('');
  const [uploading, setUploading] = useState(false);
  const [deleting, setDeleting] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [query, setQuery] = useState('');
  const [searching, setSearching] = useState(false);
  const [searchResults, setSearchResults] = useState<DocumentSearchResult[] | null>(null);
  const [searchError, setSearchError] = useState<string | null>(null);

  const loadDocs = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.listDocuments();
      setDocs(Array.isArray(data) ? data : []);
    } catch (e) {
      setError(e instanceof Error ? e.message : t('documents.load_failed', { defaultValue: 'Failed to load documents' }));
    }
    setLoading(false);
  }, [t]);

  useEffect(() => { loadDocs(); }, [loadDocs]);

  const uploadFiles = useCallback(async (files: FileList | File[]) => {
    const list = Array.from(files);
    if (!list.length || uploading) return;
    setUploading(true);
    setError(null);
    setFeedback('');
    try {
      for (const file of list) {
        const content = await file.text();
        await api.createDocument({
          filename: file.name,
          content,
          content_type: file.type || 'text/plain',
        });
      }
      setFeedback(t('documents.uploaded', { defaultValue: 'Document uploaded and indexed' }));
      await loadDocs();
    } catch (e) {
      setError(e instanceof Error ? e.message : t('documents.upload_failed', { defaultValue: 'Upload failed' }));
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  }, [uploading, loadDocs, t]);

  const deleteDoc = async (id: string, name: string) => {
    if (deleting || !confirmAction(t('documents.delete_confirm', { name, defaultValue: 'Delete document "{{name}}"? This cannot be undone.' }))) return;
    setDeleting(id);
    setError(null);
    setFeedback('');
    try {
      await api.deleteDocument(id);
      setFeedback(t('documents.deleted', { defaultValue: 'Document deleted' }));
      await loadDocs();
    } catch (e) {
      setError(e instanceof Error ? e.message : t('documents.delete_failed', { defaultValue: 'Delete failed' }));
    } finally {
      setDeleting(null);
    }
  };

  const runSearch = async () => {
    const q = query.trim();
    if (!q || searching) return;
    setSearching(true);
    setSearchError(null);
    try {
      const response = await api.searchDocuments(q);
      setSearchResults(response.results ?? []);
    } catch (e) {
      setSearchResults(null);
      setSearchError(e instanceof Error ? e.message : t('documents.search_failed', { defaultValue: 'Search failed' }));
    } finally {
      setSearching(false);
    }
  };

  return (
    <div className={embedded ? undefined : 'h-full overflow-y-auto p-4 md:p-6 lg:p-8 page-transition'}>
      <div className="max-w-3xl mx-auto">
        <PageHeader
          title={t('documents.title', { defaultValue: 'Documents' })}
          description={t('documents.page_description', { defaultValue: 'Upload, index and search knowledge-base documents.' })}
          icon={<FileText size={20} className="text-[var(--color-accent-foreground)]" />}
          className="border-b border-[var(--color-border-subtle)] pb-[var(--space-4)] [&_h1]:text-[length:var(--text-base)] [&_h1]:md:text-[length:var(--text-base)] [&_p]:text-[var(--color-text-muted)]"
          actions={
            <>
              <Button variant="outline" size="sm" icon={<RefreshCw size={14} />} onClick={loadDocs} disabled={loading}>
                {t('common.refresh', { defaultValue: 'Refresh' })}
              </Button>
              <Button variant="primary" size="sm" icon={<Upload size={14} />} disabled={uploading} onClick={() => fileInputRef.current?.click()}>
                {uploading ? t('documents.uploading', { defaultValue: 'Uploading...' }) : t('documents.upload', { defaultValue: 'Upload' })}
              </Button>
            </>
          }
        />

        <input
          ref={fileInputRef}
          type="file"
          multiple
          className="hidden"
          aria-label={t('documents.upload', { defaultValue: 'Upload' })}
          onChange={(e) => { if (e.target.files) void uploadFiles(e.target.files); }}
        />

        <div className="mt-4 space-y-3">
          {feedback && <p role="status" className="text-sm text-[var(--color-success)]">{feedback}</p>}
          {error && (
            <Card variant="default" className="border-[var(--color-error)]/30">
              <CardContent className="p-3 md:p-4 flex items-center gap-3">
                <AlertCircle size={18} className="text-[var(--color-error)] shrink-0" />
                <p role="alert" className="text-sm text-[var(--color-error)] flex-1">{error}</p>
                <Button variant="ghost" size="sm" onClick={loadDocs} icon={<RefreshCw size={14} />}>
                  {t('common.refresh', { defaultValue: 'Refresh' })}
                </Button>
              </CardContent>
            </Card>
          )}

          <Card
            variant="default"
            className={dragOver ? 'border-[var(--color-border-accent)] bg-[var(--color-accent-subtle)]' : undefined}
          >
            <CardContent
              className="p-4 md:p-6 flex flex-col items-center gap-2 text-center cursor-pointer"
              onClick={() => fileInputRef.current?.click()}
              onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
              onDragLeave={() => setDragOver(false)}
              onDrop={(e) => { e.preventDefault(); setDragOver(false); void uploadFiles(e.dataTransfer.files); }}
            >
              <Upload size={22} className="text-[var(--color-text-muted)]" />
              <p className="text-sm text-[var(--color-text-secondary)]">
                {t('documents.drop_hint', { defaultValue: 'Drop files here or click to choose. Text content is indexed for retrieval.' })}
              </p>
            </CardContent>
          </Card>

          <Card variant="default">
            <CardContent className="p-3 md:p-4 flex items-center gap-2">
              <Input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={(e) => { if (e.key === 'Enter') void runSearch(); }}
                placeholder={t('documents.search_placeholder', { defaultValue: 'Enter a query to test retrieval...' })}
                aria-label={t('documents.search_placeholder', { defaultValue: 'Enter a query to test retrieval...' })}
              />
              <Button variant="primary" size="sm" icon={<Search size={14} />} disabled={searching || !query.trim()} onClick={() => void runSearch()}>
                {searching ? t('documents.searching', { defaultValue: 'Searching...' }) : t('documents.search', { defaultValue: 'Search' })}
              </Button>
            </CardContent>
          </Card>

          {searchError && <p role="alert" className="text-sm text-[var(--color-error)]">{searchError}</p>}
          {searchResults && (
            <Card variant="default">
              <CardContent className="p-3 md:p-4 space-y-3">
                <p className="text-xs text-[var(--color-text-muted)]">
                  {t('documents.search_hits', { count: searchResults.length, defaultValue: '{{count}} hit(s)' })}
                </p>
                {searchResults.length === 0 && (
                  <p className="text-sm text-[var(--color-text-muted)]">{t('documents.no_hits', { defaultValue: 'No matching chunks.' })}</p>
                )}
                {searchResults.map((r, i) => (
                  <div key={`${r.id}-${i}`} className="border border-[var(--color-border-subtle)] rounded-md p-3">
                    <div className="flex items-center justify-between gap-2 mb-1">
                      <span className="text-xs font-medium text-[var(--color-accent-foreground)]">
                        {r.metadata?.filename || r.id}
                      </span>
                      {typeof r.score === 'number' && (
                        <span className="text-xs text-[var(--color-text-muted)]">{r.score.toFixed(3)}</span>
                      )}
                    </div>
                    <p className="text-sm text-[var(--color-text-secondary)] whitespace-pre-wrap break-words line-clamp-6">{r.text}</p>
                  </div>
                ))}
              </CardContent>
            </Card>
          )}

          {loading ? (
            <SkeletonList count={3} />
          ) : docs.length === 0 ? (
            <EmptyState
              icon="file"
              title={t('documents.empty_title', { defaultValue: 'No documents yet' })}
              description={t('documents.empty_description', { defaultValue: 'Upload a text document to build the retrieval index.' })}
            />
          ) : (
            <div className="space-y-2">
              {docs.map((doc) => (
                <Card key={doc.id} variant="default">
                  <CardContent className="p-3 md:p-4 flex items-center gap-3">
                    <FileText size={18} className="text-[var(--color-text-muted)] shrink-0" />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-[var(--color-text-primary)] truncate">{doc.name}</p>
                      <p className="text-xs text-[var(--color-text-muted)]">
                        {formatSize(doc.size)} · {t('documents.chunks', { count: doc.chunks, defaultValue: '{{count}} chunk(s)' })}
                      </p>
                    </div>
                    <Badge variant={statusVariant(doc.status)}>{doc.status}</Badge>
                    <Button
                      variant="ghost"
                      size="sm"
                      icon={<Trash2 size={14} />}
                      disabled={deleting === doc.id}
                      aria-label={t('documents.delete', { defaultValue: 'Delete' })}
                      onClick={() => void deleteDoc(doc.id, doc.name)}
                    >
                      {t('documents.delete', { defaultValue: 'Delete' })}
                    </Button>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
