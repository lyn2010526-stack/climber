import { describe, it, expect, vi } from 'vitest';
import {
  objectDebounce,
  objectThrottle,
  objectDeepClone,
  objectGenerateId,
  objectFormatDate,
  objectParseQuery,
  objectBuildQuery,
  objectGroupBy,
  objectChunk,
  objectFlatten,
  objectGetNested,
  objectSetNested,
  pick,
  omit,
  merge,
  isEmpty,
  deepEqual,
  flattenKeys,
} from '../objectUtils';

describe('objectUtils', () => {
  describe('objectDebounce', () => {
    it('debounces function calls', () => {
      vi.useFakeTimers();
      const fn = vi.fn();
      const debounced = objectDebounce(fn, 100);
      debounced();
      debounced();
      vi.advanceTimersByTime(100);
      expect(fn).toHaveBeenCalledTimes(1);
      vi.useRealTimers();
    });
  });

  describe('objectThrottle', () => {
    it('throttles function calls', () => {
      vi.useFakeTimers();
      const fn = vi.fn();
      const throttled = objectThrottle(fn, 100);
      throttled();
      throttled();
      expect(fn).toHaveBeenCalledTimes(1);
      vi.useRealTimers();
    });
  });

  describe('objectDeepClone', () => {
    it('clones objects deeply', () => {
      const obj = { a: 1, b: { c: 2 } };
      const cloned = objectDeepClone(obj);
      expect(cloned).toEqual(obj);
      expect(cloned).not.toBe(obj);
    });
  });

  describe('objectGenerateId', () => {
    it('generates ID with prefix', () => {
      expect(objectGenerateId('obj_').startsWith('obj_')).toBe(true);
    });
  });

  describe('objectFormatDate', () => {
    it('formats date correctly', () => {
      expect(objectFormatDate(new Date(2024, 0, 15))).toBe('2024-01-15');
    });
  });

  describe('objectParseQuery', () => {
    it('parses query string', () => {
      expect(objectParseQuery('?a=1')).toEqual({ a: '1' });
    });
  });

  describe('objectBuildQuery', () => {
    it('builds query string', () => {
      expect(objectBuildQuery({ a: '1' })).toBe('a=1');
    });
  });

  describe('objectGroupBy', () => {
    it('groups array by key', () => {
      const arr = [{ t: 'a' }, { t: 'b' }];
      expect(objectGroupBy(arr, 't')).toEqual({ a: [{ t: 'a' }], b: [{ t: 'b' }] });
    });
  });

  describe('objectChunk', () => {
    it('chunks array', () => {
      expect(objectChunk([1, 2, 3], 2)).toEqual([[1, 2], [3]]);
    });
  });

  describe('objectFlatten', () => {
    it('flattens nested arrays', () => {
      expect(objectFlatten([[1], [2, 3]])).toEqual([1, 2, 3]);
    });
  });

  describe('objectGetNested', () => {
    it('gets nested property', () => {
      expect(objectGetNested({ a: { b: 1 } }, 'a.b')).toBe(1);
    });
  });

  describe('objectSetNested', () => {
    it('sets nested property', () => {
      const obj: any = {};
      objectSetNested(obj, 'a.b', 1);
      expect(obj.a.b).toBe(1);
    });
  });

  describe('pick', () => {
    it('picks specified keys', () => {
      expect(pick({ a: 1, b: 2, c: 3 }, ['a', 'c'])).toEqual({ a: 1, c: 3 });
    });
  });

  describe('omit', () => {
    it('omits specified keys', () => {
      expect(omit({ a: 1, b: 2, c: 3 }, ['b'])).toEqual({ a: 1, c: 3 });
    });
  });

  describe('merge', () => {
    it('merges objects', () => {
      expect(merge({ a: 1 }, { b: 2 })).toEqual({ a: 1, b: 2 });
    });

    it('deep merges nested objects', () => {
      expect(merge({ a: { b: 1 } }, { a: { c: 2 } })).toEqual({ a: { b: 1, c: 2 } });
    });
  });

  describe('isEmpty', () => {
    it('returns true for empty object', () => {
      expect(isEmpty({})).toBe(true);
    });

    it('returns false for non-empty object', () => {
      expect(isEmpty({ a: 1 })).toBe(false);
    });
  });

  describe('deepEqual', () => {
    it('returns true for equal values', () => {
      expect(deepEqual(1, 1)).toBe(true);
      expect(deepEqual({ a: 1 }, { a: 1 })).toBe(true);
    });

    it('returns false for different values', () => {
      expect(deepEqual(1, 2)).toBe(false);
      expect(deepEqual({ a: 1 }, { a: 2 })).toBe(false);
    });
  });

  describe('flattenKeys', () => {
    it('flattens nested object keys', () => {
      expect(flattenKeys({ a: { b: 1 }, c: 2 })).toEqual({ 'a.b': 1, c: 2 });
    });
  });
});
