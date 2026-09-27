import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { act, cleanup, fireEvent, render, screen, within } from '@testing-library/react';
import { AdaptiveMobileLayout } from '../components/layout/AdaptiveMobileLayout';
import { SettingsPage } from '../pages/SettingsPage';
import i18n from '../i18n';

/**
 * Accessibility contracts for the defects this round closed.
 *
 * Each case pins a rule that a scan alone cannot guarantee. axe can confirm a
 * control has a name at one moment; it cannot confirm the name is derived from
 * the visible label, that two `aria-current="page"` markers do not both claim
 * to be the current page, or that a dialog restores focus on close. Those are
 * asserted here so a refactor has to break a test rather than quietly regress.
 */

vi.mock('../store/workspace', () => ({ useWorkspaceStore: () => ({ sessions: [] }) }));

const t = (key: string) => key;
vi.mock('../i18n/utils', async importOriginal => {
  const actual = await importOriginal<typeof import('../i18n/utils')>();
  return { ...actual, useI18n: () => ({ t }) };
});

beforeEach(async () => {
  localStorage.setItem('i18next_lng', 'en');
  await i18n.changeLanguage('en');
  window.location.hash = '#settings';
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe('settings section switcher', () => {
  function renderSettings() {
    globalThis.fetch = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes('/auth/me')) {
        return new Response(JSON.stringify({ id: 1, username: 'tester', email: 't@example.com', role: 'user' }), {
          headers: { 'Content-Type': 'application/json' },
        });
      }
      if (url.includes('/settings/')) {
        return new Response(JSON.stringify({ settings: {} }), { headers: { 'Content-Type': 'application/json' } });
      }
      return new Response('{}', { status: 200, headers: { 'Content-Type': 'application/json' } });
    }) as unknown as typeof fetch;
    return render(<SettingsPage />);
  }

  it('marks a section with aria-current="true" and never "page"', () => {
    renderSettings();
    // The shell navigation owns the page-level marker. A section of one page is
    // not a second page, so "page" here would announce two current pages.
    expect(document.querySelectorAll('[aria-current="page"]')).toHaveLength(0);
    const current = document.querySelectorAll('[aria-current="true"]');
    expect(current).toHaveLength(1);
  });

  it('derives each section name from its visible label alone', () => {
    renderSettings();
    const nav = screen.getByRole('navigation', { name: 'settings.section_nav_label' });
    const buttons = within(nav).getAllByRole('button');
    expect(buttons.length).toBeGreaterThan(1);

    for (const button of buttons) {
      const labelledBy = button.getAttribute('aria-labelledby');
      const describedBy = button.getAttribute('aria-describedby');
      expect(labelledBy, 'a section must name itself explicitly').toBeTruthy();
      expect(describedBy, 'a section must point at its hint').toBeTruthy();

      const label = document.getElementById(labelledBy!);
      const description = document.getElementById(describedBy!);
      expect(label, 'aria-labelledby must resolve').toBeTruthy();
      expect(description, 'aria-describedby must resolve').toBeTruthy();

      // WCAG 2.5.3: the accessible name has to contain the visible label, and
      // the hint must stay out of it or the name reads "Notifications
      // Notifications".
      expect(label!.textContent!.trim()).not.toBe('');
      expect(label!.textContent!.trim()).not.toBe(description!.textContent!.trim());
      expect(description!.textContent!.trim()).not.toBe('');
    }
  });

  it('keeps every section hint distinct from its label', () => {
    renderSettings();
    const nav = screen.getByRole('navigation', { name: 'settings.section_nav_label' });
    const labels = within(nav).getAllByRole('button').map(button => {
      const label = document.getElementById(button.getAttribute('aria-labelledby')!)!.textContent!.trim();
      return label;
    });
    expect(new Set(labels).size).toBe(labels.length);
  });
});

describe('mobile navigation sheet', () => {
  function openSheet() {
    render(
      <AdaptiveMobileLayout currentPage="chat" onNavigate={vi.fn()}>
        <div>workspace</div>
      </AdaptiveMobileLayout>,
    );
    fireEvent.click(screen.getByRole('button', { name: 'sidebar.more' }));
    return screen.getByRole('dialog');
  }

  it('dismisses from a labelled dialog, not from a presentation layer', () => {
    const sheet = openSheet();
    // The old markup put onClick on a role="presentation" div, which is
    // announced as nothing and answers to no key.
    expect(document.querySelector('.mobile-sheet-layer[role="presentation"]')).toBeNull();
    expect(document.querySelectorAll('[role="presentation"][onclick]')).toHaveLength(0);
    expect(sheet.tagName.toLowerCase()).toBe('section');
  });

  it('names the sheet from its visible heading', () => {
    const sheet = openSheet();
    const labelledBy = sheet.getAttribute('aria-labelledby');
    expect(labelledBy).toBeTruthy();
    const heading = document.getElementById(labelledBy!);
    expect(heading?.tagName.toLowerCase()).toBe('h2');
    expect(heading?.textContent).toBe('sidebar.all_entries');
  });

  it('closes on a press outside the sheet and keeps the press inside', () => {
    const sheet = openSheet();
    fireEvent.pointerDown(sheet);
    expect(screen.getByRole('dialog')).toBeInTheDocument();

    fireEvent.pointerDown(document.querySelector('.mobile-sheet-backdrop')!);
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });
  it('keeps the dimming layer out of the accessibility tree', () => {
    openSheet();
    const backdrop = document.querySelector('.mobile-sheet-backdrop')!;
    expect(backdrop.getAttribute('aria-hidden')).toBe('true');
    expect(backdrop.hasAttribute('tabindex')).toBe(false);
  });

  it('traps Tab inside the sheet and hands focus back to the trigger', () => {
    openSheet();
    const trigger = screen.getByRole('button', { name: 'sidebar.more' });
    const sheet = screen.getByRole('dialog');
    const stops = Array.from(sheet.querySelectorAll<HTMLElement>('button'));

    // The first stop holds focus, so Tab from the trigger lands inside.
    expect(document.activeElement).toBe(stops[0]);
    expect(sheet.contains(document.activeElement)).toBe(true);

    // Tab past the last stop wraps back to the first instead of escaping.
    stops[stops.length - 1]!.focus();
    fireEvent.keyDown(document, { key: 'Tab' });
    expect(document.activeElement).toBe(stops[0]);

    fireEvent.keyDown(document, { key: 'Escape' });
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    expect(document.activeElement).toBe(trigger);
  });
});

