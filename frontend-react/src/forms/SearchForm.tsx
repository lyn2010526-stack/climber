import React, { useState, useCallback, useEffect } from 'react'


interface SearchFormData {
    [key: string]: any
}


interface SearchFormErrors {
    [key: string]: string | undefined
}


interface SearchFormProps {
    initialData?: Partial<SearchFormData>
    onSubmit: (data: SearchFormData) => void | Promise<void>
    onCancel?: () => void
    onValidate?: (data: SearchFormData) => SearchFormErrors
    loading?: boolean
    disabled?: boolean
    submitLabel?: string
    cancelLabel?: string
    layout?: 'vertical' | 'horizontal' | 'inline'
}


export const SearchForm: React.FC<SearchFormProps> = ({
    initialData = {},
    onSubmit,
    onCancel,
    onValidate,
    loading = false,
    disabled = false,
    submitLabel = 'Submit',
    cancelLabel = 'Cancel',
    layout = 'vertical',
}) => {
    const [formData, setFormData] = useState<SearchFormData>(initialData as SearchFormData)
    const [errors, setErrors] = useState<SearchFormErrors>({})
    const [touched, setTouched] = useState<Record<string, boolean>>({})
    const [submitting, setSubmitting] = useState(false)

    const handleChange = useCallback((field: string, value: any) => {
        setFormData(prev => ({ ...prev, [field]: value }))
        setTouched(prev => ({ ...prev, [field]: true }))
    }, [])

    const handleBlur = useCallback((field: string) => {
        setTouched(prev => ({ ...prev, [field]: true }))
        if (onValidate) {
            const validationErrors = onValidate(formData)
            setErrors(prev => ({ ...prev, [field]: validationErrors[field] }))
        }
    }, [formData, onValidate])

    const handleSubmit = useCallback(async (e: React.FormEvent) => {
        e.preventDefault()
        if (onValidate) {
            const validationErrors = onValidate(formData)
            setErrors(validationErrors)
            if (Object.values(validationErrors).some(Boolean)) {
                return
            }
        }
        setSubmitting(true)
        try {
            await onSubmit(formData)
        } finally {
            setSubmitting(false)
        }
    }, [formData, onValidate, onSubmit])

    const handleReset = useCallback(() => {
        setFormData(initialData as SearchFormData)
        setErrors({})
        setTouched({})
    }, [initialData])

    const isValid = Object.values(errors).every(e => !e)

    return (
        <form
            onSubmit={handleSubmit}
            className={`form form-${layout}`}
            noValidate
        >
            <div className='form-fields'>
                {/* Form fields go here */}
            </div>

            {Object.keys(errors).length > 0 && (
                <div className='form-errors'>
                    {Object.entries(errors).map(([field, error]) => (
                        error && <span key={field} className='error'>{field}: {error}</span>
                    ))}
                </div>
            )}

            <div className='form-actions'>
                <button
                    type='submit'
                    disabled={disabled || loading || submitting || !isValid}
                >
                    {loading || submitting ? 'Loading...' : submitLabel}
                </button>
                {onCancel && (
                    <button type='button' onClick={onCancel}>
                        {cancelLabel}
                    </button>
                )}
                <button type='button' onClick={handleReset}>
                    Reset
                </button>
            </div>
        </form>
    )
}

export default SearchForm
