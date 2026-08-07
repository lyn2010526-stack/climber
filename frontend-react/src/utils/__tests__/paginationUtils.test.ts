import { describe, it, expect, vi } from 'vitest';
import * as utils from '../paginationUtils';

describe('paginationUtils', () => {
  describe('paginationDebounce', () => {
    it('debounces function calls', () => {
      vi.useFakeTimers();
      const fn = vi.fn();
      const debounced = utils.paginationDebounce(fn, 100);
      debounced();
      debounced();
      vi.advanceTimersByTime(100);
      expect(fn).toHaveBeenCalledTimes(1);
      vi.useRealTimers();
    });

    it('passes arguments correctly', () => {
      vi.useFakeTimers();
      const fn = vi.fn();
      const debounced = utils.paginationDebounce(fn, 50);
      debounced('a', 'b');
      vi.advanceTimersByTime(50);
      expect(fn).toHaveBeenCalledWith('a', 'b');
      vi.useRealTimers();
    });
  });

  describe('paginationThrottle', () => {
    it('throttles function calls', () => {
      vi.useFakeTimers();
      const fn = vi.fn();
      const throttled = utils.paginationThrottle(fn, 100);
      throttled();
      throttled();
      expect(fn).toHaveBeenCalledTimes(1);
      vi.advanceTimersByTime(100);
      throttled();
      expect(fn).toHaveBeenCalledTimes(2);
      vi.useRealTimers();
    });
  });

  describe('paginationDeepClone', () => {
    it('clones primitives', () => {
      expect(utils.paginationDeepClone(5)).toBe(5);
      expect(utils.paginationDeepClone('abc')).toBe('abc');
      expect(utils.paginationDeepClone(null)).toBe(null);
    });

    it('deep clones nested objects', () => {
      const obj = { a: { b: [1, 2] } };
      const cloned = utils.paginationDeepClone(obj);
      expect(cloned).toEqual(obj);
      expect(cloned).not.toBe(obj);
      expect(cloned['a']['b']).not.toBe(obj['a']['b']);
    });
  });

  describe('paginationGenerateId', () => {
    it('generates id with prefix', () => {
      const id = utils.paginationGenerateId('test_');
      expect(id.startsWith('test_')).toBe(true);
    });

    it('generates unique ids', () => {
      expect(utils.paginationGenerateId()).not.toBe(utils.paginationGenerateId());
    });
  });

  describe('paginationFormatDate', () => {
    it('formats date default', () => {
      expect(utils.paginationFormatDate(new Date(2024, 0, 1))).toBe('2024-01-01');
    });

    it('formats date custom', () => {
      expect(utils.paginationFormatDate(new Date(2024, 11, 31), 'DD/MM')).toBe('31/12');
    });
  });

  describe('paginationParseQuery', () => {
    it('parses query', () => {
      expect(utils.paginationParseQuery('?a=1&b=2')).toEqual({ a: '1', b: '2' });
    });

    it('decodes uri', () => {
      expect(utils.paginationParseQuery('?q=hello%20world')).toEqual({ q: 'hello world' });
    });
  });

  describe('paginationBuildQuery', () => {
    it('builds query', () => {
      expect(utils.paginationBuildQuery({ a: '1' })).toBe('a=1');
    });

    it('skips nulls', () => {
      expect(utils.paginationBuildQuery({ a: '1', b: null })).toBe('a=1');
    });
  });

  describe('paginationGroupBy', () => {
    it('groups by key', () => {
      const arr = [{ k: 'a' }, { k: 'b' }, { k: 'a' }];
      const result = utils.paginationGroupBy(arr, 'k');
      expect(result['a']).toHaveLength(2);
      expect(result['b']).toHaveLength(1);
    });
  });

  describe('paginationChunk', () => {
    it('chunks array', () => {
      expect(utils.paginationChunk([1, 2, 3, 4], 2)).toEqual([[1, 2], [3, 4]]);
    });
  });

  describe('paginationFlatten', () => {
    it('flattens', () => {
      expect(utils.paginationFlatten([[1], [2, 3]])).toEqual([1, 2, 3]);
    });
  });

  describe('paginationGetNested', () => {
    it('gets nested', () => {
      expect(utils.paginationGetNested({ a: { b: 1 } }, 'a.b')).toBe(1);
    });

    it('returns default', () => {
      expect(utils.paginationGetNested({}, 'a.b', 'def')).toBe('def');
    });
  });

  describe('paginationSetNested', () => {
    it('sets nested', () => {
      const obj: any = {};
      utils.paginationSetNested(obj, 'a.b', 5);
      expect(obj['a']['b']).toBe(5);
    });
  });
});
