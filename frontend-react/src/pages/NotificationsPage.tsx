import { useState } from 'react';
import { Bell, Send, CheckCircle, AlertCircle } from 'lucide-react';

export function NotificationsPage() {
  const [title, setTitle] = useState('Climber 通知测试');
  const [message, setMessage] = useState('这是一条测试通知');
  const [result, setResult] = useState<{ ok: boolean; error?: string } | null>(null);
  const [sending, setSending] = useState(false);

  const send = async () => {
    setSending(true);
    setResult(null);
    try {
      const res = await fetch('/api/v1/notifications/send', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title, message }),
      });
      const data = await res.json();
      setResult(data);
    } catch (e: any) {
      setResult({ ok: false, error: e.message });
    } finally {
      setSending(false);
    }
  };

  const test = async () => {
    setSending(true);
    setResult(null);
    try {
      const res = await fetch('/api/v1/notifications/test');
      const data = await res.json();
      setResult(data);
    } catch (e: any) {
      setResult({ ok: false, error: e.message });
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="h-full overflow-y-auto p-8">
      <div className="max-w-3xl mx-auto">
        <div className="mb-8">
          <h2 className="text-2xl font-bold text-white flex items-center gap-3">
            <Bell size={24} className="text-[#007AFF]" />
            通知中心
          </h2>
          <p className="text-gray-400 text-sm mt-1.5">
            测试桌面通知，任务完成或出错时会自动弹出提醒。
          </p>
        </div>

        <div className="space-y-6">
          <div className="bg-white/[0.03] border border-white/10 rounded-3xl p-6">
            <h3 className="text-sm font-semibold text-white mb-4">发送自定义通知</h3>
            <div className="space-y-4">
              <div>
                <label className="block text-xs text-gray-400 mb-1.5">标题</label>
                <input
                  type="text"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  className="w-full px-4 py-2.5 bg-white/5 border border-white/10 rounded-2xl text-sm text-gray-100 focus:outline-none focus:border-[#007AFF]/50"
                />
              </div>
              <div>
                <label className="block text-xs text-gray-400 mb-1.5">内容</label>
                <textarea
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                  rows={3}
                  className="w-full px-4 py-2.5 bg-white/5 border border-white/10 rounded-2xl text-sm text-gray-100 focus:outline-none focus:border-[#007AFF]/50 resize-none"
                />
              </div>
              <div className="flex gap-3">
                <button
                  onClick={send}
                  disabled={sending || !title.trim() || !message.trim()}
                  className="flex items-center gap-2 px-5 py-2.5 bg-[#007AFF] text-white rounded-2xl text-sm font-semibold hover:bg-[#007AFF]/90 disabled:opacity-50 transition-all"
                >
                  <Send size={14} />
                  发送通知
                </button>
                <button
                  onClick={test}
                  disabled={sending}
                  className="flex items-center gap-2 px-5 py-2.5 bg-white/5 border border-white/10 text-gray-300 rounded-2xl text-sm font-semibold hover:bg-white/10 disabled:opacity-50 transition-all"
                >
                  <Bell size={14} />
                  系统测试
                </button>
              </div>
            </div>
          </div>

          {result && (
            <div className={`rounded-2xl p-4 flex items-center gap-3 ${result.ok ? 'bg-green-500/10 border border-green-500/30' : 'bg-red-500/10 border border-red-500/30'}`}>
              {result.ok ? (
                <CheckCircle size={18} className="text-green-400 shrink-0" />
              ) : (
                <AlertCircle size={18} className="text-red-400 shrink-0" />
              )}
              <p className={`text-sm ${result.ok ? 'text-green-400' : 'text-red-400'}`}>
                {result.ok ? '通知已发送' : `发送失败: ${result.error || '未知错误'}`}
              </p>
            </div>
          )}

          <div className="bg-white/[0.03] border border-white/10 rounded-3xl p-6">
            <h3 className="text-sm font-semibold text-white mb-3">通知说明</h3>
            <ul className="text-xs text-gray-400 space-y-2 list-disc list-inside">
              <li>通知通过系统原生机制发送（Linux notify-send / macOS osascript / Windows PowerShell）</li>
              <li>如果系统不支持桌面通知，会自动跳过，不会影响应用运行</li>
              <li>任务完成、失败或需要审批时，系统会自动触发通知</li>
              <li>通知服务在后台运行，不占用前端资源</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}
