import { describe, it, expect, vi } from 'vitest';
import {
  validationDebounce,
  validationThrottle,
  validationDeepClone,
  validationGenerateId,
  validationFormatDate,
  validationParseQuery,
  validationBuildQuery,
  validationGroupBy,
  validationChunk,
  validationFlatten,
  validationGetNested,
  validationSetNested,
  isEmail,
  isUrl,
  isPhone,
  isRequired,
  minLength,
  maxLength,
  isNumber,
  isJSON,
} from '../validationUtils';

describe('validationUtils', () => {
  describe('validationDebounce', () => {
    it('debounces function calls', () => {
      vi.useFakeTimers();
      const fn = vi.fn();
      const debounced = validationDebounce(fn, 100);

      debounced();
      debounced();
      vi.advanceTimersByTime(100);
      expect(fn).toHaveBeenCalledTimes(1);
      vi.useRealTimers();
    });

    it('passes arguments to debounced function', () => {
      vi.useFakeTimers();
      const fn = vi.fn();
      const debounced = validationDebounce(fn, 100);

      debounced('arg1', 'arg2');
      vi.advanceTimersByTime(100);
      expect(fn).toHaveBeenCalledWith('arg1', 'arg2');
      vi.useRealTimers();
    });
  });

  describe('validationThrottle', () => {
    it('throttles function calls', () => {
      vi.useFakeTimers();
      const fn = vi.fn();
      const throttled = validationThrottle(fn, 100);

      throttled();
      throttled();
      expect(fn).toHaveBeenCalledTimes(1);
      vi.advanceTimersByTime(100);
      throttled();
      expect(fn).toHaveBeenCalledTimes(2);
      vi.useRealTimers();
    });
  });

  describe('validationDeepClone', () => {
    it('clones objects deeply', () => {
      const obj = { a: 1, b: { c: 2 } };
      const cloned = validationDeepClone(obj);
      expect(cloned).toEqual(obj);
      expect(cloned).not.toBe(obj);
    });

    it('clones arrays', () => {
      const arr = [1, [2, 3]];
      const cloned = validationDeepClone(arr);
      expect(cloned).toEqual(arr);
      expect(cloned).not.toBe(arr);
    });

    it('returns null for null input', () => {
      expect(validationDeepClone(null)).toBeNull();
    });

    it('returns primitive values as-is', () => {
      expect(validationDeepClone(42)).toBe(42);
      expect(validationDeepClone('hello')).toBe('hello');
    });
  });

  describe('validationGenerateId', () => {
    it('generates ID with prefix', () => {
      const id = validationGenerateId('test_');
      expect(id.startsWith('test_')).toBe(true);
    });

    it('generates ID without prefix', () => {
      const id = validationGenerateId();
      expect(id.length).toBeGreaterThan(0);
    });

    it('generates unique IDs', () => {
      const id1 = validationGenerateId();
      const id2 = validationGenerateId();
      expect(id1).not.toBe(id2);
    });
  });

  describe('validationFormatDate', () => {
    it('formats date correctly', () => {
      const date = new Date(2024, 0, 15);
      expect(validationFormatDate(date)).toBe('2024-01-15');
    });

    it('formats date with custom format', () => {
      const date = new Date(2024, 0, 15);
      expect(validationFormatDate(date, 'DD/MM/YYYY')).toBe('15/01/2024');
    });
  });

  describe('validationParseQuery', () => {
    it('parses query string', () => {
      const result = validationParseQuery('?foo=bar&baz=qux');
      expect(result).toEqual({ foo: 'bar', baz: 'qux' });
    });

    it('handles empty query string', () => {
      const result = validationParseQuery('');
      expect(result).toEqual({});
    });

    it('decodes URL-encoded values', () => {
      const result = validationParseQuery('?name=hello%20world');
      expect(result).toEqual({ name: 'hello world' });
    });
  });

  describe('validationBuildQuery', () => {
    it('builds query string from object', () => {
      const result = validationBuildQuery({ foo: 'bar', baz: 'qux' });
      expect(result).toContain('foo=bar');
      expect(result).toContain('baz=qux');
    });

    it('skips undefined and null values', () => {
      const result = validationBuildQuery({ foo: 'bar', baz: null, qux: undefined });
      expect(result).toBe('foo=bar');
    });

    it('encodes special characters', () => {
      const result = validationBuildQuery({ name: 'hello world' });
      expect(result).toBe('name=hello%20world');
    });
  });

  describe('validationGroupBy', () => {
    it('groups array by key', () => {
      const array = [
        { type: 'a', value: 1 },
        { type: 'b', value: 2 },
        { type: 'a', value: 3 },
      ];
      const result = validationGroupBy(array, 'type');
      expect(result).toEqual({
        a: [{ type: 'a', value: 1 }, { type: 'a', value: 3 }],
        b: [{ type: 'b', value: 2 }],
      });
    });
  });

  describe('validationChunk', () => {
    it('chunks array into smaller arrays', () => {
      const array = [1, 2, 3, 4, 5];
      const result = validationChunk(array, 2);
      expect(result).toEqual([[1, 2], [3, 4], [5]]);
    });
  });

  describe('validationFlatten', () => {
    it('flattens nested arrays', () => {
      const array = [1, [2, 3], [4, [5, 6]]];
      const result = validationFlatten(array);
      expect(result).toEqual([1, 2, 3, 4, [5, 6]]);
    });
  });

  describe('validationGetNested', () => {
    it('gets nested property', () => {
      const obj = { a: { b: { c: 42 } } };
      expect(validationGetNested(obj, 'a.b.c')).toBe(42);
    });

    it('returns default value for missing path', () => {
      const obj = { a: { b: { c: 42 } } };
      expect(validationGetNested(obj, 'a.b.x', 'default')).toBe('default');
    });
  });

  describe('validationSetNested', () => {
    it('sets nested property', () => {
      const obj: any = {};
      validationSetNested(obj, 'a.b.c', 42);
      expect(obj.a.b.c).toBe(42);
    });
  });

  describe('isEmail', () => {
    it('validates correct email', () => {
      expect(isEmail('test@example.com')).toBe(true);
    });

    it('rejects incorrect email', () => {
      expect(isEmail('invalid')).toBe(false);
      expect(isEmail('test@')).toBe(false);
      expect(isEmail('@example.com')).toBe(false);
    });
  });

  describe('isUrl', () => {
    it('validates correct URL', () => {
      expect(isUrl('https://example.com')).toBe(true);
    });

    it('rejects incorrect URL', () => {
      expect(isUrl('invalid')).toBe(false);
    });
  });

  describe('isPhone', () => {
    it('validates Chinese mobile number', () => {
      expect(isPhone('13800138000')).toBe(true);
    });

    it('rejects invalid phone number', () => {
      expect(isPhone('12345678901')).toBe(false);
      expect(isPhone('1380013800')).toBe(false);
    });
  });

  describe('isRequired', () => {
    it('returns true for non-empty values', () => {
      expect(isRequired('hello')).toBe(true);
      expect(isRequired(42)).toBe(true);
    });

    it('returns false for empty values', () => {
      expect(isRequired(null)).toBe(false);
      expect(isRequired(undefined)).toBe(false);
      expect(isRequired('  ')).toBe(false);
    });
  });

  describe('minLength', () => {
    it('checks minimum length', () => {
      expect(minLength('hello', 3)).toBe(true);
      expect(minLength('hi', 3)).toBe(false);
    });
  });

  describe('maxLength', () => {
    it('checks maximum length', () => {
      expect(maxLength('hello', 10)).toBe(true);
      expect(maxLength('hello world', 5)).toBe(false);
    });
  });

  describe('isNumber', () => {
    it('checks if string is a valid number', () => {
      expect(isNumber('42')).toBe(true);
      expect(isNumber('3.14')).toBe(true);
      expect(isNumber('abc')).toBe(false);
      expect(isNumber('')).toBe(false);
    });
  });

  describe('isJSON', () => {
    it('checks if string is valid JSON', () => {
      expect(isJSON('{"key": "value"}')).toBe(true);
      expect(isJSON('invalid')).toBe(false);
    });
  });
});
