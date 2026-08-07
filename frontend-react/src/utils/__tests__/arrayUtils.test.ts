import { describe, it, expect, vi } from 'vitest';
import {
  arrayDebounce,
  arrayThrottle,
  arrayDeepClone,
  arrayGenerateId,
  arrayFormatDate,
  arrayParseQuery,
  arrayBuildQuery,
  arrayGroupBy,
  arrayChunk,
  arrayFlatten,
  arrayGetNested,
  arraySetNested,
} from '../arrayUtils';

describe('arrayUtils', () => {
  describe('arrayDebounce', () => {
    it('debounces function calls', () => {
      vi.useFakeTimers();
      const fn = vi.fn();
      const debounced = arrayDebounce(fn, 100);

      debounced();
      debounced();
      debounced();

      expect(fn).not.toHaveBeenCalled();

      vi.advanceTimersByTime(100);
      expect(fn).toHaveBeenCalledTimes(1);

      vi.useRealTimers();
    });

    it('passes arguments to debounced function', () => {
      vi.useFakeTimers();
      const fn = vi.fn();
      const debounced = arrayDebounce(fn, 50);

      debounced('a', 'b');
      vi.advanceTimersByTime(50);

      expect(fn).toHaveBeenCalledWith('a', 'b');
      vi.useRealTimers();
    });
  });

  describe('arrayThrottle', () => {
    it('throttles function calls', () => {
      vi.useFakeTimers();
      const fn = vi.fn();
      const throttled = arrayThrottle(fn, 100);

      throttled();
      throttled();
      throttled();

      expect(fn).toHaveBeenCalledTimes(1);

      vi.advanceTimersByTime(100);
      throttled();
      expect(fn).toHaveBeenCalledTimes(2);

      vi.useRealTimers();
    });
  });

  describe('arrayDeepClone', () => {
    it('clones primitive values', () => {
      expect(arrayDeepClone(42)).toBe(42);
      expect(arrayDeepClone('hello')).toBe('hello');
      expect(arrayDeepClone(null)).toBe(null);
    });

    it('clones arrays', () => {
      const arr = [1, 2, [3, 4]];
      const cloned = arrayDeepClone(arr);
      expect(cloned).toEqual(arr);
      expect(cloned).not.toBe(arr);
      expect(cloned[2]).not.toBe(arr[2]);
    });

    it('clones nested objects', () => {
      const obj = { a: 1, b: { c: 2, d: [3, 4] } };
      const cloned = arrayDeepClone(obj);
      expect(cloned).toEqual(obj);
      expect(cloned).not.toBe(obj);
      expect(cloned.b).not.toBe(obj.b);
    });
  });

  describe('arrayGenerateId', () => {
    it('generates an ID without prefix', () => {
      const id = arrayGenerateId();
      expect(id).toBeTruthy();
      expect(typeof id).toBe('string');
    });

    it('generates an ID with prefix', () => {
      const id = arrayGenerateId('prefix_');
      expect(id.startsWith('prefix_')).toBe(true);
    });

    it('generates unique IDs', () => {
      const id1 = arrayGenerateId();
      const id2 = arrayGenerateId();
      expect(id1).not.toBe(id2);
    });
  });

  describe('arrayFormatDate', () => {
    it('formats date with default format', () => {
      const date = new Date(2024, 0, 15);
      expect(arrayFormatDate(date)).toBe('2024-01-15');
    });

    it('formats date with custom format', () => {
      const date = new Date(2024, 11, 25);
      expect(arrayFormatDate(date, 'DD/MM/YYYY')).toBe('25/12/2024');
    });
  });

  describe('arrayParseQuery', () => {
    it('parses simple query string', () => {
      const result = arrayParseQuery('?foo=bar&baz=qux');
      expect(result).toEqual({ foo: 'bar', baz: 'qux' });
    });

    it('decodes URI components', () => {
      const result = arrayParseQuery('?name=hello%20world');
      expect(result).toEqual({ name: 'hello world' });
    });

    it('handles empty query string', () => {
      const result = arrayParseQuery('?');
      expect(result).toEqual({});
    });
  });

  describe('arrayBuildQuery', () => {
    it('builds query string from object', () => {
      const result = arrayBuildQuery({ foo: 'bar', baz: 'qux' });
      expect(result).toContain('foo=bar');
      expect(result).toContain('baz=qux');
    });

    it('skips null and undefined values', () => {
      const result = arrayBuildQuery({ a: 'b', c: null, d: undefined });
      expect(result).toBe('a=b');
    });

    it('encodes special characters', () => {
      const result = arrayBuildQuery({ q: 'hello world' });
      expect(result).toBe('q=hello%20world');
    });
  });

  describe('arrayGroupBy', () => {
    it('groups array by key', () => {
      const arr = [
        { type: 'a', value: 1 },
        { type: 'b', value: 2 },
        { type: 'a', value: 3 },
      ];
      const result = arrayGroupBy(arr, 'type');
      expect(result).toEqual({
        a: [{ type: 'a', value: 1 }, { type: 'a', value: 3 }],
        b: [{ type: 'b', value: 2 }],
      });
    });
  });

  describe('arrayChunk', () => {
    it('chunks array into smaller arrays', () => {
      const arr = [1, 2, 3, 4, 5];
      const result = arrayChunk(arr, 2);
      expect(result).toEqual([[1, 2], [3, 4], [5]]);
    });

    it('handles empty array', () => {
      const result = arrayChunk([], 3);
      expect(result).toEqual([]);
    });
  });

  describe('arrayFlatten', () => {
    it('flattens nested arrays', () => {
      const result = arrayFlatten([[1, 2], [3, 4], [5]]);
      expect(result).toEqual([1, 2, 3, 4, 5]);
    });

    it('handles already flat array', () => {
      const result = arrayFlatten([1, 2, 3] as any);
      expect(result).toEqual([1, 2, 3]);
    });
  });

  describe('arrayGetNested', () => {
    it('gets nested property value', () => {
      const obj = { a: { b: { c: 42 } } };
      expect(arrayGetNested(obj, 'a.b.c')).toBe(42);
    });

    it('returns defaultValue for missing path', () => {
      const obj = { a: { b: 1 } };
      expect(arrayGetNested(obj, 'a.x.c', 'default')).toBe('default');
    });

    it('returns defaultValue for null intermediate', () => {
      const obj = { a: null };
      expect(arrayGetNested(obj, 'a.b', 'default')).toBe('default');
    });
  });

  describe('arraySetNested', () => {
    it('sets nested property value', () => {
      const obj: any = { a: { b: {} } };
      arraySetNested(obj, 'a.b.c', 42);
      expect(obj.a.b.c).toBe(42);
    });

    it('creates intermediate objects', () => {
      const obj: any = {};
      arraySetNested(obj, 'a.b.c', 42);
      expect(obj.a.b.c).toBe(42);
    });
  });
});
