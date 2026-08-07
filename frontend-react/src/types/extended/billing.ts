/**
 * Billing and subscription type definitions.
 *
 * This module defines TypeScript interfaces and types for the billing system.
 */

// ── Enums ──

export type BillingInterval = "daily" | "weekly" | "monthly" | "quarterly" | "yearly" | "one_time";

export type PlanStatus = "draft" | "active" | "archived" | "deprecated";

export type SubscriptionStatus = "trial" | "active" | "past_due" | "canceled" | "expired" | "paused";

export type InvoiceStatus = "draft" | "open" | "paid" | "void" | "uncollectible" | "refunded";

export type PaymentStatus = "pending" | "processing" | "succeeded" | "failed" | "canceled" | "refunded" | "disputed";

export type PaymentMethod = "credit_card" | "debit_card" | "bank_transfer" | "paypal" | "stripe" | "alipay" | "wechat" | "crypto";

export type UsageType = "api_calls" | "storage" | "compute" | "bandwidth" | "tokens" | "agents" | "workflows" | "users";

// ── Plan Types ──

export interface PlanFeature {
  name: string;
  description?: string;
  included: boolean;
  limit?: number;
}

export interface PlanLimit {
  resource: string;
  limit: number;
  unit: string;
  overage_rate?: number;
}

export interface PlanUsageRate {
  usage_type: UsageType;
  unit_price: number;
  unit_size: number;
  minimum_charge?: number;
}

export interface Plan {
  id: string;
  name: string;
  description?: string;
  price: number;
  currency: string;
  interval: BillingInterval;
  interval_count: number;
  trial_days: number;
  features: PlanFeature[];
  limits: PlanLimit[];
  usage_rates: PlanUsageRate[];
  status: PlanStatus;
  is_public: boolean;
  sort_order: number;
  created_at: string;
  updated_at: string;
}

export interface PlanCreateRequest {
  name: string;
  description?: string;
  price: number;
  currency?: string;
  interval?: BillingInterval;
  interval_count?: number;
  trial_days?: number;
  features?: PlanFeature[];
  limits?: PlanLimit[];
  usage_rates?: PlanUsageRate[];
  is_public?: boolean;
  sort_order?: number;
}

export interface PlanUpdateRequest {
  name?: string;
  description?: string;
  price?: number;
  interval?: BillingInterval;
  trial_days?: number;
  features?: PlanFeature[];
  limits?: PlanLimit[];
  usage_rates?: PlanUsageRate[];
  is_public?: boolean;
  status?: PlanStatus;
  sort_order?: number;
}

// ── Subscription Types ──

export interface Subscription {
  id: string;
  user_id: string;
  plan_id: string;
  plan_name: string;
  status: SubscriptionStatus;
  current_period_start: string;
  current_period_end: string;
  trial_start?: string;
  trial_end?: string;
  canceled_at?: string;
  cancel_at_period_end: boolean;
  quantity: number;
  unit_price: number;
  tax_rate: number;
  discount_amount: number;
  currency: string;
  amount_due: number;
  days_until_renewal: number;
  created_at: string;
}

export interface SubscriptionCreateRequest {
  plan_id: string;
  quantity?: number;
  payment_method_id?: string;
  coupon_code?: string;
}

export interface SubscriptionUpdateRequest {
  quantity?: number;
  payment_method_id?: string;
  cancel_at_period_end?: boolean;
}

// ── Invoice Types ──

export interface InvoiceLineItem {
  description: string;
  quantity: number;
  unit_price: number;
  amount: number;
  period_start?: string;
  period_end?: string;
}

export interface Invoice {
  id: string;
  invoice_number: string;
  subscription_id: string;
  user_id: string;
  status: InvoiceStatus;
  subtotal: number;
  tax_amount: number;
  discount_amount: number;
  total: number;
  amount_paid: number;
  amount_remaining: number;
  currency: string;
  due_date?: string;
  paid_at?: string;
  line_items: InvoiceLineItem[];
  notes?: string;
  created_at: string;
}

export interface InvoiceCreateRequest {
  subscription_id: string;
  line_items?: InvoiceLineItem[];
  due_date?: string;
  notes?: string;
}

// ── Payment Types ──

export interface Payment {
  id: string;
  invoice_id: string;
  user_id: string;
  amount: number;
  currency: string;
  status: PaymentStatus;
  method: PaymentMethod;
  external_id?: string;
  failure_reason?: string;
  refunded_amount: number;
  created_at: string;
}

export interface PaymentCreateRequest {
  invoice_id: string;
  method: PaymentMethod;
  amount?: number;
}

// ── Usage Types ──

export interface UsageSummary {
  usage_type: UsageType;
  quantity: number;
  cost: number;
  unit: string;
}

export interface UsageReport {
  subscription_id: string;
  period_start: string;
  period_end: string;
  summaries: UsageSummary[];
  total_cost: number;
}

export interface UsageRecordRequest {
  subscription_id: string;
  usage_type: UsageType;
  quantity: number;
  metadata?: Record<string, unknown>;
}

// ── Coupon Types ──

export interface Coupon {
  id: string;
  code: string;
  name: string;
  description?: string;
  discount_type: "percentage" | "fixed";
  discount_value: number;
  currency: string;
  max_redemptions?: number;
  times_redeemed: number;
  expires_at?: string;
  is_active: boolean;
  is_valid: boolean;
  created_at: string;
}

export interface CouponCreateRequest {
  code: string;
  name: string;
  description?: string;
  discount_type: "percentage" | "fixed";
  discount_value: number;
  currency?: string;
  max_redemptions?: number;
  expires_at?: string;
}

export interface CouponApplyRequest {
  code: string;
  amount: number;
}

// ── Payment Method Types ──

export interface PaymentMethodInfo {
  id: string;
  type: PaymentMethod;
  provider: string;
  last4?: string;
  expiry_month?: number;
  expiry_year?: number;
  is_default: boolean;
  is_active: boolean;
  billing_details?: Record<string, unknown>;
  created_at: string;
}

export interface PaymentMethodCreateRequest {
  type: PaymentMethod;
  token: string;
  set_default?: boolean;
  billing_details?: Record<string, unknown>;
}

// ── Dashboard Types ──

export interface BillingDashboard {
  active_subscriptions: number;
  monthly_revenue: number;
  outstanding_invoices: number;
  outstanding_amount: number;
  recent_payments: Payment[];
  revenue_chart: RevenueChartItem[];
  subscription_growth: SubscriptionGrowthItem[];
}

export interface RevenueChartItem {
  date: string;
  revenue: number;
  subscriptions: number;
  churn: number;
}

export interface SubscriptionGrowthItem {
  date: string;
  total: number;
  new: number;
  canceled: number;
}
