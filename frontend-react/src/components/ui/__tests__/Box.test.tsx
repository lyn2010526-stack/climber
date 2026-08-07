import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Box } from '../Box';

describe('Box', () => {
  it('renders with default title', () => {
    const { container } = render(<Box />);
    expect(container.querySelector('h3')?.textContent).toBe('Box');
  });

  it('renders with custom title', () => {
    const { container } = render(<Box title="Custom Box" />);
    expect(container.querySelector('h3')?.textContent).toBe('Custom Box');
  });

  it('renders children', () => {
    render(<Box><span>Box Content</span></Box>);
    expect(screen.getByText('Box Content')).toBeDefined();
  });

  it('applies default variant class', () => {
    const { container } = render(<Box />);
    const wrapper = container.querySelector('.component');
    expect(wrapper?.className).toContain('component--default');
  });

  it('applies custom variant class', () => {
    const { container } = render(<Box variant="danger" />);
    const wrapper = container.querySelector('.component');
    expect(wrapper?.className).toContain('component--danger');
  });

  it('applies size class', () => {
    const { container } = render(<Box size="sm" />);
    const wrapper = container.querySelector('.component');
    expect(wrapper?.className).toContain('component--sm');
  });

  it('applies disabled class when disabled', () => {
    const { container } = render(<Box disabled />);
    const wrapper = container.querySelector('.component');
    expect(wrapper?.className).toContain('component--disabled');
  });

  it('applies loading class when loading', () => {
    const { container } = render(<Box loading />);
    const wrapper = container.querySelector('.component');
    expect(wrapper?.className).toContain('component--loading');
  });

  it('applies custom className', () => {
    const { container } = render(<Box className="box-custom" />);
    const wrapper = container.querySelector('.component');
    expect(wrapper?.className).toContain('box-custom');
  });
});
