import { useState, useMemo } from 'react';
import {
  IOSPage,
  IOSListGroup,
  IOSListItem,
  IOSSearchBar,
  IOSFab,
  IOSBadge,
  IOSConfirmDialog,
  toast,
} from '../components/ios';
import {
  GitBranch,
  Play,
  Pause,
  Plus,
  Clock,
  CheckCircle2,
  XCircle,
  AlertCircle,
  Zap,
  ArrowRight,
} from 'lucide-react';
import { cn } from '../lib/utils';
import type { ReactElement } from 'react';

type WorkflowStatus = 'running' | 'success' | 'failed';

interface Workflow {
  id: string;
  name: string;
  description: string;
  status: WorkflowStatus;
  lastRun: string;
  icon: ReactElement;
  iconBg: string;
}

const WORKFLOWS: Workflow[] = [
  {
    id: '1',
    name: '代码审查流水线',
    description: '自动检查代码质量和规范',
    status: 'running',
    lastRun: '2 分钟前',
    icon: <GitBranch size={20} className="text-white" />,
    iconBg: '#007AFF',
  },
  {
    id: '2',
    name: '自动化测试',
    description: '运行单元测试和集成测试',
    status: 'success',
    lastRun: '15 分钟前',
    icon: <CheckCircle2 size={20} className="text-white" />,
    iconBg: '#34C759',
  },
  {
    id: '3',
    name: '文档生成',
    description: '从代码注释自动生成文档',
    status: 'success',
    lastRun: '1 小时前',
    icon: <Zap size={20} className="text-white" />,
    iconBg: '#AF52DE',
  },
  {
    id: '4',
    name: '数据处理 ETL',
    description: '数据抽取、转换和加载',
    status: 'failed',
    lastRun: '3 小时前',
    icon: <AlertCircle size={20} className="text-white" />,
    iconBg: '#FF3B30',
  },
  {
    id: '5',
    name: '模型训练',
    description: '训练机器学习模型',
    status: 'running',
    lastRun: '30 分钟前',
    icon: <Zap size={20} className="text-white" />,
    iconBg: '#FF9500',
  },
  {
    id: '6',
    name: 'CI/CD 部署',
    description: '持续集成和持续部署',
    status: 'success',
    lastRun: '2 小时前',
    icon: <ArrowRight size={20} className="text-white" />,
    iconBg: '#5AC8FA',
  },
];

const STATUS_OPTIONS = [
  { value: 'all', label: '全部' },
  { value: 'running', label: '运行中' },
  { value: 'success', label: '已完成' },
  { value: 'failed', label: '失败' },
];

const statusLabels: Record<WorkflowStatus, string> = {
  running: '运行中',
  success: '已完成',
  failed: '失败',
};

const statusVariant: Record<WorkflowStatus, 'info' | 'success' | 'error'> = {
  running: 'info',
  success: 'success',
  failed: 'error',
};

function StatusIcon({ status }: { status: WorkflowStatus }) {
  if (status === 'running') {
    return (
      <div className="animate-spin">
        <Clock size={16} className="text-[var(--color-info)]" />
      </div>
    );
  }
  if (status === 'success') {
    return <CheckCircle2 size={16} className="text-[var(--color-success)]" />;
  }
  return <XCircle size={16} className="text-[var(--color-error)]" />;
}

