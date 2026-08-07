#!/usr/bin/env python3
"""Bulk frontend component generator for expansion."""

from __future__ import annotations

from pathlib import Path

BASE = Path("/workspace/agent-engine")


def write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def gen_page(name: str, class_name: str) -> str:
    """Generate a page component."""
    tmpl = """import React, { useState, useEffect, useCallback, useMemo } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";

export interface %(cn)sItem {
  id: string;
  name: string;
  description: string;
  status: "active" | "inactive" | "pending" | "archived";
  createdAt: string;
  updatedAt: string;
  metadata?: Record<string, unknown>;
}

export interface %(cn)sFilter {
  search?: string;
  status?: string;
  sortBy?: string;
  sortOrder?: "asc" | "desc";
  page: number;
  pageSize: number;
}

export interface %(cn)sStats {
  total: number;
  active: number;
  inactive: number;
  pending: number;
}

const mockItems: %(cn)sItem[] = Array.from({ length: 25 }, (_, i) => ({
  id: `item-${i + 1}`,
  name: `Item ${i + 1}`,
  description: `Description for item ${i + 1}`,
  status: (["active", "inactive", "pending", "archived"] as const)[i %% 4],
  createdAt: new Date(Date.now() - i * 86400000).toISOString(),
  updatedAt: new Date(Date.now() - i * 43200000).toISOString(),
}));

export const %(cn)sPage: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const [items, setItems] = useState<%(cn)sItem[]>(mockItems);
  const [loading, setLoading] = useState(false);
  const [selectedItems, setSelectedItems] = useState<Set<string>>(new Set());
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showFilterPanel, setShowFilterPanel] = useState(false);

  const [filter, setFilter] = useState<%(cn)sFilter>({
    search: searchParams.get("search") || "",
    status: searchParams.get("status") || undefined,
    sortBy: searchParams.get("sortBy") || "createdAt",
    sortOrder: (searchParams.get("sortOrder") as "asc" | "desc") || "desc",
    page: parseInt(searchParams.get("page") || "1", 10),
    pageSize: parseInt(searchParams.get("pageSize") || "10", 10),
  });

  const filteredItems = useMemo(() => {
    let result = [...items];
    if (filter.search) {
      const search = filter.search.toLowerCase();
      result = result.filter(
        (item) => item.name.toLowerCase().includes(search) || item.description.toLowerCase().includes(search)
      );
    }
    if (filter.status) {
      result = result.filter((item) => item.status === filter.status);
    }
    result.sort((a, b) => {
      const aVal = a[filter.sortBy as keyof %(cn)sItem] || "";
      const bVal = b[filter.sortBy as keyof %(cn)sItem] || "";
      const cmp = String(aVal).localeCompare(String(bVal));
      return filter.sortOrder === "asc" ? cmp : -cmp;
    });
    return result;
  }, [items, filter]);

  const paginatedItems = useMemo(() => {
    const start = (filter.page - 1) * filter.pageSize;
    return filteredItems.slice(start, start + filter.pageSize);
  }, [filteredItems, filter]);

  const stats: %(cn)sStats = useMemo(() => ({
    total: items.length,
    active: items.filter((i) => i.status === "active").length,
    inactive: items.filter((i) => i.status === "inactive").length,
    pending: items.filter((i) => i.status === "pending").length,
  }), [items]);

  const handleSearch = useCallback((search: string) => {
    setFilter((f) => ({ ...f, search, page: 1 }));
    setSearchParams((prev) => {
      if (search) prev.set("search", search);
      else prev.delete("search");
      return prev;
    });
  }, [setSearchParams]);

  const handleStatusFilter = useCallback((status: string) => {
    setFilter((f) => ({ ...f, status: status || undefined, page: 1 }));
  }, []);

  const handleSort = useCallback((sortBy: string) => {
    setFilter((f) => ({
      ...f,
      sortBy,
      sortOrder: f.sortBy === sortBy && f.sortOrder === "asc" ? "desc" : "asc",
    }));
  }, []);

  const handleSelectItem = useCallback((id: string) => {
    setSelectedItems((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }, []);

  const handleSelectAll = useCallback(() => {
    if (selectedItems.size === paginatedItems.length) {
      setSelectedItems(new Set());
    } else {
      setSelectedItems(new Set(paginatedItems.map((i) => i.id)));
    }
  }, [selectedItems.size, paginatedItems]);

  const handleDelete = useCallback((id: string) => {
    setItems((prev) => prev.filter((item) => item.id !== id));
  }, []);

  const handleBulkDelete = useCallback(() => {
    setItems((prev) => prev.filter((item) => !selectedItems.has(item.id)));
    setSelectedItems(new Set());
  }, [selectedItems]);

  const handleCreate = useCallback((data: Partial<%(cn)sItem>) => {
    const newItem: %(cn)sItem = {
      id: `item-${Date.now()}`,
      name: data.name || "New Item",
      description: data.description || "",
      status: data.status || "pending",
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };
    setItems((prev) => [newItem, ...prev]);
    setShowCreateModal(false);
  }, []);

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 py-8">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">%(cn)s</h1>
            <p className="text-sm text-gray-500 mt-1">Manage your %(n)s items</p>
          </div>
          <button
            onClick={() => setShowCreateModal(true)}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
          >
            Create New
          </button>
        </div>
        <div className="grid grid-cols-4 gap-4 mb-6">
          <div className="bg-white rounded-lg border p-4">
            <div className="text-sm text-gray-500">Total</div>
            <div className="text-2xl font-bold">{stats.total}</div>
          </div>
          <div className="bg-white rounded-lg border p-4">
            <div className="text-sm text-gray-500">Active</div>
            <div className="text-2xl font-bold text-green-600">{stats.active}</div>
          </div>
          <div className="bg-white rounded-lg border p-4">
            <div className="text-sm text-gray-500">Inactive</div>
            <div className="text-2xl font-bold text-gray-600">{stats.inactive}</div>
          </div>
          <div className="bg-white rounded-lg border p-4">
            <div className="text-sm text-gray-500">Pending</div>
            <div className="text-2xl font-bold text-yellow-600">{stats.pending}</div>
          </div>
        </div>
        <div className="bg-white rounded-lg border">
          <div className="p-4 border-b flex items-center gap-4">
            <input
              type="text"
              placeholder="Search..."
              value={filter.search}
              onChange={(e) => handleSearch(e.target.value)}
              className="flex-1 px-3 py-2 border rounded-md"
            />
            <select
              value={filter.status || ""}
              onChange={(e) => handleStatusFilter(e.target.value)}
              className="px-3 py-2 border rounded-md"
            >
              <option value="">All Status</option>
              <option value="active">Active</option>
              <option value="inactive">Inactive</option>
              <option value="pending">Pending</option>
              <option value="archived">Archived</option>
            </select>
          </div>
          <div className="divide-y">
            {paginatedItems.map((item) => (
              <div key={item.id} className="p-4 flex items-center gap-4 hover:bg-gray-50">
                <input
                  type="checkbox"
                  checked={selectedItems.has(item.id)}
                  onChange={() => handleSelectItem(item.id)}
                  className="h-4 w-4 rounded border-gray-300"
                />
                <div className="flex-1">
                  <div className="font-medium">{item.name}</div>
                  <div className="text-sm text-gray-500">{item.description}</div>
                </div>
                <span className="px-2 py-1 text-xs rounded-full bg-gray-100">
                  {item.status}
                </span>
                <button
                  onClick={() => handleDelete(item.id)}
                  className="text-red-500 hover:text-red-700"
                >
                  Delete
                </button>
              </div>
            ))}
          </div>
          <div className="p-4 border-t flex items-center justify-between">
            <span className="text-sm text-gray-500">
              Showing {paginatedItems.length} of {filteredItems.length}
            </span>
            <div className="flex gap-2">
              <button
                disabled={filter.page === 1}
                onClick={() => setFilter((f) => ({ ...f, page: f.page - 1 }))}
                className="px-3 py-1 border rounded disabled:opacity-50"
              >
                Prev
              </button>
              <button
                disabled={filter.page * filter.pageSize >= filteredItems.length}
                onClick={() => setFilter((f) => ({ ...f, page: f.page + 1 }))}
                className="px-3 py-1 border rounded disabled:opacity-50"
              >
                Next
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default %(cn)sPage;
"""
    return tmpl % {"cn": class_name, "n": name}


