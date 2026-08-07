import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Helper } from '../Helper';

describe('Helper', () => {
  it('renders children content', () => {
    render(<Helper>Helper Content</Helper>);
    expect(screen.getByText('Helper Content')).toBeInTheDocument();
  });

  it('supports multiple children elements', () => {
    render(
      <Helper>
        <span>Child 1</span>
        <span>Child 2</span>
      </Helper>
    );
    expect(screen.getByText('Child 1')).toBeInTheDocument();
    expect(screen.getByText('Child 2')).toBeInTheDocument();
  });

  it('applies default variant class', () => {
    const { container } = render(<Helper>text</Helper>);
    expect(container.querySelector('p')?.className).toContain('text-[var(--color-text-muted)]');
  });

  it('applies error variant class', () => {
    const { container } = render(<Helper variant="error">text</Helper>);
    expect(container.querySelector('p')?.className).toContain('text-[var(--color-error)]');
  });

  it('applies success variant class', () => {
    const { container } = render(<Helper variant="success">text</Helper>);
    expect(container.querySelector('p')?.className).toContain('text-[var(--color-success)]');
  });

  it('applies warning variant class', () => {
    const { container } = render(<Helper variant="warning">text</Helper>);
    expect(container.querySelector('p')?.className).toContain('text-[var(--color-warning)]');
  });

  it('applies custom className', () => {
    const { container } = render(<Helper className="custom-helper-class">text</Helper>);
    expect(container.querySelector('p')?.className).toContain('custom-helper-class');
  });

  it('renders without errors when no children provided', () => {
    const { container } = render(<Helper />);
    expect(container.firstChild).toBeInTheDocument();
  });

  it('handles complex child structures', () => {
    render(
      <Helper>
        <div className="nested">
          <p>Nested Paragraph</p>
        </div>
      </Helper>
    );
    expect(screen.getByText('Nested Paragraph')).toBeInTheDocument();
  });

  it('allows dynamic children updates', () => {
    const { rerender } = render(<Helper>Initial Content</Helper>);
    expect(screen.getByText('Initial Content')).toBeInTheDocument();

    rerender(<Helper>Updated Content</Helper>);
    expect(screen.getByText('Updated Content')).toBeInTheDocument();
  });

  it('applies base helper classes', () => {
    const { container } = render(<Helper>text</Helper>);
    const p = container.querySelector('p');
    expect(p?.className).toContain('text-xs');
    expect(p?.className).toContain('mt-1');
  });
});
