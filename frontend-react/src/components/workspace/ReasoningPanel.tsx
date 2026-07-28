import { useState, useCallback } from 'react';
import {
  Brain, GitBranch, Target, Shield, AlertTriangle, CheckCircle2,
  ChevronDown, ChevronRight, Zap, MessageSquare, Scale, Loader2,
  ThumbsUp, ThumbsDown, Star,
} from 'lucide-react';
import { api } from '../../api';

interface ReasoningMode {
  id: string;
  name: string;
  description: string;
  available: boolean;
}

interface PathTrace {
  candidate_id: string;
  path_type: string;
  rounds: Array<{ round_num: number; action: string; output_summary: string }>;
  final_confidence: number;
}

interface CoverageReport {
  score: number;
  edge_cases_count: number;
  risks_count: number;
  assumptions_count: number;
  blind_spots_count: number;
  high_risks: number;
  checklist: Record<string, boolean>;
}

interface ReasoningResult {
  answer: string;
  mode_used: string;
  candidates: Array<{
    id: string;
    strategy: string;
    path_type: string;
    content: string;
    confidence: number;
    metadata: Record<string, any>;
  }>;
  coverage: CoverageReport | null;
  total_duration_ms: number;
  trace: {
    trace_id: string;
    path_traces: PathTrace[];
    coverage_checks: any[];
    final_selection_reason: string;
  } | null;
}

