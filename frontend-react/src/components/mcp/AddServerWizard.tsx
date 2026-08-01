import React, { useState } from 'react';
import { cn } from '../../lib/utils';
import {
  X, ArrowRight, ArrowLeft, Check, Loader2,
  Terminal, Globe, Radio, Shield, Zap,
} from 'lucide-react';

type TransportType = 'stdio' | 'http' | 'sse';

interface WizardData {
  transport: TransportType;
  name: string;
  command: string;
  url: string;
  args: string;
  env: string;
  oauth: boolean;
  tokenUrl: string;
}

const steps = [
  { id: 0, label: '传输方式', description: '选择连接协议' },
  { id: 1, label: '配置连接', description: '填写连接参数' },
  { id: 2, label: '认证', description: 'OAuth 配置（可选）' },
  { id: 3, label: '确认', description: '测试并添加' },
];

const transportOptions: Array<{ type: TransportType; label: string; description: string; icon: React.ComponentType<any> }> = [
  { type: 'stdio', label: '标准输入输出 (stdio)', description: '通过命令行启动本地进程通信', icon: Terminal },
  { type: 'http', label: 'HTTP', description: '通过 HTTP 协议连接远程服务器', icon: Globe },
  { type: 'sse', label: 'SSE (Server-Sent Events)', description: '通过 SSE 协议进行流式通信', icon: Radio },
];

interface AddServerWizardProps {
  isOpen: boolean;
  onClose: () => void;
  onAdd: (data: WizardData) => void;
}

