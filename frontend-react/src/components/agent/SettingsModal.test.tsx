import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { SettingsModal, type SettingsTab } from './SettingsModal';

const TABS: SettingsTab[] = [
  { id: 'general', label: 'General', content: <p>General body</p> },
  { id: 'model', label: 'Model', content: <p>Model body</p> },
  { id: 'advanced', label: 'Advanced', content: <p>Advanced body</p> },
];

describe('SettingsModal', () => {
  it('renders nothing while closed', () => {
    render(<SettingsModal open={false} onClose={vi.fn()} tabs={TABS} />);
    expect(screen.queryByRole('dialog')).toBeNull();
  });

  it('renders a centered dialog with a left rail and right content', () => {
    render(<SettingsModal open onClose={vi.fn()} tabs={TABS} title="Agent settings" />);
    const dialog = screen.getByRole('dialog');
    expect(dialog).toBeVisible();
    expect(screen.getByRole('heading', { name: 'Agent settings' })).toBeVisible();

    const rail = screen.getByTestId('settings-modal-rail');
    expect(rail).toHaveAttribute('aria-orientation', 'vertical');
    const tabs = screen.getAllByRole('tab');
    expect(tabs).toHaveLength(3);
    expect(tabs[0]).toHaveAttribute('aria-selected', 'true');
  });

  it('shows the first tab content by default and switches on selection', () => {
    render(<SettingsModal open onClose={vi.fn()} tabs={TABS} />);
    expect(screen.getByText('General body')).toBeVisible();
    expect(screen.queryByText('Model body')).toBeNull();

    fireEvent.click(screen.getByTestId('settings-modal-tab-model'));
    expect(screen.getByText('Model body')).toBeVisible();
    expect(screen.queryByText('General body')).toBeNull();
    expect(screen.getByTestId('settings-modal-content-model')).toBeVisible();
  });

  it('associates each tab with its panel via aria-controls and aria-labelledby', () => {
    render(<SettingsModal open onClose={vi.fn()} tabs={TABS} />);
    const selected = screen.getByRole('tab', { name: 'General' });
    const panel = screen.getByRole('tabpanel');
    expect(selected).toHaveAttribute('aria-controls', panel.id);
    expect(panel).toHaveAttribute('aria-labelledby', selected.id);
  });

  it('closes through the shared close control', () => {
    const onClose = vi.fn();
    render(<SettingsModal open onClose={onClose} tabs={TABS} />);
    fireEvent.click(screen.getByRole('button', { name: /关闭|close/i }));
    expect(onClose).toHaveBeenCalledOnce();
  });

  it('re-selects the first tab when the active tab disappears', () => {
    const { rerender } = render(<SettingsModal open onClose={vi.fn()} tabs={TABS} />);
    fireEvent.click(screen.getByTestId('settings-modal-tab-advanced'));
    expect(screen.getByText('Advanced body')).toBeVisible();

    rerender(<SettingsModal open onClose={vi.fn()} tabs={TABS.slice(0, 2)} />);
    expect(screen.getByText('General body')).toBeVisible();
  });
});
