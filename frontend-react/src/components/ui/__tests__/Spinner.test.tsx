import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/react';
import { Spinner } from '../Spinner';

describe('Spinner', () => {
  it('renders spinner element', () => {
    const { container } = render(<Spinner />);
    expect(container.querySelector('.animate-spin')).not.toBeNull();
  });

  it('applies size classes', () => {
    const { container } = render(<Spinner size="lg" />);
    expect(container.querySelector('.h-8')).not.toBeNull();
  });

  it('applies custom className', () => {
    const { container } = render(<Spinner className="text-red-500" />);
    expect(container.querySelector('.text-red-500')).not.toBeNull();
  });
});
