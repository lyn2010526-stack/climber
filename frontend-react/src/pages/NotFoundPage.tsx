import React from 'react'
import { useNavigate } from 'react-router-dom'
import { useCurrentPage } from '../store/page'


export const NotFoundPage: React.FC = () => {
    const navigate = useNavigate()
    const setPage = useCurrentPage((s: any) => s.setPage)

    const handleGoHome = () => {
        setPage('chat')
        navigate('/chat')
    }

    const handleGoBack = () => {
        navigate(-1)
    }

    return (
        <div className="flex flex-col items-center justify-center min-h-[60vh] text-center px-4">
            <div className="text-8xl font-bold text-[var(--color-text-muted)] mb-4">404</div>
            <h1 className="text-2xl font-semibold text-[var(--color-text-primary)] mb-2">页面未找到</h1>
            <p className="text-[var(--color-text-muted)] mb-8">您访问的页面不存在或已被移除</p>
            <div className="flex gap-4">
                <button
                    onClick={handleGoHome}
                    className="px-4 py-2 bg-[var(--color-accent)] text-white rounded-md hover:opacity-90 transition-opacity"
                >
                    返回首页
                </button>
                <button
                    onClick={handleGoBack}
                    className="px-4 py-2 border border-[var(--color-border-default)] text-[var(--color-text-secondary)] rounded-md hover:bg-[var(--color-bg-surface-2)] transition-colors"
                >
                    返回上页
                </button>
            </div>
        </div>
    )
}

export default NotFoundPage
