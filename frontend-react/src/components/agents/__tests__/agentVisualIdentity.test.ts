import { describe, it, expect } from 'vitest';
import {
  buildAgentVisualIdentity,
  hashAgentIdentity,
  hueFromHash,
  initialsFromName,
  classifyAgentRole,
  paletteColor,
  AGENT_IDENTITY_PALETTE,
} from '../agentVisualIdentity';

describe('agentVisualIdentity', () => {
  it('is stable for the same id', () => {
    const a = buildAgentVisualIdentity({ id: 'agent-42', name: 'Planner Alpha', provider: 'openai' });
    const b = buildAgentVisualIdentity({ id: 'agent-42', name: 'Renamed Later', provider: 'anthropic' });
    expect(a.hue).toBe(b.hue);
  });

  it('hue stays within the palette range', () => {
    for (let i = 0; i < 200; i++) {
      const hue = hueFromHash(hashAgentIdentity({ id: `id-${i}` }));
      expect(hue).toBeGreaterThanOrEqual(0);
      expect(hue).toBeLessThan(AGENT_IDENTITY_PALETTE.length);
    }
  });

  it('distributions across ids covers multiple hues', () => {
    const counts = new Set<number>();
    for (let i = 0; i < 500; i++) {
      counts.add(buildAgentVisualIdentity({ id: `unique-${i}` }).hue);
    }
    expect(counts.size).toBeGreaterThan(3);
  });

  it('paletteColor maps hue index to hex constant', () => {
    expect(paletteColor(0)).toBe(AGENT_IDENTITY_PALETTE[0]);
    expect(paletteColor(-1)).toBe(AGENT_IDENTITY_PALETTE[AGENT_IDENTITY_PALETTE.length - 1]);
    expect(paletteColor(8)).toBe(AGENT_IDENTITY_PALETTE[0]);
  });

  describe('initials', () => {
    it('two-word names produce two uppercase initials', () => {
      expect(initialsFromName('Nova Prime')).toBe('NP');
    });
    it('single word uses first two letters', () => {
      expect(initialsFromName('coder')).toBe('CO');
    });
    it('separators split words', () => {
      expect(initialsFromName('research-assistant')).toBe('RA');
      expect(initialsFromName('dev/ops')).toBe('DO');
    });
    it('empty falls back to question mark', () => {
      expect(initialsFromName('')).toBe('?');
      expect(initialsFromName(null)).toBe('?');
      expect(initialsFromName('   ')).toBe('?');
    });
  });

  describe('role classification boundaries', () => {
    it('maps known role keywords', () => {
      expect(classifyAgentRole({ name: 'System Architect' })).toBe('plan');
      expect(classifyAgentRole({ name: 'Deep Researcher' })).toBe('research');
      expect(classifyAgentRole({ name: 'Backend Engineer' })).toBe('code');
      expect(classifyAgentRole({ name: 'Code Reviewer' })).toBe('review');
      expect(classifyAgentRole({ name: 'Data Analyst' })).toBe('analysis');
      expect(classifyAgentRole({ name: 'Copy Writer' })).toBe('write');
      expect(classifyAgentRole({ name: 'Site Operator' })).toBe('ops');
    });
    it('is case-insensitive and matches on id/provider too', () => {
      expect(classifyAgentRole({ id: 'planner-1', name: 'X' })).toBe('plan');
      expect(classifyAgentRole({ name: 'X', provider: 'chief-researcher' })).toBe('research');
    });
    it('returns null when no keyword matches', () => {
      expect(classifyAgentRole({ name: 'General Helper', id: 'abc', provider: 'openai' })).toBeNull();
    });
    it('code rule wins when both plan-like and developer words appear', () => {
      expect(classifyAgentRole({ name: 'Planning Developer' })).toBe('code');
    });
    it('first matching rule by priority order wins', () => {
      expect(classifyAgentRole({ name: 'Architect Coder' })).toBe('plan');
    });
  });

  it('buildAgentVisualIdentity returns all three fields', () => {
    const id = buildAgentVisualIdentity({ id: 'x1', name: 'Nova Prime', provider: 'openai' });
    expect(id.initials).toBe('NP');
    expect(id.role).toBeNull();
    expect(typeof id.hue).toBe('number');
  });
});
