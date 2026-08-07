// @ts-nocheck
/**
 * object utility functions.
 */


/**
 * Debounce a function.
 */
export function objectDebounce<T extends (...args: any[]) => any>(
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
export function objectThrottle<T extends (...args: any[]) => any>(
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
export function objectDeepClone<T>(obj: T): T {
    if (obj === null || typeof obj !== 'object') return obj
    if (Array.isArray(obj)) return obj.map(item => objectDeepClone(item)) as T
    const cloned = {} as T
    for (const key in obj) {
        if (Object.prototype.hasOwnProperty.call(obj, key)) {
            cloned[key] = objectDeepClone(obj[key])
        }
    }
    return cloned
}


/**
 * Generate a unique ID.
 */
export function objectGenerateId(prefix: string = ''): string {
    const timestamp = Date.now().toString(36)
    const random = Math.random().toString(36).substring(2, 8)
    return `${prefix}${timestamp}${random}`
}


/**
 * Format a date.
 */
export function objectFormatDate(date: Date, format: string = 'YYYY-MM-DD'): string {
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
export function objectParseQuery(queryString: string): Record<string, string> {
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
export function objectBuildQuery(params: Record<string, any>): string {
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
export function objectGroupBy<T>(array: T[], key: keyof T): Record<string, T[]> {
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
export function objectChunk<T>(array: T[], size: number): T[][] {
    const chunks: T[][] = []
    for (let i = 0; i < array.length; i += size) {
        chunks.push(array.slice(i, i + size))
    }
    return chunks
}


/**
 * Flatten nested array.
 */
export function objectFlatten<T>(array: (T | T[])[]): T[] {
    return array.reduce<T[]>((acc, val) => acc.concat(val), [])
}


/**
 * Get nested property.
 */
export function objectGetNested(obj: any, path: string, defaultValue?: any): any {
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
export function objectSetNested(obj: any, path: string, value: any): void {
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
 * Pick specified keys from an object.
 */
export function pick<T extends object, K extends keyof T>(obj: T, keys: K[]): Pick<T, K> {
    const result = {} as Pick<T, K>
    for (const key of keys) {
        if (key in obj) {
            result[key] = obj[key]
        }
    }
    return result
}


/**
 * Omit specified keys from an object.
 */
export function omit<T extends object, K extends keyof T>(obj: T, keys: K[]): Omit<T, K> {
    const result = { ...obj }
    for (const key of keys) {
        delete result[key]
    }
    return result as Omit<T, K>
}


/**
 * Deep merge objects.
 */
export function merge<T extends object, U extends object>(a: T, b: U): T & U {
    const result = { ...a } as T & U
    for (const key in b) {
        if (Object.prototype.hasOwnProperty.call(b, key)) {
            const val = (b as any)[key]
            if (val && typeof val === 'object' && !Array.isArray(val) && typeof (result as any)[key] === 'object') {
                (result as any)[key] = merge((result as any)[key], val)
            } else {
                (result as any)[key] = val
            }
        }
    }
    return result
}


/**
 * Check if an object is empty.
 */
export function isEmpty(obj: object): boolean {
    return Object.keys(obj).length === 0
}


/**
 * Deep equality check.
 */
export function deepEqual(a: unknown, b: unknown): boolean {
    if (a === b) return true
    if (typeof a !== typeof b) return false
    if (typeof a !== 'object' || a === null || b === null) return false
    const keysA = Object.keys(a as object)
    const keysB = Object.keys(b as object)
    if (keysA.length !== keysB.length) return false
    for (const key of keysA) {
        if (!deepEqual((a as any)[key], (b as any)[key])) return false
    }
    return true
}


/**
 * Flatten nested object keys.
 */
export function flattenKeys(obj: Record<string, any>, prefix: string = ''): Record<string, any> {
    const result: Record<string, any> = {}
    for (const key in obj) {
        if (Object.prototype.hasOwnProperty.call(obj, key)) {
            const newKey = prefix ? `${prefix}.${key}` : key
            if (obj[key] && typeof obj[key] === 'object' && !Array.isArray(obj[key])) {
                Object.assign(result, flattenKeys(obj[key], newKey))
            } else {
                result[newKey] = obj[key]
            }
        }
    }
    return result
}
