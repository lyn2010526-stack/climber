import { describe, it, expect, vi } from 'vitest';
import * as utils from '../cryptoUtils';

describe('cryptoUtils', () => {
  describe('cryptoDebounce', () => {
    it('debounces function calls', () => {
      vi.useFakeTimers();
      const fn = vi.fn();
      const debounced = utils.cryptoDebounce(fn, 100);
      debounced();
      debounced();
      vi.advanceTimersByTime(100);
      expect(fn).toHaveBeenCalledTimes(1);
      vi.useRealTimers();
    });

    it('passes arguments correctly', () => {
      vi.useFakeTimers();
      const fn = vi.fn();
      const debounced = utils.cryptoDebounce(fn, 50);
      debounced('a', 'b');
      vi.advanceTimersByTime(50);
      expect(fn).toHaveBeenCalledWith('a', 'b');
      vi.useRealTimers();
    });
  });

  describe('cryptoThrottle', () => {
    it('throttles function calls', () => {
      vi.useFakeTimers();
      const fn = vi.fn();
      const throttled = utils.cryptoThrottle(fn, 100);
      throttled();
      throttled();
      expect(fn).toHaveBeenCalledTimes(1);
      vi.advanceTimersByTime(100);
      throttled();
      expect(fn).toHaveBeenCalledTimes(2);
      vi.useRealTimers();
    });
  });

  describe('cryptoDeepClone', () => {
    it('clones primitives', () => {
      expect(utils.cryptoDeepClone(5)).toBe(5);
      expect(utils.cryptoDeepClone('abc')).toBe('abc');
      expect(utils.cryptoDeepClone(null)).toBe(null);
    });

    it('deep clones nested objects', () => {
      const obj = { a: { b: [1, 2] } };
      const cloned = utils.cryptoDeepClone(obj);
      expect(cloned).toEqual(obj);
      expect(cloned).not.toBe(obj);
      expect(cloned['a']['b']).not.toBe(obj['a']['b']);
    });
  });

  describe('cryptoGenerateId', () => {
    it('generates id with prefix', () => {
      const id = utils.cryptoGenerateId('test_');
      expect(id.startsWith('test_')).toBe(true);
    });

    it('generates unique ids', () => {
      expect(utils.cryptoGenerateId()).not.toBe(utils.cryptoGenerateId());
    });
  });

  describe('cryptoFormatDate', () => {
    it('formats date default', () => {
      expect(utils.cryptoFormatDate(new Date(2024, 0, 1))).toBe('2024-01-01');
    });

    it('formats date custom', () => {
      expect(utils.cryptoFormatDate(new Date(2024, 11, 31), 'DD/MM')).toBe('31/12');
    });
  });

  describe('cryptoParseQuery', () => {
    it('parses query', () => {
      expect(utils.cryptoParseQuery('?a=1&b=2')).toEqual({ a: '1', b: '2' });
    });

    it('decodes uri', () => {
      expect(utils.cryptoParseQuery('?q=hello%20world')).toEqual({ q: 'hello world' });
    });
  });

  describe('cryptoBuildQuery', () => {
    it('builds query', () => {
      expect(utils.cryptoBuildQuery({ a: '1' })).toBe('a=1');
    });

    it('skips nulls', () => {
      expect(utils.cryptoBuildQuery({ a: '1', b: null })).toBe('a=1');
    });
  });

  describe('cryptoGroupBy', () => {
    it('groups by key', () => {
      const arr = [{ k: 'a' }, { k: 'b' }, { k: 'a' }];
      const result = utils.cryptoGroupBy(arr, 'k');
      expect(result['a']).toHaveLength(2);
      expect(result['b']).toHaveLength(1);
    });
  });

  describe('cryptoChunk', () => {
    it('chunks array', () => {
      expect(utils.cryptoChunk([1, 2, 3, 4], 2)).toEqual([[1, 2], [3, 4]]);
    });
  });

  describe('cryptoFlatten', () => {
    it('flattens', () => {
      expect(utils.cryptoFlatten([[1], [2, 3]])).toEqual([1, 2, 3]);
    });
  });

  describe('cryptoGetNested', () => {
    it('gets nested', () => {
      expect(utils.cryptoGetNested({ a: { b: 1 } }, 'a.b')).toBe(1);
    });

    it('returns default', () => {
      expect(utils.cryptoGetNested({}, 'a.b', 'def')).toBe('def');
    });
  });

  describe('cryptoSetNested', () => {
    it('sets nested', () => {
      const obj: any = {};
      utils.cryptoSetNested(obj, 'a.b', 5);
      expect(obj['a']['b']).toBe(5);
    });
  });
});
