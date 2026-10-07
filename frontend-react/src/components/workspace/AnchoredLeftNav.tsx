import { useEffect, useMemo, useRef, useState } from 'react';
import { ChevronDown, ChevronRight, LogOut, MessageSquare, PanelLeftClose, Pin, PinOff, Plus, Search, Trash2, MoreHorizontal, BookmarkPlus, History, RotateCcw, GitFork } from 'lucide-react';
import { useI18n } from '../../i18n';
import { formatTime, formatDateTime } from '../../i18n/utils';
import { cn } from '../../lib/utils';
import { icons, iconSizes } from '../../lib/icons';
import { WorkbenchIcon } from '../ui/WorkbenchIcon';
import { ThemeToggle } from '../ui/ThemeToggle';
import { ClimberMark } from '../brand/ClimberMark';
import { api, type SessionCheckpoint } from '../../api';
import { apiClient } from '../../lib/api-client';
import { useWorkspaceStore, type Session } from '../../store/workspace';
import { useAnchoredStore } from '../../store/anchored';
import { PROFILE_ORDER } from '../../store/anchored';
import { useAnchoredNavSessions } from '../../hooks/useAnchoredNavSessions';
import { groupSessions, sessionLastActivityAt } from './sessionGrouping';
import './codex-suite.css';

type MenuState = { sessionId: string; x: number; y: number } | null;

const PIN_KEY = 'anchored.pinned-sessions';

const PROFILE_LABEL_KEY: Record<(typeof PROFILE_ORDER)[number], string> = {
  minimal: 'anchored.profile.minimal',
  standard: 'anchored.profile.standard',
  full: 'anchored.profile.full',
};

function readPinned(): Set<string> {
  try {
    const raw = localStorage.getItem(PIN_KEY);
    if (!raw) return new Set();
    const parsed: unknown = JSON.parse(raw);
    return Array.isArray(parsed) ? new Set(parsed.map(String)) : new Set();
  } catch {
    return new Set();
  }
}

function writePinned(ids: Set<string>): void {
  try {
    localStorage.setItem(PIN_KEY, JSON.stringify([...ids]));
  } catch {
    // 忽略持久化失败：置顶仅是本地偏好。
  }
}

