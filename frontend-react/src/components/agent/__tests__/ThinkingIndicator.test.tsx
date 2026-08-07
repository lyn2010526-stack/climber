import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ThinkingIndicator, ThinkingDots } from '../ThinkingIndicator';

describe('ThinkingIndicator', () => {
  it('renders without crashing', () => {
    const { container } = render(<ThinkingIndicator />);
    expect(container).toBeDefined();
  });

  it('returns null when isActive is false', () => {
    const { container } = render(<ThinkingIndicator isActive={false} />);
    expect(container.innerHTML).toBe('');
  });

  it('renders thinking text', () => {
    render(<ThinkingIndicator />);
    expect(screen.getByText('思考中')).toBeDefined();
  });

  it('renders custom stage text', () => {
    render(<ThinkingIndicator stage="Custom stage" />);
    expect(screen.getByText(/Custom stage/)).toBeDefined();
  });

  it('renders in compact mode', () => {
    const { container } = render(<ThinkingIndicator compact />);
    expect(container.textContent).toContain('正在分析问题...');
  });

  it('renders with sparkle prop', () => {
    const { container } = render(<ThinkingIndicator sparkle />);
    expect(container.querySelectorAll('svg').length).toBeGreaterThan(1);
  });

  it('renders progress bar', () => {
    const { container } = render(<ThinkingIndicator />);
    expect(container.querySelector('[style*="width: 60%"]')).toBeTruthy();
  });
});

describe('ThinkingDots', () => {
  it('renders without crashing', () => {
    const { container } = render(<ThinkingDots />);
    expect(container).toBeDefined();
  });

  it('renders default text', () => {
    render(<ThinkingDots />);
    expect(screen.getByText(/思考中/)).toBeDefined();
  });

  it('renders custom text', () => {
    render(<ThinkingDots text="Loading" />);
    expect(screen.getByText(/Loading/)).toBeDefined();
  });
});
