import { describe, it, expect, vi } from 'vitest';
import * as utils from '../mathUtils';

describe('mathUtils', () => {
  describe('mathDebounce', () => {
    it('debounces function calls', () => {
      vi.useFakeTimers();
      const fn = vi.fn();
      const debounced = utils.mathDebounce(fn, 100);
      debounced();
      debounced();
      vi.advanceTimersByTime(100);
      expect(fn).toHaveBeenCalledTimes(1);
      vi.useRealTimers();
    });

    it('passes arguments correctly', () => {
      vi.useFakeTimers();
      const fn = vi.fn();
      const debounced = utils.mathDebounce(fn, 50);
      debounced('a', 'b');
      vi.advanceTimersByTime(50);
      expect(fn).toHaveBeenCalledWith('a', 'b');
      vi.useRealTimers();
    });
  });

  describe('mathThrottle', () => {
    it('throttles function calls', () => {
      vi.useFakeTimers();
      const fn = vi.fn();
      const throttled = utils.mathThrottle(fn, 100);
      throttled();
      throttled();
      expect(fn).toHaveBeenCalledTimes(1);
      vi.advanceTimersByTime(100);
      throttled();
      expect(fn).toHaveBeenCalledTimes(2);
      vi.useRealTimers();
    });
  });

  describe('mathDeepClone', () => {
    it('clones primitives', () => {
      expect(utils.mathDeepClone(5)).toBe(5);
      expect(utils.mathDeepClone('abc')).toBe('abc');
      expect(utils.mathDeepClone(null)).toBe(null);
    });

    it('deep clones nested objects', () => {
      const obj = { a: { b: [1, 2] } };
      const cloned = utils.mathDeepClone(obj);
      expect(cloned).toEqual(obj);
      expect(cloned).not.toBe(obj);
      expect(cloned['a']['b']).not.toBe(obj['a']['b']);
    });
  });

  describe('mathGenerateId', () => {
    it('generates id with prefix', () => {
      const id = utils.mathGenerateId('test_');
      expect(id.startsWith('test_')).toBe(true);
    });

    it('generates unique ids', () => {
      expect(utils.mathGenerateId()).not.toBe(utils.mathGenerateId());
    });
  });

  describe('mathFormatDate', () => {
    it('formats date default', () => {
      expect(utils.mathFormatDate(new Date(2024, 0, 1))).toBe('2024-01-01');
    });

    it('formats date custom', () => {
      expect(utils.mathFormatDate(new Date(2024, 11, 31), 'DD/MM')).toBe('31/12');
    });
  });

  describe('mathParseQuery', () => {
    it('parses query', () => {
      expect(utils.mathParseQuery('?a=1&b=2')).toEqual({ a: '1', b: '2' });
    });

    it('decodes uri', () => {
      expect(utils.mathParseQuery('?q=hello%20world')).toEqual({ q: 'hello world' });
    });
  });

  describe('mathBuildQuery', () => {
    it('builds query', () => {
      expect(utils.mathBuildQuery({ a: '1' })).toBe('a=1');
    });

    it('skips nulls', () => {
      expect(utils.mathBuildQuery({ a: '1', b: null })).toBe('a=1');
    });
  });

  describe('mathGroupBy', () => {
    it('groups by key', () => {
      const arr = [{ k: 'a' }, { k: 'b' }, { k: 'a' }];
      const result = utils.mathGroupBy(arr, 'k');
      expect(result['a']).toHaveLength(2);
      expect(result['b']).toHaveLength(1);
    });
  });

  describe('mathChunk', () => {
    it('chunks array', () => {
      expect(utils.mathChunk([1, 2, 3, 4], 2)).toEqual([[1, 2], [3, 4]]);
    });
  });

  describe('mathFlatten', () => {
    it('flattens', () => {
      expect(utils.mathFlatten([[1], [2, 3]])).toEqual([1, 2, 3]);
    });
  });

  describe('mathGetNested', () => {
    it('gets nested', () => {
      expect(utils.mathGetNested({ a: { b: 1 } }, 'a.b')).toBe(1);
    });

    it('returns default', () => {
      expect(utils.mathGetNested({}, 'a.b', 'def')).toBe('def');
    });
  });

  describe('mathSetNested', () => {
    it('sets nested', () => {
      const obj: any = {};
      utils.mathSetNested(obj, 'a.b', 5);
      expect(obj['a']['b']).toBe(5);
    });
  });
});
