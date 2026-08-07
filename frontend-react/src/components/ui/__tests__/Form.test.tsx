import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Form } from '../Form';

describe('Form', () => {
  it('renders with default props', () => {
    const { container } = render(<Form />);
    expect(container.querySelector('.component')).not.toBeNull();
  });

  it('renders children', () => {
    render(<Form><span>Form Content</span></Form>);
    expect(screen.getByText('Form Content')).toBeDefined();
  });

  it('applies default variant class', () => {
    const { container } = render(<Form />);
    const wrapper = container.querySelector('.component');
    expect(wrapper?.className).toContain('component--default');
  });

  it('applies custom variant class', () => {
    const { container } = render(<Form variant="primary" />);
    const wrapper = container.querySelector('.component');
    expect(wrapper?.className).toContain('component--primary');
  });

  it('applies size class', () => {
    const { container } = render(<Form size="md" />);
    const wrapper = container.querySelector('.component');
    expect(wrapper?.className).toContain('component--md');
  });

  it('applies disabled class when disabled', () => {
    const { container } = render(<Form disabled />);
    const wrapper = container.querySelector('.component');
    expect(wrapper?.className).toContain('component--disabled');
  });

  it('applies loading class when loading', () => {
    const { container } = render(<Form loading />);
    const wrapper = container.querySelector('.component');
    expect(wrapper?.className).toContain('component--loading');
  });

  it('applies custom className', () => {
    const { container } = render(<Form className="form-custom" />);
    const wrapper = container.querySelector('.component');
    expect(wrapper?.className).toContain('form-custom');
  });
});
