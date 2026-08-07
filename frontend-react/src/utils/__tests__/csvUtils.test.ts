import { describe, it, expect, vi } from 'vitest';
import * as utils from '../csvUtils';

describe('csvUtils', () => {
  describe('csvDebounce', () => {
    it('debounces function calls', () => {
      vi.useFakeTimers();
      const fn = vi.fn();
      const debounced = utils.csvDebounce(fn, 100);
      debounced();
      debounced();
      vi.advanceTimersByTime(100);
      expect(fn).toHaveBeenCalledTimes(1);
      vi.useRealTimers();
    });

    it('passes arguments correctly', () => {
      vi.useFakeTimers();
      const fn = vi.fn();
      const debounced = utils.csvDebounce(fn, 50);
      debounced('a', 'b');
      vi.advanceTimersByTime(50);
      expect(fn).toHaveBeenCalledWith('a', 'b');
      vi.useRealTimers();
    });
  });

  describe('csvThrottle', () => {
    it('throttles function calls', () => {
      vi.useFakeTimers();
      const fn = vi.fn();
      const throttled = utils.csvThrottle(fn, 100);
      throttled();
      throttled();
      expect(fn).toHaveBeenCalledTimes(1);
      vi.advanceTimersByTime(100);
      throttled();
      expect(fn).toHaveBeenCalledTimes(2);
      vi.useRealTimers();
    });
  });

  describe('csvDeepClone', () => {
    it('clones primitives', () => {
      expect(utils.csvDeepClone(5)).toBe(5);
      expect(utils.csvDeepClone('abc')).toBe('abc');
      expect(utils.csvDeepClone(null)).toBe(null);
    });

    it('deep clones nested objects', () => {
      const obj = { a: { b: [1, 2] } };
      const cloned = utils.csvDeepClone(obj);
      expect(cloned).toEqual(obj);
      expect(cloned).not.toBe(obj);
      expect(cloned['a']['b']).not.toBe(obj['a']['b']);
    });
  });

  describe('csvGenerateId', () => {
    it('generates id with prefix', () => {
      const id = utils.csvGenerateId('test_');
      expect(id.startsWith('test_')).toBe(true);
    });

    it('generates unique ids', () => {
      expect(utils.csvGenerateId()).not.toBe(utils.csvGenerateId());
    });
  });

  describe('csvFormatDate', () => {
    it('formats date default', () => {
      expect(utils.csvFormatDate(new Date(2024, 0, 1))).toBe('2024-01-01');
    });

    it('formats date custom', () => {
      expect(utils.csvFormatDate(new Date(2024, 11, 31), 'DD/MM')).toBe('31/12');
    });
  });

  describe('csvParseQuery', () => {
    it('parses query', () => {
      expect(utils.csvParseQuery('?a=1&b=2')).toEqual({ a: '1', b: '2' });
    });

    it('decodes uri', () => {
      expect(utils.csvParseQuery('?q=hello%20world')).toEqual({ q: 'hello world' });
    });
  });

  describe('csvBuildQuery', () => {
    it('builds query', () => {
      expect(utils.csvBuildQuery({ a: '1' })).toBe('a=1');
    });

    it('skips nulls', () => {
      expect(utils.csvBuildQuery({ a: '1', b: null })).toBe('a=1');
    });
  });

  describe('csvGroupBy', () => {
    it('groups by key', () => {
      const arr = [{ k: 'a' }, { k: 'b' }, { k: 'a' }];
      const result = utils.csvGroupBy(arr, 'k');
      expect(result['a']).toHaveLength(2);
      expect(result['b']).toHaveLength(1);
    });
  });

  describe('csvChunk', () => {
    it('chunks array', () => {
      expect(utils.csvChunk([1, 2, 3, 4], 2)).toEqual([[1, 2], [3, 4]]);
    });
  });

  describe('csvFlatten', () => {
    it('flattens', () => {
      expect(utils.csvFlatten([[1], [2, 3]])).toEqual([1, 2, 3]);
    });
  });

  describe('csvGetNested', () => {
    it('gets nested', () => {
      expect(utils.csvGetNested({ a: { b: 1 } }, 'a.b')).toBe(1);
    });

    it('returns default', () => {
      expect(utils.csvGetNested({}, 'a.b', 'def')).toBe('def');
    });
  });

  describe('csvSetNested', () => {
    it('sets nested', () => {
      const obj: any = {};
      utils.csvSetNested(obj, 'a.b', 5);
      expect(obj['a']['b']).toBe(5);
    });
  });
});
