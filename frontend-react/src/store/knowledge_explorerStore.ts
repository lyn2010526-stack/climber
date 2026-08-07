import { create } from "zustand";
import { devtools, persist } from "zustand/middleware";

export interface KnowledgeExplorerState {
  items: KnowledgeExplorerItem[];
  selectedId: string | null;
  filter: KnowledgeExplorerFilter;
  loading: boolean;
  error: string | null;
}

export interface KnowledgeExplorerItem {
  id: string;
  name: string;
  description: string;
  status: string;
  createdAt: string;
  updatedAt: string;
}

export interface KnowledgeExplorerFilter {
  search: string;
  status: string | null;
  sortBy: string;
  sortOrder: "asc" | "desc";
  page: number;
  pageSize: number;
}

export interface KnowledgeExplorerActions {
  setItems: (items: KnowledgeExplorerItem[]) => void;
  addItem: (item: KnowledgeExplorerItem) => void;
  updateItem: (id: string, updates: Partial<KnowledgeExplorerItem>) => void;
  removeItem: (id: string) => void;
  selectItem: (id: string | null) => void;
  setFilter: (filter: Partial<KnowledgeExplorerFilter>) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  reset: () => void;
}

const initialFilter: KnowledgeExplorerFilter = {
  search: "",
  status: null,
  sortBy: "createdAt",
  sortOrder: "desc",
  page: 1,
  pageSize: 10,
};

const initialState: KnowledgeExplorerState = {
  items: [],
  selectedId: null,
  filter: initialFilter,
  loading: false,
  error: null,
};

export const useKnowledgeExplorerStore = create<KnowledgeExplorerState & KnowledgeExplorerActions>()(
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
      { name: "knowledge_explorer-store" }
    )
  )
);

export const selectFilteredItems = (state: KnowledgeExplorerState): KnowledgeExplorerItem[] => {
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
    const aVal = String(a[state.filter.sortBy as keyof KnowledgeExplorerItem] || "");
    const bVal = String(b[state.filter.sortBy as keyof KnowledgeExplorerItem] || "");
    const cmp = aVal.localeCompare(bVal);
    return state.filter.sortOrder === "asc" ? cmp : -cmp;
  });
  return items;
};

export const selectPaginatedItems = (state: KnowledgeExplorerState): KnowledgeExplorerItem[] => {
  const filtered = selectFilteredItems(state);
  const start = (state.filter.page - 1) * state.filter.pageSize;
  return filtered.slice(start, start + state.filter.pageSize);
};
