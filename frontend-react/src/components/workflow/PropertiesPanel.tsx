import { useState } from 'react';
import { Trash2, AlertCircle } from 'lucide-react';
import type { Node } from '@xyflow/react';

interface PropertiesPanelProps {
  node: Node;
  onUpdate: (nodeId: string, data: Record<string, any>) => void;
  onDelete: () => void;
}

const FIELD_CONFIG: Record<string, { label: string; type: 'text' | 'select' | 'textarea'; options?: string[] }[]> = {
  input: [
    { label: 'Label', type: 'text' },
    { label: 'Description', type: 'textarea' },
    { label: 'Variable Name', type: 'text' },
    { label: 'Required', type: 'select', options: ['true', 'false'] },
  ],
  llm: [
    { label: 'Label', type: 'text' },
    { label: 'Model', type: 'select', options: ['gpt-4', 'gpt-3.5-turbo', 'claude-3-opus', 'claude-3-sonnet', 'llama-3'] },
    { label: 'System Prompt', type: 'textarea' },
    { label: 'Temperature', type: 'text' },
    { label: 'Max Tokens', type: 'text' },
  ],
  tool: [
    { label: 'Label', type: 'text' },
    { label: 'Tool Name', type: 'select', options: ['web_search', 'calculator', 'file_reader', 'code_executor', 'http_request'] },
    { label: 'Parameters (JSON)', type: 'textarea' },
  ],
  condition: [
    { label: 'Label', type: 'text' },
    { label: 'Variable', type: 'text' },
    { label: 'Operator', type: 'select', options: ['equals', 'not_equals', 'contains', 'not_empty', 'greater_than', 'less_than'] },
    { label: 'Expected Value', type: 'text' },
  ],
  output: [
    { label: 'Label', type: 'text' },
    { label: 'Description', type: 'textarea' },
    { label: 'Format', type: 'select', options: ['text', 'json', 'markdown'] },
  ],
};

export function PropertiesPanel({ node, onUpdate, onDelete }: PropertiesPanelProps) {
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const fields = FIELD_CONFIG[node.type || ''] || [];

  const handleChange = (key: string, value: string) => {
    onUpdate(node.id, { [key]: value });
  };

  const fieldKey = (label: string) => label.toLowerCase().replace(/\s+/g, '_');

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between p-3 border-b border-gray-700">
        <h3 className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider">
          Node Properties
        </h3>
        <div className="flex items-center gap-1">
          <button
            onClick={() => setShowDeleteConfirm(true)}
            className="p-1 rounded hover:bg-red-500/10 text-gray-500 hover:text-red-400 transition-colors"
          >
            <Trash2 size={12} />
          </button>
        </div>
      </div>

      {/* Node Info */}
      <div className="p-3 border-b border-gray-700">
        <div className="flex items-center gap-2 mb-1">
          <span className="text-xs font-medium text-gray-100 capitalize">{node.type}</span>
          <span className="text-[9px] text-gray-500 font-mono">{node.id}</span>
        </div>
      </div>

      {/* Fields */}
      <div className="flex-1 overflow-y-auto p-3 space-y-3">
        {fields.map((field) => {
          const key = fieldKey(field.label);
          const value = (node.data as any)?.[key] || '';

          return (
            <div key={field.label}>
              <label className="block text-[10px] font-medium text-gray-500 mb-1">
                {field.label}
              </label>
              {field.type === 'select' ? (
                <select
                  value={value}
                  onChange={(e) => handleChange(key, e.target.value)}
                  className="w-full px-2 py-1.5 bg-gray-700 border border-gray-700 rounded text-[11px] text-gray-100 focus:outline-none focus:border-blue-500/50"
                >
                  <option value="">Select...</option>
                  {field.options?.map((opt) => (
                    <option key={opt} value={opt}>{opt}</option>
                  ))}
                </select>
              ) : field.type === 'textarea' ? (
                <textarea
                  value={value}
                  onChange={(e) => handleChange(key, e.target.value)}
                  rows={3}
                  className="w-full px-2 py-1.5 bg-gray-700 border border-gray-700 rounded text-[11px] text-gray-100 placeholder:text-gray-500 focus:outline-none focus:border-blue-500/50 resize-none"
                  placeholder={`Enter ${fieldKey(field.label)}...`}
                />
              ) : (
                <input
                  type="text"
                  value={value}
                  onChange={(e) => handleChange(key, e.target.value)}
                  className="w-full px-2 py-1.5 bg-gray-700 border border-gray-700 rounded text-[11px] text-gray-100 placeholder:text-gray-500 focus:outline-none focus:border-blue-500/50"
                  placeholder={`Enter ${fieldKey(field.label)}...`}
                />
              )}
            </div>
          );
        })}
      </div>

      {/* Delete Confirmation */}
      {showDeleteConfirm && (
        <div className="absolute inset-0 bg-gray-900/80 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="p-4 bg-gray-800 border border-gray-700 rounded-xl shadow-xl max-w-[240px]">
            <div className="flex items-center gap-2 mb-3">
              <AlertCircle size={16} className="text-red-400" />
              <span className="text-xs font-medium text-gray-100">Delete Node?</span>
            </div>
            <p className="text-[10px] text-gray-500 mb-4">
              This will remove the node and all its connections.
            </p>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setShowDeleteConfirm(false)}
                className="flex-1 px-3 py-1.5 text-[11px] text-gray-400 bg-gray-700 rounded-lg hover:bg-gray-700/50 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={() => {
                  onDelete();
                  setShowDeleteConfirm(false);
                }}
                className="flex-1 px-3 py-1.5 text-[11px] text-white bg-red-500 rounded-lg hover:bg-red-500/90 transition-colors"
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
