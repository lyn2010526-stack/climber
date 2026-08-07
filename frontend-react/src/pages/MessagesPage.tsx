import { useState, useCallback, useMemo } from 'react';
import { MessagesList, type MessageItem } from '../components/messages/MessagesList';
import { MessageDetail } from '../components/messages/MessageDetail';
import { useWorkspaceStore } from '../store/workspace';

const MOCK_MESSAGES: MessageItem[] = [
  {
    id: 'msg-1',
    title: 'Python 数据处理脚本',
    preview: '我来帮你写一个处理 CSV 文件的 Python 脚本。这个脚本会读取数据、清洗空值并生成统计报告...',
    timestamp: Date.now() - 120000,
    role: 'assistant',
    sessionId: 'session-abc123',
  },
  {
    id: 'msg-2',
    title: '代码优化建议',
    preview: '这段代码可以通过使用列表推导式来优化，同时建议添加类型注解以提高可读性...',
    timestamp: Date.now() - 3600000,
    role: 'assistant',
    sessionId: 'session-abc123',
  },
  {
    id: 'msg-3',
    title: '项目架构讨论',
    preview: '对于这个项目，我建议采用分层架构：API 层、Service 层、Repository 层...',
    timestamp: Date.now() - 7200000,
    role: 'assistant',
    sessionId: 'session-def456',
    isPinned: true,
  },
  {
    id: 'msg-4',
    title: 'Bug 修复方案',
    preview: '这个问题的根本原因是异步状态没有正确同步。解决方案是使用 useEffect 依赖数组...',
    timestamp: Date.now() - 86400000,
    role: 'assistant',
    sessionId: 'session-ghi789',
  },
  {
    id: 'msg-5',
    title: 'API 设计建议',
    preview: 'RESTful API 设计应该遵循资源导向的原则，使用合适的 HTTP 方法和状态码...',
    timestamp: Date.now() - 172800000,
    role: 'assistant',
    sessionId: 'session-abc123',
    isArchived: true,
  },
];

export function MessagesPage() {
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [messages, setMessages] = useState<MessageItem[]>(MOCK_MESSAGES);
  const [showDetail, setShowDetail] = useState(false);

  const selectedMessage = useMemo(
    () => messages.find((m) => m.id === selectedId) ?? null,
    [messages, selectedId],
  );

  const handleSelect = useCallback((id: string) => {
    setSelectedId(id);
    setShowDetail(true);
  }, []);

  const handleBack = useCallback(() => {
    setShowDetail(false);
  }, []);

  const handlePin = useCallback((id: string) => {
    setMessages((prev) =>
      prev.map((m) => (m.id === id ? { ...m, isPinned: !m.isPinned } : m)),
    );
  }, []);

  const handleDelete = useCallback((id: string) => {
    setMessages((prev) => prev.filter((m) => m.id !== id));
    if (selectedId === id) {
      setSelectedId(null);
      setShowDetail(false);
    }
  }, [selectedId]);

  const handleArchive = useCallback((id: string) => {
    setMessages((prev) =>
      prev.map((m) => (m.id === id ? { ...m, isArchived: !m.isArchived } : m)),
    );
  }, []);

  const handleExport = useCallback((id: string) => {
    const msg = messages.find((m) => m.id === id);
    if (msg) {
      const blob = new Blob([msg.preview], { type: 'text/plain' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${msg.title}.txt`;
      a.click();
      URL.revokeObjectURL(url);
    }
  }, [messages]);

  return (
    <div className="flex h-full">
      {/* Messages sidebar */}
      <div
        className={`w-full md:w-80 lg:w-96 shrink-0 ${
          showDetail ? 'hidden md:flex' : 'flex'
        } flex-col h-full`}
        style={{ borderRight: '1px solid var(--color-border-subtle)' }}
      >
        <MessagesList
          messages={messages}
          selectedId={selectedId}
          onSelect={handleSelect}
          onPin={handlePin}
          onDelete={handleDelete}
          onArchive={handleArchive}
          onExport={handleExport}
        />
      </div>

      {/* Message detail */}
      <div
        className={`flex-1 ${
          showDetail ? 'flex' : 'hidden md:flex'
        } flex-col h-full`}
      >
        <MessageDetail message={selectedMessage} onBack={handleBack} />
      </div>
    </div>
  );
}

export default MessagesPage;
