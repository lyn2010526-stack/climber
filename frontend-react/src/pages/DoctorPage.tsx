import { useState, useEffect } from 'react';
import { Activity, RefreshCw, AlertCircle, CheckCircle } from 'lucide-react';

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
      const res = await fetch('/api/v1/doctor');
      if (res.ok) {
        const data = await res.json();
        const items: CheckItem[] = [];
        for (const section of data.sections || []) {
          for (const c of section.checks || []) {
            items.push({ name: c.name, ok: c.ok, detail: c.detail, section: section.section });
          }
        }
        setChecks(items);
        setHealthy(data.healthy);
      } else {
        setError(`诊断失败 (HTTP ${res.status})`);
      }
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
            <h2 className="text-2xl font-bold text-white flex items-center gap-3">
              <Activity size={24} className="text-[#007AFF]" />
              系统诊断
            </h2>
            <p className="text-gray-400 text-sm mt-1.5">
              运行环境健康检查，快速定位配置和依赖问题。
            </p>
          </div>
          <button
            onClick={fetchDoctor}
            disabled={loading}
            className="flex items-center gap-2 px-4 py-2.5 bg-white/5 border border-white/10 rounded-2xl text-sm text-gray-300 hover:bg-white/10 disabled:opacity-50 transition-all"
          >
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
            重新诊断
          </button>
        </div>

        {error && (
          <div className="bg-red-500/10 border border-red-500/30 rounded-2xl p-4 mb-6 flex items-center gap-3">
            <AlertCircle size={18} className="text-red-400 shrink-0" />
            <p className="text-sm text-red-400 flex-1">{error}</p>
          </div>
        )}

        {loading && (
          <div className="space-y-4">
            {[1, 2, 3].map(i => (
              <div key={i} className="animate-pulse bg-white/5 border border-white/10 rounded-2xl p-5">
                <div className="h-4 w-32 bg-white/5 rounded-xl mb-3" />
                <div className="space-y-2">
                  <div className="h-3 w-full bg-white/5 rounded-xl" />
                  <div className="h-3 w-3/4 bg-white/5 rounded-xl" />
                </div>
              </div>
            ))}
          </div>
        )}

        {!loading && !error && (
          <>
            <div className={`mb-6 rounded-2xl p-4 flex items-center gap-3 ${healthy ? 'bg-green-500/10 border border-green-500/30' : 'bg-red-500/10 border border-red-500/30'}`}>
              {healthy ? (
                <CheckCircle size={20} className="text-green-400 shrink-0" />
              ) : (
                <AlertCircle size={20} className="text-red-400 shrink-0" />
              )}
              <p className={`text-sm font-semibold ${healthy ? 'text-green-400' : 'text-red-400'}`}>
                {healthy ? '系统健康，所有检查通过' : '系统存在异常，请检查下方 FAIL 项'}
              </p>
            </div>

             <div className="space-y-6">
               {sections.map(section => {
                 const sectionChecks = checks.filter(c => c.section === section);
                 return (
                  <div key={section} className="bg-white/[0.03] border border-white/10 rounded-3xl p-6">
                    <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-4">
                      {section}
                    </h3>
                    <div className="space-y-3">
                      {sectionChecks.map(check => (
                        <div key={check.name} className="flex items-start justify-between gap-4">
                          <div className="flex items-center gap-3 min-w-0">
                            {check.ok ? (
                              <CheckCircle size={16} className="text-green-400 shrink-0 mt-0.5" />
                            ) : (
                              <AlertCircle size={16} className="text-red-400 shrink-0 mt-0.5" />
                            )}
                            <div className="min-w-0">
                              <p className="text-sm text-gray-200 truncate">{check.name}</p>
                              <p className="text-xs text-gray-500 truncate">{check.detail}</p>
                            </div>
                          </div>
                          <span className={`text-[10px] font-semibold px-2 py-1 rounded-full shrink-0 ${check.ok ? 'bg-green-500/10 text-green-400' : 'bg-red-500/10 text-red-400'}`}>
                            {check.ok ? 'OK' : 'FAIL'}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                );
              })}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
