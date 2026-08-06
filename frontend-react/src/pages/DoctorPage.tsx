import { useState, useEffect } from 'react';
import { Activity, RefreshCw, AlertCircle, CheckCircle, HeartPulse } from 'lucide-react';
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
  const passCount = checks.filter(c => c.ok).length;
  const failCount = checks.length - passCount;

  return (
    <div className="h-full overflow-y-auto page-transition">
      <div className="p-4 md:p-6 lg:p-8 max-w-5xl mx-auto">
        <PageHeader
          title="系统诊断"
          description="运行环境健康检查，快速定位配置和依赖问题"
          icon={<Activity size={20} />}
          actions={
            <Button
              variant="secondary"
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
          <div className="bg-[var(--color-error)]/10 border border-[var(--color-error)]/30 rounded-xl p-4 mb-6 flex items-center gap-3">
            <AlertCircle size={18} className="text-[var(--color-error)] shrink-0" />
            <p className="text-sm text-[var(--color-error)] flex-1">{error}</p>
          </div>
        )}

        {loading && <SkeletonList count={3} />}

        {!loading && !error && (
          <>
            <Card variant="default" className="mb-6">
              <CardContent className="p-4 flex items-center gap-4">
                <div className={`p-3 rounded-2xl ${healthy ? 'bg-[var(--color-success)]/10 border border-[var(--color-success)]/20' : 'bg-[var(--color-error)]/10 border border-[var(--color-error)]/20'}`}>
                  <HeartPulse size={24} className={healthy ? 'text-[var(--color-success)]' : 'text-[var(--color-error)]'} />
                </div>
                <div className="flex-1">
                  <p className={`text-sm font-semibold ${healthy ? 'text-[var(--color-success)]' : 'text-[var(--color-error)]'}`}>
                    {healthy ? '系统健康，所有检查通过' : '系统存在异常，请检查下方 FAIL 项'}
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
              </CardContent>
            </Card>

            <div className="space-y-6 stagger-children">
              {sections.map(section => {
                const sectionChecks = checks.filter(c => c.section === section);
                const sectionPass = sectionChecks.filter(c => c.ok).length;
                return (
                  <Card key={section} variant="default">
                    <CardContent className="p-6">
                      <div className="flex items-center justify-between mb-4">
                        <h3 className="text-xs font-semibold text-[var(--color-text-muted)] uppercase tracking-wider">
                          {section}
                        </h3>
                        <span className="text-xs text-[var(--color-text-muted)]">
                          {sectionPass}/{sectionChecks.length}
                        </span>
                      </div>
                      <div className="space-y-3">
                        {sectionChecks.map(check => (
                          <div key={check.name} className="flex items-start justify-between gap-4">
                            <div className="flex items-center gap-3 min-w-0 flex-1">
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
          </>
        )}
      </div>
    </div>
  );
}
