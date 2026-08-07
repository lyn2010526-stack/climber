import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Summary } from '../Summary';

describe('Summary', () => {
  it('renders with default props', () => {
    const { container } = render(<Summary />);
    expect(container.querySelector('.component')).not.toBeNull();
  });

  it('renders children', () => {
    render(<Summary><span>Summary Content</span></Summary>);
    expect(screen.getByText('Summary Content')).toBeDefined();
  });

  it('applies default variant class', () => {
    const { container } = render(<Summary />);
    const wrapper = container.querySelector('.component');
    expect(wrapper?.className).toContain('component--default');
  });

  it('applies custom variant class', () => {
    const { container } = render(<Summary variant="info" />);
    const wrapper = container.querySelector('.component');
    expect(wrapper?.className).toContain('component--info');
  });

  it('applies size class', () => {
    const { container } = render(<Summary size="lg" />);
    const wrapper = container.querySelector('.component');
    expect(wrapper?.className).toContain('component--lg');
  });

  it('applies disabled class when disabled', () => {
    const { container } = render(<Summary disabled />);
    const wrapper = container.querySelector('.component');
    expect(wrapper?.className).toContain('component--disabled');
  });

  it('applies loading class when loading', () => {
    const { container } = render(<Summary loading />);
    const wrapper = container.querySelector('.component');
    expect(wrapper?.className).toContain('component--loading');
  });

  it('applies custom className', () => {
    const { container } = render(<Summary className="summary-custom" />);
    const wrapper = container.querySelector('.component');
    expect(wrapper?.className).toContain('summary-custom');
  });
});
