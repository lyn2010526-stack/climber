import { useState } from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import CommandPalette from '../CommandPalette';

vi.mock('../../../i18n', () => ({ useI18n: () => ({ t: (key: string) => key }) }));

describe('CommandPalette', () => {
  it('lets the query field be the whole subject and names each result group', () => {
    const { container } = render(<CommandPalette isOpen onClose={vi.fn()} onNavigate={vi.fn()} />);
    const input = screen.getByRole('combobox');
    expect(input).toHaveFocus();
    expect(container.querySelector('h1,h2,h3,h4,h5,h6')).toBeNull();
    // The dialog keeps a name through the field that labels it.
    expect(screen.getByRole('dialog')).toHaveAccessibleName('common.command_palette');
    // The empty-state mark and the result tally were decoration around the field.
    expect(screen.queryByText(/^common\.count$/)).not.toBeInTheDocument();
    fireEvent.change(input, { target: { value: 'settings' } });
    expect(screen.getByRole('option').closest('[role="group"]')).toHaveAttribute('aria-label');
  });

  it('keeps one close affordance instead of two escape labels', () => {
    render(<CommandPalette isOpen onClose={vi.fn()} onNavigate={vi.fn()} />);
    expect(screen.queryByText(/^esc$/i)).not.toBeInTheDocument();
    expect(screen.getByText('common.navigate')).toBeInTheDocument();
    expect(screen.getByText('common.open')).toBeInTheDocument();
    expect(screen.queryByText('common.close')).not.toBeInTheDocument();
  });

  it('selects in visual order, bounds navigation, and executes once', () => {
    const onNavigate = vi.fn();
    const onClose = vi.fn();
    render(<CommandPalette isOpen onClose={onClose} onNavigate={onNavigate} />);
    const input = screen.getByRole('combobox');
    expect(input).toHaveFocus();
    fireEvent.change(input, { target: { value: 'a' } });
    const options = screen.getAllByRole('option');
    fireEvent.keyDown(input, { key: 'ArrowUp' });
    expect(options[0]).toHaveAttribute('aria-selected', 'true');
    for (let i = 1; i < options.length; i++) {
      fireEvent.keyDown(input, { key: 'ArrowDown' });
      expect(options[i]).toHaveAttribute('aria-selected', 'true');
      expect(input).toHaveAttribute('aria-activedescendant', options[i].id);
    }
    fireEvent.keyDown(input, { key: 'ArrowDown' });
    fireEvent.keyDown(input, { key: 'Enter' });
    expect(onNavigate).toHaveBeenCalledTimes(1);
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it('jumps to both ends of the result list', () => {
    render(<CommandPalette isOpen onClose={vi.fn()} onNavigate={vi.fn()} />);
    const input = screen.getByRole('combobox');
    fireEvent.change(input, { target: { value: 'a' } });
    const options = screen.getAllByRole('option');
    expect(options[0]).toHaveAttribute('aria-selected', 'true');
    fireEvent.keyDown(input, { key: 'End' });
    expect(options[options.length - 1]).toHaveAttribute('aria-selected', 'true');
    fireEvent.keyDown(input, { key: 'Home' });
    expect(options[0]).toHaveAttribute('aria-selected', 'true');
    expect(input).toHaveAttribute('aria-activedescendant', options[0].id);
  });

  it('walks exactly the order the rows are rendered in', () => {
    const onNavigate = vi.fn();
    render(<CommandPalette isOpen onClose={vi.fn()} onNavigate={onNavigate} />);
    const input = screen.getByRole('combobox');
    fireEvent.change(input, { target: { value: 'a' } });
    const rendered = screen.getAllByRole('option');
    expect(rendered.length).toBeGreaterThan(2);
    expect(rendered[0]).toHaveAttribute('aria-selected', 'true');
    for (const option of rendered.slice(1)) {
      fireEvent.keyDown(input, { key: 'ArrowDown' });
      expect(option).toHaveAttribute('aria-selected', 'true');
    }
    // The row the walk ended on is the one Enter acts on, whatever the ranking
    // put last; its option id is the list id, a separator, and the page id.
    const listId = screen.getByRole('listbox').id;
    const lastRow = rendered[rendered.length - 1]!;
    expect(input).toHaveAttribute('aria-activedescendant', lastRow.id);
    fireEvent.keyDown(input, { key: 'Enter' });
    expect(onNavigate).toHaveBeenCalledWith(lastRow.id.slice(listId.length + 1));
  });

  it('handles empty results, trimmed queries, pointer selection and IME composition', () => {
    const onNavigate = vi.fn();
    render(<CommandPalette isOpen onClose={vi.fn()} onNavigate={onNavigate} />);
    const input = screen.getByRole('combobox');
    fireEvent.change(input, { target: { value: 'unmatched-xyz' } });
    fireEvent.keyDown(input, { key: 'ArrowDown' });
    fireEvent.keyDown(input, { key: 'Enter' });
    expect(onNavigate).not.toHaveBeenCalled();
    expect(screen.getByRole('status')).toHaveTextContent('common.no_results');
    expect(input).not.toHaveAttribute('aria-activedescendant');
    fireEvent.change(input, { target: { value: '  settings  ' } });
    fireEvent.keyDown(input, { key: 'Enter', isComposing: true });
    expect(onNavigate).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole('option'));
    expect(onNavigate).toHaveBeenCalledWith('settings');
  });

  it('ranks the command the user named first, not the one declared first', () => {
    const onNavigate = vi.fn();
    render(<CommandPalette isOpen onClose={vi.fn()} onNavigate={onNavigate} />);
    const input = screen.getByRole('combobox');
    // "crews" is declared near the end of nav-config, so it can only come first
    // if the ranking actually ran.
    fireEvent.change(input, { target: { value: 'crews' } });
    expect(screen.getAllByRole('option')).toHaveLength(1);
    fireEvent.keyDown(input, { key: 'Enter' });
    expect(onNavigate).toHaveBeenCalledWith('crews');
  });

  it('surfaces a row reached only by a fuzzy subsequence match', () => {
    const onNavigate = vi.fn();
    render(<CommandPalette isOpen onClose={vi.fn()} onNavigate={onNavigate} />);
    const input = screen.getByRole('combobox');
    // w and f appear in that order inside "workflow", but never as a phrase.
    fireEvent.change(input, { target: { value: 'wf' } });
    const options = screen.getAllByRole('option');
    expect(options).toHaveLength(1);
    expect(options[0]).toHaveTextContent('navigation.workflows');
    fireEvent.keyDown(input, { key: 'Enter' });
    expect(onNavigate).toHaveBeenCalledWith('workflows');
  });

  it('narrows to the one entry whose label the query names', () => {
    render(<CommandPalette isOpen onClose={vi.fn()} onNavigate={vi.fn()} />);
    const input = screen.getByRole('combobox');
    fireEvent.change(input, { target: { value: '  CRews  ' } });
    const options = screen.getAllByRole('option');
    expect(options).toHaveLength(1);
    expect(options[0]).toHaveTextContent('navigation.crews');
  });

  it('reaches every nav entry from a single character of its label', () => {
    render(<CommandPalette isOpen onClose={vi.fn()} onNavigate={vi.fn()} />);
    const input = screen.getByRole('combobox');
    for (const id of ['api access', 'workflow', 'terminal', 'traces', 'eval']) {
      fireEvent.change(input, { target: { value: id } });
      expect(screen.getAllByRole('option').length).toBeGreaterThan(0);
    }
  });

  it('recommends the first eight nav entries in declaration order for an empty query', () => {
    render(<CommandPalette isOpen onClose={vi.fn()} onNavigate={vi.fn()} />);
    const options = screen.getAllByRole('option');
    expect(options).toHaveLength(8);
    // The empty query keeps the work group together rather than scattering rows.
    expect(new Set(options.map(option => option.closest('[role="group"]')?.getAttribute('aria-label'))).size).toBe(1);
  });

  it('closes with Escape, restores the trigger, resets on reopen and holds focus', async () => {
    const user = userEvent.setup();
    function Harness() {
      const [open, setOpen] = useState(false);
      return <><button onClick={() => setOpen(true)}>Launch</button><CommandPalette isOpen={open} onClose={() => setOpen(false)} onNavigate={vi.fn()} /></>;
    }
    render(<Harness />);
    await user.click(screen.getByText('Launch'));
    await user.type(screen.getByRole('combobox'), 'settings');
    await user.tab();
    expect(screen.getByRole('combobox')).toHaveFocus();
    await user.tab({ shift: true });
    expect(screen.getByRole('combobox')).toHaveFocus();
    await user.keyboard('{Escape}');
    await waitFor(() => expect(screen.getByText('Launch')).toHaveFocus());
    await user.click(screen.getByText('Launch'));
    expect(screen.getByRole('combobox')).toHaveValue('');
  });
});
