import { useCallback, useEffect, useRef, useState } from 'react';
import { Send } from 'lucide-react';
import { api } from '../../api';
import { useI18n } from '../../i18n';
import { formatTime } from '../../i18n/utils';
import { Button } from '../ui/Button';

interface GroupMessage {
  id: string;
  sender_name: string;
  content: string;
  created_at: string;
}

interface GroupRoomProps {
  groupId: string;
  onMemberUpdate?: (memberId: string, status: string) => void;
  onTaskUpdate?: (taskId: string) => void;
}

/** Backend WS frames: the hub acks each frame and broadcasts message/task events. */
type Frame =
  | { type: 'ack'; data: { ok: boolean; id?: string; error?: string } }
  | { type: 'message'; data: { id?: string } }
  | { type: 'member_update'; data?: { id?: string; member_id?: string; status?: string } }
  | { type: 'task_update'; data?: { id?: string; task_id?: string } }
  | { type: 'error'; error?: string }
  | { type: 'pong' }
  | { type: string; data?: unknown };

export function GroupRoom({ groupId, onMemberUpdate, onTaskUpdate }: GroupRoomProps) {
  const { t } = useI18n();
  const [messages, setMessages] = useState<GroupMessage[]>([]);
  const [input, setInput] = useState('');
  const [connected, setConnected] = useState(false);
  const [sending, setSending] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [historyError, setHistoryError] = useState('');
  const wsRef = useRef<WebSocket | null>(null);
  const endRef = useRef<HTMLDivElement>(null);
  const disposedRef = useRef(false);

  const sortMessages = (list: GroupMessage[]) =>
    [...list].sort((a, b) => a.created_at.localeCompare(b.created_at));

  const loadHistory = useCallback(async (targetGroupId: string) => {
    const data = await api.listGroupMessages(targetGroupId);
    if (!Array.isArray(data?.messages)) throw new Error(t('common.error'));
    const list = data.messages as GroupMessage[];
    if (list.some(item => !item || typeof item.id !== 'string' || typeof item.content !== 'string')) {
      throw new Error(t('common.error'));
    }
    return sortMessages(list);
  }, [t]);

  useEffect(() => {
    disposedRef.current = false;
    setMessages([]);
    setLoading(true);
    setError('');
    setHistoryError('');

    void loadHistory(groupId)
      .then(list => {
        if (!disposedRef.current) setMessages(list);
      })
      .catch(reason => {
        if (!disposedRef.current) {
          setHistoryError(reason instanceof Error ? reason.message : '加载消息失败');
        }
      })
      .finally(() => {
        if (!disposedRef.current) setLoading(false);
      });

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const ws = new WebSocket(`${protocol}//${window.location.host}/api/v1/ws/groups/${groupId}`);
    wsRef.current = ws;
    ws.onopen = () => { if (!disposedRef.current) setConnected(true); };
    ws.onclose = () => {
      if (!disposedRef.current) {
        setConnected(false);
        setSending(false);
      }
    };
    ws.onmessage = event => {
      if (disposedRef.current) return;
      let frame: Frame;
      try {
        frame = JSON.parse(event.data) as Frame;
      } catch {
        return;
      }
      if (frame.type === 'ack') {
        setSending(false);
        const ack = frame.data as { ok?: boolean; error?: string } | undefined;
        if (ack && ack.ok === false) {
          setError(ack.error || t('common.error'));
        } else {
          setInput('');
          setError('');
        }
        return;
      }
      if (frame.type === 'error') {
        setSending(false);
        setError((frame as { error?: string }).error || t('common.error'));
        return;
      }
      if (frame.type === 'member_update') {
        const data = frame.data as { id?: string; member_id?: string; status?: string } | undefined;
        if (data?.status && (data.member_id || data.id)) onMemberUpdate?.(data.member_id || data.id || '', data.status);
        return;
      }
      if (frame.type === 'task_update') {
        const data = frame.data as { id?: string; task_id?: string } | undefined;
        if (data?.task_id || data?.id) onTaskUpdate?.(data.task_id || data.id || '');
        return;
      }
      if (frame.type !== 'message') return;
      // A broadcast only confirms that a message exists; the transcript endpoint
      // is the only source of its sender and body, so re-read it instead of
      // rendering an empty placeholder.
      void loadHistory(groupId)
        .then(list => { if (!disposedRef.current) setMessages(list); })
         .catch(reason => {
           if (!disposedRef.current) setHistoryError(reason instanceof Error ? reason.message : t('common.error'));
         });
    };

    return () => {
      disposedRef.current = true;
      ws.close();
      wsRef.current = null;
    };
  }, [groupId, loadHistory]);

  useEffect(() => {
    const node = endRef.current;
    if (node && typeof node.scrollIntoView === 'function') {
      node.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages]);

  const submit = (event: React.FormEvent) => {
    event.preventDefault();
     if (!input.trim() || sending) return;
     if (wsRef.current?.readyState !== WebSocket.OPEN) {
       setError(t('common.error'));
       return;
     }
     const content = input.trim();
     try {
       setSending(true);
       wsRef.current.send(JSON.stringify({ type: 'message', content }));
       setError('');
     } catch {
       setSending(false);
       setError(t('common.error'));
     }
   };

  const empty = !loading && !historyError && !error && messages.length === 0;

  return (
     <section aria-label={t('common.message')} className="flex h-full min-w-0 flex-col">
       <div className="flex items-center justify-between border-b border-[var(--color-border-subtle)] pb-3">
         <h2 className="text-sm font-semibold">{t('common.message')}</h2>
         <span role="status" className="text-xs text-[var(--color-text-muted)]">
           {connected ? t('common.status') : t('common.error')}
         </span>
       </div>
       {(error || historyError) && (
         <div className="py-3 text-sm text-[var(--color-error)]">
           <p role="alert">{error || historyError}</p>
           {historyError && <Button variant="ghost" size="xs" className="mt-1" onClick={() => {
             setHistoryError('');
             setLoading(true);
             void loadHistory(groupId).then(setMessages).catch(reason => setHistoryError(reason instanceof Error ? reason.message : t('common.error'))).finally(() => setLoading(false));
           }}>{t('common.retry')}</Button>}
         </div>
       )}
      <div className="min-h-0 flex-1 space-y-4 overflow-y-auto py-4">
         {loading && <p role="status" className="text-sm">{t('common.loading')}</p>}
         {empty && <p className="text-sm text-[var(--color-text-muted)]">{t('chat.no_messages')}</p>}
        {messages.map(message => (
          <article key={message.id} className="text-sm">
            <div className="flex flex-wrap gap-2 text-xs">
              <span className="font-medium">{message.sender_name}</span>
              <time className="text-[var(--color-text-muted)]">
                {formatTime(message.created_at)}
              </time>
            </div>
            <p className="mt-1 whitespace-pre-wrap break-words text-[var(--color-text-secondary)]">
              {message.content}
            </p>
          </article>
        ))}
        <div ref={endRef} />
      </div>
      <form className="flex gap-2 border-t border-[var(--color-border-subtle)] pt-3" onSubmit={submit}>
        <input
           aria-label={t('common.message')}
          value={input}
          onChange={event => setInput(event.target.value)}
           placeholder={t('chat.placeholder')}
          className="min-w-0 flex-1 rounded-lg border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-1)] px-3 py-2 text-sm"
        />
        <Button
          type="submit"
          size="sm"
          disabled={!input.trim() || !connected || sending}
          icon={<Send size={14} />}
        >
           {sending ? t('common.saving') : t('chat.send')}
        </Button>
      </form>
    </section>
  );
}
