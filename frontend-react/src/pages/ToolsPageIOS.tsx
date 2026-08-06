import { useState, useMemo } from 'react';
import {
  IOSPage,
  IOSListGroup,
  IOSListItem,
  IOSSearchBar,
  IOSFab,
  IOSSegmentedControl,
  IOSBadge,
  IOSSwitch,
  toast,
} from '../components/ios';
import {
  Cpu,
  Search,
  Plus,
  Wifi,
  Zap,
  Globe,
  Code,
  Database,
  FileText,
  Image,
  BarChart3,
  Lock,
} from 'lucide-react';
import { cn } from '../lib/utils';
import type { ReactElement } from 'react';

type Category = 'all' | 'dev' | 'data' | 'ai' | 'office';
type ToolStatus = 'installed' | 'available' | 'pro';

interface Tool {
  id: string;
  name: string;
  description: string;
  icon: ReactElement;
  iconBg: string;
  category: Category;
  status: ToolStatus;
  installed: boolean;
}

const TOOLS: Tool[] = [
  {
    id: '1',
    name: '代码解释器',
    description: '执行和解释代码片段',
    icon: <Code size={20} className="text-white" />,
    iconBg: '#34C759',
    category: 'dev',
    status: 'installed',
    installed: true,
  },
  {
    id: '2',
    name: '网络搜索',
    description: '实时搜索互联网信息',
    icon: <Wifi size={20} className="text-white" />,
    iconBg: '#007AFF',
    category: 'data',
    status: 'installed',
    installed: true,
  },
  {
    id: '3',
    name: '图片生成',
    description: 'AI 智能图像创作',
    icon: <Image size={20} className="text-white" />,
    iconBg: '#AF52DE',
    category: 'ai',
    status: 'pro',
    installed: false,
  },
  {
    id: '4',
    name: '数据分析',
    description: '可视化数据统计与分析',
    icon: <BarChart3 size={20} className="text-white" />,
    iconBg: '#FF9500',
    category: 'data',
    status: 'available',
    installed: false,
  },
  {
    id: '5',
    name: 'API 测试',
    description: '接口调试与性能测试',
    icon: <Zap size={20} className="text-white" />,
    iconBg: '#FF3B30',
    category: 'dev',
    status: 'available',
    installed: false,
  },
  {
    id: '6',
    name: '文档生成',
    description: '自动生成技术文档',
    icon: <FileText size={20} className="text-white" />,
    iconBg: '#5AC8FA',
    category: 'office',
    status: 'available',
    installed: false,
  },
  {
    id: '7',
    name: '数据库查询',
    description: 'SQL 查询与数据管理',
    icon: <Database size={20} className="text-white" />,
    iconBg: '#8E8E93',
    category: 'data',
    status: 'installed',
    installed: true,
  },
  {
    id: '8',
    name: '代码审查',
    description: '智能代码质量分析',
    icon: <Lock size={20} className="text-white" />,
    iconBg: '#FF2D55',
    category: 'dev',
    status: 'pro',
    installed: false,
  },
];

const CATEGORY_OPTIONS = [
  { value: 'all', label: '全部' },
  { value: 'dev', label: '开发' },
  { value: 'data', label: '数据' },
  { value: 'ai', label: 'AI' },
  { value: 'office', label: '办公' },
];

const categoryLabels: Record<Category, string> = {
  all: '全部',
  dev: '开发',
  data: '数据',
  ai: 'AI',
  office: '办公',
};

const statusVariant: Record<ToolStatus, 'success' | 'warning' | 'info'> = {
  installed: 'success',
  available: 'info',
  pro: 'warning',
};

const statusLabels: Record<ToolStatus, string> = {
  installed: '已安装',
  available: '可用',
  pro: 'Pro',
};

export default function ToolsPageIOS() {
  const [search, setSearch] = useState('');
  const [category, setCategory] = useState<Category>('all');
  const [tools, setTools] = useState<Tool[]>(TOOLS);

  const filteredTools = useMemo(() => {
    return tools.filter((tool) => {
      const matchesSearch =
        tool.name.toLowerCase().includes(search.toLowerCase()) ||
        tool.description.toLowerCase().includes(search.toLowerCase());
      const matchesCategory = category === 'all' || tool.category === category;
      return matchesSearch && matchesCategory;
    });
  }, [tools, search, category]);

  const installedCount = tools.filter((t) => t.installed).length;

  const handleToggle = (id: string) => {
    setTools((prev) =>
      prev.map((tool) => {
        if (tool.id !== id) return tool;
        const newInstalled = !tool.installed;
        if (newInstalled) {
          toast.success(`${tool.name} 已安装`);
        } else {
          toast.error(`${tool.name} 已卸载`);
        }
        return { ...tool, installed: newInstalled };
      })
    );
  };

  const handleInstall = (id: string) => {
    const tool = tools.find((t) => t.id === id);
    if (!tool) return;
    setTools((prev) =>
      prev.map((t) => (t.id === id ? { ...t, installed: true } : t))
    );
    toast.success(`${tool.name} 已安装`);
  };

  return (
    <IOSPage className="pb-24">
      <div className="px-4 pt-6">
        <h1 className="ios-title-1 text-[var(--color-text-primary)]">工具市场</h1>
        <p className="ios-subhead text-[var(--color-text-muted)] mt-1">
          发现和管理您的工作工具
        </p>
      </div>

      <div className="px-4 mt-5">
        <IOSSearchBar
          value={search}
          onChange={setSearch}
          placeholder="搜索工具..."
        />
      </div>

      <div className="px-4 mt-4">
        <IOSSegmentedControl
          options={CATEGORY_OPTIONS}
          value={category}
          onChange={(v) => setCategory(v as Category)}
          className="ios-segment"
        />
      </div>

      <div className="px-4 mt-5">
        <IOSListGroup title={categoryLabels[category]}>
          {filteredTools.map((tool) => (
            <IOSListItem
              key={tool.id}
              icon={tool.icon}
              iconBg={tool.iconBg}
              title={tool.name}
              detail={
                <div className="flex flex-col items-end gap-1.5">
                  <span className="ios-caption text-[var(--color-text-muted)]">
                    {tool.description}
                  </span>
                  <div className="flex items-center gap-2">
                    <IOSBadge variant={statusVariant[tool.status]}>
                      {statusLabels[tool.status]}
                    </IOSBadge>
                    {tool.installed ? (
                      <IOSSwitch
                        checked={tool.installed}
                        onChange={() => handleToggle(tool.id)}
                      />
                    ) : (
                      <button
                        type="button"
                        onClick={() => handleInstall(tool.id)}
                        className={cn(
                          'ios-caption font-semibold px-3 py-1 rounded-full',
                          'bg-[var(--color-accent)] text-white active:opacity-70 transition-opacity'
                        )}
                      >
                        安装
                      </button>
                    )}
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
          <div className="text-center">
            <p className="ios-title-3 text-[var(--color-text-primary)]">{tools.length}</p>
            <p className="ios-caption text-[var(--color-text-muted)]">总工具数</p>
          </div>
          <div className="w-px h-8 bg-[var(--color-border-subtle)]" />
          <div className="text-center">
            <p className="ios-title-3 text-[var(--color-success)]">{installedCount}</p>
            <p className="ios-caption text-[var(--color-text-muted)]">已安装</p>
          </div>
        </div>
      </div>

      <IOSFab
        icon={<Plus size={20} />}
        label="添加工具"
        onClick={() => toast.info('添加工具功能即将上线')}
      />
    </IOSPage>
  );
}
