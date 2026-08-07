import { describe, it, expect, vi } from 'vitest';
import * as utils from '../fileUtils';

describe('fileUtils', () => {
  describe('fileDebounce', () => {
    it('debounces function calls', () => {
      vi.useFakeTimers();
      const fn = vi.fn();
      const debounced = utils.fileDebounce(fn, 100);
      debounced();
      debounced();
      vi.advanceTimersByTime(100);
      expect(fn).toHaveBeenCalledTimes(1);
      vi.useRealTimers();
    });

    it('passes arguments correctly', () => {
      vi.useFakeTimers();
      const fn = vi.fn();
      const debounced = utils.fileDebounce(fn, 50);
      debounced('a', 'b');
      vi.advanceTimersByTime(50);
      expect(fn).toHaveBeenCalledWith('a', 'b');
      vi.useRealTimers();
    });
  });

  describe('fileThrottle', () => {
    it('throttles function calls', () => {
      vi.useFakeTimers();
      const fn = vi.fn();
      const throttled = utils.fileThrottle(fn, 100);
      throttled();
      throttled();
      expect(fn).toHaveBeenCalledTimes(1);
      vi.advanceTimersByTime(100);
      throttled();
      expect(fn).toHaveBeenCalledTimes(2);
      vi.useRealTimers();
    });
  });

  describe('fileDeepClone', () => {
    it('clones primitives', () => {
      expect(utils.fileDeepClone(5)).toBe(5);
      expect(utils.fileDeepClone('abc')).toBe('abc');
      expect(utils.fileDeepClone(null)).toBe(null);
    });

    it('deep clones nested objects', () => {
      const obj = { a: { b: [1, 2] } };
      const cloned = utils.fileDeepClone(obj);
      expect(cloned).toEqual(obj);
      expect(cloned).not.toBe(obj);
      expect(cloned['a']['b']).not.toBe(obj['a']['b']);
    });
  });

  describe('fileGenerateId', () => {
    it('generates id with prefix', () => {
      const id = utils.fileGenerateId('test_');
      expect(id.startsWith('test_')).toBe(true);
    });

    it('generates unique ids', () => {
      expect(utils.fileGenerateId()).not.toBe(utils.fileGenerateId());
    });
  });

  describe('fileFormatDate', () => {
    it('formats date default', () => {
      expect(utils.fileFormatDate(new Date(2024, 0, 1))).toBe('2024-01-01');
    });

    it('formats date custom', () => {
      expect(utils.fileFormatDate(new Date(2024, 11, 31), 'DD/MM')).toBe('31/12');
    });
  });

  describe('fileParseQuery', () => {
    it('parses query', () => {
      expect(utils.fileParseQuery('?a=1&b=2')).toEqual({ a: '1', b: '2' });
    });

    it('decodes uri', () => {
      expect(utils.fileParseQuery('?q=hello%20world')).toEqual({ q: 'hello world' });
    });
  });

  describe('fileBuildQuery', () => {
    it('builds query', () => {
      expect(utils.fileBuildQuery({ a: '1' })).toBe('a=1');
    });

    it('skips nulls', () => {
      expect(utils.fileBuildQuery({ a: '1', b: null })).toBe('a=1');
    });
  });

  describe('fileGroupBy', () => {
    it('groups by key', () => {
      const arr = [{ k: 'a' }, { k: 'b' }, { k: 'a' }];
      const result = utils.fileGroupBy(arr, 'k');
      expect(result['a']).toHaveLength(2);
      expect(result['b']).toHaveLength(1);
    });
  });

  describe('fileChunk', () => {
    it('chunks array', () => {
      expect(utils.fileChunk([1, 2, 3, 4], 2)).toEqual([[1, 2], [3, 4]]);
    });
  });

  describe('fileFlatten', () => {
    it('flattens', () => {
      expect(utils.fileFlatten([[1], [2, 3]])).toEqual([1, 2, 3]);
    });
  });

  describe('fileGetNested', () => {
    it('gets nested', () => {
      expect(utils.fileGetNested({ a: { b: 1 } }, 'a.b')).toBe(1);
    });

    it('returns default', () => {
      expect(utils.fileGetNested({}, 'a.b', 'def')).toBe('def');
    });
  });

  describe('fileSetNested', () => {
    it('sets nested', () => {
      const obj: any = {};
      utils.fileSetNested(obj, 'a.b', 5);
      expect(obj['a']['b']).toBe(5);
    });
  });
});
