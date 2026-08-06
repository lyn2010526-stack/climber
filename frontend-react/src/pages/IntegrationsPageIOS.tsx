import { useState, useMemo } from 'react';
import {
  IOSPage,
  IOSListGroup,
  IOSListItem,
  IOSSearchBar,
  IOSSwitch,
  IOSSegmentedControl,
  IOSBadge,
  toast,
} from '../components/ios';
import {
  Github,
  GitBranch,
  Database,
  MessageSquare,
  BarChart3,
  Cloud,
  Calendar,
  Webhook,
  Plug,
} from 'lucide-react';
import { cn } from '../lib/utils';
import type { ReactElement } from 'react';

type Category = 'all' | 'dev' | 'team' | 'data' | 'ai';

interface Integration {
  id: string;
  name: string;
  description: string;
  icon: ReactElement;
  iconBg: string;
  category: Category;
  connected: boolean;
}

const INITIAL_INTEGRATIONS: Integration[] = [
  {
    id: '1',
    name: 'GitHub',
    description: '代码托管与版本管理',
    icon: <Github size={20} className="text-white" />,
    iconBg: '#333333',
    category: 'dev',
    connected: true,
  },
  {
    id: '2',
    name: 'Slack',
    description: '团队即时通讯',
    icon: <MessageSquare size={20} className="text-white" />,
    iconBg: '#AF52DE',
    category: 'team',
    connected: false,
  },
  {
    id: '3',
    name: 'Notion',
    description: '知识库与文档协作',
    icon: <Calendar size={20} className="text-white" />,
    iconBg: '#8E8E93',
    category: 'team',
    connected: true,
  },
  {
    id: '4',
    name: 'Jira',
    description: '项目管理与工单追踪',
    icon: <GitBranch size={20} className="text-white" />,
    iconBg: '#007AFF',
    category: 'dev',
    connected: false,
  },
  {
    id: '5',
    name: 'PostgreSQL',
    description: '关系型数据库连接',
    icon: <Database size={20} className="text-white" />,
    iconBg: '#34C759',
    category: 'data',
    connected: true,
  },
  {
    id: '6',
    name: 'Webhook',
    description: '事件回调与自动化',
    icon: <Webhook size={20} className="text-white" />,
    iconBg: '#FF9500',
    category: 'dev',
    connected: false,
  },
  {
    id: '7',
    name: 'Google Drive',
    description: '云端文件存储',
    icon: <Cloud size={20} className="text-white" />,
    iconBg: '#FF3B30',
    category: 'data',
    connected: false,
  },
  {
    id: '8',
    name: 'Zapier',
    description: '自动化工作流连接',
    icon: <BarChart3 size={20} className="text-white" />,
    iconBg: '#5AC8FA',
    category: 'ai',
    connected: false,
  },
];

const CATEGORY_OPTIONS = [
  { value: 'all', label: '全部' },
  { value: 'dev', label: '开发' },
  { value: 'team', label: '协作' },
  { value: 'data', label: '数据' },
  { value: 'ai', label: 'AI' },
];

export default function IntegrationsPageIOS() {
  const [search, setSearch] = useState('');
  const [category, setCategory] = useState<Category>('all');
  const [integrations, setIntegrations] = useState<Integration[]>(
    INITIAL_INTEGRATIONS
  );

  const filtered = useMemo(() => {
    return integrations.filter((item) => {
      const matchesSearch =
        item.name.toLowerCase().includes(search.toLowerCase()) ||
        item.description.toLowerCase().includes(search.toLowerCase());
      const matchesCategory = category === 'all' || item.category === category;
      return matchesSearch && matchesCategory;
    });
  }, [integrations, search, category]);

  const connectedCount = integrations.filter((i) => i.connected).length;

  const handleToggle = (id: string) => {
    setIntegrations((prev) =>
      prev.map((item) => {
        if (item.id !== id) return item;
        const connected = !item.connected;
        if (connected) {
          toast.success(`${item.name} 已连接`);
        } else {
          toast.error(`${item.name} 已断开`);
        }
        return { ...item, connected };
      })
    );
  };

  return (
    <IOSPage className="pb-24">
      <div className="px-4 pt-6">
        <h1 className="ios-title-1 text-[var(--color-text-primary)]">应用集成</h1>
        <p className="ios-subhead text-[var(--color-text-muted)] mt-1">
          连接外部服务，扩展智能体能力
        </p>
      </div>

      <div className="px-4 mt-5">
        <IOSSegmentedControl
          options={CATEGORY_OPTIONS}
          value={category}
          onChange={(v) => setCategory(v as Category)}
          className="ios-segment"
        />
      </div>

      <div className="px-4 mt-4">
        <IOSSearchBar
          value={search}
          onChange={setSearch}
          placeholder="搜索集成..."
        />
      </div>

      <div className="px-4 mt-5">
        <IOSListGroup title="可用集成">
          {filtered.map((item) => (
            <IOSListItem
              key={item.id}
              icon={item.icon}
              iconBg={item.iconBg}
              title={item.name}
              detail={
                <div className="flex flex-col items-end gap-1.5">
                  <span className="ios-caption text-[var(--color-text-muted)]">
                    {item.description}
                  </span>
                  <div className="flex items-center gap-2">
                    <IOSBadge
                      variant={item.connected ? 'success' : 'default'}
                      className={cn(!item.connected && 'opacity-60')}
                    >
                      {item.connected ? '已连接' : '未连接'}
                    </IOSBadge>
                    <IOSSwitch
                      checked={item.connected}
                      onChange={() => handleToggle(item.id)}
                    />
                  </div>
                </div>
              }
              showChevron={false}
            />
          ))}
        </IOSListGroup>
      </div>

      <div className="px-4 mt-6">
        <div className="flex items-center justify-between px-4 py-3 rounded-xl bg-[var(--color-bg-surface-2)] border border-[var(--color-border-subtle)]">
          <div className="flex items-center gap-2">
            <Plug size={16} className="text-[var(--color-accent)]" />
            <span className="ios-body text-[var(--color-text-muted)]">
              已连接
            </span>
          </div>
          <span className="ios-title-3 text-[var(--color-success)]">
            {connectedCount}/8
          </span>
        </div>
      </div>
    </IOSPage>
  );
}
