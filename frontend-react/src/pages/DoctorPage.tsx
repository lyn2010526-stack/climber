import { useState, useEffect } from 'react';
import { Activity, RefreshCw, AlertCircle, CheckCircle } from 'lucide-react';
import { api } from '../api';
import { Alert, Badge, Button, Card, LoadingSpinner } from '../components/ui';

interface CheckItem {
  name: string;
  ok: boolean;
  detail: string;
  section: string;
}

export function DoctorPage() {
  const [checks, setChecks] = useState<CheckItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [healthy, setHealthy] = useState(false);

  const fetchDoctor = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.runDoctor();
      const items: CheckItem[] = [];
      for (const section of data.sections || []) {
        for (const c of section.checks || []) {
          items.push({ name: c.name, ok: c.ok, detail: c.detail, section: section.section });
        }
      }
      setChecks(items);
      setHealthy(data.healthy);
    } catch (e: any) {
      setError(e.message || '诊断失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDoctor();
  }, []);

  const sections = Array.from(new Set(checks.map(c => c.section)));

  return (
    <div className="h-full overflow-y-auto p-8">
      <div className="max-w-5xl mx-auto">
        <div className="mb-8 flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-bold text-[var(--color-text-primary)] flex items-center gap-3">
              <div className="w-9 h-9 rounded-2xl bg-[var(--color-accent)]/10 flex items-center justify-center border border-[var(--color-accent)]/20">
                <Activity size={20} className="text-[var(--color-accent)]" />
              </div>
              系统诊断
            </h2>
            <p className="text-[var(--color-text-secondary)] text-sm mt-1.5">
              运行环境健康检查，快速定位配置和依赖问题。
            </p>
          </div>
          <Button
            onClick={fetchDoctor}
            disabled={loading}
            variant="secondary"
            className="rounded-2xl px-4 py-2.5 h-auto"
          >
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
            重新诊断
          </Button>
        </div>

        {error && (
          <div className="mb-6">
            <Alert variant="destructive">{error}</Alert>
          </div>
        )}

        {loading && (
          <div className="flex items-center justify-center py-16">
            <LoadingSpinner message="正在诊断..." />
          </div>
        )}

        {!loading && !error && (
          <>
            <div className={`mb-6 rounded-2xl p-4 flex items-center gap-3 border ${healthy ? 'bg-[var(--color-success)]/10 border-[var(--color-success)]/30' : 'bg-[var(--color-error)]/10 border-[var(--color-error)]/30'}`}>
              {healthy ? (
                <CheckCircle size={20} className="text-[var(--color-success)] shrink-0" />
              ) : (
                <AlertCircle size={20} className="text-[var(--color-error)] shrink-0" />
              )}
              <p className={`text-sm font-semibold ${healthy ? 'text-[var(--color-success)]' : 'text-[var(--color-error)]'}`}>
                {healthy ? '系统健康，所有检查通过' : '系统存在异常，请检查下方 FAIL 项'}
              </p>
            </div>

            <div className="space-y-6">
              {sections.map(section => {
                const sectionChecks = checks.filter(c => c.section === section);
                return (
                  <Card key={section} className="rounded-3xl p-6">
                    <h3 className="text-xs font-semibold text-[var(--color-text-muted)] uppercase tracking-wider mb-4">
                      {section}
                    </h3>
                    <div className="space-y-3">
                      {sectionChecks.map(check => (
                        <div key={check.name} className="flex items-start justify-between gap-4">
                          <div className="flex items-center gap-3 min-w-0">
                            {check.ok ? (
                              <CheckCircle size={16} className="text-[var(--color-success)] shrink-0 mt-0.5" />
                            ) : (
                              <AlertCircle size={16} className="text-[var(--color-error)] shrink-0 mt-0.5" />
                            )}
                            <div className="min-w-0">
                              <p className="text-sm text-[var(--color-text-primary)] truncate">{check.name}</p>
                              <p className="text-xs text-[var(--color-text-muted)] truncate">{check.detail}</p>
                            </div>
                          </div>
                          <Badge variant={check.ok ? 'success' : 'destructive'} className="shrink-0 text-[10px]">
                            {check.ok ? 'OK' : 'FAIL'}
                          </Badge>
                        </div>
                      ))}
                    </div>
                  </Card>
                );
              })}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
