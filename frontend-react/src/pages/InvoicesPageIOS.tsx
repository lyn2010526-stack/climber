import { useState } from 'react';
import {
  IOSPage,
  IOSListGroup,
  IOSListItem,
  IOSBadge,
  IOSConfirmDialog,
  IOSStaggerList,
  IOSStaggerItem,
  toast,
} from '../components/ios';
import { CirclePlus, CircleMinus, TrendingUp, TrendingDown, Scale } from 'lucide-react';
import { cn } from '../lib/utils';
import type { ReactElement } from 'react';

type TxStatus = 'success' | 'pending' | 'failed';

interface TxItem {
  id: number;
  description: string;
  amount: string;
  income: boolean;
  date: string;
  status: TxStatus;
  icon: ReactElement;
  iconBg: string;
}

const TX_ITEMS: TxItem[] = [
  { id: 1, description: '发票充值', amount: '+¥500.00', income: true, date: '07-28 10:24', status: 'success', icon: <CirclePlus size={18} className="text-[#34C759]" />, iconBg: 'transparent' },
  { id: 2, description: 'Token 消耗', amount: '-¥86.50', income: false, date: '07-27 16:40', status: 'success', icon: <CircleMinus size={18} className="text-[var(--color-text-muted)]" />, iconBg: 'transparent' },
  { id: 3, description: '发票充值', amount: '+¥200.00', income: true, date: '07-26 09:12', status: 'pending', icon: <CirclePlus size={18} className="text-[#34C759]" />, iconBg: 'transparent' },
  { id: 4, description: '模型调用费用', amount: '-¥142.80', income: false, date: '07-25 14:05', status: 'success', icon: <CircleMinus size={18} className="text-[var(--color-text-muted)]" />, iconBg: 'transparent' },
  { id: 5, description: '存储空间扣费', amount: '-¥35.20', income: false, date: '07-24 08:33', status: 'failed', icon: <CircleMinus size={18} className="text-[var(--color-text-muted)]" />, iconBg: 'transparent' },
  { id: 6, description: '发票充值', amount: '+¥1000.00', income: true, date: '07-23 11:50', status: 'success', icon: <CirclePlus size={18} className="text-[#34C759]" />, iconBg: 'transparent' },
];

const statusVariant: Record<TxStatus, 'success' | 'warning' | 'error'> = {
  success: 'success',
  pending: 'warning',
  failed: 'error',
};

const statusLabel: Record<TxStatus, string> = {
  success: '成功',
  pending: '处理中',
  failed: '失败',
};

const SUMMARY = [
  { icon: TrendingUp, label: '本月收入', value: '¥1,700.00', color: '#34C759' },
  { icon: TrendingDown, label: '本月支出', value: '¥264.50', color: '#FF3B30' },
  { icon: Scale, label: '本月净额', value: '¥1,435.50', color: '#007AFF' },
];

export default function InvoicesPageIOS() {
  const [confirmOpen, setConfirmOpen] = useState(false);

  const handleRecharge = () => {
    setConfirmOpen(false);
    toast.success('充值申请已提交');
  };

  return (
    <IOSPage className="pb-24">
      <IOSStaggerList className="px-4 pt-6 space-y-5">
        <IOSStaggerItem>
          <h1 className="ios-title-1 text-[var(--color-text-primary)]">发票中心</h1>
          <p className="ios-subhead text-[var(--color-text-muted)] mt-1">账户余额与交易记录</p>
        </IOSStaggerItem>

        <IOSStaggerItem>
          <div className="ios-card p-5 bg-gradient-to-br from-[#007AFF] to-[#AF52DE] border-none">
            <p className="ios-caption text-white/80">当前余额</p>
            <p className="ios-title-1 text-white mt-1">¥2,458.60</p>
            <button
              type="button"
              onClick={() => setConfirmOpen(true)}
              className="mt-4 px-4 py-2 rounded-full bg-white text-[#007AFF] ios-body font-semibold active:opacity-80 transition-opacity"
            >
              充值
            </button>
          </div>
        </IOSStaggerItem>

        <IOSStaggerItem>
          <IOSListGroup title="交易记录">
            {TX_ITEMS.map((tx) => (
              <IOSListItem
                key={tx.id}
                icon={tx.icon}
                iconBg={tx.iconBg}
                title={tx.description}
                showChevron={false}
                detail={
                  <div className="flex flex-col items-end gap-0.5">
                    <span
                      className={cn(
                        'ios-headline',
                        tx.income ? 'text-[var(--color-success)]' : 'text-[var(--color-text-primary)]'
                      )}
                    >
                      {tx.amount}
                    </span>
                    <span className="ios-footnote text-[var(--color-text-muted)]">{tx.date}</span>
                    <IOSBadge variant={statusVariant[tx.status]}>{statusLabel[tx.status]}</IOSBadge>
                  </div>
                }
              />
            ))}
          </IOSListGroup>
        </IOSStaggerItem>

        <IOSStaggerItem>
          <div className="ios-card p-4">
            <div className="flex items-center justify-around">
              {SUMMARY.map((item) => (
                <div key={item.label} className="flex flex-col items-center gap-1">
                  <item.icon size={18} style={{ color: item.color }} />
                  <span className="ios-headline text-[var(--color-text-primary)]">{item.value}</span>
                  <span className="ios-caption text-[var(--color-text-muted)]">{item.label}</span>
                </div>
              ))}
            </div>
          </div>
        </IOSStaggerItem>
      </IOSStaggerList>

      <IOSConfirmDialog
        open={confirmOpen}
        onOpenChange={setConfirmOpen}
        title="确认充值"
        description="将向当前账户充值 ¥500.00"
        confirmText="确认充值"
        onConfirm={handleRecharge}
      />
    </IOSPage>
  );
}
