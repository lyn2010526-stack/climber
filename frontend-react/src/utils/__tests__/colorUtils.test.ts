import { describe, it, expect, vi } from 'vitest';
import * as utils from '../colorUtils';

describe('colorUtils', () => {
  describe('colorDebounce', () => {
    it('debounces function calls', () => {
      vi.useFakeTimers();
      const fn = vi.fn();
      const debounced = utils.colorDebounce(fn, 100);
      debounced();
      debounced();
      vi.advanceTimersByTime(100);
      expect(fn).toHaveBeenCalledTimes(1);
      vi.useRealTimers();
    });

    it('passes arguments correctly', () => {
      vi.useFakeTimers();
      const fn = vi.fn();
      const debounced = utils.colorDebounce(fn, 50);
      debounced('a', 'b');
      vi.advanceTimersByTime(50);
      expect(fn).toHaveBeenCalledWith('a', 'b');
      vi.useRealTimers();
    });
  });

  describe('colorThrottle', () => {
    it('throttles function calls', () => {
      vi.useFakeTimers();
      const fn = vi.fn();
      const throttled = utils.colorThrottle(fn, 100);
      throttled();
      throttled();
      expect(fn).toHaveBeenCalledTimes(1);
      vi.advanceTimersByTime(100);
      throttled();
      expect(fn).toHaveBeenCalledTimes(2);
      vi.useRealTimers();
    });
  });

  describe('colorDeepClone', () => {
    it('clones primitives', () => {
      expect(utils.colorDeepClone(5)).toBe(5);
      expect(utils.colorDeepClone('abc')).toBe('abc');
      expect(utils.colorDeepClone(null)).toBe(null);
    });

    it('deep clones nested objects', () => {
      const obj = { a: { b: [1, 2] } };
      const cloned = utils.colorDeepClone(obj);
      expect(cloned).toEqual(obj);
      expect(cloned).not.toBe(obj);
      expect(cloned['a']['b']).not.toBe(obj['a']['b']);
    });
  });

  describe('colorGenerateId', () => {
    it('generates id with prefix', () => {
      const id = utils.colorGenerateId('test_');
      expect(id.startsWith('test_')).toBe(true);
    });

    it('generates unique ids', () => {
      expect(utils.colorGenerateId()).not.toBe(utils.colorGenerateId());
    });
  });

  describe('colorFormatDate', () => {
    it('formats date default', () => {
      expect(utils.colorFormatDate(new Date(2024, 0, 1))).toBe('2024-01-01');
    });

    it('formats date custom', () => {
      expect(utils.colorFormatDate(new Date(2024, 11, 31), 'DD/MM')).toBe('31/12');
    });
  });

  describe('colorParseQuery', () => {
    it('parses query', () => {
      expect(utils.colorParseQuery('?a=1&b=2')).toEqual({ a: '1', b: '2' });
    });

    it('decodes uri', () => {
      expect(utils.colorParseQuery('?q=hello%20world')).toEqual({ q: 'hello world' });
    });
  });

  describe('colorBuildQuery', () => {
    it('builds query', () => {
      expect(utils.colorBuildQuery({ a: '1' })).toBe('a=1');
    });

    it('skips nulls', () => {
      expect(utils.colorBuildQuery({ a: '1', b: null })).toBe('a=1');
    });
  });

  describe('colorGroupBy', () => {
    it('groups by key', () => {
      const arr = [{ k: 'a' }, { k: 'b' }, { k: 'a' }];
      const result = utils.colorGroupBy(arr, 'k');
      expect(result['a']).toHaveLength(2);
      expect(result['b']).toHaveLength(1);
    });
  });

  describe('colorChunk', () => {
    it('chunks array', () => {
      expect(utils.colorChunk([1, 2, 3, 4], 2)).toEqual([[1, 2], [3, 4]]);
    });
  });

  describe('colorFlatten', () => {
    it('flattens', () => {
      expect(utils.colorFlatten([[1], [2, 3]])).toEqual([1, 2, 3]);
    });
  });

  describe('colorGetNested', () => {
    it('gets nested', () => {
      expect(utils.colorGetNested({ a: { b: 1 } }, 'a.b')).toBe(1);
    });

    it('returns default', () => {
      expect(utils.colorGetNested({}, 'a.b', 'def')).toBe('def');
    });
  });

  describe('colorSetNested', () => {
    it('sets nested', () => {
      const obj: any = {};
      utils.colorSetNested(obj, 'a.b', 5);
      expect(obj['a']['b']).toBe(5);
    });
  });
});
