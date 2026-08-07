import { describe, it, expect, vi } from 'vitest';
import * as utils from '../htmlUtils';

describe('htmlUtils', () => {
  describe('htmlDebounce', () => {
    it('debounces function calls', () => {
      vi.useFakeTimers();
      const fn = vi.fn();
      const debounced = utils.htmlDebounce(fn, 100);
      debounced();
      debounced();
      vi.advanceTimersByTime(100);
      expect(fn).toHaveBeenCalledTimes(1);
      vi.useRealTimers();
    });

    it('passes arguments correctly', () => {
      vi.useFakeTimers();
      const fn = vi.fn();
      const debounced = utils.htmlDebounce(fn, 50);
      debounced('a', 'b');
      vi.advanceTimersByTime(50);
      expect(fn).toHaveBeenCalledWith('a', 'b');
      vi.useRealTimers();
    });
  });

  describe('htmlThrottle', () => {
    it('throttles function calls', () => {
      vi.useFakeTimers();
      const fn = vi.fn();
      const throttled = utils.htmlThrottle(fn, 100);
      throttled();
      throttled();
      expect(fn).toHaveBeenCalledTimes(1);
      vi.advanceTimersByTime(100);
      throttled();
      expect(fn).toHaveBeenCalledTimes(2);
      vi.useRealTimers();
    });
  });

  describe('htmlDeepClone', () => {
    it('clones primitives', () => {
      expect(utils.htmlDeepClone(5)).toBe(5);
      expect(utils.htmlDeepClone('abc')).toBe('abc');
      expect(utils.htmlDeepClone(null)).toBe(null);
    });

    it('deep clones nested objects', () => {
      const obj = { a: { b: [1, 2] } };
      const cloned = utils.htmlDeepClone(obj);
      expect(cloned).toEqual(obj);
      expect(cloned).not.toBe(obj);
      expect(cloned['a']['b']).not.toBe(obj['a']['b']);
    });
  });

  describe('htmlGenerateId', () => {
    it('generates id with prefix', () => {
      const id = utils.htmlGenerateId('test_');
      expect(id.startsWith('test_')).toBe(true);
    });

    it('generates unique ids', () => {
      expect(utils.htmlGenerateId()).not.toBe(utils.htmlGenerateId());
    });
  });

  describe('htmlFormatDate', () => {
    it('formats date default', () => {
      expect(utils.htmlFormatDate(new Date(2024, 0, 1))).toBe('2024-01-01');
    });

    it('formats date custom', () => {
      expect(utils.htmlFormatDate(new Date(2024, 11, 31), 'DD/MM')).toBe('31/12');
    });
  });

  describe('htmlParseQuery', () => {
    it('parses query', () => {
      expect(utils.htmlParseQuery('?a=1&b=2')).toEqual({ a: '1', b: '2' });
    });

    it('decodes uri', () => {
      expect(utils.htmlParseQuery('?q=hello%20world')).toEqual({ q: 'hello world' });
    });
  });

  describe('htmlBuildQuery', () => {
    it('builds query', () => {
      expect(utils.htmlBuildQuery({ a: '1' })).toBe('a=1');
    });

    it('skips nulls', () => {
      expect(utils.htmlBuildQuery({ a: '1', b: null })).toBe('a=1');
    });
  });

  describe('htmlGroupBy', () => {
    it('groups by key', () => {
      const arr = [{ k: 'a' }, { k: 'b' }, { k: 'a' }];
      const result = utils.htmlGroupBy(arr, 'k');
      expect(result['a']).toHaveLength(2);
      expect(result['b']).toHaveLength(1);
    });
  });

  describe('htmlChunk', () => {
    it('chunks array', () => {
      expect(utils.htmlChunk([1, 2, 3, 4], 2)).toEqual([[1, 2], [3, 4]]);
    });
  });

  describe('htmlFlatten', () => {
    it('flattens', () => {
      expect(utils.htmlFlatten([[1], [2, 3]])).toEqual([1, 2, 3]);
    });
  });

  describe('htmlGetNested', () => {
    it('gets nested', () => {
      expect(utils.htmlGetNested({ a: { b: 1 } }, 'a.b')).toBe(1);
    });

    it('returns default', () => {
      expect(utils.htmlGetNested({}, 'a.b', 'def')).toBe('def');
    });
  });

  describe('htmlSetNested', () => {
    it('sets nested', () => {
      const obj: any = {};
      utils.htmlSetNested(obj, 'a.b', 5);
      expect(obj['a']['b']).toBe(5);
    });
  });
});
