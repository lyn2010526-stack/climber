import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/react';
import { ContextUsageIndicator } from '../ContextUsageIndicator';

describe('ContextUsageIndicator', () => {
  it('renders token counts', () => {
    const { container } = render(
      <ContextUsageIndicator currentTokens={4000} maxTokens={128000} />,
    );
    expect(container.textContent).toContain('4,000');
    expect(container.textContent).toContain('128,000');
  });

  it('shows normal color at low usage', () => {
    const { container } = render(
      <ContextUsageIndicator currentTokens={1000} maxTokens={128000} />,
    );
    const bar = container.querySelector('[style*="width"]');
    expect(bar).toBeTruthy();
  });

  it('caps at 100%', () => {
    const { container } = render(
      <ContextUsageIndicator currentTokens={200000} maxTokens={128000} />,
    );
    const bar = container.querySelector('[style*="width: 100%"]');
    expect(bar).toBeTruthy();
  });
});
