import { useState } from 'react';
import {
  Settings, Palette, Keyboard, Cpu, Eye,
  Moon, Sun, Sunset,
} from 'lucide-react';
import { cn } from '../../lib/utils';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../ui/Card';
import { Toggle, Slider } from '../ui/Controls';

type SettingsTab = 'general' | 'appearance' | 'models' | 'shortcuts' | 'accessibility';

const THEMES = [
  { id: 'dark', label: '深色', icon: Moon, color: '#000000' },
  { id: 'light', label: '浅色', icon: Sun, color: '#f8f9fb' },
  { id: 'warm', label: '暖色', icon: Sunset, color: '#1a1512' },
];

const ACCENT_COLORS = [
  { id: 'indigo', color: '#5E6AD2' },
  { id: 'blue', color: '#3B82F6' },
  { id: 'purple', color: '#8B5CF6' },
  { id: 'pink', color: '#EC4899' },
  { id: 'green', color: '#10B981' },
  { id: 'orange', color: '#F97316' },
];

const FONT_SIZES = [
  { id: 'small', label: '小', size: '12px' },
  { id: 'medium', label: '中', size: '14px' },
  { id: 'large', label: '大', size: '16px' },
];

export function SettingsPage() {
  const [activeTab, setActiveTab] = useState<SettingsTab>('general');

  const tabs = [
    { id: 'general', label: '通用', icon: <Settings size={12} /> },
    { id: 'appearance', label: '外观', icon: <Palette size={12} /> },
    { id: 'models', label: '模型', icon: <Cpu size={12} /> },
    { id: 'shortcuts', label: '快捷键', icon: <Keyboard size={12} /> },
    { id: 'accessibility', label: '无障碍', icon: <Eye size={12} /> },
  ];

  return (
    <div className="max-w-4xl mx-auto">
      <div className="flex items-center gap-3 mb-6">
        <div className="p-2 rounded-xl bg-[var(--color-bg-surface-2)] border border-[var(--color-border-subtle)]">
          <Settings size={20} className="text-[var(--color-accent)]" />
        </div>
        <div>
          <h1 className="text-xl font-bold text-[var(--color-text-primary)]">设置</h1>
          <p className="text-sm text-[var(--color-text-muted)]">自定义你的 Climber 体验</p>
        </div>
      </div>

      <div className="flex items-center gap-1 p-1 rounded-xl mb-6 overflow-x-auto" style={{ backgroundColor: 'var(--color-bg-surface-2)' }}>
        {tabs.map(({ id, label, icon }) => (
          <button
            key={id}
            onClick={() => setActiveTab(id as SettingsTab)}
            className={cn(
              'flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-medium transition-all duration-200 whitespace-nowrap',
              activeTab === id
                ? 'bg-[var(--color-bg-surface-1)] text-[var(--color-text-primary)] shadow-sm'
                : 'text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)]'
            )}
          >
            {icon}
            {label}
          </button>
        ))}
      </div>

      <div className="space-y-4">
        {activeTab === 'general' && <GeneralSettings />}
        {activeTab === 'appearance' && <AppearanceSettings />}
        {activeTab === 'models' && <ModelSettings />}
        {activeTab === 'shortcuts' && <ShortcutSettings />}
        {activeTab === 'accessibility' && <AccessibilitySettings />}
      </div>
    </div>
  );
}

