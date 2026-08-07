import React, { useState, useEffect, useCallback } from 'react'
import { useParams, useNavigate, useSearchParams } from 'react-router-dom'


interface FilesPageProps {
    title?: string
}


interface FilesPageState {
    loading: boolean
    error: string | null
    data: any
    searchQuery: string
    currentPage: number
    pageSize: number
    totalItems: number
    sortField: string
    sortDirection: 'asc' | 'desc'
    selectedItems: string[]
    filters: Record<string, any>
}


export const FilesPage: React.FC<FilesPageProps> = ({ title }) => {
    const params = useParams()
    const navigate = useNavigate()
    const [searchParams, setSearchParams] = useSearchParams()

    const [state, setState] = useState<FilesPageState>({
        loading: false,
        error: null,
        data: null,
        searchQuery: '',
        currentPage: 1,
        pageSize: 20,
        totalItems: 0,
        sortField: 'createdAt',
        sortDirection: 'desc',
        selectedItems: [],
        filters: {},
    })

    const fetchData = useCallback(async () => {
        setState(prev => ({ ...prev, loading: true, error: null }))
        try {
            await new Promise(resolve => setTimeout(resolve, 100))
            setState(prev => ({ ...prev, loading: false, data: [] }))
        } catch (err) {
            setState(prev => ({ ...prev, loading: false, error: String(err) }))
        }
    }, [state.currentPage, state.pageSize, state.sortField, state.sortDirection])

    useEffect(() => {
        fetchData()
    }, [fetchData])

    const handleSearch = useCallback((query: string) => {
        setState(prev => ({ ...prev, searchQuery: query, currentPage: 1 }))
    }, [])

    const handleSort = useCallback((field: string) => {
        setState(prev => ({
            ...prev,
            sortField: field,
            sortDirection: prev.sortField === field && prev.sortDirection === 'asc' ? 'desc' : 'asc',
        }))
    }, [])

    const handlePageChange = useCallback((page: number) => {
        setState(prev => ({ ...prev, currentPage: page }))
    }, [])

    const handleSelect = useCallback((id: string) => {
        setState(prev => ({
            ...prev,
            selectedItems: prev.selectedItems.includes(id)
                ? prev.selectedItems.filter(i => i !== id)
                : [...prev.selectedItems, id],
        }))
    }, [])

    return (
        <div className='page-container'>
            <header className='page-header'>
                <h1>{title || 'Files Page'}</h1>
            </header>

            <div className='page-toolbar'>
                <input
                    type='search'
                    placeholder='Search...'
                    value={state.searchQuery}
                    onChange={e => handleSearch(e.target.value)}
                />
                <button onClick={fetchData}>Refresh</button>
            </div>

            {state.loading && <div className='loading'>Loading...</div>}
            {state.error && <div className='error'>{state.error}</div>}

            <main className='page-content'>
                {/* Content goes here */}
            </main>

            <footer className='page-footer'>
                <span>Page {state.currentPage} of {Math.ceil(state.totalItems / state.pageSize)}</span>
            </footer>
        </div>
    )
}

export default FilesPage
