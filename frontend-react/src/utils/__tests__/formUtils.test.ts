import { describe, it, expect, vi } from 'vitest';
import * as utils from '../formUtils';

describe('formUtils', () => {
  describe('formDebounce', () => {
    it('debounces function calls', () => {
      vi.useFakeTimers();
      const fn = vi.fn();
      const debounced = utils.formDebounce(fn, 100);
      debounced();
      debounced();
      vi.advanceTimersByTime(100);
      expect(fn).toHaveBeenCalledTimes(1);
      vi.useRealTimers();
    });

    it('passes arguments correctly', () => {
      vi.useFakeTimers();
      const fn = vi.fn();
      const debounced = utils.formDebounce(fn, 50);
      debounced('a', 'b');
      vi.advanceTimersByTime(50);
      expect(fn).toHaveBeenCalledWith('a', 'b');
      vi.useRealTimers();
    });
  });

  describe('formThrottle', () => {
    it('throttles function calls', () => {
      vi.useFakeTimers();
      const fn = vi.fn();
      const throttled = utils.formThrottle(fn, 100);
      throttled();
      throttled();
      expect(fn).toHaveBeenCalledTimes(1);
      vi.advanceTimersByTime(100);
      throttled();
      expect(fn).toHaveBeenCalledTimes(2);
      vi.useRealTimers();
    });
  });

  describe('formDeepClone', () => {
    it('clones primitives', () => {
      expect(utils.formDeepClone(5)).toBe(5);
      expect(utils.formDeepClone('abc')).toBe('abc');
      expect(utils.formDeepClone(null)).toBe(null);
    });

    it('deep clones nested objects', () => {
      const obj = { a: { b: [1, 2] } };
      const cloned = utils.formDeepClone(obj);
      expect(cloned).toEqual(obj);
      expect(cloned).not.toBe(obj);
      expect(cloned['a']['b']).not.toBe(obj['a']['b']);
    });
  });

  describe('formGenerateId', () => {
    it('generates id with prefix', () => {
      const id = utils.formGenerateId('test_');
      expect(id.startsWith('test_')).toBe(true);
    });

    it('generates unique ids', () => {
      expect(utils.formGenerateId()).not.toBe(utils.formGenerateId());
    });
  });

  describe('formFormatDate', () => {
    it('formats date default', () => {
      expect(utils.formFormatDate(new Date(2024, 0, 1))).toBe('2024-01-01');
    });

    it('formats date custom', () => {
      expect(utils.formFormatDate(new Date(2024, 11, 31), 'DD/MM')).toBe('31/12');
    });
  });

  describe('formParseQuery', () => {
    it('parses query', () => {
      expect(utils.formParseQuery('?a=1&b=2')).toEqual({ a: '1', b: '2' });
    });

    it('decodes uri', () => {
      expect(utils.formParseQuery('?q=hello%20world')).toEqual({ q: 'hello world' });
    });
  });

  describe('formBuildQuery', () => {
    it('builds query', () => {
      expect(utils.formBuildQuery({ a: '1' })).toBe('a=1');
    });

    it('skips nulls', () => {
      expect(utils.formBuildQuery({ a: '1', b: null })).toBe('a=1');
    });
  });

  describe('formGroupBy', () => {
    it('groups by key', () => {
      const arr = [{ k: 'a' }, { k: 'b' }, { k: 'a' }];
      const result = utils.formGroupBy(arr, 'k');
      expect(result['a']).toHaveLength(2);
      expect(result['b']).toHaveLength(1);
    });
  });

  describe('formChunk', () => {
    it('chunks array', () => {
      expect(utils.formChunk([1, 2, 3, 4], 2)).toEqual([[1, 2], [3, 4]]);
    });
  });

  describe('formFlatten', () => {
    it('flattens', () => {
      expect(utils.formFlatten([[1], [2, 3]])).toEqual([1, 2, 3]);
    });
  });

  describe('formGetNested', () => {
    it('gets nested', () => {
      expect(utils.formGetNested({ a: { b: 1 } }, 'a.b')).toBe(1);
    });

    it('returns default', () => {
      expect(utils.formGetNested({}, 'a.b', 'def')).toBe('def');
    });
  });

  describe('formSetNested', () => {
    it('sets nested', () => {
      const obj: any = {};
      utils.formSetNested(obj, 'a.b', 5);
      expect(obj['a']['b']).toBe(5);
    });
  });
});
