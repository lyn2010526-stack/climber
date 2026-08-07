import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Error } from '../Error';

describe('Error', () => {
  it('renders with default title', () => {
    const { container } = render(<Error />);
    expect(container.querySelector('h3')?.textContent).toBe('Error');
  });

  it('renders with custom title', () => {
    const { container } = render(<Error title="Error Title" />);
    expect(container.querySelector('h3')?.textContent).toBe('Error Title');
  });

  it('renders children', () => {
    render(<Error><span>Error Content</span></Error>);
    expect(screen.getByText('Error Content')).toBeDefined();
  });

  it('applies default variant class', () => {
    const { container } = render(<Error />);
    const wrapper = container.querySelector('.component');
    expect(wrapper?.className).toContain('component--default');
  });

  it('applies custom variant class', () => {
    const { container } = render(<Error variant="danger" />);
    const wrapper = container.querySelector('.component');
    expect(wrapper?.className).toContain('component--danger');
  });

  it('applies size class', () => {
    const { container } = render(<Error size="md" />);
    const wrapper = container.querySelector('.component');
    expect(wrapper?.className).toContain('component--md');
  });

  it('applies disabled class when disabled', () => {
    const { container } = render(<Error disabled />);
    const wrapper = container.querySelector('.component');
    expect(wrapper?.className).toContain('component--disabled');
  });

  it('applies loading class when loading', () => {
    const { container } = render(<Error loading />);
    const wrapper = container.querySelector('.component');
    expect(wrapper?.className).toContain('component--loading');
  });

  it('applies custom className', () => {
    const { container } = render(<Error className="error-custom" />);
    const wrapper = container.querySelector('.component');
    expect(wrapper?.className).toContain('error-custom');
  });
});
