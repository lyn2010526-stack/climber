import { useState } from 'react';
import {
  IOSPage,
  IOSCard,
  IOSListGroup,
  IOSBadge,
  IOSSwitch,
  IOSFab,
  toast,
} from '../components/ios';
import { Plus, Minus, Factory, Zap, Cpu, Boxes, PackageCheck } from 'lucide-react';
import type { ReactElement } from 'react';

type PipelineStatus = 'running' | 'paused' | 'completed';
type BadgeVariant = 'success' | 'warning' | 'info';

interface Pipeline {
  id: number;
  name: string;
  output: string;
  progress: number;
  status: PipelineStatus;
  icon: ReactElement;
  iconBg: string;
}

const STATUS_META: Record<PipelineStatus, { label: string; variant: BadgeVariant }> = {
  running: { label: '运行', variant: 'success' },
  paused: { label: '暂停', variant: 'warning' },
  completed: { label: '完成', variant: 'info' },
};

const PROGRESS_COLOR: Record<PipelineStatus, string> = {
  running: 'var(--color-accent)',
  paused: 'var(--color-warning)',
  completed: 'var(--color-success)',
};

const PIPELINES: Pipeline[] = [
  { id: 1, name: '组件装配流水线', output: '1280 件/时', progress: 72, status: 'running', icon: <Factory size={16} className="text-white" />, iconBg: '#007AFF' },
  { id: 2, name: '数据清洗流水线', output: '860 条/分', progress: 45, status: 'running', icon: <Zap size={16} className="text-white" />, iconBg: '#FF9500' },
  { id: 3, name: '模型推理流水线', output: '320 次/时', progress: 90, status: 'paused', icon: <Cpu size={16} className="text-white" />, iconBg: '#AF52DE' },
  { id: 4, name: '包装质检流水线', output: '640 件/时', progress: 100, status: 'completed', icon: <Boxes size={16} className="text-white" />, iconBg: '#34C759' },
  { id: 5, name: '成品发货流水线', output: '512 件/时', progress: 100, status: 'completed', icon: <PackageCheck size={16} className="text-white" />, iconBg: '#5E6AD2' },
];

export default function FactoryModePageIOS() {
  const [productionMode, setProductionMode] = useState(true);
  const [autoStart, setAutoStart] = useState(true);
  const [retryOnFailure, setRetryOnFailure] = useState(true);
  const [concurrency, setConcurrency] = useState(4);

  const decreaseConcurrency = () => {
    setConcurrency((prev) => Math.max(1, prev - 1));
  };

  const increaseConcurrency = () => {
    setConcurrency((prev) => Math.min(32, prev + 1));
  };

  return (
    <IOSPage className="pb-24">
      <div className="px-4 pt-6 space-y-5">
        <div>
          <h1 className="ios-title-1 text-[var(--color-text-primary)]">工厂模式</h1>
          <p className="ios-subhead text-[var(--color-text-muted)] mt-1">
            批量生产与自动化流水线
          </p>
        </div>

        <IOSCard className="p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="ios-caption text-[var(--color-text-muted)]">当前模式</p>
              <div className="flex items-center gap-2 mt-1">
                <p className="ios-headline text-[var(--color-text-primary)]">
                  {productionMode ? '生产模式' : '演示模式'}
                </p>
                <IOSBadge variant={productionMode ? 'success' : 'warning'}>
                  {productionMode ? '批量生产' : '模拟运行'}
                </IOSBadge>
              </div>
            </div>
            <IOSSwitch checked={productionMode} onChange={setProductionMode} />
          </div>
        </IOSCard>

        <IOSListGroup title="生产流水线">
          {PIPELINES.map((pipeline) => {
            const meta = STATUS_META[pipeline.status];
            return (
              <div
                key={pipeline.id}
                className="px-4 py-3 border-b border-[var(--color-border-subtle)] last:border-b-0"
              >
                <div className="flex items-center gap-3">
                  <span
                    className="flex h-9 w-9 items-center justify-center rounded-full shrink-0"
                    style={{ background: pipeline.iconBg }}
                  >
                    {pipeline.icon}
                  </span>
                  <div className="flex-1 min-w-0">
                    <p className="ios-headline text-[var(--color-text-primary)] truncate">{pipeline.name}</p>
                    <p className="ios-caption text-[var(--color-text-muted)] mt-0.5">{pipeline.output}</p>
                  </div>
                  <IOSBadge variant={meta.variant} className="shrink-0">{meta.label}</IOSBadge>
                </div>
                <div className="flex items-center gap-3 mt-3">
                  <div className="flex-1 h-1.5 rounded-full bg-[var(--color-bg-surface-3)] overflow-hidden">
                    <div
                      className="h-full rounded-full transition-all duration-300"
                      style={{ width: `${pipeline.progress}%`, background: PROGRESS_COLOR[pipeline.status] }}
                    />
                  </div>
                  <span className="ios-footnote text-[var(--color-text-muted)] shrink-0">{pipeline.progress}%</span>
                </div>
              </div>
            );
          })}
        </IOSListGroup>

        <IOSListGroup title="设置">
          <div className="flex items-center justify-between px-4 py-3 border-b border-[var(--color-border-subtle)]">
            <span className="ios-headline text-[var(--color-text-primary)]">自动启动</span>
            <IOSSwitch checked={autoStart} onChange={setAutoStart} />
          </div>
          <div className="flex items-center justify-between px-4 py-3 border-b border-[var(--color-border-subtle)]">
            <span className="ios-headline text-[var(--color-text-primary)]">并发数</span>
            <div className="flex items-center gap-4">
              <button
                type="button"
                onClick={decreaseConcurrency}
                className="flex h-8 w-8 items-center justify-center rounded-full bg-[var(--color-bg-surface-3)] text-[var(--color-text-primary)] active:opacity-70 transition-opacity"
                aria-label="减少并发数"
              >
                <Minus size={14} />
              </button>
              <span className="ios-subhead text-[var(--color-text-primary)] min-w-[2ch] text-center">
                {concurrency}
              </span>
              <button
                type="button"
                onClick={increaseConcurrency}
                className="flex h-8 w-8 items-center justify-center rounded-full bg-[var(--color-bg-surface-3)] text-[var(--color-text-primary)] active:opacity-70 transition-opacity"
                aria-label="增加并发数"
              >
                <Plus size={14} />
              </button>
            </div>
          </div>
          <div className="flex items-center justify-between px-4 py-3">
            <span className="ios-headline text-[var(--color-text-primary)]">失败重试</span>
            <IOSSwitch checked={retryOnFailure} onChange={setRetryOnFailure} />
          </div>
        </IOSListGroup>
      </div>

      <IOSFab
        icon={<Plus size={20} />}
        label="新建流水线"
        onClick={() => toast.info('新建流水线功能开发中')}
      />
    </IOSPage>
  );
}
