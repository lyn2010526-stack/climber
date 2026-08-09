import React, { useState, useEffect } from 'react';
import { Key, LogIn, AlertCircle, Eye, EyeOff } from 'lucide-react';
import { Card, CardContent } from '../components/ui/Card';
import { Input } from '../components/ui/Input';
import { Button } from '../components/ui/Button';

interface LoginPageProps {
    onLogin?: (token: string, user: any) => void;
}

export const LoginPage: React.FC<LoginPageProps> = ({ onLogin }) => {
    const navigateToApp = () => {
        window.location.hash = 'chat';
    };
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [showPassword, setShowPassword] = useState(false);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [authEnabled, setAuthEnabled] = useState(true);

    useEffect(() => {
        const token = localStorage.getItem('auth_token');
        if (token) {
            navigateToApp();
            return;
        }

        fetch('/api/v1/auth/health')
            .then(r => r.json())
            .then(data => setAuthEnabled(data.authentication_enabled))
            .catch(() => setAuthEnabled(false));
    }, []);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        setError(null);

        try {
            const response = await fetch('/api/v1/auth/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password }),
            });

            if (!response.ok) {
                const data = await response.json().catch(() => ({}));
                throw new Error(data.detail || 'Login failed');
            }

            const data = await response.json();
            localStorage.setItem('auth_token', data.access_token);
            localStorage.setItem('refresh_token', data.refresh_token);
            localStorage.setItem('user_info', JSON.stringify(data.user));

            if (onLogin) {
                onLogin(data.access_token, data.user);
            }

            navigateToApp();
        } catch (err: any) {
            setError(err.message || 'Invalid credentials');
        } finally {
            setLoading(false);
        }
    };

    const handleSkipAuth = () => {
        navigateToApp();
    };

    if (!authEnabled) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-[var(--color-bg-page)] p-4">
                <div className="text-center max-w-sm w-full">
                    <div className="h-14 w-14 rounded-[var(--radius-lg)] bg-[var(--color-accent-muted)] flex items-center justify-center mx-auto mb-4 ring-1 ring-[var(--color-accent)]/20">
                        <Key size={24} className="text-[var(--color-accent)]" />
                    </div>
                    <h2 className="text-lg font-semibold text-[var(--color-text-primary)]">Authentication Disabled</h2>
                    <p className="text-sm text-[var(--color-text-muted)] mt-2 mb-6">
                        The system is running without authentication.
                    </p>
                    <Button variant="primary" size="md" onClick={handleSkipAuth} className="w-full">
                        Continue to App
                    </Button>
                </div>
            </div>
        );
    }

    return (
        <div className="min-h-screen flex items-center justify-center bg-[var(--color-bg-page)] p-4">
            <div className="w-full max-w-md">
                <Card variant="elevated" padding="none" className="overflow-hidden shadow-[var(--shadow-xl)]">
                    <CardContent className="p-6 md:p-8">
                        <div className="text-center mb-6 md:mb-8">
                            <div className="h-14 w-14 rounded-[var(--radius-lg)] flex items-center justify-center mx-auto mb-4"
                                style={{ background: 'var(--gradient-accent)', boxShadow: 'var(--shadow-glow)' }}>
                                <Key size={24} className="text-white" />
                            </div>
                            <h1 className="text-xl md:text-2xl font-bold text-[var(--color-text-primary)]">Welcome Back</h1>
                            <p className="text-sm text-[var(--color-text-muted)] mt-1.5">
                                Sign in to access Agent Engine
                            </p>
                        </div>

                        {error && (
                            <div className="mb-4 md:mb-6 p-3 md:p-4 bg-[var(--color-error-subtle)] border border-[var(--color-error)]/20 rounded-[var(--radius-lg)] flex items-center gap-3">
                                <AlertCircle size={18} className="text-[var(--color-error)] shrink-0" />
                                <span className="text-sm text-[var(--color-error)]">{error}</span>
                            </div>
                        )}

                        <form onSubmit={handleSubmit} className="space-y-4">
                            <div>
                                <label className="block text-xs font-medium text-[var(--color-text-secondary)] mb-1.5">
                                    Username
                                </label>
                                <Input
                                    type="text"
                                    value={username}
                                    onChange={e => setUsername(e.target.value)}
                                    placeholder="Enter your username"
                                    autoComplete="username"
                                />
                            </div>

                            <div>
                                <label className="block text-xs font-medium text-[var(--color-text-secondary)] mb-1.5">
                                    Password
                                </label>
                                <Input
                                    type={showPassword ? 'text' : 'password'}
                                    value={password}
                                    onChange={e => setPassword(e.target.value)}
                                    placeholder="Enter your password"
                                    autoComplete="current-password"
                                    rightIcon={
                                        <button
                                            type="button"
                                            onClick={() => setShowPassword(!showPassword)}
                                            className="text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)] transition-colors focus-ring rounded"
                                        >
                                            {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                                        </button>
                                    }
                                />
                            </div>

                            <Button
                                type="submit"
                                variant="primary"
                                size="md"
                                className="w-full"
                                loading={loading}
                                disabled={!username || !password}
                                icon={<LogIn size={16} />}
                            >
                                Sign In
                            </Button>
                        </form>

                        <div className="mt-6 pt-6 border-t border-[var(--color-border-subtle)]">
                            <p className="text-xs text-center text-[var(--color-text-muted)] leading-relaxed">
                                Default admin credentials are created on first startup.<br />
                                Check server logs for initial password.
                            </p>
                        </div>
                    </CardContent>
                </Card>
            </div>
        </div>
    );
};

export default LoginPage;
