import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen, within } from '@testing-library/react';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { Button, buttonVariants } from '../Button';
import { Badge, badgeVariants } from '../Badge';
import { Input } from '../Input';
import { FormField } from '../Field';
import { Label } from '../Label';
import { Helper } from '../Helper';
import { Switch } from '../Switch';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '../Tabs';
import { Progress } from '../Progress';
import { Skeleton, SkeletonCard, SkeletonText } from '../Skeleton';
import { Card, cardVariants } from '../Card';
import { PageHeader } from '../PageHeader';
import { statusTones } from '../../../lib/icons';

afterEach(cleanup);

const css = readFileSync(resolve(process.cwd(), 'src/index.css'), 'utf-8');

/** The literal value a token resolves to in one theme block. */
const tokenValue = (name: string, theme: 'dark' | 'light' = 'dark'): string | undefined => {
  const start = theme === 'dark' ? 0 : css.indexOf('[data-theme="light"] {');
  const end = theme === 'dark' ? css.indexOf('[data-theme="light"] {') : css.indexOf('\n}', start);
  return new RegExp(`${name}:\\s*([^;]+);`).exec(css.slice(start, end))?.[1]?.trim();
};

describe('button state matrix', () => {
  it('gives primary a real three-step press, distinct in both themes', () => {
    const primary = buttonVariants({ variant: 'primary' });
    expect(primary).toContain('bg-[var(--color-accent)]');
    expect(primary).toContain('hover:bg-[var(--color-accent-hover)]');
    expect(primary).toContain('active:bg-[var(--color-accent-active)]');
    for (const theme of ['dark', 'light'] as const) {
      const resting = tokenValue('--color-accent', theme);
      const hover = tokenValue('--color-accent-hover', theme);
      const active = tokenValue('--color-accent-active', theme);
      expect(resting, theme).toBeTruthy();
      expect(new Set([resting, hover, active]).size, `${theme} accent press ladder`).toBe(3);
    }
  });

  it('resolves the danger trio to the error hue on every state', () => {
    for (const variant of ['destructive', 'danger'] as const) {
      const classes = buttonVariants({ variant });
      expect(classes, variant).toContain('text-[var(--color-error)]');
      expect(classes, variant).toContain('bg-[var(--color-error-subtle)]');
      expect(classes, variant).toMatch(/hover:bg-\[var\(--color-error\)\]\/\d+/);
      expect(classes, variant).toMatch(/active:bg-\[var\(--color-error\)\]\/\d+/);
      // A faded error fill would still read as a live destructive action.
      expect(classes, variant).toContain('disabled:bg-[var(--color-bg-disabled)]');
    }
  });

  it('keeps secondary on the surface ramp and ghost/quiet fully transparent at rest', () => {
    const secondary = buttonVariants({ variant: 'secondary' });
    expect(secondary).toContain('bg-[var(--color-bg-surface-1)]');
    expect(secondary).toContain('border-[var(--color-border-default)]');
    expect(secondary).toContain('hover:bg-[var(--color-bg-surface-2)]');
    expect(secondary).toContain('active:bg-[var(--color-bg-surface-3)]');
    for (const variant of ['ghost', 'link'] as const) {
      const classes = buttonVariants({ variant });
      expect(classes, variant).toMatch(/(?:^|\s)bg-transparent(?:\s|$)/);
      expect(classes, variant).not.toMatch(/hover:border-\[/);
    }
    // `subtle` is the quiet filled one: transparent at rest would make it a
    // second `ghost` and a filled one would make it a second `secondary`.
    expect(buttonVariants({ variant: 'subtle' })).toMatch(/(?:^|\s)bg-\[var\(--color-bg-surface-2\)\]/);
  });

  it('pairs every disabled variant with the disabled fill and the disabled label', () => {
    for (const variant of ['primary', 'secondary', 'outline', 'ghost', 'subtle', 'destructive', 'danger', 'success', 'link'] as const) {
      const classes = buttonVariants({ variant });
      expect(classes, variant).toContain('disabled:text-[var(--color-text-disabled)]');
      expect(classes, variant).not.toMatch(/disabled:opacity-/);
    }
  });

  it('spends spacing, radius and focus on tokens at every size', () => {
    for (const size of ['xs', 'sm', 'md', 'lg', 'icon', 'icon-sm'] as const) {
      const classes = buttonVariants({ size });
      expect(classes, size).toMatch(/rounded-\[var\(--radius-\w+\)\]/);
      expect(classes, size).not.toMatch(/\brounded-(?:sm|md|lg|xl|full|none)\b/);
    }
    for (const size of ['xs', 'sm', 'md', 'lg'] as const) {
      expect(buttonVariants({ size }), size).toMatch(/text-\[length:var\(--text-/);
    }
  });

  it('disables a pending button and swaps in the spinner without dropping the name', () => {
    const onClick = vi.fn();
    const { container, rerender } = render(<Button loading onClick={onClick}>Save</Button>);
    const button = screen.getByRole('button', { name: 'Save' });
    expect(button).toBeDisabled();
    expect(button).toHaveClass('disabled:bg-[var(--color-bg-disabled)]');
    expect(container.querySelector('svg')).not.toBeNull();
    expect(screen.getByText('Save')).toBeInTheDocument();
    rerender(<Button onClick={onClick}>Save</Button>);
    expect(screen.getByRole('button', { name: 'Save' })).not.toBeDisabled();
  });
});

describe('badge state matrix', () => {
  it('covers every resting status tone, and names the one it cannot hold', () => {
    const mapping: Record<string, string> = {
      error: 'destructive',
      success: 'success',
      warning: 'warning',
      info: 'info',
      queued: 'queued',
      approval: 'approval',
      unknown: 'unknown',
    };
    for (const tone of statusTones) {
      const variant = mapping[tone];
      // `loading` is motion, so a resting label has no honest way to hold it.
      if (tone === 'loading') {
        expect(variant, tone).toBeUndefined();
        continue;
      }
      expect(badgeVariants({ variant }), tone).toBeTruthy();
    }
    // Nothing answers to the tone a badge cannot hold, so a call site that
    // reaches for it lands on the neutral default instead of a status paint.
    const source = readFileSync(resolve(process.cwd(), 'src/components/ui/Badge.tsx'), 'utf8');
    expect(source).not.toMatch(/^\s+loading:\s/m);
  });

  it('keeps unknown and disabled apart on three independent channels', () => {
    const unknown = badgeVariants({ variant: 'unknown' });
    const disabled = badgeVariants({ variant: 'disabled' });
    // Border style: a value that was never reported has no solid edge.
    expect(unknown).toContain('border-dashed');
    expect(disabled).not.toContain('border-dashed');
    // Wash: unknown sits on its own tint, disabled has none at all.
    expect(unknown).toContain('bg-[var(--color-unknown-subtle)]');
    expect(disabled).toMatch(/(?:^|\s)bg-transparent(?:\s|$)/);
    // Label: the muted grey versus the fully dropped text ramp.
    expect(unknown).toContain('text-[var(--color-unknown)]');
    expect(disabled).toContain('text-[var(--color-text-disabled)]');
  });

  it('reserves the pill shape for an explicit opt-in', () => {
    expect(badgeVariants()).toContain('rounded-[var(--radius-sm)]');
    expect(badgeVariants()).not.toContain('rounded-[var(--radius-pill)]');
    expect(badgeVariants({ shape: 'pill' })).toContain('rounded-[var(--radius-pill)]');
    // A status chip may take it; a prose label may not.
    expect(badgeVariants({ variant: 'success', shape: 'pill' })).toContain('rounded-[var(--radius-pill)]');
  });

  it('gives every variant its own colour pair, so no two read as one', () => {
    const hues = ['success', 'warning', 'destructive', 'info', 'queued', 'approval', 'unknown'] as const;
    const classes = hues.map(hue => badgeVariants({ variant: hue }));
    for (const hue of hues) {
      expect(new Set(classes).size, hues.join('/')).toBe(classes.length);
      expect(badgeVariants({ variant: hue }), hue).not.toBe(badgeVariants({ variant: 'default' }));
    }
  });
});

describe('input state matrix', () => {
  const classesOf = (element: HTMLElement) => element.className;

  it('covers resting, hover, focus, invalid, disabled and placeholder', () => {
    const { container, rerender } = render(<Input aria-label="Email" />);
    const input = screen.getByRole('textbox');
    expect(classesOf(input)).toContain('border-[var(--color-border-default)]');
    expect(classesOf(input)).toContain('placeholder:text-[var(--color-text-muted)]');
    expect(classesOf(input)).toContain('enabled:hover:border-[var(--color-border-strong)]');
    expect(classesOf(input)).toContain('focus-visible:border-[var(--color-border-accent)]');
    expect(classesOf(input)).toContain('focus-visible:shadow-[var(--focus-ring)]');
    expect(classesOf(input)).toContain('disabled:bg-[var(--color-bg-disabled)]');
    expect(classesOf(input)).toContain('disabled:text-[var(--color-text-disabled)]');
    // A blanket fade on a field hides the value the user is checking.
    expect(classesOf(input)).not.toMatch(/disabled:opacity-/);
    rerender(<Input aria-label="Email" error="Required" />);
    expect(input).toHaveAttribute('aria-invalid', 'true');
    expect(classesOf(input)).toContain('border-[var(--color-error)]/60');
    expect(classesOf(input)).toContain('bg-[var(--color-error-subtle)]');
    expect(classesOf(input)).toContain('enabled:hover:border-[var(--color-error)]');
    expect(classesOf(input)).toContain('focus-visible:border-[var(--color-error)]');
    expect(container.querySelector('[aria-invalid="true"]')).toBe(input);
  });

  it('routes every status through StatusIcon instead of drawing a glyph locally', () => {
    const source = readFileSync(resolve(process.cwd(), 'src/components/ui/Input.tsx'), 'utf8');
    expect(source).toContain('<StatusIcon tone={statusTone}');
    // `icons.loading`, `icons.error` and `icons.success` are the three ways the
    // component used to bypass the single tone-to-glyph entry point.
    expect(source).not.toMatch(/icons\.(?:loading|error|success)\b/);
  });

  it('reports loading ahead of an outcome, and a rejected value as invalid', () => {
    const { rerender } = render(<Input aria-label="Email" loading error="Required" />);
    const input = screen.getByRole('textbox');
    expect(input).toHaveAttribute('aria-busy', 'true');
    expect(input).toHaveAttribute('aria-invalid', 'true');
    rerender(<Input aria-label="Email" success />);
    expect(screen.getByRole('textbox')).not.toHaveAttribute('aria-busy', 'true');
  });
});

describe('tabs state matrix', () => {
  const setup = () =>
    render(
      <Tabs defaultValue="one">
        <TabsList>
          <TabsTrigger value="one">One</TabsTrigger>
          <TabsTrigger value="two">Two</TabsTrigger>
          <TabsTrigger value="three" disabled>Three</TabsTrigger>
        </TabsList>
        <TabsContent value="one">First</TabsContent>
        <TabsContent value="two">Second</TabsContent>
      </Tabs>
    );

  it('derives the paint and the announced state from the same comparison', () => {
    setup();
    const [one, two] = screen.getAllByRole('tab');
    const selectedPaint = 'bg-[var(--color-accent-subtle)]';
    expect(one).toHaveAttribute('aria-selected', 'true');
    expect(one).toHaveClass(selectedPaint, 'text-[var(--color-accent-foreground)]');
    expect(two).toHaveAttribute('aria-selected', 'false');
    expect(two).not.toHaveClass(selectedPaint);
    // data-state and the roving tabindex have to agree with aria-selected too.
    expect(one).toHaveAttribute('data-state', 'active');
    expect(two).toHaveAttribute('data-state', 'inactive');
    expect(one).toHaveAttribute('tabindex', '0');
    expect(two).toHaveAttribute('tabindex', '-1');
  });

  it('keeps a disabled tab out of the accent even when it is the current one', () => {
    render(
      <Tabs defaultValue="one">
        <TabsList>
          <TabsTrigger value="one" disabled>One</TabsTrigger>
        </TabsList>
        <TabsContent value="one">First</TabsContent>
      </Tabs>
    );
    const tab = screen.getByRole('tab');
    expect(tab).toHaveAttribute('aria-selected', 'true');
    expect(tab).toBeDisabled();
    expect(tab).toHaveClass('text-[var(--color-text-disabled)]');
    // A locked tab painted in the selected colour would claim to be actionable.
    expect(tab).not.toHaveClass('bg-[var(--color-accent-subtle)]');
  });

  it('excludes a disabled tab from arrow-key navigation', () => {
    setup();
    const [one, , three] = screen.getAllByRole('tab');
    one.focus();
    one.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowRight', bubbles: true }));
    expect(three).not.toHaveAttribute('aria-selected', 'true');
  });
});

describe('field, label and helper hierarchy', () => {
  it('steps the label, the description and the hint down one rung each', () => {
    const { container } = render(
      <FormField label="Endpoint" description="Where requests go" hint="Leave blank for the default">
        <Input />
      </FormField>
    );
    const label = screen.getByText('Endpoint');
    expect(label).toHaveClass('text-[var(--color-text-secondary)]');
    expect(screen.getByText('Where requests go')).toHaveClass('text-[var(--color-text-muted)]');
    expect(screen.getByText('Leave blank for the default')).toHaveClass('text-[var(--color-text-muted)]');
    expect(container.querySelector('label')).toHaveClass('text-[length:var(--text-sm)]');
  });

  it('reports an error in the error hue and drops the hint that would compete', () => {
    render(
      <FormField label="Endpoint" hint="Leave blank for the default" error="Already in use">
        <Input error="Already in use" />
      </FormField>
    );
    expect(screen.getAllByText('Already in use').length).toBeGreaterThan(0);
    expect(screen.queryByText('Leave blank for the default')).not.toBeInTheDocument();
    expect(screen.getByText('Already in use')).toHaveClass('text-[var(--color-error)]');
  });

  it('offers a dropped label and helper tone for a retired field', () => {
    render(<><Label tone="disabled">Retired</Label><Helper variant="disabled">Gone</Helper></>);
    expect(screen.getByText('Retired')).toHaveClass('text-[var(--color-text-disabled)]');
    expect(screen.getByText('Gone')).toHaveClass('text-[var(--color-text-disabled)]');
  });
});

describe('switch state matrix', () => {
  it('covers checked, unchecked, focus and disabled without a blanket fade', () => {
    const { container, rerender } = render(<Switch checked onChange={vi.fn()} aria-label="Streaming" />);
    const control = screen.getByRole('switch');
    expect(control).toHaveClass('bg-[var(--color-accent)]', 'border-[var(--color-accent)]');
    expect(control).toHaveClass('enabled:hover:bg-[var(--color-accent-hover)]');
    expect(control).toHaveClass('enabled:active:bg-[var(--color-accent-active)]');
    expect(control).toHaveClass('focus-visible:shadow-[var(--focus-ring)]');
    rerender(<Switch checked={false} onChange={vi.fn()} aria-label="Streaming" />);
    expect(control).toHaveClass('bg-[var(--color-bg-surface-4)]', 'border-[var(--color-border-default)]');
    rerender(<Switch checked disabled onChange={vi.fn()} aria-label="Streaming" />);
    expect(control).toHaveClass('bg-[var(--color-bg-disabled)]', 'border-[var(--color-border-subtle)]');
    // A disabled switch must never reach the accent, or it reads as live.
    expect(control).not.toHaveClass('bg-[var(--color-accent)]');
    expect(control.className).not.toMatch(/opacity-/);
    expect(container.querySelector('span')).toHaveClass('bg-[var(--color-bg-page)]');
  });

  it('drops the label and the description to the disabled ramp with the control', () => {
    render(<Switch label="Streaming" description="Live output" checked disabled onChange={vi.fn()} />);
    expect(screen.getByText('Streaming')).toHaveClass('text-[var(--color-text-disabled)]');
    expect(screen.getByText('Live output')).toHaveClass('text-[var(--color-text-disabled)]');
  });

  it('derives every size from the same knob-plus-travel recipe', () => {
    for (const size of ['sm', 'md', 'lg'] as const) {
      const { container, unmount } = render(<Switch size={size} checked onChange={vi.fn()} aria-label="S" />);
      const control = screen.getByRole('switch');
      // A `--space-*` rung name is not a measurement: `--space-0-5` is 0.125rem
      // and `--space-10` is 2.5rem, so the name has to be resolved through the
      // token table. Reading the name as the number made the recipe unsatisfiable
      // by any class string, and reading a dashed name as 0.1 per unit did the
      // same; both passed or failed for reasons that had nothing to do with the
      // switch.
      const rem = (pattern: RegExp, from: string) => {
        const rung = pattern.exec(from)![1]!;
        const declared = new RegExp(`--space-${rung}:\\s*([\\d.]+)rem`).exec(css);
        if (!declared) throw new Error(`--space-${rung} is not a rem token`);
        return Number.parseFloat(declared[1]!);
      };
      const trackWidth = rem(/w-\[var\(--space-(\d[\d-]*)\)\]/, control.className);
      const trackHeight = rem(/h-\[var\(--space-(\d[\d-]*)\)\]/, control.className);
      const thumb = container.querySelector('span')!;
      const thumbSize = rem(/size-\[var\(--space-(\d[\d-]*)\)\]/, thumb.className);
      const offset = rem(/translate-x-\[var\(--space-(\d[\d-]*)\)\]/, thumb.className);
      // Track width is knob plus travel plus a space of slack at each end, and
      // the checked offset is the travel plus the leading slack. If any of the
      // three rungs were hand-tuned, the knob would drift off centre.
      expect(trackWidth, size).toBeCloseTo(2 * thumbSize + 0.5, 5);
      expect(trackHeight, size).toBeCloseTo(thumbSize + 0.5, 5);
      expect(offset, size).toBeCloseTo(thumbSize + 0.25, 5);
      unmount();
      // The unchecked knob has to rest on the same leading gap it leaves, or the
      // control shunts sideways on the way across. Read the same span again in
      // the other position rather than trusting a class that is not there.
      const { unmount: unmountResting } = render(<Switch size={size} checked={false} onChange={vi.fn()} aria-label="S" />);
      const resting = rem(/translate-x-\[var\(--space-(\d[\d-]*)\)\]/, screen.getByRole('switch').querySelector('span')!.className);
      expect(resting, size).toBeCloseTo(offset - thumbSize, 5);
      expect(offset - thumbSize, size).toBeCloseTo(0.25, 5);
      unmountResting();
    }
  });
});

describe('progress states', () => {
  it('puts a determinate value on the bar and a surface behind it', () => {
    render(<Progress value={42} label="Completion" showLabel />);
    const bar = screen.getByRole('progressbar', { name: 'Completion' });
    expect(bar).toHaveAttribute('aria-valuenow', '42');
    expect(bar).toHaveAttribute('aria-valuemin', '0');
    expect(bar).toHaveAttribute('aria-valuemax', '100');
    expect(bar).toHaveStyle({ backgroundColor: 'var(--color-bg-surface-3)' });
    expect(bar.querySelector('div')).toHaveStyle({ width: '42%', backgroundColor: 'var(--color-accent)' });
    expect(screen.getByText('42%')).toBeInTheDocument();
  });

  it('withholds the value entirely when the run cannot be measured', () => {
    const { rerender } = render(<Progress value={0} indeterminate label="Streaming" showLabel />);
    const bar = screen.getByRole('progressbar', { name: 'Streaming' });
    expect(bar).not.toHaveAttribute('aria-valuenow');
    expect(bar).not.toHaveAttribute('aria-valuemin');
    expect(bar).not.toHaveAttribute('aria-valuemax');
    expect(bar).toHaveAttribute('aria-valuetext', 'In progress');
    // No number, because there is no number: a bar that announced 0% would be
    // reporting a stall it cannot see.
    expect(screen.queryByText('0%')).not.toBeInTheDocument();
    expect(bar.querySelector('div')).toHaveClass('motion-safe:animate-pulse');
    rerender(<Progress value={0} indeterminate variant="circular" label="Streaming" showLabel />);
    const ring = screen.getByRole('progressbar', { name: 'Streaming' });
    expect(ring).not.toHaveAttribute('aria-valuenow');
    expect(ring).toHaveAttribute('aria-valuetext', 'In progress');
  });

  it('never tints the track with the fill hue', () => {
    const source = readFileSync(resolve(process.cwd(), 'src/components/ui/Progress.tsx'), 'utf8');
    const trackMap = source.slice(source.indexOf('const colorTrackMap'), source.indexOf('const heightMap'));
    for (const hue of ['success', 'warning', 'danger', 'info', 'unknown', 'accent']) {
      expect(trackMap, hue).not.toContain(`--color-${hue}`);
    }
    expect(trackMap).toContain('var(--color-bg-surface-3)');
  });
});

describe('skeleton construction', () => {
  it('shimmers between two surfaces with no gradient anywhere', () => {
    const source = readFileSync(resolve(process.cwd(), 'src/components/ui/Skeleton.tsx'), 'utf8');
    expect(source).not.toMatch(/gradient/);
    expect(source).toContain('bg-[var(--color-bg-surface-3)]');
    expect(source).toContain('bg-[var(--color-bg-surface-2)]');
    const { container } = render(<Skeleton />);
    const [sunk, lit] = Array.from(container.querySelectorAll('span'));
    expect(sunk).toHaveClass('bg-[var(--color-bg-surface-3)]');
    expect(lit).toHaveClass('bg-[var(--color-bg-surface-2)]', 'animate-pulse');
    expect(container.firstChild).toHaveClass('overflow-hidden');
  });

  it('renders a still placeholder when motion is off', () => {
    const { container } = render(<Skeleton animated={false} width={100} />);
    expect(container.firstChild).toHaveAttribute('aria-hidden', 'true');
    expect(container.querySelector('.animate-pulse')).toBeNull();
    expect(container.querySelectorAll('span').length).toBe(1);
  });

  it('spends radius and padding on tokens in the composite placeholders', () => {
    const { container } = render(<><SkeletonCard /><SkeletonText count={2} /></>);
    expect(container.querySelectorAll('[class*="gradient"]').length).toBe(0);
    expect(container.innerHTML).toMatch(/rounded-\[var\(--radius-lg\)\]/);
    expect(container.innerHTML).toMatch(/p-\[var\(--space-4\)\]/);
  });
});

describe('card structure', () => {
  it('lets the border carry the structure on every variant', () => {
    for (const variant of ['default', 'elevated', 'bordered', 'glass', 'outline', 'filled', 'gradient', 'interactive'] as const) {
      const classes = cardVariants({ variant });
      expect(classes, variant).toContain('border-[var(--color-border-default)]');
      expect(classes, variant).toMatch(/rounded-\[var\(--radius-lg\)\]/);
    }
  });

  it('confines a shadow to the single panel rung and keeps every name flat', () => {
    const withShadow = ['default', 'elevated', 'glass', 'gradient', 'interactive'] as const;
    for (const variant of withShadow) {
      expect(cardVariants({ variant }), variant).toContain('shadow-[var(--shadow-panel)]');
    }
    for (const variant of ['bordered', 'filled', 'outline'] as const) {
      expect(cardVariants({ variant }), variant).not.toMatch(/shadow-/);
    }
    // `glass` and `gradient` are legacy names. They resolve to a flat panel and
    // must not reintroduce a frosted highlight or a ramp.
    for (const variant of ['glass', 'gradient'] as const) {
      const classes = cardVariants({ variant });
      expect(classes, variant).not.toMatch(/blur|backdrop/);
      expect(classes, variant).not.toMatch(/gradient/);
    }
  });

  it('spends padding on the space ladder', () => {
    expect(cardVariants({ padding: 'none' })).toBe('');
    for (const [padding, token] of [['sm', '--space-3'], ['md', '--space-4'], ['lg', '--space-6'], ['xl', '--space-8']] as const) {
      expect(cardVariants({ padding }), padding).toBe(`p-[var(${token})]`);
    }
  });

  it('paints a rendered card with both axes at once', () => {
    // The two axes are joined by `cardVariants`, so a card the component paints
    // has to carry its structure and its interior together, at the documented
    // default interior.
    const { container, rerender } = render(<Card data-testid="c">Body</Card>);
    const card = container.firstChild as HTMLElement;
    expect(card).toHaveClass('border-[var(--color-border-default)]', 'p-[var(--space-4)]');
    expect(screen.getByTestId('c')).toBe(card);
    rerender(<Card variant="bordered" padding="none">Body</Card>);
    expect(container.firstChild).toHaveClass('bg-[var(--color-bg-surface-2)]', 'border-[var(--color-border-default)]');
    // A bare frame carries no interior and no shadow.
    expect(container.firstChild?.className).not.toMatch(/\bp-\[var\(--space-|shadow-\[var\(--shadow-/);
  });
});

describe('page header hierarchy', () => {
  it('puts the title on the bright rung and every line under it one step down', () => {
    const { container } = render(
      <PageHeader
        title="Agents"
        description="Everything running on the cluster"
        breadcrumbs={[{ label: 'Home' }, { label: 'Agents' }]}
      />
    );
    const title = screen.getByRole('heading', { level: 1 });
    expect(title).toHaveTextContent('Agents');
    expect(title).toHaveClass('text-[var(--color-text-primary)]', 'text-[length:var(--text-xl)]');
    expect(title.className).not.toMatch(/style=/);
    expect(screen.getByText('Everything running on the cluster')).toHaveClass('text-[var(--color-text-secondary)]');
    // A trail is the quietest thing in the header, and the current page still
    // has to outrank the ancestors it sits among.
    expect(screen.getByText('Home')).toHaveClass('text-[var(--color-text-muted)]');
    expect(screen.getByText('Agents', { selector: 'nav span' })).toHaveClass('text-[var(--color-text-secondary)]');
    expect(container.querySelector('header')).toHaveClass('mb-[var(--space-5)]');
  });
});

describe('token discipline across the base control layer', () => {
  const files = [
    'Button.tsx', 'Badge.tsx', 'Input.tsx', 'Field.tsx', 'Label.tsx', 'Helper.tsx',
    'Switch.tsx', 'Tabs.tsx', 'Progress.tsx', 'Skeleton.tsx', 'Card.tsx', 'PageHeader.tsx',
  ];

  it('spends no raw palette, radius, shadow or Tailwind scale on radius and shadow', () => {
    for (const file of files) {
      const source = readFileSync(resolve(process.cwd(), 'src/components/ui', file), 'utf8');
      const code = source.split('\n').map(line => line.replace(/\/\/.*$/, '')).join('\n');
      expect(code, file).not.toMatch(/#[0-9a-fA-F]{3,8}\b/);
      expect(code, file).not.toMatch(/\brgba?\(/);
      expect(code, file).not.toMatch(/\b(?:bg|text|border|ring|shadow|fill|stroke|outline|divide|from|via|to|placeholder)-(?:red|blue|green|teal|cyan|slate|gray|zinc|neutral|stone|amber|yellow|violet|purple|pink|rose|indigo|emerald|lime|orange|fuchsia|sky)-\d{2,3}\b/);
      // Radius and shadow are the two scales most often hand-tuned; both are
      // token-only, and `rounded-none` stands for the zero rung.
      expect(code, file).not.toMatch(/\brounded-(?:sm|md|lg|xl|2xl|3xl|full)\b/);
      expect(code, file).not.toMatch(/\bshadow-(?:sm|md|lg|xl|2xl|inner|none)\b/);
    }
  });

  it('resolves every token a base control names, in both themes', () => {
    const declared = new Set([...css.matchAll(/(--[a-z0-9-]+)\s*:/g)].map(match => match[1]!));
    const lightStart = css.indexOf('[data-theme="light"] {');
    const lightEnd = css.indexOf('\n}', lightStart);
    const lightDeclared = new Set([...css.slice(lightStart, lightEnd).matchAll(/(--[a-z0-9-]+)\s*:/g)].map(match => match[1]!));
    for (const file of files) {
      const source = readFileSync(resolve(process.cwd(), 'src/components/ui', file), 'utf8');
      for (const match of source.matchAll(/var\((--[a-z0-9-]+)\)/g)) {
        expect(declared.has(match[1]!), `${file} ${match[1]}`).toBe(true);
      }
      // A `--color-*` token a control paints with has to be restated for the
      // light theme, or switching themes leaves the dark value on screen.
      for (const match of source.matchAll(/(bg|text|border)-\[var\((--color-[\w-]+)\)\]/g)) {
        expect(lightDeclared.has(match[2]!), `${file} ${match[2]} in light`).toBe(true);
      }
    }
  });

  it('keeps every variant name a caller can already pass', () => {
    // The CVA surface is the compatibility contract: existing call sites pass
    // these names and their meaning must not move under them.
    for (const variant of ['primary', 'secondary', 'outline', 'ghost', 'subtle', 'destructive', 'danger', 'success', 'link'] as const) {
      expect(buttonVariants({ variant }), variant).toBeTruthy();
    }
    for (const variant of ['default', 'secondary', 'primary', 'success', 'warning', 'destructive', 'info', 'unknown', 'outline', 'disabled', 'queued', 'approval'] as const) {
      expect(badgeVariants({ variant }), variant).toBeTruthy();
    }
    for (const variant of ['default', 'elevated', 'bordered', 'glass', 'outline', 'filled', 'gradient', 'interactive'] as const) {
      expect(cardVariants({ variant }), variant).toBeTruthy();
    }
  });

  it('keeps the render count of a control that carries no icon at zero', () => {
    const { container } = render(<div><Button>Save</Button><Badge>Ready</Badge></div>);
    // An absent status must resolve to no glyph at all, never a placeholder.
    expect(within(container).queryAllByRole('img')).toHaveLength(0);
    expect(container.querySelectorAll('svg')).toHaveLength(0);
  });
});
