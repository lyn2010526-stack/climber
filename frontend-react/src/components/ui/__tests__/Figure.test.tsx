import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Figure } from '../Figure';

describe('Figure', () => {
  it('renders with default props', () => {
    const { container } = render(<Figure />);
    expect(container.querySelector('.component')).not.toBeNull();
  });

  it('renders children', () => {
    render(<Figure><span>Figure Content</span></Figure>);
    expect(screen.getByText('Figure Content')).toBeDefined();
  });

  it('applies default variant class', () => {
    const { container } = render(<Figure />);
    const wrapper = container.querySelector('.component');
    expect(wrapper?.className).toContain('component--default');
  });

  it('applies custom variant class', () => {
    const { container } = render(<Figure variant="primary" />);
    const wrapper = container.querySelector('.component');
    expect(wrapper?.className).toContain('component--primary');
  });

  it('applies size class', () => {
    const { container } = render(<Figure size="md" />);
    const wrapper = container.querySelector('.component');
    expect(wrapper?.className).toContain('component--md');
  });

  it('applies disabled class when disabled', () => {
    const { container } = render(<Figure disabled />);
    const wrapper = container.querySelector('.component');
    expect(wrapper?.className).toContain('component--disabled');
  });

  it('applies loading class when loading', () => {
    const { container } = render(<Figure loading />);
    const wrapper = container.querySelector('.component');
    expect(wrapper?.className).toContain('component--loading');
  });

  it('applies custom className', () => {
    const { container } = render(<Figure className="figure-custom" />);
    const wrapper = container.querySelector('.component');
    expect(wrapper?.className).toContain('figure-custom');
  });
});
