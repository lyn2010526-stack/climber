import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Section } from '../Section';

describe('Section', () => {
  it('renders with default props', () => {
    const { container } = render(<Section />);
    expect(container.querySelector('.component')).not.toBeNull();
  });

  it('renders children', () => {
    render(<Section><span>Section Content</span></Section>);
    expect(screen.getByText('Section Content')).toBeDefined();
  });

  it('applies default variant class', () => {
    const { container } = render(<Section />);
    const wrapper = container.querySelector('.component');
    expect(wrapper?.className).toContain('component--default');
  });

  it('applies custom variant class', () => {
    const { container } = render(<Section variant="warning" />);
    const wrapper = container.querySelector('.component');
    expect(wrapper?.className).toContain('component--warning');
  });

  it('applies size class', () => {
    const { container } = render(<Section size="sm" />);
    const wrapper = container.querySelector('.component');
    expect(wrapper?.className).toContain('component--sm');
  });

  it('applies disabled class when disabled', () => {
    const { container } = render(<Section disabled />);
    const wrapper = container.querySelector('.component');
    expect(wrapper?.className).toContain('component--disabled');
  });

  it('applies loading class when loading', () => {
    const { container } = render(<Section loading />);
    const wrapper = container.querySelector('.component');
    expect(wrapper?.className).toContain('component--loading');
  });

  it('applies custom className', () => {
    const { container } = render(<Section className="section-custom" />);
    const wrapper = container.querySelector('.component');
    expect(wrapper?.className).toContain('section-custom');
  });
});
