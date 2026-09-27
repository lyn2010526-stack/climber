import { describe, it, expect } from 'vitest';
import {
  PERMISSION_MODES,
  PERMISSION_MODE_INFO,
  autonomyLevelForMode,
  isPermissionMode,
  modeForAutonomyLevel,
  modeForAutonomyMove,
  normalizePermissionMode,
} from '../permissionMode';

/**
 * The permission UI used to describe two modes the backend does not have
 * ("sandbox", "native") and a five-step autonomy slider stored as local state
 * the API never received. These cases pin the vocabulary to
 * `app/core/permission_rules.py` and keep every slider position mapped to a mode
 * the backend can actually store.
 */
describe('permission modes mirror the backend vocabulary', () => {
  it('accepts exactly the modes the backend rule engine defines', () => {
    expect([...PERMISSION_MODES].sort()).toEqual(
      ['acceptEdits', 'auto', 'bypass', 'default', 'plan', 'strict'].sort(),
    );
    for (const mode of PERMISSION_MODES) {
      expect(isPermissionMode(mode)).toBe(true);
      expect(PERMISSION_MODE_INFO[mode]).toBeTruthy();
    }
  });

  it('rejects the invented modes and reports an unusable value as null', () => {
    expect(isPermissionMode('sandbox')).toBe(false);
    expect(isPermissionMode('native')).toBe(false);
    expect(normalizePermissionMode('sandbox')).toBeNull();
    expect(normalizePermissionMode(undefined)).toBeNull();
    expect(normalizePermissionMode(null)).toBeNull();
    expect(normalizePermissionMode('plan')).toBe('plan');
  });

  it('describes each mode without claiming access the rules do not grant', () => {
    // `bypass` is the backend skipping its own checks, not the frontend handing
    // out system-wide access.
    expect(PERMISSION_MODE_INFO.bypass.label).toBe('跳过检查');
    expect(PERMISSION_MODE_INFO.bypass.summary).toContain('后端');
    for (const [mode, info] of Object.entries(PERMISSION_MODE_INFO)) {
      expect(info.summary.length).toBeGreaterThan(0);
      expect(info.label.length).toBeGreaterThan(0);
      expect(isPermissionMode(mode)).toBe(true);
    }
  });
});

describe('the autonomy slider is a view of the backend mode', () => {
  it('maps every stop onto a storable mode and back', () => {
    for (const mode of PERMISSION_MODES) {
      const level = autonomyLevelForMode(mode);
      expect(level).not.toBeNull();
      // `plan` and `strict` share level 1, so the round trip only has to hold
      // for the modes the slider itself can select.
      if (mode !== 'plan') expect(modeForAutonomyLevel(level!)).toBe(mode);
    }
  });

  it('leaves the position unreported when no mode is known', () => {
    expect(autonomyLevelForMode(null)).toBeNull();
  });

  it('keeps the exact mode when the user re-selects the current stop', () => {
    // Level 1 is shared by `strict` and `plan`; clicking it while on `plan`
    // must not silently rewrite the stored mode to `strict`.
    expect(modeForAutonomyMove(1, 'plan')).toBe('plan');
    expect(modeForAutonomyMove(1, 'strict')).toBe('strict');
    expect(modeForAutonomyMove(4, 'plan')).toBe('auto');
  });

  it('holds the current mode when the level is out of range', () => {
    expect(modeForAutonomyMove(99, 'default')).toBe('default');
    expect(modeForAutonomyMove(99, null)).toBeNull();
  });
});
