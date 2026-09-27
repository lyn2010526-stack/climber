import { createRef } from 'react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { Button, buttonVariants } from '../Button';
import { Badge } from '../Badge';
import { Input } from '../Input';
import { FormField } from '../Field';
import { icons, iconSizes } from '../../../lib/icons';

afterEach(cleanup);

describe('control visual foundation', () => {
  it.each(Object.entries(iconSizes))('uses the %s icon size for a loading button', (size, pixels) => {
    const onClick = vi.fn();
    const { container } = render(<Button size={size as keyof typeof iconSizes} loading onClick={onClick}>Save</Button>);
    const button = screen.getByRole('button', { name: 'Save' });
    expect(button).toBeDisabled();
    expect(button).toHaveAttribute('aria-busy', 'true');
    expect(container.querySelector('svg')).toHaveAttribute('width', String(pixels));
    expect(container.querySelector('svg')).toHaveAttribute('aria-hidden', 'true');
    expect(container.querySelector('svg')).toHaveClass('motion-reduce:animate-none');
    fireEvent.click(button);
    expect(onClick).not.toHaveBeenCalled();
  });

  it('retains button refs, submit type, custom icons and class overrides', () => {
    const ref = createRef<HTMLButtonElement>();
    const { rerender } = render(<Button ref={ref} type="submit" className="h-12" icon={<icons.success data-testid="custom-icon" />} loading>Save</Button>);
    rerender(<Button ref={ref} type="submit" className="h-12" icon={<icons.success data-testid="custom-icon" />}>Save</Button>);
    expect(ref.current).toBe(screen.getByRole('button', { name: 'Save' }));
    expect(ref.current).toHaveAttribute('type', 'submit');
    expect(ref.current).not.toBeDisabled();
    expect(ref.current).not.toHaveAttribute('aria-busy', 'true');
    expect(ref.current).toHaveClass('h-12');
    expect(ref.current).not.toHaveClass('h-[var(--control-height-md)]');
    expect(screen.getByTestId('custom-icon')).toBeInTheDocument();
    expect(buttonVariants({ size: 'icon-sm' })).toContain('w-[var(--control-height-sm)]');
    expect(buttonVariants({ size: 'icon' })).toContain('w-[var(--control-height-md)]');
  });

  it('keeps explicit disabled and caller busy states', () => {
    render(<Button disabled aria-busy="true">Save</Button>);
    expect(screen.getByRole('button')).toBeDisabled();
    expect(screen.getByRole('button')).toHaveAttribute('aria-busy', 'true');
  });

  it('preserves badge content, semantics and custom icons', () => {
    const ref = createRef<HTMLSpanElement>();
    render(<Badge ref={ref} variant="success" size="xs" icon={<icons.success data-testid="badge-icon" />} className="gap-3">Ready</Badge>);
    expect(ref.current).toHaveClass('text-[var(--color-success)]', 'gap-3');
    expect(ref.current).not.toHaveClass('gap-[var(--control-gap-compact)]');
    expect(screen.getByTestId('badge-icon')).toBeInTheDocument();
    expect(screen.getByText('Ready')).toBeInTheDocument();
  });

  it('associates errors and hints while preserving caller descriptions and refs', () => {
    const ref = createRef<HTMLInputElement>();
    const { rerender } = render(<Input ref={ref} id="email" aria-label="Email" aria-describedby="external" error="Invalid email" hint="Use work email" />);
    const input = screen.getByRole('textbox');
    expect(ref.current).toBe(input);
    expect(input).toHaveAttribute('aria-invalid', 'true');
    expect(input).toHaveAttribute('aria-describedby', 'external email-message');
    expect(screen.getByText('Invalid email')).toHaveAttribute('id', 'email-message');
    expect(screen.queryByText('Use work email')).not.toBeInTheDocument();
    rerender(<Input id="email" aria-label="Email" aria-describedby="external" hint="Use work email" />);
    expect(input).not.toHaveAttribute('aria-invalid');
    expect(screen.getByText('Use work email')).toHaveAttribute('id', 'email-message');
    rerender(<Input id="email" aria-label="Email" aria-describedby="external" aria-invalid="grammar" />);
    expect(input).toHaveAttribute('aria-describedby', 'external');
    expect(input).toHaveAttribute('aria-invalid', 'grammar');
  });

  it('generates unique stable description IDs', () => {
    const { rerender } = render(<><Input aria-label="First" hint="First hint" /><Input aria-label="Second" hint="Second hint" /></>);
    const first = screen.getByLabelText('First');
    const second = screen.getByLabelText('Second');
    const id = first.id;
    expect(first.id).not.toBe(second.id);
    expect(first).toHaveAttribute('aria-describedby', screen.getByText('First hint').id);
    rerender(<><Input aria-label="First" hint="Changed hint" /><Input aria-label="Second" hint="Second hint" /></>);
    expect(first.id).toBe(id);
  });

  it('exposes password toggle state and disables it with the input', () => {
    const { rerender } = render(<Input type="password" aria-label="Secret" error="Required" />);
    const input = screen.getByLabelText('Secret');
    const toggle = screen.getByRole('button', { name: 'Show password' });
    expect(toggle).toHaveAttribute('type', 'button');
    expect(toggle).toHaveAttribute('aria-controls', input.id);
    expect(toggle).toHaveAttribute('aria-pressed', 'false');
    // A password field with a status glyph carries two trailing controls, so
    // its right inset is the wide rung: half a space, the reveal button, a
    // quarter space, the glyph, and half a space back to the edge.
    expect(input).toHaveClass('pr-[var(--space-16)]');
    fireEvent.click(toggle);
    expect(input).toHaveAttribute('type', 'text');
    expect(toggle).toHaveAttribute('aria-pressed', 'true');
    fireEvent.click(toggle);
    expect(input).toHaveAttribute('type', 'password');
    rerender(<Input type="password" aria-label="Secret" disabled />);
    expect(toggle).toBeDisabled();
    fireEvent.click(toggle);
    expect(input).toHaveAttribute('type', 'password');
  });

  it('reports input loading without preventing edits and preserves icon precedence', () => {
    const onChange = vi.fn();
    const { container, rerender } = render(<Input aria-label="Search" loading onChange={onChange} icon={<span>legacy</span>} leftIcon={<span>left</span>} rightIcon={<span>right</span>} />);
    const input = screen.getByRole('textbox');
    expect(input).toHaveAttribute('aria-busy', 'true');
    expect(input).not.toBeDisabled();
    fireEvent.change(input, { target: { value: 'query' } });
    expect(onChange).toHaveBeenCalledOnce();
    expect(screen.getByText('left')).toBeInTheDocument();
    expect(screen.queryByText('legacy')).not.toBeInTheDocument();
    expect(screen.queryByText('right')).not.toBeInTheDocument();
    expect(container.querySelector('svg')).toHaveAttribute('aria-hidden', 'true');
    rerender(<Input aria-label="Search" rightIcon={<span>right</span>} />);
    expect(input).not.toHaveAttribute('aria-busy', 'true');
    expect(screen.getByText('right')).toBeInTheDocument();
  });

  it('keeps density, visible focus and reduced-motion CSS contracts', () => {
    const css = readFileSync(resolve(process.cwd(), 'src/index.css'), 'utf-8');
    for (const [name, value] of Object.entries({ xs: '2rem', sm: '2.25rem', md: '2.5rem', lg: '2.75rem' })) {
      expect(css).toContain(`--control-height-${name}: ${value};`);
    }
    expect(css).toContain('--control-height: 44px;');
    expect(css).toContain('--control-gap-compact: 0.25rem;');
    expect(css).toContain('--control-gap: 0.5rem;');
    for (const [name, pixels] of Object.entries(iconSizes)) {
      expect(css).toContain(`--icon-${name}: ${pixels / 16}rem;`);
    }
    expect(css).toMatch(/:focus-visible\s*\{[^}]*outline: 2px solid var\(--color-accent-foreground\)/);
    expect(css).toMatch(/@media \(prefers-reduced-motion: reduce\)[\s\S]*animation-delay: 0ms !important;[\s\S]*transition-delay: 0ms !important;/);
  });

  it('lets the field own one message, and points the control at that one node', () => {
    const { container } = render(
      <FormField label="Endpoint" description="Where requests go" hint="Leave blank for the default" error="Already in use">
        <Input error="Already in use" />
      </FormField>
    );
    const input = screen.getByRole('textbox');
    // One sentence, one node. A control that redraws the field's message shows
    // it twice and reads it twice.
    expect(screen.getAllByText('Already in use')).toHaveLength(1);
    // The hint loses to the error rather than competing with it.
    expect(screen.queryByText('Leave blank for the default')).not.toBeInTheDocument();
    // Both the description and the error are announced, and every id the
    // control names has to resolve to a node that is actually on screen.
    const named = (input.getAttribute('aria-describedby') ?? '').split(' ').filter(Boolean);
    expect(named).toHaveLength(2);
    for (const id of named) {
      expect(container.querySelector(`#${CSS.escape(id)}`), id).not.toBeNull();
    }
    expect(screen.getByText('Where requests go').id).toBe(named[0]);
    expect(screen.getByText('Already in use').id).toBe(named[1]);
  });

  it('still renders and announces the message for an input standing alone', () => {
    // Nothing owns the text out here, so the control has to.
    render(<Input aria-label="Endpoint" error="Already in use" />);
    const input = screen.getByRole('textbox');
    const message = screen.getByText('Already in use');
    expect(input.getAttribute('aria-describedby')).toBe(message.id);
  });
});
