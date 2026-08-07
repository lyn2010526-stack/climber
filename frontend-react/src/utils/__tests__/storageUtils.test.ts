import { describe, it, expect, vi } from 'vitest';
import * as utils from '../storageUtils';

describe('storageUtils', () => {
  describe('storageDebounce', () => {
    it('debounces function calls', () => {
      vi.useFakeTimers();
      const fn = vi.fn();
      const debounced = utils.storageDebounce(fn, 100);
      debounced();
      debounced();
      vi.advanceTimersByTime(100);
      expect(fn).toHaveBeenCalledTimes(1);
      vi.useRealTimers();
    });

    it('passes arguments correctly', () => {
      vi.useFakeTimers();
      const fn = vi.fn();
      const debounced = utils.storageDebounce(fn, 50);
      debounced('a', 'b');
      vi.advanceTimersByTime(50);
      expect(fn).toHaveBeenCalledWith('a', 'b');
      vi.useRealTimers();
    });
  });

  describe('storageThrottle', () => {
    it('throttles function calls', () => {
      vi.useFakeTimers();
      const fn = vi.fn();
      const throttled = utils.storageThrottle(fn, 100);
      throttled();
      throttled();
      expect(fn).toHaveBeenCalledTimes(1);
      vi.advanceTimersByTime(100);
      throttled();
      expect(fn).toHaveBeenCalledTimes(2);
      vi.useRealTimers();
    });
  });

  describe('storageDeepClone', () => {
    it('clones primitives', () => {
      expect(utils.storageDeepClone(5)).toBe(5);
      expect(utils.storageDeepClone('abc')).toBe('abc');
      expect(utils.storageDeepClone(null)).toBe(null);
    });

    it('deep clones nested objects', () => {
      const obj = { a: { b: [1, 2] } };
      const cloned = utils.storageDeepClone(obj);
      expect(cloned).toEqual(obj);
      expect(cloned).not.toBe(obj);
      expect(cloned['a']['b']).not.toBe(obj['a']['b']);
    });
  });

  describe('storageGenerateId', () => {
    it('generates id with prefix', () => {
      const id = utils.storageGenerateId('test_');
      expect(id.startsWith('test_')).toBe(true);
    });

    it('generates unique ids', () => {
      expect(utils.storageGenerateId()).not.toBe(utils.storageGenerateId());
    });
  });

  describe('storageFormatDate', () => {
    it('formats date default', () => {
      expect(utils.storageFormatDate(new Date(2024, 0, 1))).toBe('2024-01-01');
    });

    it('formats date custom', () => {
      expect(utils.storageFormatDate(new Date(2024, 11, 31), 'DD/MM')).toBe('31/12');
    });
  });

  describe('storageParseQuery', () => {
    it('parses query', () => {
      expect(utils.storageParseQuery('?a=1&b=2')).toEqual({ a: '1', b: '2' });
    });

    it('decodes uri', () => {
      expect(utils.storageParseQuery('?q=hello%20world')).toEqual({ q: 'hello world' });
    });
  });

  describe('storageBuildQuery', () => {
    it('builds query', () => {
      expect(utils.storageBuildQuery({ a: '1' })).toBe('a=1');
    });

    it('skips nulls', () => {
      expect(utils.storageBuildQuery({ a: '1', b: null })).toBe('a=1');
    });
  });

  describe('storageGroupBy', () => {
    it('groups by key', () => {
      const arr = [{ k: 'a' }, { k: 'b' }, { k: 'a' }];
      const result = utils.storageGroupBy(arr, 'k');
      expect(result['a']).toHaveLength(2);
      expect(result['b']).toHaveLength(1);
    });
  });

  describe('storageChunk', () => {
    it('chunks array', () => {
      expect(utils.storageChunk([1, 2, 3, 4], 2)).toEqual([[1, 2], [3, 4]]);
    });
  });

  describe('storageFlatten', () => {
    it('flattens', () => {
      expect(utils.storageFlatten([[1], [2, 3]])).toEqual([1, 2, 3]);
    });
  });

  describe('storageGetNested', () => {
    it('gets nested', () => {
      expect(utils.storageGetNested({ a: { b: 1 } }, 'a.b')).toBe(1);
    });

    it('returns default', () => {
      expect(utils.storageGetNested({}, 'a.b', 'def')).toBe('def');
    });
  });

  describe('storageSetNested', () => {
    it('sets nested', () => {
      const obj: any = {};
      utils.storageSetNested(obj, 'a.b', 5);
      expect(obj['a']['b']).toBe(5);
    });
  });
});
