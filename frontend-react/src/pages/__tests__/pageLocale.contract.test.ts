import { describe, expect, it } from 'vitest';
import i18n from '../../i18n';
import en from '../../locales/en.json';
import zh from '../../locales/zh-CN.json';

describe('page locale resources', () => {
  it('keeps Factory, Scheduler, plugin and evaluation key sets aligned', () => {
    function keys(value: Record<string, unknown>, prefix = ''): string[] {
      return Object.entries(value).flatMap(([key, entry]) => {
        const path = prefix ? `${prefix}.${key}` : key;
        return typeof entry === 'object' && entry !== null
          ? keys(entry as Record<string, unknown>, path)
          : [path];
      }).sort();
    }
    for (const namespace of ['factory_mode', 'scheduler', 'plugins', 'eval'] as const) {
      expect(keys(en[namespace])).toEqual(keys(zh[namespace]));
    }
  });

  it.each([
    ['en', 'Read 2 active agents and 3 provider credential configurations', 'Last: Not reported'],
    ['zh-CN', '已读取 2 个启用智能体和 3 个提供商凭据配置', '上次：未上报'],
  ])('interpolates configuration and absent timestamps in %s', (lng, configuration, stamp) => {
    const t = i18n.getFixedT(lng);
    expect(t('factory_mode.config_read_summary', { agents: 2, providers: 3 })).toBe(configuration);
    expect(t('scheduler.last_run', { stamp: t('common.not_reported') })).toBe(stamp);
  });

  it.each([
    ['en', 'Steps 0/0', 'Waiting to run', 'Active'],
    ['zh-CN', '步数 0/0', '等待执行', '活跃'],
  ])('keeps task progress and group lifecycle labels distinct in %s', (lng, progress, pending, active) => {
    const t = i18n.getFixedT(lng);
    expect(t('collaboration.steps_progress', { done: 0, total: 0 })).toBe(progress);
    expect(t('collaboration.task_status.pending')).toBe(pending);
    expect(t('collaboration.group_status.active')).toBe(active);
  });
});
