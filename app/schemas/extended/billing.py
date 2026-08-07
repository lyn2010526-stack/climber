"""Comprehensive billing schemas.

This module defines all Pydantic schemas for the billing system including
request/response schemas for plans, subscriptions, invoices, payments,
and usage tracking.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, field_validator

# ── Enums ──

class BillingIntervalSchema(StrEnum):
    """Billing interval options."""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"
    ONE_TIME = "one_time"


class PlanStatusSchema(StrEnum):
    """Plan status."""
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"
    DEPRECATED = "deprecated"


class SubscriptionStatusSchema(StrEnum):
    """Subscription status."""
    TRIAL = "trial"
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELED = "canceled"
    EXPIRED = "expired"
    PAUSED = "paused"


class InvoiceStatusSchema(StrEnum):
    """Invoice status."""
    DRAFT = "draft"
    OPEN = "open"
    PAID = "paid"
    VOID = "void"
    UNCOLLECTIBLE = "uncollectible"
    REFUNDED = "refunded"


class PaymentStatusSchema(StrEnum):
    """Payment status."""
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELED = "canceled"
    REFUNDED = "refunded"
    DISPUTED = "disputed"


class PaymentMethodSchema(StrEnum):
    """Payment method types."""
    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"
    BANK_TRANSFER = "bank_transfer"
    PAYPAL = "paypal"
    STRIPE = "stripe"
    ALIPAY = "alipay"
    WECHAT = "wechat"
    CRYPTO = "crypto"


class UsageTypeSchema(StrEnum):
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
    description: str | None = Field(None, max_length=512, description="Feature description")
    included: bool = Field(True, description="Whether feature is included")
    limit: int | None = Field(None, ge=0, description="Feature limit if applicable")


class PlanLimitSchema(BaseModel):
    """Plan resource limit definition."""
    resource: str = Field(..., min_length=1, max_length=64, description="Resource name")
    limit: int = Field(..., ge=0, description="Maximum allowed amount")
    unit: str = Field(..., max_length=32, description="Unit of measurement")
    overage_rate: Decimal | None = Field(None, ge=0, description="Cost per unit over limit")


class PlanUsageRateSchema(BaseModel):
    """Usage-based pricing rate."""
    usage_type: UsageTypeSchema = Field(..., description="Type of usage")
    unit_price: Decimal = Field(..., ge=0, description="Price per unit")
    unit_size: int = Field(1, ge=1, description="Number of units per billing unit")
    minimum_charge: Decimal | None = Field(None, ge=0, description="Minimum charge per period")


class PlanCreateSchema(BaseModel):
    """Schema for creating a new plan."""
    name: str = Field(..., min_length=1, max_length=128, description="Plan name")
    description: str | None = Field(None, max_length=1024, description="Plan description")
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
    metadata: dict[str, Any] | None = Field(None, description="Additional metadata")

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v: str) -> str:
        return v.upper()


class PlanUpdateSchema(BaseModel):
    """Schema for updating an existing plan."""
    name: str | None = Field(None, min_length=1, max_length=128)
    description: str | None = Field(None, max_length=1024)
    price: Decimal | None = Field(None, ge=0)
    interval: BillingIntervalSchema | None = None
    trial_days: int | None = Field(None, ge=0, le=365)
    features: list[PlanFeatureSchema] | None = None
    limits: list[PlanLimitSchema] | None = None
    usage_rates: list[PlanUsageRateSchema] | None = None
    is_public: bool | None = None
    status: PlanStatusSchema | None = None
    sort_order: int | None = Field(None, ge=0)


class PlanResponseSchema(BaseModel):
    """Schema for plan response."""
    id: str = Field(..., description="Plan identifier")
    name: str = Field(..., description="Plan name")
    description: str | None = Field(None, description="Plan description")
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
    payment_method_id: str | None = Field(None, description="Payment method ID")
    coupon_code: str | None = Field(None, max_length=64, description="Coupon code to apply")
    metadata: dict[str, Any] | None = Field(None, description="Additional metadata")


class SubscriptionUpdateSchema(BaseModel):
    """Schema for updating a subscription."""
    quantity: int | None = Field(None, ge=1, le=1000)
    payment_method_id: str | None = None
    cancel_at_period_end: bool | None = None


class SubscriptionResponseSchema(BaseModel):
    """Schema for subscription response."""
    id: str = Field(..., description="Subscription identifier")
    user_id: str = Field(..., description="Subscribed user ID")
    plan_id: str = Field(..., description="Plan ID")
    plan_name: str = Field(..., description="Plan name")
    status: SubscriptionStatusSchema = Field(..., description="Subscription status")
    current_period_start: datetime = Field(..., description="Current period start")
    current_period_end: datetime = Field(..., description="Current period end")
    trial_start: datetime | None = Field(None, description="Trial start")
    trial_end: datetime | None = Field(None, description="Trial end")
    canceled_at: datetime | None = Field(None, description="Cancellation timestamp")
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
    period_start: datetime | None = Field(None, description="Service period start")
    period_end: datetime | None = Field(None, description="Service period end")


class InvoiceCreateSchema(BaseModel):
    """Schema for creating an invoice."""
    subscription_id: str = Field(..., description="Subscription ID")
    line_items: list[InvoiceLineItemSchema] = Field(default_factory=list)
    due_date: datetime | None = Field(None, description="Payment due date")
    notes: str | None = Field(None, max_length=2048, description="Additional notes")


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
    due_date: datetime | None = Field(None, description="Due date")
    paid_at: datetime | None = Field(None, description="Payment timestamp")
    line_items: list[InvoiceLineItemSchema] = Field(default_factory=list)
    notes: str | None = Field(None, description="Notes")
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
    amount: Decimal | None = Field(None, ge=0, description="Payment amount (defaults to remaining)")


class PaymentResponseSchema(BaseModel):
    """Schema for payment response."""
    id: str = Field(..., description="Payment identifier")
    invoice_id: str = Field(..., description="Invoice ID")
    user_id: str = Field(..., description="Paying user ID")
    amount: Decimal = Field(..., description="Payment amount")
    currency: str = Field(..., description="Currency code")
    status: PaymentStatusSchema = Field(..., description="Payment status")
    method: PaymentMethodSchema = Field(..., description="Payment method")
    external_id: str | None = Field(None, description="External payment ID")
    failure_reason: str | None = Field(None, description="Failure reason")
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
    metadata: dict[str, Any] | None = Field(None, description="Additional metadata")


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
    description: str | None = Field(None, max_length=512)
    discount_type: str = Field(..., pattern="^(percentage|fixed)$")
    discount_value: Decimal = Field(..., gt=0, description="Discount value")
    currency: str = Field("USD", min_length=3, max_length=3)
    max_redemptions: int | None = Field(None, ge=1)
    expires_at: datetime | None = None

    @field_validator("code")
    @classmethod
    def validate_code(cls, v: str) -> str:
        return v.upper()


class CouponResponseSchema(BaseModel):
    """Schema for coupon response."""
    id: str
    code: str
    name: str
    description: str | None
    discount_type: str
    discount_value: Decimal
    currency: str
    max_redemptions: int | None
    times_redeemed: int
    expires_at: datetime | None
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
    billing_details: dict[str, Any] | None = None


class PaymentMethodResponseSchema(BaseModel):
    """Schema for payment method response."""
    id: str
    type: PaymentMethodSchema
    provider: str
    last4: str | None
    expiry_month: int | None
    expiry_year: int | None
    is_default: bool
    is_active: bool
    billing_details: dict[str, Any] | None
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