export function AnchoredLeftNav({ onCollapse }: { onCollapse?: () => void }) {
  const SettingsIcon = icons.settings;
  const CloseIcon = icons.close;
  const { t } = useI18n();
  const sessions = useWorkspaceStore((s) => s.sessions);
  const activeSessionId = useWorkspaceStore((s) => s.activeSessionId);
  const setActiveSession = useWorkspaceStore((s) => s.setActiveSession);
  const { error, busy, createSession, goHome, removeSession } = useAnchoredNavSessions();

  // 配置档：全局生效，激活档持久化在 anchored store。
  const activeProfile = useAnchoredStore((s) => s.profile);
  const setProfile = useAnchoredStore((s) => s.setProfile);

  const [pinned, setPinned] = useState<Set<string>>(() => readPinned());
  const [menu, setMenu] = useState<MenuState>(null);
  const [sessionQuery, setSessionQuery] = useState('');
  const [settingsOpen, setSettingsOpen] = useState(false);

  // 技能中心
  const [skills, setSkills] = useState<Array<{ id: string; name: string; enabled: boolean }>>([]);
  const [skillQuery, setSkillQuery] = useState('');
  const [skillsOpen, setSkillsOpen] = useState(false);
  const [skillsError, setSkillsError] = useState(false);

  // 配置档管理（默认折叠）
  const [profilesOpen, setProfilesOpen] = useState(false);

  // 用户区
  const [userName, setUserName] = useState<string | null>(null);

  // 会话检查点：操作结果走轻量通知条，历史走弹层。
  const [notice, setNotice] = useState<string | null>(null);
  const [checkpointBusy, setCheckpointBusy] = useState(false);
  const [history, setHistory] = useState<{ sessionId: string; checkpoints: SessionCheckpoint[] } | null>(null);

  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let active = true;
    api
      .listSkills()
      .then((data) => {
        if (!active) return;
        const rows = Array.isArray(data) ? data : [];
        setSkills(
          rows
            .map((row: Record<string, unknown>, index: number) => ({
              id: String(row.id ?? row.skill_id ?? index),
              name: String(row.name ?? row.id ?? row.skill_id ?? `#${index}`),
              enabled: row.enabled === undefined ? Boolean(row.is_active) : Boolean(row.enabled),
            }))
            .sort((a, b) => a.name.localeCompare(b.name)),
        );
      })
      .catch(() => {
        if (active) setSkillsError(true);
      });
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    let active = true;
    apiClient
      .get<{ id?: string; name?: string; username?: string; email?: string }>('/auth/me')
      .then((user: { id?: string; name?: string; username?: string; email?: string }) => {
        if (!active) return;
        setUserName(user.name ?? user.username ?? user.email ?? user.id ?? null);
      })
      .catch(() => {
        if (active) setUserName(null);
      });
    return () => {
      active = false;
    };
  }, []);

  // 点击其他位置关闭右键菜单。
  useEffect(() => {
    if (!menu) return;
    const close = (event: MouseEvent) => {
      if (menuRef.current && event.target instanceof Node && menuRef.current.contains(event.target)) return;
      setMenu(null);
    };
    window.addEventListener('mousedown', close);
    const escape = (event: KeyboardEvent) => { if (event.key === 'Escape') setMenu(null); };
    window.addEventListener('keydown', escape);
    return () => {
      window.removeEventListener('mousedown', close);
      window.removeEventListener('keydown', escape);
    };
  }, [menu]);

  const visibleSessions = useMemo(() => {
    const query = sessionQuery.trim().toLowerCase();
    const matched = query
      ? sessions.filter((session) => (session.title ?? '').toLowerCase().includes(query))
      : sessions;
    return [...matched].sort((a, b) => {
      const pinDiff = Number(pinned.has(b.id)) - Number(pinned.has(a.id));
      if (pinDiff !== 0) return pinDiff;
      return b.createdAt - a.createdAt;
    });
  }, [sessions, sessionQuery, pinned]);

  // The clock the date buckets are cut against. A long-lived sidebar re-reads
  // it, so a session that was "today" at mount does not stay there until reload.
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const tick = window.setInterval(() => setNow(Date.now()), 60_000);
    return () => window.clearInterval(tick);
  }, []);

  // Pinned rows sort ahead of the rest within each date group, so the grouping
  // is applied after the sort rather than flattening it away.
  const sessionGroups = useMemo(() => groupSessions(visibleSessions, now), [visibleSessions, now]);

  const sessionTime = (session: Session) => {
    const timestamp = sessionLastActivityAt(session);
    return timestamp === null ? t('common.not_reported') : formatTime(timestamp);
  };

  const visibleSkills = useMemo(() => {
    const query = skillQuery.trim().toLowerCase();
    return query ? skills.filter((skill) => skill.name.toLowerCase().includes(query)) : skills;
  }, [skills, skillQuery]);

  const togglePin = (sessionId: string) => {
    setMenu(null);
    setPinned((previous) => {
      const next = new Set(previous);
      if (next.has(sessionId)) next.delete(sessionId);
      else next.add(sessionId);
      writePinned(next);
      return next;
    });
  };

  const runSessionAction = async (failureKey: string, action: () => Promise<string>) => {
    if (checkpointBusy) return;
    setCheckpointBusy(true);
    setNotice(null);
    try {
      setNotice(await action());
    } catch {
      setNotice(t(failureKey));
    } finally {
      setCheckpointBusy(false);
    }
  };

  // 检查点快照取服务端持久化消息，迭代号用消息数近似（后端不校验语义）。
  const createCheckpoint = (sessionId: string) =>
    runSessionAction('anchored.nav.checkpoint_failed', async () => {
      const messages = await api.getSessionMessages(sessionId);
      await api.saveCheckpoint(sessionId, {
        messages: messages.map((message) => ({
          role: message.role,
          content: message.content,
          tool_call_id: message.tool_call_id,
          tool_calls: message.tool_calls,
          tool_name: message.tool_name,
        })),
        iteration: messages.length,
      });
      return t('anchored.nav.checkpoint_created');
    });

  const openCheckpointHistory = async (sessionId: string) => {
    try {
      const data = await api.getCheckpointHistory(sessionId);
      setHistory({ sessionId, checkpoints: data.checkpoints });
    } catch {
      setNotice(t('anchored.nav.checkpoint_failed'));
    }
  };

  const resumeFromCheckpoint = (sessionId: string) =>
    runSessionAction('anchored.nav.checkpoint_failed', async () => {
      const result = await api.resumeSession(sessionId);
      setActiveSession(sessionId);
      setHistory(null);
      return t('anchored.nav.checkpoint_resumed', { iteration: result.checkpoint.iteration });
    });

  const forkSession = (sessionId: string) =>
    runSessionAction('anchored.nav.fork_failed', async () => {
      await api.forkSession(sessionId);
      const list = await api.listSessions();
      useWorkspaceStore.getState().loadSessions(list.map((item) => ({
        id: String(item.id),
        title: item.title ?? null,
        status: item.status ?? '',
        created_at: item.created_at ?? null,
        updated_at: item.updated_at ?? null,
        provider: item.provider ?? null,
        model_id: item.model_id ?? null,
        agent_id: item.agent_id ?? null,
      })));
      return t('anchored.nav.forked');
    });

  return (
    <nav
      data-testid="anchored-left-nav"
      aria-label={t('anchored.nav.label')}
      className="flex h-full min-w-0 flex-col border-r border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-1)]"
    >
      {/* Logo 区保持固定高度，设置入口锚定在右侧。 */}
      <div className="flex h-12 shrink-0 items-center border-b border-[var(--color-border-subtle)]">
        <button
          type="button"
          data-testid="anchored-logo"
          onClick={goHome}
          title={t('anchored.nav.logo_hint')}
          className="flex h-full min-w-0 flex-1 items-center gap-[var(--space-2)] px-[var(--space-3)] text-left transition-colors hover:bg-[var(--color-bg-surface-2)] focus-visible:outline-none focus-visible:shadow-[var(--focus-ring)]"
        >
          <span aria-hidden="true" className="flex size-6 shrink-0 items-center justify-center rounded-[var(--radius-sm)] bg-[var(--color-accent-foreground)] text-[length:var(--text-2xs)] font-bold text-[var(--color-bg-page)]">
            <ClimberMark size={iconSizes.lg} />
          </span>
          <span className="min-w-0 flex-1 truncate text-[length:var(--text-sm)] font-semibold text-[var(--color-text-primary)]">
            Climber
          </span>
        </button>
        {onCollapse && (
          <button
            type="button"
            onClick={onCollapse}
            title={t('anchored.layout.collapse_left')}
            aria-label={t('anchored.layout.collapse_left')}
            className="mr-[var(--space-1)] flex size-7 shrink-0 items-center justify-center rounded-[var(--radius-sm)] text-[var(--color-text-muted)] transition-colors hover:bg-[var(--color-bg-surface-2)] hover:text-[var(--color-text-primary)] focus-visible:outline-none focus-visible:shadow-[var(--focus-ring)]"
          >
            <PanelLeftClose size={iconSizes.sm} aria-hidden="true" />
          </button>
        )}
      </div>

      <div className="flex min-h-0 flex-1 flex-col">
        {/* 会话管理 */}
        <section className="flex min-h-0 flex-1 flex-col" data-testid="anchored-sessions" aria-label={t('anchored.nav.sessions')}>
          <header className="shrink-0 px-2 py-2">
            <button
              type="button"
              onClick={() => void createSession()}
              disabled={busy}
              aria-label={t('anchored.nav.new_session')}
              className="cx-row flex h-8 w-full items-center gap-2 rounded-[var(--radius-md)] px-2 text-[13px] text-[var(--color-text-primary)] hover:bg-[var(--color-bg-surface-2)] disabled:opacity-50"
            >
              <Plus size={iconSizes.xs} aria-hidden="true" />
              {t('anchored.nav.new_session')}
            </button>
          </header>
          <div className="shrink-0 px-[var(--space-2)] pb-[var(--space-1)]">
            <div className="flex h-8 items-center gap-[var(--space-1-5)] rounded-[var(--radius-sm)] bg-[var(--color-bg-surface-2)] px-[var(--space-2)]">
              <Search size={iconSizes.xs} aria-hidden="true" className="shrink-0 text-[var(--color-text-muted)]" />
              <input
                value={sessionQuery}
                onChange={(event) => setSessionQuery(event.target.value)}
                placeholder={t('anchored.nav.search_sessions')}
                aria-label={t('anchored.nav.search_sessions')}
                className="min-w-0 flex-1 bg-transparent text-[length:var(--text-xs)] text-[var(--color-text-primary)] placeholder:text-[var(--color-text-muted)] focus:outline-none"
              />
            </div>
          </div>
          {error && <p role="alert" className="shrink-0 px-3 py-2 text-xs text-[var(--color-error)]">{error}</p>}
          <div className="min-h-0 flex-1 overflow-y-auto px-[var(--space-2)] pb-[var(--space-2)]">
            {sessionGroups.map((group) => (
              <section key={group.id} aria-label={group.label}>
                <h3 className="cx-group-label px-[var(--space-2)] pb-[var(--space-1)] pt-[var(--space-2)]">
                  {group.label}
                </h3>
                <ul>
                  {group.sessions.map((session) => {
                    const active = session.id === activeSessionId;
                    return (
                      <li key={session.id} className="group flex h-10 items-center">
                        <button
                          type="button"
                          onClick={() => setActiveSession(session.id)}
                          onContextMenu={(event) => {
                            event.preventDefault();
                            setMenu({ sessionId: session.id, x: event.clientX, y: event.clientY });
                          }}
                          aria-current={active}
                          className={cn(
                            'relative flex h-10 min-w-0 flex-1 items-center gap-[var(--space-2)] rounded-[var(--radius-sm)] px-[var(--space-2)] text-left transition-colors',
                            active
                              ? 'bg-[var(--color-accent-subtle)] text-[var(--color-accent-foreground)]'
                              : 'text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-surface-2)] hover:text-[var(--color-text-primary)]',
                          )}
                        >
                          {active && (
                            <span aria-hidden="true" className="absolute inset-y-[var(--space-2)] left-0 w-0.5 rounded-[var(--radius-pill)] bg-[var(--color-accent)]" />
                          )}
                          <MessageSquare
                            size={iconSizes.sm}
                            aria-hidden="true"
                            className={cn('shrink-0', active ? 'text-[var(--color-accent-foreground)]' : 'text-[var(--color-text-muted)]')}
                          />
                          {pinned.has(session.id) && (
                            <Pin size={iconSizes.xs} aria-hidden="true" className="shrink-0 text-[var(--color-accent-foreground)]" />
                          )}
                          <span className="min-w-0 flex-1 truncate text-[13px]">
                            {session.title ?? t('chat.new_conversation')}
                          </span>
                          <span aria-hidden="true" className="cx-count shrink-0">
                            {sessionTime(session)}
                          </span>
                        </button>
                        <button
                          type="button"
                          aria-label={`${t('anchored.nav.session_menu')}: ${session.title ?? t('chat.new_conversation')}`}
                          onClick={(event) => {
                            const rect = event.currentTarget.getBoundingClientRect();
                            setMenu({ sessionId: session.id, x: Math.min(rect.left, window.innerWidth - 200), y: Math.max(0, Math.min(rect.bottom, window.innerHeight - 180)) });
                          }}
                          className="flex size-7 shrink-0 items-center justify-center rounded text-[var(--color-text-muted)] opacity-0 hover:bg-[var(--color-bg-surface-2)] focus:opacity-100 group-hover:opacity-100"
                        >
                          <MoreHorizontal size={iconSizes.sm} aria-hidden="true" />
                        </button>
                      </li>
                    );
                  })}
                </ul>
              </section>
            ))}
          </div>
          {visibleSessions.length === 0 && <p className="px-3 py-2 text-xs text-[var(--color-text-muted)]">{sessionQuery.trim() ? t('anchored.nav.no_matching_sessions') : t('anchored.nav.no_sessions')}</p>}
        </section>

        <div className="shrink-0 border-t border-[var(--color-border-subtle)]">
          <button type="button" aria-expanded={settingsOpen} aria-controls="anchored-nav-settings" onClick={() => setSettingsOpen((open) => !open)} className="flex h-10 w-full items-center gap-2 px-3 text-xs text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-surface-2)]">
            <SettingsIcon size={iconSizes.sm} />
            <span className="flex-1 text-left">{t('settings.title')}</span>
            {settingsOpen ? <ChevronDown size={iconSizes.xs} /> : <ChevronRight size={iconSizes.xs} />}
          </button>
          {settingsOpen && <div id="anchored-nav-settings" className="max-h-[40vh] overflow-y-auto">
          <a href="#settings" className="block px-3 py-2 text-xs text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-surface-2)]">{t('anchored.nav.open_settings')}</a>

        {/* 技能中心：搜索 + 分类折叠 + 开关即时生效 */}
        <section data-testid="anchored-skills" aria-label={t('anchored.nav.skills')}>
          <button
            type="button"
            aria-expanded={skillsOpen}
            onClick={() => setSkillsOpen((open) => !open)}
            className="flex h-9 w-full items-center gap-[var(--space-1-5)] px-[var(--space-3)] text-left transition-colors hover:bg-[var(--color-bg-surface-2)]"
          >
            {skillsOpen ? <ChevronDown size={iconSizes.xs} aria-hidden="true" /> : <ChevronRight size={iconSizes.xs} aria-hidden="true" />}
            <h3 className="cx-group-label min-w-0 flex-1 truncate uppercase">
              {t('anchored.nav.skills')}
            </h3>
            <span className="cx-count shrink-0">
              {skills.length}
            </span>
          </button>
          {skillsOpen && (
            <>
              <div className="px-[var(--space-2)] pb-[var(--space-1)]">
                <div className="flex h-8 items-center gap-[var(--space-1-5)] rounded-[var(--radius-sm)] bg-[var(--color-bg-surface-2)] px-[var(--space-2)]">
                  <Search size={iconSizes.xs} aria-hidden="true" className="shrink-0 text-[var(--color-text-muted)]" />
                  <input
                    value={skillQuery}
                    onChange={(event) => setSkillQuery(event.target.value)}
                    placeholder={t('anchored.nav.search_skills')}
                    aria-label={t('anchored.nav.search_skills')}
                    className="min-w-0 flex-1 bg-transparent text-[length:var(--text-xs)] text-[var(--color-text-primary)] placeholder:text-[var(--color-text-muted)] focus:outline-none"
                  />
                </div>
              </div>
              {skillsError ? (
                <p className="px-[var(--space-3)] pb-[var(--space-2)] text-[length:var(--text-2xs)] text-[var(--color-error)]">
                  {t('anchored.nav.skills_error')}
                </p>
              ) : (
                <ul className="px-[var(--space-2)] pb-[var(--space-2)]">
                  {visibleSkills.map((skill) => (
                    <li key={skill.id} data-enabled={skill.enabled} className="workbench-skill flex h-9 items-center gap-[var(--space-2)] rounded-[var(--radius-sm)] px-[var(--space-2)] hover:bg-[var(--color-bg-surface-2)]">
                      <WorkbenchIcon name="skill" size={iconSizes.sm} className="shrink-0" />
                      <span className="min-w-0 flex-1 truncate text-[length:var(--text-xs)] text-[var(--color-text-secondary)]">
                        {skill.name}
                      </span>
                      <button
                        type="button"
                        role="switch"
                        aria-checked={skill.enabled}
                        aria-label={t('anchored.nav.toggle_skill', { name: skill.name })}
                        onClick={() => {
                          const next = !skill.enabled;
                          setSkills((previous) =>
                            previous.map((item) => (item.id === skill.id ? { ...item, enabled: next } : item)),
                          );
                          api.toggleSkill(skill.id, next).catch(() => {
                            // 失败回滚本地开关状态。
                            setSkills((previous) =>
                              previous.map((item) => (item.id === skill.id ? { ...item, enabled: !next } : item)),
                            );
                          });
                        }}
                        className={cn(
                          'relative h-4 w-7 shrink-0 rounded-[var(--radius-pill)] transition-colors',
                          skill.enabled ? 'bg-[var(--color-success)]' : 'bg-[var(--color-bg-surface-2)] shadow-[inset_0_0_0_1px_var(--color-border-default)]',
                        )}
                      >
                        <span
                          aria-hidden="true"
                          className={cn(
                            'absolute top-[2px] size-3 rounded-[var(--radius-pill)] bg-[var(--color-bg-surface-1)] transition-[left]',
                            skill.enabled ? 'left-[14px]' : 'left-[2px]',
                          )}
                        />
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </>
          )}
        </section>

        {/* 配置档管理：三档切换全局生效（默认折叠） */}
        <section data-testid="anchored-profiles" aria-label={t('anchored.nav.profiles')}>
          <button
            type="button"
            aria-expanded={profilesOpen}
            onClick={() => setProfilesOpen((open) => !open)}
            className="flex h-9 w-full items-center gap-[var(--space-1-5)] px-[var(--space-3)] text-left transition-colors hover:bg-[var(--color-bg-surface-2)]"
          >
            {profilesOpen ? <ChevronDown size={iconSizes.xs} aria-hidden="true" /> : <ChevronRight size={iconSizes.xs} aria-hidden="true" />}
            <h3 className="cx-group-label min-w-0 flex-1 truncate uppercase">
              {t('anchored.nav.profiles')}
            </h3>
            <span className="shrink-0 text-[length:var(--text-2xs)] text-[var(--color-text-muted)]">
              {t(PROFILE_LABEL_KEY[activeProfile])}
            </span>
          </button>
          {profilesOpen && (
            <div className="px-[var(--space-2)] pb-[var(--space-2)]">
              <ul className="space-y-[var(--space-0-5)]">
                {PROFILE_ORDER.map((profile) => (
                  <li key={profile}>
                    <button
                      type="button"
                      role="switch"
                      aria-checked={profile === activeProfile}
                      onClick={() => setProfile(profile)}
                      className={cn(
                        'flex h-8 w-full items-center rounded-[var(--radius-sm)] px-[var(--space-2)] text-left text-[length:var(--text-xs)] transition-colors',
                        profile === activeProfile
                          ? 'bg-[var(--color-accent-subtle)] text-[var(--color-text-primary)]'
                          : 'text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-surface-2)] hover:text-[var(--color-text-primary)]',
                      )}
                    >
                        <WorkbenchIcon name="settings" size={iconSizes.sm} className="mr-[var(--space-2)] shrink-0" />
                        {t(PROFILE_LABEL_KEY[profile])}
                    </button>
                  </li>
                ))}
              </ul>
              <p className="px-[var(--space-2)] pt-[var(--space-1)] text-[length:var(--text-2xs)] text-[var(--color-text-muted)]">
                {t('anchored.profile.hint')}
              </p>
            </div>
          )}
        </section>
          </div>}
        </div>
      </div>

      {/* 底部用户区 48px */}
      <footer className="flex h-12 shrink-0 items-center gap-[var(--space-2)] border-t border-[var(--color-border-subtle)] px-[var(--space-3)]">
        <span aria-hidden="true" className="flex size-7 shrink-0 items-center justify-center rounded-[var(--radius-pill)] bg-[var(--color-bg-surface-2)] text-[length:var(--text-2xs)] font-medium text-[var(--color-text-secondary)]">
          {(userName ?? '?').slice(0, 1).toUpperCase()}
        </span>
        <span className="min-w-0 flex-1 truncate text-[length:var(--text-xs)] text-[var(--color-text-secondary)]">
          {userName ?? t('anchored.nav.user_unknown')}
        </span>
        <ThemeToggle className="size-7 min-h-7 min-w-7" />
        <button
          type="button"
          aria-label={t('anchored.nav.logout')}
          title={t('anchored.nav.logout')}
          onClick={() => {
            void api.logout().finally(() => {
              window.location.assign('/login');
            });
          }}
          className="flex size-7 shrink-0 items-center justify-center rounded-[var(--radius-sm)] text-[var(--color-text-muted)] transition-colors hover:bg-[var(--color-bg-surface-2)] hover:text-[var(--color-text-primary)]"
        >
          <LogOut size={iconSizes.sm} aria-hidden="true" />
        </button>
      </footer>

      {/* 会话右键菜单：重命名 / 置顶 / 删除 */}
      {menu && (
        <div
          ref={menuRef}
          role="menu"
          aria-label={t('anchored.nav.session_menu')}
          className="fixed z-50 min-w-32 overflow-hidden rounded-[var(--radius-md)] border border-[var(--color-border-default)] bg-[var(--color-bg-surface-1)] py-[var(--space-1)] shadow-[var(--shadow-md)]"
          style={{ left: menu.x, top: menu.y }}
        >
          {/* 会话右键菜单：置顶 / 删除。后端没有会话重命名端点，不提供该入口。 */}
          <button
            type="button"
            role="menuitem"
            onClick={() => togglePin(menu.sessionId)}
            className="flex h-8 w-full items-center gap-[var(--space-1-5)] px-[var(--space-2-5)] text-left text-[length:var(--text-xs)] text-[var(--color-text-secondary)] transition-colors hover:bg-[var(--color-bg-surface-2)] hover:text-[var(--color-text-primary)]"
          >
            {pinned.has(menu.sessionId) ? <PinOff size={iconSizes.xs} aria-hidden="true" /> : <Pin size={iconSizes.xs} aria-hidden="true" />}
            {pinned.has(menu.sessionId) ? t('anchored.nav.unpin') : t('anchored.nav.pin')}
          </button>
          <button
            type="button"
            role="menuitem"
            disabled={checkpointBusy}
            onClick={() => { setMenu(null); void createCheckpoint(menu.sessionId); }}
            className="flex h-8 w-full items-center gap-[var(--space-1-5)] px-[var(--space-2-5)] text-left text-[length:var(--text-xs)] text-[var(--color-text-secondary)] transition-colors hover:bg-[var(--color-bg-surface-2)] hover:text-[var(--color-text-primary)] disabled:opacity-50"
          >
            <BookmarkPlus size={iconSizes.xs} aria-hidden="true" />
            {t('anchored.nav.checkpoint_create')}
          </button>
          <button
            type="button"
            role="menuitem"
            onClick={() => { setMenu(null); void openCheckpointHistory(menu.sessionId); }}
            className="flex h-8 w-full items-center gap-[var(--space-1-5)] px-[var(--space-2-5)] text-left text-[length:var(--text-xs)] text-[var(--color-text-secondary)] transition-colors hover:bg-[var(--color-bg-surface-2)] hover:text-[var(--color-text-primary)]"
          >
            <History size={iconSizes.xs} aria-hidden="true" />
            {t('anchored.nav.checkpoint_history')}
          </button>
          <button
            type="button"
            role="menuitem"
            disabled={checkpointBusy}
            onClick={() => { setMenu(null); void resumeFromCheckpoint(menu.sessionId); }}
            className="flex h-8 w-full items-center gap-[var(--space-1-5)] px-[var(--space-2-5)] text-left text-[length:var(--text-xs)] text-[var(--color-text-secondary)] transition-colors hover:bg-[var(--color-bg-surface-2)] hover:text-[var(--color-text-primary)] disabled:opacity-50"
          >
            <RotateCcw size={iconSizes.xs} aria-hidden="true" />
            {t('anchored.nav.checkpoint_resume')}
          </button>
          <button
            type="button"
            role="menuitem"
            disabled={checkpointBusy}
            onClick={() => { setMenu(null); void forkSession(menu.sessionId); }}
            className="flex h-8 w-full items-center gap-[var(--space-1-5)] px-[var(--space-2-5)] text-left text-[length:var(--text-xs)] text-[var(--color-text-secondary)] transition-colors hover:bg-[var(--color-bg-surface-2)] hover:text-[var(--color-text-primary)] disabled:opacity-50"
          >
            <GitFork size={iconSizes.xs} aria-hidden="true" />
            {t('anchored.nav.fork_session')}
          </button>
          <button
            type="button"
            role="menuitem"
            disabled={busy}
            onClick={() => { setMenu(null); void removeSession(menu.sessionId); }}
            className="flex h-8 w-full items-center gap-[var(--space-1-5)] px-[var(--space-2-5)] text-left text-[length:var(--text-xs)] text-[var(--color-error)] transition-colors hover:bg-[var(--color-bg-surface-2)]"
          >
            <Trash2 size={iconSizes.xs} aria-hidden="true" />
            {t('anchored.nav.delete_session')}
          </button>
        </div>
      )}

      {/* 会话操作结果通知 */}
      {notice && (
        <div
          role="status"
          className="fixed bottom-4 left-1/2 z-50 flex -translate-x-1/2 items-center gap-2 rounded-[var(--radius-md)] border border-[var(--color-border-default)] bg-[var(--color-bg-surface-1)] px-3 py-2 text-[length:var(--text-xs)] text-[var(--color-text-secondary)] shadow-[var(--shadow-md)]"
        >
          {notice}
          <button
            type="button"
            aria-label={t('common.dismiss')}
            onClick={() => setNotice(null)}
            className="text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)]"
          >
            <CloseIcon size={iconSizes.xs} aria-hidden="true" />
          </button>
        </div>
      )}

      {/* 检查点历史弹层 */}
      {history && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/30"
          onClick={() => setHistory(null)}
        >
          <div
            role="dialog"
            aria-label={t('anchored.nav.checkpoint_history_title')}
            className="max-h-[60vh] w-80 overflow-y-auto rounded-[var(--radius-md)] border border-[var(--color-border-default)] bg-[var(--color-bg-surface-1)] p-3 shadow-[var(--shadow-md)]"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="flex items-center justify-between">
              <h3 className="text-[length:var(--text-xs)] font-semibold text-[var(--color-text-primary)]">
                {t('anchored.nav.checkpoint_history_title')}
              </h3>
              <button
                type="button"
                aria-label={t('common.close')}
                onClick={() => setHistory(null)}
                className="text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)]"
              >
                <CloseIcon size={iconSizes.xs} aria-hidden="true" />
              </button>
            </div>
            {history.checkpoints.length === 0 ? (
              <p className="py-3 text-[length:var(--text-xs)] text-[var(--color-text-muted)]">
                {t('anchored.nav.checkpoint_history_empty')}
              </p>
            ) : (
              <ul className="mt-2 space-y-1">
                {[...history.checkpoints].reverse().map((checkpoint) => (
                  <li
                    key={checkpoint.id}
                    className="rounded-[var(--radius-sm)] border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-2)] px-2 py-1.5"
                  >
                    <div className="flex items-center justify-between text-[length:var(--text-xs)] text-[var(--color-text-primary)]">
                      <span>{t('anchored.nav.checkpoint_iteration', { iteration: checkpoint.iteration })}</span>
                      <span className="text-[var(--color-text-muted)]">{checkpoint.status}</span>
                    </div>
                    <p className="mt-0.5 text-[length:var(--text-2xs)] text-[var(--color-text-muted)]">
                      {checkpoint.created_at && Number.isFinite(Date.parse(checkpoint.created_at)) ? formatDateTime(checkpoint.created_at) : '-'}
                    </p>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      )}
    </nav>
  );
}
