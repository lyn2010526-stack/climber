import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { resetAnchoredStore, useAnchoredStore } from './anchored';

const rule = { id: 'soul', kind: 'soul', scope: 'user', title: 'soul', content: 'saved', revision: 'a'.repeat(64) };
beforeEach(() => {
  resetAnchoredStore();
  localStorage.setItem('auth_token', 'test-token');
});
afterEach(() => {
  vi.unstubAllGlobals();
  localStorage.removeItem('auth_token');
});

it('uses the real apiClient to serialize owner-authenticated GET and revision PUT (mocked fetch)', async () => {
  const fetchMock = vi.fn()
    .mockResolvedValueOnce(new Response(JSON.stringify([rule]), { headers: { 'Content-Type': 'application/json' } }))
    .mockResolvedValueOnce(new Response(JSON.stringify({ ...rule, content: '' }), { headers: { 'Content-Type': 'application/json' } }));
  vi.stubGlobal('fetch', fetchMock);
  await useAnchoredStore.getState().loadRules();
  await useAnchoredStore.getState().saveRule('soul', '');
  expect(fetchMock).toHaveBeenNthCalledWith(1, '/api/v1/ui/rules', expect.objectContaining({ method: 'GET', headers: expect.objectContaining({ Authorization: 'Bearer test-token' }) }));
  expect(fetchMock).toHaveBeenNthCalledWith(2, '/api/v1/ui/rules/soul', expect.objectContaining({ method: 'PUT', body: JSON.stringify({ content: '', revision: rule.revision }) }));
});

it('propagates backend conflict detail through the real apiClient (mocked fetch)', async () => {
  vi.stubGlobal('fetch', vi.fn()
    .mockResolvedValueOnce(new Response(JSON.stringify([rule]), { headers: { 'Content-Type': 'application/json' } }))
    .mockResolvedValueOnce(new Response(JSON.stringify({ detail: 'Rule changed; reload its current revision' }), { status: 409, headers: { 'Content-Type': 'application/json' } })));
  await useAnchoredStore.getState().loadRules();
  useAnchoredStore.getState().setRuleDraft('soul', 'draft');
  expect(await useAnchoredStore.getState().saveRule('soul', 'draft')).toBe(false);
  expect(useAnchoredStore.getState().ruleConflictId).toBe('soul');
  expect(useAnchoredStore.getState().rulesError).toBe('Rule changed; reload its current revision');
  expect(useAnchoredStore.getState().ruleDrafts.soul).toBe('draft');
});
