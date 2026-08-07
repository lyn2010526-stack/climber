import React, { useState, useEffect, useCallback, useMemo } from 'react'


interface SummaryProps {
    title?: string
    variant?: 'default' | 'primary' | 'secondary' | 'danger' | 'success' | 'warning' | 'info' | 'accent'
    size?: 'xs' | 'sm' | 'md' | 'lg' | 'xl'
    disabled?: boolean
    loading?: boolean
    className?: string
    children?: React.ReactNode
    onClick?: (e: React.MouseEvent) => void
    onChange?: (value: any) => void
    onFocus?: (e: React.FocusEvent) => void
    onBlur?: (e: React.FocusEvent) => void
    onKeyDown?: (e: React.KeyboardEvent) => void
    onKeyUp?: (e: React.KeyboardEvent) => void
    onMouseEnter?: (e: React.MouseEvent) => void
    onMouseLeave?: (e: React.MouseEvent) => void
}


interface SummaryState {
    isActive: boolean
    isHovered: boolean
    isFocused: boolean
    value: any
    error: string | null
    touched: boolean
}


export const Summary: React.FC<SummaryProps> = ({
    title = 'Summary',
    variant = 'default',
    size = 'md',
    disabled = false,
    loading = false,
    className = '',
    children,
    onClick,
    onChange,
    onFocus,
    onBlur,
    onKeyDown,
    onKeyUp,
    onMouseEnter,
    onMouseLeave,
}) => {
    const [state, setState] = useState<SummaryState>({
        isActive: false,
        isHovered: false,
        isFocused: false,
        value: null,
        error: null,
        touched: false,
    })

    const handleClick = useCallback((e: React.MouseEvent) => {
        if (disabled || loading) return
        setState(prev => ({ ...prev, isActive: !prev.isActive }))
        onClick?.(e)
    }, [disabled, loading, onClick])

    const handleChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
        const value = e.target.value
        setState(prev => ({ ...prev, value, touched: true }))
        onChange?.(value)
    }, [onChange])

    const handleFocus = useCallback((e: React.FocusEvent) => {
        setState(prev => ({ ...prev, isFocused: true }))
        onFocus?.(e)
    }, [onFocus])

    const handleBlur = useCallback((e: React.FocusEvent) => {
        setState(prev => ({ ...prev, isFocused: false }))
        onBlur?.(e)
    }, [onBlur])

    const classNames = useMemo(() => {
        const classes = ['component', 'summary']
        classes.push(`component--${variant}`)
        classes.push(`component--${size}`)
        if (disabled) classes.push('component--disabled')
        if (loading) classes.push('component--loading')
        if (state.isActive) classes.push('component--active')
        if (state.isHovered) classes.push('component--hovered')
        if (state.isFocused) classes.push('component--focused')
        if (state.error) classes.push('component--error')
        if (className) classes.push(className)
        return classes.join(' ')
    }, [variant, size, disabled, loading, state.isActive, state.isHovered, state.isFocused, state.error, className])

    return (
        <div className={classNames}>
            <div className='component-header'>
                <h3>{title}</h3>
            </div>
            <div className='component-body'>
                {children}
            </div>
            {state.error && (
                <div className='component-error'>{state.error}</div>
            )}
        </div>
    )
}

export default Summary
