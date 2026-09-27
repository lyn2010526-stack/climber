import type { PermissionMode } from '../../store/workspace';

/**
 * The permission vocabulary the backend owns. `PermissionMode` in
 * `app/core/permission_rules.py` and the `mode` field of
 * `GET/PUT /permissions/config` are the single source of truth; the UI only
 * reads and writes these six values.
 */
export const PERMISSION_MODES: readonly PermissionMode[] = [
  'default',
  'acceptEdits',
  'plan',
  'auto',
  'bypass',
  'strict',
];

/**
 * Wording is limited to what the backend rule engine actually does per mode.
 * No line here claims an access level the rules do not enforce, and no line
 * promises an approval prompt that never happens.
 */
export const PERMISSION_MODE_INFO: Record<PermissionMode, { label: string; summary: string }> = {
  default: { label: '默认', summary: '仅自动放行读取类操作' },
  acceptEdits: { label: '接受编辑', summary: '文件编辑自动放行' },
  plan: { label: '计划', summary: '只读规划，不执行修改' },
  auto: { label: '自动', summary: '按后端分类器做安全检查' },
  bypass: { label: '跳过检查', summary: '后端跳过权限检查' },
  strict: { label: '严格', summary: '未显式放行即拒绝' },
};

/** True when the string is one of the six modes the backend accepts. */
export function isPermissionMode(value: unknown): value is PermissionMode {
  return typeof value === 'string' && (PERMISSION_MODES as readonly string[]).includes(value);
}

/** Normalise a `mode` field, or `null` when the payload carries nothing usable. */
export function normalizePermissionMode(value: unknown): PermissionMode | null {
  return isPermissionMode(value) ? value : null;
}

/**
 * The five-step autonomy scale is a *view* of the backend mode, not a setting
 * of its own: each stop names the mode it writes, and the current mode decides
 * which stop is highlighted. `plan` shares the most restrictive stop with
 * `strict` because both refuse mutations, so moving the slider away from a stop
 * always produces a different mode.
 */
export interface AutonomyStop {
  level: number;
  mode: PermissionMode;
}

export const AUTONOMY_STOPS: readonly AutonomyStop[] = [
  { level: 1, mode: 'strict' },
  { level: 2, mode: 'default' },
  { level: 3, mode: 'acceptEdits' },
  { level: 4, mode: 'auto' },
  { level: 5, mode: 'bypass' },
];

/** The mode a stop writes, or `null` when the level is out of range. */
export function modeForAutonomyLevel(level: number): PermissionMode | null {
  return AUTONOMY_STOPS.find((stop) => stop.level === level)?.mode ?? null;
}

/**
 * The level a backend mode lands on. Only `plan` and `strict` share level 1,
 * so the caller keeps the exact mode it read and only uses the level for
 * positioning.
 */
export function autonomyLevelForMode(mode: PermissionMode | null): number | null {
  if (!mode) return null;
  return AUTONOMY_STOPS.find((stop) => stop.mode === mode)?.level
    ?? AUTONOMY_STOPS.find((stop) => stop.mode === 'strict')!.level;
}

/**
 * The mode a move to `level` should write. Selecting the level the current mode
 * already sits on keeps that mode, so a click never silently rewrites
 * `plan` into `strict`.
 */
export function modeForAutonomyMove(
  level: number,
  current: PermissionMode | null,
): PermissionMode | null {
  const target = modeForAutonomyLevel(level);
  if (target === null) return current;
  if (current && autonomyLevelForMode(current) === level) return current;
  return target;
}
