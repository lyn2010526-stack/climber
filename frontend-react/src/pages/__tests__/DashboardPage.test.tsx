import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { DashboardPage } from '../DashboardPage';

vi.mock('../../i18n/utils', () => {
  const t = (key: string): string => {
    const map: Record<string, string> = {
      'home.title': '工作台',
      'home.subtitle': '欢迎回来，这里是您的智能体工作台',
      'home.active_agents': '活跃智能体',
      'home.performance': '性能指数',
      'home.running_sessions': '运行中会话',
      'home.efficiency': '资源效率',
      'home.last_7_days': '近 7 天',
      'home.today': '今日',
      'home.yesterday': '昨日',
      'home.this_week': '本周',
      'home.activity': '动态',
      'home.recent_activity': '最近活动',
      'home.quick_actions': '快速操作',
      'home.quick_actions_desc': '常用操作入口',
      'home.create_agent': '创建智能体',
      'home.create_agent_desc': '配置一个新的智能体',
      'home.start_task': '开始任务',
      'home.start_task_desc': '启动一个新的执行任务',
    };
    return map[key] ?? key;
  };
  return { useI18n: () => ({ t }) };
});

describe('DashboardPage', () => {
  it('renders without crashing', () => {
    const { container } = render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>
    );
    expect(container).toBeDefined();
  });

  it('renders welcome message', async () => {
    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>
    );
    expect(await screen.findByText(/欢迎回来/, undefined, { timeout: 5000 })).toBeDefined();
  });

  it('renders real service status', async () => {
    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>
    );
    expect(await screen.findByText('API service', undefined, { timeout: 5000 })).toBeDefined();
  });

  it('renders quick actions', async () => {
    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>
    );
    expect(await screen.findByText('快速操作', undefined, { timeout: 5000 })).toBeDefined();
  });
});
