import { describe, it, expect, vi } from 'vitest';
import * as utils from '../jsonUtils';

describe('jsonUtils', () => {
  describe('jsonDebounce', () => {
    it('debounces function calls', () => {
      vi.useFakeTimers();
      const fn = vi.fn();
      const debounced = utils.jsonDebounce(fn, 100);
      debounced();
      debounced();
      vi.advanceTimersByTime(100);
      expect(fn).toHaveBeenCalledTimes(1);
      vi.useRealTimers();
    });

    it('passes arguments correctly', () => {
      vi.useFakeTimers();
      const fn = vi.fn();
      const debounced = utils.jsonDebounce(fn, 50);
      debounced('a', 'b');
      vi.advanceTimersByTime(50);
      expect(fn).toHaveBeenCalledWith('a', 'b');
      vi.useRealTimers();
    });
  });

  describe('jsonThrottle', () => {
    it('throttles function calls', () => {
      vi.useFakeTimers();
      const fn = vi.fn();
      const throttled = utils.jsonThrottle(fn, 100);
      throttled();
      throttled();
      expect(fn).toHaveBeenCalledTimes(1);
      vi.advanceTimersByTime(100);
      throttled();
      expect(fn).toHaveBeenCalledTimes(2);
      vi.useRealTimers();
    });
  });

  describe('jsonDeepClone', () => {
    it('clones primitives', () => {
      expect(utils.jsonDeepClone(5)).toBe(5);
      expect(utils.jsonDeepClone('abc')).toBe('abc');
      expect(utils.jsonDeepClone(null)).toBe(null);
    });

    it('deep clones nested objects', () => {
      const obj = { a: { b: [1, 2] } };
      const cloned = utils.jsonDeepClone(obj);
      expect(cloned).toEqual(obj);
      expect(cloned).not.toBe(obj);
      expect(cloned['a']['b']).not.toBe(obj['a']['b']);
    });
  });

  describe('jsonGenerateId', () => {
    it('generates id with prefix', () => {
      const id = utils.jsonGenerateId('test_');
      expect(id.startsWith('test_')).toBe(true);
    });

    it('generates unique ids', () => {
      expect(utils.jsonGenerateId()).not.toBe(utils.jsonGenerateId());
    });
  });

  describe('jsonFormatDate', () => {
    it('formats date default', () => {
      expect(utils.jsonFormatDate(new Date(2024, 0, 1))).toBe('2024-01-01');
    });

    it('formats date custom', () => {
      expect(utils.jsonFormatDate(new Date(2024, 11, 31), 'DD/MM')).toBe('31/12');
    });
  });

  describe('jsonParseQuery', () => {
    it('parses query', () => {
      expect(utils.jsonParseQuery('?a=1&b=2')).toEqual({ a: '1', b: '2' });
    });

    it('decodes uri', () => {
      expect(utils.jsonParseQuery('?q=hello%20world')).toEqual({ q: 'hello world' });
    });
  });

  describe('jsonBuildQuery', () => {
    it('builds query', () => {
      expect(utils.jsonBuildQuery({ a: '1' })).toBe('a=1');
    });

    it('skips nulls', () => {
      expect(utils.jsonBuildQuery({ a: '1', b: null })).toBe('a=1');
    });
  });

  describe('jsonGroupBy', () => {
    it('groups by key', () => {
      const arr = [{ k: 'a' }, { k: 'b' }, { k: 'a' }];
      const result = utils.jsonGroupBy(arr, 'k');
      expect(result['a']).toHaveLength(2);
      expect(result['b']).toHaveLength(1);
    });
  });

  describe('jsonChunk', () => {
    it('chunks array', () => {
      expect(utils.jsonChunk([1, 2, 3, 4], 2)).toEqual([[1, 2], [3, 4]]);
    });
  });

  describe('jsonFlatten', () => {
    it('flattens', () => {
      expect(utils.jsonFlatten([[1], [2, 3]])).toEqual([1, 2, 3]);
    });
  });

  describe('jsonGetNested', () => {
    it('gets nested', () => {
      expect(utils.jsonGetNested({ a: { b: 1 } }, 'a.b')).toBe(1);
    });

    it('returns default', () => {
      expect(utils.jsonGetNested({}, 'a.b', 'def')).toBe('def');
    });
  });

  describe('jsonSetNested', () => {
    it('sets nested', () => {
      const obj: any = {};
      utils.jsonSetNested(obj, 'a.b', 5);
      expect(obj['a']['b']).toBe(5);
    });
  });
});
