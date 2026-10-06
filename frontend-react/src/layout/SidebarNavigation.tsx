import { ALL_NAV_ITEMS_BASE, NAV_GROUPS, type NavGroup, type Page } from '../navigation/navConfig';
import { WorkbenchIcon, type WorkbenchIconName } from '../components/ui/WorkbenchIcon';

const NAV_ICON: Partial<Record<Page, WorkbenchIconName>> = {
  chat: 'conversation', tasks: 'task', skills: 'skill', settings: 'settings', mcp: 'tool', terminal: 'tool', agents: 'agent',
};

interface SidebarNavigationProps {
  currentPage: Page;
  onNavigate: (page: Page) => void;
  collapsed?: boolean;
  label: string;
  translate: (key: string) => string;
  groupLabels?: Record<NavGroup, string>;
}

export function SidebarNavigation({ currentPage, onNavigate, collapsed = false, label, translate, groupLabels }: SidebarNavigationProps) {
  return (
    <nav aria-label={label} className="min-h-0 flex-1 overflow-y-auto px-2 py-1">
      {NAV_GROUPS.map(group => (
        <section key={group.id} aria-labelledby={collapsed ? undefined : `${group.id}-navigation-heading`} className="mb-2">
          {!collapsed && (
            <h2 id={`${group.id}-navigation-heading`} className="px-2 pb-1 pt-2 text-[11px] font-medium text-[var(--color-text-muted)]">
              {groupLabels?.[group.id] ?? group.label}
            </h2>
          )}
          <ul className="space-y-0.5">
            {ALL_NAV_ITEMS_BASE.filter(item => item.group === group.id).map(item => {
              const Icon = item.icon;
              const title = item.labelKey ? translate(item.labelKey) : item.label ?? item.id;
              const active = currentPage === item.id;
              return (
                <li key={item.id}>
                  <button
                    type="button"
                    aria-label={title}
                    aria-current={active ? 'page' : undefined}
                    title={collapsed ? title : undefined}
                    onClick={() => onNavigate(item.id)}
                    data-secondary={item.secondary || undefined}
                    className={`flex min-h-11 w-full items-center gap-2 rounded-md px-2 text-left text-sm transition-colors [@media(pointer:fine)]:min-h-9 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-accent)] ${collapsed ? 'justify-center' : ''} ${active ? 'bg-[var(--color-accent-subtle)] font-medium text-[var(--color-accent-foreground)]' : 'text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-surface-2)] hover:text-[var(--color-text-primary)]'}`}
                  >
                    {NAV_ICON[item.id] ? <WorkbenchIcon name={NAV_ICON[item.id]!} className="shrink-0" /> : <Icon size={16} aria-hidden="true" className={`shrink-0 ${item.secondary && !active ? 'text-[var(--color-text-muted)]' : ''}`} />}
                    {!collapsed && <span className={`truncate ${item.secondary && !active ? 'text-[var(--color-text-muted)]' : ''}`}>{title}</span>}
                  </button>
                </li>
              );
            })}
          </ul>
        </section>
      ))}
    </nav>
  );
}
