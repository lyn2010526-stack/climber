import { useState } from 'react';
import {
  User,
  Globe,
  Palette,
  Bell,
  Mail,
  Monitor,
  Shield,
  Smartphone,
  RefreshCw,
  Trash2,
  ChevronRight,
} from 'lucide-react';
import {
  IOSPage,
  IOSListGroup,
  IOSListItem,
  IOSSwitch,
  IOSSegmentedControl,
  IOSBadge,
  IOSConfirmDialog,
  toast,
} from '../components/ios';
import { cn } from '../lib/utils';

export function SettingsPageIOS() {
  const [language, setLanguage] = useState('zh');
  const [theme, setTheme] = useState('system');
  const [pushNotification, setPushNotification] = useState(true);
  const [emailNotification, setEmailNotification] = useState(false);
  const [desktopNotification, setDesktopNotification] = useState(true);
  const [twoFactorAuth, setTwoFactorAuth] = useState(true);
  const [clearCacheOpen, setClearCacheOpen] = useState(false);

  const handleClearCache = () => {
    setClearCacheOpen(false);
    toast.success('缓存已清除');
  };

  return (
    <IOSPage className="h-full overflow-y-auto">
      <div className="px-4 pt-6 pb-4 flex flex-col items-center">
        <div className="w-20 h-20 rounded-full bg-[var(--color-accent)] flex items-center justify-center mb-3">
          <User size={36} className="text-white" />
        </div>
        <h2 className="text-[var(--color-text-primary)] text-lg font-semibold">张三</h2>
        <p className="text-[var(--color-text-muted)] text-sm mt-0.5">zhangsan@example.com</p>
        <IOSBadge variant="info" className="mt-2">Pro</IOSBadge>
      </div>

      <IOSListGroup title="通用" className="mb-6">
        <IOSListItem
          icon={<Globe size={18} className="text-white" />}
          iconBg="#34C759"
          title="语言"
          detail={
            <IOSSegmentedControl
              options={[
                { value: 'zh', label: '中文' },
                { value: 'en', label: 'English' },
              ]}
              value={language}
              onChange={setLanguage}
            />
          }
          showChevron={false}
        />
        <IOSListItem
          icon={<Palette size={18} className="text-white" />}
          iconBg="#FF9500"
          title="主题"
          detail={
            <IOSSegmentedControl
              options={[
                { value: 'dark', label: '深色' },
                { value: 'light', label: '浅色' },
                { value: 'system', label: '跟随系统' },
              ]}
              value={theme}
              onChange={setTheme}
            />
          }
          showChevron={false}
        />
      </IOSListGroup>

      <IOSListGroup title="通知" className="mb-6">
        <IOSListItem
          icon={<Bell size={18} className="text-white" />}
          iconBg="#FF3B30"
          title="推送通知"
          detail={<IOSSwitch checked={pushNotification} onChange={(v) => { setPushNotification(v); toast.success(v ? '已开启推送通知' : '已关闭推送通知'); }} />}
          showChevron={false}
        />
        <IOSListItem
          icon={<Mail size={18} className="text-white" />}
          iconBg="#007AFF"
          title="邮件通知"
          detail={<IOSSwitch checked={emailNotification} onChange={(v) => { setEmailNotification(v); toast.success(v ? '已开启邮件通知' : '已关闭邮件通知'); }} />}
          showChevron={false}
        />
        <IOSListItem
          icon={<Monitor size={18} className="text-white" />}
          iconBg="#5856D6"
          title="桌面通知"
          detail={<IOSSwitch checked={desktopNotification} onChange={(v) => { setDesktopNotification(v); toast.success(v ? '已开启桌面通知' : '已关闭桌面通知'); }} />}
          showChevron={false}
        />
      </IOSListGroup>

      <IOSListGroup title="安全" className="mb-6">
        <IOSListItem
          icon={<Shield size={18} className="text-white" />}
          iconBg="#007AFF"
          title="两步验证"
          detail={
            <span className="flex items-center gap-2">
              <IOSSwitch checked={twoFactorAuth} onChange={(v) => { setTwoFactorAuth(v); toast.success(v ? '已启用两步验证' : '已关闭两步验证'); }} />
              {twoFactorAuth && <IOSBadge variant="success">已启用</IOSBadge>}
            </span>
          }
          showChevron={false}
        />
        <IOSListItem
          icon={<Smartphone size={18} className="text-white" />}
          iconBg="#FF9500"
          title="会话管理"
          detail={<ChevronRight size={16} className="text-[var(--color-text-muted)]" />}
        />
      </IOSListGroup>

      <IOSListGroup title="关于" className="mb-6">
        <IOSListItem
          icon={<RefreshCw size={18} className="text-white" />}
          iconBg="#8E8E93"
          title="版本号"
          detail={<span className="text-[var(--color-text-muted)]">2.1.0</span>}
          showChevron={false}
        />
        <IOSListItem
          icon={<RefreshCw size={18} className="text-white" />}
          iconBg="#30D158"
          title="检查更新"
          detail={<ChevronRight size={16} className="text-[var(--color-text-muted)]" />}
          onClick={() => toast.info('当前已是最新版本')}
        />
        <IOSListItem
          icon={<Trash2 size={18} className="text-white" />}
          iconBg="#FF3B30"
          title="清除缓存"
          detail={<ChevronRight size={16} className="text-[var(--color-text-muted)]" />}
          onClick={() => setClearCacheOpen(true)}
        />
      </IOSListGroup>

      <IOSListGroup className="mb-8">
        <IOSListItem
          title="退出登录"
          danger
          showChevron={false}
          onClick={() => toast.info('已退出登录')}
        />
      </IOSListGroup>

      <IOSConfirmDialog
        open={clearCacheOpen}
        onOpenChange={setClearCacheOpen}
        title="清除缓存"
        description="确定要清除所有缓存数据吗？此操作不可撤销。"
        onConfirm={handleClearCache}
        confirmText="清除"
        cancelText="取消"
        danger
      />
    </IOSPage>
  );
}
