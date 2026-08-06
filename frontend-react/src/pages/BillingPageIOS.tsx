import { useState } from 'react';
import {
  IOSPage,
  IOSListGroup,
  IOSListItem,
  IOSBadge,
  IOSConfirmDialog,
  toast,
} from '../components/ios';
import {
  CheckCircle,
  Circle,
  CreditCard,
  Wallet,
  MessageSquare,
  Crown,
  Receipt,
} from 'lucide-react';
import { cn } from '../lib/utils';
import type { ReactElement } from 'react';

interface Plan {
  id: string;
  name: string;
  price: string;
  description: string;
  icon: ReactElement;
  iconBg: string;
}

const PLANS: Plan[] = [
  {
    id: 'free',
    name: '免费版',
    price: '¥0/月',
    description: '基础功能，适合个人体验',
    icon: <Circle size={20} className="text-white" />,
    iconBg: '#8E8E93',
  },
  {
    id: 'pro',
    name: '专业版',
    price: '¥299/月',
    description: '高级智能体与协作能力',
    icon: <Crown size={20} className="text-white" />,
    iconBg: '#007AFF',
  },
  {
    id: 'enterprise',
    name: '企业版',
    price: '¥899/月',
    description: '定制方案与专属支持',
    icon: <Crown size={20} className="text-white" />,
    iconBg: '#FF9500',
  },
];

const PAYMENT_METHODS = [
  {
    id: 'card',
    name: '信用卡',
    detail: '尾号 4242',
    icon: <CreditCard size={20} className="text-white" />,
    iconBg: '#34C759',
  },
  {
    id: 'alipay',
    name: '支付宝',
    detail: '在线支付',
    icon: <Wallet size={20} className="text-white" />,
    iconBg: '#007AFF',
  },
  {
    id: 'wechat',
    name: '微信支付',
    detail: '扫码支付',
    icon: <MessageSquare size={20} className="text-white" />,
    iconBg: '#34C759',
  },
];

const INVOICES = [
  {
    id: '1',
    date: '2026-08-01',
    amount: '¥299.00',
    status: '已支付',
    variant: 'success' as const,
  },
  {
    id: '2',
    date: '2026-07-01',
    amount: '¥299.00',
    status: '已支付',
    variant: 'success' as const,
  },
  {
    id: '3',
    date: '2026-06-01',
    amount: '¥299.00',
    status: '已退款',
    variant: 'error' as const,
  },
];

const STATUS_OPTIONS = ['免费版', '专业版', '企业版'];

