import type { JsonObject, OkResult } from './common';
import type { TaskDetail } from './api';

export interface TaskGuardrail {
  name: string;
  description: string;
}

export interface CreateTaskInput {
  group_id?: string;
  groupId?: string;
  description: string;
  worker_id?: string;
  reviewer_ids?: string[];
  max_rounds?: number;
  context?: string[];
  guardrails?: TaskGuardrail[];
  human_review_required?: boolean;
  output_schema?: JsonObject;
  provider?: string;
  model_id?: string;
  api_key?: string;
}

export interface CreatedTask extends Omit<TaskDetail, 'current_round'> {
  task_id: string;
}

export interface TaskActionResult extends OkResult {
  task_id: string;
  status: string;
}

export type TaskRunInputs = JsonObject;
