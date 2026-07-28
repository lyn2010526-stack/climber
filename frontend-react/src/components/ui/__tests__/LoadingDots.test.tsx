import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/react';
import { LoadingDots } from '../LoadingDots';

describe('LoadingDots', () => {
  it('renders three dots', () => {
    render(<LoadingDots />);
    const dots = document.querySelectorAll('.animate-loading-dots');
    expect(dots.length).toBe(3);
  });

  it('applies custom className', () => {
    render(<LoadingDots className="text-red-500" />);
    const container = document.querySelector('.text-red-500');
    expect(container).not.toBeNull();
  });

  it('renders different sizes', () => {
    const { rerender } = render(<LoadingDots size="sm" />);
    let dots = document.querySelectorAll('.w-1.h-1');
    expect(dots.length).toBe(3);

    rerender(<LoadingDots size="lg" />);
    dots = document.querySelectorAll('.w-2.h-2');
    expect(dots.length).toBe(3);
  });
});
