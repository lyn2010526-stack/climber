import { useMemo, useState } from 'react';
import {
  IOSPage,
  IOSListGroup,
  IOSListItem,
  IOSBadge,
  IOSSegmentedControl,
  IOSStaggerList,
  IOSStaggerItem,
} from '../components/ios';
import {
  ShieldCheck,
  KeyRound,
  Edit3,
  AlertTriangle,
  Zap,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react';
import { cn } from '../lib/utils';
import type { ReactElement } from 'react';

type LogCategory = 'all' | 'auth' | 'action' | 'system' | 'error';
type LogStatus = 'success' | 'warning' | 'error';

interface LogEntry {
  id: number;
  category: Exclude<LogCategory, 'all'>;
  icon: ReactElement;
  iconBg: string;
  description: string;
  operator: string;
  time: string;
  status: LogStatus;
}

const CATEGORY_OPTIONS = [
  { value: 'all', label: '全部' },
  { value: 'auth', label: '认证' },
  { value: 'action', label: '操作' },
  { value: 'system', label: '系统' },
  { value: 'error', label: '错误' },
];

const LOGS: LogEntry[] = [
  { id: 1, category: 'auth', icon: <KeyRound size={16} className="text-white" />, iconBg: '#FF9500', description: '用户登录成功', operator: 'admin', time: '09:42:15', status: 'success' },
  { id: 2, category: 'action', icon: <Edit3 size={16} className="text-white" />, iconBg: '#007AFF', description: '修改 Agent 配置', operator: 'zhangsan', time: '09:35:02', status: 'success' },
  { id: 3, category: 'system', icon: <Zap size={16} className="text-white" />, iconBg: '#34C759', description: '工作流调度启动', operator: 'system', time: '09:20:47', status: 'success' },
  { id: 4, category: 'error', icon: <AlertTriangle size={16} className="text-white" />, iconBg: '#FF3B30', description: 'API 调用超时', operator: 'gateway', time: '08:58:11', status: 'error' },
  { id: 5, category: 'auth', icon: <ShieldCheck size={16} className="text-white" />, iconBg: '#34C759', description: '权限变更审核通过', operator: 'lisi', time: '08:47:33', status: 'success' },
  { id: 6, category: 'system', icon: <Zap size={16} className="text-white" />, iconBg: '#AF52DE', description: '模型热更新完成', operator: 'system', time: '08:30:19', status: 'success' },
  { id: 7, category: 'error', icon: <AlertTriangle size={16} className="text-white" />, iconBg: '#FF3B30', description: '磁盘空间告警', operator: 'monitor', time: '07:52:44', status: 'warning' },
  { id: 8, category: 'action', icon: <Edit3 size={16} className="text-white" />, iconBg: '#007AFF', description: '删除测试数据集', operator: 'zhangsan', time: '07:21:08', status: 'warning' },
  { id: 9, category: 'auth', icon: <KeyRound size={16} className="text-white" />, iconBg: '#FF9500', description: '重置用户密码', operator: 'admin', time: '06:55:30', status: 'success' },
  { id: 10, category: 'system', icon: <ShieldCheck size={16} className="text-white" />, iconBg: '#34C759', description: '安全扫描完成', operator: 'system', time: '06:12:56', status: 'success' },
];

const statusVariant: Record<LogStatus, 'success' | 'warning' | 'error'> = {
  success: 'success',
  warning: 'warning',
  error: 'error',
};

const statusLabel: Record<LogStatus, string> = {
  success: '成功',
  warning: '警告',
  error: '失败',
};

const PAGE_SIZE = 5;

export default function AuditLogPageIOS() {
  const [category, setCategory] = useState<LogCategory>('all');
  const [page, setPage] = useState(0);

  const filteredLogs = useMemo(() => {
    if (category === 'all') return LOGS;
    return LOGS.filter((log) => log.category === category);
  }, [category]);

  const totalPages = Math.max(1, Math.ceil(filteredLogs.length / PAGE_SIZE));
  const safePage = Math.min(page, totalPages - 1);
  const pageLogs = filteredLogs.slice(safePage * PAGE_SIZE, safePage * PAGE_SIZE + PAGE_SIZE);

  const handleCategoryChange = (v: string) => {
    setCategory(v as LogCategory);
    setPage(0);
  };

  return (
    <IOSPage className="pb-24">
      <IOSStaggerList className="px-4 pt-6 space-y-5">
        <IOSStaggerItem>
          <h1 className="ios-title-1 text-[var(--color-text-primary)]">审计日志</h1>
          <p className="ios-subhead text-[var(--color-text-muted)] mt-1">安全与操作记录</p>
        </IOSStaggerItem>

        <IOSStaggerItem>
          <IOSSegmentedControl
            options={CATEGORY_OPTIONS}
            value={category}
            onChange={handleCategoryChange}
          />
        </IOSStaggerItem>

        <IOSStaggerItem>
          <IOSListGroup title={`共 ${filteredLogs.length} 条记录`}>
            {pageLogs.map((log) => (
              <IOSListItem
                key={log.id}
                icon={log.icon}
                iconBg={log.iconBg}
                title={log.description}
                showChevron={false}
                detail={
                  <div className="flex flex-col items-end gap-0.5">
                    <IOSBadge variant={statusVariant[log.status]}>{statusLabel[log.status]}</IOSBadge>
                    <span className="ios-caption text-[var(--color-text-muted)]">{log.operator}</span>
                    <span className="ios-footnote text-[var(--color-text-muted)]">{log.time}</span>
                  </div>
                }
              />
            ))}
          </IOSListGroup>
        </IOSStaggerItem>

        <IOSStaggerItem>
          <div className="flex items-center justify-center gap-4 py-2">
            <button
              type="button"
              onClick={() => setPage(Math.max(0, safePage - 1))}
              disabled={safePage === 0}
              className={cn(
                'flex items-center gap-1 px-3 py-1.5 rounded-lg ios-caption font-medium',
                'bg-[var(--color-bg-surface-2)] text-[var(--color-text-primary)] active:opacity-70 transition-opacity',
                safePage === 0 && 'opacity-40 pointer-events-none'
              )}
            >
              <ChevronLeft size={14} />
              上一页
            </button>
            <span className="ios-caption text-[var(--color-text-muted)]">
              第 {safePage + 1} / {totalPages} 页
            </span>
            <button
              type="button"
              onClick={() => setPage(Math.min(totalPages - 1, safePage + 1))}
              disabled={safePage >= totalPages - 1}
              className={cn(
                'flex items-center gap-1 px-3 py-1.5 rounded-lg ios-caption font-medium',
                'bg-[var(--color-bg-surface-2)] text-[var(--color-text-primary)] active:opacity-70 transition-opacity',
                safePage >= totalPages - 1 && 'opacity-40 pointer-events-none'
              )}
            >
              下一页
              <ChevronRight size={14} />
            </button>
          </div>
        </IOSStaggerItem>
      </IOSStaggerList>
    </IOSPage>
  );
}
