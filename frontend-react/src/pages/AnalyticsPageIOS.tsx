import { useState } from 'react';
import {
  TrendingUp,
  Zap,
  Clock,
  DollarSign,
  BarChart3,
} from 'lucide-react';
import {
  IOSPage,
  IOSCard,
  IOSListGroup,
  IOSListItem,
  IOSBadge,
  IOSSegmentedControl,
} from '../components/ios';
import { cn } from '../lib/utils';

type TimeRange = 'today' | 'week' | 'month' | 'year';

const timeRangeOptions = [
  { value: 'today', label: '今日' },
  { value: 'week', label: '本周' },
  { value: 'month', label: '本月' },
  { value: 'year', label: '本年' },
];

interface KpiCardProps {
  icon: React.ReactNode;
  value: string;
  label: string;
  change: string;
  variant: 'success' | 'warning' | 'error' | 'info';
}

function KpiCard({ icon, value, label, change, variant }: KpiCardProps) {
  return (
    <IOSCard className="p-4">
      <div className="flex items-start justify-between mb-3">
        <div className="w-9 h-9 rounded-xl bg-[var(--color-accent-subtle)] flex items-center justify-center text-[var(--color-accent)]">
          {icon}
        </div>
        <IOSBadge variant={variant}>{change}</IOSBadge>
      </div>
      <div className="ios-title-2 text-[var(--color-text-primary)]">{value}</div>
      <div className="ios-caption text-[var(--color-text-muted)] mt-0.5">{label}</div>
    </IOSCard>
  );
}

const tokenTrendData = [35, 52, 48, 65, 72, 58, 80, 76, 90, 85, 78, 92];

const modelDistribution = [
  { name: 'GPT-4', percent: 45 },
  { name: 'Claude', percent: 30 },
  { name: 'Gemini', percent: 15 },
  { name: '其他', percent: 10 },
];

const topTools = [
  { name: '代码解释器', count: 386 },
  { name: '网络搜索', count: 274 },
  { name: '文档生成', count: 198 },
  { name: '数据分析', count: 156 },
  { name: 'API 测试', count: 112 },
];

export default function AnalyticsPageIOS() {
  const [timeRange, setTimeRange] = useState<TimeRange>('today');

  return (
    <IOSPage className="px-4 pb-8">
      <div className="ios-title-1 text-[var(--color-text-primary)] mt-4 mb-1">数据分析</div>
      <div className="ios-subhead text-[var(--color-text-muted)] mb-5">核心指标监控</div>

      <div className="mb-6">
        <IOSSegmentedControl
          options={timeRangeOptions}
          value={timeRange}
          onChange={(v) => setTimeRange(v as TimeRange)}
        />
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
        <KpiCard
          icon={<TrendingUp size={18} />}
          value="1,284"
          label="总会话数"
          change="+12.5%"
          variant="success"
        />
        <KpiCard
          icon={<Zap size={18} />}
          value="4.2M"
          label="Token 消耗"
          change="+8.3%"
          variant="success"
        />
        <KpiCard
          icon={<Clock size={18} />}
          value="234"
          label="平均响应时间 (ms)"
          change="-5.2%"
          variant="info"
        />
        <KpiCard
          icon={<DollarSign size={18} />}
          value="156.8"
          label="成本 (¥)"
          change="+3.1%"
          variant="warning"
        />
      </div>

      <IOSCard className="p-4 mb-6">
        <div className="flex items-center gap-2 mb-4">
          <BarChart3 size={16} className="text-[var(--color-accent)]" />
          <span className="ios-subhead text-[var(--color-text-primary)]">Token 趋势</span>
        </div>
        <div className="h-[120px] flex items-end gap-1.5">
          {tokenTrendData.map((value, index) => (
            <div
              key={index}
              className="flex-1 rounded-t-sm bg-gradient-to-t from-[var(--color-accent)] to-[var(--color-accent-subtle)] opacity-80 hover:opacity-100 transition-opacity"
              style={{ height: `${value}%` }}
            />
          ))}
        </div>
      </IOSCard>

      <IOSCard className="p-4 mb-6">
        <div className="ios-subhead text-[var(--color-text-primary)] mb-4">模型使用分布</div>
        <div className="space-y-3">
          {modelDistribution.map((model) => (
            <div key={model.name}>
              <div className="flex items-center justify-between mb-1">
                <span className="ios-caption text-[var(--color-text-primary)]">{model.name}</span>
                <span className="ios-caption text-[var(--color-text-muted)]">{model.percent}%</span>
              </div>
              <div className="h-2 rounded-full bg-[var(--color-bg-surface-2)] overflow-hidden">
                <div
                  className="h-full rounded-full bg-[var(--color-accent)]"
                  style={{ width: `${model.percent}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      </IOSCard>

      <IOSListGroup title="热门工具 TOP5">
        {topTools.map((tool, index) => (
          <IOSListItem
            key={tool.name}
            title={tool.name}
            detail={<IOSBadge>{tool.count}</IOSBadge>}
            icon={
              <span className="text-xs font-bold text-white">{index + 1}</span>
            }
            iconBg={index === 0 ? 'var(--color-warning)' : index === 1 ? 'var(--color-text-muted)' : index === 2 ? 'var(--color-accent)' : 'var(--color-bg-surface-3)'}
            showChevron={false}
          />
        ))}
      </IOSListGroup>
    </IOSPage>
  );
}
