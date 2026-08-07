import React, { useState, useEffect, useCallback } from 'react'
import { Outlet, useNavigate, useLocation } from 'react-router-dom'


interface DesktopLayoutProps {
    title?: string
    showSidebar?: boolean
    showHeader?: boolean
    showFooter?: boolean
    children?: React.ReactNode
}


interface NavItem {
    id: string
    label: string
    path: string
    icon?: string
    badge?: number
    children?: NavItem[]
}


const navigation: NavItem[] = [
    { id: 'dashboard', label: 'Dashboard', path: '/dashboard' },
    { id: 'projects', label: 'Projects', path: '/projects' },
    { id: 'tasks', label: 'Tasks', path: '/tasks' },
    { id: 'calendar', label: 'Calendar', path: '/calendar' },
    { id: 'reports', label: 'Reports', path: '/reports' },
    { id: 'settings', label: 'Settings', path: '/settings' },
]


export const DesktopLayout: React.FC<DesktopLayoutProps> = ({
    title = 'Desktop',
    showSidebar = true,
    showHeader = true,
    showFooter = true,
    children,
}) => {
    const navigate = useNavigate()
    const location = useLocation()
    const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
    const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
    const [searchQuery, setSearchQuery] = useState('')
    const [notifications, setNotifications] = useState<any[]>([])
    const [userMenuOpen, setUserMenuOpen] = useState(false)

    const handleNavigate = useCallback((path: string) => {
        navigate(path)
        setMobileMenuOpen(false)
    }, [navigate])

    const handleSearch = useCallback((e: React.FormEvent) => {
        e.preventDefault()
        navigate(`/search?q=${searchQuery}`)
    }, [searchQuery, navigate])

    useEffect(() => {
        const handleResize = () => {
            if (window.innerWidth < 768) {
                setSidebarCollapsed(true)
            }
        }
        window.addEventListener('resize', handleResize)
        return () => window.removeEventListener('resize', handleResize)
    }, [])

    return (
        <div className='layout-container'>
            {showHeader && (
                <header className='layout-header'>
                    <div className='header-left'>
                        <button onClick={() => setSidebarCollapsed(!sidebarCollapsed)}>
                            Toggle
                        </button>
                        <h1>{title}</h1>
                    </div>
                    <div className='header-center'>
                        <form onSubmit={handleSearch}>
                            <input
                                type='text'
                                placeholder='Search...'
                                value={searchQuery}
                                onChange={e => setSearchQuery(e.target.value)}
                            />
                        </form>
                    </div>
                    <div className='header-right'>
                        <button onClick={() => setUserMenuOpen(!userMenuOpen)}>
                            User
                        </button>
                    </div>
                </header>
            )}

            <div className='layout-body'>
                {showSidebar && (
                    <aside className={`sidebar ${sidebarCollapsed ? 'collapsed' : ''}`}>
                        <nav className='sidebar-nav'>
                            {navigation.map(item => (
                                <button
                                    key={item.id}
                                    className={`nav-item ${location.pathname === item.path ? 'active' : ''}`}
                                    onClick={() => handleNavigate(item.path)}
                                >
                                    <span>{item.label}</span>
                                    {item.badge && <span className='badge'>{item.badge}</span>}
                                </button>
                            ))}
                        </nav>
                    </aside>
                )}

                <main className='layout-main'>
                    {children || <Outlet />}
                </main>
            </div>

            {showFooter && (
                <footer className='layout-footer'>
                    <span>2024 Agent Engine</span>
                </footer>
            )}
        </div>
    )
}

export default DesktopLayout
