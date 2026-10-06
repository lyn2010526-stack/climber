import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MobileFactoryPage } from '../MobileFactoryPage';
import i18n from '../../../i18n';

beforeEach(async () => {
  localStorage.setItem('i18next_lng', 'en');
  await i18n.changeLanguage('en');
});

describe('MobileFactoryPage', () => {
  it('stays a stable mobile card surface instead of the multi-column editor', () => {
    render(<MobileFactoryPage />);
    expect(screen.getByRole('heading', { name: i18n.t('mobile.factory.card_title') })).toBeInTheDocument();
    expect(screen.getByText(i18n.t('mobile.factory.card_description'))).toBeInTheDocument();
    expect(screen.queryByText('Factory Content')).toBeNull();
  });

  it('keeps the shared empty state and chat action', () => {
    render(<MobileFactoryPage />);
    expect(screen.getByRole('heading', { name: i18n.t('mobile.factory.empty_title') })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: i18n.t('mobile.open_chat') })).toBeInTheDocument();
  });
});
