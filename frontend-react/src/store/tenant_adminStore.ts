import { create } from "zustand";
import { devtools, persist } from "zustand/middleware";

export interface TenantAdminState {
  items: TenantAdminItem[];
  selectedId: string | null;
  filter: TenantAdminFilter;
  loading: boolean;
  error: string | null;
}

export interface TenantAdminItem {
  id: string;
  name: string;
  description: string;
  status: string;
  createdAt: string;
  updatedAt: string;
}

export interface TenantAdminFilter {
  search: string;
  status: string | null;
  sortBy: string;
  sortOrder: "asc" | "desc";
  page: number;
  pageSize: number;
}

export interface TenantAdminActions {
  setItems: (items: TenantAdminItem[]) => void;
  addItem: (item: TenantAdminItem) => void;
  updateItem: (id: string, updates: Partial<TenantAdminItem>) => void;
  removeItem: (id: string) => void;
  selectItem: (id: string | null) => void;
  setFilter: (filter: Partial<TenantAdminFilter>) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  reset: () => void;
}

const initialFilter: TenantAdminFilter = {
  search: "",
  status: null,
  sortBy: "createdAt",
  sortOrder: "desc",
  page: 1,
  pageSize: 10,
};

const initialState: TenantAdminState = {
  items: [],
  selectedId: null,
  filter: initialFilter,
  loading: false,
  error: null,
};

export const useTenantAdminStore = create<TenantAdminState & TenantAdminActions>()(
  devtools(
    persist(
      (set) => ({
        ...initialState,
        setItems: (items) => set({ items }),
        addItem: (item) => set((state) => ({ items: [item, ...state.items] })),
        updateItem: (id, updates) =>
          set((state) => ({
            items: state.items.map((item) =>
              item.id === id ? { ...item, ...updates } : item
            ),
          })),
        removeItem: (id) =>
          set((state) => ({ items: state.items.filter((item) => item.id !== id) })),
        selectItem: (id) => set({ selectedId: id }),
        setFilter: (filter) =>
          set((state) => ({ filter: { ...state.filter, ...filter } })),
        setLoading: (loading) => set({ loading }),
        setError: (error) => set({ error }),
        reset: () => set(initialState),
      }),
      { name: "tenant_admin-store" }
    )
  )
);

export const selectFilteredItems = (state: TenantAdminState): TenantAdminItem[] => {
  let items = [...state.items];
  if (state.filter.search) {
    const search = state.filter.search.toLowerCase();
    items = items.filter(
      (item) =>
        item.name.toLowerCase().includes(search) ||
        item.description.toLowerCase().includes(search)
    );
  }
  if (state.filter.status) {
    items = items.filter((item) => item.status === state.filter.status);
  }
  items.sort((a, b) => {
    const aVal = String(a[state.filter.sortBy as keyof TenantAdminItem] || "");
    const bVal = String(b[state.filter.sortBy as keyof TenantAdminItem] || "");
    const cmp = aVal.localeCompare(bVal);
    return state.filter.sortOrder === "asc" ? cmp : -cmp;
  });
  return items;
};

export const selectPaginatedItems = (state: TenantAdminState): TenantAdminItem[] => {
  const filtered = selectFilteredItems(state);
  const start = (state.filter.page - 1) * state.filter.pageSize;
  return filtered.slice(start, start + state.filter.pageSize);
};
