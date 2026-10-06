import { beforeEach, describe, expect, it, vi } from 'vitest';
import { api, ApiRequestError } from '../api';
import i18n from '../i18n/config';
import { buildMeterSnapshot, resetAnchoredStore, useAnchoredStore } from './anchored';

vi.mock('../api', async (original) => ({
  ...await original<typeof import('../api')>(),
  api: { getUiRules: vi.fn(), putUiRules: vi.fn() },
}));

const revision = 'a'.repeat(64);
const document = { id: 'soul', kind: 'soul' as const, scope: 'user' as const, title: 'soul', content: 'server', revision };
const store = () => useAnchoredStore.getState();

beforeEach(() => {
  vi.resetAllMocks();
  resetAnchoredStore();
  vi.mocked(api.getUiRules).mockResolvedValue([document]);
});

describe('account rule store (mocked transport)', () => {
  it('loads server content and sends the revision, adopting only the saved response', async () => {
    await store().loadRules();
    expect(api.getUiRules).toHaveBeenCalled();
    store().setRuleDraft('soul', 'draft');
    const saved = { ...document, content: 'draft', revision: 'b'.repeat(64) };
    vi.mocked(api.putUiRules).mockResolvedValue(saved);
    expect(await store().saveRule('soul', 'draft')).toBe(true);
    expect(api.putUiRules).toHaveBeenCalledWith('soul', { content: 'draft', revision });
    expect(store().rules[0]).toEqual(saved);
    expect(store().ruleDrafts).toEqual({});
    expect(store().rulesMessage).toContain(i18n.t('store_anchored.rules_saved'));
  });

  it('sends null revision for first creation, including empty content', async () => {
    vi.mocked(api.getUiRules).mockResolvedValue([{ ...document, content: 'first', revision: null }]);
    await store().loadRules();
    vi.mocked(api.putUiRules).mockResolvedValue({ ...document, content: '' });
    expect(await store().saveRule('soul', '')).toBe(true);
    expect(api.putUiRules).toHaveBeenCalledWith('soul', { content: '', revision: null });
  });

  it('retains drafts on conflict, blocks blind retry, and reloads a fresh revision', async () => {
    await store().loadRules();
    store().setRuleDraft('soul', 'draft');
    vi.mocked(api.putUiRules).mockRejectedValue(new ApiRequestError(409, 'Conflict', { detail: 'Rule changed' }));
    expect(await store().saveRule('soul', 'draft')).toBe(false);
    expect(store().rulesError).toBe('Rule changed');
    expect(store().ruleConflictId).toBe('soul');
    expect(store().rules[0]).toEqual(document);
    expect(await store().saveRule('soul', 'draft')).toBe(false);
    expect(api.putUiRules).toHaveBeenCalledTimes(1);
    vi.mocked(api.getUiRules).mockResolvedValue([{ ...document, revision: 'c'.repeat(64) }]);
    await store().loadRules();
    expect(store().ruleDrafts.soul).toBe('draft');
    expect(store().ruleConflictId).toBeNull();
    vi.mocked(api.putUiRules).mockResolvedValue(document);
    await store().saveRule('soul', 'draft');
    expect(api.putUiRules).toHaveBeenLastCalledWith('soul', { content: 'draft', revision: 'c'.repeat(64) });
  });

  it.each([403, 422, 500])('reports HTTP %i and preserves the draft and server content', async status => {
    await store().loadRules();
    store().setRuleDraft('soul', 'draft');
    vi.mocked(api.putUiRules).mockRejectedValue(new ApiRequestError(status, 'Failure', { detail: 'save failed' }));
    await store().saveRule('soul', 'draft');
    expect(store().rulesError).toBe('save failed');
    expect(store().ruleDrafts.soul).toBe('draft');
    expect(store().rules[0]).toEqual(document);
    expect(store().ruleSavingId).toBeNull();
  });

  it('allows retry after load failure and prevents saving an unloaded revision', async () => {
    vi.mocked(api.getUiRules).mockRejectedValueOnce(new Error('offline'));
    await store().loadRules();
    expect(store().rulesError).toBe('offline');
    expect(await store().saveRule('soul', 'draft')).toBe(false);
    expect(api.putUiRules).not.toHaveBeenCalled();
    await store().loadRules();
    expect(store().rulesLoaded).toBe(true);
    expect(store().rulesError).toBeNull();
  });

  it('deduplicates requests and preserves edits made during saving', async () => {
    await store().loadRules();
    store().setRuleDraft('soul', 'submitted');
    let resolve!: (value: typeof document) => void;
    vi.mocked(api.putUiRules).mockReturnValue(new Promise(r => { resolve = r; }));
    const pending = store().saveRule('soul', 'submitted');
    expect(await store().saveRule('soul', 'submitted')).toBe(false);
    await store().loadRules();
    expect(api.getUiRules).toHaveBeenCalledTimes(1);
    store().setRuleDraft('soul', 'newer draft');
    resolve({ ...document, content: 'submitted' });
    await pending;
    expect(store().ruleDrafts.soul).toBe('newer draft');
  });

  it('ignores stale loads after resetting the store', async () => {
    let resolve!: (value: typeof document[]) => void;
    vi.mocked(api.getUiRules).mockReturnValue(new Promise(r => { resolve = r; }));
    const pending = store().loadRules();
    resetAnchoredStore();
    resolve([document]);
    await pending;
    expect(store().rulesLoaded).toBe(false);
    expect(store().rules[0].content).toBe('');
  });
});

describe('reported meter values', () => {
  const now = new Date(2026, 9, 2, 12).getTime();
  it('keeps zero usage and distinguishes missing records', () => {
    const row = { prompt_tokens: 0, completion_tokens: 0, total_tokens: 0, created_at: new Date(now).toISOString() };
    expect(buildMeterSnapshot({ total_cost: 0, cache_hit_rate: 0 }, [row], now).meter).toEqual({
      cumulativeInputTokens: 0, cumulativeOutputTokens: 0, cacheHitRate: 0,
      estimatedCost: 0, todayTokens: 0, avgTurnTokens: 0,
    });
    expect(buildMeterSnapshot(null, [], now).meter.todayTokens).toBeNull();
    expect(buildMeterSnapshot(null, [{ ...row, created_at: new Date(now - 86400000).toISOString() }], now).meter.todayTokens).toBe(0);
  });

  it('uses the latest ten records in chronological order without mutating input', () => {
    const rows = Array.from({ length: 12 }, (_, i) => ({ prompt_tokens: i, completion_tokens: 0, total_tokens: i, created_at: new Date(now + i * 1000).toISOString() })).reverse();
    const original = [...rows];
    const result = buildMeterSnapshot(null, rows, now);
    expect(result.turnTrend.map(turn => turn.total)).toEqual([2, 3, 4, 5, 6, 7, 8, 9, 10, 11]);
    expect(result.meter.avgTurnTokens).toBe(7);
    expect(rows).toEqual(original);
  });
});
