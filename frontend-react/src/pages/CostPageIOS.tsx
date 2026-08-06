import { useState, useMemo } from 'react';
import {
  IOSPage,
  IOSListGroup,
  IOSListItem,
  IOSBadge,
} from '../components/ios';
import {
  Wallet,
  Cpu,
  Globe,
  PiggyBank,
  Bot,
  Database,
  Server,
  HardDrive,
  TrendingUp,
  TrendingDown,
} from 'lucide-react';
import { cn } from '../lib/utils';
import type { ReactElement } from 'react';

type Trend = '增长' | '稳定';

interface CostItem {
  id: string;
  name: string;
  amount: string;
  icon: ReactElement;
  iconBg: string;
  trend: Trend;
}

const COST_ITEMS: CostItem[] = [
  {
    id: '1',
    name: 'GPT-4 API',
    amount: '¥1,280.50',
    icon: <Bot size={20} className="text-white" />,
    iconBg: '#007AFF',
    trend: '增长',
  },
  {
    id: '2',
    name: 'Claude API',
    amount: '¥896.20',
    icon: <Globe size={20} className="text-white" />,
    iconBg: '#AF52DE',
    trend: '增长',
  },
  {
    id: '3',
    name: '向量存储',
    amount: '¥456.00',
    icon: <Database size={20} className="text-white" />,
    iconBg: '#34C759',
    trend: '稳定',
  },
  {
    id: '4',
    name: '计算资源',
    amount: '¥328.80',
    icon: <Server size={20} className="text-white" />,
    iconBg: '#FF9500',
    trend: '稳定',
  },
  {
    id: '5',
    name: '存储空间',
    amount: '¥120.40',
    icon: <HardDrive size={20} className="text-white" />,
    iconBg: '#5AC8FA',
    trend: '稳定',
  },
];

const KPI_CARDS = [
  {
    label: '本月总成本',
    value: '¥3,081.90',
    icon: <Wallet size={20} className="text-white" />,
    iconBg: '#FF3B30',
  },
  {
    label: 'Token 成本',
    value: '¥2,176.70',
    icon: <Cpu size={20} className="text-white" />,
    iconBg: '#007AFF',
  },
  {
    label: 'API 成本',
    value: '¥785.40',
    icon: <Globe size={20} className="text-white" />,
    iconBg: '#AF52DE',
  },
  {
    label: '预算剩余',
    value: '¥918.10',
    icon: <PiggyBank size={20} className="text-white" />,
    iconBg: '#34C759',
  },
];

const trendVariant: Record<Trend, 'success' | 'info'> = {
  增长: 'success',
  稳定: 'info',
};

const BARS = [35, 55, 40, 70, 50, 85, 62];

export default function CostPageIOS() {
  const [range] = useState('近 7 天');

  const total = useMemo(
    () => COST_ITEMS.reduce((sum, item) => sum + parseFloat(item.amount.replace(/[¥,]/g, '')), 0),
    []
  );

  return (
    <IOSPage className="pb-24">
      <div className="px-4 pt-6">
        <h1 className="ios-title-1 text-[var(--color-text-primary)]">成本中心</h1>
        <p className="ios-subhead text-[var(--color-text-muted)] mt-1">
          实时监控资源消耗与预算使用情况
        </p>
      </div>

      <div className="px-4 mt-5 grid grid-cols-2 md:grid-cols-4 gap-3">
        {KPI_CARDS.map((card) => (
          <div key={card.label} className="ios-card p-3.5">
            <div
              className="flex items-center justify-center w-9 h-9 rounded-full mb-2"
              style={{ background: card.iconBg }}
            >
              {card.icon}
            </div>
            <p className="ios-title-3 text-[var(--color-text-primary)]">
              {card.value}
            </p>
            <p className="ios-caption text-[var(--color-text-muted)] mt-0.5">
              {card.label}
            </p>
          </div>
        ))}
      </div>

      <div className="px-4 mt-4">
        <div className="ios-card p-4">
          <div className="flex items-center justify-between mb-3">
            <p className="ios-headline text-[var(--color-text-primary)]">
              成本趋势
            </p>
            <span className="ios-caption text-[var(--color-text-muted)]">
              {range}
            </span>
          </div>
          <div className="flex items-end gap-2 h-[100px]">
            {BARS.map((height, i) => (
              <div
                key={i}
                className={cn(
                  'flex-1 rounded-t-md bg-gradient-to-t from-[var(--color-accent)]/30 to-[var(--color-accent)]',
                  i === BARS.length - 1 && 'from-[var(--color-success)]/30 to-[var(--color-success)]'
                )}
                style={{ height: `${height}%` }}
              />
            ))}
          </div>
        </div>
      </div>

      <div className="px-4 mt-5">
        <IOSListGroup title="明细">
          {COST_ITEMS.map((item) => (
            <IOSListItem
              key={item.id}
              icon={item.icon}
              iconBg={item.iconBg}
              title={item.name}
              detail={
                <div className="flex items-center gap-2">
                  <span className="ios-body font-semibold text-[var(--color-text-primary)]">
                    {item.amount}
                  </span>
                  <IOSBadge variant={trendVariant[item.trend]}>
                    {item.trend === '增长' ? (
                      <span className="flex items-center gap-0.5">
                        <TrendingUp size={11} />
                        {item.trend}
                      </span>
                    ) : (
                      <span className="flex items-center gap-0.5">
                        <TrendingDown size={11} />
                        {item.trend}
                      </span>
                    )}
                  </IOSBadge>
                </div>
              }
            />
          ))}
        </IOSListGroup>
      </div>

      <div className="px-4 mt-4">
        <div className="flex items-center justify-between px-4 py-3 rounded-xl bg-[var(--color-bg-surface-2)] border border-[var(--color-border-subtle)]">
          <span className="ios-body text-[var(--color-text-muted)]">
            本月累计消费
          </span>
          <span className="ios-title-3 text-[var(--color-error)]">
            ¥{total.toFixed(2)}
          </span>
        </div>
      </div>
    </IOSPage>
  );
}
