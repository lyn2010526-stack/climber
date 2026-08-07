import { describe, it, expect, vi } from 'vitest';
import {
  numberDebounce,
  numberThrottle,
  numberDeepClone,
  numberGenerateId,
  numberFormatDate,
  numberParseQuery,
  numberBuildQuery,
  numberGroupBy,
  numberChunk,
  numberFlatten,
  numberGetNested,
  numberSetNested,
  clamp,
  round,
  randomInt,
  formatNumber,
  parseNumber,
  sum,
  average,
  percentage,
} from '../numberUtils';

describe('numberUtils', () => {
  describe('numberDebounce', () => {
    it('debounces function calls', () => {
      vi.useFakeTimers();
      const fn = vi.fn();
      const debounced = numberDebounce(fn, 100);
      debounced();
      debounced();
      vi.advanceTimersByTime(100);
      expect(fn).toHaveBeenCalledTimes(1);
      vi.useRealTimers();
    });
  });

  describe('numberThrottle', () => {
    it('throttles function calls', () => {
      vi.useFakeTimers();
      const fn = vi.fn();
      const throttled = numberThrottle(fn, 100);
      throttled();
      throttled();
      expect(fn).toHaveBeenCalledTimes(1);
      vi.advanceTimersByTime(100);
      throttled();
      expect(fn).toHaveBeenCalledTimes(2);
      vi.useRealTimers();
    });
  });

  describe('numberDeepClone', () => {
    it('clones objects deeply', () => {
      const obj = { a: 1, b: { c: 2 } };
      const cloned = numberDeepClone(obj);
      expect(cloned).toEqual(obj);
      expect(cloned).not.toBe(obj);
    });
  });

  describe('numberGenerateId', () => {
    it('generates ID with prefix', () => {
      const id = numberGenerateId('num_');
      expect(id.startsWith('num_')).toBe(true);
    });
  });

  describe('numberFormatDate', () => {
    it('formats date correctly', () => {
      const date = new Date(2024, 0, 15);
      expect(numberFormatDate(date)).toBe('2024-01-15');
    });
  });

  describe('numberParseQuery', () => {
    it('parses query string', () => {
      expect(numberParseQuery('?a=1&b=2')).toEqual({ a: '1', b: '2' });
    });
  });

  describe('numberBuildQuery', () => {
    it('builds query string', () => {
      const result = numberBuildQuery({ a: '1', b: '2' });
      expect(result).toContain('a=1');
      expect(result).toContain('b=2');
    });

    it('skips null values', () => {
      expect(numberBuildQuery({ a: '1', b: null })).toBe('a=1');
    });
  });

  describe('numberGroupBy', () => {
    it('groups array by key', () => {
      const arr = [{ t: 'a' }, { t: 'b' }, { t: 'a' }];
      expect(numberGroupBy(arr, 't')).toEqual({
        a: [{ t: 'a' }, { t: 'a' }],
        b: [{ t: 'b' }],
      });
    });
  });

  describe('numberChunk', () => {
    it('chunks array', () => {
      expect(numberChunk([1, 2, 3, 4, 5], 2)).toEqual([[1, 2], [3, 4], [5]]);
    });
  });

  describe('numberFlatten', () => {
    it('flattens nested arrays', () => {
      expect(numberFlatten([[1, 2], [3, 4]])).toEqual([1, 2, 3, 4]);
    });
  });

  describe('numberGetNested', () => {
    it('gets nested property', () => {
      expect(numberGetNested({ a: { b: 1 } }, 'a.b')).toBe(1);
    });

    it('returns default for missing path', () => {
      expect(numberGetNested({}, 'a.b', 'default')).toBe('default');
    });
  });

  describe('numberSetNested', () => {
    it('sets nested property', () => {
      const obj: any = {};
      numberSetNested(obj, 'a.b', 1);
      expect(obj.a.b).toBe(1);
    });
  });

  describe('clamp', () => {
    it('clamps value between min and max', () => {
      expect(clamp(5, 0, 10)).toBe(5);
      expect(clamp(-5, 0, 10)).toBe(0);
      expect(clamp(15, 0, 10)).toBe(10);
    });
  });

  describe('round', () => {
    it('rounds to specified decimals', () => {
      expect(round(3.14159, 2)).toBe(3.14);
      expect(round(3.14159, 0)).toBe(3);
    });
  });

  describe('randomInt', () => {
    it('generates random integer in range', () => {
      const val = randomInt(1, 10);
      expect(val).toBeGreaterThanOrEqual(1);
      expect(val).toBeLessThanOrEqual(10);
    });
  });

  describe('formatNumber', () => {
    it('formats number with locale', () => {
      const result = formatNumber(1234567);
      expect(result).toBeTruthy();
    });
  });

  describe('parseNumber', () => {
    it('parses valid number string', () => {
      expect(parseNumber('42')).toBe(42);
    });

    it('returns default for invalid string', () => {
      expect(parseNumber('invalid', 0)).toBe(0);
    });
  });

  describe('sum', () => {
    it('sums array of numbers', () => {
      expect(sum([1, 2, 3, 4, 5])).toBe(15);
    });

    it('returns 0 for empty array', () => {
      expect(sum([])).toBe(0);
    });
  });

  describe('average', () => {
    it('calculates average', () => {
      expect(average([2, 4, 6])).toBe(4);
    });

    it('returns 0 for empty array', () => {
      expect(average([])).toBe(0);
    });
  });

  describe('percentage', () => {
    it('calculates percentage', () => {
      expect(percentage(25, 100)).toBe(25);
    });

    it('returns 0 when total is 0', () => {
      expect(percentage(10, 0)).toBe(0);
    });
  });
});
