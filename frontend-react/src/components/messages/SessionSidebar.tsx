import { useState } from 'react';
import {
  MessageSquare, Search, Plus, Archive, Download, Trash2,
  MoreHorizontal, Edit3, Pin, Star, Clock, X, Check,
} from 'lucide-react';
import { cn } from '../../lib/utils';
import { Dropdown, DropdownItem, DropdownDivider } from '../ui/Dropdown';

interface Session {
  id: string;
  title: string;
  lastMessage?: string;
  timestamp: number;
  pinned?: boolean;
  archived?: boolean;
  messageCount?: number;
}

interface SidebarProps {
  sessions: Session[];
  activeSessionId: string | null;
  onSelectSession: (id: string) => void;
  onCreateSession: () => void;
  onDeleteSession: (id: string) => void;
  onArchiveSession: (id: string) => void;
  onPinSession: (id: string) => void;
  onRenameSession: (id: string, title: string) => void;
  onExportSession: (id: string) => void;
  collapsed?: boolean;
}

type ViewMode = 'all' | 'pinned' | 'archived';

export function SessionSidebar({
  sessions,
  activeSessionId,
  onSelectSession,
  onCreateSession,
  onDeleteSession,
  onArchiveSession,
  onPinSession,
  onRenameSession,
  onExportSession,
  collapsed,
}: SidebarProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [viewMode, setViewMode] = useState<ViewMode>('all');
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState('');

  const filteredSessions = sessions.filter((s) => {
    if (viewMode === 'pinned') return s.pinned && !s.archived;
    if (viewMode === 'archived') return s.archived;
    return !s.archived;
  }).filter((s) => {
    if (!searchQuery) return true;
    return s.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      s.lastMessage?.toLowerCase().includes(searchQuery.toLowerCase());
  });

  const pinnedSessions = filteredSessions.filter(s => s.pinned);
  const recentSessions = filteredSessions.filter(s => !s.pinned);

  const startRename = (session: Session) => {
    setEditingId(session.id);
    setEditTitle(session.title);
  };

  const saveRename = () => {
    if (editingId && editTitle.trim()) {
      onRenameSession(editingId, editTitle.trim());
    }
    setEditingId(null);
    setEditTitle('');
  };

  const formatTime = (ts: number) => {
    const diff = Date.now() - ts;
    if (diff < 60000) return '刚刚';
    if (diff < 3600000) return `${Math.floor(diff / 60000)}分钟前`;
    if (diff < 86400000) return `${Math.floor(diff / 3600000)}小时前`;
    return new Date(ts).toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' });
  };

  if (collapsed) {
    return (
      <div className="flex flex-col items-center py-3 gap-2">
        <button onClick={onCreateSession} className="p-2.5 rounded-xl hover:bg-[var(--color-bg-surface-2)] text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] transition-colors" aria-label="新建会话" title="新建会话">
          <Plus size={18} />
        </button>
        <button className="p-2.5 rounded-xl hover:bg-[var(--color-bg-surface-2)] text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] transition-colors" aria-label="搜索会话" title="搜索会话">
          <Search size={18} />
        </button>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      <div className="p-3 space-y-2">
        <button
          onClick={onCreateSession}
          className="w-full flex items-center gap-2.5 px-3 py-2.5 rounded-xl text-sm font-medium transition-all duration-200 border"
          style={{ backgroundColor: 'var(--color-accent-subtle)', borderColor: 'var(--color-accent)/20', color: 'var(--color-accent)' }}
        >
          <Plus size={16} />
          新建会话
        </button>

        <div className="relative">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--color-text-muted)]" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="搜索会话..."
            className="w-full pl-9 pr-3 py-2 rounded-xl text-xs bg-[var(--color-bg-surface-2)] border border-[var(--color-border-subtle)] text-[var(--color-text-primary)] placeholder:text-[var(--color-text-muted)] focus:outline-none focus:border-[var(--color-accent)]/30 transition-colors"
            aria-label="搜索会话"
          />
          {searchQuery && (
            <button onClick={() => setSearchQuery('')} className="absolute right-2 top-1/2 -translate-y-1/2 p-0.5 rounded text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)]" aria-label="清除搜索">
              <X size={12} />
            </button>
          )}
        </div>

        <div className="flex items-center gap-1 p-1 rounded-lg" style={{ backgroundColor: 'var(--color-bg-surface-2)' }}>
          {([
            { id: 'all', label: '全部', icon: MessageSquare },
            { id: 'pinned', label: '置顶', icon: Pin },
            { id: 'archived', label: '归档', icon: Archive },
          ] as const).map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              onClick={() => setViewMode(id)}
              className={cn(
                'flex items-center gap-1 px-2 py-1 rounded-md text-[10px] font-medium transition-all duration-200 flex-1 justify-center',
                viewMode === id
                  ? 'bg-[var(--color-bg-surface-1)] text-[var(--color-text-primary)] shadow-sm'
                  : 'text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)]'
              )}
            >
              <Icon size={10} />
              {label}
            </button>
          ))}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto px-2 space-y-1">
        {pinnedSessions.length > 0 && viewMode !== 'archived' && (
          <div className="mb-2">
            <div className="flex items-center gap-1.5 px-2 py-1.5 text-[10px] font-semibold uppercase tracking-wider text-[var(--color-text-muted)]">
              <Star size={10} />
              置顶
            </div>
            {pinnedSessions.map((session) => (
              <SessionItem
                key={session.id}
                session={session}
                isActive={session.id === activeSessionId}
                editing={editingId === session.id}
                editTitle={editTitle}
                onSelect={() => onSelectSession(session.id)}
                onEdit={() => startRename(session)}
                onDelete={() => onDeleteSession(session.id)}
                onArchive={() => onArchiveSession(session.id)}
                onPin={() => onPinSession(session.id)}
                onExport={() => onExportSession(session.id)}
                onRenameChange={setEditTitle}
                onRenameSave={saveRename}
                onRenameCancel={() => setEditingId(null)}
                formatTime={formatTime}
              />
            ))}
          </div>
        )}

        {recentSessions.length > 0 && (
          <div>
            {viewMode === 'all' && pinnedSessions.length > 0 && (
              <div className="flex items-center gap-1.5 px-2 py-1.5 text-[10px] font-semibold uppercase tracking-wider text-[var(--color-text-muted)]">
                <Clock size={10} />
                最近
              </div>
            )}
            {recentSessions.map((session) => (
              <SessionItem
                key={session.id}
                session={session}
                isActive={session.id === activeSessionId}
                editing={editingId === session.id}
                editTitle={editTitle}
                onSelect={() => onSelectSession(session.id)}
                onEdit={() => startRename(session)}
                onDelete={() => onDeleteSession(session.id)}
                onArchive={() => onArchiveSession(session.id)}
                onPin={() => onPinSession(session.id)}
                onExport={() => onExportSession(session.id)}
                onRenameChange={setEditTitle}
                onRenameSave={saveRename}
                onRenameCancel={() => setEditingId(null)}
                formatTime={formatTime}
              />
            ))}
          </div>
        )}

        {filteredSessions.length === 0 && (
          <div className="text-center py-8">
            <MessageSquare size={32} className="mx-auto mb-2 text-[var(--color-text-muted)] opacity-30" />
            <p className="text-xs text-[var(--color-text-muted)]">
              {searchQuery ? '未找到匹配的会话' : '暂无会话'}
            </p>
          </div>
        )}
      </div>

      <div className="p-3 border-t border-[var(--color-border-subtle)]">
        <div className="flex items-center justify-between">
          <span className="text-[10px] text-[var(--color-text-muted)]">
            {filteredSessions.length} 个会话
          </span>
          <button className="p-1.5 rounded-lg text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-surface-2)] transition-colors" aria-label="导出全部" title="导出全部">
            <Download size={14} />
          </button>
        </div>
      </div>
    </div>
  );
}

