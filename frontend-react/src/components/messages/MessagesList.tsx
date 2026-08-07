import { useState } from 'react';
import { Search, Filter, MoreHorizontal, Archive, Trash2, Pin, Download, RefreshCw } from 'lucide-react';
import { cn } from '../../lib/utils';

export interface MessageItem {
  id: string;
  title: string;
  preview: string;
  timestamp: number;
  role: 'user' | 'assistant';
  sessionId: string;
  isPinned?: boolean;
  isArchived?: boolean;
}

interface MessagesListProps {
  messages: MessageItem[];
  selectedId?: string | null;
  onSelect: (id: string) => void;
  onDelete?: (id: string) => void;
  onArchive?: (id: string) => void;
  onPin?: (id: string) => void;
  onExport?: (id: string) => void;
  className?: string;
}

function formatTimestamp(ts: number): string {
  const diff = Date.now() - ts;
  if (diff < 60000) return '刚刚';
  if (diff < 3600000) return `${Math.floor(diff / 60000)} 分钟前`;
  if (diff < 86400000) return `${Math.floor(diff / 3600000)} 小时前`;
  return new Date(ts).toLocaleDateString('zh-CN', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export function MessagesList({
  messages,
  selectedId,
  onSelect,
  onDelete,
  onArchive,
  onPin,
  onExport,
  className,
}: MessagesListProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [activeMenu, setActiveMenu] = useState<string | null>(null);

  const filtered = messages.filter((m) => {
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase();
    return (
      m.title.toLowerCase().includes(q) ||
      m.preview.toLowerCase().includes(q)
    );
  });

  return (
    <div className={cn('flex flex-col h-full', className)}>
      {/* Header */}
      <div className="p-4 space-y-3" style={{ borderBottom: '1px solid var(--color-border-subtle)' }}>
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-[var(--color-text-primary)]">消息记录</h2>
          <button
            className="p-2 rounded-xl text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-surface-2)] transition-colors"
            title="刷新"
          >
            <RefreshCw size={16} />
          </button>
        </div>

        {/* Search */}
        <div className="relative">
          <Search
            size={14}
            className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--color-text-muted)]"
          />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="搜索消息..."
            className={cn(
              'w-full pl-9 pr-3 py-2 rounded-xl text-xs transition-colors',
              'bg-[var(--color-bg-surface-2)] border border-[var(--color-border-subtle)]',
              'text-[var(--color-text-primary)] placeholder:text-[var(--color-text-muted)]',
              'focus:outline-none focus:border-[var(--color-accent)]/30',
            )}
          />
        </div>

        {/* Filter bar */}
        <div className="flex items-center gap-2">
          <button
            className="flex items-center gap-1 px-2.5 py-1 rounded-lg text-[10px] font-medium text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-surface-2)] transition-colors"
          >
            <Filter size={11} />
            全部
          </button>
          <span className="text-[10px] text-[var(--color-text-muted)]">
            {filtered.length} 条消息
          </span>
        </div>
      </div>

      {/* Message list */}
      <div className="flex-1 overflow-y-auto">
        {filtered.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full py-12">
            <Search size={32} className="text-[var(--color-text-muted)] opacity-30 mb-3" />
            <p className="text-sm text-[var(--color-text-muted)]">
              {searchQuery ? '未找到匹配的消息' : '暂无消息记录'}
            </p>
          </div>
        ) : (
          <div className="divide-y" style={{ borderColor: 'var(--color-border-subtle)' }}>
            {filtered.map((msg) => (
              <div
                key={msg.id}
                className={cn(
                  'group relative flex items-start gap-3 px-4 py-3 cursor-pointer transition-colors',
                  selectedId === msg.id
                    ? 'bg-[var(--color-accent-subtle)]'
                    : 'hover:bg-[var(--color-bg-surface-2)]',
                )}
                onClick={() => onSelect(msg.id)}
              >
                {/* Role indicator */}
                <div
                  className={cn(
                    'w-2 h-2 rounded-full mt-2 shrink-0',
                    msg.role === 'user' ? 'bg-[var(--color-accent)]' : 'bg-[#8B5CF6]',
                  )}
                />

                {/* Content */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span
                      className={cn(
                        'text-xs font-medium truncate',
                        selectedId === msg.id
                          ? 'text-[var(--color-text-primary)]'
                          : 'text-[var(--color-text-secondary)]',
                      )}
                    >
                      {msg.title}
                    </span>
                    {msg.isPinned && (
                      <Pin size={9} className="text-[var(--color-warning)] shrink-0" />
                    )}
                  </div>
                  <p className="text-[11px] text-[var(--color-text-muted)] truncate mt-0.5 leading-relaxed">
                    {msg.preview}
                  </p>
                  <span className="text-[9px] text-[var(--color-text-muted)] mt-1 block">
                    {formatTimestamp(msg.timestamp)}
                  </span>
                </div>

                {/* Actions menu */}
                <div className="opacity-0 group-hover:opacity-100 transition-opacity shrink-0">
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      setActiveMenu(activeMenu === msg.id ? null : msg.id);
                    }}
                    className="p-1 rounded-md text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-surface-3)] transition-colors"
                  >
                    <MoreHorizontal size={14} />
                  </button>

                  {activeMenu === msg.id && (
                    <div
                      className="absolute right-4 top-10 z-20 w-40 rounded-xl border py-1 shadow-xl fade-enter"
                      style={{
                        backgroundColor: 'var(--color-bg-surface-2)',
                        borderColor: 'var(--color-border-subtle)',
                        boxShadow: '0 8px 24px rgba(0, 0, 0, 0.3)',
                      }}
                    >
                      {onPin && (
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            onPin(msg.id);
                            setActiveMenu(null);
                          }}
                          className="w-full flex items-center gap-2 px-3 py-2 text-xs text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-surface-3)] transition-colors"
                        >
                          <Pin size={12} />
                          {msg.isPinned ? '取消置顶' : '置顶'}
                        </button>
                      )}
                      {onExport && (
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            onExport(msg.id);
                            setActiveMenu(null);
                          }}
                          className="w-full flex items-center gap-2 px-3 py-2 text-xs text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-surface-3)] transition-colors"
                        >
                          <Download size={12} />
                          导出
                        </button>
                      )}
                      {onArchive && (
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            onArchive(msg.id);
                            setActiveMenu(null);
                          }}
                          className="w-full flex items-center gap-2 px-3 py-2 text-xs text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-surface-3)] transition-colors"
                        >
                          <Archive size={12} />
                          归档
                        </button>
                      )}
                      {onDelete && (
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            onDelete(msg.id);
                            setActiveMenu(null);
                          }}
                          className="w-full flex items-center gap-2 px-3 py-2 text-xs text-[var(--color-error)] hover:bg-[var(--color-error-subtle)] transition-colors"
                        >
                          <Trash2 size={12} />
                          删除
                        </button>
                      )}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
