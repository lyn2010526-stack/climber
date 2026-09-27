import { describe, expect, it } from 'vitest';
import { isActiveTaskStatus, taskStatusLabel } from './taskStatus';

const translate = (key: string) => ({
  'collaboration.not_reported': 'Not reported',
  'collaboration.task_status.pending': 'Pending',
  'collaboration.task_status.running': 'Running',
}[key] ?? key);

describe('task status contract', () => {
  it('only treats backend active states as active', () => {
    expect(isActiveTaskStatus('pending')).toBe(true);
    expect(isActiveTaskStatus('running')).toBe(true);
    expect(isActiveTaskStatus('paused')).toBe(false);
    expect(isActiveTaskStatus('unknown')).toBe(false);
    expect(isActiveTaskStatus(null)).toBe(false);
  });

  it('keeps backend terminal vocabulary explicit', () => {
    expect(isActiveTaskStatus('stopped')).toBe(false);
    expect(taskStatusLabel('stopped', translate)).toBe('Not reported');
  });

  it('reports missing and unknown states explicitly', () => {
    expect(taskStatusLabel(undefined, translate)).toBe('Not reported');
    expect(taskStatusLabel('paused', translate)).toBe('Not reported');
    expect(taskStatusLabel('completed', translate)).toBe('collaboration.task_status.completed');
  });
});