interface SessionItemProps {
  session: Session;
  isActive: boolean;
  editing: boolean;
  editTitle: string;
  onSelect: () => void;
  onEdit: () => void;
  onDelete: () => void;
  onArchive: () => void;
  onPin: () => void;
  onExport: () => void;
  onRenameChange: (title: string) => void;
  onRenameSave: () => void;
  onRenameCancel: () => void;
  formatTime: (ts: number) => string;
}

function SessionItem({
  session, isActive, editing, editTitle,
  onSelect, onEdit, onDelete, onArchive, onPin, onExport,
  onRenameChange, onRenameSave, onRenameCancel, formatTime,
}: SessionItemProps) {
  return (
    <div
      className={cn(
        'group relative flex items-center gap-2 px-2.5 py-2 rounded-xl cursor-pointer transition-all duration-200',
        isActive
          ? 'bg-[var(--color-accent-subtle)] border border-[var(--color-accent)]/20'
          : 'hover:bg-[var(--color-bg-surface-2)] border border-transparent'
      )}
      onClick={onSelect}
      role="button"
      aria-current={isActive ? 'true' : undefined}
      tabIndex={0}
    >
      <div className="flex-1 min-w-0">
        {editing ? (
          <div className="flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
            <input
              type="text"
              value={editTitle}
              onChange={(e) => onRenameChange(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') onRenameSave();
                if (e.key === 'Escape') onRenameCancel();
              }}
              className="flex-1 px-1.5 py-0.5 rounded text-xs bg-[var(--color-bg-surface-3)] text-[var(--color-text-primary)] border border-[var(--color-accent)]/30 focus:outline-none"
              autoFocus
              aria-label="编辑会话名称"
            />
            <button onClick={onRenameSave} className="p-0.5 rounded text-[var(--color-success)] hover:bg-[var(--color-success-subtle)]">
              <Check size={12} />
            </button>
            <button onClick={onRenameCancel} className="p-0.5 rounded text-[var(--color-text-muted)] hover:bg-[var(--color-bg-surface-3)]">
              <X size={12} />
            </button>
          </div>
        ) : (
          <>
            <div className="flex items-center gap-1.5">
              {session.pinned && <Pin size={9} className="text-[var(--color-warning)] shrink-0" />}
              <span className={cn(
                'text-xs font-medium truncate',
                isActive ? 'text-[var(--color-text-primary)]' : 'text-[var(--color-text-secondary)]'
              )}>
                {session.title}
              </span>
            </div>
            {session.lastMessage && (
              <p className="text-[10px] text-[var(--color-text-muted)] truncate mt-0.5">{session.lastMessage}</p>
            )}
            <div className="flex items-center gap-2 mt-0.5">
              <span className="text-[9px] text-[var(--color-text-muted)]">{formatTime(session.timestamp)}</span>
              {session.messageCount !== undefined && (
                <span className="text-[9px] text-[var(--color-text-muted)]">{session.messageCount} 条消息</span>
              )}
            </div>
          </>
        )}
      </div>

      {!editing && (
        <div className="opacity-0 group-hover:opacity-100 transition-opacity shrink-0" onClick={(e) => e.stopPropagation()}>
          <Dropdown
            trigger={
              <button className="p-1 rounded-lg text-[var(--color-text-muted)] hover:bg-[var(--color-bg-surface-3)] transition-colors" aria-label="会话选项">
                <MoreHorizontal size={14} />
              </button>
            }
            align="right"
          >
            <DropdownItem icon={<Edit3 size={12} />} onClick={onEdit}>重命名</DropdownItem>
            <DropdownItem icon={<Pin size={12} />} onClick={onPin}>{session.pinned ? '取消置顶' : '置顶'}</DropdownItem>
            <DropdownItem icon={<Download size={12} />} onClick={onExport}>导出</DropdownItem>
            <DropdownDivider />
            <DropdownItem icon={<Archive size={12} />} onClick={onArchive}>归档</DropdownItem>
            <DropdownItem icon={<Trash2 size={12} />} danger onClick={onDelete}>删除</DropdownItem>
          </Dropdown>
        </div>
      )}
    </div>
  );
}
