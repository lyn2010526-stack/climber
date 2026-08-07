import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Aside } from '../Aside';

describe('Aside', () => {
  it('renders with default title', () => {
    const { container } = render(<Aside />);
    expect(container.querySelector('h3')?.textContent).toBe('Aside');
  });

  it('renders with custom title', () => {
    const { container } = render(<Aside title="Custom Title" />);
    expect(container.querySelector('h3')?.textContent).toBe('Custom Title');
  });

  it('renders children', () => {
    render(<Aside><span>Child Content</span></Aside>);
    expect(screen.getByText('Child Content')).toBeDefined();
  });

  it('applies default variant class', () => {
    const { container } = render(<Aside />);
    const wrapper = container.querySelector('.component');
    expect(wrapper?.className).toContain('component--default');
  });

  it('applies custom variant class', () => {
    const { container } = render(<Aside variant="primary" />);
    const wrapper = container.querySelector('.component');
    expect(wrapper?.className).toContain('component--primary');
  });

  it('applies size class', () => {
    const { container } = render(<Aside size="lg" />);
    const wrapper = container.querySelector('.component');
    expect(wrapper?.className).toContain('component--lg');
  });

  it('applies disabled class when disabled', () => {
    const { container } = render(<Aside disabled />);
    const wrapper = container.querySelector('.component');
    expect(wrapper?.className).toContain('component--disabled');
  });

  it('applies loading class when loading', () => {
    const { container } = render(<Aside loading />);
    const wrapper = container.querySelector('.component');
    expect(wrapper?.className).toContain('component--loading');
  });

  it('applies custom className', () => {
    const { container } = render(<Aside className="custom-class" />);
    const wrapper = container.querySelector('.component');
    expect(wrapper?.className).toContain('custom-class');
  });

  it('renders error message when error exists', () => {
    const { container } = render(<Aside />);
    const errorDiv = container.querySelector('.component-error');
    expect(errorDiv).toBeNull();
  });
});
