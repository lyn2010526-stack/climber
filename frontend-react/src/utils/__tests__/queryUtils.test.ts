import { describe, it, expect, vi } from 'vitest';
import * as utils from '../queryUtils';

describe('queryUtils', () => {
  describe('queryDebounce', () => {
    it('debounces function calls', () => {
      vi.useFakeTimers();
      const fn = vi.fn();
      const debounced = utils.queryDebounce(fn, 100);
      debounced();
      debounced();
      vi.advanceTimersByTime(100);
      expect(fn).toHaveBeenCalledTimes(1);
      vi.useRealTimers();
    });

    it('passes arguments correctly', () => {
      vi.useFakeTimers();
      const fn = vi.fn();
      const debounced = utils.queryDebounce(fn, 50);
      debounced('a', 'b');
      vi.advanceTimersByTime(50);
      expect(fn).toHaveBeenCalledWith('a', 'b');
      vi.useRealTimers();
    });
  });

  describe('queryThrottle', () => {
    it('throttles function calls', () => {
      vi.useFakeTimers();
      const fn = vi.fn();
      const throttled = utils.queryThrottle(fn, 100);
      throttled();
      throttled();
      expect(fn).toHaveBeenCalledTimes(1);
      vi.advanceTimersByTime(100);
      throttled();
      expect(fn).toHaveBeenCalledTimes(2);
      vi.useRealTimers();
    });
  });

  describe('queryDeepClone', () => {
    it('clones primitives', () => {
      expect(utils.queryDeepClone(5)).toBe(5);
      expect(utils.queryDeepClone('abc')).toBe('abc');
      expect(utils.queryDeepClone(null)).toBe(null);
    });

    it('deep clones nested objects', () => {
      const obj = { a: { b: [1, 2] } };
      const cloned = utils.queryDeepClone(obj);
      expect(cloned).toEqual(obj);
      expect(cloned).not.toBe(obj);
      expect(cloned['a']['b']).not.toBe(obj['a']['b']);
    });
  });

  describe('queryGenerateId', () => {
    it('generates id with prefix', () => {
      const id = utils.queryGenerateId('test_');
      expect(id.startsWith('test_')).toBe(true);
    });

    it('generates unique ids', () => {
      expect(utils.queryGenerateId()).not.toBe(utils.queryGenerateId());
    });
  });

  describe('queryFormatDate', () => {
    it('formats date default', () => {
      expect(utils.queryFormatDate(new Date(2024, 0, 1))).toBe('2024-01-01');
    });

    it('formats date custom', () => {
      expect(utils.queryFormatDate(new Date(2024, 11, 31), 'DD/MM')).toBe('31/12');
    });
  });

  describe('queryParseQuery', () => {
    it('parses query', () => {
      expect(utils.queryParseQuery('?a=1&b=2')).toEqual({ a: '1', b: '2' });
    });

    it('decodes uri', () => {
      expect(utils.queryParseQuery('?q=hello%20world')).toEqual({ q: 'hello world' });
    });
  });

  describe('queryBuildQuery', () => {
    it('builds query', () => {
      expect(utils.queryBuildQuery({ a: '1' })).toBe('a=1');
    });

    it('skips nulls', () => {
      expect(utils.queryBuildQuery({ a: '1', b: null })).toBe('a=1');
    });
  });

  describe('queryGroupBy', () => {
    it('groups by key', () => {
      const arr = [{ k: 'a' }, { k: 'b' }, { k: 'a' }];
      const result = utils.queryGroupBy(arr, 'k');
      expect(result['a']).toHaveLength(2);
      expect(result['b']).toHaveLength(1);
    });
  });

  describe('queryChunk', () => {
    it('chunks array', () => {
      expect(utils.queryChunk([1, 2, 3, 4], 2)).toEqual([[1, 2], [3, 4]]);
    });
  });

  describe('queryFlatten', () => {
    it('flattens', () => {
      expect(utils.queryFlatten([[1], [2, 3]])).toEqual([1, 2, 3]);
    });
  });

  describe('queryGetNested', () => {
    it('gets nested', () => {
      expect(utils.queryGetNested({ a: { b: 1 } }, 'a.b')).toBe(1);
    });

    it('returns default', () => {
      expect(utils.queryGetNested({}, 'a.b', 'def')).toBe('def');
    });
  });

  describe('querySetNested', () => {
    it('sets nested', () => {
      const obj: any = {};
      utils.querySetNested(obj, 'a.b', 5);
      expect(obj['a']['b']).toBe(5);
    });
  });
});