export function AddServerWizard({ isOpen, onClose, onAdd }: AddServerWizardProps) {
  const [step, setStep] = useState(0);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<'success' | 'error' | null>(null);
  const [data, setData] = useState<WizardData>({
    transport: 'stdio',
    name: '',
    command: '',
    url: '',
    args: '',
    env: '',
    oauth: false,
    tokenUrl: '',
  });

  if (!isOpen) return null;

  const canNext = () => {
    if (step === 0) return true;
    if (step === 1) {
      if (data.transport === 'stdio') return data.name && data.command;
      return data.name && data.url;
    }
    if (step === 2) return true;
    return testResult === 'success';
  };

  const handleTest = async () => {
    setTesting(true);
    setTestResult(null);
    await new Promise(r => setTimeout(r, 1500));
    setTesting(false);
    setTestResult('success');
  };

  const handleFinish = () => {
    onAdd(data);
    setStep(0);
    setData({
      transport: 'stdio',
      name: '',
      command: '',
      url: '',
      args: '',
      env: '',
      oauth: false,
      tokenUrl: '',
    });
    setTestResult(null);
    onClose();
  };

  const handleClose = () => {
    setStep(0);
    setTestResult(null);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center" onClick={handleClose}>
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" />
      <div
        className="relative w-full max-w-xl bg-[#12121A] border border-white/[0.08] rounded-2xl shadow-2xl overflow-hidden"
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-white/[0.06]">
          <div>
            <h3 className="text-sm font-semibold text-white">添加 MCP 服务器</h3>
            <p className="text-[11px] text-gray-500 mt-0.5">配置新的模型上下文协议服务器</p>
          </div>
          <button onClick={handleClose} className="p-1.5 rounded-lg hover:bg-white/[0.06] text-gray-500 hover:text-gray-300 transition-colors">
            <X size={16} />
          </button>
        </div>

        {/* Step indicator */}
        <div className="px-6 py-4 border-b border-white/[0.04]">
          <div className="flex items-center gap-2">
            {steps.map((s, i) => (
              <React.Fragment key={s.id}>
                <div className="flex items-center gap-2">
                  <div className={cn(
                    'w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-semibold transition-all',
                    i < step ? 'bg-green-500/20 text-green-400' :
                    i === step ? 'bg-blue-500/20 text-blue-400 ring-2 ring-blue-500/30' :
                    'bg-white/[0.04] text-gray-600'
                  )}>
                    {i < step ? <Check size={12} /> : i + 1}
                  </div>
                  <span className={cn(
                    'text-[11px] font-medium hidden sm:inline',
                    i === step ? 'text-white' : 'text-gray-500'
                  )}>
                    {s.label}
                  </span>
                </div>
                {i < steps.length - 1 && (
                  <div className={cn('flex-1 h-px', i < step ? 'bg-green-500/30' : 'bg-white/[0.06]')} />
                )}
              </React.Fragment>
            ))}
          </div>
        </div>

        {/* Step content */}
        <div className="px-6 py-5 min-h-[240px]">
          {step === 0 && (
            <div className="space-y-3">
              <p className="text-xs text-gray-400 mb-4">选择服务器使用的传输协议</p>
              {transportOptions.map(opt => (
                <button
                  key={opt.type}
                  onClick={() => setData(d => ({ ...d, transport: opt.type }))}
                  className={cn(
                    'w-full flex items-center gap-4 p-4 rounded-xl border transition-all text-left',
                    data.transport === opt.type
                      ? 'border-blue-500/40 bg-blue-500/[0.06]'
                      : 'border-white/[0.06] bg-white/[0.02] hover:border-white/[0.1] hover:bg-white/[0.04]'
                  )}
                >
                  <div className={cn(
                    'w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0',
                    data.transport === opt.type ? 'bg-blue-500/20 text-blue-400' : 'bg-white/[0.04] text-gray-500'
                  )}>
                    <opt.icon size={18} />
                  </div>
                  <div>
                    <div className="text-sm font-medium text-white">{opt.label}</div>
                    <div className="text-[11px] text-gray-500 mt-0.5">{opt.description}</div>
                  </div>
                </button>
              ))}
            </div>
          )}

          {step === 1 && (
            <div className="space-y-4">
              <div>
                <label className="text-[11px] font-medium text-gray-400 mb-1.5 block">服务器名称</label>
                <input
                  type="text"
                  value={data.name}
                  onChange={e => setData(d => ({ ...d, name: e.target.value }))}
                  placeholder="my-mcp-server"
                  className="w-full h-10 px-3 rounded-xl bg-white/[0.04] border border-white/[0.08] text-sm text-gray-200 placeholder:text-gray-600 focus:outline-none focus:border-blue-500/40 transition-all"
                />
              </div>
              {data.transport === 'stdio' ? (
                <>
                  <div>
                    <label className="text-[11px] font-medium text-gray-400 mb-1.5 block">启动命令</label>
                    <input
                      type="text"
                      value={data.command}
                      onChange={e => setData(d => ({ ...d, command: e.target.value }))}
                      placeholder="npx -y @modelcontextprotocol/server-filesystem"
                      className="w-full h-10 px-3 rounded-xl bg-white/[0.04] border border-white/[0.08] text-sm text-gray-200 font-mono placeholder:text-gray-600 focus:outline-none focus:border-blue-500/40 transition-all"
                    />
                  </div>
                  <div>
                    <label className="text-[11px] font-medium text-gray-400 mb-1.5 block">参数（可选）</label>
                    <input
                      type="text"
                      value={data.args}
                      onChange={e => setData(d => ({ ...d, args: e.target.value }))}
                      placeholder="/path/to/directory"
                      className="w-full h-10 px-3 rounded-xl bg-white/[0.04] border border-white/[0.08] text-sm text-gray-200 font-mono placeholder:text-gray-600 focus:outline-none focus:border-blue-500/40 transition-all"
                    />
                  </div>
                </>
              ) : (
                <div>
                  <label className="text-[11px] font-medium text-gray-400 mb-1.5 block">服务器 URL</label>
                  <input
                    type="text"
                    value={data.url}
                    onChange={e => setData(d => ({ ...d, url: e.target.value }))}
                    placeholder={data.transport === 'sse' ? 'https://example.com/sse' : 'https://example.com/api'}
                    className="w-full h-10 px-3 rounded-xl bg-white/[0.04] border border-white/[0.08] text-sm text-gray-200 font-mono placeholder:text-gray-600 focus:outline-none focus:border-blue-500/40 transition-all"
                  />
                </div>
              )}
              <div>
                <label className="text-[11px] font-medium text-gray-400 mb-1.5 block">环境变量（可选）</label>
                <textarea
                  value={data.env}
                  onChange={e => setData(d => ({ ...d, env: e.target.value }))}
                  placeholder={"KEY=value\nANOTHER_KEY=value2"}
                  rows={3}
                  className="w-full px-3 py-2.5 rounded-xl bg-white/[0.04] border border-white/[0.08] text-sm text-gray-200 font-mono placeholder:text-gray-600 focus:outline-none focus:border-blue-500/40 transition-all resize-none"
                />
              </div>
            </div>
          )}

          {step === 2 && (
            <div className="space-y-4">
              <div className="flex items-center gap-3 p-4 rounded-xl bg-white/[0.03] border border-white/[0.06]">
                <Shield size={18} className="text-amber-400 flex-shrink-0" />
                <div className="flex-1">
                  <div className="text-sm font-medium text-white">OAuth 认证</div>
                  <div className="text-[11px] text-gray-500 mt-0.5">如果服务器需要 OAuth 认证，请启用此选项</div>
                </div>
                <button
                  onClick={() => setData(d => ({ ...d, oauth: !d.oauth }))}
                  className={cn(
                    'w-10 h-6 rounded-full transition-all relative',
                    data.oauth ? 'bg-blue-500' : 'bg-white/[0.1]'
                  )}
                >
                  <div className={cn(
                    'absolute top-1 w-4 h-4 rounded-full bg-white shadow transition-all',
                    data.oauth ? 'left-5' : 'left-1'
                  )} />
                </button>
              </div>
              {data.oauth && (
                <div>
                  <label className="text-[11px] font-medium text-gray-400 mb-1.5 block">Token URL</label>
                  <input
                    type="text"
                    value={data.tokenUrl}
                    onChange={e => setData(d => ({ ...d, tokenUrl: e.target.value }))}
                    placeholder="https://auth.example.com/oauth/token"
                    className="w-full h-10 px-3 rounded-xl bg-white/[0.04] border border-white/[0.08] text-sm text-gray-200 font-mono placeholder:text-gray-600 focus:outline-none focus:border-blue-500/40 transition-all"
                  />
                </div>
              )}
            </div>
          )}

          {step === 3 && (
            <div className="space-y-4">
              <div className="p-4 rounded-xl bg-white/[0.03] border border-white/[0.06] space-y-3">
                <div className="flex justify-between text-xs">
                  <span className="text-gray-500">名称</span>
                  <span className="text-gray-300 font-medium">{data.name}</span>
                </div>
                <div className="flex justify-between text-xs">
                  <span className="text-gray-500">传输方式</span>
                  <span className="text-gray-300 font-medium capitalize">{data.transport}</span>
                </div>
                <div className="flex justify-between text-xs">
                  <span className="text-gray-500">连接</span>
                  <span className="text-gray-300 font-mono text-[11px] truncate max-w-[200px]">
                    {data.transport === 'stdio' ? data.command : data.url}
                  </span>
                </div>
                {data.oauth && (
                  <div className="flex justify-between text-xs">
                    <span className="text-gray-500">OAuth</span>
                    <span className="text-amber-400 font-medium">已启用</span>
                  </div>
                )}
              </div>

              {!testResult && (
                <button
                  onClick={handleTest}
                  disabled={testing}
                  className="w-full py-3 rounded-xl bg-blue-500/10 text-blue-400 text-sm font-medium border border-blue-500/20 hover:bg-blue-500/15 transition-all flex items-center justify-center gap-2"
                >
                  {testing ? (
                    <>
                      <Loader2 size={14} className="animate-spin" />
                      测试连接中...
                    </>
                  ) : (
                    <>
                      <Zap size={14} />
                      测试连接
                    </>
                  )}
                </button>
              )}

              {testResult === 'success' && (
                <div className="flex items-center gap-3 p-4 rounded-xl bg-green-500/[0.06] border border-green-500/20">
                  <Check size={18} className="text-green-400" />
                  <div>
                    <div className="text-sm font-medium text-green-400">连接成功</div>
                    <div className="text-[11px] text-gray-500 mt-0.5">服务器响应正常，可以添加</div>
                  </div>
                </div>
              )}

              {testResult === 'error' && (
                <div className="flex items-center gap-3 p-4 rounded-xl bg-red-500/[0.06] border border-red-500/20">
                  <X size={18} className="text-red-400" />
                  <div>
                    <div className="text-sm font-medium text-red-400">连接失败</div>
                    <div className="text-[11px] text-gray-500 mt-0.5">请检查配置后重试</div>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-6 py-4 border-t border-white/[0.06]">
          <button
            onClick={() => setStep(s => Math.max(0, s - 1))}
            disabled={step === 0}
            className={cn(
              'flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-medium transition-all',
              step === 0
                ? 'text-gray-600 cursor-not-allowed'
                : 'text-gray-400 hover:text-white hover:bg-white/[0.06]'
            )}
          >
            <ArrowLeft size={13} />
            上一步
          </button>
          <div className="flex items-center gap-2">
            {step < 3 ? (
              <button
                onClick={() => setStep(s => Math.min(3, s + 1))}
                disabled={!canNext()}
                className={cn(
                  'flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-medium transition-all',
                  canNext()
                    ? 'bg-gradient-to-r from-blue-500 to-violet-500 text-white shadow-lg shadow-blue-500/20 hover:brightness-110'
                    : 'bg-white/[0.04] text-gray-600 cursor-not-allowed'
                )}
              >
                下一步
                <ArrowRight size={13} />
              </button>
            ) : (
              <button
                onClick={handleFinish}
                disabled={!canNext()}
                className={cn(
                  'flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-medium transition-all',
                  canNext()
                    ? 'bg-gradient-to-r from-green-500 to-emerald-500 text-white shadow-lg shadow-green-500/20 hover:brightness-110'
                    : 'bg-white/[0.04] text-gray-600 cursor-not-allowed'
                )}
              >
                <Check size={13} />
                添加服务器
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
