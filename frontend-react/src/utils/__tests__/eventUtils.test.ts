import { describe, it, expect, vi } from 'vitest';
import * as utils from '../eventUtils';

describe('eventUtils', () => {
  describe('eventDebounce', () => {
    it('debounces function calls', () => {
      vi.useFakeTimers();
      const fn = vi.fn();
      const debounced = utils.eventDebounce(fn, 100);
      debounced();
      debounced();
      vi.advanceTimersByTime(100);
      expect(fn).toHaveBeenCalledTimes(1);
      vi.useRealTimers();
    });

    it('passes arguments correctly', () => {
      vi.useFakeTimers();
      const fn = vi.fn();
      const debounced = utils.eventDebounce(fn, 50);
      debounced('a', 'b');
      vi.advanceTimersByTime(50);
      expect(fn).toHaveBeenCalledWith('a', 'b');
      vi.useRealTimers();
    });
  });

  describe('eventThrottle', () => {
    it('throttles function calls', () => {
      vi.useFakeTimers();
      const fn = vi.fn();
      const throttled = utils.eventThrottle(fn, 100);
      throttled();
      throttled();
      expect(fn).toHaveBeenCalledTimes(1);
      vi.advanceTimersByTime(100);
      throttled();
      expect(fn).toHaveBeenCalledTimes(2);
      vi.useRealTimers();
    });
  });

  describe('eventDeepClone', () => {
    it('clones primitives', () => {
      expect(utils.eventDeepClone(5)).toBe(5);
      expect(utils.eventDeepClone('abc')).toBe('abc');
      expect(utils.eventDeepClone(null)).toBe(null);
    });

    it('deep clones nested objects', () => {
      const obj = { a: { b: [1, 2] } };
      const cloned = utils.eventDeepClone(obj);
      expect(cloned).toEqual(obj);
      expect(cloned).not.toBe(obj);
      expect(cloned['a']['b']).not.toBe(obj['a']['b']);
    });
  });

  describe('eventGenerateId', () => {
    it('generates id with prefix', () => {
      const id = utils.eventGenerateId('test_');
      expect(id.startsWith('test_')).toBe(true);
    });

    it('generates unique ids', () => {
      expect(utils.eventGenerateId()).not.toBe(utils.eventGenerateId());
    });
  });

  describe('eventFormatDate', () => {
    it('formats date default', () => {
      expect(utils.eventFormatDate(new Date(2024, 0, 1))).toBe('2024-01-01');
    });

    it('formats date custom', () => {
      expect(utils.eventFormatDate(new Date(2024, 11, 31), 'DD/MM')).toBe('31/12');
    });
  });

  describe('eventParseQuery', () => {
    it('parses query', () => {
      expect(utils.eventParseQuery('?a=1&b=2')).toEqual({ a: '1', b: '2' });
    });

    it('decodes uri', () => {
      expect(utils.eventParseQuery('?q=hello%20world')).toEqual({ q: 'hello world' });
    });
  });

  describe('eventBuildQuery', () => {
    it('builds query', () => {
      expect(utils.eventBuildQuery({ a: '1' })).toBe('a=1');
    });

    it('skips nulls', () => {
      expect(utils.eventBuildQuery({ a: '1', b: null })).toBe('a=1');
    });
  });

  describe('eventGroupBy', () => {
    it('groups by key', () => {
      const arr = [{ k: 'a' }, { k: 'b' }, { k: 'a' }];
      const result = utils.eventGroupBy(arr, 'k');
      expect(result['a']).toHaveLength(2);
      expect(result['b']).toHaveLength(1);
    });
  });

  describe('eventChunk', () => {
    it('chunks array', () => {
      expect(utils.eventChunk([1, 2, 3, 4], 2)).toEqual([[1, 2], [3, 4]]);
    });
  });

  describe('eventFlatten', () => {
    it('flattens', () => {
      expect(utils.eventFlatten([[1], [2, 3]])).toEqual([1, 2, 3]);
    });
  });

  describe('eventGetNested', () => {
    it('gets nested', () => {
      expect(utils.eventGetNested({ a: { b: 1 } }, 'a.b')).toBe(1);
    });

    it('returns default', () => {
      expect(utils.eventGetNested({}, 'a.b', 'def')).toBe('def');
    });
  });

  describe('eventSetNested', () => {
    it('sets nested', () => {
      const obj: any = {};
      utils.eventSetNested(obj, 'a.b', 5);
      expect(obj['a']['b']).toBe(5);
    });
  });
});
