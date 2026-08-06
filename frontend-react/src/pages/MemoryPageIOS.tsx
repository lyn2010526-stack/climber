import { useState, useCallback } from 'react';
import {
  Brain, Search, Clock, Trash2, Sparkles,
  Database, Layers, Filter, Plus, RefreshCw,
} from 'lucide-react';
import {
  IOSPage, IOSListGroup, IOSListItem, IOSSearchBar, IOSFab, IOSBadge,
  IOSSkeletonGroup, IOSConfirmDialog, toast,
} from '../components/ios';
import type { MemoryItem, MemoryLayer } from '../../types/memory';

const MEMORY_LAYERS: { id: MemoryLayer; label: string; icon: typeof Brain; color: string }[] = [
  { id: 'working', label: '工作记忆', icon: Layers, color: 'var(--color-accent)' },
  { id: 'episodic', label: '情景记忆', icon: Clock, color: 'var(--color-success)' },
  { id: 'semantic', label: '语义记忆', icon: Database, color: 'var(--color-accent-secondary)' },
  { id: 'procedural', label: '程序记忆', icon: Sparkles, color: 'var(--color-warning)' },
];

const SAMPLE_MEMORIES: MemoryItem[] = [
  { id: '1', content: '用户偏好使用 Python 进行数据分析', layer: 'semantic', score: 0.95, createdAt: '2026-08-04' },
  { id: '2', content: '上次对话中用户提到正在构建 Agent 平台', layer: 'episodic', score: 0.88, createdAt: '2026-08-05' },
  { id: '3', content: '代码生成任务需要先理解需求再实现', layer: 'procedural', score: 0.82, createdAt: '2026-08-03' },
  { id: '4', content: '当前正在优化记忆系统的检索性能', layer: 'working', score: 0.76, createdAt: '2026-08-06' },
  { id: '5', content: '用户喜欢简洁的 API 设计风格', layer: 'semantic', score: 0.91, createdAt: '2026-08-02' },
  { id: '6', content: '之前重构了沙箱执行器的命令解析逻辑', layer: 'episodic', score: 0.79, createdAt: '2026-08-05' },
];

export default function MemoryPage() {
  const [activeLayer, setActiveLayer] = useState<MemoryLayer | 'all'>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [memories] = useState<MemoryItem[]>(SAMPLE_MEMORIES);
  const [selectedMemory, setSelectedMemory] = useState<string | null>(null);
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);

  const filteredMemories = memories.filter((m) => {
    const matchesLayer = activeLayer === 'all' || m.layer === activeLayer;
    const matchesSearch = !searchQuery || m.content.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesLayer && matchesSearch;
  });

  const layerStats = MEMORY_LAYERS.map((layer) => ({
    ...layer,
    count: memories.filter((m) => m.layer === layer.id).length,
  }));

  const handleDelete = useCallback(() => {
    setShowDeleteDialog(false);
    toast.success('记忆已删除');
  }, []);

  return (
    <IOSPage className="h-full overflow-y-auto">
      <div className="p-4 md:p-6 max-w-4xl mx-auto pb-24">
        {/* Header */}
        <div className="mb-6">
          <h1 className="ios-title-1 text-[var(--color-text-primary)]">记忆管理</h1>
          <p className="ios-subhead text-[var(--color-text-muted)] mt-1">
            Agent 的多层记忆系统，支持语义检索与生命周期管理
          </p>
        </div>

        {/* Search */}
        <IOSSearchBar
          value={searchQuery}
          onChange={setSearchQuery}
          placeholder="搜索记忆内容..."
          className="mb-4"
        />

        {/* Layer Filter */}
        <div className="flex gap-2 mb-6 overflow-x-auto pb-2 -mx-4 px-4 md:mx-0 md:px-0">
          <button
            type="button"
            onClick={() => setActiveLayer('all')}
            className={`ios-segment flex-shrink-0 ${activeLayer === 'all' ? 'active' : ''}`}
          >
            全部 <IOSBadge variant="info">{memories.length}</IOSBadge>
          </button>
          {layerStats.map((layer) => (
            <button
              key={layer.id}
              type="button"
              onClick={() => setActiveLayer(layer.id)}
              className={`ios-segment flex-shrink-0 ${activeLayer === layer.id ? 'active' : ''}`}
            >
              {layer.label} <IOSBadge>{layer.count}</IOSBadge>
            </button>
          ))}
        </div>

        {/* Memory List */}
        <IOSListGroup title={`记忆条目 (${filteredMemories.length})`}>
          {filteredMemories.length === 0 ? (
            <div className="ios-empty-state">
              <Database size={40} strokeWidth={1.5} />
              <p>暂无匹配的记忆条目</p>
            </div>
          ) : (
            filteredMemories.map((memory) => {
              const layer = MEMORY_LAYERS.find((l) => l.id === memory.layer);
              return (
                <IOSListItem
                  key={memory.id}
                  icon={layer?.icon && <layer.icon size={16} />}
                  iconBg={layer?.color}
                  title={
                    <span className="line-clamp-2">{memory.content}</span>
                  }
                  detail={
                    <span className="flex items-center gap-2">
                      <IOSBadge variant={memory.score > 0.9 ? 'success' : memory.score > 0.8 ? 'info' : 'default'}>
                        {Math.round(memory.score * 100)}%
                      </IOSBadge>
                      <span className="ios-footnote">{memory.createdAt}</span>
                    </span>
                  }
                  showChevron={false}
                  onClick={() => {
                    setSelectedMemory(memory.id);
                    setShowDeleteDialog(true);
                  }}
                />
              );
            })
          )}
        </IOSListGroup>

        {/* Stats */}
        <IOSListGroup title="存储统计" className="mt-6">
          <IOSListItem
            icon={<Database size={16} />}
            iconBg="var(--color-accent)"
            title="总记忆条目"
            detail={<span className="ios-body">{memories.length} 条</span>}
            showChevron={false}
          />
          <IOSListItem
            icon={<Brain size={16} />}
            iconBg="var(--color-success)"
            title="平均相关度"
            detail={
              <span className="ios-body">
                {Math.round((memories.reduce((s, m) => s + m.score, 0) / memories.length) * 100)}%
              </span>
            }
            showChevron={false}
          />
        </IOSListGroup>

        {/* FAB */}
        <IOSFab icon={<Plus size={24} />} label="添加记忆" onClick={() => toast.info('添加记忆功能开发中')} />

        {/* Delete Dialog */}
        <IOSConfirmDialog
          open={showDeleteDialog}
          onOpenChange={setShowDeleteDialog}
          title="删除记忆"
          description="确定要删除这条记忆吗？此操作不可撤销。"
          onConfirm={handleDelete}
          confirmText="删除"
          danger
        />
      </div>
    </IOSPage>
  );
}
