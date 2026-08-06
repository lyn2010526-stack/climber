export type MemoryLayer = 'working' | 'episodic' | 'semantic' | 'procedural';

export interface MemoryItem {
  id: string;
  content: string;
  layer: MemoryLayer;
  score: number;
  createdAt: string;
}
