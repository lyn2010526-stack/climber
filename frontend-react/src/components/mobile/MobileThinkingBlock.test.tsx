import { describe, it, expect, beforeAll } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import i18n from '../../i18n';
import { MobileThinkingBlock } from './MobileThinkingBlock';

beforeAll(async () => {
  await i18n.changeLanguage('zh-CN');
});

describe('MobileThinkingBlock', () => {
  it('reads back as a static thinking-process panel once the turn settles', () => {
    render(<MobileThinkingBlock reasoning="先解析需求" />);
    expect(screen.getByRole('button', { name: /思考过程/ })).toBeInTheDocument();
    expect(screen.queryByText('思考中')).not.toBeInTheDocument();
  });

  it('shows the pulsing thinking label while the turn streams', () => {
    render(<MobileThinkingBlock reasoning="先解析需求" streaming />);
    expect(screen.getByRole('button', { name: /思考中/ })).toBeInTheDocument();
  });

  it('expands the trace in place through aria controls', () => {
    render(<MobileThinkingBlock reasoning="先解析需求" />);
    const header = screen.getByRole('button', { name: /思考过程/ });
    expect(header).toHaveAttribute('aria-expanded', 'false');
    const body = document.getElementById(header.getAttribute('aria-controls')!)!;
    expect(body).toContainElement(screen.getByText('先解析需求'));
    fireEvent.click(header);
    expect(header).toHaveAttribute('aria-expanded', 'true');
    expect(body.style.gridTemplateRows).toBe('1fr');
  });
});
