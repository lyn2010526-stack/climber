import { describe, it, expect, vi } from 'vitest';
import * as utils from '../urlUtils';

describe('urlUtils', () => {
  describe('urlDebounce', () => {
    it('debounces function calls', () => {
      vi.useFakeTimers();
      const fn = vi.fn();
      const debounced = utils.urlDebounce(fn, 100);
      debounced();
      debounced();
      vi.advanceTimersByTime(100);
      expect(fn).toHaveBeenCalledTimes(1);
      vi.useRealTimers();
    });

    it('passes arguments correctly', () => {
      vi.useFakeTimers();
      const fn = vi.fn();
      const debounced = utils.urlDebounce(fn, 50);
      debounced('a', 'b');
      vi.advanceTimersByTime(50);
      expect(fn).toHaveBeenCalledWith('a', 'b');
      vi.useRealTimers();
    });
  });

  describe('urlThrottle', () => {
    it('throttles function calls', () => {
      vi.useFakeTimers();
      const fn = vi.fn();
      const throttled = utils.urlThrottle(fn, 100);
      throttled();
      throttled();
      expect(fn).toHaveBeenCalledTimes(1);
      vi.advanceTimersByTime(100);
      throttled();
      expect(fn).toHaveBeenCalledTimes(2);
      vi.useRealTimers();
    });
  });

  describe('urlDeepClone', () => {
    it('clones primitives', () => {
      expect(utils.urlDeepClone(5)).toBe(5);
      expect(utils.urlDeepClone('abc')).toBe('abc');
      expect(utils.urlDeepClone(null)).toBe(null);
    });

    it('deep clones nested objects', () => {
      const obj = { a: { b: [1, 2] } };
      const cloned = utils.urlDeepClone(obj);
      expect(cloned).toEqual(obj);
      expect(cloned).not.toBe(obj);
      expect(cloned['a']['b']).not.toBe(obj['a']['b']);
    });
  });

  describe('urlGenerateId', () => {
    it('generates id with prefix', () => {
      const id = utils.urlGenerateId('test_');
      expect(id.startsWith('test_')).toBe(true);
    });

    it('generates unique ids', () => {
      expect(utils.urlGenerateId()).not.toBe(utils.urlGenerateId());
    });
  });

  describe('urlFormatDate', () => {
    it('formats date default', () => {
      expect(utils.urlFormatDate(new Date(2024, 0, 1))).toBe('2024-01-01');
    });

    it('formats date custom', () => {
      expect(utils.urlFormatDate(new Date(2024, 11, 31), 'DD/MM')).toBe('31/12');
    });
  });

  describe('urlParseQuery', () => {
    it('parses query', () => {
      expect(utils.urlParseQuery('?a=1&b=2')).toEqual({ a: '1', b: '2' });
    });

    it('decodes uri', () => {
      expect(utils.urlParseQuery('?q=hello%20world')).toEqual({ q: 'hello world' });
    });
  });

  describe('urlBuildQuery', () => {
    it('builds query', () => {
      expect(utils.urlBuildQuery({ a: '1' })).toBe('a=1');
    });

    it('skips nulls', () => {
      expect(utils.urlBuildQuery({ a: '1', b: null })).toBe('a=1');
    });
  });

  describe('urlGroupBy', () => {
    it('groups by key', () => {
      const arr = [{ k: 'a' }, { k: 'b' }, { k: 'a' }];
      const result = utils.urlGroupBy(arr, 'k');
      expect(result['a']).toHaveLength(2);
      expect(result['b']).toHaveLength(1);
    });
  });

  describe('urlChunk', () => {
    it('chunks array', () => {
      expect(utils.urlChunk([1, 2, 3, 4], 2)).toEqual([[1, 2], [3, 4]]);
    });
  });

  describe('urlFlatten', () => {
    it('flattens', () => {
      expect(utils.urlFlatten([[1], [2, 3]])).toEqual([1, 2, 3]);
    });
  });

  describe('urlGetNested', () => {
    it('gets nested', () => {
      expect(utils.urlGetNested({ a: { b: 1 } }, 'a.b')).toBe(1);
    });

    it('returns default', () => {
      expect(utils.urlGetNested({}, 'a.b', 'def')).toBe('def');
    });
  });

  describe('urlSetNested', () => {
    it('sets nested', () => {
      const obj: any = {};
      utils.urlSetNested(obj, 'a.b', 5);
      expect(obj['a']['b']).toBe(5);
    });
  });
});
