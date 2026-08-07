import { describe, it, expect, vi } from 'vitest';
import * as utils from '../durationUtils';

describe('durationUtils', () => {
  describe('durationDebounce', () => {
    it('debounces function calls', () => {
      vi.useFakeTimers();
      const fn = vi.fn();
      const debounced = utils.durationDebounce(fn, 100);
      debounced();
      debounced();
      vi.advanceTimersByTime(100);
      expect(fn).toHaveBeenCalledTimes(1);
      vi.useRealTimers();
    });

    it('passes arguments correctly', () => {
      vi.useFakeTimers();
      const fn = vi.fn();
      const debounced = utils.durationDebounce(fn, 50);
      debounced('a', 'b');
      vi.advanceTimersByTime(50);
      expect(fn).toHaveBeenCalledWith('a', 'b');
      vi.useRealTimers();
    });
  });

  describe('durationThrottle', () => {
    it('throttles function calls', () => {
      vi.useFakeTimers();
      const fn = vi.fn();
      const throttled = utils.durationThrottle(fn, 100);
      throttled();
      throttled();
      expect(fn).toHaveBeenCalledTimes(1);
      vi.advanceTimersByTime(100);
      throttled();
      expect(fn).toHaveBeenCalledTimes(2);
      vi.useRealTimers();
    });
  });

  describe('durationDeepClone', () => {
    it('clones primitives', () => {
      expect(utils.durationDeepClone(5)).toBe(5);
      expect(utils.durationDeepClone('abc')).toBe('abc');
      expect(utils.durationDeepClone(null)).toBe(null);
    });

    it('deep clones nested objects', () => {
      const obj = { a: { b: [1, 2] } };
      const cloned = utils.durationDeepClone(obj);
      expect(cloned).toEqual(obj);
      expect(cloned).not.toBe(obj);
      expect(cloned['a']['b']).not.toBe(obj['a']['b']);
    });
  });

  describe('durationGenerateId', () => {
    it('generates id with prefix', () => {
      const id = utils.durationGenerateId('test_');
      expect(id.startsWith('test_')).toBe(true);
    });

    it('generates unique ids', () => {
      expect(utils.durationGenerateId()).not.toBe(utils.durationGenerateId());
    });
  });

  describe('durationFormatDate', () => {
    it('formats date default', () => {
      expect(utils.durationFormatDate(new Date(2024, 0, 1))).toBe('2024-01-01');
    });

    it('formats date custom', () => {
      expect(utils.durationFormatDate(new Date(2024, 11, 31), 'DD/MM')).toBe('31/12');
    });
  });

  describe('durationParseQuery', () => {
    it('parses query', () => {
      expect(utils.durationParseQuery('?a=1&b=2')).toEqual({ a: '1', b: '2' });
    });

    it('decodes uri', () => {
      expect(utils.durationParseQuery('?q=hello%20world')).toEqual({ q: 'hello world' });
    });
  });

  describe('durationBuildQuery', () => {
    it('builds query', () => {
      expect(utils.durationBuildQuery({ a: '1' })).toBe('a=1');
    });

    it('skips nulls', () => {
      expect(utils.durationBuildQuery({ a: '1', b: null })).toBe('a=1');
    });
  });

  describe('durationGroupBy', () => {
    it('groups by key', () => {
      const arr = [{ k: 'a' }, { k: 'b' }, { k: 'a' }];
      const result = utils.durationGroupBy(arr, 'k');
      expect(result['a']).toHaveLength(2);
      expect(result['b']).toHaveLength(1);
    });
  });

  describe('durationChunk', () => {
    it('chunks array', () => {
      expect(utils.durationChunk([1, 2, 3, 4], 2)).toEqual([[1, 2], [3, 4]]);
    });
  });

  describe('durationFlatten', () => {
    it('flattens', () => {
      expect(utils.durationFlatten([[1], [2, 3]])).toEqual([1, 2, 3]);
    });
  });

  describe('durationGetNested', () => {
    it('gets nested', () => {
      expect(utils.durationGetNested({ a: { b: 1 } }, 'a.b')).toBe(1);
    });

    it('returns default', () => {
      expect(utils.durationGetNested({}, 'a.b', 'def')).toBe('def');
    });
  });

  describe('durationSetNested', () => {
    it('sets nested', () => {
      const obj: any = {};
      utils.durationSetNested(obj, 'a.b', 5);
      expect(obj['a']['b']).toBe(5);
    });
  });
});
