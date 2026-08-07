import { create } from 'zustand'
import { devtools } from 'zustand/middleware'
import { immer } from 'zustand/middleware/immer'


interface ActionItem {
    id: number
    name: string
    description: string
    status: 'active' | 'inactive' | 'pending'
    priority: 'low' | 'medium' | 'high' | 'critical'
    createdAt: string
    updatedAt: string
    metadata: Record<string, any>
}


interface ActionFilters {
    search: string
    status: string | null
    priority: string | null
    sortBy: string
    sortOrder: 'asc' | 'desc'
    page: number
    pageSize: number
}


interface ActionState {
    items: ActionItem[]
    selectedId: number | null
    filters: ActionFilters
    loading: boolean
    error: string | null
    total: number

    // Actions
    setItems: (items: ActionItem[]) => void
    addItem: (item: ActionItem) => void
    updateItem: (id: number, data: Partial<ActionItem>) => void
    removeItem: (id: number) => void
    selectItem: (id: number | null) => void

    setSearch: (search: string) => void
    setStatusFilter: (status: string | null) => void
    setPriorityFilter: (priority: string | null) => void
    setSorting: (sortBy: string, sortOrder: 'asc' | 'desc') => void
    setPage: (page: number) => void
    setPageSize: (size: number) => void
    resetFilters: () => void

    setLoading: (loading: boolean) => void
    setError: (error: string | null) => void
    setTotal: (total: number) => void

    // Computed
    getFilteredItems: () => ActionItem[]
    getSelectedItem: () => ActionItem | null
    getItemById: (id: number) => ActionItem | undefined
}


const defaultFilters: ActionFilters = {
    search: '',
    status: null,
    priority: null,
    sortBy: 'createdAt',
    sortOrder: 'desc',
    page: 1,
    pageSize: 20,
}


export const useActionStore = create<ActionState>()(
    devtools(
        immer((set, get) => ({
            items: [],
            selectedId: null,
            filters: defaultFilters,
            loading: false,
            error: null,
            total: 0,

            setItems: (items) => set({ items }),

            addItem: (item) => set((state) => {
                state.items.push(item)
                state.total += 1
            }),

            updateItem: (id, data) => set((state) => {
                const index = state.items.findIndex((item: ActionItem) => item.id === id)
                if (index !== -1) {
                    state.items[index] = { ...state.items[index], ...data } as ActionItem
                }
            }),

            removeItem: (id) => set((state) => {
                state.items = state.items.filter((item: ActionItem) => item.id !== id)
                state.total = Math.max(0, state.total - 1)
                if (state.selectedId === id) {
                    state.selectedId = null
                }
            }),

            selectItem: (id) => set({ selectedId: id }),

            setSearch: (search) => set((state) => {
                state.filters.search = search
                state.filters.page = 1
            }),

            setStatusFilter: (status) => set((state) => {
                state.filters.status = status
                state.filters.page = 1
            }),

            setPriorityFilter: (priority) => set((state) => {
                state.filters.priority = priority
                state.filters.page = 1
            }),

            setSorting: (sortBy, sortOrder) => set((state) => {
                state.filters.sortBy = sortBy
                state.filters.sortOrder = sortOrder
            }),

            setPage: (page) => set((state) => {
                state.filters.page = page
            }),

            setPageSize: (pageSize) => set((state) => {
                state.filters.pageSize = pageSize
                state.filters.page = 1
            }),

            resetFilters: () => set({ filters: defaultFilters }),

            setLoading: (loading) => set({ loading }),
            setError: (error) => set({ error }),
            setTotal: (total) => set({ total }),

            getFilteredItems: () => {
                const { items, filters } = get()
                let filtered = [...items]

                if (filters.search) {
                    const search = filters.search.toLowerCase()
                    filtered = filtered.filter((item: ActionItem) =>
                        item.name.toLowerCase().includes(search) ||
                        item.description.toLowerCase().includes(search)
                    )
                }

                if (filters.status) {
                    filtered = filtered.filter((item: ActionItem) => item.status === filters.status)
                }

                if (filters.priority) {
                    filtered = filtered.filter((item: ActionItem) => item.priority === filters.priority)
                }

                return filtered
            },

            getSelectedItem: () => {
                const { items, selectedId } = get()
                return items.find(item => item.id === selectedId) || null
            },

            getItemById: (id) => {
                return get().items.find(item => item.id === id)
            },
        })),
        { name: 'ActionStore' },
    )
)
