import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import i18n from '../../i18n';
import { RawRenderedToggle, formatRaw } from './RawRenderedToggle';

afterEach(() => cleanup());

describe('RawRenderedToggle', () => {
  it('shows the rendered pane by default and the raw pane on demand', () => {
    render(<RawRenderedToggle rendered={<span>Hello rendered</span>} raw={{ a: 1 }} />);
    expect(screen.getByText('Hello rendered')).toBeVisible();
    expect(screen.queryByTestId('raw-payload')).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole('tab', { name: i18n.t('content_view.raw', { defaultValue: 'Raw' }) }));
    expect(screen.getByTestId('raw-payload')).toBeVisible();
    expect(screen.getByText(/"a": 1/)).toBeVisible();
    expect(screen.queryByText('Hello rendered')).not.toBeInTheDocument();
  });

  it('toggles back to rendered', () => {
    render(<RawRenderedToggle rendered={<span>Rendered body</span>} raw="plain" />);
    const rawTab = screen.getByRole('tab', { name: i18n.t('content_view.raw', { defaultValue: 'Raw' }) });
    const renderedTab = screen.getByRole('tab', { name: i18n.t('content_view.rendered', { defaultValue: 'Rendered' }) });
    expect(renderedTab).toHaveAttribute('aria-selected', 'true');

    fireEvent.click(rawTab);
    expect(rawTab).toHaveAttribute('aria-selected', 'true');
    expect(screen.getByText('plain')).toBeVisible();

    fireEvent.click(renderedTab);
    expect(screen.getByText('Rendered body')).toBeVisible();
  });

  it('supports a controlled view and reports changes', () => {
    const onViewChange = vi.fn();
    render(<RawRenderedToggle rendered={<span>R</span>} raw="x" view="rendered" onViewChange={onViewChange} />);
    fireEvent.click(screen.getByRole('tab', { name: i18n.t('content_view.raw', { defaultValue: 'Raw' }) }));
    expect(onViewChange).toHaveBeenCalledExactlyOnceWith('raw');
    // Controlled: the parent did not change the prop, so the rendered pane stays.
    expect(screen.getByText('R')).toBeVisible();
  });

  it('pretty-prints JSON strings and objects and passes plain text through', () => {
    expect(formatRaw({ a: 1 })).toBe('{\n  "a": 1\n}');
    expect(formatRaw('{"b":2}')).toBe('{\n  "b": 2\n}');
    expect(formatRaw('not json')).toBe('not json');
    expect(formatRaw(null)).toBe('');
    expect(formatRaw(undefined)).toBe('');
  });

  it('shows an empty raw payload without throwing', () => {
    render(<RawRenderedToggle rendered={<span>R</span>} raw={null} defaultView="raw" />);
    expect(screen.getByTestId('raw-payload')).toBeVisible();
    expect(screen.getByTestId('raw-payload')).toHaveTextContent('');
  });
});
