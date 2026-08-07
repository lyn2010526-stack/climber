import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Caption } from '../Caption';

describe('Caption', () => {
  it('renders with default title', () => {
    const { container } = render(<Caption />);
    expect(container.querySelector('h3')?.textContent).toBe('Caption');
  });

  it('renders with custom title', () => {
    const { container } = render(<Caption title="My Caption" />);
    expect(container.querySelector('h3')?.textContent).toBe('My Caption');
  });

  it('renders children', () => {
    render(<Caption><span>Caption Text</span></Caption>);
    expect(screen.getByText('Caption Text')).toBeDefined();
  });

  it('applies default variant class', () => {
    const { container } = render(<Caption />);
    const wrapper = container.querySelector('.component');
    expect(wrapper?.className).toContain('component--default');
  });

  it('applies custom variant class', () => {
    const { container } = render(<Caption variant="success" />);
    const wrapper = container.querySelector('.component');
    expect(wrapper?.className).toContain('component--success');
  });

  it('applies size class', () => {
    const { container } = render(<Caption size="md" />);
    const wrapper = container.querySelector('.component');
    expect(wrapper?.className).toContain('component--md');
  });

  it('applies disabled class when disabled', () => {
    const { container } = render(<Caption disabled />);
    const wrapper = container.querySelector('.component');
    expect(wrapper?.className).toContain('component--disabled');
  });

  it('applies loading class when loading', () => {
    const { container } = render(<Caption loading />);
    const wrapper = container.querySelector('.component');
    expect(wrapper?.className).toContain('component--loading');
  });

  it('applies custom className', () => {
    const { container } = render(<Caption className="caption-custom" />);
    const wrapper = container.querySelector('.component');
    expect(wrapper?.className).toContain('caption-custom');
  });
});
