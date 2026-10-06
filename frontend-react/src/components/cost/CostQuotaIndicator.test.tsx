import { render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import i18n from '../../i18n';
import { api } from '../../api';
import { CostQuotaIndicator } from './CostQuotaIndicator';

vi.mock('../../api', () => ({ api: { getCostQuota: vi.fn() } }));

beforeEach(async () => {
  vi.resetAllMocks();
  await i18n.changeLanguage('zh-CN');
});

describe('CostQuotaIndicator — 配额指示条', () => {
  it('配额已上报时渲染 used-percent 条与 mono 数字', async () => {
    vi.mocked(api.getCostQuota).mockResolvedValue({
      max_requests_per_day: 200,
      requests_today: 50,
      max_tokens_per_day: 100000,
      tokens_today: 1200,
      max_cost_per_month: 10,
      cost_this_month: 1.2,
    });
    render(<CostQuotaIndicator />);
    const indicator = await screen.findByTestId('cost-quota-indicator');
    expect(indicator).toHaveAttribute('data-state', 'ready');
    expect(indicator).toHaveAttribute('data-quota-tone', 'safe');
    expect(indicator.textContent).toContain('50/200');
    expect(screen.getByTestId('cost-quota-fill')).toHaveStyle({ width: '25%' });
  });

  it('超过 90% 时变为 danger 色', async () => {
    vi.mocked(api.getCostQuota).mockResolvedValue({
      max_requests_per_day: 100,
      requests_today: 95,
    });
    render(<CostQuotaIndicator />);
    await waitFor(() => expect(screen.getByTestId('cost-quota-indicator')).toHaveAttribute('data-quota-tone', 'danger'));
  });

  it('后端缺失 requests 字段时显示未上报占位', async () => {
    vi.mocked(api.getCostQuota).mockResolvedValue({
      max_tokens_per_day: 1000,
      tokens_today: 10,
    });
    render(<CostQuotaIndicator />);
    expect(await screen.findByText(/未上报/)).toBeInTheDocument();
    expect(screen.getByTestId('cost-quota-indicator')).toHaveAttribute('data-state', 'unreported');
  });

  it('请求失败时同样优雅占位而非报错', async () => {
    vi.mocked(api.getCostQuota).mockRejectedValue(new Error('quota down'));
    render(<CostQuotaIndicator />);
    expect(await screen.findByText(/未上报/)).toBeInTheDocument();
  });

  it('max 为 0 时按未上报处理', async () => {
    vi.mocked(api.getCostQuota).mockResolvedValue({ max_requests_per_day: 0, requests_today: 0 });
    render(<CostQuotaIndicator />);
    expect(await screen.findByText(/未上报/)).toBeInTheDocument();
  });
});
