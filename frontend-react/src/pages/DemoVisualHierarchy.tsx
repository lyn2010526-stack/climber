import React from 'react';
import { 
  Bot, CheckCircle2, AlertCircle, Info, Loader2, XCircle, 
  AlertTriangle, Sparkles, Settings, Search, Plus, Trash2,
  ChevronRight, Bell, Mail, Shield, CreditCard, Users
} from 'lucide-react';
import { Card } from '../components/extended/Card';
import { Button } from '../components/extended/Button';
import { Input } from '../components/extended/Input';
import { Badge } from '../components/extended/Badge';

/** Visual Hierarchy Demo Page - LineCodePro Standard */
export default function DemoVisualHierarchy() {
  return (
    <div className="min-h-screen bg-bg-page text-text-primary p-8">
      {/* Header */}
      <header className="mb-12 pb-8 border-b border-border-subtle">
        <h1 className="text-4xl font-bold mb-3 tracking-tight">视觉层级设计系统</h1>
        <p className="text-text-level-2 leading-relaxed max-w-2xl">
          基于 LineCodePro / LobeChat / OpenWebUI 标准的完整 UI 视觉增强系统
        </p>
      </header>

      {/* Section: Typography */}
      <section className="mb-12">
        <h2 className="text-2xl font-semibold mb-6 flex items-center gap-2">
          <Sparkles className="w-5 h-5 text-accent" />
          排版系统
        </h2>
        <div className="grid gap-6">
          <Card padding="lg">
            <div className="space-y-4">
              <div><h1 className="text-h1">标题 1 (36px) - 主标题</h1></div>
              <div><h2 className="text-h2">标题 2 (30px) - 章节标题</h2></div>
              <div><h3 className="text-h3">标题 3 (24px) - 子章节</h3></div>
              <div><h4 className="text-h4">标题 4 (19px) - 小节标题</h4></div>
              <div><p className="text-body-lg">正文大 (15px) - 主要段落内容</p></div>
              <div><p className="text-body-md">正文小 (14px) - 辅助文本</p></div>
              <div><p className="text-caption">说明文字 (12px) - 辅助信息</p></div>
            </div>
          </Card>
          
          <Card padding="lg">
            <h3 className="text-title-md mb-4">字重对比</h3>
            <div className="flex flex-wrap gap-4">
              <span className="font-thin">Thin 100</span>
              <span className="font-light">Light 300</span>
              <span className="font-normal">Normal 400</span>
              <span className="font-medium">Medium 500</span>
              <span className="font-semibold">Semibold 600</span>
              <span className="font-bold">Bold 700</span>
            </div>
          </Card>
        </div>
      </section>

      {/* Section: Colors */}
      <section className="mb-12">
        <h2 className="text-2xl font-semibold mb-6 flex items-center gap-2">
          <Settings className="w-5 h-5 text-accent" />
          色彩系统
        </h2>
        <div className="grid md:grid-cols-2 gap-6">
          {/* Surface Layers */}
          <Card padding="lg">
            <h3 className="text-title-md mb-4">表面层级 (Surface Layers)</h3>
            <div className="space-y-3">
              <div className="flex items-center justify-between p-3 rounded-lg bg-surface-1 border border-border-subtle">
                <span className="text-sm text-text-level-2">Page (黑色画布)</span>
                <div className="w-32 h-8 rounded bg-surface-page" />
              </div>
              <div className="flex items-center justify-between p-3 rounded-lg bg-surface-1 border border-border-subtle">
                <span className="text-sm text-text-level-2">Surface 1 (卡片基底)</span>
                <div className="w-32 h-8 rounded bg-surface-1" />
              </div>
              <div className="flex items-center justify-between p-3 rounded-lg bg-surface-1 border border-border-subtle">
                <span className="text-sm text-text-level-2">Surface 2 (悬停态)</span>
                <div className="w-32 h-8 rounded bg-surface-2" />
              </div>
              <div className="flex items-center justify-between p-3 rounded-lg bg-surface-1 border border-border-subtle">
                <span className="text-sm text-text-level-2">Surface 3 (抬升)</span>
                <div className="w-32 h-8 rounded bg-surface-3" />
              </div>
              <div className="flex items-center justify-between p-3 rounded-lg bg-surface-1 border border-border-subtle">
                <span className="text-sm text-text-level-2">Surface 4 (强抬升)</span>
                <div className="w-32 h-8 rounded bg-surface-4" />
              </div>
            </div>
          </Card>

          {/* Semantic Colors */}
          <Card padding="lg">
            <h3 className="text-title-md mb-4">语义状态色</h3>
            <div className="grid grid-cols-2 gap-4">
              <div className="rounded-xl p-4 bg-success border border-success-strong">
                <CheckCircle2 className="w-8 h-8 mb-2 text-success" />
                <p className="text-sm text-success">Success</p>
              </div>
              <div className="rounded-xl p-4 bg-warning border border-warning-strong">
                <AlertTriangle className="w-8 h-8 mb-2 text-warning" />
                <p className="text-sm text-warning">Warning</p>
              </div>
              <div className="rounded-xl p-4 bg-error border border-error-strong">
                <XCircle className="w-8 h-8 mb-2 text-error" />
                <p className="text-sm text-error">Error</p>
              </div>
              <div className="rounded-xl p-4 bg-accent-subtle border border-accent-border">
                <Info className="w-8 h-8 mb-2 text-accent" />
                <p className="text-sm text-accent">Info</p>
              </div>
            </div>
          </Card>
        </div>
      </section>

      {/* Section: Shadows */}
      <section className="mb-12">
        <h2 className="text-2xl font-semibold mb-6 flex items-center gap-2">
          <Shield className="w-5 h-5 text-accent" />
          阴影系统 (4 个层级)
        </h2>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          <Card variant="filled" shadow="none" padding="md">
            <p className="text-xs text-text-level-3 mb-2">No Shadow</p>
            <div className="w-full h-12 bg-surface-2 rounded" />
          </Card>
          <Card variant="filled" shadow="sm" padding="md">
            <p className="text-xs text-text-level-3 mb-2">Shadow SM</p>
            <div className="w-full h-12 bg-surface-2 rounded" />
          </Card>
          <Card variant="filled" shadow="md" padding="md">
            <p className="text-xs text-text-level-3 mb-2">Shadow MD</p>
            <div className="w-full h-12 bg-surface-2 rounded" />
          </Card>
          <Card variant="filled" shadow="lg" padding="md">
            <p className="text-xs text-text-level-3 mb-2">Shadow LG</p>
            <div className="w-full h-12 bg-surface-2 rounded" />
          </Card>
          <Card variant="filled" shadow="xl" padding="md">
            <p className="text-xs text-text-level-3 mb-2">Shadow XL</p>
            <div className="w-full h-12 bg-surface-2 rounded" />
          </Card>
        </div>
      </section>

      {/* Section: Borders & Radius */}
      <section className="mb-12">
        <h2 className="text-2xl font-semibold mb-6 flex items-center gap-2">
          <Settings className="w-5 h-5 text-accent" />
          圆角系统
        </h2>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          {[
            { name: 'SM', value: '4px', class: 'rounded-sm' },
            { name: 'MD', value: '8px', class: 'rounded' },
            { name: 'LG', value: '12px', class: 'rounded-lg' },
            { name: 'XL', value: '16px', class: 'rounded-xl' },
            { name: 'Full', value: '9999px', class: 'rounded-full' },
          ].map((item) => (
            <Card key={item.name} padding="md">
              <p className="text-xs text-text-level-3 mb-2">{item.name} ({item.value})</p>
              <div className={`w-full h-12 ${item.class} bg-surface-2`} />
            </Card>
          ))}
        </div>
      </section>

      {/* Section: Cards */}
      <section className="mb-12">
        <h2 className="text-2xl font-semibold mb-6 flex items-center gap-2">
          <Bot className="w-5 h-5 text-accent" />
          卡片组件
        </h2>
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
          <Card variant="default" interactive hoverLift>
            <div className="mb-3">
              <Badge variant="primary">Default</Badge>
            </div>
            <p className="text-body-md text-text-level-2">默认卡片样式，带细微阴影和悬停效果</p>
          </Card>
          
          <Card variant="elevated" padding="md">
            <div className="mb-3">
              <Badge variant="secondary">Elevated</Badge>
            </div>
            <p className="text-body-md text-text-level-2">抬高样式，更强的边界感和阴影层次</p>
          </Card>
          
          <Card variant="filled" padding="md">
            <div className="mb-3">
              <Badge variant="warning">Filled</Badge>
            </div>
            <p className="text-body-md text-text-level-2">填充样式，用于强调内容的容器</p>
          </Card>
          
          <Card variant="outlined" padding="md">
            <div className="mb-3">
              <Badge variant="error">Outlined</Badge>
            </div>
            <p className="text-body-md text-text-level-2">轮廓样式，最小化的视觉干扰</p>
          </Card>
          
          <Card loading padding="md">
            <div className="mb-3">
              <Skeleton className="w-20 h-6 rounded-md" />
            </div>
            <div className="space-y-2">
              <Skeleton className="w-full h-4 rounded" />
              <Skeleton className="w-2/3 h-4 rounded" />
            </div>
          </Card>
        </div>
      </section>

      {/* Section: Buttons */}
      <section className="mb-12">
        <h2 className="text-2xl font-semibold mb-6 flex items-center gap-2">
          <Plus className="w-5 h-5 text-accent" />
          按钮系统
        </h2>
        <div className="space-y-6">
          <div>
            <h3 className="text-title-md mb-3">主要变体</h3>
            <div className="flex flex-wrap gap-3">
              <Button variant="primary" leadingIcon={<Plus size={16}/>}>Primary</Button>
              <Button variant="secondary" leadingIcon={<Settings size={16}/>}>Secondary</Button>
              <Button variant="ghost" leadingIcon={<Search size={16}/>}>Ghost</Button>
              <Button variant="destructive" leadingIcon={<Trash2 size={16}/>}>Destructive</Button>
            </div>
          </div>
          
          <div>
            <h3 className="text-title-md mb-3">尺寸变体</h3>
            <div className="flex flex-wrap gap-3 items-center">
              <Button variant="primary" size="sm">Small</Button>
              <Button variant="primary">Medium</Button>
              <Button variant="primary" size="lg">Large</Button>
              <Button variant="primary" size="sm" trailingIcon={<ChevronRight size={16}/>} />
            </div>
          </div>
          
          <div>
            <h3 className="text-title-md mb-3">交互状态</h3>
            <div className="flex flex-wrap gap-3">
              <Button variant="primary" loading>Loading State</Button>
              <Button variant="primary" disabled>Disabled State</Button>
            </div>
          </div>
        </div>
      </section>

      {/* Section: Inputs */}
      <section className="mb-12">
        <h2 className="text-2xl font-semibold mb-6 flex items-center gap-2">
          <Settings className="w-5 h-5 text-accent" />
          输入框系统
        </h2>
        <div className="grid md:grid-cols-2 gap-6">
          <Card padding="lg">
            <h3 className="text-title-md mb-4">基础输入框</h3>
            <div className="space-y-4">
              <Input label="正常状态" placeholder="请输入..." />
              <Input label="聚焦状态" defaultValue="Focused state with glow ring" />
              <Input label="错误状态" error="请输入有效的邮箱地址" placeholder="user@example.com" />
              <Input label="成功状态" success defaultValue="valid@email.com" />
              <Input label="禁用状态" disabled defaultValue="Cannot edit" />
            </div>
          </Card>
          
          <Card padding="lg">
            <h3 className="text-title-md mb-4">尺寸与变体</h3>
            <div className="space-y-4">
              <Input size="sm" label="Small (28px)" placeholder="Small input" />
              <Input size="md" label="Medium (36px)" placeholder="Medium input" />
              <Input size="lg" label="Large (44px)" placeholder="Large input" />
            </div>
            
            <h3 className="text-title-md mt-6 mb-4">带图标输入</h3>
            <Input 
              label="搜索输入框"
              leadingIcon={<Search size={16} />}
              placeholder="搜索..."
            />
          </Card>
        </div>
      </section>

      {/* Section: Badges & Tags */}
      <section className="mb-12">
        <h2 className="text-2xl font-semibold mb-6 flex items-center gap-2">
          <Badge variant="primary">徽章</Badge>
          徽标与标签
        </h2>
        <div className="grid md:grid-cols-2 gap-6">
          <Card padding="lg">
            <h3 className="text-title-md mb-4">状态徽章</h3>
            <div className="flex flex-wrap gap-3">
              <Badge variant="success" leadingIcon={<CheckCircle2 size={12}/>}>Success</Badge>
              <Badge variant="warning" leadingIcon={<AlertTriangle size={12}/>}>Warning</Badge>
              <Badge variant="error" leadingIcon={<XCircle size={12}/>}>Error</Badge>
              <Badge variant="info" leadingIcon={<Info size={12}/>}>Info</Badge>
            </div>
          </Card>
          
          <Card padding="lg">
            <h3 className="text-title-md mb-4">功能标签</h3>
            <div className="flex flex-wrap gap-2">
              <span className="tag"><Bell size={12}/> Notifications</span>
              <span className="tag"><Mail size={12}/> Messages</span>
              <span className="tag"><Users size={12}/> Team</span>
              <span className="tag"><CreditCard size={12}/> Billing</span>
            </div>
          </Card>
        </div>
      </section>

      {/* Section: Alert Messages */}
      <section className="mb-12">
        <h2 className="text-2xl font-semibold mb-6 flex items-center gap-2">
          <AlertCircle className="w-5 h-5 text-accent" />
          提示消息
        </h2>
        <div className="space-y-3 max-w-2xl">
          <div className="alert alert-info flex items-start gap-3">
            <Info className="w-5 h-5 mt-0.5 flex-shrink-0" />
            <div>
              <h4 className="font-semibold text-base">Information</h4>
              <p className="text-sm opacity-90">这是一个信息提示，用于展示一般性提示信息。</p>
            </div>
          </div>
          
          <div className="alert alert-success flex items-start gap-3">
            <CheckCircle2 className="w-5 h-5 mt-0.5 flex-shrink-0" />
            <div>
              <h4 className="font-semibold text-base">Success</h4>
              <p className="text-sm opacity-90">操作成功完成，数据已保存。</p>
            </div>
          </div>
          
          <div className="alert alert-warning flex items-start gap-3">
            <AlertTriangle className="w-5 h-5 mt-0.5 flex-shrink-0" />
            <div>
              <h4 className="font-semibold text-base">Warning</h4>
              <p className="text-sm opacity-90">请注意，您的订阅即将到期。</p>
            </div>
          </div>
          
          <div className="alert alert-error flex items-start gap-3">
            <XCircle className="w-5 h-5 mt-0.5 flex-shrink-0" />
            <div>
              <h4 className="font-semibold text-base">Error</h4>
              <p className="text-sm opacity-90">请求失败，请检查网络连接后重试。</p>
            </div>
          </div>
        </div>
      </section>

      {/* Section: Loading States */}
      <section className="mb-12">
        <h2 className="text-2xl font-semibold mb-6 flex items-center gap-2">
          <Loader2 className="w-5 h-5 text-accent animate-spin" />
          加载状态
        </h2>
        <div className="grid md:grid-cols-3 gap-6">
          <Card padding="md" className="flex flex-col items-center gap-3">
            <Loader2 className="w-6 h-6 animate-spin text-accent" />
            <p className="text-sm text-text-level-2">Loading Icon</p>
          </Card>
          
          <Card padding="md" className="flex items-center justify-center gap-3">
            <div className="progress-bar w-48">
              <div className="progress-fill" style={{ width: '60%' }} />
            </div>
            <span className="text-sm text-text-level-2">60%</span>
          </Card>
          
          <Card loading padding="md">
            <Skeleton className="w-32 h-6 mb-3 rounded" />
            <div className="space-y-2">
              <Skeleton className="w-full h-4 rounded" />
              <Skeleton className="w-5/6 h-4 rounded" />
              <Skeleton className="w-4/6 h-4 rounded" />
            </div>
          </Card>
        </div>
      </section>

      {/* Footer */}
      <footer className="pt-8 border-t border-border-subtle text-center">
        <p className="text-text-level-3">视觉层级设计系统 · LineCodePro 标准</p>
      </footer>
    </div>
  );
}

// Simple Skeleton component
function Skeleton({ className }: { className?: string }) {
  return <div className={`skeleton ${className}`} />;
}
