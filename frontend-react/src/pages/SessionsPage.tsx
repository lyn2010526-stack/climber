import { useState } from 'react';
import { Plus, Trash2, RefreshCw, MessageSquare, AlertCircle } from 'lucide-react';
import { useSessions } from '../stores/useSessions';
import { PageHeader } from '../components/ui/PageHeader';
import { Card, CardContent } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import { Input } from '../components/ui/Input';
import { EmptyState } from '../components/ui/EmptyState';
import { SkeletonList } from '../components/ui/Skeleton';

export function SessionsPage() {
  const { sessions, loading, error, createSession, deleteSession, refresh } = useSessions();
  const [newTitle, setNewTitle] = useState('');
  const [creating, setCreating] = useState(false);

  const handleCreate = async () => {
    setCreating(true);
    try {
      await createSession({ title: newTitle || undefined });
      setNewTitle('');
    } catch { /* skip */ }
    setCreating(false);
  };

  const handleDelete = async (id: string) => {
    try {
      await deleteSession(id);
    } catch { /* skip */ }
  };

  const formatDate = (dateStr: string) => {
    const d = new Date(dateStr);
    return d.toLocaleDateString() + ' ' + d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  return (
    <div className="h-full overflow-y-auto page-transition">
      <div className="p-4 md:p-6 lg:p-8 max-w-4xl mx-auto">
        <PageHeader
          title="会话"
          description="管理智能体会话"
          icon={<MessageSquare size={20} />}
          actions={
            <Button variant="ghost" size="icon" onClick={refresh} loading={loading}>
              <RefreshCw size={16} />
            </Button>
          }
        />

        <Card variant="default" className="mb-6">
          <CardContent className="p-4">
            <div className="flex gap-3">
              <Input
                placeholder="新会话标题（可选）..."
                value={newTitle}
                onChange={(e) => setNewTitle(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && handleCreate()}
              />
              <Button
                variant="primary"
                size="sm"
                icon={<Plus size={14} />}
                onClick={handleCreate}
                loading={creating}
              >
                创建
              </Button>
            </div>
          </CardContent>
        </Card>

        {error && (
          <Card variant="default" className="mb-6 border-[var(--color-error)]/30">
            <CardContent className="p-4 flex items-center gap-3">
              <AlertCircle size={18} className="text-[var(--color-error)] shrink-0" />
              <p className="text-sm text-[var(--color-error)] flex-1">{error}</p>
              <Button variant="outline" size="sm" onClick={refresh}>重试</Button>
            </CardContent>
          </Card>
        )}

        {loading && <SkeletonList count={3} />}

        {!loading && !error && sessions.length === 0 && (
          <EmptyState
            icon="file"
            title="暂无会话"
            description="创建一个会话以开始与智能体对话"
            action={
              <Button variant="primary" size="sm" onClick={handleCreate} icon={<Plus size={14} />}>
                创建会话
              </Button>
            }
          />
        )}

        {!loading && !error && sessions.length > 0 && (
          <div className="space-y-3 stagger-children">
            {sessions.map((session) => (
              <Card key={session.id} variant="default" className="hover-lift">
                <CardContent className="p-4">
                  <div className="flex items-center gap-4">
                    <div className="w-10 h-10 rounded-xl bg-[var(--color-accent)]/10 flex items-center justify-center border border-[var(--color-accent)]/20 shrink-0">
                      <MessageSquare size={18} className="text-[var(--color-accent)]" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <h3 className="text-sm font-semibold text-[var(--color-text-primary)] truncate">
                          {session.title || '未命名会话'}
                        </h3>
                        <Badge
                          variant={session.status === 'active' ? 'success' : 'default'}
                          size="xs"
                        >
                          {session.status}
                        </Badge>
                      </div>
                      <p className="text-xs text-[var(--color-text-muted)] mt-1">
                        创建于 {formatDate(session.created_at)} &middot; 更新于 {formatDate(session.updated_at)}
                      </p>
                    </div>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => handleDelete(session.id)}
                      className="text-[var(--color-text-muted)] hover:text-[var(--color-error)]"
                    >
                      <Trash2 size={16} />
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
