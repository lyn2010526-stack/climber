import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { INFO_CARD_ORDER } from '../../../store/anchored';

/**
 * 契约测试：docs/plans/frontend-anchored-ui.md 第四节「AI 生成防乱写强制校验清单」。
 *
 * 这一组用例只扫描源码与已渲染的组件树，不修改任何生产代码。发现真实违规时
 * 断言会指出 file 与规则，交由人工修复。
 */

const SRC = resolve(process.cwd(), 'src');

function source(relative: string): string {
  return readFileSync(resolve(SRC, relative), 'utf-8');
}

// ---------------------------------------------------------------------------
// 1. 位置校验：三栏顺序必须左导航 - 中聊天 - 右信息，禁止调换
// ---------------------------------------------------------------------------
describe('锚定布局位置契约', () => {
  const layout = source('components/workspace/AnchoredWorkspaceLayout.tsx');

  it('桌面三栏按 左-中-右 顺序声明 Panel', () => {
    const left = layout.indexOf('id="anchored-left"');
    const center = layout.indexOf('id="anchored-center"');
    const right = layout.indexOf('id="anchored-right"');
    expect(left, '缺少左侧面板').toBeGreaterThan(-1);
    expect(center, '缺少中间面板').toBeGreaterThan(-1);
    expect(right, '缺少右侧面板').toBeGreaterThan(-1);
    expect(left, '三栏顺序必须左 < 中').toBeLessThan(center);
    expect(center, '三栏顺序必须中 < 右').toBeLessThan(right);
  });

  it('布局组件本身不暴露调换栏序的 prop', () => {
    // 若出现 orientation/reorder/order 之类开关，说明栏序可被调用方调换。
    expect(layout).not.toMatch(/orientation\s*=\s*['"]vertical['"]/);
    expect(layout).not.toMatch(/reverse|reorder/i);
  });

  it('各栏承载的组件在各自栏位内部顺序固定', () => {
    const leftNav = source('components/workspace/AnchoredLeftNav.tsx');
    const chat = source('components/agent/AnchoredChatColumn.tsx');
    const info = source('components/workspace/AnchoredInfoPanel.tsx');

    // 左栏自上而下：Logo 区 → 会话管理 → 技能中心 → 配置档 → 底部用户区。
    const logo = leftNav.indexOf('data-testid="anchored-logo"');
    const sessions = leftNav.indexOf('data-testid="anchored-sessions"');
    const skills = leftNav.indexOf('data-testid="anchored-skills"');
    const profiles = leftNav.indexOf('data-testid="anchored-profiles"');
    const footer = leftNav.indexOf('<footer');
    for (const [name, index] of Object.entries({ logo, sessions, skills, profiles, footer })) {
      expect(index, `${name} 缺少锚点`).toBeGreaterThan(-1);
    }
    expect(logo).toBeLessThan(sessions);
    expect(sessions).toBeLessThan(skills);
    expect(skills).toBeLessThan(profiles);
    expect(profiles).toBeLessThan(footer);

    // 中栏自上而下：标题栏 → 消息流 → 输入栈 → 状态栏。
    const title = chat.indexOf('data-testid="anchored-title-bar"');
    const scroll = chat.indexOf('data-testid="anchored-message-scroll"');
    const composer = chat.indexOf('<AnchoredComposer');
    const status = chat.indexOf('<AnchoredStatusRail');
    expect(title).toBeLessThan(scroll);
    expect(scroll).toBeLessThan(composer);
    expect(composer).toBeLessThan(status);

    // 右栏卡片顺序由 INFO_CARD_ORDER 单点定义并驱动渲染。
    expect(info).toContain('INFO_CARD_ORDER.map');
    expect(INFO_CARD_ORDER).toEqual(['taskBoard', 'tokenMeter', 'subAgentTree', 'filePreview', 'ruleEditor', 'memoryArchive']);
  });
});

// ---------------------------------------------------------------------------
// 2/3. 视觉校验：颜色必须走设计令牌，禁止硬编码 hex（除令牌定义文件）
// ---------------------------------------------------------------------------
describe('设计令牌颜色契约', () => {
  const HEX = /#[0-9a-fA-F]{3,8}\b/g;
  // 仅令牌定义文件允许出现字面 hex（index.css 的 @theme/:root，workbench.css 的 .workbench-theme）。
  const TOKEN_DEFINITION_FILES = new Set([
    'index.css',
    'styles/workbench.css',
  ]);

  it('组件源码不出现硬编码 hex 颜色', async () => {
    const { globSync } = await import('node:fs');
    const files = globSync('components/**/*.{ts,tsx}', { cwd: SRC })
      .filter((file) => !/\.(test|spec)\./.test(file) && !file.includes('__tests__'));

    const violations: string[] = [];
    for (const file of files) {
      if (TOKEN_DEFINITION_FILES.has(file)) continue;
      const matches = source(file).match(HEX);
      if (matches) violations.push(`${file}: ${[...new Set(matches)].join(', ')}`);
    }
    expect(violations, `以下组件硬编码了 hex 颜色:\n${violations.join('\n')}`).toEqual([]);
  });

  it('令牌定义文件确实定义了颜色令牌（作为白名单存在的理由）', () => {
    for (const file of TOKEN_DEFINITION_FILES) {
      expect(source(file), `${file} 应包含颜色令牌定义`).toMatch(/--color-[\w-]+:\s*#/);
    }
  });
});

// ---------------------------------------------------------------------------
// 4. 交互校验：可交互元素必须有 默认/悬停/选中/禁用 四态样式
// ---------------------------------------------------------------------------
describe('可交互元素四态契约', () => {
  it('index.css 覆盖通用控件的 hover/focus-visible/disabled 状态', () => {
    const css = source('index.css');
    expect(css).toMatch(/\.icon-button\s*\{/);
    expect(css).toMatch(/\.icon-button\s*\{[^}]*transition:/);
    expect(css).toMatch(/button:disabled,/);
    expect(css).toMatch(/cursor:\s*not-allowed/);
    expect(css).toMatch(/:focus-visible\s*\{/);
  });

  it('workbench.css 覆盖 workbench 控件的 hover/active/disabled/focus-visible', () => {
    const css = source('styles/workbench.css');
    expect(css).toMatch(/\.workbench-theme button:focus-visible/);
    expect(css).toMatch(/\.workbench-theme button:active\s*\{/);
    expect(css).toMatch(/\.workbench-theme button:disabled\s*\{/);
    expect(css).toMatch(/\.workbench-desktop-panel-button:hover\s*\{/);
  });

  it('左栏关键交互元素同时提供悬停与选中态样式', () => {
    const leftNav = source('components/workspace/AnchoredLeftNav.tsx');
    // 会话项：选中用主色浅底，悬停用 surface-2。
    expect(leftNav).toMatch(/hover:bg-\[var\(--color-bg-surface-2\)\]/);
    expect(leftNav).toMatch(/bg-\[var\(--color-accent-subtle\)\]/);
    // 禁用可见反馈。
    expect(leftNav).toMatch(/disabled:opacity-50/);
  });
});
