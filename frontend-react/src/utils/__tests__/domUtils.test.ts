import { describe, it, expect, vi } from 'vitest';
import * as utils from '../domUtils';

describe('domUtils', () => {
  describe('domDebounce', () => {
    it('debounces function calls', () => {
      vi.useFakeTimers();
      const fn = vi.fn();
      const debounced = utils.domDebounce(fn, 100);
      debounced();
      debounced();
      vi.advanceTimersByTime(100);
      expect(fn).toHaveBeenCalledTimes(1);
      vi.useRealTimers();
    });

    it('passes arguments correctly', () => {
      vi.useFakeTimers();
      const fn = vi.fn();
      const debounced = utils.domDebounce(fn, 50);
      debounced('a', 'b');
      vi.advanceTimersByTime(50);
      expect(fn).toHaveBeenCalledWith('a', 'b');
      vi.useRealTimers();
    });
  });

  describe('domThrottle', () => {
    it('throttles function calls', () => {
      vi.useFakeTimers();
      const fn = vi.fn();
      const throttled = utils.domThrottle(fn, 100);
      throttled();
      throttled();
      expect(fn).toHaveBeenCalledTimes(1);
      vi.advanceTimersByTime(100);
      throttled();
      expect(fn).toHaveBeenCalledTimes(2);
      vi.useRealTimers();
    });
  });

  describe('domDeepClone', () => {
    it('clones primitives', () => {
      expect(utils.domDeepClone(5)).toBe(5);
      expect(utils.domDeepClone('abc')).toBe('abc');
      expect(utils.domDeepClone(null)).toBe(null);
    });

    it('deep clones nested objects', () => {
      const obj = { a: { b: [1, 2] } };
      const cloned = utils.domDeepClone(obj);
      expect(cloned).toEqual(obj);
      expect(cloned).not.toBe(obj);
      expect(cloned['a']['b']).not.toBe(obj['a']['b']);
    });
  });

  describe('domGenerateId', () => {
    it('generates id with prefix', () => {
      const id = utils.domGenerateId('test_');
      expect(id.startsWith('test_')).toBe(true);
    });

    it('generates unique ids', () => {
      expect(utils.domGenerateId()).not.toBe(utils.domGenerateId());
    });
  });

  describe('domFormatDate', () => {
    it('formats date default', () => {
      expect(utils.domFormatDate(new Date(2024, 0, 1))).toBe('2024-01-01');
    });

    it('formats date custom', () => {
      expect(utils.domFormatDate(new Date(2024, 11, 31), 'DD/MM')).toBe('31/12');
    });
  });

  describe('domParseQuery', () => {
    it('parses query', () => {
      expect(utils.domParseQuery('?a=1&b=2')).toEqual({ a: '1', b: '2' });
    });

    it('decodes uri', () => {
      expect(utils.domParseQuery('?q=hello%20world')).toEqual({ q: 'hello world' });
    });
  });

  describe('domBuildQuery', () => {
    it('builds query', () => {
      expect(utils.domBuildQuery({ a: '1' })).toBe('a=1');
    });

    it('skips nulls', () => {
      expect(utils.domBuildQuery({ a: '1', b: null })).toBe('a=1');
    });
  });

  describe('domGroupBy', () => {
    it('groups by key', () => {
      const arr = [{ k: 'a' }, { k: 'b' }, { k: 'a' }];
      const result = utils.domGroupBy(arr, 'k');
      expect(result['a']).toHaveLength(2);
      expect(result['b']).toHaveLength(1);
    });
  });

  describe('domChunk', () => {
    it('chunks array', () => {
      expect(utils.domChunk([1, 2, 3, 4], 2)).toEqual([[1, 2], [3, 4]]);
    });
  });

  describe('domFlatten', () => {
    it('flattens', () => {
      expect(utils.domFlatten([[1], [2, 3]])).toEqual([1, 2, 3]);
    });
  });

  describe('domGetNested', () => {
    it('gets nested', () => {
      expect(utils.domGetNested({ a: { b: 1 } }, 'a.b')).toBe(1);
    });

    it('returns default', () => {
      expect(utils.domGetNested({}, 'a.b', 'def')).toBe('def');
    });
  });

  describe('domSetNested', () => {
    it('sets nested', () => {
      const obj: any = {};
      utils.domSetNested(obj, 'a.b', 5);
      expect(obj['a']['b']).toBe(5);
    });
  });
});
