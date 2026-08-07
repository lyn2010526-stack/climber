import { create } from 'zustand'
import { devtools, persist } from 'zustand/middleware'


interface AuditState {
    items: any[]
    selectedId: string | null
    loading: boolean
    error: string | null
    filters: Record<string, any>
    pagination: {
        page: number
        pageSize: number
        total: number
    }
}


interface AuditActions {
    setItems: (items: any[]) => void
    addItem: (item: any) => void
    updateItem: (id: string, data: any) => void
    removeItem: (id: string) => void
    selectItem: (id: string | null) => void
    setLoading: (loading: boolean) => void
    setError: (error: string | null) => void
    setFilters: (filters: Record<string, any>) => void
    setPagination: (pagination: Partial<{ page: number; pageSize: number; total: number }>) => void
    reset: () => void
}


const initialState: AuditState = {
    items: [],
    selectedId: null,
    loading: false,
    error: null,
    filters: {},
    pagination: {
        page: 1,
        pageSize: 20,
        total: 0,
    },
}


export const useAuditStore = create<AuditState & AuditActions>()(
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

                setFilters: (filters) => set({ filters }),

                setPagination: (pagination) => set((state) => ({
                    pagination: { ...state.pagination, ...pagination },
                })),

                reset: () => set(initialState),
            }),
            { name: 'Audit-store' }
        )
    )
)
