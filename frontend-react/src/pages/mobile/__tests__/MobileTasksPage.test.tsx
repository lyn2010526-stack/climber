import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MobileTasksPage } from '../MobileTasksPage';
import i18n from '../../../i18n';

beforeEach(async () => {
  localStorage.setItem('i18next_lng', 'en');
  await i18n.changeLanguage('en');
});

describe('MobileTasksPage', () => {
  it('stays a stable mobile card surface instead of the squeezed console', () => {
    render(<MobileTasksPage />);
    expect(screen.getByRole('heading', { name: i18n.t('mobile.tasks.card_title') })).toBeInTheDocument();
    expect(screen.getByText(i18n.t('mobile.tasks.card_description'))).toBeInTheDocument();
    expect(screen.queryByText('Tasks Content')).toBeNull();
  });

  it('keeps the shared empty state and chat action', () => {
    render(<MobileTasksPage />);
    expect(screen.getByRole('heading', { name: i18n.t('mobile.tasks.empty_title') })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: i18n.t('mobile.open_chat') })).toBeInTheDocument();
  });
});
