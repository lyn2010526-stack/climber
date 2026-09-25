import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { Brain, Factory, GitBranch, Key, Stethoscope } from 'lucide-react';
import { ALL_NAV_ITEMS_BASE, CORE_NAV_ITEMS_BASE, MOBILE_ADAPTED_PAGE_IDS, NAV_ITEM_IDS } from './navConfig';
import { AdaptiveMobileLayout } from '../components/layout/AdaptiveMobileLayout';
import { MobileBottomNav } from '../legacy/components/mobile/MobileBottomNav';
import appSource from '../App.tsx?raw';

vi.mock('../i18n', () => ({ useI18n: () => ({ t: (key: string) => key }) }));
vi.mock('../store/workspace', () => ({ useWorkspaceStore: () => ({ sessions: [] }) }));
afterEach(cleanup);

describe('Semantic navigation contract', () => {
  it.each([
    ['factory', Factory],
    ['reasoning', Brain],
    ['traces', GitBranch],
    ['doctor', Stethoscope],
  ] as const)('%s uses its semantic icon', (id, icon) => {
    expect(ALL_NAV_ITEMS_BASE.find(item => item.id === id)?.icon).toBe(icon);
    for (const item of CORE_NAV_ITEMS_BASE.filter(item => item.id === id)) {
      expect(item.icon).toBe(icon);
    }
  });

  it('exposes a distinct API key entry in desktop and command navigation', () => {
    for (const items of [CORE_NAV_ITEMS_BASE, ALL_NAV_ITEMS_BASE]) {
      expect(items.filter(item => item.id === 'apikeys')).toHaveLength(1);
      expect(items.find(item => item.id === 'apikeys')).toMatchObject({ icon: Key, group: 'config' });
      expect(new Set(items.map(item => item.id)).size).toBe(items.length);
    }
    expect(NAV_ITEM_IDS.has('apikeys')).toBe(true);
    expect(MOBILE_ADAPTED_PAGE_IDS.has('apikeys')).toBe(true);
    expect([...NAV_ITEM_IDS]).not.toContain('login');
    expect(appSource.match(/case 'apikeys': return <ApiKeysPage \/>;/g)).toHaveLength(2);
  });

  it('opens the independent API key entry from the mobile more sheet', () => {
    const onNavigate = vi.fn();
    render(<AdaptiveMobileLayout currentPage="chat" onNavigate={onNavigate}><div>Workspace</div></AdaptiveMobileLayout>);
    fireEvent.click(screen.getByRole('button', { name: 'sidebar.more' }));
    expect(screen.getByRole('dialog')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'navigation.api_keys' }));
    expect(onNavigate).toHaveBeenCalledWith('apikeys');
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('marks the mobile more entry active while on API keys', () => {
    render(<AdaptiveMobileLayout currentPage="apikeys" onNavigate={vi.fn()}><div>Keys</div></AdaptiveMobileLayout>);
    expect(screen.getByRole('button', { name: 'sidebar.more' })).toHaveAttribute('aria-current', 'page');
  });

  it('keeps the legacy mobile API key entry reachable', () => {
    const onNavigate = vi.fn();
    render(<MobileBottomNav currentPage="apikeys" onNavigate={onNavigate} />);
    const more = screen.getByRole('button', { name: '更多' });
    expect(more).toHaveAttribute('aria-current', 'page');
    fireEvent.click(more);
    fireEvent.click(screen.getByRole('button', { name: 'API 密钥' }));
    expect(onNavigate).toHaveBeenCalledWith('apikeys');
    expect(screen.queryByRole('button', { name: 'API 密钥' })).not.toBeInTheDocument();
  });
});
