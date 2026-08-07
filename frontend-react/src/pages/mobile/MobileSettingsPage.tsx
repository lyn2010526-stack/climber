import { useState, useCallback } from 'react';
import {
  User, Bell, Shield, Palette, Globe, HelpCircle,
  LogOut, ChevronRight, Moon, Sun, Smartphone,
  Key, Database, Terminal, ExternalLink, Check
} from 'lucide-react';
import { cn } from '../../lib/utils';

interface SettingItem {
  id: string;
  label: string;
  description?: string;
  icon: typeof User;
  action?: 'navigate' | 'toggle' | 'external';
  value?: boolean;
  danger?: boolean;
}

interface SettingGroup {
  title: string;
  items: SettingItem[];
}

const SETTING_GROUPS: SettingGroup[] = [
  {
    title: '账户',
    items: [
      { id: 'profile', label: '个人资料', description: '管理你的个人信息', icon: User, action: 'navigate' },
      { id: 'api-keys', label: 'API 密钥', description: '管理 API 访问密钥', icon: Key, action: 'navigate' },
      { id: 'notifications', label: '通知设置', description: '推送和邮件通知', icon: Bell, action: 'navigate' },
    ],
  },
  {
    title: '外观',
    items: [
      { id: 'theme', label: '主题模式', description: '深色 / 浅色 / 跟随系统', icon: Moon, action: 'navigate' },
      { id: 'language', label: '语言', description: '简体中文', icon: Globe, action: 'navigate' },
      { id: 'display', label: '显示设置', description: '字体大小、紧凑模式', icon: Smartphone, action: 'navigate' },
    ],
  },
  {
    title: '数据与安全',
    items: [
      { id: 'privacy', label: '隐私设置', description: '数据收集和分享偏好', icon: Shield, action: 'navigate' },
      { id: 'storage', label: '存储管理', description: '缓存和数据清理', icon: Database, action: 'navigate' },
      { id: 'terminal', label: '终端沙箱', description: '开发环境设置', icon: Terminal, action: 'navigate' },
    ],
  },
  {
    title: '帮助与支持',
    items: [
      { id: 'help', label: '帮助中心', description: '使用指南和常见问题', icon: HelpCircle, action: 'external' },
      { id: 'feedback', label: '反馈建议', description: '告诉我们你的想法', icon: ExternalLink, action: 'external' },
    ],
  },
];