export function ReasoningPanel() {
  const [task, setTask] = useState('');
  const [mode, setMode] = useState('auto');
  const [maxPaths, setMaxPaths] = useState(3);
  const [maxRounds, setMaxRounds] = useState(3);
  const [coverageEnabled, setCoverageEnabled] = useState(true);
  const [modes, setModes] = useState<ReasoningMode[]>([]);
  const [result, setResult] = useState<ReasoningResult | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expandedPaths, setExpandedPaths] = useState<Set<string>>(new Set());
  const [feedbackRating, setFeedbackRating] = useState(0);
  const [feedbackThumbs, setFeedbackThumbs] = useState<'up' | 'down' | null>(null);
  const [feedbackComment, setFeedbackComment] = useState('');
  const [feedbackSubmitted, setFeedbackSubmitted] = useState(false);

  const loadModes = useCallback(async () => {
    try {
      const data = await api.listReasoningModes();
      setModes(data);
    } catch { /* skip */ }
  }, []);

  const handleReason = async () => {
    if (!task.trim()) return;
    setIsRunning(true);
    setError(null);
    setResult(null);

    if (modes.length === 0) await loadModes();

    try {
      const data = await api.reasonStream(task, mode, maxPaths, maxRounds, coverageEnabled, () => {});
      setResult(data);
    } catch (err: any) {
      setError(err.message || 'Reasoning failed');
    } finally {
      setIsRunning(false);
    }
  };

  const togglePathExpand = (id: string) => {
    setExpandedPaths(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const handleFeedback = async () => {
    if (!result?.trace?.trace_id || feedbackRating === 0) return;
    try {
      const feedback: { rating: number; thumbs?: string; comment?: string } = {
        rating: feedbackRating,
        comment: feedbackComment,
      };
      if (feedbackThumbs !== undefined && feedbackThumbs !== null) {
        feedback['thumbs'] = feedbackThumbs;
      }
      await api.submitReasoningFeedback(result.trace.trace_id, feedback);
      setFeedbackSubmitted(true);
    } catch { /* skip */ }
  };

  const getModeIcon = (modeId: string) => {
    switch (modeId) {
      case 'tree': return <GitBranch size={14} />;
      case 'deep': return <Zap size={14} />;
      case 'debate': return <Scale size={14} />;
      default: return <Brain size={14} />;
    }
  };

  return (
    <div className="flex flex-col h-full bg-gray-900">
      {/* Input Section */}
      <div className="p-4 border-b border-gray-700 space-y-3">
        <div className="flex items-center gap-2">
          <Brain size={16} className="text-purple-400" />
          <h3 className="text-sm font-semibold text-gray-100">推理引擎</h3>
        </div>

        <textarea
          value={task}
          onChange={(e) => setTask(e.target.value)}
          placeholder="输入一个复杂任务以进行多策略推理..."
          className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-sm text-gray-100 placeholder-gray-500 focus:outline-none focus:border-purple-500/50 resize-none"
          rows={3}
        />

        <div className="flex gap-2">
          <select
            value={mode}
            onChange={(e) => setMode(e.target.value)}
            className="flex-1 px-3 py-1.5 bg-gray-800 border border-gray-700 rounded text-xs text-gray-200 focus:outline-none focus:border-purple-500/50"
          >
            <option value="auto">自动</option>
            <option value="tree">思维树</option>
            <option value="deep">深度反思</option>
            <option value="debate">辩论</option>
          </select>
          <select
            value={maxPaths}
            onChange={(e) => setMaxPaths(Number(e.target.value))}
            className="px-2 py-1.5 bg-gray-800 border border-gray-700 rounded text-xs text-gray-200 focus:outline-none"
          >
            <option value={1}>1 条路径</option>
            <option value={2}>2 条路径</option>
            <option value={3}>3 条路径</option>
            <option value={5}>5 条路径</option>
          </select>
          <select
            value={maxRounds}
            onChange={(e) => setMaxRounds(Number(e.target.value))}
            className="px-2 py-1.5 bg-gray-800 border border-gray-700 rounded text-xs text-gray-200 focus:outline-none"
          >
            <option value={1}>1 轮</option>
            <option value={2}>2 轮</option>
            <option value={3}>3 轮</option>
            <option value={5}>5 轮</option>
          </select>
        </div>

        <div className="flex items-center justify-between">
          <label className="flex items-center gap-2 text-xs text-gray-400 cursor-pointer">
            <input
              type="checkbox"
              checked={coverageEnabled}
              onChange={(e) => setCoverageEnabled(e.target.checked)}
              className="rounded border-gray-600 bg-gray-800 text-purple-500 focus:ring-purple-500/30"
            />
             覆盖率检查
          </label>

          <button
            onClick={handleReason}
            disabled={isRunning || !task.trim()}
            className="flex items-center gap-1.5 px-4 py-1.5 bg-purple-600 hover:bg-purple-700 disabled:bg-gray-700 disabled:text-gray-500 text-white rounded-lg text-xs font-medium transition-all"
          >
            {isRunning ? <Loader2 size={12} className="animate-spin" /> : <Zap size={12} />}
             {isRunning ? '推理中...' : '推理'}
          </button>
        </div>
      </div>

      {/* Results Section */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {error && (
          <div className="p-3 bg-red-900/30 border border-red-700/50 rounded-lg text-xs text-red-300">
            <AlertTriangle size={12} className="inline mr-1" />
            {error}
          </div>
        )}

        {!result && !isRunning && (
          <div className="text-center py-8 text-gray-500 text-xs">
            <Brain size={32} className="mx-auto mb-3 opacity-30" />
             <p>输入任务并点击"推理"开始多策略推理。</p>
             <div className="mt-4 space-y-1 text-left px-4">
               <p className="text-gray-400 font-medium">可用策略：</p>
               <p className="pl-2"><span className="text-green-400">思维树</span> — 多路径并行探索</p>
               <p className="pl-2"><span className="text-blue-400">深度反思</span> — 迭代细化与回溯</p>
               <p className="pl-2"><span className="text-yellow-400">辩论</span> — 多智能体辩论收敛</p>
             </div>
          </div>
        )}

        {isRunning && (
          <div className="flex flex-col items-center justify-center py-12 text-gray-400">
            <Loader2 size={32} className="animate-spin mb-3 text-purple-400" />
             <p className="text-sm">推理进行中...</p>
             <p className="text-xs mt-1 text-gray-500">模式: {mode} | 路径: {maxPaths} | 轮次: {maxRounds}</p>
          </div>
        )}

        {result && !isRunning && (
          <>
            {/* Summary */}
            <div className="p-3 bg-gray-800 rounded-lg border border-gray-700">
              <div className="flex items-center gap-2 mb-2">
                <CheckCircle2 size={14} className="text-green-400" />
                 <span className="text-xs font-medium text-gray-200">推理完成</span>
                <span className="ml-auto text-xs text-gray-500">{result.total_duration_ms.toFixed(0)}ms</span>
              </div>
              <div className="flex gap-3 text-xs text-gray-400">
                <span className="flex items-center gap-1">{getModeIcon(result.mode_used)} {result.mode_used}</span>
                 <span>{result.candidates.length} 个候选</span>
                 {result.coverage && <span>覆盖率: {(result.coverage.score * 100).toFixed(0)}%</span>}
              </div>
            </div>

            {/* Coverage Dashboard */}
            {result.coverage && result.coverage.score > 0 && (
              <div className="p-3 bg-gray-800 rounded-lg border border-gray-700">
                <div className="flex items-center gap-2 mb-2">
                  <Shield size={13} className="text-blue-400" />
                   <span className="text-xs font-medium text-gray-200">覆盖率报告</span>
                </div>
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div className="flex items-center justify-between p-2 bg-gray-900 rounded">
                     <span className="text-gray-400">边界情况</span>
                    <span className="text-gray-200 font-mono">{result.coverage.edge_cases_count}</span>
                  </div>
                  <div className="flex items-center justify-between p-2 bg-gray-900 rounded">
                     <span className="text-gray-400">风险</span>
                    <span className="text-gray-200 font-mono">{result.coverage.risks_count}</span>
                  </div>
                  <div className="flex items-center justify-between p-2 bg-gray-900 rounded">
                     <span className="text-gray-400">假设</span>
                    <span className="text-gray-200 font-mono">{result.coverage.assumptions_count}</span>
                  </div>
                  <div className="flex items-center justify-between p-2 bg-gray-900 rounded">
                     <span className="text-gray-400">盲点</span>
                    <span className="text-gray-200 font-mono">{result.coverage.blind_spots_count}</span>
                  </div>
                </div>
                {result.coverage.high_risks > 0 && (
                  <div className="mt-2 p-2 bg-red-900/20 border border-red-700/30 rounded text-xs text-red-300">
                    <AlertTriangle size={11} className="inline mr-1" />
                     检测到 {result.coverage.high_risks} 个高风险问题
                  </div>
                )}
              </div>
            )}

            {/* Path Comparison */}
            {result.trace?.path_traces && result.trace.path_traces.length > 0 && (
              <div className="space-y-2">
                <div className="flex items-center gap-2 text-xs font-medium text-gray-300">
                  <GitBranch size={13} />
                   <span>路径对比</span>
                </div>
                {result.trace.path_traces.map((path) => (
                  <div key={path.candidate_id} className="bg-gray-800 rounded-lg border border-gray-700 overflow-hidden">
                    <button
                      onClick={() => togglePathExpand(path.candidate_id)}
                      className="w-full flex items-center gap-2 px-3 py-2 text-xs text-left hover:bg-gray-750"
                    >
                      {expandedPaths.has(path.candidate_id) ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
                      <span className="text-purple-300 font-mono">{path.path_type}</span>
                      <span className="ml-auto text-gray-400">
                        {path.final_confidence > 0 ? `${(path.final_confidence * 100).toFixed(0)}%` : '—'}
                      </span>
                    </button>
                    {expandedPaths.has(path.candidate_id) && (
                      <div className="border-t border-gray-700 p-2 space-y-1">
                        {path.rounds.map((round) => (
                          <div key={round.round_num} className="flex items-start gap-2 text-xs">
                            <span className="text-gray-500 font-mono w-14 shrink-0">R{round.round_num} {round.action}</span>
                            <span className="text-gray-400">{round.output_summary}</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}

            {/* Best Answer */}
            <div className="p-3 bg-gray-800 rounded-lg border border-purple-700/30">
              <div className="flex items-center gap-2 mb-2">
                <Target size={13} className="text-purple-400" />
                 <span className="text-xs font-medium text-gray-200">最佳答案</span>
              </div>
              <div className="text-sm text-gray-300 whitespace-pre-wrap max-h-64 overflow-y-auto">
                {result.answer}
              </div>
            </div>

            {/* Feedback Section */}
            {!feedbackSubmitted ? (
              <div className="p-3 bg-gray-800/50 rounded-lg border border-gray-700/50 space-y-2">
                 <span className="text-xs font-medium text-gray-400">评价此推理</span>
                <div className="flex items-center gap-3">
                  <div className="flex gap-1">
                    {[1, 2, 3, 4, 5].map((star) => (
                      <button
                        key={star}
                        onClick={() => setFeedbackRating(star)}
                        className={`p-1 rounded ${feedbackRating >= star ? 'text-yellow-400' : 'text-gray-600 hover:text-gray-400'}`}
                      >
                        <Star size={14} fill={feedbackRating >= star ? 'currentColor' : 'none'} />
                      </button>
                    ))}
                  </div>
                  <div className="flex gap-2">
                    <button
                      onClick={() => setFeedbackThumbs(feedbackThumbs === 'up' ? null : 'up')}
                      className={`p-1 rounded ${feedbackThumbs === 'up' ? 'text-green-400 bg-green-400/10' : 'text-gray-500 hover:text-gray-300'}`}
                    >
                      <ThumbsUp size={14} />
                    </button>
                    <button
                      onClick={() => setFeedbackThumbs(feedbackThumbs === 'down' ? null : 'down')}
                      className={`p-1 rounded ${feedbackThumbs === 'down' ? 'text-red-400 bg-red-400/10' : 'text-gray-500 hover:text-gray-300'}`}
                    >
                      <ThumbsDown size={14} />
                    </button>
                  </div>
                </div>
                <textarea
                  value={feedbackComment}
                  onChange={(e) => setFeedbackComment(e.target.value)}
                   placeholder="可选评论..."
                  className="w-full px-2 py-1 bg-gray-900 border border-gray-700 rounded text-xs text-gray-300 placeholder-gray-500 focus:outline-none resize-none"
                  rows={2}
                />
                <button
                  onClick={handleFeedback}
                  disabled={feedbackRating === 0}
                  className="px-3 py-1 bg-purple-600 hover:bg-purple-500 disabled:bg-gray-700 disabled:text-gray-500 text-white text-xs rounded transition-colors"
                >
                   提交反馈
                </button>
              </div>
            ) : (
              <div className="p-2 bg-green-900/20 rounded-lg border border-green-700/30 text-xs text-green-300 text-center">
                 感谢你的反馈！
              </div>
            )}

            {/* Selection Reason */}
            {result.trace?.final_selection_reason && (
              <div className="p-3 bg-gray-800 rounded-lg border border-gray-700">
                <div className="flex items-center gap-2 mb-1">
                  <MessageSquare size={13} className="text-gray-400" />
                   <span className="text-xs font-medium text-gray-300">选择理由</span>
                </div>
                <p className="text-xs text-gray-400">{result.trace.final_selection_reason}</p>
              </div>
            )}

            {/* Candidate List */}
            {result.candidates.length > 1 && (
              <div className="space-y-2">
                 <span className="text-xs font-medium text-gray-400">所有候选 ({result.candidates.length})</span>
                {result.candidates.map((c) => (
                  <div key={c.id} className="p-2 bg-gray-800 rounded border border-gray-700 text-xs">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-purple-300 font-mono">{c.path_type || c.strategy}</span>
                      <span className="text-gray-400">{(c.confidence * 100).toFixed(0)}%</span>
                    </div>
                    <p className="text-gray-500 line-clamp-2">{c.content?.slice(0, 150)}...</p>
                  </div>
                ))}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
