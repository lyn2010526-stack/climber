import { create } from 'zustand'
import { devtools, persist } from 'zustand/middleware'


interface SearchItem {
    id: string
    name: string
    createdAt: string
    updatedAt: string
}


interface SearchState {
    items: SearchItem[]
    selectedId: string | null
    loading: boolean
    error: string | null
    filters: Record<string, any>
    sortBy: string
    sortOrder: 'asc' | 'desc'
    pagination: {
        page: number
        pageSize: number
        total: number
    }
}


interface SearchActions {
    setItems: (items: SearchItem[]) => void
    addItem: (item: SearchItem) => void
    updateItem: (id: string, data: Partial<SearchItem>) => void
    removeItem: (id: string) => void
    selectItem: (id: string | null) => void
    setLoading: (loading: boolean) => void
    setError: (error: string | null) => void
    setFilters: (filters: Record<string, any>) => void
    setSort: (sortBy: string, sortOrder: 'asc' | 'desc') => void
    setPagination: (pagination: Partial<{ page: number; pageSize: number; total: number }>) => void
    reset: () => void
}


const initialState: SearchState = {
    items: [],
    selectedId: null,
    loading: false,
    error: null,
    filters: {},
    sortBy: 'createdAt',
    sortOrder: 'desc',
    pagination: {
        page: 1,
        pageSize: 20,
        total: 0,
    },
}


export const useSearchStore = create<SearchState & SearchActions>()(
    devtools(
        persist(
            (set, get) => ({
                ...initialState,

                setItems: (items) => set({ items }),

                addItem: (item) => set((state) => ({
                    items: [...state.items, item],
                })),

                updateItem: (id, data) => set((state) => ({
                    items: state.items.map((item) =>
                        item.id === id ? { ...item, ...data } : item
                    ),
                })),

                removeItem: (id) => set((state) => ({
                    items: state.items.filter((item) => item.id !== id),
                })),

                selectItem: (id) => set({ selectedId: id }),

                setLoading: (loading) => set({ loading }),

                setError: (error) => set({ error }),

                setFilters: (filters) => set({ filters, pagination: { ...get().pagination, page: 1 } }),

                setSort: (sortBy, sortOrder) => set({ sortBy, sortOrder }),

                setPagination: (pagination) => set((state) => ({
                    pagination: { ...state.pagination, ...pagination },
                })),

                reset: () => set(initialState),
            }),
            { name: 'Search-store' }
        )
    )
)
