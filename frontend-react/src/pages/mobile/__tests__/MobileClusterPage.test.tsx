import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MobileClusterPage } from '../MobileClusterPage';
import i18n from '../../../i18n';

beforeEach(async () => {
  localStorage.setItem('i18next_lng', 'en');
  await i18n.changeLanguage('en');
});

describe('MobileClusterPage', () => {
  it('stays a stable mobile card surface instead of the desktop workbench', () => {
    render(<MobileClusterPage />);
    expect(screen.getByRole('heading', { name: i18n.t('mobile.cluster.card_title') })).toBeInTheDocument();
    expect(screen.getByText(i18n.t('mobile.cluster.card_description'))).toBeInTheDocument();
    expect(screen.queryByText('Cluster Content')).toBeNull();
  });

  it('keeps the shared empty state and chat action', () => {
    render(<MobileClusterPage />);
    expect(screen.getByRole('heading', { name: i18n.t('mobile.cluster.empty_title') })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: i18n.t('mobile.open_chat') })).toBeInTheDocument();
  });
});