export default function WorkflowsPageIOS() {
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [showCreateDialog, setShowCreateDialog] = useState(false);

  const filteredWorkflows = useMemo(() => {
    return WORKFLOWS.filter((workflow) => {
      const matchesSearch =
        workflow.name.toLowerCase().includes(search.toLowerCase()) ||
        workflow.description.toLowerCase().includes(search.toLowerCase());
      const matchesStatus = statusFilter === 'all' || workflow.status === statusFilter;
      return matchesSearch && matchesStatus;
    });
  }, [search, statusFilter]);

  const runningCount = WORKFLOWS.filter((w) => w.status === 'running').length;
  const successCount = WORKFLOWS.filter((w) => w.status === 'success').length;
  const failedCount = WORKFLOWS.filter((w) => w.status === 'failed').length;

  const handleWorkflowClick = (workflow: Workflow) => {
    toast.info(`${workflow.name} - ${statusLabels[workflow.status]}`);
  };

  return (
    <IOSPage className="pb-24">
      <div className="px-4 pt-6">
        <h1 className="ios-title-1 text-[var(--color-text-primary)]">工作流</h1>
        <p className="ios-subhead text-[var(--color-text-muted)] mt-1">
          管理和监控您的自动化工作流
        </p>
      </div>

      <div className="px-4 mt-5 grid grid-cols-3 gap-3">
        <div className="ios-card p-3 text-center">
          <div className="flex items-center justify-center gap-1.5">
            <Play size={14} className="text-[var(--color-info)]" />
            <span className="ios-title-2 text-[var(--color-info)]">{runningCount}</span>
          </div>
          <p className="ios-caption text-[var(--color-text-muted)] mt-1">运行中</p>
        </div>
        <div className="ios-card p-3 text-center">
          <div className="flex items-center justify-center gap-1.5">
            <CheckCircle2 size={14} className="text-[var(--color-success)]" />
            <span className="ios-title-2 text-[var(--color-success)]">{successCount}</span>
          </div>
          <p className="ios-caption text-[var(--color-text-muted)] mt-1">成功</p>
        </div>
        <div className="ios-card p-3 text-center">
          <div className="flex items-center justify-center gap-1.5">
            <XCircle size={14} className="text-[var(--color-error)]" />
            <span className="ios-title-2 text-[var(--color-error)]">{failedCount}</span>
          </div>
          <p className="ios-caption text-[var(--color-text-muted)] mt-1">失败</p>
        </div>
      </div>

      <div className="px-4 mt-5">
        <IOSSearchBar
          value={search}
          onChange={setSearch}
          placeholder="搜索工作流..."
        />
      </div>

      <div className="px-4 mt-4">
        <div className="ios-segment">
          {STATUS_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              type="button"
              onClick={() => setStatusFilter(opt.value)}
              className={cn(
                'ios-segment-item',
                statusFilter === opt.value && 'active'
              )}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>

      <div className="px-4 mt-5">
        {filteredWorkflows.length > 0 ? (
          <IOSListGroup title="工作流列表">
            {filteredWorkflows.map((workflow) => (
              <IOSListItem
                key={workflow.id}
                icon={workflow.icon}
                iconBg={workflow.iconBg}
                title={workflow.name}
                detail={
                  <div className="flex flex-col items-end gap-1">
                    <span className="ios-caption text-[var(--color-text-muted)]">
                      {workflow.description}
                    </span>
                    <div className="flex items-center gap-2">
                      <IOSBadge variant={statusVariant[workflow.status]}>
                        <span className="flex items-center gap-1">
                          <StatusIcon status={workflow.status} />
                          {statusLabels[workflow.status]}
                        </span>
                      </IOSBadge>
                      <span className="ios-caption text-[var(--color-text-muted)] flex items-center gap-0.5">
                        <Clock size={10} />
                        {workflow.lastRun}
                      </span>
                    </div>
                  </div>
                }
                onClick={() => handleWorkflowClick(workflow)}
              />
            ))}
          </IOSListGroup>
        ) : (
          <div className="ios-empty-state py-16">
            <div className="flex flex-col items-center">
              <div className="w-16 h-16 rounded-full bg-[var(--color-bg-surface-2)] flex items-center justify-center mb-4">
                <GitBranch size={28} className="text-[var(--color-text-muted)]" />
              </div>
              <p className="ios-headline text-[var(--color-text-primary)]">未找到工作流</p>
              <p className="ios-caption text-[var(--color-text-muted)] mt-1">
                尝试调整搜索条件或筛选状态
              </p>
            </div>
          </div>
        )}
      </div>

      <IOSFab
        icon={<Plus size={20} />}
        label="创建工作流"
        onClick={() => setShowCreateDialog(true)}
      />

      <IOSConfirmDialog
        open={showCreateDialog}
        onOpenChange={setShowCreateDialog}
        title="创建工作流"
        description="创建新的自动化工作流，开始您的效率之旅"
        onConfirm={() => {
          setShowCreateDialog(false);
          toast.success('工作流创建成功');
        }}
        confirmText="创建"
        cancelText="取消"
      />
    </IOSPage>
  );
}
