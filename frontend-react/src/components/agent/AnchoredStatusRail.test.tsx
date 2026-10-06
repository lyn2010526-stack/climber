import { render, screen } from '@testing-library/react';
import { beforeAll, beforeEach, describe, expect, it } from 'vitest';
import i18n from '../../i18n';
import { resetAnchoredStore, useAnchoredStore } from '../../store/anchored';
import { AnchoredStatusRail } from './AnchoredStatusRail';

function renderRail() {
  return render(<AnchoredStatusRail />);
}

beforeAll(async () => {
  await i18n.changeLanguage('zh-CN');
});

beforeEach(() => {
  resetAnchoredStore();
});

describe('AnchoredStatusRail', () => {
  it('keeps the 24px rail and reads left to right: state, cache hit rate, turn tokens', () => {
    const { container } = renderRail();
    const rail = screen.getByTestId('anchored-status-rail');
    expect(rail).toHaveClass('h-6', 'shrink-0');
    expect(rail).toHaveAttribute('aria-label', 'Agent 状态');

    const text = container.textContent ?? '';
    expect(text.indexOf('等待输入')).toBeLessThan(text.indexOf('缓存命中率'));
    expect(text.indexOf('缓存命中率')).toBeLessThan(text.indexOf('本轮 Token'));
  });

  it.each([
    ['thinking', '思考中', 'text-[var(--color-accent-foreground)]', 'bg-[var(--color-accent-foreground)]', true],
    ['executing_tool', '执行工具', 'text-[var(--color-info)]', 'bg-[var(--color-info)]', true],
    ['awaiting_input', '等待输入', 'text-[var(--color-success)]', 'bg-[var(--color-success)]', false],
    ['error', '异常', 'text-[var(--color-error)]', 'bg-[var(--color-error)]', false],
  ] as const)(
    'renders %s with its fixed token colour and its own motion',
    (state, label, textColor, dotColor, animated) => {
      useAnchoredStore.setState({ agentState: state });
      const { container } = renderRail();
      const rail = screen.getByTestId('anchored-status-rail');
      expect(rail).toHaveAttribute('data-agent-state', state);
      expect(screen.getByText(label)).toBeVisible();

      const stateGroup = screen.getByText(label).parentElement!;
      expect(stateGroup).toHaveClass(textColor);
      const dot = stateGroup.querySelector('[aria-hidden="true"]')!;
      expect(dot).toHaveClass(dotColor);
      expect(dot.className.includes('motion-safe:animate-pulse')).toBe(animated);
      expect(container.querySelectorAll('[class*="animate-pulse"]')).toHaveLength(animated ? 1 : 0);
    },
  );

  it('shows unreported rather than a fabricated value when usage is missing', () => {
    renderRail();
    expect(screen.getByTestId('anchored-status-cache')).toHaveTextContent('未上报');
    expect(screen.getByTestId('anchored-status-tokens')).toHaveTextContent('未上报');
  });

  it('formats only the backend-reported hit rate and token count', () => {
    useAnchoredStore.setState({ cacheHitRate: 0.42, turnTokens: 12345 });
    renderRail();
    expect(screen.getByTestId('anchored-status-cache')).toHaveTextContent('42%');
    expect(screen.getByTestId('anchored-status-tokens')).toHaveTextContent('12,345');
  });
});
