import { describe, it, expect, vi } from 'vitest';
import * as utils from '../imageUtils';

describe('imageUtils', () => {
  describe('imageDebounce', () => {
    it('debounces function calls', () => {
      vi.useFakeTimers();
      const fn = vi.fn();
      const debounced = utils.imageDebounce(fn, 100);
      debounced();
      debounced();
      vi.advanceTimersByTime(100);
      expect(fn).toHaveBeenCalledTimes(1);
      vi.useRealTimers();
    });

    it('passes arguments correctly', () => {
      vi.useFakeTimers();
      const fn = vi.fn();
      const debounced = utils.imageDebounce(fn, 50);
      debounced('a', 'b');
      vi.advanceTimersByTime(50);
      expect(fn).toHaveBeenCalledWith('a', 'b');
      vi.useRealTimers();
    });
  });

  describe('imageThrottle', () => {
    it('throttles function calls', () => {
      vi.useFakeTimers();
      const fn = vi.fn();
      const throttled = utils.imageThrottle(fn, 100);
      throttled();
      throttled();
      expect(fn).toHaveBeenCalledTimes(1);
      vi.advanceTimersByTime(100);
      throttled();
      expect(fn).toHaveBeenCalledTimes(2);
      vi.useRealTimers();
    });
  });

  describe('imageDeepClone', () => {
    it('clones primitives', () => {
      expect(utils.imageDeepClone(5)).toBe(5);
      expect(utils.imageDeepClone('abc')).toBe('abc');
      expect(utils.imageDeepClone(null)).toBe(null);
    });

    it('deep clones nested objects', () => {
      const obj = { a: { b: [1, 2] } };
      const cloned = utils.imageDeepClone(obj);
      expect(cloned).toEqual(obj);
      expect(cloned).not.toBe(obj);
      expect(cloned['a']['b']).not.toBe(obj['a']['b']);
    });
  });

  describe('imageGenerateId', () => {
    it('generates id with prefix', () => {
      const id = utils.imageGenerateId('test_');
      expect(id.startsWith('test_')).toBe(true);
    });

    it('generates unique ids', () => {
      expect(utils.imageGenerateId()).not.toBe(utils.imageGenerateId());
    });
  });

  describe('imageFormatDate', () => {
    it('formats date default', () => {
      expect(utils.imageFormatDate(new Date(2024, 0, 1))).toBe('2024-01-01');
    });

    it('formats date custom', () => {
      expect(utils.imageFormatDate(new Date(2024, 11, 31), 'DD/MM')).toBe('31/12');
    });
  });

  describe('imageParseQuery', () => {
    it('parses query', () => {
      expect(utils.imageParseQuery('?a=1&b=2')).toEqual({ a: '1', b: '2' });
    });

    it('decodes uri', () => {
      expect(utils.imageParseQuery('?q=hello%20world')).toEqual({ q: 'hello world' });
    });
  });

  describe('imageBuildQuery', () => {
    it('builds query', () => {
      expect(utils.imageBuildQuery({ a: '1' })).toBe('a=1');
    });

    it('skips nulls', () => {
      expect(utils.imageBuildQuery({ a: '1', b: null })).toBe('a=1');
    });
  });

  describe('imageGroupBy', () => {
    it('groups by key', () => {
      const arr = [{ k: 'a' }, { k: 'b' }, { k: 'a' }];
      const result = utils.imageGroupBy(arr, 'k');
      expect(result['a']).toHaveLength(2);
      expect(result['b']).toHaveLength(1);
    });
  });

  describe('imageChunk', () => {
    it('chunks array', () => {
      expect(utils.imageChunk([1, 2, 3, 4], 2)).toEqual([[1, 2], [3, 4]]);
    });
  });

  describe('imageFlatten', () => {
    it('flattens', () => {
      expect(utils.imageFlatten([[1], [2, 3]])).toEqual([1, 2, 3]);
    });
  });

  describe('imageGetNested', () => {
    it('gets nested', () => {
      expect(utils.imageGetNested({ a: { b: 1 } }, 'a.b')).toBe(1);
    });

    it('returns default', () => {
      expect(utils.imageGetNested({}, 'a.b', 'def')).toBe('def');
    });
  });

  describe('imageSetNested', () => {
    it('sets nested', () => {
      const obj: any = {};
      utils.imageSetNested(obj, 'a.b', 5);
      expect(obj['a']['b']).toBe(5);
    });
  });
});
