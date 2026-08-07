/**
 * Notification system type definitions.
 */

export type NotificationType = "info" | "success" | "warning" | "error" | "system" | "marketing" | "security" | "billing" | "social" | "reminder";

export type NotificationChannel = "in_app" | "email" | "sms" | "push" | "webhook" | "slack" | "discord" | "telegram";

export type NotificationPriority = "low" | "normal" | "high" | "urgent" | "critical";

export type NotificationStatus = "pending" | "queued" | "sending" | "sent" | "delivered" | "read" | "failed" | "canceled";

export interface NotificationTemplate {
  id: string;
  name: string;
  type: NotificationType;
  channel: NotificationChannel;
  subject?: string;
  body_template: string;
  html_template?: string;
  variables: string[];
  locale: string;
  version: number;
  is_active: boolean;
  created_at: string;
}

export interface NotificationTemplateCreateRequest {
  name: string;
  type: NotificationType;
  channel: NotificationChannel;
  subject?: string;
  body_template: string;
  html_template?: string;
  variables?: string[];
  locale?: string;
  description?: string;
}

export interface Notification {
  id: string;
  user_id: string;
  type: NotificationType;
  channel: NotificationChannel;
  priority: NotificationPriority;
  status: NotificationStatus;
  subject?: string;
  body: string;
  data?: Record<string, unknown>;
  sent_at?: string;
  delivered_at?: string;
  read_at?: string;
  created_at: string;
}

export interface NotificationCreateRequest {
  user_id: string;
  type: NotificationType;
  channel: NotificationChannel;
  body: string;
  subject?: string;
  priority?: NotificationPriority;
  data?: Record<string, unknown>;
  template_id?: string;
  scheduled_at?: string;
}

export interface NotificationBulkCreateRequest {
  user_ids: string[];
  type: NotificationType;
  channel: NotificationChannel;
  body: string;
  subject?: string;
}

export interface NotificationPreference {
  type: NotificationType;
  channel: NotificationChannel;
  enabled: boolean;
  quiet_hours_start?: string;
  quiet_hours_end?: string;
  quiet_hours_timezone: string;
}

export interface NotificationPreferenceUpdateRequest {
  enabled?: boolean;
  quiet_hours_start?: string;
  quiet_hours_end?: string;
}

export interface WebhookEndpoint {
  id: string;
  name: string;
  url: string;
  events: string[];
  is_active: boolean;
  failure_count: number;
  last_success_at?: string;
  created_at: string;
}

export interface WebhookCreateRequest {
  name: string;
  url: string;
  events: string[];
}

export interface DeviceToken {
  id: string;
  token: string;
  platform: string;
  device_name?: string;
  is_active: boolean;
  last_used_at?: string;
  created_at: string;
}

export interface DeviceTokenCreateRequest {
  token: string;
  platform: string;
  device_name?: string;
  device_model?: string;
  os_version?: string;
  app_version?: string;
}