def gen_hook(name: str, class_name: str) -> str:
    """Generate a custom hook."""
    tmpl = """import { useState, useEffect, useCallback, useRef } from "react";

export interface %(cn)sHookOptions {
  autoFetch?: boolean;
  pollingInterval?: number;
  retryCount?: number;
  retryDelay?: number;
  cacheTime?: number;
  onSuccess?: (data: unknown) => void;
  onError?: (error: Error) => void;
}

export interface %(cn)sHookResult<T> {
  data: T | null;
  loading: boolean;
  error: Error | null;
  refetch: () => Promise<void>;
  reset: () => void;
  isStale: boolean;
  lastFetchedAt: Date | null;
}

const cache = new Map<string, { data: unknown; timestamp: number }>();

export function use%(cn)s<T = unknown>(
  key: string,
  fetcher: () => Promise<T>,
  options: %(cn)sHookOptions = {}
): %(cn)sHookResult<T> {
  const {
    autoFetch = true,
    pollingInterval,
    retryCount = 3,
    retryDelay = 1000,
    cacheTime = 300000,
    onSuccess,
    onError,
  } = options;

  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(autoFetch);
  const [error, setError] = useState<Error | null>(null);
  const [lastFetchedAt, setLastFetchedAt] = useState<Date | null>(null);
  const mountedRef = useRef(true);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await fetcher();
      if (!mountedRef.current) return;
      setData(result);
      setLastFetchedAt(new Date());
      onSuccess?.(result);
    } catch (err) {
      if (!mountedRef.current) return;
      const error = err instanceof Error ? err : new Error(String(err));
      setError(error);
      onError?.(error);
    } finally {
      if (mountedRef.current) setLoading(false);
    }
  }, [fetcher, onSuccess, onError]);

  const refetch = useCallback(async () => {
    cache.delete(key);
    await fetchData();
  }, [key, fetchData]);

  const reset = useCallback(() => {
    setData(null);
    setError(null);
    setLoading(false);
    setLastFetchedAt(null);
  }, []);

  useEffect(() => {
    mountedRef.current = true;
    if (autoFetch) fetchData();
    return () => { mountedRef.current = false; };
  }, [autoFetch, fetchData]);

  useEffect(() => {
    if (!pollingInterval) return;
    const interval = setInterval(() => {
      if (!loading) refetch();
    }, pollingInterval);
    return () => clearInterval(interval);
  }, [pollingInterval, loading, refetch]);

  return { data, loading, error, refetch, reset, isStale: false, lastFetchedAt };
}

export function use%(cn)sMutation<T = unknown, V = unknown>(
  mutator: (variables: V) => Promise<T>
) {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const mutate = useCallback(async (variables: V) => {
    setLoading(true);
    setError(null);
    try {
      const result = await mutator(variables);
      setData(result);
      return result;
    } catch (err) {
      const error = err instanceof Error ? err : new Error(String(err));
      setError(error);
      throw error;
    } finally {
      setLoading(false);
    }
  }, [mutator]);

  const reset = useCallback(() => {
    setData(null);
    setError(null);
    setLoading(false);
  }, []);

  return { mutate, data, loading, error, reset };
}
"""
    return tmpl % {"cn": class_name}


