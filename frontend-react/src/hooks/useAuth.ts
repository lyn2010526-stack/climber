import { useState, useEffect, useCallback, useRef, useMemo } from 'react'


interface AuthConfig {
    enabled?: boolean
    immediate?: boolean
    interval?: number
    retryCount?: number
    retryDelay?: number
    onSuccess?: (data: any) => void
    onError?: (error: Error) => void
    transform?: (data: any) => any
    cacheTime?: number
    staleTime?: number
}


interface AuthState<T> {
    data: T | null
    loading: boolean
    error: Error | null
    stale: boolean
}


interface AuthActions {
    refetch: () => Promise<void>
    reset: () => void
    mutate: (data: any) => void
}


export function useAuth<T = any>(
    key: string,
    fetcher: () => Promise<T>,
    config: AuthConfig = {}
): AuthState<T> & AuthActions {
    const {
        enabled = true,
        immediate = true,
        interval,
        retryCount = 3,
        retryDelay = 1000,
        onSuccess,
        onError,
        transform,
        cacheTime = 5 * 60 * 1000,
        staleTime = 0,
    } = config

    const [state, setState] = useState<AuthState<T>>({
        data: null,
        loading: immediate,
        error: null,
        stale: false,
    })

    const cacheRef = useRef<Map<string, { data: T; timestamp: number }>>(new Map())
    const retryRef = useRef(0)
    const mountedRef = useRef(true)

    const fetchData = useCallback(async () => {
        setState(prev => ({ ...prev, loading: true, error: null }))
        try {
            const cached = cacheRef.current.get(key)
            if (cached && Date.now() - cached.timestamp < staleTime) {
                setState({ data: cached.data, loading: false, error: null, stale: true })
                return
            }
            let result = await fetcher()
            if (transform) {
                result = transform(result)
            }
            if (mountedRef.current) {
                cacheRef.current.set(key, { data: result, timestamp: Date.now() })
                setState({ data: result, loading: false, error: null, stale: false })
                onSuccess?.(result)
            }
        } catch (err) {
            if (mountedRef.current) {
                const error = err instanceof Error ? err : new Error(String(err))
                setState(prev => ({ ...prev, loading: false, error }))
                onError?.(error)
                if (retryRef.current < retryCount) {
                    retryRef.current++
                    setTimeout(fetchData, retryDelay)
                }
            }
        }
    }, [key, fetcher, transform, onSuccess, onError, retryCount, retryDelay, staleTime])

    const reset = useCallback(() => {
        setState({ data: null, loading: false, error: null, stale: false })
        retryRef.current = 0
    }, [])

    const mutate = useCallback((data: T) => {
        cacheRef.current.set(key, { data, timestamp: Date.now() })
        setState(prev => ({ ...prev, data }))
    }, [key])

    useEffect(() => {
        mountedRef.current = true
        if (enabled && immediate) {
            fetchData()
        }
        return () => {
            mountedRef.current = false
        }
    }, [enabled, immediate, fetchData])

    useEffect(() => {
        if (interval && interval > 0) {
            const id = setInterval(fetchData, interval)
            return () => clearInterval(id)
        }
    }, [interval, fetchData])

    return {
        ...state,
        refetch: fetchData,
        reset,
        mutate,
    }
}
