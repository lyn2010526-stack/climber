import { useEffect, useState } from 'react';
import {
  IOSPage,
  IOSListGroup,
  IOSListItem,
  IOSFab,
  IOSBadge,
  IOSConfirmDialog,
  IOSStaggerList,
  IOSStaggerItem,
  toast,
} from '../components/ios';
import {
  Wrench,
  Code,
  MessageSquare,
  ListChecks,
  RotateCcw,
  Plus,
  RefreshCw,
} from 'lucide-react';
import { cn } from '../lib/utils';
import type { ReactElement } from 'react';

interface EvalItem {
  id: number;
  name: string;
  score: number;
  status: 'pass' | 'improve';
  time: string;
  icon: ReactElement;
  iconBg: string;
}

const EVAL_ITEMS: EvalItem[] = [
  { id: 1, name: '工具调用', score: 92, status: 'pass', time: '10 分钟前', icon: <Wrench size={16} className="text-white" />, iconBg: '#007AFF' },
  { id: 2, name: '代码生成', score: 85, status: 'pass', time: '1 小时前', icon: <Code size={16} className="text-white" />, iconBg: '#34C759' },
  { id: 3, name: '对话质量', score: 78, status: 'improve', time: '3 小时前', icon: <MessageSquare size={16} className="text-white" />, iconBg: '#AF52DE' },
  { id: 4, name: '任务规划', score: 88, status: 'pass', time: '昨天', icon: <ListChecks size={16} className="text-white" />, iconBg: '#FF9500' },
  { id: 5, name: '错误恢复', score: 64, status: 'improve', time: '2 天前', icon: <RotateCcw size={16} className="text-white" />, iconBg: '#FF3B30' },
];

const STATS = [
  { label: '评测总数', value: '128' },
  { label: '平均分', value: '84.6' },
  { label: '通过率', value: '86%' },
];

export default function EvalPageIOS() {
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [running, setRunning] = useState(false);
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    if (!running) return;
    const timer = setInterval(() => {
      setProgress((prev) => {
        if (prev >= 100) {
          setRunning(false);
          toast.success('评测完成');
          return 100;
        }
        return prev + 5;
      });
    }, 250);
    return () => clearInterval(timer);
  }, [running]);

  const handleStart = () => {
    setConfirmOpen(false);
    setProgress(0);
    setRunning(true);
    toast.success('评测已启动');
  };

  return (
    <IOSPage className="pb-24">
      <IOSStaggerList className="px-4 pt-6 space-y-6">
        <IOSStaggerItem>
          <h1 className="ios-title-1 text-[var(--color-text-primary)]">评测中心</h1>
          <p className="ios-subhead text-[var(--color-text-muted)] mt-1">Agent 质量评估</p>
        </IOSStaggerItem>

        <IOSStaggerItem>
          <div className="flex gap-3">
            {STATS.map((stat) => (
              <div key={stat.label} className="flex-1 ios-card p-4">
                <p className="ios-title-1 text-[var(--color-text-primary)]">{stat.value}</p>
                <p className="ios-caption text-[var(--color-text-muted)] mt-0.5">{stat.label}</p>
              </div>
            ))}
          </div>
        </IOSStaggerItem>

        <IOSStaggerItem>
          {running && (
            <div className="ios-card p-4 flex items-center gap-4">
              <RefreshCw size={22} className="text-[var(--color-accent)] animate-spin shrink-0" />
              <div className="flex-1">
                <p className="ios-headline text-[var(--color-text-primary)]">正在运行评测</p>
                <div className="h-1.5 rounded-full bg-[var(--color-bg-surface-2)] mt-2 overflow-hidden">
                  <div
                    className="h-full rounded-full bg-gradient-to-r from-[var(--color-accent)] to-[var(--color-success)] transition-all duration-300"
                    style={{ width: `${progress}%` }}
                  />
                </div>
              </div>
              <span className="ios-title-3 text-[var(--color-accent)]">{progress}%</span>
            </div>
          )}
        </IOSStaggerItem>

        <IOSStaggerItem>
          <IOSListGroup title="最近评测">
            {EVAL_ITEMS.map((item) => (
              <IOSListItem
                key={item.id}
                icon={item.icon}
                iconBg={item.iconBg}
                title={item.name}
                showChevron={false}
                detail={
                  <div className="flex flex-col items-end gap-1 w-36">
                    <div className="flex items-center justify-between w-full">
                      <span className="ios-headline text-[var(--color-text-primary)]">{item.score} 分</span>
                      <IOSBadge variant={item.status === 'pass' ? 'success' : 'warning'}>
                        {item.status === 'pass' ? '通过' : '待改进'}
                      </IOSBadge>
                    </div>
                    <div className="h-1.5 w-full rounded-full bg-[var(--color-bg-surface-2)] overflow-hidden">
                      <div
                        className="h-full rounded-full bg-gradient-to-r from-green-400 to-emerald-500"
                        style={{ width: `${item.score}%` }}
                      />
                    </div>
                    <span className="ios-footnote text-[var(--color-text-muted)]">{item.time}</span>
                  </div>
                }
              />
            ))}
          </IOSListGroup>
        </IOSStaggerItem>
      </IOSStaggerList>

      <IOSFab
        icon={<Plus size={20} />}
        label="开始评测"
        onClick={() => setConfirmOpen(true)}
      />

      <IOSConfirmDialog
        open={confirmOpen}
        onOpenChange={setConfirmOpen}
        title="开始新的评测"
        description="将对当前 Agent 运行完整的质量评估流程"
        confirmText="开始"
        onConfirm={handleStart}
      />
    </IOSPage>
  );
}
