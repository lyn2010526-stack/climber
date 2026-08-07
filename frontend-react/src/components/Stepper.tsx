import React, { useState, useEffect, useCallback, useMemo } from 'react'


interface StepperProps {
    title?: string
    variant?: 'default' | 'primary' | 'secondary' | 'danger'
    size?: 'sm' | 'md' | 'lg'
    disabled?: boolean
    loading?: boolean
    className?: string
    children?: React.ReactNode
    onClick?: () => void
    onChange?: (value: any) => void
}


interface StepperState {
    isActive: boolean
    isHovered: boolean
    value: any
    error: string | null
}


export const Stepper: React.FC<StepperProps> = ({
    title = 'Stepper',
    variant = 'default',
    size = 'md',
    disabled = false,
    loading = false,
    className = '',
    children,
    onClick,
    onChange,
}) => {
    const [state, setState] = useState<StepperState>({
        isActive: false,
        isHovered: false,
        value: null,
        error: null,
    })

    const handleClick = useCallback(() => {
        if (disabled || loading) return
        setState(prev => ({ ...prev, isActive: !prev.isActive }))
        onClick?.()
    }, [disabled, loading, onClick])

    const handleMouseEnter = useCallback(() => {
        setState(prev => ({ ...prev, isHovered: true }))
    }, [])

    const handleMouseLeave = useCallback(() => {
        setState(prev => ({ ...prev, isHovered: false }))
    }, [])

    const handleChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
        const value = e.target.value
        setState(prev => ({ ...prev, value }))
        onChange?.(value)
    }, [onChange])

    const classNames = useMemo(() => {
        const classes = ['component', 'stepper']
        classes.push(`component--${variant}`)
        classes.push(`component--${size}`)
        if (disabled) classes.push('component--disabled')
        if (loading) classes.push('component--loading')
        if (state.isActive) classes.push('component--active')
        if (state.isHovered) classes.push('component--hovered')
        if (className) classes.push(className)
        return classes.join(' ')
    }, [variant, size, disabled, loading, state.isActive, state.isHovered, className])

    return (
        <div
            className={classNames}
            onMouseEnter={handleMouseEnter}
            onMouseLeave={handleMouseLeave}
        >
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

export default Stepper
