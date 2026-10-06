import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import i18n from '../i18n';
import { api } from '../api';
import CostPage from './CostPage';

vi.mock('../api', () => ({
  api: {
    getCostUsage: vi.fn(),
    getCostBudget: vi.fn(),
    getCostQuota: vi.fn(),
  },
}));

beforeEach(async () => {
  vi.resetAllMocks();
  await i18n.changeLanguage('zh-CN');
  vi.mocked(api.getCostQuota).mockResolvedValue({
    max_requests_per_day: 200,
    max_tokens_per_day: 1000000,
    max_cost_per_month: 50,
    requests_today: 50,
    tokens_today: 100000,
    cost_this_month: 12.5,
  } as any);
});

describe('CostPage — 成本概览', () => {
  it('渲染总额指标与按模型用量表', async () => {
    vi.mocked(api.getCostUsage).mockResolvedValue({
      total_cost: 1.2345,
      total_tokens: 45000,
      total_calls: 12,
      by_model: [
        { model: 'gpt-4o', cost: 1.0, tokens: 40000, calls: 10 },
        { model: 'gpt-4o-mini', cost: 0.2345, tokens: 5000, calls: 2 },
      ],
      by_day: [],
    } as any);
    vi.mocked(api.getCostBudget).mockResolvedValue(null as any);
    render(<CostPage />);
    expect(await screen.findByText('按模型用量')).toBeInTheDocument();
    expect(screen.getByText('gpt-4o')).toBeInTheDocument();
    expect(screen.getByText('gpt-4o-mini')).toBeInTheDocument();
    expect(screen.getByText('成本概览')).toBeInTheDocument();
  });

  it('无模型用量时显示空态而非空表', async () => {
    vi.mocked(api.getCostUsage).mockResolvedValue({
      total_cost: 0,
      total_tokens: 0,
      total_calls: 0,
      by_model: [],
      by_day: [],
    } as any);
    vi.mocked(api.getCostBudget).mockResolvedValue(null as any);
    render(<CostPage />);
    expect(await screen.findByText('暂无模型用量')).toBeInTheDocument();
    expect(screen.queryByRole('table')).not.toBeInTheDocument();
  });

  it('用量接口失败时给出明确的失败提示', async () => {
    vi.mocked(api.getCostUsage).mockRejectedValue(new Error('down'));
    vi.mocked(api.getCostBudget).mockResolvedValue(null as any);
    render(<CostPage />);
    expect(await screen.findByText(/无法加载/)).toBeInTheDocument();
  });

  it('激活的预算呈现用量条与启用徽标', async () => {
    vi.mocked(api.getCostUsage).mockResolvedValue({
      total_cost: 0,
      total_tokens: 0,
      total_calls: 0,
      by_model: [],
      by_day: [],
    } as any);
    vi.mocked(api.getCostBudget).mockResolvedValue({
      amount: 100,
      period: 'monthly',
      is_active: true,
      current_spend: 42,
      per_session_limit: null,
      per_request_limit: null,
    } as any);
    render(<CostPage />);
    expect(await screen.findByText('预算使用')).toBeInTheDocument();
    expect(screen.getByText('$42.00 / $100.00')).toBeInTheDocument();
  });

  it('头部动作区渲染配额指示器（今日请求 50/200）', async () => {
    vi.mocked(api.getCostUsage).mockResolvedValue({
      total_cost: 0,
      total_tokens: 0,
      total_calls: 0,
      by_model: [],
      by_day: [],
    } as any);
    vi.mocked(api.getCostBudget).mockResolvedValue(null as any);
    render(<CostPage />);
    expect(await screen.findByText('50/200')).toBeInTheDocument();
    expect(api.getCostQuota).toHaveBeenCalled();
  });

  it('刷新按钮重新拉取数据', async () => {
    vi.mocked(api.getCostUsage).mockResolvedValue({
      total_cost: 0,
      total_tokens: 0,
      total_calls: 0,
      by_model: [],
      by_day: [],
    } as any);
    vi.mocked(api.getCostBudget).mockResolvedValue(null as any);
    render(<CostPage />);
    await screen.findByText('总成本');
    fireEvent.click(screen.getByRole('button', { name: /刷新/ }));
    expect(api.getCostUsage).toHaveBeenCalledTimes(2);
  });
});
