import { describe, it, expect } from 'vitest';
import {
  PERMISSION_MODES,
  PERMISSION_MODE_INFO,
  isPermissionMode,
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
