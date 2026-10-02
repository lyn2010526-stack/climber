import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, within } from '@testing-library/react';
import { ALL_NAV_ITEMS_BASE } from '../navigation/navConfig';
import { SidebarNavigation } from './SidebarNavigation';

afterEach(cleanup);

describe('SidebarNavigation', () => {
  it('groups every route and navigates with an accessible active state', () => {
    const onNavigate = vi.fn();
    render(<SidebarNavigation currentPage="authapikeys" onNavigate={onNavigate} label="Navigation" translate={key => key} />);
    expect(screen.getAllByRole('heading').map(heading => heading.textContent)).toEqual(['工作', '资源', '管理运维']);
    expect(screen.getAllByRole('button')).toHaveLength(ALL_NAV_ITEMS_BASE.length);
    expect(within(screen.getByRole('region', { name: '资源' })).getByRole('button', { name: 'navigation.skills' })).toBeInTheDocument();
    const platformTokens = ALL_NAV_ITEMS_BASE.find(item => item.id === 'authapikeys')!;
    expect(screen.getByRole('button', { name: platformTokens.labelKey! })).toHaveAttribute('aria-current', 'page');
    for (const item of ALL_NAV_ITEMS_BASE) {
      fireEvent.click(screen.getByRole('button', { name: item.labelKey ?? item.label ?? item.id }));
      expect(onNavigate).toHaveBeenLastCalledWith(item.id);
    }
    expect(screen.getByRole('button', { name: 'navigation.cluster' })).toHaveAttribute('data-secondary', 'true');
  });

  it('keeps every collapsed entry named and reachable', () => {
    render(<SidebarNavigation currentPage="cluster" onNavigate={vi.fn()} collapsed label="Navigation" translate={key => key} />);
    expect(screen.queryAllByRole('heading')).toHaveLength(0);
    for (const item of ALL_NAV_ITEMS_BASE) {
      const title = item.labelKey ?? item.label ?? item.id;
      expect(screen.getByRole('button', { name: title })).toHaveAttribute('title', title);
    }
    expect(screen.getByRole('button', { name: 'navigation.cluster' })).toHaveAttribute('aria-current', 'page');
  });

  it('accepts translated group labels without changing route groups', () => {
    render(<SidebarNavigation currentPage="chat" onNavigate={vi.fn()} label="Navigation" translate={key => key} groupLabels={{ main: 'Work', manage: 'Resources', config: 'Administration' }} />);
    expect(screen.getAllByRole('heading').map(heading => heading.textContent)).toEqual(['Work', 'Resources', 'Administration']);
  });
});
