import { MobileDesktopFallback } from './MobileDesktopFallback';

export function MobileFactoryPage() {
  return <MobileDesktopFallback title="工厂模式" description="工厂模式包含复杂的多栏编辑器，移动端提供可用回退，桌面端继续保留完整工作台。" />;
}