describe('shell chrome', () => {
  it('gives the theme toggle a 44px touch target and a state-bearing name', async () => {
    const [{ ThemeToggle }, { ThemeProvider }] = await Promise.all([
      import('../components/ui/ThemeToggle'),
      import('../hooks/useTheme'),
    ]);
    render(
      <ThemeProvider>
        <ThemeToggle />
      </ThemeProvider>,
    );
    const toggle = screen.getByRole('button');
    // jsdom reports a zero box, so the guarantee is asserted on the class that
    // sets the floor; the pixel measurement lives in the axe sweep, which runs
    // target-size against a real layout.
    expect(toggle.className).toMatch(/\bmin-h-11\b/);
    expect(toggle.className).toMatch(/\bmin-w-11\b/);
    expect(toggle.getAttribute('aria-label')).toMatch(/模式，点击切换/);
  });
});

describe('form field association', () => {
  it('points a field label at the control that has no id of its own', async () => {
    const { FormField } = await import('../components/ui/Field');
    const { Input } = await import('../components/ui/Input');
    render(
      <FormField label="当前密码" required>
        <Input type="password" />
      </FormField>,
    );
    // The required marker is part of the label text, so match on the name the
    // user reads rather than on an exact string.
    const input = screen.getByLabelText(/^当前密码/);
    expect(input.tagName.toLowerCase()).toBe('input');
    // The label and the control have to agree on one id, which is the whole
    // point: a mismatch is what leaves a control with no name.
    expect(input.id).not.toBe('');
    expect(document.querySelector(`label[for="${input.id}"]`)).not.toBeNull();
  });

  it('lets the field target win so label and control cannot drift', async () => {
    const { FormField } = await import('../components/ui/Field');
    const { Input } = await import('../components/ui/Input');
    render(
      <FormField label="固定" htmlFor="fixed-control">
        <Input id="explicit-id" />
      </FormField>,
    );
    // The label is what the user sees, so it decides the target and the control
    // adopts it.
    const input = screen.getByLabelText('固定');
    expect(input).toHaveAttribute('id', 'fixed-control');
  });

  it('associates a switch with its field label', async () => {
    const { FormField } = await import('../components/ui/Field');
    const { Switch } = await import('../components/ui/Switch');
    render(
      <FormField label="自动保存">
        <Switch checked={false} onChange={vi.fn()} />
      </FormField>,
    );
    expect(screen.getByRole('switch', { name: '自动保存' })).toBeInTheDocument();
  });
});

describe('focus trap helper', () => {
  it('skips hidden and explicitly unfocusable stops', async () => {
    const { collectFocusable } = await import('../lib/focusTrap');
    const root = document.createElement('div');
    root.innerHTML = `
      <button id="a">a</button>
      <button id="b" tabindex="-1">b</button>
      <button id="c" aria-hidden="true">c</button>
      <button id="d" hidden>d</button>
      <div inert><button id="e">e</button></div>
      <button id="f" disabled>f</button>
    `;
    document.body.appendChild(root);
    act(() => { root.focus(); });
    const ids = collectFocusable(root).map(node => node.id);
    expect(ids).toEqual(['a']);
    root.remove();
  });

  it('wraps backwards from the first stop to the last', async () => {
    const { trapTab } = await import('../lib/focusTrap');
    const root = document.createElement('div');
    root.tabIndex = -1;
    root.innerHTML =
      '<button id="first">first</button><button id="middle">middle</button><button id="last">last</button>';
    document.body.appendChild(root);
    const first = document.getElementById('first')!;
    const last = document.getElementById('last')!;
    const middle = document.getElementById('middle')!;

    first.focus();
    expect(trapTab(root, true)).toBe(true);
    expect(document.activeElement).toBe(last);

    expect(trapTab(root, false)).toBe(true);
    expect(document.activeElement).toBe(first);

    // A press in the middle needs no handling, so the caller can let the
    // browser move focus itself.
    middle.focus();
    expect(trapTab(root, false)).toBe(false);
    expect(trapTab(root, true)).toBe(false);
    root.remove();
  });

  it('pulls focus to the dialog when it holds no stops at all', async () => {
    const { trapTab } = await import('../lib/focusTrap');
    const root = document.createElement('div');
    root.tabIndex = -1;
    document.body.appendChild(root);
    expect(trapTab(root, false)).toBe(true);
    expect(document.activeElement).toBe(root);
    root.remove();
  });
});
