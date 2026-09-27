import { describe, expect, it } from 'vitest';
import source from '../WorkspaceLayout.tsx?raw';

describe('WorkspaceLayout geometry contract', () => {
  it('keeps the chat column shrinkable and the inspector bounded', () => {
    expect(source).toContain('className="flex min-w-0 flex-1 overflow-hidden"');
    expect(source).toContain('<Panel minSize={40}>');
    expect(source).toContain('defaultSize={`${RIGHT_PANEL_WIDTH}px`}');
    expect(source).toContain('minSize={`${RIGHT_PANEL_MIN}px`}');
    expect(source).toContain('maxSize={`${RIGHT_PANEL_MAX}px`}');
  });

  it('uses the drawer contract on compact widths without a second resize separator', () => {
    expect(source).toContain('const showRightDrawer = rightPanelOpen && !isWideDesktop && !focusMode;');
    expect(source).toContain('data-testid="right-panel-drawer"');
    expect(source).toContain('className="relative z-20 flex h-full w-[min(360px,42%)]');
    expect(source).toContain("{showRightPanel && (");
    expect(source).toContain("{showRightDrawer && (");
  });
});
