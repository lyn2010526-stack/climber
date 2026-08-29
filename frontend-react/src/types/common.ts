export type JsonObject = Record<string, unknown>;

export interface OkResult {
  ok: boolean;
}

export function getErrorMessage(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}