def gen_store(name: str, class_name: str) -> str:
    """Generate a Zustand store."""
    tmpl = """import { create } from "zustand";
import { devtools, persist } from "zustand/middleware";

export interface %(cn)sState {
  items: %(cn)sItem[];
  selectedId: string | null;
  filter: %(cn)sFilter;
  loading: boolean;
  error: string | null;
}

export interface %(cn)sItem {
  id: string;
  name: string;
  description: string;
  status: string;
  createdAt: string;
  updatedAt: string;
}

export interface %(cn)sFilter {
  search: string;
  status: string | null;
  sortBy: string;
  sortOrder: "asc" | "desc";
  page: number;
  pageSize: number;
}

export interface %(cn)sActions {
  setItems: (items: %(cn)sItem[]) => void;
  addItem: (item: %(cn)sItem) => void;
  updateItem: (id: string, updates: Partial<%(cn)sItem>) => void;
  removeItem: (id: string) => void;
  selectItem: (id: string | null) => void;
  setFilter: (filter: Partial<%(cn)sFilter>) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  reset: () => void;
}

const initialFilter: %(cn)sFilter = {
  search: "",
  status: null,
  sortBy: "createdAt",
  sortOrder: "desc",
  page: 1,
  pageSize: 10,
};

const initialState: %(cn)sState = {
  items: [],
  selectedId: null,
  filter: initialFilter,
  loading: false,
  error: null,
};

export const use%(cn)sStore = create<%(cn)sState & %(cn)sActions>()(
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
      { name: "%(n)s-store" }
    )
  )
);

export const selectFilteredItems = (state: %(cn)sState): %(cn)sItem[] => {
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
    const aVal = String(a[state.filter.sortBy as keyof %(cn)sItem] || "");
    const bVal = String(b[state.filter.sortBy as keyof %(cn)sItem] || "");
    const cmp = aVal.localeCompare(bVal);
    return state.filter.sortOrder === "asc" ? cmp : -cmp;
  });
  return items;
};

export const selectPaginatedItems = (state: %(cn)sState): %(cn)sItem[] => {
  const filtered = selectFilteredItems(state);
  const start = (state.filter.page - 1) * state.filter.pageSize;
  return filtered.slice(start, start + state.filter.pageSize);
};
"""
    return tmpl % {"cn": class_name, "n": name}


