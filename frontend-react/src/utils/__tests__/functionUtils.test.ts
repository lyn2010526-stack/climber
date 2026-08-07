import { describe, it, expect, vi } from 'vitest';
import * as utils from '../functionUtils';

describe('functionUtils', () => {
  describe('functionDebounce', () => {
    it('debounces function calls', () => {
      vi.useFakeTimers();
      const fn = vi.fn();
      const debounced = utils.functionDebounce(fn, 100);
      debounced();
      debounced();
      vi.advanceTimersByTime(100);
      expect(fn).toHaveBeenCalledTimes(1);
      vi.useRealTimers();
    });

    it('passes arguments correctly', () => {
      vi.useFakeTimers();
      const fn = vi.fn();
      const debounced = utils.functionDebounce(fn, 50);
      debounced('a', 'b');
      vi.advanceTimersByTime(50);
      expect(fn).toHaveBeenCalledWith('a', 'b');
      vi.useRealTimers();
    });
  });

  describe('functionThrottle', () => {
    it('throttles function calls', () => {
      vi.useFakeTimers();
      const fn = vi.fn();
      const throttled = utils.functionThrottle(fn, 100);
      throttled();
      throttled();
      expect(fn).toHaveBeenCalledTimes(1);
      vi.advanceTimersByTime(100);
      throttled();
      expect(fn).toHaveBeenCalledTimes(2);
      vi.useRealTimers();
    });
  });

  describe('functionDeepClone', () => {
    it('clones primitives', () => {
      expect(utils.functionDeepClone(5)).toBe(5);
      expect(utils.functionDeepClone('abc')).toBe('abc');
      expect(utils.functionDeepClone(null)).toBe(null);
    });

    it('deep clones nested objects', () => {
      const obj = { a: { b: [1, 2] } };
      const cloned = utils.functionDeepClone(obj);
      expect(cloned).toEqual(obj);
      expect(cloned).not.toBe(obj);
      expect(cloned['a']['b']).not.toBe(obj['a']['b']);
    });
  });

  describe('functionGenerateId', () => {
    it('generates id with prefix', () => {
      const id = utils.functionGenerateId('test_');
      expect(id.startsWith('test_')).toBe(true);
    });

    it('generates unique ids', () => {
      expect(utils.functionGenerateId()).not.toBe(utils.functionGenerateId());
    });
  });

  describe('functionFormatDate', () => {
    it('formats date default', () => {
      expect(utils.functionFormatDate(new Date(2024, 0, 1))).toBe('2024-01-01');
    });

    it('formats date custom', () => {
      expect(utils.functionFormatDate(new Date(2024, 11, 31), 'DD/MM')).toBe('31/12');
    });
  });

  describe('functionParseQuery', () => {
    it('parses query', () => {
      expect(utils.functionParseQuery('?a=1&b=2')).toEqual({ a: '1', b: '2' });
    });

    it('decodes uri', () => {
      expect(utils.functionParseQuery('?q=hello%20world')).toEqual({ q: 'hello world' });
    });
  });

  describe('functionBuildQuery', () => {
    it('builds query', () => {
      expect(utils.functionBuildQuery({ a: '1' })).toBe('a=1');
    });

    it('skips nulls', () => {
      expect(utils.functionBuildQuery({ a: '1', b: null })).toBe('a=1');
    });
  });

  describe('functionGroupBy', () => {
    it('groups by key', () => {
      const arr = [{ k: 'a' }, { k: 'b' }, { k: 'a' }];
      const result = utils.functionGroupBy(arr, 'k');
      expect(result['a']).toHaveLength(2);
      expect(result['b']).toHaveLength(1);
    });
  });

  describe('functionChunk', () => {
    it('chunks array', () => {
      expect(utils.functionChunk([1, 2, 3, 4], 2)).toEqual([[1, 2], [3, 4]]);
    });
  });

  describe('functionFlatten', () => {
    it('flattens', () => {
      expect(utils.functionFlatten([[1], [2, 3]])).toEqual([1, 2, 3]);
    });
  });

  describe('functionGetNested', () => {
    it('gets nested', () => {
      expect(utils.functionGetNested({ a: { b: 1 } }, 'a.b')).toBe(1);
    });

    it('returns default', () => {
      expect(utils.functionGetNested({}, 'a.b', 'def')).toBe('def');
    });
  });

  describe('functionSetNested', () => {
    it('sets nested', () => {
      const obj: any = {};
      utils.functionSetNested(obj, 'a.b', 5);
      expect(obj['a']['b']).toBe(5);
    });
  });
});
