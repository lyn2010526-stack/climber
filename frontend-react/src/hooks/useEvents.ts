// @ts-nocheck
import { useState, useEffect, useCallback, useRef, useMemo } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'

import { apiClient } from '@/lib/api-client'
import { useToast } from '@/hooks/useToast'
import { useAuth } from '@/hooks/useAuth'


interface EventsState {
    data: any | null
    loading: boolean
    error: Error | null
    page: number
    pageSize: number
    total: number
    filters: Record<string, any>
    sortBy: string
    sortOrder: 'asc' | 'desc'
    selectedIds: number[]
    isCreating: boolean
    isUpdating: boolean
    isDeleting: boolean
}


interface EventsActions {
    fetch: (params?: any) => Promise<void>
    create: (data: any) => Promise<any>
    update: (id: number, data: any) => Promise<any>
    remove: (id: number) => Promise<boolean>
    setPage: (page: number) => void
    setPageSize: (size: number) => void
    setFilters: (filters: Record<string, any>) => void
    setSorting: (sortBy: string, sortOrder: 'asc' | 'desc') => void
    selectItem: (id: number, selected: boolean) => void
    selectAll: (selected: boolean) => void
    resetFilters: () => void
    refresh: () => void
}


type EventsHookReturn = EventsState & EventsActions


export function useEvents(initialFilters?: Record<string, any>): EventsHookReturn {
    const { showToast } = useToast()
    const { user } = useAuth()
    const queryClient = useQueryClient()
    const abortControllerRef = useRef<AbortController | null>(null)

    const [state, setState] = useState<EventsState>({
        data: null,
        loading: false,
        error: null,
        page: 1,
        pageSize: 20,
        total: 0,
        filters: initialFilters || {},
        sortBy: 'created_at',
        sortOrder: 'desc',
        selectedIds: [],
        isCreating: false,
        isUpdating: false,
        isDeleting: false,
    })

    const { data, isLoading, error, refetch } = useQuery({
        queryKey: ['events', state.page, state.pageSize, state.filters, state.sortBy, state.sortOrder],
        queryFn: async () => {
            abortControllerRef.current?.abort()
            abortControllerRef.current = new AbortController()
            const response = await apiClient.get('/events', {
                params: {
                    page: state.page,
                    page_size: state.pageSize,
                    ...state.filters,
                    sort_by: state.sortBy,
                    sort_order: state.sortOrder,
                },
                signal: abortControllerRef.current.signal,
            })
            return response.data
        },
        staleTime: 30000,
    })

    const createMutation = useMutation({
        mutationFn: async (data: any) => {
            setState(prev => ({ ...prev, isCreating: true }))
            const response = await apiClient.post('/events', data)
            return response.data
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['events'] })
            showToast({ type: 'success', message: 'Created successfully' })
        },
        onError: (err: Error) => {
            showToast({ type: 'error', message: err.message })
        },
        onSettled: () => {
            setState(prev => ({ ...prev, isCreating: false }))
        },
    })

    const updateMutation = useMutation({
        mutationFn: async ({ id, data }: { id: number; data: any }) => {
            setState(prev => ({ ...prev, isUpdating: true }))
            const response = await apiClient.put('/events/' + id, data)
            return response.data
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['events'] })
            showToast({ type: 'success', message: 'Updated successfully' })
        },
        onError: (err: Error) => {
            showToast({ type: 'error', message: err.message })
        },
        onSettled: () => {
            setState(prev => ({ ...prev, isUpdating: false }))
        },
    })

    const deleteMutation = useMutation({
        mutationFn: async (id: number) => {
            setState(prev => ({ ...prev, isDeleting: true }))
            await apiClient.delete('/events/' + id)
            return id
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['events'] })
            showToast({ type: 'success', message: 'Deleted successfully' })
        },
        onError: (err: Error) => {
            showToast({ type: 'error', message: err.message })
        },
        onSettled: () => {
            setState(prev => ({ ...prev, isDeleting: false }))
        },
    })

    const fetch = useCallback(async (params?: any) => {
        await refetch()
    }, [refetch])

    const create = useCallback(async (data: any) => {
        return createMutation.mutateAsync(data)
    }, [createMutation])

    const update = useCallback(async (id: number, data: any) => {
        return updateMutation.mutateAsync({ id, data })
    }, [updateMutation])

    const remove = useCallback(async (id: number) => {
        return deleteMutation.mutateAsync(id)
    }, [deleteMutation])

    const setPage = useCallback((page: number) => {
        setState(prev => ({ ...prev, page }))
    }, [])

    const setPageSize = useCallback((pageSize: number) => {
        setState(prev => ({ ...prev, pageSize, page: 1 }))
    }, [])

    const setFilters = useCallback((filters: Record<string, any>) => {
        setState(prev => ({ ...prev, filters, page: 1 }))
    }, [])

    const setSorting = useCallback((sortBy: string, sortOrder: 'asc' | 'desc') => {
        setState(prev => ({ ...prev, sortBy, sortOrder }))
    }, [])

    const selectItem = useCallback((id: number, selected: boolean) => {
        setState(prev => ({
            ...prev,
            selectedIds: selected
                ? [...prev.selectedIds, id]
                : prev.selectedIds.filter(i => i !== id),
        }))
    }, [])

    const selectAll = useCallback((selected: boolean) => {
        if (selected && data?.items) {
            setState(prev => ({ ...prev, selectedIds: data.items.map((i: any) => i.id) }))
        } else {
            setState(prev => ({ ...prev, selectedIds: [] }))
        }
    }, [data])

    const resetFilters = useCallback(() => {
        setState(prev => ({ ...prev, filters: {}, page: 1 }))
    }, [])

    const refresh = useCallback(() => {
        refetch()
    }, [refetch])

    useEffect(() => {
        return () => {
            abortControllerRef.current?.abort()
        }
    }, [])

    return {
        ...state,
        data,
        loading: isLoading,
        error,
        fetch,
        create,
        update,
        remove,
        setPage,
        setPageSize,
        setFilters,
        setSorting,
        selectItem,
        selectAll,
        resetFilters,
        refresh,
    }
}
