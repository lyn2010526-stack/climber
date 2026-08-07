import { describe, it, expect, vi } from 'vitest';
import * as utils from '../randomUtils';

describe('randomUtils', () => {
  describe('randomDebounce', () => {
    it('debounces function calls', () => {
      vi.useFakeTimers();
      const fn = vi.fn();
      const debounced = utils.randomDebounce(fn, 100);
      debounced();
      debounced();
      vi.advanceTimersByTime(100);
      expect(fn).toHaveBeenCalledTimes(1);
      vi.useRealTimers();
    });

    it('passes arguments correctly', () => {
      vi.useFakeTimers();
      const fn = vi.fn();
      const debounced = utils.randomDebounce(fn, 50);
      debounced('a', 'b');
      vi.advanceTimersByTime(50);
      expect(fn).toHaveBeenCalledWith('a', 'b');
      vi.useRealTimers();
    });
  });

  describe('randomThrottle', () => {
    it('throttles function calls', () => {
      vi.useFakeTimers();
      const fn = vi.fn();
      const throttled = utils.randomThrottle(fn, 100);
      throttled();
      throttled();
      expect(fn).toHaveBeenCalledTimes(1);
      vi.advanceTimersByTime(100);
      throttled();
      expect(fn).toHaveBeenCalledTimes(2);
      vi.useRealTimers();
    });
  });

  describe('randomDeepClone', () => {
    it('clones primitives', () => {
      expect(utils.randomDeepClone(5)).toBe(5);
      expect(utils.randomDeepClone('abc')).toBe('abc');
      expect(utils.randomDeepClone(null)).toBe(null);
    });

    it('deep clones nested objects', () => {
      const obj = { a: { b: [1, 2] } };
      const cloned = utils.randomDeepClone(obj);
      expect(cloned).toEqual(obj);
      expect(cloned).not.toBe(obj);
      expect(cloned['a']['b']).not.toBe(obj['a']['b']);
    });
  });

  describe('randomGenerateId', () => {
    it('generates id with prefix', () => {
      const id = utils.randomGenerateId('test_');
      expect(id.startsWith('test_')).toBe(true);
    });

    it('generates unique ids', () => {
      expect(utils.randomGenerateId()).not.toBe(utils.randomGenerateId());
    });
  });

  describe('randomFormatDate', () => {
    it('formats date default', () => {
      expect(utils.randomFormatDate(new Date(2024, 0, 1))).toBe('2024-01-01');
    });

    it('formats date custom', () => {
      expect(utils.randomFormatDate(new Date(2024, 11, 31), 'DD/MM')).toBe('31/12');
    });
  });

  describe('randomParseQuery', () => {
    it('parses query', () => {
      expect(utils.randomParseQuery('?a=1&b=2')).toEqual({ a: '1', b: '2' });
    });

    it('decodes uri', () => {
      expect(utils.randomParseQuery('?q=hello%20world')).toEqual({ q: 'hello world' });
    });
  });

  describe('randomBuildQuery', () => {
    it('builds query', () => {
      expect(utils.randomBuildQuery({ a: '1' })).toBe('a=1');
    });

    it('skips nulls', () => {
      expect(utils.randomBuildQuery({ a: '1', b: null })).toBe('a=1');
    });
  });

  describe('randomGroupBy', () => {
    it('groups by key', () => {
      const arr = [{ k: 'a' }, { k: 'b' }, { k: 'a' }];
      const result = utils.randomGroupBy(arr, 'k');
      expect(result['a']).toHaveLength(2);
      expect(result['b']).toHaveLength(1);
    });
  });

  describe('randomChunk', () => {
    it('chunks array', () => {
      expect(utils.randomChunk([1, 2, 3, 4], 2)).toEqual([[1, 2], [3, 4]]);
    });
  });

  describe('randomFlatten', () => {
    it('flattens', () => {
      expect(utils.randomFlatten([[1], [2, 3]])).toEqual([1, 2, 3]);
    });
  });

  describe('randomGetNested', () => {
    it('gets nested', () => {
      expect(utils.randomGetNested({ a: { b: 1 } }, 'a.b')).toBe(1);
    });

    it('returns default', () => {
      expect(utils.randomGetNested({}, 'a.b', 'def')).toBe('def');
    });
  });

  describe('randomSetNested', () => {
    it('sets nested', () => {
      const obj: any = {};
      utils.randomSetNested(obj, 'a.b', 5);
      expect(obj['a']['b']).toBe(5);
    });
  });
});
