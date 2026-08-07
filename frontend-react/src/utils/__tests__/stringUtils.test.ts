import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import {
  stringDebounce,
  stringThrottle,
  stringDeepClone,
  stringGenerateId,
  stringFormatDate,
  stringParseQuery,
  stringBuildQuery,
  stringGroupBy,
  stringChunk,
  stringFlatten,
  stringGetNested,
  stringSetNested,
} from '../stringUtils';

describe('stringDebounce', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });
  afterEach(() => {
    vi.useRealTimers();
  });

  it('debounces function calls', () => {
    const fn = vi.fn();
    const debounced = stringDebounce(fn, 100);
    debounced();
    debounced();
    expect(fn).not.toHaveBeenCalled();
    vi.advanceTimersByTime(100);
    expect(fn).toHaveBeenCalledTimes(1);
  });
});

describe('stringThrottle', () => {
  it('throttles function calls', () => {
    const fn = vi.fn();
    const throttled = stringThrottle(fn, 100);
    throttled();
    throttled();
    expect(fn).toHaveBeenCalledTimes(1);
  });
});

describe('stringDeepClone', () => {
  it('clones primitives', () => {
    expect(stringDeepClone(42)).toBe(42);
    expect(stringDeepClone('hello')).toBe('hello');
    expect(stringDeepClone(null)).toBe(null);
  });

  it('clones arrays', () => {
    const arr = [1, 2, [3, 4]];
    const cloned = stringDeepClone(arr);
    expect(cloned).toEqual(arr);
    expect(cloned).not.toBe(arr);
  });

  it('clones objects', () => {
    const obj = { a: 1, b: { c: 2 } };
    const cloned = stringDeepClone(obj);
    expect(cloned).toEqual(obj);
    expect(cloned).not.toBe(obj);
    expect(cloned['b']).not.toBe(obj['b']);
  });
});

describe('stringGenerateId', () => {
  it('generates an ID', () => {
    const id = stringGenerateId();
    expect(id).toBeTruthy();
    expect(typeof id).toBe('string');
  });

  it('includes prefix', () => {
    const id = stringGenerateId('test-');
    expect(id.startsWith('test-')).toBe(true);
  });
});

describe('stringFormatDate', () => {
  it('formats date with default format', () => {
    const date = new Date(2024, 0, 15);
    expect(stringFormatDate(date)).toBe('2024-01-15');
  });

  it('formats date with custom format', () => {
    const date = new Date(2024, 11, 25);
    expect(stringFormatDate(date, 'DD/MM/YYYY')).toBe('25/12/2024');
  });
});

describe('stringParseQuery', () => {
  it('parses query string', () => {
    expect(stringParseQuery('?a=1&b=2')).toEqual({ a: '1', b: '2' });
  });

  it('handles empty query', () => {
    expect(stringParseQuery('')).toEqual({});
  });

  it('decodes URL encoded values', () => {
    expect(stringParseQuery('name=hello%20world')).toEqual({ name: 'hello world' });
  });
});

describe('stringBuildQuery', () => {
  it('builds query string', () => {
    expect(stringBuildQuery({ a: 1, b: 2 })).toBe('a=1&b=2');
  });

  it('skips null and undefined', () => {
    expect(stringBuildQuery({ a: 1, b: null, c: undefined })).toBe('a=1');
  });

  it('encodes values', () => {
    expect(stringBuildQuery({ name: 'hello world' })).toBe('name=hello%20world');
  });
});

describe('stringGroupBy', () => {
  it('groups array by key', () => {
    const arr = [
      { type: 'a', value: 1 },
      { type: 'b', value: 2 },
      { type: 'a', value: 3 },
    ];
    const grouped = stringGroupBy(arr, 'type');
    expect(grouped['a']).toHaveLength(2);
    expect(grouped['b']).toHaveLength(1);
  });
});

describe('stringChunk', () => {
  it('chunks array', () => {
    expect(stringChunk([1, 2, 3, 4, 5], 2)).toEqual([[1, 2], [3, 4], [5]]);
  });

  it('handles empty array', () => {
    expect(stringChunk([], 2)).toEqual([]);
  });
});

describe('stringFlatten', () => {
  it('flattens nested arrays', () => {
    expect(stringFlatten([1, [2, 3], 4])).toEqual([1, 2, 3, 4]);
  });
});

describe('stringGetNested', () => {
  it('gets nested value', () => {
    const obj = { a: { b: { c: 42 } } };
    expect(stringGetNested(obj, 'a.b.c')).toBe(42);
  });

  it('returns default value for missing path', () => {
    expect(stringGetNested({}, 'a.b.c', 'default')).toBe('default');
  });
});

describe('stringSetNested', () => {
  it('sets nested value', () => {
    const obj: any = {};
    stringSetNested(obj, 'a.b.c', 42);
    expect(obj['a']['b'].c).toBe(42);
  });

  it('overwrites existing value', () => {
    const obj: any = { a: { b: { c: 1 } } };
    stringSetNested(obj, 'a.b.c', 42);
    expect(obj['a']['b'].c).toBe(42);
  });
});
