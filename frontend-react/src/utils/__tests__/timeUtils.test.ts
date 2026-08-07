import { describe, it, expect, vi } from 'vitest';
import * as utils from '../timeUtils';

describe('timeUtils', () => {
  describe('timeDebounce', () => {
    it('debounces function calls', () => {
      vi.useFakeTimers();
      const fn = vi.fn();
      const debounced = utils.timeDebounce(fn, 100);
      debounced();
      debounced();
      vi.advanceTimersByTime(100);
      expect(fn).toHaveBeenCalledTimes(1);
      vi.useRealTimers();
    });

    it('passes arguments correctly', () => {
      vi.useFakeTimers();
      const fn = vi.fn();
      const debounced = utils.timeDebounce(fn, 50);
      debounced('a', 'b');
      vi.advanceTimersByTime(50);
      expect(fn).toHaveBeenCalledWith('a', 'b');
      vi.useRealTimers();
    });
  });

  describe('timeThrottle', () => {
    it('throttles function calls', () => {
      vi.useFakeTimers();
      const fn = vi.fn();
      const throttled = utils.timeThrottle(fn, 100);
      throttled();
      throttled();
      expect(fn).toHaveBeenCalledTimes(1);
      vi.advanceTimersByTime(100);
      throttled();
      expect(fn).toHaveBeenCalledTimes(2);
      vi.useRealTimers();
    });
  });

  describe('timeDeepClone', () => {
    it('clones primitives', () => {
      expect(utils.timeDeepClone(5)).toBe(5);
      expect(utils.timeDeepClone('abc')).toBe('abc');
      expect(utils.timeDeepClone(null)).toBe(null);
    });

    it('deep clones nested objects', () => {
      const obj = { a: { b: [1, 2] } };
      const cloned = utils.timeDeepClone(obj);
      expect(cloned).toEqual(obj);
      expect(cloned).not.toBe(obj);
      expect(cloned['a']['b']).not.toBe(obj['a']['b']);
    });
  });

  describe('timeGenerateId', () => {
    it('generates id with prefix', () => {
      const id = utils.timeGenerateId('test_');
      expect(id.startsWith('test_')).toBe(true);
    });

    it('generates unique ids', () => {
      expect(utils.timeGenerateId()).not.toBe(utils.timeGenerateId());
    });
  });

  describe('timeFormatDate', () => {
    it('formats date default', () => {
      expect(utils.timeFormatDate(new Date(2024, 0, 1))).toBe('2024-01-01');
    });

    it('formats date custom', () => {
      expect(utils.timeFormatDate(new Date(2024, 11, 31), 'DD/MM')).toBe('31/12');
    });
  });

  describe('timeParseQuery', () => {
    it('parses query', () => {
      expect(utils.timeParseQuery('?a=1&b=2')).toEqual({ a: '1', b: '2' });
    });

    it('decodes uri', () => {
      expect(utils.timeParseQuery('?q=hello%20world')).toEqual({ q: 'hello world' });
    });
  });

  describe('timeBuildQuery', () => {
    it('builds query', () => {
      expect(utils.timeBuildQuery({ a: '1' })).toBe('a=1');
    });

    it('skips nulls', () => {
      expect(utils.timeBuildQuery({ a: '1', b: null })).toBe('a=1');
    });
  });

  describe('timeGroupBy', () => {
    it('groups by key', () => {
      const arr = [{ k: 'a' }, { k: 'b' }, { k: 'a' }];
      const result = utils.timeGroupBy(arr, 'k');
      expect(result['a']).toHaveLength(2);
      expect(result['b']).toHaveLength(1);
    });
  });

  describe('timeChunk', () => {
    it('chunks array', () => {
      expect(utils.timeChunk([1, 2, 3, 4], 2)).toEqual([[1, 2], [3, 4]]);
    });
  });

  describe('timeFlatten', () => {
    it('flattens', () => {
      expect(utils.timeFlatten([[1], [2, 3]])).toEqual([1, 2, 3]);
    });
  });

  describe('timeGetNested', () => {
    it('gets nested', () => {
      expect(utils.timeGetNested({ a: { b: 1 } }, 'a.b')).toBe(1);
    });

    it('returns default', () => {
      expect(utils.timeGetNested({}, 'a.b', 'def')).toBe('def');
    });
  });

  describe('timeSetNested', () => {
    it('sets nested', () => {
      const obj: any = {};
      utils.timeSetNested(obj, 'a.b', 5);
      expect(obj['a']['b']).toBe(5);
    });
  });
});
