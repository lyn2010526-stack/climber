import { create } from "zustand";
import { devtools, persist } from "zustand/middleware";

export interface ExperimentLabState {
  items: ExperimentLabItem[];
  selectedId: string | null;
  filter: ExperimentLabFilter;
  loading: boolean;
  error: string | null;
}

export interface ExperimentLabItem {
  id: string;
  name: string;
  description: string;
  status: string;
  createdAt: string;
  updatedAt: string;
}

export interface ExperimentLabFilter {
  search: string;
  status: string | null;
  sortBy: string;
  sortOrder: "asc" | "desc";
  page: number;
  pageSize: number;
}

export interface ExperimentLabActions {
  setItems: (items: ExperimentLabItem[]) => void;
  addItem: (item: ExperimentLabItem) => void;
  updateItem: (id: string, updates: Partial<ExperimentLabItem>) => void;
  removeItem: (id: string) => void;
  selectItem: (id: string | null) => void;
  setFilter: (filter: Partial<ExperimentLabFilter>) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  reset: () => void;
}

const initialFilter: ExperimentLabFilter = {
  search: "",
  status: null,
  sortBy: "createdAt",
  sortOrder: "desc",
  page: 1,
  pageSize: 10,
};

const initialState: ExperimentLabState = {
  items: [],
  selectedId: null,
  filter: initialFilter,
  loading: false,
  error: null,
};

export const useExperimentLabStore = create<ExperimentLabState & ExperimentLabActions>()(
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
      { name: "experiment_lab-store" }
    )
  )
);

export const selectFilteredItems = (state: ExperimentLabState): ExperimentLabItem[] => {
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
    const aVal = String(a[state.filter.sortBy as keyof ExperimentLabItem] || "");
    const bVal = String(b[state.filter.sortBy as keyof ExperimentLabItem] || "");
    const cmp = aVal.localeCompare(bVal);
    return state.filter.sortOrder === "asc" ? cmp : -cmp;
  });
  return items;
};

export const selectPaginatedItems = (state: ExperimentLabState): ExperimentLabItem[] => {
  const filtered = selectFilteredItems(state);
  const start = (state.filter.page - 1) * state.filter.pageSize;
  return filtered.slice(start, start + state.filter.pageSize);
};