export function MobileSettingsPage() {
  const [expandedGroup, setExpandedGroup] = useState<string | null>('account');
  const [longPressTimer, setLongPressTimer] = useState<ReturnType<typeof setTimeout> | null>(null);
  const [activeItem, setActiveItem] = useState<string | null>(null);

  const handleItemPress = useCallback((id: string) => {
    setActiveItem(id);
    setTimeout(() => setActiveItem(null), 150);
  }, []);

  const handleLongPress = useCallback((id: string) => {
    setLongPressTimer(setTimeout(() => {
      setActiveItem(id);
    }, 500));
  }, []);

  const handleLongPressEnd = useCallback(() => {
    if (longPressTimer) {
      clearTimeout(longPressTimer);
      setLongPressTimer(null);
    }
    setActiveItem(null);
  }, [longPressTimer]);

  return (
    <div className="mobile-settings">
      {/* Header */}
      <div className="px-5 pt-5 pb-4">
        <h2 className="text-xl font-bold" style={{ color: 'var(--color-text-primary)' }}>
          设置
        </h2>
        <p className="text-xs mt-0.5" style={{ color: 'var(--color-text-muted)' }}>
          管理你的账户和应用偏好
        </p>
      </div>

      {/* User Card */}
      <div className="px-5 pb-4">
        <div
          className="flex items-center gap-3 p-4 rounded-2xl"
          style={{
            backgroundColor: 'var(--color-bg-surface-1)',
            border: '1px solid var(--color-border-subtle)',
          }}
        >
          <div
            className="w-12 h-12 rounded-2xl flex items-center justify-center"
            style={{ background: 'var(--gradient-accent)' }}
          >
            <User size={20} className="text-white" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-semibold truncate" style={{ color: 'var(--color-text-primary)' }}>
              用户
            </p>
            <p className="text-xs truncate" style={{ color: 'var(--color-text-muted)' }}>
              user@example.com
            </p>
          </div>
          <ChevronRight size={16} style={{ color: 'var(--color-text-muted)' }} />
        </div>
      </div>

      {/* Settings Groups */}
      <div className="px-5 pb-6 space-y-4">
        {SETTING_GROUPS.map((group) => (
          <div key={group.title}>
            <button
              onClick={() => setExpandedGroup(expandedGroup === group.title ? null : group.title)}
              className="w-full flex items-center justify-between py-2 mb-1"
              aria-expanded={expandedGroup === group.title}
            >
              <span className="text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--color-text-muted)' }}>
                {group.title}
              </span>
              <ChevronRight
                size={14}
                className={cn(
                  'transition-transform duration-200',
                  expandedGroup === group.title ? 'rotate-90' : ''
                )}
                style={{ color: 'var(--color-text-muted)' }}
              />
            </button>

            <div
              className={cn(
                'overflow-hidden transition-all duration-300 ease-[cubic-bezier(0.16,1,0.3,1)]',
                expandedGroup === group.title ? 'max-h-[500px] opacity-100' : 'max-h-0 opacity-0'
              )}
            >
              <div
                className="rounded-2xl overflow-hidden divide-y"
                style={{
                  backgroundColor: 'var(--color-bg-surface-1)',
                  border: '1px solid var(--color-border-subtle)',
                  borderColor: 'var(--color-border-subtle)',
                }}
              >
                {group.items.map((item, idx) => (
                  <button
                    key={item.id}
                    onClick={() => handleItemPress(item.id)}
                    onTouchStart={() => handleLongPress(item.id)}
                    onTouchEnd={handleLongPressEnd}
                    onMouseDown={() => handleLongPress(item.id)}
                    onMouseUp={handleLongPressEnd}
                    onMouseLeave={handleLongPressEnd}
                    className={cn(
                      'w-full flex items-center gap-3 px-4 py-3.5 transition-all duration-200',
                      'min-h-[56px]',
                      activeItem === item.id ? 'scale-[0.98] bg-[var(--color-bg-surface-2)]' : '',
                      idx !== group.items.length - 1 ? 'border-b border-[var(--color-border-subtle)]' : ''
                    )}
                    style={{
                      borderBottomColor: idx !== group.items.length - 1 ? 'var(--color-border-subtle)' : undefined,
                    }}
                  >
                    <div
                      className="w-8 h-8 rounded-xl flex items-center justify-center shrink-0"
                      style={{
                        backgroundColor: item.danger ? 'var(--color-error-subtle)' : 'var(--color-bg-surface-2)',
                      }}
                    >
                      <item.icon
                        size={16}
                        style={{ color: item.danger ? 'var(--color-error)' : 'var(--color-text-secondary)' }}
                      />
                    </div>
                    <div className="flex-1 text-left min-w-0">
                      <p
                        className="text-sm font-medium"
                        style={{ color: item.danger ? 'var(--color-error)' : 'var(--color-text-primary)' }}
                      >
                        {item.label}
                      </p>
                      {item.description && (
                        <p className="text-[10px] mt-0.5 truncate" style={{ color: 'var(--color-text-muted)' }}>
                          {item.description}
                        </p>
                      )}
                    </div>
                    {item.action === 'navigate' && (
                      <ChevronRight size={16} style={{ color: 'var(--color-text-muted)' }} />
                    )}
                    {item.action === 'external' && (
                      <ExternalLink size={14} style={{ color: 'var(--color-text-muted)' }} />
                    )}
                  </button>
                ))}
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Logout Button */}
      <div className="px-5 pb-8">
        <button
          className="w-full flex items-center justify-center gap-2 py-3.5 rounded-2xl transition-all duration-200 active:scale-[0.98] min-h-[48px]"
          style={{
            backgroundColor: 'var(--color-error-subtle)',
            border: '1px solid var(--color-error-subtle)',
          }}
        >
          <LogOut size={16} style={{ color: 'var(--color-error)' }} />
          <span className="text-sm font-medium" style={{ color: 'var(--color-error)' }}>
            退出登录
          </span>
        </button>
      </div>

      {/* Version Info */}
      <div className="text-center pb-6">
        <p className="text-[10px]" style={{ color: 'var(--color-text-muted)' }}>
          Climber v1.0.0
        </p>
      </div>
    </div>
  );
}
