import { describe, it, expect, vi } from 'vitest';
import * as utils from '../xmlUtils';

describe('xmlUtils', () => {
  describe('xmlDebounce', () => {
    it('debounces function calls', () => {
      vi.useFakeTimers();
      const fn = vi.fn();
      const debounced = utils.xmlDebounce(fn, 100);
      debounced();
      debounced();
      vi.advanceTimersByTime(100);
      expect(fn).toHaveBeenCalledTimes(1);
      vi.useRealTimers();
    });

    it('passes arguments correctly', () => {
      vi.useFakeTimers();
      const fn = vi.fn();
      const debounced = utils.xmlDebounce(fn, 50);
      debounced('a', 'b');
      vi.advanceTimersByTime(50);
      expect(fn).toHaveBeenCalledWith('a', 'b');
      vi.useRealTimers();
    });
  });

  describe('xmlThrottle', () => {
    it('throttles function calls', () => {
      vi.useFakeTimers();
      const fn = vi.fn();
      const throttled = utils.xmlThrottle(fn, 100);
      throttled();
      throttled();
      expect(fn).toHaveBeenCalledTimes(1);
      vi.advanceTimersByTime(100);
      throttled();
      expect(fn).toHaveBeenCalledTimes(2);
      vi.useRealTimers();
    });
  });

  describe('xmlDeepClone', () => {
    it('clones primitives', () => {
      expect(utils.xmlDeepClone(5)).toBe(5);
      expect(utils.xmlDeepClone('abc')).toBe('abc');
      expect(utils.xmlDeepClone(null)).toBe(null);
    });

    it('deep clones nested objects', () => {
      const obj = { a: { b: [1, 2] } };
      const cloned = utils.xmlDeepClone(obj);
      expect(cloned).toEqual(obj);
      expect(cloned).not.toBe(obj);
      expect(cloned['a']['b']).not.toBe(obj['a']['b']);
    });
  });

  describe('xmlGenerateId', () => {
    it('generates id with prefix', () => {
      const id = utils.xmlGenerateId('test_');
      expect(id.startsWith('test_')).toBe(true);
    });

    it('generates unique ids', () => {
      expect(utils.xmlGenerateId()).not.toBe(utils.xmlGenerateId());
    });
  });

  describe('xmlFormatDate', () => {
    it('formats date default', () => {
      expect(utils.xmlFormatDate(new Date(2024, 0, 1))).toBe('2024-01-01');
    });

    it('formats date custom', () => {
      expect(utils.xmlFormatDate(new Date(2024, 11, 31), 'DD/MM')).toBe('31/12');
    });
  });

  describe('xmlParseQuery', () => {
    it('parses query', () => {
      expect(utils.xmlParseQuery('?a=1&b=2')).toEqual({ a: '1', b: '2' });
    });

    it('decodes uri', () => {
      expect(utils.xmlParseQuery('?q=hello%20world')).toEqual({ q: 'hello world' });
    });
  });

  describe('xmlBuildQuery', () => {
    it('builds query', () => {
      expect(utils.xmlBuildQuery({ a: '1' })).toBe('a=1');
    });

    it('skips nulls', () => {
      expect(utils.xmlBuildQuery({ a: '1', b: null })).toBe('a=1');
    });
  });

  describe('xmlGroupBy', () => {
    it('groups by key', () => {
      const arr = [{ k: 'a' }, { k: 'b' }, { k: 'a' }];
      const result = utils.xmlGroupBy(arr, 'k');
      expect(result['a']).toHaveLength(2);
      expect(result['b']).toHaveLength(1);
    });
  });

  describe('xmlChunk', () => {
    it('chunks array', () => {
      expect(utils.xmlChunk([1, 2, 3, 4], 2)).toEqual([[1, 2], [3, 4]]);
    });
  });

  describe('xmlFlatten', () => {
    it('flattens', () => {
      expect(utils.xmlFlatten([[1], [2, 3]])).toEqual([1, 2, 3]);
    });
  });

  describe('xmlGetNested', () => {
    it('gets nested', () => {
      expect(utils.xmlGetNested({ a: { b: 1 } }, 'a.b')).toBe(1);
    });

    it('returns default', () => {
      expect(utils.xmlGetNested({}, 'a.b', 'def')).toBe('def');
    });
  });

  describe('xmlSetNested', () => {
    it('sets nested', () => {
      const obj: any = {};
      utils.xmlSetNested(obj, 'a.b', 5);
      expect(obj['a']['b']).toBe(5);
    });
  });
});
