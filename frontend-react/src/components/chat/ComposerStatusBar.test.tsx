import { render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it } from 'vitest';
import i18n from '../../i18n';
import { ComposerStatusBar, formatTokensCompact } from './ComposerStatusBar';

beforeEach(async () => {
  await i18n.changeLanguage('zh-CN');
});

describe('formatTokensCompact', () => {
  it('mirrors the codex compact token format', () => {
    expect(formatTokensCompact(0)).toBe('0');
    expect(formatTokensCompact(999)).toBe('999');
    expect(formatTokensCompact(12345)).toBe('12.3K');
    expect(formatTokensCompact(1_250_000)).toBe('1.25M');
  });
});

describe('ComposerStatusBar', () => {
  it('renders cwd, model and tokens as a mono tabular row over a hairline', () => {
    render(<ComposerStatusBar cwd="/workspace/app" model="gpt-5" turnTokens={12345} />);
    const bar = screen.getByTestId('composer-status-bar');
    expect(bar).toHaveClass('font-mono', 'tabular-nums', 'border-t');
    expect(screen.getByTestId('composer-status-cwd')).toHaveTextContent('/workspace/app');
    expect(screen.getByTestId('composer-status-model')).toHaveTextContent('gpt-5');
    expect(screen.getByTestId('composer-status-tokens')).toHaveTextContent('12.3K');
  });

  it('shows unreported rather than fabricating values', () => {
    render(<ComposerStatusBar />);
    expect(screen.getByTestId('composer-status-cwd')).toHaveTextContent('未上报');
    expect(screen.getByTestId('composer-status-model')).toHaveTextContent('未上报');
    expect(screen.getByTestId('composer-status-tokens')).toHaveTextContent('未上报');
  });

  it('treats an empty name as unreported', () => {
    render(<ComposerStatusBar cwd="   " model="" turnTokens={null} />);
    expect(screen.getByTestId('composer-status-cwd')).toHaveTextContent('未上报');
    expect(screen.getByTestId('composer-status-model')).toHaveTextContent('未上报');
  });
});
