import { useMemo, useState } from 'react';
import {
  IOSPage,
  IOSListGroup,
  IOSBadge,
  IOSSegmentedControl,
  IOSStaggerList,
  IOSStaggerItem,
} from '../components/ios';
import { Bot, Wrench, Workflow, Settings } from 'lucide-react';
import type { ReactElement } from 'react';

type ActivityCategory = 'agent' | 'tool' | 'workflow' | 'system';
type ActivityGroup = 'today' | 'yesterday' | 'earlier';
type BadgeVariant = 'success' | 'info' | 'warning' | 'default';

interface ActivityItem {
  id: number;
  category: ActivityCategory;
  group: ActivityGroup;
  icon: ReactElement;
  iconBg: string;
  title: string;
  description: string;
  time: string;
  badgeLabel: string;
  badgeVariant: BadgeVariant;
}

const CATEGORY_OPTIONS = [
  { value: 'all', label: '全部' },
  { value: 'agent', label: 'Agent' },
  { value: 'tool', label: '工具' },
  { value: 'workflow', label: '工作流' },
  { value: 'system', label: '系统' },
];

const ACTIVITIES: ActivityItem[] = [
  { id: 1, category: 'agent', group: 'today', icon: <Bot size={16} className="text-white" />, iconBg: '#5E6AD2', title: 'Agent 完成任务', description: '数据分析 Agent 已生成季度销售报表', time: '09:42', badgeLabel: '完成', badgeVariant: 'success' },
  { id: 2, category: 'tool', group: 'today', icon: <Wrench size={16} className="text-white" />, iconBg: '#007AFF', title: '工具调用成功', description: '代码执行器成功运行 Python 数据分析脚本', time: '09:20', badgeLabel: '成功', badgeVariant: 'success' },
  { id: 3, category: 'workflow', group: 'today', icon: <Workflow size={16} className="text-white" />, iconBg: '#AF52DE', title: '工作流启动', description: '自动部署流水线已触发并进入构建阶段', time: '08:55', badgeLabel: '运行中', badgeVariant: 'info' },
  { id: 4, category: 'agent', group: 'yesterday', icon: <Bot size={16} className="text-white" />, iconBg: '#34C759', title: '模型切换', description: '默认推理模型已切换为 DeepSeek-V3', time: '17:30', badgeLabel: '已切换', badgeVariant: 'info' },
  { id: 5, category: 'system', group: 'yesterday', icon: <Settings size={16} className="text-white" />, iconBg: '#FF9500', title: '用户登录', description: '用户 admin 从新设备登录控制台', time: '16:12', badgeLabel: '完成', badgeVariant: 'success' },
  { id: 6, category: 'system', group: 'earlier', icon: <Settings size={16} className="text-white" />, iconBg: '#8E8E93', title: '系统更新', description: 'Agent 引擎已自动升级至 v2.4.0', time: '08:00', badgeLabel: '完成', badgeVariant: 'success' },
  { id: 7, category: 'agent', group: 'earlier', icon: <Bot size={16} className="text-white" />, iconBg: '#5E6AD2', title: '评测完成', description: '智能体评测跑分已生成完整对比报告', time: '07:45', badgeLabel: '完成', badgeVariant: 'success' },
  { id: 8, category: 'system', group: 'earlier', icon: <Settings size={16} className="text-white" />, iconBg: '#FF3B30', title: '成本告警', description: '本月 API 调用费用已超出预算 20%', time: '06:30', badgeLabel: '告警', badgeVariant: 'warning' },
];

const GROUP_ORDER: ActivityGroup[] = ['today', 'yesterday', 'earlier'];

const GROUP_LABEL: Record<ActivityGroup, string> = {
  today: '今天',
  yesterday: '昨天',
  earlier: '更早',
};

export default function ActivityPageIOS() {
  const [category, setCategory] = useState<string>('all');

  const filteredActivities = useMemo(() => {
    if (category === 'all') return ACTIVITIES;
    return ACTIVITIES.filter((activity) => activity.category === category);
  }, [category]);

  return (
    <IOSPage className="pb-24">
      <IOSStaggerList className="px-4 pt-6 space-y-5">
        <IOSStaggerItem>
          <h1 className="ios-title-1 text-[var(--color-text-primary)]">活动中心</h1>
          <p className="ios-subhead text-[var(--color-text-muted)] mt-1">
            实时掌握 Agent 动态与系统事件
          </p>
        </IOSStaggerItem>

        <IOSStaggerItem>
          <IOSSegmentedControl
            options={CATEGORY_OPTIONS}
            value={category}
            onChange={setCategory}
          />
        </IOSStaggerItem>

        {GROUP_ORDER.map((group) => {
          const activities = filteredActivities.filter((activity) => activity.group === group);
          if (activities.length === 0) return null;
          return (
            <IOSStaggerItem key={group}>
              <IOSListGroup title={GROUP_LABEL[group]}>
                {activities.map((activity) => (
                  <div
                    key={activity.id}
                    className="flex items-start gap-3 px-4 py-3 border-b border-[var(--color-border-subtle)] last:border-b-0"
                  >
                    <span
                      className="ios-footnote text-[var(--color-text-muted)] leading-tight shrink-0"
                      style={{ writingMode: 'vertical-rl' }}
                    >
                      {activity.time}
                    </span>
                    <span
                      className="flex h-9 w-9 items-center justify-center rounded-full shrink-0"
                      style={{ background: activity.iconBg }}
                    >
                      {activity.icon}
                    </span>
                    <div className="flex-1 min-w-0">
                      <p className="ios-headline text-[var(--color-text-primary)]">{activity.title}</p>
                      <p className="ios-caption text-[var(--color-text-muted)] mt-0.5">
                        {activity.description}
                      </p>
                    </div>
                    <IOSBadge variant={activity.badgeVariant} className="shrink-0">
                      {activity.badgeLabel}
                    </IOSBadge>
                  </div>
                ))}
              </IOSListGroup>
            </IOSStaggerItem>
          );
        })}
      </IOSStaggerList>
    </IOSPage>
  );
}