function GeneralSettings() {
  return (
    <div className="space-y-4">
      <Card variant="default" padding="md">
        <CardHeader>
          <CardTitle>语言与地区</CardTitle>
          <CardDescription>设置界面语言和日期格式</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-sm font-medium text-[var(--color-text-primary)]">界面语言</div>
              <div className="text-xs text-[var(--color-text-muted)] mt-0.5">选择显示语言</div>
            </div>
            <select className="px-3 py-1.5 rounded-lg text-xs bg-[var(--color-bg-surface-2)] border border-[var(--color-border-subtle)] text-[var(--color-text-primary)] focus:outline-none focus:border-[var(--color-accent)]/30">
              <option value="zh-CN">简体中文</option>
              <option value="en">English</option>
              <option value="ja">日本語</option>
            </select>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function AppearanceSettings() {
  const [accentColor, setAccentColor] = useState('indigo');
  const [fontSize, setFontSize] = useState('medium');
  const [compactMode, setCompactMode] = useState(false);

  return (
    <div className="space-y-4">
      <Card variant="default" padding="md">
        <CardHeader>
          <CardTitle>主题</CardTitle>
          <CardDescription>选择界面主题风格</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-3 gap-3">
            {THEMES.map(({ id, label, icon: Icon, color }) => (
              <button
                key={id}
                className="flex flex-col items-center gap-2 p-4 rounded-xl border-2 transition-all duration-200 hover:border-[var(--color-accent)]/30"
                style={{ borderColor: 'var(--color-border-subtle)' }}
                onClick={() => document.documentElement.setAttribute('data-theme', id)}
              >
                <div className="w-12 h-12 rounded-xl border border-[var(--color-border-subtle)]" style={{ backgroundColor: color }}>
                  <Icon size={20} className="w-full h-full p-3 text-white/80" />
                </div>
                <span className="text-xs font-medium text-[var(--color-text-secondary)]">{label}</span>
              </button>
            ))}
          </div>
        </CardContent>
      </Card>

      <Card variant="default" padding="md">
        <CardHeader>
          <CardTitle>强调色</CardTitle>
          <CardDescription>自定义主题强调色</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-3">
            {ACCENT_COLORS.map(({ id, color }) => (
              <button
                key={id}
                onClick={() => setAccentColor(id)}
                className={cn(
                  'w-8 h-8 rounded-full transition-all duration-200',
                  accentColor === id ? 'ring-2 ring-offset-2 scale-110' : 'hover:scale-110'
                )}
                style={{ backgroundColor: color, '--tw-ring-color': color, '--tw-ring-offset-color': 'var(--color-bg-page)' } as React.CSSProperties}
                aria-label={`选择${id}色`}
              />
            ))}
          </div>
        </CardContent>
      </Card>

      <Card variant="default" padding="md">
        <CardHeader>
          <CardTitle>字体大小</CardTitle>
          <CardDescription>调整界面字体大小</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-3">
            {FONT_SIZES.map(({ id, label, size }) => (
              <button
                key={id}
                onClick={() => setFontSize(id)}
                className={cn(
                  'flex-1 py-2 rounded-lg text-xs font-medium border transition-all duration-200',
                  fontSize === id
                    ? 'bg-[var(--color-accent-subtle)] border-[var(--color-accent)]/30 text-[var(--color-accent)]'
                    : 'bg-[var(--color-bg-surface-2)] border-[var(--color-border-subtle)] text-[var(--color-text-secondary)] hover:border-[var(--color-border-default)]'
                )}
              >
                <span style={{ fontSize: size }}>{label}</span>
              </button>
            ))}
          </div>
        </CardContent>
      </Card>

      <Card variant="default" padding="md">
        <CardHeader>
          <CardTitle>布局</CardTitle>
        </CardHeader>
        <CardContent>
          <Toggle label="紧凑模式" description="减少间距，显示更多内容" checked={compactMode} onChange={setCompactMode} />
        </CardContent>
      </Card>
    </div>
  );
}

function ModelSettings() {
  const [temperature, setTemperature] = useState(0.7);
  const [maxTokens, setMaxTokens] = useState(4096);
  const [topP, setTopP] = useState(0.9);
  const [systemPrompt, setSystemPrompt] = useState('You are a helpful AI assistant.');

  return (
    <div className="space-y-4">
      <Card variant="default" padding="md">
        <CardHeader>
          <CardTitle>模型选择</CardTitle>
          <CardDescription>选择使用的 AI 模型</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-3">
            {['GPT-4o', 'Claude 3.5', 'DeepSeek', 'Gemini Pro'].map((model) => (
              <button
                key={model}
                className={cn(
                  'flex items-center gap-3 p-3 rounded-xl border transition-all duration-200',
                  model === 'GPT-4o'
                    ? 'bg-[var(--color-accent-subtle)] border-[var(--color-accent)]/30'
                    : 'bg-[var(--color-bg-surface-2)] border-[var(--color-border-subtle)] hover:border-[var(--color-border-default)]'
                )}
              >
                <Cpu size={16} className={model === 'GPT-4o' ? 'text-[var(--color-accent)]' : 'text-[var(--color-text-muted)]'} />
                <span className={cn('text-xs font-medium', model === 'GPT-4o' ? 'text-[var(--color-accent)]' : 'text-[var(--color-text-secondary)]')}>{model}</span>
              </button>
            ))}
          </div>
        </CardContent>
      </Card>

      <Card variant="default" padding="md">
        <CardHeader>
          <CardTitle>模型参数</CardTitle>
          <CardDescription>调节模型生成行为</CardDescription>
        </CardHeader>
        <CardContent className="space-y-5">
          <Slider label="Temperature" value={temperature} onChange={setTemperature} min={0} max={2} step={0.1} description="控制输出的随机值越高，输出越多样" />
          <Slider label="Max Tokens" value={maxTokens} onChange={setMaxTokens} min={256} max={128000} step={256} unit=" tokens" description="单次回复的最大长度" />
          <Slider label="Top P" value={topP} onChange={setTopP} min={0} max={1} step={0.05} description="核采样阈值" />
        </CardContent>
      </Card>

      <Card variant="default" padding="md">
        <CardHeader>
          <CardTitle>System Prompt</CardTitle>
          <CardDescription>设置系统级提示词</CardDescription>
        </CardHeader>
        <CardContent>
          <textarea
            value={systemPrompt}
            onChange={(e) => setSystemPrompt(e.target.value)}
            className="w-full h-24 px-3 py-2 rounded-xl text-xs bg-[var(--color-bg-surface-2)] border border-[var(--color-border-subtle)] text-[var(--color-text-primary)] placeholder:text-[var(--color-text-muted)] focus:outline-none focus:border-[var(--color-accent)]/30 resize-none"
            placeholder="输入系统提示词..."
          />
        </CardContent>
      </Card>
    </div>
  );
}

function ShortcutSettings() {
  const shortcuts = [
    { action: '发送消息', keys: ['Enter'], category: '聊天' },
    { action: '新建行', keys: ['Shift', 'Enter'], category: '聊天' },
    { action: '命令面板', keys: ['⌘', 'K'], category: '全局' },
    { action: '搜索', keys: ['⌘', 'F'], category: '全局' },
    { action: '切换侧边栏', keys: ['⌘', 'B'], category: '全局' },
    { action: '停止生成', keys: ['Escape'], category: '聊天' },
    { action: '设置', keys: ['⌘', ','], category: '全局' },
  ];

  const categories = [...new Set(shortcuts.map(s => s.category))];

  return (
    <div className="space-y-4">
      <Card variant="default" padding="md">
        <CardHeader>
          <CardTitle>键盘快捷键</CardTitle>
          <CardDescription>查看和自定义快捷键</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {categories.map(category => (
            <div key={category}>
              <h4 className="text-xs font-semibold uppercase tracking-wider text-[var(--color-text-muted)] mb-2">{category}</h4>
              <div className="space-y-1">
                {shortcuts.filter(s => s.category === category).map((shortcut) => (
                  <div key={shortcut.action} className="flex items-center justify-between py-2 px-3 rounded-lg hover:bg-[var(--color-bg-surface-2)] transition-colors">
                    <span className="text-sm text-[var(--color-text-secondary)]">{shortcut.action}</span>
                    <div className="flex items-center gap-1">
                      {shortcut.keys.map((key) => (
                        <kbd key={key} className="px-2 py-0.5 rounded-md text-[10px] font-mono font-medium border" style={{ backgroundColor: 'var(--color-bg-surface-3)', borderColor: 'var(--color-border-subtle)', color: 'var(--color-text-primary)' }}>
                          {key}
                        </kbd>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}

function AccessibilitySettings() {
  const [reduceMotion, setReduceMotion] = useState(false);
  const [highContrast, setHighContrast] = useState(false);

  return (
    <div className="space-y-4">
      <Card variant="default" padding="md">
        <CardHeader>
          <CardTitle>无障碍</CardTitle>
          <CardDescription>让 Climber 更适合你</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <Toggle label="减少动画" description="禁用过渡动画和视觉效果" checked={reduceMotion} onChange={setReduceMotion} />
          <Toggle label="高对比度" description="增强文字和界面的对比度" checked={highContrast} onChange={setHighContrast} />
        </CardContent>
      </Card>
    </div>
  );
}

export default SettingsPage;