def main() -> None:
    all_files: dict[str, str] = {}

    modules = [
        ("agent_config", "Agent configuration"),
        ("session_history", "Session history"),
        ("model_catalog", "Model catalog"),
        ("prompt_editor", "Prompt editor"),
        ("workflow_designer", "Workflow designer"),
        ("knowledge_explorer", "Knowledge explorer"),
        ("analytics_dashboard", "Analytics dashboard"),
        ("user_admin", "User admin"),
        ("billing_overview", "Billing overview"),
        ("settings_panel", "Settings panel"),
        ("integration_manager", "Integration manager"),
        ("deployment_center", "Deployment center"),
        ("monitoring_center", "Monitoring center"),
        ("alert_center", "Alert center"),
        ("log_viewer", "Log viewer"),
        ("task_board", "Task board"),
        ("report_center", "Report center"),
        ("dataset_browser", "Dataset browser"),
        ("experiment_lab", "Experiment lab"),
        ("model_playground", "Model playground"),
        ("collaboration_hub", "Collaboration hub"),
        ("notification_feed", "Notification feed"),
        ("search_center", "Search center"),
        ("file_manager", "File manager"),
        ("api_explorer", "API explorer"),
        ("security_center", "Security center"),
        ("audit_viewer", "Audit viewer"),
        ("template_gallery", "Template gallery"),
        ("plugin_marketplace", "Plugin marketplace"),
        ("tenant_admin", "Tenant admin"),
    ]

    print(f"Generating {len(modules)} frontend modules...")

    for name, _desc in modules:
        class_name = "".join(w.capitalize() for w in name.split("_"))

        page_content = gen_page(name, class_name)
        all_files[f"frontend-react/src/pages/{name}.tsx"] = page_content

        hook_content = gen_hook(name, class_name)
        all_files[f"frontend-react/src/hooks/use{name}.ts"] = hook_content

        store_content = gen_store(name, class_name)
        all_files[f"frontend-react/src/store/{name}Store.ts"] = store_content

    print(f"Writing {len(all_files)} files...")
    for path_str, content in all_files.items():
        write_file(BASE / path_str, content)

    print(f"Done! Generated {len(all_files)} frontend files across {len(modules)} modules.")


if __name__ == "__main__":
    main()
