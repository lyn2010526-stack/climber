#!/usr/bin/env python3
"""Generator for large schema files, type definitions, and additional modules."""

from pathlib import Path

BASE = Path("/workspace/agent-engine")
SCHEMAS_DIR = BASE / "app" / "schemas" / "extended"
TYPES_DIR = BASE / "frontend-react" / "src" / "types" / "extended"

SCHEMAS_DIR.mkdir(parents=True, exist_ok=True)
TYPES_DIR.mkdir(parents=True, exist_ok=True)


def write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


# ── Generate comprehensive billing schemas ──

def generate_billing_schemas() -> str:
    return '''"""Comprehensive billing schemas.

This module defines all Pydantic schemas for the billing system including
request/response schemas for plans, subscriptions, invoices, payments,
and usage tracking.
"""

from __future__ import annotations

from datetime import datetime, date
from decimal import Decimal
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


# ── Enums ──

class BillingIntervalSchema(str, Enum):
    """Billing interval options."""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"
    ONE_TIME = "one_time"


class PlanStatusSchema(str, Enum):
    """Plan status."""
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"
    DEPRECATED = "deprecated"


class SubscriptionStatusSchema(str, Enum):
    """Subscription status."""
    TRIAL = "trial"
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELED = "canceled"
    EXPIRED = "expired"
    PAUSED = "paused"


class InvoiceStatusSchema(str, Enum):
    """Invoice status."""
    DRAFT = "draft"
    OPEN = "open"
    PAID = "paid"
    VOID = "void"
    UNCOLLECTIBLE = "uncollectible"
    REFUNDED = "refunded"


class PaymentStatusSchema(str, Enum):
    """Payment status."""
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELED = "canceled"
    REFUNDED = "refunded"
    DISPUTED = "disputed"


class PaymentMethodSchema(str, Enum):
    """Payment method types."""
    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"
    BANK_TRANSFER = "bank_transfer"
    PAYPAL = "paypal"
    STRIPE = "stripe"
    ALIPAY = "alipay"
    WECHAT = "wechat"
    CRYPTO = "crypto"


class UsageTypeSchema(str, Enum):
    """Types of usage."""
    API_CALLS = "api_calls"
    STORAGE = "storage"
    COMPUTE = "compute"
    BANDWIDTH = "bandwidth"
    TOKENS = "tokens"
    AGENTS = "agents"
    WORKFLOWS = "workflows"
    USERS = "users"


# ── Plan Schemas ──

class PlanFeatureSchema(BaseModel):
    """Plan feature definition."""
    name: str = Field(..., min_length=1, max_length=128, description="Feature name")
    description: Optional[str] = Field(None, max_length=512, description="Feature description")
    included: bool = Field(True, description="Whether feature is included")
    limit: Optional[int] = Field(None, ge=0, description="Feature limit if applicable")


class PlanLimitSchema(BaseModel):
    """Plan resource limit definition."""
    resource: str = Field(..., min_length=1, max_length=64, description="Resource name")
    limit: int = Field(..., ge=0, description="Maximum allowed amount")
    unit: str = Field(..., max_length=32, description="Unit of measurement")
    overage_rate: Optional[Decimal] = Field(None, ge=0, description="Cost per unit over limit")


class PlanUsageRateSchema(BaseModel):
    """Usage-based pricing rate."""
    usage_type: UsageTypeSchema = Field(..., description="Type of usage")
    unit_price: Decimal = Field(..., ge=0, description="Price per unit")
    unit_size: int = Field(1, ge=1, description="Number of units per billing unit")
    minimum_charge: Optional[Decimal] = Field(None, ge=0, description="Minimum charge per period")


class PlanCreateSchema(BaseModel):
    """Schema for creating a new plan."""
    name: str = Field(..., min_length=1, max_length=128, description="Plan name")
    description: Optional[str] = Field(None, max_length=1024, description="Plan description")
    price: Decimal = Field(..., ge=0, description="Base price amount")
    currency: str = Field("USD", min_length=3, max_length=3, description="Currency code (ISO 4217)")
    interval: BillingIntervalSchema = Field(BillingIntervalSchema.MONTHLY, description="Billing interval")
    interval_count: int = Field(1, ge=1, le=12, description="Number of intervals per billing cycle")
    trial_days: int = Field(0, ge=0, le=365, description="Number of trial days")
    features: list[PlanFeatureSchema] = Field(default_factory=list, description="Included features")
    limits: list[PlanLimitSchema] = Field(default_factory=list, description="Resource limits")
    usage_rates: list[PlanUsageRateSchema] = Field(default_factory=list, description="Usage-based rates")
    is_public: bool = Field(True, description="Whether plan is publicly visible")
    sort_order: int = Field(0, ge=0, description="Sort order for display")
    metadata: Optional[dict[str, Any]] = Field(None, description="Additional metadata")

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v: str) -> str:
        return v.upper()


class PlanUpdateSchema(BaseModel):
    """Schema for updating an existing plan."""
    name: Optional[str] = Field(None, min_length=1, max_length=128)
    description: Optional[str] = Field(None, max_length=1024)
    price: Optional[Decimal] = Field(None, ge=0)
    interval: Optional[BillingIntervalSchema] = None
    trial_days: Optional[int] = Field(None, ge=0, le=365)
    features: Optional[list[PlanFeatureSchema]] = None
    limits: Optional[list[PlanLimitSchema]] = None
    usage_rates: Optional[list[PlanUsageRateSchema]] = None
    is_public: Optional[bool] = None
    status: Optional[PlanStatusSchema] = None
    sort_order: Optional[int] = Field(None, ge=0)


class PlanResponseSchema(BaseModel):
    """Schema for plan response."""
    id: str = Field(..., description="Plan identifier")
    name: str = Field(..., description="Plan name")
    description: Optional[str] = Field(None, description="Plan description")
    price: Decimal = Field(..., description="Base price")
    currency: str = Field(..., description="Currency code")
    interval: BillingIntervalSchema = Field(..., description="Billing interval")
    interval_count: int = Field(..., description="Interval count")
    trial_days: int = Field(..., description="Trial days")
    features: list[PlanFeatureSchema] = Field(default_factory=list)
    limits: list[PlanLimitSchema] = Field(default_factory=list)
    usage_rates: list[PlanUsageRateSchema] = Field(default_factory=list)
    status: PlanStatusSchema = Field(..., description="Plan status")
    is_public: bool = Field(..., description="Public visibility")
    sort_order: int = Field(..., description="Sort order")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        from_attributes = True


class PlanListSchema(BaseModel):
    """Schema for plan list response."""
    items: list[PlanResponseSchema] = Field(default_factory=list, description="List of plans")
    total: int = Field(0, ge=0, description="Total number of plans")
    page: int = Field(1, ge=1, description="Current page")
    page_size: int = Field(20, ge=1, le=100, description="Items per page")


# ── Subscription Schemas ──

class SubscriptionCreateSchema(BaseModel):
    """Schema for creating a subscription."""
    plan_id: str = Field(..., description="Plan identifier")
    quantity: int = Field(1, ge=1, le=1000, description="Number of units")
    payment_method_id: Optional[str] = Field(None, description="Payment method ID")
    coupon_code: Optional[str] = Field(None, max_length=64, description="Coupon code to apply")
    metadata: Optional[dict[str, Any]] = Field(None, description="Additional metadata")


class SubscriptionUpdateSchema(BaseModel):
    """Schema for updating a subscription."""
    quantity: Optional[int] = Field(None, ge=1, le=1000)
    payment_method_id: Optional[str] = None
    cancel_at_period_end: Optional[bool] = None


class SubscriptionResponseSchema(BaseModel):
    """Schema for subscription response."""
    id: str = Field(..., description="Subscription identifier")
    user_id: str = Field(..., description="Subscribed user ID")
    plan_id: str = Field(..., description="Plan ID")
    plan_name: str = Field(..., description="Plan name")
    status: SubscriptionStatusSchema = Field(..., description="Subscription status")
    current_period_start: datetime = Field(..., description="Current period start")
    current_period_end: datetime = Field(..., description="Current period end")
    trial_start: Optional[datetime] = Field(None, description="Trial start")
    trial_end: Optional[datetime] = Field(None, description="Trial end")
    canceled_at: Optional[datetime] = Field(None, description="Cancellation timestamp")
    cancel_at_period_end: bool = Field(..., description="Cancel at period end flag")
    quantity: int = Field(..., description="Quantity")
    unit_price: Decimal = Field(..., description="Price per unit")
    tax_rate: Decimal = Field(..., description="Tax rate percentage")
    discount_amount: Decimal = Field(..., description="Discount amount")
    currency: str = Field(..., description="Currency code")
    amount_due: Decimal = Field(..., description="Amount due for current period")
    days_until_renewal: int = Field(..., description="Days until renewal")
    created_at: datetime = Field(..., description="Creation timestamp")

    class Config:
        from_attributes = True


class SubscriptionListSchema(BaseModel):
    """Schema for subscription list response."""
    items: list[SubscriptionResponseSchema] = Field(default_factory=list)
    total: int = Field(0, ge=0)


# ── Invoice Schemas ──

class InvoiceLineItemSchema(BaseModel):
    """Invoice line item."""
    description: str = Field(..., max_length=512, description="Item description")
    quantity: Decimal = Field(1, gt=0, description="Quantity")
    unit_price: Decimal = Field(..., ge=0, description="Price per unit")
    amount: Decimal = Field(..., ge=0, description="Total amount")
    period_start: Optional[datetime] = Field(None, description="Service period start")
    period_end: Optional[datetime] = Field(None, description="Service period end")


class InvoiceCreateSchema(BaseModel):
    """Schema for creating an invoice."""
    subscription_id: str = Field(..., description="Subscription ID")
    line_items: list[InvoiceLineItemSchema] = Field(default_factory=list)
    due_date: Optional[datetime] = Field(None, description="Payment due date")
    notes: Optional[str] = Field(None, max_length=2048, description="Additional notes")


class InvoiceResponseSchema(BaseModel):
    """Schema for invoice response."""
    id: str = Field(..., description="Invoice identifier")
    invoice_number: str = Field(..., description="Invoice number")
    subscription_id: str = Field(..., description="Subscription ID")
    user_id: str = Field(..., description="Billed user ID")
    status: InvoiceStatusSchema = Field(..., description="Invoice status")
    subtotal: Decimal = Field(..., description="Subtotal")
    tax_amount: Decimal = Field(..., description="Tax amount")
    discount_amount: Decimal = Field(..., description="Discount amount")
    total: Decimal = Field(..., description="Total amount")
    amount_paid: Decimal = Field(..., description="Amount paid")
    amount_remaining: Decimal = Field(..., description="Amount remaining")
    currency: str = Field(..., description="Currency code")
    due_date: Optional[datetime] = Field(None, description="Due date")
    paid_at: Optional[datetime] = Field(None, description="Payment timestamp")
    line_items: list[InvoiceLineItemSchema] = Field(default_factory=list)
    notes: Optional[str] = Field(None, description="Notes")
    created_at: datetime = Field(..., description="Creation timestamp")

    class Config:
        from_attributes = True


class InvoiceListSchema(BaseModel):
    """Schema for invoice list response."""
    items: list[InvoiceResponseSchema] = Field(default_factory=list)
    total: int = Field(0, ge=0)
    total_outstanding: Decimal = Field(Decimal("0"), ge=0)


# ── Payment Schemas ──

class PaymentCreateSchema(BaseModel):
    """Schema for creating a payment."""
    invoice_id: str = Field(..., description="Invoice ID")
    method: PaymentMethodSchema = Field(..., description="Payment method")
    amount: Optional[Decimal] = Field(None, ge=0, description="Payment amount (defaults to remaining)")


class PaymentResponseSchema(BaseModel):
    """Schema for payment response."""
    id: str = Field(..., description="Payment identifier")
    invoice_id: str = Field(..., description="Invoice ID")
    user_id: str = Field(..., description="Paying user ID")
    amount: Decimal = Field(..., description="Payment amount")
    currency: str = Field(..., description="Currency code")
    status: PaymentStatusSchema = Field(..., description="Payment status")
    method: PaymentMethodSchema = Field(..., description="Payment method")
    external_id: Optional[str] = Field(None, description="External payment ID")
    failure_reason: Optional[str] = Field(None, description="Failure reason")
    refunded_amount: Decimal = Field(..., description="Refunded amount")
    created_at: datetime = Field(..., description="Creation timestamp")

    class Config:
        from_attributes = True


class PaymentListSchema(BaseModel):
    """Schema for payment list response."""
    items: list[PaymentResponseSchema] = Field(default_factory=list)
    total: int = Field(0, ge=0)
    total_amount: Decimal = Field(Decimal("0"), ge=0)


# ── Usage Schemas ──

class UsageRecordSchema(BaseModel):
    """Schema for recording usage."""
    subscription_id: str = Field(..., description="Subscription ID")
    usage_type: UsageTypeSchema = Field(..., description="Type of usage")
    quantity: Decimal = Field(..., gt=0, description="Amount consumed")
    metadata: Optional[dict[str, Any]] = Field(None, description="Additional metadata")


class UsageSummarySchema(BaseModel):
    """Schema for usage summary."""
    usage_type: UsageTypeSchema = Field(..., description="Type of usage")
    quantity: Decimal = Field(..., description="Total quantity")
    cost: Decimal = Field(..., description="Total cost")
    unit: str = Field(..., description="Unit of measurement")


class UsageReportSchema(BaseModel):
    """Schema for usage report."""
    subscription_id: str = Field(..., description="Subscription ID")
    period_start: datetime = Field(..., description="Report period start")
    period_end: datetime = Field(..., description="Report period end")
    summaries: list[UsageSummarySchema] = Field(default_factory=list)
    total_cost: Decimal = Field(..., description="Total cost for period")


# ── Coupon Schemas ──

class CouponCreateSchema(BaseModel):
    """Schema for creating a coupon."""
    code: str = Field(..., min_length=3, max_length=64, description="Coupon code")
    name: str = Field(..., min_length=1, max_length=128, description="Coupon name")
    description: Optional[str] = Field(None, max_length=512)
    discount_type: str = Field(..., pattern="^(percentage|fixed)$")
    discount_value: Decimal = Field(..., gt=0, description="Discount value")
    currency: str = Field("USD", min_length=3, max_length=3)
    max_redemptions: Optional[int] = Field(None, ge=1)
    expires_at: Optional[datetime] = None

    @field_validator("code")
    @classmethod
    def validate_code(cls, v: str) -> str:
        return v.upper()


class CouponResponseSchema(BaseModel):
    """Schema for coupon response."""
    id: str
    code: str
    name: str
    description: Optional[str]
    discount_type: str
    discount_value: Decimal
    currency: str
    max_redemptions: Optional[int]
    times_redeemed: int
    expires_at: Optional[datetime]
    is_active: bool
    is_valid: bool
    created_at: datetime

    class Config:
        from_attributes = True


class CouponApplySchema(BaseModel):
    """Schema for applying a coupon."""
    code: str = Field(..., description="Coupon code to apply")
    amount: Decimal = Field(..., gt=0, description="Original amount")


# ── Payment Method Schemas ──

class PaymentMethodCreateSchema(BaseModel):
    """Schema for adding a payment method."""
    type: PaymentMethodSchema = Field(..., description="Payment method type")
    token: str = Field(..., min_length=1, max_length=512, description="Payment provider token")
    set_default: bool = Field(False, description="Set as default payment method")
    billing_details: Optional[dict[str, Any]] = None


class PaymentMethodResponseSchema(BaseModel):
    """Schema for payment method response."""
    id: str
    type: PaymentMethodSchema
    provider: str
    last4: Optional[str]
    expiry_month: Optional[int]
    expiry_year: Optional[int]
    is_default: bool
    is_active: bool
    billing_details: Optional[dict[str, Any]]
    created_at: datetime

    class Config:
        from_attributes = True


# ── Billing Dashboard Schemas ──

class BillingDashboardSchema(BaseModel):
    """Schema for billing dashboard data."""
    active_subscriptions: int = Field(0, ge=0)
    monthly_revenue: Decimal = Field(Decimal("0"), ge=0)
    outstanding_invoices: int = Field(0, ge=0)
    outstanding_amount: Decimal = Field(Decimal("0"), ge=0)
    recent_payments: list[PaymentResponseSchema] = Field(default_factory=list)
    revenue_chart: list[dict[str, Any]] = Field(default_factory=list)
    subscription_growth: list[dict[str, Any]] = Field(default_factory=list)


class RevenueChartItemSchema(BaseModel):
    """Revenue chart data point."""
    date: date = Field(..., description="Date")
    revenue: Decimal = Field(..., description="Revenue amount")
    subscriptions: int = Field(..., description="New subscriptions")
    churn: int = Field(..., description="Canceled subscriptions")
'''


