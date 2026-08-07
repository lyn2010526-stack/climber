import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Divider } from '../Divider';

describe('Divider', () => {
  it('renders label as title', () => {
    render(<Divider label="Default" />);
    expect(screen.getByText('Default')).toBeInTheDocument();
  });

  it('renders with custom label', () => {
    render(<Divider label="Custom Label" />);
    expect(screen.getByText('Custom Label')).toBeInTheDocument();
  });

  it('renders horizontal divider by default', () => {
    const { container } = render(<Divider />);
    expect(container.firstChild?.className).toContain('h-px');
    expect(container.firstChild?.className).toContain('w-full');
  });

  it('renders vertical divider when orientation is vertical', () => {
    const { container } = render(<Divider orientation="vertical" />);
    expect(container.firstChild?.className).toContain('w-px');
    expect(container.firstChild?.className).toContain('h-full');
  });

  it('renders with lines when label is provided', () => {
    const { container } = render(<Divider label="Title" />);
    expect(container.querySelectorAll('.h-px')).toHaveLength(2);
  });

  it('applies custom className', () => {
    const { container } = render(<Divider className="custom-divider-class" />);
    expect(container.firstChild?.className).toContain('custom-divider-class');
  });

  it('renders without errors when no props provided', () => {
    const { container } = render(<Divider />);
    expect(container.firstChild).toBeInTheDocument();
  });

  it('passes className to labelled divider', () => {
    const { container } = render(<Divider label="Title" className="custom-labelled-class" />);
    expect(container.firstChild?.className).toContain('custom-labelled-class');
  });
});