export default function BillingPageIOS() {
  const [selectedPlan, setSelectedPlan] = useState('pro');
  const [paymentMethod, setPaymentMethod] = useState('card');
  const [segment, setSegment] = useState('当前套餐');
  const [confirmPlan, setConfirmPlan] = useState<Plan | null>(null);

  const handleSelectPlan = (plan: Plan) => {
    if (plan.id === selectedPlan) {
      toast.info(`${plan.name} 已是当前套餐`);
      return;
    }
    setConfirmPlan(plan);
  };

  const handleConfirmSwitch = () => {
    if (!confirmPlan) return;
    setSelectedPlan(confirmPlan.id);
    toast.success(`已切换到${confirmPlan.name}`);
    setConfirmPlan(null);
  };

  return (
    <IOSPage className="pb-24">
      <div className="px-4 pt-6">
        <h1 className="ios-title-1 text-[var(--color-text-primary)]">账单管理</h1>
        <p className="ios-subhead text-[var(--color-text-muted)] mt-1">
          管理套餐、支付方式与发票记录
        </p>
      </div>

      <div className="px-4 mt-5">
        <div className="ios-card relative overflow-hidden p-5 bg-gradient-to-br from-[var(--color-accent)]/25 to-[var(--color-accent)]/5">
          <div className="flex items-center justify-between">
            <div>
              <p className="ios-caption text-[var(--color-text-muted)]">当前套餐</p>
              <p className="ios-title-1 text-[var(--color-text-primary)] mt-0.5">
                Pro 套餐
              </p>
              <p className="ios-title-3 text-[var(--color-text-primary)] mt-1">
                ¥299/月
              </p>
              <p className="ios-caption text-[var(--color-text-muted)] mt-1">
                下次续费：2026-09-01
              </p>
            </div>
            <IOSBadge variant="info">当前套餐</IOSBadge>
          </div>
        </div>
      </div>

      <div className="px-4 mt-5">
        <div className="ios-segmented">
          {STATUS_OPTIONS.map((opt) => (
            <button
              key={opt}
              type="button"
              onClick={() => setSegment(opt)}
              className={cn('ios-segment', segment === opt && 'active')}
            >
              {opt}
            </button>
          ))}
        </div>
      </div>

      <div className="px-4 mt-5">
        <IOSListGroup title="选择套餐">
          {PLANS.map((plan) => {
            const isSelected = plan.id === selectedPlan;
            return (
              <IOSListItem
                key={plan.id}
                icon={plan.icon}
                iconBg={plan.iconBg}
                title={plan.name}
                detail={
                  <div className="flex items-center gap-2">
                    <div className="flex flex-col items-end">
                      <span className="ios-body font-semibold text-[var(--color-text-primary)]">
                        {plan.price}
                      </span>
                      <span className="ios-caption text-[var(--color-text-muted)]">
                        {plan.description}
                      </span>
                    </div>
                    {isSelected ? (
                      <CheckCircle
                        size={20}
                        className="text-[var(--color-accent)]"
                      />
                    ) : (
                      <Circle
                        size={20}
                        className="text-[var(--color-text-muted)]"
                      />
                    )}
                  </div>
                }
                showChevron={false}
                onClick={() => handleSelectPlan(plan)}
              />
            );
          })}
        </IOSListGroup>
      </div>

      <div className="px-4 mt-5">
        <IOSListGroup title="支付方式">
          {PAYMENT_METHODS.map((method) => (
            <IOSListItem
              key={method.id}
              icon={method.icon}
              iconBg={method.iconBg}
              title={method.name}
              detail={
                <div className="flex items-center gap-2">
                  <span className="ios-caption text-[var(--color-text-muted)]">
                    {method.detail}
                  </span>
                  {paymentMethod === method.id ? (
                    <CheckCircle
                      size={20}
                      className="text-[var(--color-accent)]"
                    />
                  ) : (
                    <Circle
                      size={20}
                      className="text-[var(--color-text-muted)]"
                    />
                  )}
                </div>
              }
              showChevron={false}
              onClick={() => {
                setPaymentMethod(method.id);
                toast.success(`已选择${method.name}`);
              }}
            />
          ))}
        </IOSListGroup>
      </div>

      <div className="px-4 mt-5">
        <IOSListGroup title="发票记录">
          {INVOICES.map((invoice) => (
            <IOSListItem
              key={invoice.id}
              icon={<Receipt size={20} className="text-white" />}
              iconBg="#5AC8FA"
              title={invoice.date}
              detail={
                <div className="flex items-center gap-2">
                  <span className="ios-body font-semibold text-[var(--color-text-primary)]">
                    {invoice.amount}
                  </span>
                  <IOSBadge variant={invoice.variant}>
                    {invoice.status}
                  </IOSBadge>
                </div>
              }
            />
          ))}
        </IOSListGroup>
      </div>

      <IOSConfirmDialog
        open={confirmPlan !== null}
        onOpenChange={(open) => !open && setConfirmPlan(null)}
        title={`切换到${confirmPlan?.name ?? ''}`}
        description={
          confirmPlan
            ? `${confirmPlan.name}价格为 ${confirmPlan.price}，切换后立即生效`
            : undefined
        }
        onConfirm={handleConfirmSwitch}
        confirmText="确认切换"
      />
    </IOSPage>
  );
}
