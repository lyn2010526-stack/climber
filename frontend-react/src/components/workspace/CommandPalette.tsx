import { useState, useEffect, useRef, useMemo } from 'react';
import { Search, ArrowRight, FileText, Bot, Workflow, Cpu, Network, Settings } from 'lucide-react';

const iconMap: Record<string, typeof Search> = {
  MessageSquare: Search,
  Bot: Bot,
  Workflow: Workflow,
  Cpu: Cpu,
  Network: Network,
  Settings: Settings,
  FileText: FileText,
  Activity: Cpu,
  BarChart3: Cpu,
  Bell: Search,
  Server: Settings,
  Key: Settings,
  Package: Workflow,
  Clock: Cpu,
  Users: Network,
  History: FileText,
  FlaskConical: Cpu,
  DollarSign: Cpu,
  Puzzle: Workflow,
  Terminal: Settings,
  Sparkles: Bot,
};

interface CommandPaletteProps {
  isOpen: boolean;
  onClose: () => void;
  onNavigate: (page: string) => void;
}

export default function CommandPalette({ isOpen, onClose, onNavigate }: CommandPaletteProps) {
  const [query, setQuery] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLDivElement>(null);
  const keyboardIndexRef = useRef(0);

  const allItems = useMemo(() => [
    { id: 'chat', label: '工作台', icon: 'MessageSquare', keywords: 'home workspace dashboard 对话 工作台', group: '核心' },
    { id: 'factory', label: '自主执行', icon: 'Sparkles', keywords: 'auto agent execute 自主 自动执行', group: '核心' },
    { id: 'cluster', label: '集群协作', icon: 'Network', keywords: 'multi agent team 集群 协作', group: '核心' },
    { id: 'tasks', label: '任务监控', icon: 'Cpu', keywords: 'monitor task running 任务 监控', group: '核心' },
    { id: 'task-history', label: '任务历史', icon: 'History', keywords: 'history past 历史', group: '核心' },
    { id: 'reasoning', label: '推理引擎', icon: 'Activity', keywords: 'reason think 推理', group: '核心' },
    { id: 'reasoning-history', label: '推理历史', icon: 'History', keywords: 'reasoning history 推理历史', group: '核心' },
    { id: 'agents', label: '智能体管理', icon: 'Bot', keywords: 'agent config 智能体 管理', group: '管理' },
    { id: 'workflows', label: '工作流', icon: 'Workflow', keywords: 'workflow dag 工作流', group: '管理' },
    { id: 'crews', label: '团队协作', icon: 'Users', keywords: 'crew team 团队', group: '管理' },
    { id: 'scheduler', label: '定时任务', icon: 'Clock', keywords: 'cron schedule 定时', group: '管理' },
    { id: 'plugins', label: '插件市场', icon: 'Puzzle', keywords: 'plugin marketplace 插件 市场', group: '配置' },
    { id: 'plugin-manage', label: '插件管理', icon: 'Package', keywords: 'plugin manage installed 插件 管理', group: '配置' },
    { id: 'skills', label: '技能中心', icon: 'Package', keywords: 'skill tool 技能', group: '配置' },
    { id: 'notifications', label: '通知中心', icon: 'Bell', keywords: 'notification alert 通知', group: '配置' },
    { id: 'doctor', label: '系统诊断', icon: 'Activity', keywords: 'health debug 诊断 系统', group: '配置' },
    { id: 'mcp', label: 'MCP 市场', icon: 'Server', keywords: 'mcp protocol tool MCP', group: '配置' },
    { id: 'apikeys', label: 'API 密钥', icon: 'Key', keywords: 'api key secret API 密钥', group: '配置' },
    { id: 'stats', label: '数据统计', icon: 'BarChart3', keywords: 'stats analytics chart 统计 数据', group: '配置' },
    { id: 'traces', label: '链路追踪', icon: 'Activity', keywords: 'trace debug 追踪 链路', group: '配置' },
    { id: 'eval', label: '效果评估', icon: 'FlaskConical', keywords: 'eval benchmark 评估 效果', group: '配置' },
    { id: 'cost', label: '成本控制', icon: 'DollarSign', keywords: 'cost billing token 成本', group: '配置' },
    { id: 'settings', label: '系统设置', icon: 'Settings', keywords: 'settings config preference 设置', group: '配置' },
    { id: 'terminal', label: '终端沙箱', icon: 'Terminal', keywords: 'terminal shell 终端', group: '配置' },
  ], []);

  const filtered = useMemo(() => {
    if (!query.trim()) return allItems.slice(0, 8);
    const q = query.toLowerCase();
    return allItems.filter(item =>
      item.label.toLowerCase().includes(q) ||
      item.keywords.toLowerCase().includes(q) ||
      item.group.toLowerCase().includes(q)
    );
  }, [query, allItems]);

  useEffect(() => {
    setSelectedIndex(0);
  }, [query]);

  useEffect(() => {
    if (isOpen && inputRef.current) {
      inputRef.current.focus();
    }
  }, [isOpen]);

  useEffect(() => {
    if (!isOpen) {
      setQuery('');
      setSelectedIndex(0);
    }
  }, [isOpen]);

  useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      } else if (e.key === 'ArrowDown') {
        e.preventDefault();
        setSelectedIndex(i => {
          keyboardIndexRef.current = Math.min(i + 1, filtered.length - 1);
          return keyboardIndexRef.current;
        });
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        setSelectedIndex(i => {
          keyboardIndexRef.current = Math.max(i - 1, 0);
          return keyboardIndexRef.current;
        });
      } else if (e.key === 'Enter' && filtered[selectedIndex]) {
        onNavigate(filtered[selectedIndex].id);
        onClose();
      }
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, filtered, selectedIndex, onClose, onNavigate]);

  if (!isOpen) return null;

  const grouped = filtered.reduce<Record<string, typeof allItems>>((acc, item) => {
    if (!acc[item.group]) acc[item.group] = [];
    (acc[item.group] ||= []).push(item);
    return acc;
  }, {});

  return (
    <div className="fixed inset-0 z-[100]" onClick={onClose} role="dialog" aria-modal="true" aria-label="命令面板">
      <div className="absolute inset-0" style={{ backgroundColor: 'rgba(0,0,0,0.6)', backdropFilter: 'blur(4px)' }} />
      <div
        className="relative mx-auto mt-[20vh] w-full max-w-[640px] max-h-[480px] flex flex-col rounded-2xl overflow-hidden"
        style={{
          backgroundColor: 'var(--color-bg-surface-1)',
          border: '1px solid var(--color-border-default)',
          boxShadow: '0 25px 50px -12px rgba(0,0,0,0.5)',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Input */}
        <div className="flex items-center gap-3 px-4 py-3" style={{ borderBottom: '1px solid var(--color-border-subtle)' }}>
          <Search size={18} style={{ color: 'var(--color-text-muted)', flexShrink: 0 }} />
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="搜索页面、功能..."
            className="flex-1 bg-transparent text-sm outline-none"
            style={{ color: 'var(--color-text-primary)' }}
          />
          <kbd className="text-[10px] px-1.5 py-0.5 rounded-md font-mono" style={{
            backgroundColor: 'var(--color-bg-surface-3)',
            color: 'var(--color-text-muted)',
            border: '1px solid var(--color-border-subtle)'
          }}>ESC</kbd>
        </div>

        {/* Results */}
        <div ref={listRef} className="flex-1 overflow-y-auto p-2">
          {filtered.length === 0 ? (
            <div className="py-12 text-center" style={{ color: 'var(--color-text-muted)' }}>
              <Search size={32} className="mx-auto mb-3 opacity-50" />
              <p className="text-sm">未找到 "{query}"</p>
            </div>
          ) : (
            Object.entries(grouped).map(([group, items]) => (
              <div key={group} className="mb-2">
                {filtered.length > 3 && (
                  <div className="px-3 py-1.5 text-[10px] font-semibold uppercase tracking-wider" style={{
                    color: 'var(--color-text-muted)'
                  }}>
                    {group}
                  </div>
                )}
                <div className="space-y-0.5">
                  {items.map((item) => {
                    const globalIndex = filtered.indexOf(item);
                    const IconComponent = iconMap[item.icon] || Search;
                    return (
                      <button
                        key={item.id}
                        onClick={() => { onNavigate(item.id); onClose(); }}
                        className="w-full flex items-center gap-3 px-3 py-2.5 rounded-2xl text-sm text-left transition-all duration-150"
                        style={{
                          backgroundColor: globalIndex === selectedIndex ? 'var(--color-bg-surface-2)' : 'transparent',
                          color: globalIndex === selectedIndex ? 'var(--color-text-primary)' : 'var(--color-text-secondary)',
                        }}
                        onMouseEnter={() => setSelectedIndex(globalIndex)}
                        onMouseLeave={() => setSelectedIndex(keyboardIndexRef.current)}
                      >
                        <div className="p-1.5 rounded-lg" style={{
                          backgroundColor: globalIndex === selectedIndex ? 'var(--color-accent-subtle)' : 'var(--color-bg-surface-3)',
                          color: globalIndex === selectedIndex ? 'var(--color-accent)' : 'var(--color-text-muted)',
                        }}>
                          <IconComponent size={14} />
                        </div>
                        <span className="flex-1">{item.label}</span>
                        {globalIndex === selectedIndex && (
                          <ArrowRight size={14} style={{ color: 'var(--color-accent)' }} />
                        )}
                      </button>
                    );
                  })}
                </div>
              </div>
            ))
          )}
        </div>

        {/* Footer hint */}
        <div className="px-4 py-2 flex items-center gap-4 text-[10px]" style={{
          borderTop: '1px solid var(--color-border-subtle)',
          color: 'var(--color-text-muted)',
          backgroundColor: 'var(--color-bg-surface-2)',
        }}>
          <span className="flex items-center gap-1">
            <kbd className="px-1 py-0.5 rounded font-mono" style={{ border: '1px solid var(--color-border-subtle)' }}>↑↓</kbd> 导航
          </span>
          <span className="flex items-center gap-1">
            <kbd className="px-1 py-0.5 rounded font-mono" style={{ border: '1px solid var(--color-border-subtle)' }}>↵</kbd> 打开
          </span>
          <span className="flex items-center gap-1">
            <kbd className="px-1 py-0.5 rounded font-mono" style={{ border: '1px solid var(--color-border-subtle)' }}>esc</kbd> 关闭
          </span>
        </div>
      </div>
    </div>
  );
}
