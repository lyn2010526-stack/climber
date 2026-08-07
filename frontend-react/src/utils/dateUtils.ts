// @ts-nocheck
/**
 * date utility functions.
 */


/**
 * Debounce a function.
 */
export function dateDebounce<T extends (...args: any[]) => any>(
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
export function dateThrottle<T extends (...args: any[]) => any>(
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
export function dateDeepClone<T>(obj: T): T {
    if (obj === null || typeof obj !== 'object') return obj
    if (Array.isArray(obj)) return obj.map(item => dateDeepClone(item)) as T
    const cloned = {} as T
    for (const key in obj) {
        if (Object.prototype.hasOwnProperty.call(obj, key)) {
            cloned[key] = dateDeepClone(obj[key])
        }
    }
    return cloned
}


/**
 * Generate a unique ID.
 */
export function dateGenerateId(prefix: string = ''): string {
    const timestamp = Date.now().toString(36)
    const random = Math.random().toString(36).substring(2, 8)
    return `${prefix}${timestamp}${random}`
}


/**
 * Format a date.
 */
export function dateFormatDate(date: Date, format: string = 'YYYY-MM-DD'): string {
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
export function dateParseQuery(queryString: string): Record<string, string> {
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
export function dateBuildQuery(params: Record<string, any>): string {
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
export function dateGroupBy<T>(array: T[], key: keyof T): Record<string, T[]> {
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
export function dateChunk<T>(array: T[], size: number): T[][] {
    const chunks: T[][] = []
    for (let i = 0; i < array.length; i += size) {
        chunks.push(array.slice(i, i + size))
    }
    return chunks
}


/**
 * Flatten nested array.
 */
export function dateFlatten<T>(array: (T | T[])[]): T[] {
    return array.reduce<T[]>((acc, val) => acc.concat(val), [])
}


/**
 * Get nested property.
 */
export function dateGetNested(obj: any, path: string, defaultValue?: any): any {
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
export function dateSetNested(obj: any, path: string, value: any): void {
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
 * Format a date to string.
 */
export function formatDate(date: Date, format: string = 'YYYY-MM-DD'): string {
    const year = date.getFullYear()
    const month = String(date.getMonth() + 1).padStart(2, '0')
    const day = String(date.getDate()).padStart(2, '0')
    return format
        .replace('YYYY', String(year))
        .replace('MM', month)
        .replace('DD', day)
}


/**
 * Parse a date string to Date object.
 */
export function parseDate(dateStr: string): Date | null {
    const date = new Date(dateStr)
    return isNaN(date.getTime()) ? null : date
}


/**
 * Add days to a date.
 */
export function addDays(date: Date, days: number): Date {
    const result = new Date(date)
    result.setDate(result.getDate() + days)
    return result
}


/**
 * Get start of day.
 */
export function startOfDay(date: Date): Date {
    const result = new Date(date)
    result.setHours(0, 0, 0, 0)
    return result
}


/**
 * Get end of day.
 */
export function endOfDay(date: Date): Date {
    const result = new Date(date)
    result.setHours(23, 59, 59, 999)
    return result
}


/**
 * Check if two dates are the same day.
 */
export function isSameDay(a: Date, b: Date): boolean {
    return a.getFullYear() === b.getFullYear() &&
        a.getMonth() === b.getMonth() &&
        a.getDate() === b.getDate()
}


/**
 * Calculate days between two dates.
 */
export function daysBetween(a: Date, b: Date): number {
    const diffTime = Math.abs(b.getTime() - a.getTime())
    return Math.round(diffTime / (1000 * 60 * 60 * 24))
}
