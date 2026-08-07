import { describe, it, expect, vi } from 'vitest';
import * as utils from '../textUtils';

describe('textUtils', () => {
  describe('textDebounce', () => {
    it('debounces function calls', () => {
      vi.useFakeTimers();
      const fn = vi.fn();
      const debounced = utils.textDebounce(fn, 100);
      debounced();
      debounced();
      vi.advanceTimersByTime(100);
      expect(fn).toHaveBeenCalledTimes(1);
      vi.useRealTimers();
    });

    it('passes arguments correctly', () => {
      vi.useFakeTimers();
      const fn = vi.fn();
      const debounced = utils.textDebounce(fn, 50);
      debounced('a', 'b');
      vi.advanceTimersByTime(50);
      expect(fn).toHaveBeenCalledWith('a', 'b');
      vi.useRealTimers();
    });
  });

  describe('textThrottle', () => {
    it('throttles function calls', () => {
      vi.useFakeTimers();
      const fn = vi.fn();
      const throttled = utils.textThrottle(fn, 100);
      throttled();
      throttled();
      expect(fn).toHaveBeenCalledTimes(1);
      vi.advanceTimersByTime(100);
      throttled();
      expect(fn).toHaveBeenCalledTimes(2);
      vi.useRealTimers();
    });
  });

  describe('textDeepClone', () => {
    it('clones primitives', () => {
      expect(utils.textDeepClone(5)).toBe(5);
      expect(utils.textDeepClone('abc')).toBe('abc');
      expect(utils.textDeepClone(null)).toBe(null);
    });

    it('deep clones nested objects', () => {
      const obj = { a: { b: [1, 2] } };
      const cloned = utils.textDeepClone(obj);
      expect(cloned).toEqual(obj);
      expect(cloned).not.toBe(obj);
      expect(cloned['a']['b']).not.toBe(obj['a']['b']);
    });
  });

  describe('textGenerateId', () => {
    it('generates id with prefix', () => {
      const id = utils.textGenerateId('test_');
      expect(id.startsWith('test_')).toBe(true);
    });

    it('generates unique ids', () => {
      expect(utils.textGenerateId()).not.toBe(utils.textGenerateId());
    });
  });

  describe('textFormatDate', () => {
    it('formats date default', () => {
      expect(utils.textFormatDate(new Date(2024, 0, 1))).toBe('2024-01-01');
    });

    it('formats date custom', () => {
      expect(utils.textFormatDate(new Date(2024, 11, 31), 'DD/MM')).toBe('31/12');
    });
  });

  describe('textParseQuery', () => {
    it('parses query', () => {
      expect(utils.textParseQuery('?a=1&b=2')).toEqual({ a: '1', b: '2' });
    });

    it('decodes uri', () => {
      expect(utils.textParseQuery('?q=hello%20world')).toEqual({ q: 'hello world' });
    });
  });

  describe('textBuildQuery', () => {
    it('builds query', () => {
      expect(utils.textBuildQuery({ a: '1' })).toBe('a=1');
    });

    it('skips nulls', () => {
      expect(utils.textBuildQuery({ a: '1', b: null })).toBe('a=1');
    });
  });

  describe('textGroupBy', () => {
    it('groups by key', () => {
      const arr = [{ k: 'a' }, { k: 'b' }, { k: 'a' }];
      const result = utils.textGroupBy(arr, 'k');
      expect(result['a']).toHaveLength(2);
      expect(result['b']).toHaveLength(1);
    });
  });

  describe('textChunk', () => {
    it('chunks array', () => {
      expect(utils.textChunk([1, 2, 3, 4], 2)).toEqual([[1, 2], [3, 4]]);
    });
  });

  describe('textFlatten', () => {
    it('flattens', () => {
      expect(utils.textFlatten([[1], [2, 3]])).toEqual([1, 2, 3]);
    });
  });

  describe('textGetNested', () => {
    it('gets nested', () => {
      expect(utils.textGetNested({ a: { b: 1 } }, 'a.b')).toBe(1);
    });

    it('returns default', () => {
      expect(utils.textGetNested({}, 'a.b', 'def')).toBe('def');
    });
  });

  describe('textSetNested', () => {
    it('sets nested', () => {
      const obj: any = {};
      utils.textSetNested(obj, 'a.b', 5);
      expect(obj['a']['b']).toBe(5);
    });
  });
});
