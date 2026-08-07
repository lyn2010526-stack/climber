import { describe, it, expect, vi } from 'vitest';
import * as utils from '../markdownUtils';

describe('markdownUtils', () => {
  describe('markdownDebounce', () => {
    it('debounces function calls', () => {
      vi.useFakeTimers();
      const fn = vi.fn();
      const debounced = utils.markdownDebounce(fn, 100);
      debounced();
      debounced();
      vi.advanceTimersByTime(100);
      expect(fn).toHaveBeenCalledTimes(1);
      vi.useRealTimers();
    });

    it('passes arguments correctly', () => {
      vi.useFakeTimers();
      const fn = vi.fn();
      const debounced = utils.markdownDebounce(fn, 50);
      debounced('a', 'b');
      vi.advanceTimersByTime(50);
      expect(fn).toHaveBeenCalledWith('a', 'b');
      vi.useRealTimers();
    });
  });

  describe('markdownThrottle', () => {
    it('throttles function calls', () => {
      vi.useFakeTimers();
      const fn = vi.fn();
      const throttled = utils.markdownThrottle(fn, 100);
      throttled();
      throttled();
      expect(fn).toHaveBeenCalledTimes(1);
      vi.advanceTimersByTime(100);
      throttled();
      expect(fn).toHaveBeenCalledTimes(2);
      vi.useRealTimers();
    });
  });

  describe('markdownDeepClone', () => {
    it('clones primitives', () => {
      expect(utils.markdownDeepClone(5)).toBe(5);
      expect(utils.markdownDeepClone('abc')).toBe('abc');
      expect(utils.markdownDeepClone(null)).toBe(null);
    });

    it('deep clones nested objects', () => {
      const obj = { a: { b: [1, 2] } };
      const cloned = utils.markdownDeepClone(obj);
      expect(cloned).toEqual(obj);
      expect(cloned).not.toBe(obj);
      expect(cloned['a']['b']).not.toBe(obj['a']['b']);
    });
  });

  describe('markdownGenerateId', () => {
    it('generates id with prefix', () => {
      const id = utils.markdownGenerateId('test_');
      expect(id.startsWith('test_')).toBe(true);
    });

    it('generates unique ids', () => {
      expect(utils.markdownGenerateId()).not.toBe(utils.markdownGenerateId());
    });
  });

  describe('markdownFormatDate', () => {
    it('formats date default', () => {
      expect(utils.markdownFormatDate(new Date(2024, 0, 1))).toBe('2024-01-01');
    });

    it('formats date custom', () => {
      expect(utils.markdownFormatDate(new Date(2024, 11, 31), 'DD/MM')).toBe('31/12');
    });
  });

  describe('markdownParseQuery', () => {
    it('parses query', () => {
      expect(utils.markdownParseQuery('?a=1&b=2')).toEqual({ a: '1', b: '2' });
    });

    it('decodes uri', () => {
      expect(utils.markdownParseQuery('?q=hello%20world')).toEqual({ q: 'hello world' });
    });
  });

  describe('markdownBuildQuery', () => {
    it('builds query', () => {
      expect(utils.markdownBuildQuery({ a: '1' })).toBe('a=1');
    });

    it('skips nulls', () => {
      expect(utils.markdownBuildQuery({ a: '1', b: null })).toBe('a=1');
    });
  });

  describe('markdownGroupBy', () => {
    it('groups by key', () => {
      const arr = [{ k: 'a' }, { k: 'b' }, { k: 'a' }];
      const result = utils.markdownGroupBy(arr, 'k');
      expect(result['a']).toHaveLength(2);
      expect(result['b']).toHaveLength(1);
    });
  });

  describe('markdownChunk', () => {
    it('chunks array', () => {
      expect(utils.markdownChunk([1, 2, 3, 4], 2)).toEqual([[1, 2], [3, 4]]);
    });
  });

  describe('markdownFlatten', () => {
    it('flattens', () => {
      expect(utils.markdownFlatten([[1], [2, 3]])).toEqual([1, 2, 3]);
    });
  });

  describe('markdownGetNested', () => {
    it('gets nested', () => {
      expect(utils.markdownGetNested({ a: { b: 1 } }, 'a.b')).toBe(1);
    });

    it('returns default', () => {
      expect(utils.markdownGetNested({}, 'a.b', 'def')).toBe('def');
    });
  });

  describe('markdownSetNested', () => {
    it('sets nested', () => {
      const obj: any = {};
      utils.markdownSetNested(obj, 'a.b', 5);
      expect(obj['a']['b']).toBe(5);
    });
  });
});