write_file(SCHEMAS_DIR / "billing.py", generate_billing_schemas())
print("Generated billing schemas")


def generate_notification_schemas() -> str:
    return '''"""Comprehensive notification schemas.

This module defines all Pydantic schemas for the notification system.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator


class NotificationTypeSchema(str, Enum):
    """Notification types."""
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    SYSTEM = "system"
    MARKETING = "marketing"
    SECURITY = "security"
    BILLING = "billing"
    SOCIAL = "social"
    REMINDER = "reminder"


class NotificationChannelSchema(str, Enum):
    """Notification channels."""
    IN_APP = "in_app"
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"
    WEBHOOK = "webhook"
    SLACK = "slack"
    DISCORD = "discord"
    TELEGRAM = "telegram"


class NotificationPrioritySchema(str, Enum):
    """Notification priority levels."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"
    CRITICAL = "critical"


class NotificationStatusSchema(str, Enum):
    """Notification delivery status."""
    PENDING = "pending"
    QUEUED = "queued"
    SENDING = "sending"
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    FAILED = "failed"
    CANCELED = "canceled"


# ── Template Schemas ──

class NotificationTemplateCreateSchema(BaseModel):
    """Schema for creating notification template."""
    name: str = Field(..., min_length=1, max_length=128)
    type: NotificationTypeSchema
    channel: NotificationChannelSchema
    subject: Optional[str] = Field(None, max_length=255)
    body_template: str = Field(..., min_length=1)
    html_template: Optional[str] = None
    variables: list[str] = Field(default_factory=list)
    locale: str = Field("en", min_length=2, max_length=16)
    description: Optional[str] = None


class NotificationTemplateResponseSchema(BaseModel):
    """Schema for notification template response."""
    id: str
    name: str
    type: NotificationTypeSchema
    channel: NotificationChannelSchema
    subject: Optional[str]
    body_template: str
    html_template: Optional[str]
    variables: list[str]
    locale: str
    version: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ── Notification Schemas ──

class NotificationCreateSchema(BaseModel):
    """Schema for creating notification."""
    user_id: str
    type: NotificationTypeSchema
    channel: NotificationChannelSchema
    body: str = Field(..., min_length=1)
    subject: Optional[str] = Field(None, max_length=255)
    priority: NotificationPrioritySchema = NotificationPrioritySchema.NORMAL
    data: Optional[dict[str, Any]] = None
    template_id: Optional[str] = None
    scheduled_at: Optional[datetime] = None


class NotificationBulkCreateSchema(BaseModel):
    """Schema for bulk notification creation."""
    user_ids: list[str] = Field(..., min_length=1)
    type: NotificationTypeSchema
    channel: NotificationChannelSchema
    body: str
    subject: Optional[str] = None


class NotificationResponseSchema(BaseModel):
    """Schema for notification response."""
    id: str
    user_id: str
    type: NotificationTypeSchema
    channel: NotificationChannelSchema
    priority: NotificationPrioritySchema
    status: NotificationStatusSchema
    subject: Optional[str]
    body: str
    data: Optional[dict[str, Any]]
    sent_at: Optional[datetime]
    delivered_at: Optional[datetime]
    read_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


# ── Preference Schemas ──

class NotificationPreferenceSchema(BaseModel):
    """Schema for notification preference."""
    type: NotificationTypeSchema
    channel: NotificationChannelSchema
    enabled: bool = True
    quiet_hours_start: Optional[str] = Field(None, pattern=r"^\\d{2}:\\d{2}$")
    quiet_hours_end: Optional[str] = Field(None, pattern=r"^\\d{2}:\\d{2}$")
    quiet_hours_timezone: str = "UTC"


class NotificationPreferenceUpdateSchema(BaseModel):
    """Schema for updating notification preference."""
    enabled: Optional[bool] = None
    quiet_hours_start: Optional[str] = None
    quiet_hours_end: Optional[str] = None


# ── Webhook Schemas ──

class WebhookCreateSchema(BaseModel):
    """Schema for creating webhook endpoint."""
    name: str = Field(..., min_length=1, max_length=128)
    url: str = Field(..., max_length=512)
    events: list[str] = Field(..., min_length=1)


class WebhookResponseSchema(BaseModel):
    """Schema for webhook endpoint response."""
    id: str
    name: str
    url: str
    events: list[str]
    is_active: bool
    failure_count: int
    last_success_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


# ── Device Token Schemas ──

class DeviceTokenCreateSchema(BaseModel):
    """Schema for registering device token."""
    token: str = Field(..., min_length=1, max_length=512)
    platform: str = Field(..., pattern="^(ios|android|web)$")
    device_name: Optional[str] = None
    device_model: Optional[str] = None
    os_version: Optional[str] = None
    app_version: Optional[str] = None


class DeviceTokenResponseSchema(BaseModel):
    """Schema for device token response."""
    id: str
    token: str
    platform: str
    device_name: Optional[str]
    is_active: bool
    last_used_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


# ── Enums ──

from enum import Enum
'''


write_file(SCHEMAS_DIR / "notifications.py", generate_notification_schemas())
print("Generated notification schemas")


# ── Generate TypeScript type definitions ──

def generate_billing_types() -> str:
    return '''/**
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
'''


write_file(TYPES_DIR / "billing.ts", generate_billing_types())
print("Generated billing TypeScript types")


def generate_notification_types() -> str:
    return '''/**
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
'''


write_file(TYPES_DIR / "notifications.ts", generate_notification_types())
print("Generated notification TypeScript types")

print("Phase 4 complete: schemas and types generated")
