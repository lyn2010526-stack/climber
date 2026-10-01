import { useState, useEffect } from 'react';
import { Activity, RefreshCw, AlertCircle, CheckCircle } from 'lucide-react';
import { api } from '../api';
import { PageHeader } from '../components/ui/PageHeader';
import { Card, CardContent } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import { SkeletonList } from '../components/ui/Skeleton';

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
  const [healthy, setHealthy] = useState<boolean | null>(null);

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
      setHealthy(typeof data.healthy === 'boolean' ? data.healthy : null);
    } catch (e) {
      setError(e instanceof Error ? e.message : '诊断失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDoctor();
  }, []);

  const sections = Array.from(new Set(checks.map(c => c.section)));
  const passCount = checks.filter(c => c.ok).length;
  const failCount = checks.length - passCount;

  return (
    <div className="h-full overflow-y-auto page-transition">
      <div className="p-4 md:p-6 max-w-6xl mx-auto">
        <PageHeader
          title="系统诊断"
          icon={<Activity size={20} />}
          actions={
            <Button
              variant="primary"
              size="sm"
              onClick={fetchDoctor}
              loading={loading}
              icon={<RefreshCw size={14} />}
            >
              重新诊断
            </Button>
          }
        />

        {error && (
          <Card variant="default" className="border-[var(--color-error)]/30">
            <CardContent className="p-4 flex items-center gap-3">
              <AlertCircle size={18} className="text-[var(--color-error)] shrink-0" />
              <p role="alert" className="text-sm text-[var(--color-error)] flex-1">{error}</p>
            </CardContent>
          </Card>
        )}

        {loading && <SkeletonList count={3} />}

        {!loading && !error && (
          <div className="space-y-4">
            <div role="status" className="flex flex-wrap items-center gap-3 border-b border-[var(--color-border-subtle)] pb-3">
                <div className="flex-1">
                  <p className="text-sm font-medium text-[var(--color-text-primary)]">
                    {checks.length === 0 ? '未返回诊断检查项' : healthy === null ? '诊断状态未知' : healthy && failCount === 0 ? '本次诊断通过' : '本次诊断存在异常'}
                  </p>
                  <div className="flex items-center gap-3 mt-1 text-xs text-[var(--color-text-muted)]">
                    <span className="flex items-center gap-1">
                      <CheckCircle size={12} className="text-[var(--color-success)]" />
                      {passCount} 通过
                    </span>
                    {failCount > 0 && (
                      <span className="flex items-center gap-1">
                        <AlertCircle size={12} className="text-[var(--color-error)]" />
                        {failCount} 失败
                      </span>
                    )}
                  </div>
                </div>
            </div>

            <div className="space-y-3">
              {sections.map(section => {
                const sectionChecks = checks.filter(c => c.section === section);
                const sectionPass = sectionChecks.filter(c => c.ok).length;
                return (
                  <Card key={section} variant="default">
                    <CardContent className="p-4">
                      <div className="flex items-center justify-between mb-2">
                        <h3 className="text-xs font-semibold text-[var(--color-text-muted)] uppercase tracking-wider">
                          {section}
                        </h3>
                        <span className="text-xs text-[var(--color-text-muted)]">
                          {sectionPass}/{sectionChecks.length}
                        </span>
                      </div>
                      <div className="divide-y divide-[var(--color-border-subtle)]">
                        {sectionChecks.map(check => (
                          <div key={check.name} className="flex items-start justify-between gap-3 py-2.5">
                            <div className="flex items-center gap-3 min-w-0 flex-1">
                              {check.ok ? (
                                <CheckCircle size={16} className="text-[var(--color-success)] shrink-0 mt-0.5" />
                              ) : (
                                <AlertCircle size={16} className="text-[var(--color-error)] shrink-0 mt-0.5" />
                              )}
                              <div className="min-w-0">
                                <p className="text-sm text-[var(--color-text-primary)] break-words">{check.name}</p>
                                <p className="text-xs text-[var(--color-text-muted)] whitespace-pre-wrap break-words">{check.detail}</p>
                              </div>
                            </div>
                            <Badge variant={check.ok ? 'success' : 'destructive'} size="xs">
                              {check.ok ? 'OK' : 'FAIL'}
                            </Badge>
                          </div>
                        ))}
                      </div>
                    </CardContent>
                  </Card>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
