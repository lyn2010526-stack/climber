// @ts-nocheck
import React, { useState, useEffect, useCallback, useMemo } from 'react'
import { useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'

import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Table, TableHeader, TableBody, TableRow, TableCell } from '@/components/ui/Table'
import { Modal, ModalHeader, ModalBody, ModalFooter } from '@/components/ui/Modal'
import { Badge } from '@/components/ui/Badge'
import { toast } from 'react-hot-toast'

import { fetchTicketss, createTickets, updateTickets, deleteTickets } from '@/api/tickets'
import { Tickets } from '@/types'


interface TicketsPageProps {
    title?: string
}


export const TicketsPage: React.FC<TicketsPageProps> = ({ title }) => {
    const { t } = useTranslation()
    const navigate = useNavigate()
    const queryClient = useQueryClient()
    const [searchParams, setSearchParams] = useSearchParams()

    const [page, setPage] = useState(1)
    const [pageSize, setPageSize] = useState(20)
    const [search, setSearch] = useState('')
    const [statusFilter, setStatusFilter] = useState<string>('all')
    const [sortBy, setSortBy] = useState<string>('created_at')
    const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc')
    const [selectedIds, setSelectedIds] = useState<number[]>([])
    const [isCreateModalOpen, setIsCreateModalOpen] = useState(false)
    const [isEditModalOpen, setIsEditModalOpen] = useState(false)
    const [editingId, setEditingId] = useState<number | null>(null)

    const { data, isLoading, error } = useQuery({
        queryKey: ['tickets', page, pageSize, search, statusFilter, sortBy, sortOrder],
        queryFn: () => fetchTicketss({ page, pageSize, search, status: statusFilter, sortBy, sortOrder })
    })

    const createMutation = useMutation({
        mutationFn: createTickets,
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['tickets'] })
            setIsCreateModalOpen(false)
            toast.success(t('common.created'))
        },
        onError: () => {
            toast.error(t('common.error'))
        }
    })

    const updateMutation = useMutation({
        mutationFn: (data: Partial<Tickets>) => updateTickets(editingId!, data),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['tickets'] })
            setIsEditModalOpen(false)
            toast.success(t('common.updated'))
        }
    })

    const deleteMutation = useMutation({
        mutationFn: deleteTickets,
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['tickets'] })
            toast.success(t('common.deleted'))
        }
    })

    const handleSearch = useCallback((value: string) => {
        setSearch(value)
        setPage(1)
    }, [])

    const handleSort = useCallback((column: string) => {
        if (sortBy === column) {
            setSortOrder(prev => prev === 'asc' ? 'desc' : 'asc')
        } else {
            setSortBy(column)
            setSortOrder('asc')
        }
    }, [sortBy])

    const handleSelectAll = useCallback((checked: boolean) => {
        if (checked && data?.items) {
            setSelectedIds(data.items.map(item => item.id))
        } else {
            setSelectedIds([])
        }
    }, [data])

    const handleSelect = useCallback((id: number, checked: boolean) => {
        setSelectedIds(prev =>
            checked ? [...prev, id] : prev.filter(i => i !== id)
        )
    }, [])

    const handleBulkDelete = useCallback(() => {
        if (selectedIds.length === 0) return
        if (confirm(t('common.confirm_delete'))) {
            selectedIds.forEach(id => deleteMutation.mutate(id))
            setSelectedIds([])
        }
    }, [selectedIds, deleteMutation, t])

    const statusCounts = useMemo(() => {
        if (!data?.items) return {}
        return data.items.reduce((acc, item) => {
            acc[item.status] = (acc[item.status] || 0) + 1
            return acc
        }, {} as Record<string, number>)
    }, [data])

    if (error) {
        return (
            <div className='flex items-center justify-center min-h-screen'>
                <Card className='max-w-md'>
                    <CardContent>
                        <p className='text-red-500'>{t('common.error_loading')}</p>
                        <Button onClick={() => navigate(0)} className='mt-4'>
                            {t('common.retry')}
                        </Button>
                    </CardContent>
                </Card>
            </div>
        )
    }

    return (
        <div className='space-y-6 p-6'>
            <div className='flex items-center justify-between'>
                <h1 className='text-2xl font-bold'>{title || t('tickets.title')}</h1>
                <div className='flex gap-2'>
                    <Button variant='outline' onClick={() => navigate(0)}>
                        {t('common.refresh')}
                    </Button>
                    <Button onClick={() => setIsCreateModalOpen(true)}>
                        {t('common.create')}
                    </Button>
                </div>
            </div>

            <Card>
                <CardContent className='p-4'>
                    <div className='flex gap-4 items-center'>
                        <Input
                            placeholder={t('common.search')}
                            value={search}
                            onChange={e => handleSearch(e.target.value)}
                            className='max-w-sm'
                        />
                        <select
                            value={statusFilter}
                            onChange={e => setStatusFilter(e.target.value)}
                            className='border rounded px-3 py-2'
                        >
                            <option value='all'>{t('common.all_status')}</option>
                            <option value='active'>{t('common.active')}</option>
                            <option value='inactive'>{t('common.inactive')}</option>
                        </select>
                    </div>
                </CardContent>
            </Card>

            <Card>
                <CardContent className='p-0'>
                    <Table>
                        <TableHeader>
                            <TableRow>
                                <TableCell>
                                    <input type='checkbox' onChange={e => handleSelectAll(e.target.checked)} />
                                </TableCell>
                                <TableCell>{t('common.name')}</TableCell>
                                <TableCell>{t('common.status')}</TableCell>
                                <TableCell>{t('common.created_at')}</TableCell>
                                <TableCell>{t('common.actions')}</TableCell>
                            </TableRow>
                        </TableHeader>
                        <TableBody>
                            {isLoading && (
                                <TableRow>
                                    <TableCell colSpan={5}>{t('common.loading')}</TableCell>
                                </TableRow>
                            )}
                            {data?.items?.map(item => (
                                <TableRow key={item.id}>
                                    <TableCell>
                                        <input type='checkbox' checked={selectedIds.includes(item.id)} onChange={e => handleSelect(item.id, e.target.checked)} />
                                    </TableCell>
                                    <TableCell>{item.name}</TableCell>
                                    <TableCell>
                                        <Badge variant={item.status === 'active' ? 'success' : 'secondary'}>
                                            {item.status}
                                        </Badge>
                                    </TableCell>
                                    <TableCell>{item.created_at}</TableCell>
                                    <TableCell>
                                        <div className='flex gap-2'>
                                            <Button size='sm' variant='outline' onClick={() => { setEditingId(item.id); setIsEditModalOpen(true) }}>{t('common.edit')}</Button>
                                            <Button size='sm' variant='destructive' onClick={() => { if (confirm(t('common.confirm_delete'))) deleteMutation.mutate(item.id) }}>{t('common.delete')}</Button>
                                        </div>
                                    </TableCell>
                                </TableRow>
                            ))}
                        </TableBody>
                    </Table>
                </CardContent>
            </Card>

            <div className='flex justify-between items-center'>
                <span className='text-sm text-gray-500'>
                    {t('common.showing', { from: (page - 1) * pageSize + 1, to: Math.min(page * pageSize, data?.total || 0), total: data?.total || 0 })}
                </span>
                <div className='flex gap-2'>
                    <Button variant='outline' disabled={page <= 1} onClick={() => setPage(p => p - 1)}>{t('common.previous')}</Button>
                    <Button variant='outline' disabled={page * pageSize >= (data?.total || 0)} onClick={() => setPage(p => p + 1)}>{t('common.next')}</Button>
                </div>
            </div>

            <Modal isOpen={isCreateModalOpen} onClose={() => setIsCreateModalOpen(false)}>
                <ModalHeader>{t('common.create')}</ModalHeader>
                <ModalBody>
                    <p>{t('tickets.create_description')}</p>
                </ModalBody>
                <ModalFooter>
                    <Button variant='outline' onClick={() => setIsCreateModalOpen(false)}>{t('common.cancel')}</Button>
                    <Button onClick={() => createMutation.mutate({ name: 'New Item' })}>{t('common.create')}</Button>
                </ModalFooter>
            </Modal>
        </div>
    )
}

export default TicketsPage
