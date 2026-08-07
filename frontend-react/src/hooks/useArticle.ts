import { useState, useEffect, useCallback, useRef, useMemo } from 'react'


interface ArticleState<T> {
    data: T | null
    loading: boolean
    error: Error | null
}


interface ArticleOptions {
    autoFetch?: boolean
    refreshInterval?: number
    retryCount?: number
    retryDelay?: number
    onSuccess?: (data: any) => void
    onError?: (error: Error) => void
}


interface ArticleActions<T> {
    refetch: () => Promise<void>
    reset: () => void
    setData: (data: T) => void
    invalidate: () => void
}


export function useArticle<T = any>(
    key: string,
    fetcher: () => Promise<T>,
    options: ArticleOptions = {}
): ArticleState<T> & ArticleActions<T> {
    const {
        autoFetch = true,
        refreshInterval,
        retryCount = 3,
        retryDelay = 1000,
        onSuccess,
        onError,
    } = options

    const [state, setState] = useState<ArticleState<T>>({
        data: null,
        loading: autoFetch,
        error: null,
    })

    const mountedRef = useRef(true)
    const retryCountRef = useRef(0)
    const cacheRef = useRef<Map<string, T>>(new Map())

    const fetchData = useCallback(async () => {
        setState(prev => ({ ...prev, loading: true, error: null }))
        try {
            const cached = cacheRef.current.get(key)
            if (cached) {
                setState({ data: cached, loading: false, error: null })
                onSuccess?.(cached)
                return
            }
            const data = await fetcher()
            if (mountedRef.current) {
                cacheRef.current.set(key, data)
                setState({ data, loading: false, error: null })
                onSuccess?.(data)
            }
        } catch (err) {
            if (mountedRef.current) {
                const error = err instanceof Error ? err : new Error(String(err))
                setState(prev => ({ ...prev, loading: false, error }))
                onError?.(error)
                if (retryCountRef.current < retryCount) {
                    retryCountRef.current++
                    setTimeout(fetchData, retryDelay)
                }
            }
        }
    }, [key, fetcher, onSuccess, onError, retryCount, retryDelay])

    const reset = useCallback(() => {
        setState({ data: null, loading: false, error: null })
        retryCountRef.current = 0
    }, [])

    const setData = useCallback((data: T) => {
        cacheRef.current.set(key, data)
        setState(prev => ({ ...prev, data }))
    }, [key])

    const invalidate = useCallback(() => {
        cacheRef.current.delete(key)
        fetchData()
    }, [key, fetchData])

    useEffect(() => {
        if (autoFetch) {
            fetchData()
        }
        return () => {
            mountedRef.current = false
        }
    }, [autoFetch, fetchData])

    useEffect(() => {
        if (refreshInterval && refreshInterval > 0) {
            const id = setInterval(fetchData, refreshInterval)
            return () => clearInterval(id)
        }
    }, [refreshInterval, fetchData])

    return {
        ...state,
        refetch: fetchData,
        reset,
        setData,
        invalidate,
    }
}
