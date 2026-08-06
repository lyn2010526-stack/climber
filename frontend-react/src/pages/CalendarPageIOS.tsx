import { useState } from 'react';
import {
  IOSPage,
  IOSListGroup,
  IOSListItem,
  IOSSwitch,
  IOSBadge,
  IOSFab,
  IOSStaggerList,
  IOSStaggerItem,
  toast,
} from '../components/ios';
import { Plus } from 'lucide-react';
import { cn } from '../lib/utils';

const WEEK_LABELS = ['周一', '周二', '周三', '周四', '周五', '周六', '周日'] as const;

interface ScheduleItem {
  id: number;
  time: string;
  title: string;
  tag: '会议' | '任务' | '提醒';
  color: string;
}

interface TodoItem {
  id: number;
  title: string;
  done: boolean;
}

const SCHEDULES: ScheduleItem[] = [
  { id: 1, time: '09:00', title: '产品需求评审会', tag: '会议', color: '#007AFF' },
  { id: 2, time: '10:30', title: '编写季度技术方案', tag: '任务', color: '#FF9500' },
  { id: 3, time: '12:00', title: '午餐提醒', tag: '提醒', color: '#34C759' },
  { id: 4, time: '14:30', title: '与设计团队对齐原型', tag: '会议', color: '#AF52DE' },
  { id: 5, time: '17:00', title: '提交代码审查', tag: '任务', color: '#FF3B30' },
];

const INITIAL_TODOS: TodoItem[] = [
  { id: 1, title: '回复客户邮件', done: true },
  { id: 2, title: '整理会议纪要', done: false },
  { id: 3, title: '更新项目文档', done: false },
];

const tagVariant: Record<ScheduleItem['tag'], 'info' | 'default' | 'warning'> = {
  会议: 'info',
  任务: 'default',
  提醒: 'warning',
};

export default function CalendarPageIOS() {
  const [todos, setTodos] = useState<TodoItem[]>(INITIAL_TODOS);

  const now = new Date();
  const weekday = WEEK_LABELS[(now.getDay() + 6) % 7] ?? '周一';
  const monthDay = now.getDate();
  const weekStart = new Date(now);
  weekStart.setDate(now.getDate() - ((now.getDay() + 6) % 7));

  const weekDays = Array.from({ length: 7 }, (_, i) => {
    const d = new Date(weekStart);
    d.setDate(weekStart.getDate() + i);
    return {
      label: WEEK_LABELS[i] ?? '',
      day: d.getDate(),
      isToday: d.toDateString() === now.toDateString(),
    };
  });

  const handleToggle = (id: number) => {
    setTodos((prev) =>
      prev.map((todo) => {
        if (todo.id !== id) return todo;
        const done = !todo.done;
        if (done) toast.success(`已完成：${todo.title}`);
        return { ...todo, done };
      })
    );
  };

  return (
    <IOSPage className="pb-24">
      <IOSStaggerList className="px-4 pt-6 space-y-5">
        <IOSStaggerItem>
          <h1 className="ios-title-1 text-[var(--color-text-primary)]">日程中心</h1>
          <p className="ios-subhead text-[var(--color-text-muted)] mt-1">安排每一天的精彩</p>
        </IOSStaggerItem>

        <IOSStaggerItem>
          <div className="ios-card p-5 flex items-center justify-between">
            <div className="flex items-baseline gap-2">
              <span className="ios-title-1 text-[var(--color-accent)]">{monthDay}</span>
              <div>
                <p className="ios-headline text-[var(--color-text-primary)]">{weekday}</p>
                <p className="ios-caption text-[var(--color-text-muted)]">{now.getMonth() + 1} 月</p>
              </div>
            </div>
            <span className="ios-caption text-[var(--color-text-muted)]">农历六月廿三</span>
          </div>
        </IOSStaggerItem>

        <IOSStaggerItem>
          <div className="flex gap-2">
            {weekDays.map((day) => (
              <div
                key={day.label}
                className={cn(
                  'flex-1 flex flex-col items-center py-2.5 rounded-xl transition-colors',
                  day.isToday
                    ? 'bg-[var(--color-accent)] text-white shadow-lg shadow-[var(--color-accent-glow)]'
                    : 'bg-[var(--color-bg-surface-2)] text-[var(--color-text-secondary)]'
                )}
              >
                <span className="ios-footnote opacity-70">{day.label}</span>
                <span className="ios-headline mt-1">{day.day}</span>
              </div>
            ))}
          </div>
        </IOSStaggerItem>

        <IOSStaggerItem>
          <IOSListGroup title="今日日程">
            {SCHEDULES.map((item) => (
              <IOSListItem
                key={item.id}
                title={item.title}
                showChevron={false}
                icon={
                  <span className="w-1.5 h-8 rounded-full" style={{ background: item.color }} />
                }
                iconBg="transparent"
                detail={
                  <div className="flex items-center gap-2">
                    <span className="ios-headline text-[var(--color-text-primary)]">{item.time}</span>
                    <IOSBadge variant={tagVariant[item.tag]}>{item.tag}</IOSBadge>
                  </div>
                }
              />
            ))}
          </IOSListGroup>
        </IOSStaggerItem>

        <IOSStaggerItem>
          <IOSListGroup title="待办">
            {todos.map((todo) => (
              <IOSListItem
                key={todo.id}
                title={todo.title}
                showChevron={false}
                className={cn(todo.done && 'opacity-50')}
                icon={
                  <span
                    className={cn(
                      'w-6 h-6 rounded-full border-2 flex items-center justify-center',
                      todo.done
                        ? 'bg-[var(--color-success)] border-[var(--color-success)]'
                        : 'border-[var(--color-text-muted)]'
                    )}
                  />
                }
                iconBg="transparent"
                detail={
                  <IOSSwitch checked={todo.done} onChange={() => handleToggle(todo.id)} />
                }
              />
            ))}
          </IOSListGroup>
        </IOSStaggerItem>
      </IOSStaggerList>

      <IOSFab
        icon={<Plus size={20} />}
        label="添加日程"
        onClick={() => toast.info('添加日程功能即将上线')}
      />
    </IOSPage>
  );
}
