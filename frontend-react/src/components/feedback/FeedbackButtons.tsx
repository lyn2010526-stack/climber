import { useState } from 'react';
import { ThumbsUp, ThumbsDown, X } from 'lucide-react';
import { api } from '../../api';

interface FeedbackButtonsProps {
  messageId: string;
  initialRating?: 'up' | 'down' | null;
}

const REASONS = [
  { value: 'factual_error', label: 'Factual Error' },
  { value: 'format', label: 'Format Issue' },
  { value: 'incomplete', label: 'Incomplete' },
  { value: 'irrelevant', label: 'Irrelevant' },
  { value: 'other', label: 'Other' },
] as const;

export function FeedbackButtons({ messageId, initialRating = null }: FeedbackButtonsProps) {
  const [rating, setRating] = useState<'up' | 'down' | null>(initialRating);
  const [showReasons, setShowReasons] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  const handleRate = async (value: 'up' | 'down') => {
    if (rating === value) {
      setRating(null);
      return;
    }

    setRating(value);
    setSubmitted(false);

    if (value === 'down') {
      setShowReasons(true);
    } else {
      await submitFeedback(value);
    }
  };

  const handleReasonSelect = async (reason: string) => {
    setShowReasons(false);
    await submitFeedback('down', reason);
  };

  const submitFeedback = async (value: 'up' | 'down', reason?: string) => {
    try {
      await api.submitFeedback(messageId, value, reason);
      setSubmitted(true);
      setTimeout(() => setSubmitted(false), 2000);
    } catch {
      // silently fail
    }
  };

  return (
    <div className="relative flex items-center gap-1">
      <button
        onClick={() => handleRate('up')}
        className={`p-1.5 rounded-md transition-colors ${
          rating === 'up'
            ? 'bg-green-500/20 text-green-400'
            : 'text-gray-500 hover:text-gray-400 hover:bg-gray-700/50'
        }`}
         title="有用"
      >
        <ThumbsUp size={14} />
      </button>
      <button
        onClick={() => handleRate('down')}
        className={`p-1.5 rounded-md transition-colors ${
          rating === 'down'
            ? 'bg-red-500/20 text-red-400'
            : 'text-gray-500 hover:text-gray-400 hover:bg-gray-700/50'
        }`}
         title="没用"
      >
        <ThumbsDown size={14} />
      </button>

      {submitted && (
         <span className="text-[10px] text-green-400 ml-1">已保存</span>
      )}

      {showReasons && (
        <div className="absolute bottom-full left-0 mb-2 z-50 bg-gray-800 border border-gray-700 rounded-lg shadow-xl p-2 min-w-[160px]">
          <div className="flex items-center justify-between px-2 pb-1.5 mb-1.5 border-b border-gray-700/50">
             <span className="text-xs text-gray-400 font-medium">为什么没用？</span>
            <button
              onClick={() => setShowReasons(false)}
              className="p-0.5 text-gray-500 hover:text-gray-400 rounded transition-colors"
            >
              <X size={12} />
            </button>
          </div>
          {REASONS.map((r) => (
            <button
              key={r.value}
              onClick={() => handleReasonSelect(r.value)}
              className="w-full text-left px-2 py-1.5 text-xs text-gray-400 hover:text-gray-100 hover:bg-gray-700/50 rounded transition-colors"
            >
              {r.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
