import { motion } from 'framer-motion';
import {
  Sparkles,
  Play,
  CheckCircle,
  XCircle,
  Bot,
  ListTodo,
  Coins,
  Clock,
  MessageSquare,
  Compass,
  UserPlus,
  BarChart3,
  ChevronRight,
} from 'lucide-react';
import {
  IOSPage,
  IOSCard,
  IOSListGroup,
  IOSListItem,
  IOSBadge,
  IOSSkeletonGroup,
} from '../components/ios';
import { cn } from '../lib/utils';

const stats = [
  { icon: Bot, label: '活跃 Agent', value: '12', badge: '+12%', badgeVariant: 'success' as const, iconBg: '#34C759' },
  { icon: ListTodo, label: '今日任务', value: '47', badge: '85% 完成', badgeVariant: 'info' as const, iconBg: '#007AFF' },
  { icon: Coins, label: 'Token 消耗', value: '2.4M', caption: '¥23.5', iconBg: '#FF9500' },
  { icon: Clock, label: '运行时间', value: '12h 30m', caption: '12h 30m', iconBg: '#AF52DE' },
];

const activities = [
  { icon: CheckCircle, color: '#34C759', text: '代码审查完成', time: '5 分钟前' },
  { icon: Sparkles, color: '#FF9500', text: '新 Agent 创建', time: '15 分钟前' },
  { icon: XCircle, color: '#FF3B30', text: '工作流执行失败', time: '1 小时前' },
  { icon: CheckCircle, color: '#34C759', text: '文档生成完成', time: '2 小时前' },
  { icon: Play, color: '#007AFF', text: '模型训练开始', time: '3 小时前' },
];

const quickActions = [
  { icon: MessageSquare, title: '新建对话', iconBg: '#007AFF' },
  { icon: Compass, title: '浏览工具', iconBg: '#34C759' },
  { icon: UserPlus, title: '创建 Agent', iconBg: '#FF9500' },
  { icon: BarChart3, title: '查看分析', iconBg: '#AF52DE' },
];

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.06 },
  },
};

const itemVariants = {
  hidden: { opacity: 0, y: 12 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.3, ease: [0.16, 1, 0.3, 1] } },
};

export default function DashboardPageIOS() {
  return (
    <IOSPage className="h-full overflow-y-auto pb-6">
      <motion.div variants={containerVariants} initial="hidden" animate="visible" className="px-4 pt-6 space-y-6">
        <motion.div variants={itemVariants}>
          <h1 className="ios-title-1">工作台</h1>
          <p className="ios-subhead text-[var(--color-text-muted)] mt-1">今日概览</p>
        </motion.div>

        <motion.div variants={itemVariants} className="grid grid-cols-2 gap-3">
          {stats.map((stat) => (
            <IOSCard key={stat.label} className="p-4">
              <stat.icon size={18} style={{ color: stat.iconBg }} className="mb-2" />
              <div className="ios-title-1">{stat.value}</div>
              <div className="ios-caption text-[var(--color-text-muted)] mt-0.5">{stat.label}</div>
              {stat.badge && (
                <IOSBadge variant={stat.badgeVariant} className="mt-2">{stat.badge}</IOSBadge>
              )}
              {stat.caption && !stat.badge && (
                <div className="ios-caption text-[var(--color-text-muted)] mt-2">{stat.caption}</div>
              )}
            </IOSCard>
          ))}
        </motion.div>

        <motion.div variants={itemVariants}>
          <IOSListGroup title="最近活动">
            {activities.map((activity, index) => (
              <IOSListItem
                key={index}
                icon={<activity.icon size={18} className="text-white" />}
                iconBg={activity.color}
                title={activity.text}
                detail={<span className="ios-footnote text-[var(--color-text-muted)]">{activity.time}</span>}
                showChevron={false}
              />
            ))}
          </IOSListGroup>
        </motion.div>

        <motion.div variants={itemVariants}>
          <IOSListGroup title="快捷操作">
            {quickActions.map((action) => (
              <IOSListItem
                key={action.title}
                icon={<action.icon size={18} className="text-white" />}
                iconBg={action.iconBg}
                title={action.title}
                detail={<ChevronRight size={16} className="text-[var(--color-text-muted)] opacity-40" />}
              />
            ))}
          </IOSListGroup>
        </motion.div>

        <motion.div variants={itemVariants}>
          <IOSListGroup title="加载演示">
            <div className="px-4 py-3">
              <IOSSkeletonGroup count={3} />
            </div>
          </IOSListGroup>
        </motion.div>
      </motion.div>
    </IOSPage>
  );
}
