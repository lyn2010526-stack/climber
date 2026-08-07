import React, { useState, useCallback, useMemo } from 'react'


interface FormBuilderProps {
    title?: string
    subtitle?: string
    loading?: boolean
    error?: string | null
    data?: any[]
    onAction?: (action: string, data?: any) => void
    className?: string
    variant?: 'default' | 'compact' | 'expanded'
    disabled?: boolean
    children?: React.ReactNode
}


interface FormBuilderState {
    isExpanded: boolean
    activeTab: string
    searchQuery: string
    selectedItems: number[]
    sortColumn: string
    sortDirection: 'asc' | 'desc'
    showFilters: boolean
    showActions: boolean
    isRefreshing: boolean
    lastUpdated: Date | null
}


const initialState: FormBuilderState = {
    isExpanded: true,
    activeTab: 'all',
    searchQuery: '',
    selectedItems: [],
    sortColumn: 'name',
    sortDirection: 'asc',
    showFilters: false,
    showActions: false,
    isRefreshing: false,
    lastUpdated: null,
}


export const FormBuilder: React.FC<FormBuilderProps> = ({
    title = 'FormBuilder',
    subtitle,
    loading = false,
    error = null,
    data = [],
    onAction,
    className = '',
    variant = 'default',
    disabled = false,
    children,
}) => {
    const [state, setState] = useState<FormBuilderState>(initialState)

    const handleToggleExpand = useCallback(() => {
        setState(prev => ({ ...prev, isExpanded: !prev.isExpanded }))
    }, [])

    const handleTabChange = useCallback((tab: string) => {
        setState(prev => ({ ...prev, activeTab: tab }))
    }, [])

    const handleSearch = useCallback((query: string) => {
        setState(prev => ({ ...prev, searchQuery: query }))
    }, [])

    const handleSort = useCallback((column: string) => {
        setState(prev => ({
            ...prev,
            sortColumn: column,
            sortDirection: prev.sortColumn === column && prev.sortDirection === 'asc' ? 'desc' : 'asc',
        }))
    }, [])

    const handleSelectItem = useCallback((id: number, selected: boolean) => {
        setState(prev => ({
            ...prev,
            selectedItems: selected
                ? [...prev.selectedItems, id]
                : prev.selectedItems.filter(i => i !== id),
        }))
    }, [])

    const handleRefresh = useCallback(async () => {
        setState(prev => ({ ...prev, isRefreshing: true }))
        onAction?.('refresh')
        setTimeout(() => {
            setState(prev => ({ ...prev, isRefreshing: false, lastUpdated: new Date() }))
        }, 1000)
    }, [onAction])

    const handleAction = useCallback((action: string, itemData?: any) => {
        if (disabled) return
        onAction?.(action, itemData)
    }, [disabled, onAction])

    const filteredData = useMemo(() => {
        let result = [...data]

        if (state.searchQuery) {
            const query = state.searchQuery.toLowerCase()
            result = result.filter(item =>
                JSON.stringify(item).toLowerCase().includes(query)
            )
        }

        result.sort((a, b) => {
            const aVal = a[state.sortColumn]
            const bVal = b[state.sortColumn]
            const modifier = state.sortDirection === 'asc' ? 1 : -1
            if (aVal < bVal) return -1 * modifier
            if (aVal > bVal) return 1 * modifier
            return 0
        })

        return result
    }, [data, state.searchQuery, state.sortColumn, state.sortDirection])

    const selectedCount = state.selectedItems.length

    return (
        <div className={`formbuilder-container ${className}`}>
            <div className='header'>
                <div className='header-left'>
                    <button onClick={handleToggleExpand} className='toggle-btn'>
                        {state.isExpanded ? 'Collapse' : 'Expand'}
                    </button>
                    <h2 className='title'>{title}</h2>
                    {subtitle && <span className='subtitle'>{subtitle}</span>}
                </div>
                <div className='header-right'>
                    <button onClick={handleRefresh} disabled={state.isRefreshing}>
                        {state.isRefreshing ? 'Refreshing...' : 'Refresh'}
                    </button>
                    <button onClick={() => handleAction('create')}>
                        Create
                    </button>
                </div>
            </div>

            {state.isExpanded && (
                <div className='content'>
                    <div className='toolbar'>
                        <input
                            type='text'
                            placeholder='Search...'
                            value={state.searchQuery}
                            onChange={e => handleSearch(e.target.value)}
                            className='search-input'
                        />
                        <button onClick={() => setState(prev => ({ ...prev, showFilters: !prev.showFilters }))}>
                            Filters
                        </button>
                    </div>

                    {state.showFilters && (
                        <div className='filters-panel'>
                            <span>Active Tab: {state.activeTab}</span>
                            <span>Sorted by: {state.sortColumn} ({state.sortDirection})</span>
                        </div>
                    )}

                    {error && (
                        <div className='error-banner'>
                            <span>{error}</span>
                            <button onClick={() => handleAction('retry')}>Retry</button>
                        </div>
                    )}

                    {loading ? (
                        <div className='loading-state'>
                            <span>Loading...</span>
                        </div>
                    ) : filteredData.length === 0 ? (
                        <div className='empty-state'>
                            <span>No data available</span>
                        </div>
                    ) : (
                        <div className='data-list'>
                            {filteredData.map((item, index) => (
                                <div key={item.id || index} className='data-item'>
                                    <input
                                        type='checkbox'
                                        checked={state.selectedItems.includes(item.id)}
                                        onChange={e => handleSelectItem(item.id, e.target.checked)}
                                    />
                                    <span className='item-name'>{item.name}</span>
                                    <span className='item-status'>{item.status}</span>
                                    <button onClick={() => handleAction('edit', item)}>Edit</button>
                                    <button onClick={() => handleAction('delete', item)}>Delete</button>
                                </div>
                            ))}
                        </div>
                    )}

                    {selectedCount > 0 && (
                        <div className='bulk-actions'>
                            <span>{selectedCount} selected</span>
                            <button onClick={() => handleAction('bulk-delete')}>Delete</button>
                            <button onClick={() => handleAction('bulk-export')}>Export</button>
                        </div>
                    )}
                </div>
            )}

            {children}
        </div>
    )
}

export default FormBuilder
