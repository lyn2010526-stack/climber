import { useMemo, useState } from 'react';
import {
  IOSPage,
  IOSListGroup,
  IOSBadge,
  IOSSegmentedControl,
  toast,
} from '../components/ios';
import { Check, X, FileText, KeyRound, Cpu, Globe, Bot, Shield } from 'lucide-react';
import type { ReactElement } from 'react';

type ApprovalStatus = 'pending' | 'approved' | 'rejected';
type BadgeVariant = 'success' | 'warning' | 'error';

interface ApprovalItem {
  id: number;
  title: string;
  applicant: string;
  time: string;
  icon: ReactElement;
  iconBg: string;
  status: ApprovalStatus;
}

const STATUS_META: Record<ApprovalStatus, { label: string; variant: BadgeVariant }> = {
  pending: { label: '待审批', variant: 'warning' },
  approved: { label: '已通过', variant: 'success' },
  rejected: { label: '已拒绝', variant: 'error' },
};

const FILTER_OPTIONS = [
  { value: 'all', label: '全部' },
  { value: 'pending', label: '待审批' },
  { value: 'approved', label: '已通过' },
  { value: 'rejected', label: '已拒绝' },
];

const INITIAL_APPROVALS: ApprovalItem[] = [
  { id: 1, title: '新建文档权限申请', applicant: '王小明', time: '10 分钟前', icon: <FileText size={16} className="text-white" />, iconBg: '#007AFF', status: 'pending' },
  { id: 2, title: 'API 密钥访问申请', applicant: '李华', time: '32 分钟前', icon: <KeyRound size={16} className="text-white" />, iconBg: '#FF9500', status: 'pending' },
  { id: 3, title: 'GPU 算力资源扩容', applicant: '赵强', time: '1 小时前', icon: <Cpu size={16} className="text-white" />, iconBg: '#AF52DE', status: 'pending' },
  { id: 4, title: '外网发布白名单', applicant: '陈静', time: '2 小时前', icon: <Globe size={16} className="text-white" />, iconBg: '#34C759', status: 'approved' },
  { id: 5, title: '自动化 Agent 部署', applicant: '刘洋', time: '3 小时前', icon: <Bot size={16} className="text-white" />, iconBg: '#5E6AD2', status: 'approved' },
  { id: 6, title: '安全策略变更申请', applicant: '孙丽', time: '昨天', icon: <Shield size={16} className="text-white" />, iconBg: '#FF3B30', status: 'rejected' },
];

export default function ApprovalsPageIOS() {
  const [approvals, setApprovals] = useState<ApprovalItem[]>(INITIAL_APPROVALS);
  const [filter, setFilter] = useState<string>('all');

  const stats = useMemo(() => ({
    pending: approvals.filter((item) => item.status === 'pending').length,
    approved: approvals.filter((item) => item.status === 'approved').length,
    rejected: approvals.filter((item) => item.status === 'rejected').length,
  }), [approvals]);

  const filtered = useMemo(() => {
    if (filter === 'all') return approvals;
    return approvals.filter((item) => item.status === filter);
  }, [approvals, filter]);

  const statCards = [
    { label: '待审批', value: stats.pending, color: 'var(--color-warning)' },
    { label: '已通过', value: stats.approved, color: 'var(--color-success)' },
    { label: '已拒绝', value: stats.rejected, color: 'var(--color-error)' },
  ];

  const handleAction = (item: ApprovalItem, status: ApprovalStatus) => {
    setApprovals((prev) => prev.map((entry) => (entry.id === item.id ? { ...entry, status } : entry)));
    if (status === 'approved') {
      toast.success(`已同意「${item.title}」`);
    } else {
      toast.error(`已拒绝「${item.title}」`);
    }
  };

  return (
    <IOSPage className="pb-24">
      <div className="px-4 pt-6 space-y-5">
        <div>
          <h1 className="ios-title-1 text-[var(--color-text-primary)]">审批中心</h1>
          <p className="ios-subhead text-[var(--color-text-muted)] mt-1">
            集中处理资源与权限申请
          </p>
        </div>

        <div className="flex gap-3">
          {statCards.map((stat) => (
            <div key={stat.label} className="flex-1 ios-card p-3">
              <div className="ios-title-1" style={{ color: stat.color }}>
                {stat.value}
              </div>
              <div className="ios-caption text-[var(--color-text-muted)] mt-0.5">{stat.label}</div>
            </div>
          ))}
        </div>

        <IOSSegmentedControl
          options={FILTER_OPTIONS}
          value={filter}
          onChange={setFilter}
        />

        <IOSListGroup title={`审批列表 (${filtered.length})`}>
          {filtered.length === 0 ? (
            <div className="ios-empty-state">
              <Shield size={40} strokeWidth={1.5} />
              <p>暂无匹配的审批记录</p>
            </div>
          ) : (
            filtered.map((item) => {
              const meta = STATUS_META[item.status];
              return (
                <div
                  key={item.id}
                  className="flex items-center gap-3 px-4 py-3 border-b border-[var(--color-border-subtle)] last:border-b-0"
                >
                  <span
                    className="flex h-9 w-9 items-center justify-center rounded-full shrink-0"
                    style={{ background: item.iconBg }}
                  >
                    {item.icon}
                  </span>
                  <div className="flex-1 min-w-0">
                    <p className="ios-headline text-[var(--color-text-primary)] truncate">{item.title}</p>
                    <div className="flex items-center gap-2 mt-0.5">
                      <span className="ios-caption text-[var(--color-text-muted)]">申请人：{item.applicant}</span>
                      <span className="ios-footnote text-[var(--color-text-muted)]">{item.time}</span>
                    </div>
                  </div>
                  <div className="flex flex-col items-end gap-2 shrink-0">
                    <IOSBadge variant={meta.variant}>{meta.label}</IOSBadge>
                    {item.status === 'pending' && (
                      <div className="flex items-center gap-2">
                        <button
                          type="button"
                          onClick={() => handleAction(item, 'approved')}
                          className="flex h-9 w-9 items-center justify-center rounded-full text-white active:opacity-80 transition-opacity"
                          style={{ background: 'var(--color-success)' }}
                          aria-label="同意"
                        >
                          <Check size={16} />
                        </button>
                        <button
                          type="button"
                          onClick={() => handleAction(item, 'rejected')}
                          className="flex h-9 w-9 items-center justify-center rounded-full text-white active:opacity-80 transition-opacity"
                          style={{ background: 'var(--color-error)' }}
                          aria-label="拒绝"
                        >
                          <X size={16} />
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              );
            })
          )}
        </IOSListGroup>
      </div>
    </IOSPage>
  );
}
