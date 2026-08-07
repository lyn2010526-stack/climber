// @ts-nocheck
/**
 * number utility functions.
 */


/**
 * Debounce a function.
 */
export function numberDebounce<T extends (...args: any[]) => any>(
    fn: T,
    delay: number
): (...args: Parameters<T>) => void {
    let timeoutId: ReturnType<typeof setTimeout> | null = null
    return (...args: Parameters<T>) => {
        if (timeoutId) clearTimeout(timeoutId)
        timeoutId = setTimeout(() => fn(...args), delay)
    }
}


/**
 * Throttle a function.
 */
export function numberThrottle<T extends (...args: any[]) => any>(
    fn: T,
    limit: number
): (...args: Parameters<T>) => void {
    let inThrottle = false
    return (...args: Parameters<T>) => {
        if (!inThrottle) {
            fn(...args)
            inThrottle = true
            setTimeout(() => { inThrottle = false }, limit)
        }
    }
}


/**
 * Deep clone an object.
 */
export function numberDeepClone<T>(obj: T): T {
    if (obj === null || typeof obj !== 'object') return obj
    if (Array.isArray(obj)) return obj.map(item => numberDeepClone(item)) as T
    const cloned = {} as T
    for (const key in obj) {
        if (Object.prototype.hasOwnProperty.call(obj, key)) {
            cloned[key] = numberDeepClone(obj[key])
        }
    }
    return cloned
}


/**
 * Generate a unique ID.
 */
export function numberGenerateId(prefix: string = ''): string {
    const timestamp = Date.now().toString(36)
    const random = Math.random().toString(36).substring(2, 8)
    return `${prefix}${timestamp}${random}`
}


/**
 * Format a date.
 */
export function numberFormatDate(date: Date, format: string = 'YYYY-MM-DD'): string {
    const year = date.getFullYear()
    const month = String(date.getMonth() + 1).padStart(2, '0')
    const day = String(date.getDate()).padStart(2, '0')
    return format
        .replace('YYYY', String(year))
        .replace('MM', month)
        .replace('DD', day)
}


/**
 * Parse query string.
 */
export function numberParseQuery(queryString: string): Record<string, string> {
    const params: Record<string, string> = {}
    const pairs = queryString.replace(/^\?/, '').split('&')
    for (const pair of pairs) {
        const [key, value] = pair.split('=')
        if (key) {
            params[decodeURIComponent(key)] = decodeURIComponent(value || '')
        }
    }
    return params
}


/**
 * Build query string.
 */
export function numberBuildQuery(params: Record<string, any>): string {
    const parts: string[] = []
    for (const key in params) {
        if (params[key] !== undefined && params[key] !== null) {
            parts.push(`${encodeURIComponent(key)}=${encodeURIComponent(params[key])}`)
        }
    }
    return parts.join('&')
}


/**
 * Group array by key.
 */
export function numberGroupBy<T>(array: T[], key: keyof T): Record<string, T[]> {
    return array.reduce((acc, item) => {
        const group = String(item[key])
        if (!acc[group]) acc[group] = []
        acc[group].push(item)
        return acc
    }, {} as Record<string, T[]>)
}


/**
 * Chunk array.
 */
export function numberChunk<T>(array: T[], size: number): T[][] {
    const chunks: T[][] = []
    for (let i = 0; i < array.length; i += size) {
        chunks.push(array.slice(i, i + size))
    }
    return chunks
}


/**
 * Flatten nested array.
 */
export function numberFlatten<T>(array: (T | T[])[]): T[] {
    return array.reduce<T[]>((acc, val) => acc.concat(val), [])
}


/**
 * Get nested property.
 */
export function numberGetNested(obj: any, path: string, defaultValue?: any): any {
    const keys = path.split('.')
    let current = obj
    for (const key of keys) {
        if (current === undefined || current === null) return defaultValue
        current = current[key]
    }
    return current !== undefined ? current : defaultValue
}


/**
 * Set nested property.
 */
export function numberSetNested(obj: any, path: string, value: any): void {
    const keys = path.split('.')
    let current = obj
    for (let i = 0; i < keys.length - 1; i++) {
        if (!(keys[i] in current)) {
            current[keys[i]] = {}
        }
        current = current[keys[i]]
    }
    current[keys[keys.length - 1]] = value
}


/**
 * Clamp a value between min and max.
 */
export function clamp(value: number, min: number, max: number): number {
    return Math.min(Math.max(value, min), max)
}


/**
 * Round a number to specified decimal places.
 */
export function round(value: number, decimals: number = 0): number {
    const factor = Math.pow(10, decimals)
    return Math.round(value * factor) / factor
}


/**
 * Generate a random integer between min and max (inclusive).
 */
export function randomInt(min: number, max: number): number {
    return Math.floor(Math.random() * (max - min + 1)) + min
}


/**
 * Format a number with locale options.
 */
export function formatNumber(value: number, options?: Intl.NumberFormatOptions): string {
    return new Intl.NumberFormat(undefined, options).format(value)
}


/**
 * Parse a string to number.
 */
export function parseNumber(value: string, defaultValue: number = NaN): number {
    const parsed = Number(value)
    return isNaN(parsed) ? defaultValue : parsed
}


/**
 * Sum an array of numbers.
 */
export function sum(values: number[]): number {
    return values.reduce((acc, val) => acc + val, 0)
}


/**
 * Calculate average of an array of numbers.
 */
export function average(values: number[]): number {
    return values.length === 0 ? 0 : sum(values) / values.length
}


/**
 * Calculate percentage.
 */
export function percentage(value: number, total: number): number {
    return total === 0 ? 0 : (value / total) * 100
}
