export type AgentRole = 'plan' | 'research' | 'code' | 'review' | 'analysis' | 'write' | 'ops';

export interface AgentVisualIdentity {
  hue: number;
  initials: string;
  role: AgentRole | null;
}

export interface AgentIdentityInput {
  id?: string | null;
  name?: string | null;
  provider?: string | null;
}

export const AGENT_IDENTITY_PALETTE = [
  '#5B6ABF',
  '#3E8E7E',
  '#B0783A',
  '#8A5FBF',
  '#4F79A6',
  '#A8556D',
  '#5E8C4F',
  '#7A6E52',
] as const;

const ROLE_RULES: Array<{ role: AgentRole; keywords: string[] }> = [
  { role: 'plan', keywords: ['planner', 'architect'] },
  { role: 'research', keywords: ['researcher'] },
  { role: 'code', keywords: ['coder', 'engineer', 'developer'] },
  { role: 'review', keywords: ['reviewer'] },
  { role: 'analysis', keywords: ['analyst'] },
  { role: 'write', keywords: ['writer'] },
  { role: 'ops', keywords: ['operator'] },
];

function djb2Hash(input: string): number {
  let hash = 5381;
  for (let i = 0; i < input.length; i++) {
    hash = (((hash << 5) + hash) + input.charCodeAt(i)) >>> 0;
  }
  return hash >>> 0;
}

function firstNonEmpty(...values: Array<string | null | undefined>): string | null {
  for (const v of values) {
    if (typeof v === 'string' && v.trim().length > 0) return v.trim();
  }
  return null;
}

export function hashAgentIdentity(input: AgentIdentityInput): number {
  const seed = firstNonEmpty(input.id, input.name, input.provider);
  return djb2Hash(seed ?? '');
}

export function hueFromHash(hash: number): number {
  return hash % AGENT_IDENTITY_PALETTE.length;
}

export function paletteColor(hue: number): string {
  const idx = ((hue % AGENT_IDENTITY_PALETTE.length) + AGENT_IDENTITY_PALETTE.length) % AGENT_IDENTITY_PALETTE.length;
  return AGENT_IDENTITY_PALETTE[idx] ?? AGENT_IDENTITY_PALETTE[0];
}

export function initialsFromName(name?: string | null): string {
  if (!name) return '?';
  const trimmed = name.trim();
  if (!trimmed) return '?';
  const words = trimmed.split(/[\s\-_/.,:;()#]+/).filter(w => w.length > 0);
  if (words.length >= 2) {
    const first = words[0]?.[0] ?? '';
    const second = words[1]?.[0] ?? '';
    return (first + second).toUpperCase() || '?';
  }
  const single = words[0] ?? '';
  return single.slice(0, 2).toUpperCase() || '?';
}

export function classifyAgentRole(input: AgentIdentityInput): AgentRole | null {
  const haystack = `${input.name ?? ''} ${input.id ?? ''} ${input.provider ?? ''}`.toLowerCase();
  for (const rule of ROLE_RULES) {
    if (rule.keywords.some(k => haystack.includes(k))) {
      return rule.role;
    }
  }
  return null;
}

export function buildAgentVisualIdentity(input: AgentIdentityInput): AgentVisualIdentity {
  const hash = hashAgentIdentity(input);
  return {
    hue: hueFromHash(hash),
    initials: initialsFromName(firstNonEmpty(input.name, input.id)),
    role: classifyAgentRole(input),
  };
}
