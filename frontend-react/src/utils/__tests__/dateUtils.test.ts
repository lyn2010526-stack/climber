import { describe, it, expect, vi } from 'vitest';
import {
  dateDebounce,
  dateThrottle,
  dateDeepClone,
  dateGenerateId,
  dateFormatDate,
  dateParseQuery,
  dateBuildQuery,
  dateGroupBy,
  dateChunk,
  dateFlatten,
  dateGetNested,
  dateSetNested,
  formatDate,
  parseDate,
  addDays,
  startOfDay,
  endOfDay,
  isSameDay,
  daysBetween,
} from '../dateUtils';

describe('dateUtils', () => {
  describe('dateDebounce', () => {
    it('debounces function calls', () => {
      vi.useFakeTimers();
      const fn = vi.fn();
      const debounced = dateDebounce(fn, 100);

      debounced();
      debounced();
      debounced();

      expect(fn).not.toHaveBeenCalled();
      vi.advanceTimersByTime(100);
      expect(fn).toHaveBeenCalledTimes(1);
      vi.useRealTimers();
    });
  });

  describe('dateThrottle', () => {
    it('throttles function calls', () => {
      vi.useFakeTimers();
      const fn = vi.fn();
      const throttled = dateThrottle(fn, 100);

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

  describe('dateDeepClone', () => {
    it('clones primitive values', () => {
      expect(dateDeepClone(42)).toBe(42);
      expect(dateDeepClone('hello')).toBe('hello');
      expect(dateDeepClone(null)).toBeNull();
    });

    it('clones arrays', () => {
      const arr = [1, 2, [3, 4]];
      const cloned = dateDeepClone(arr);
      expect(cloned).toEqual(arr);
      expect(cloned).not.toBe(arr);
    });

    it('clones objects', () => {
      const obj = { a: 1, b: { c: 2 } };
      const cloned = dateDeepClone(obj);
      expect(cloned).toEqual(obj);
      expect(cloned).not.toBe(obj);
      expect(cloned.b).not.toBe(obj.b);
    });
  });

  describe('dateGenerateId', () => {
    it('generates unique ID without prefix', () => {
      const id = dateGenerateId();
      expect(id).toBeTruthy();
      expect(typeof id).toBe('string');
    });

    it('generates ID with prefix', () => {
      const id = dateGenerateId('prefix_');
      expect(id.startsWith('prefix_')).toBe(true);
    });
  });

  describe('dateFormatDate', () => {
    it('formats date with default format', () => {
      const date = new Date(2024, 0, 15);
      expect(dateFormatDate(date)).toBe('2024-01-15');
    });

    it('formats date with custom format', () => {
      const date = new Date(2024, 11, 25);
      expect(dateFormatDate(date, 'DD/MM/YYYY')).toBe('25/12/2024');
    });
  });

  describe('dateParseQuery', () => {
    it('parses query string', () => {
      const result = dateParseQuery('?foo=bar&baz=qux');
      expect(result).toEqual({ foo: 'bar', baz: 'qux' });
    });

    it('handles empty query', () => {
      expect(dateParseQuery('')).toEqual({});
    });

    it('decodes URI components', () => {
      const result = dateParseQuery('name=hello%20world');
      expect(result).toEqual({ name: 'hello world' });
    });
  });

  describe('dateBuildQuery', () => {
    it('builds query string from object', () => {
      const result = dateBuildQuery({ foo: 'bar', baz: 'qux' });
      expect(result).toContain('foo=bar');
      expect(result).toContain('baz=qux');
    });

    it('skips null/undefined values', () => {
      const result = dateBuildQuery({ a: '1', b: null, c: undefined });
      expect(result).toBe('a=1');
    });

    it('encodes URI components', () => {
      const result = dateBuildQuery({ name: 'hello world' });
      expect(result).toBe('name=hello%20world');
    });
  });

  describe('dateGroupBy', () => {
    it('groups array by key', () => {
      const arr = [
        { type: 'a', value: 1 },
        { type: 'b', value: 2 },
        { type: 'a', value: 3 },
      ];
      const result = dateGroupBy(arr, 'type');
      expect(result).toEqual({
        a: [{ type: 'a', value: 1 }, { type: 'a', value: 3 }],
        b: [{ type: 'b', value: 2 }],
      });
    });
  });

  describe('dateChunk', () => {
    it('chunks array into smaller arrays', () => {
      const arr = [1, 2, 3, 4, 5];
      expect(dateChunk(arr, 2)).toEqual([[1, 2], [3, 4], [5]]);
    });
  });

  describe('dateFlatten', () => {
    it('flattens nested arrays', () => {
      expect(dateFlatten([[1, 2], [3, 4]])).toEqual([1, 2, 3, 4]);
    });
  });

  describe('dateGetNested', () => {
    it('gets nested property', () => {
      const obj = { a: { b: { c: 42 } } };
      expect(dateGetNested(obj, 'a.b.c')).toBe(42);
    });

    it('returns default value for missing path', () => {
      const obj = { a: { b: 1 } };
      expect(dateGetNested(obj, 'a.c', 'default')).toBe('default');
    });
  });

  describe('dateSetNested', () => {
    it('sets nested property', () => {
      const obj: any = {};
      dateSetNested(obj, 'a.b.c', 42);
      expect(obj.a.b.c).toBe(42);
    });
  });

  describe('formatDate', () => {
    it('formats date correctly', () => {
      const date = new Date(2024, 5, 10);
      expect(formatDate(date)).toBe('2024-06-10');
    });
  });

  describe('parseDate', () => {
    it('parses valid date string', () => {
      const result = parseDate('2024-01-15');
      expect(result).toBeInstanceOf(Date);
    });

    it('returns null for invalid date', () => {
      expect(parseDate('invalid')).toBeNull();
    });
  });

  describe('addDays', () => {
    it('adds days to date', () => {
      const date = new Date(2024, 0, 1);
      const result = addDays(date, 5);
      expect(result.getDate()).toBe(6);
    });

    it('subtracts days with negative value', () => {
      const date = new Date(2024, 0, 10);
      const result = addDays(date, -5);
      expect(result.getDate()).toBe(5);
    });
  });

  describe('startOfDay', () => {
    it('sets time to 00:00:00', () => {
      const date = new Date(2024, 0, 15, 14, 30, 45);
      const result = startOfDay(date);
      expect(result.getHours()).toBe(0);
      expect(result.getMinutes()).toBe(0);
      expect(result.getSeconds()).toBe(0);
    });
  });

  describe('endOfDay', () => {
    it('sets time to 23:59:59', () => {
      const date = new Date(2024, 0, 15, 14, 30, 45);
      const result = endOfDay(date);
      expect(result.getHours()).toBe(23);
      expect(result.getMinutes()).toBe(59);
      expect(result.getSeconds()).toBe(59);
    });
  });

  describe('isSameDay', () => {
    it('returns true for same day', () => {
      const a = new Date(2024, 0, 15, 10, 0);
      const b = new Date(2024, 0, 15, 20, 0);
      expect(isSameDay(a, b)).toBe(true);
    });

    it('returns false for different days', () => {
      const a = new Date(2024, 0, 15);
      const b = new Date(2024, 0, 16);
      expect(isSameDay(a, b)).toBe(false);
    });
  });

  describe('daysBetween', () => {
    it('calculates days between dates', () => {
      const a = new Date(2024, 0, 1);
      const b = new Date(2024, 0, 10);
      expect(daysBetween(a, b)).toBe(9);
    });
  });
});
