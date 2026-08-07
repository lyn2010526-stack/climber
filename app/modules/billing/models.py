"""Billing and subscription data models.

This module defines all data models for the billing system including
plans, subscriptions, invoices, payments, usage records, and coupons.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.storage.database import Base


class BillingInterval(StrEnum):
    """Billing interval options."""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"
    ONE_TIME = "one_time"


class PlanStatus(StrEnum):
    """Plan status."""
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"
    DEPRECATED = "deprecated"


class SubscriptionStatus(StrEnum):
    """Subscription status."""
    TRIAL = "trial"
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELED = "canceled"
    EXPIRED = "expired"
    PAUSED = "paused"


class InvoiceStatus(StrEnum):
    """Invoice status."""
    DRAFT = "draft"
    OPEN = "open"
    PAID = "paid"
    VOID = "void"
    UNCOLLECTIBLE = "uncollectible"
    REFUNDED = "refunded"


class PaymentStatus(StrEnum):
    """Payment status."""
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELED = "canceled"
    REFUNDED = "refunded"
    DISPUTED = "disputed"


class PaymentMethod(StrEnum):
    """Payment method types."""
    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"
    BANK_TRANSFER = "bank_transfer"
    PAYPAL = "paypal"
    STRIPE = "stripe"
    ALIPAY = "alipay"
    WECHAT = "wechat"
    CRYPTO = "crypto"


class UsageType(StrEnum):
    """Types of usage that can be tracked."""
    API_CALLS = "api_calls"
    STORAGE = "storage"
    COMPUTE = "compute"
    BANDWIDTH = "bandwidth"
    TOKENS = "tokens"
    AGENTS = "agents"
    WORKFLOWS = "workflows"
    USERS = "users"


class Plan(Base):
    """Subscription plan definition.

    Defines a pricing plan with features, limits, and billing options.

    Attributes:
        id: Unique plan identifier.
        name: Plan name.
        description: Plan description.
        price: Base price amount.
        currency: Currency code (ISO 4217).
        interval: Billing interval.
        interval_count: Number of intervals per billing cycle.
        trial_days: Number of trial days.
        features: List of included features.
        limits: Resource limits as JSON.
        usage_rates: Usage-based pricing rates.
        status: Plan status.
        is_public: Whether plan is publicly visible.
        metadata_json: Additional metadata.
        created_at: Creation timestamp.
        updated_at: Last update timestamp.
    """

    __tablename__ = "billing_plans"
    __table_args__ = (
        Index("ix_billing_plans_status", "status"),
        Index("ix_billing_plans_is_public", "is_public"),
        UniqueConstraint("name", name="uq_billing_plans_name"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    interval: Mapped[BillingInterval] = mapped_column(SAEnum(BillingInterval), default=BillingInterval.MONTHLY, nullable=False)
    interval_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    trial_days: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    features: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    limits: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    usage_rates: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    status: Mapped[PlanStatus] = mapped_column(SAEnum(PlanStatus), default=PlanStatus.DRAFT, nullable=False)
    is_public: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    metadata_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    subscriptions: Mapped[list[Subscription]] = relationship("Subscription", back_populates="plan")

    @property
    def is_free(self) -> bool:
        """Check if plan is free."""
        return self.price == 0

    @property
    def is_recurring(self) -> bool:
        """Check if plan has recurring billing."""
        return self.interval != BillingInterval.ONE_TIME

    @property
    def monthly_price(self) -> Decimal:
        """Calculate equivalent monthly price."""
        if self.interval == BillingInterval.MONTHLY:
            return self.price
        elif self.interval == BillingInterval.YEARLY:
            return self.price / 12
        elif self.interval == BillingInterval.QUARTERLY:
            return self.price / 3
        elif self.interval == BillingInterval.WEEKLY:
            return self.price * 4
        elif self.interval == BillingInterval.DAILY:
            return self.price * 30
        return self.price


class Subscription(Base):
    """User subscription to a plan.

    Tracks the state of a user's subscription including billing dates,
    status, and associated plan.

    Attributes:
        id: Unique subscription identifier.
        user_id: Subscribed user ID.
        plan_id: Associated plan ID.
        status: Current subscription status.
        current_period_start: Start of current billing period.
        current_period_end: End of current billing period.
        trial_start: Trial period start.
        trial_end: Trial period end.
        canceled_at: When subscription was canceled.
        cancel_at_period_end: Whether to cancel at period end.
        quantity: Number of subscription units.
        unit_price: Price per unit.
        tax_rate: Tax rate percentage.
        discount_id: Applied discount ID.
        metadata_json: Additional metadata.
        created_at: Creation timestamp.
        updated_at: Last update timestamp.
    """

    __tablename__ = "billing_subscriptions"
    __tablename__ = "billing_subscriptions"
    __table_args__ = (
        Index("ix_billing_subscriptions_user_id", "user_id"),
        Index("ix_billing_subscriptions_plan_id", "plan_id"),
        Index("ix_billing_subscriptions_status", "status"),
        Index("ix_billing_subscriptions_period_end", "current_period_end"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    plan_id: Mapped[str] = mapped_column(String(36), ForeignKey("billing_plans.id", ondelete="RESTRICT"), nullable=False)
    status: Mapped[SubscriptionStatus] = mapped_column(SAEnum(SubscriptionStatus), default=SubscriptionStatus.TRIAL, nullable=False)
    current_period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    current_period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    trial_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    trial_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    canceled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancel_at_period_end: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    tax_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("0"), nullable=False)
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0"), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    payment_method_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    plan: Mapped[Plan] = relationship("Plan", back_populates="subscriptions")
    invoices: Mapped[list[Invoice]] = relationship("Invoice", back_populates="subscription", cascade="all, delete-orphan")

    @property
    def is_active(self) -> bool:
        """Check if subscription is currently active."""
        return self.status in (SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIAL)

    @property
    def is_trial(self) -> bool:
        """Check if subscription is in trial period."""
        if self.trial_end is None:
            return False
        return datetime.utcnow() < self.trial_end

    @property
    def amount_due(self) -> Decimal:
        """Calculate amount due for current period."""
        subtotal = self.unit_price * self.quantity
        tax = subtotal * (self.tax_rate / 100)
        return subtotal + tax - self.discount_amount

    @property
    def days_until_renewal(self) -> int:
        """Calculate days until next renewal."""
        delta = self.current_period_end - datetime.utcnow()
        return max(0, delta.days)


class Invoice(Base):
    """Billing invoice for a subscription period.

    Represents a bill sent to the user for services rendered during
    a specific billing period.

    Attributes:
        id: Unique invoice identifier.
        subscription_id: Associated subscription ID.
        user_id: Billed user ID.
        status: Invoice status.
        subtotal: Subtotal before tax and discounts.
        tax_amount: Tax amount.
        discount_amount: Discount applied.
        total: Final total amount.
        amount_paid: Amount already paid.
        amount_remaining: Amount still owed.
        currency: Currency code.
        due_date: Payment due date.
        paid_at: When invoice was paid.
        line_items: List of invoice line items.
        notes: Additional notes.
        metadata_json: Additional metadata.
        created_at: Creation timestamp.
    """

    __tablename__ = "billing_invoices"
    __table_args__ = (
        Index("ix_billing_invoices_subscription_id", "subscription_id"),
        Index("ix_billing_invoices_user_id", "user_id"),
        Index("ix_billing_invoices_status", "status"),
        Index("ix_billing_invoices_due_date", "due_date"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    subscription_id: Mapped[str] = mapped_column(String(36), ForeignKey("billing_subscriptions.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[InvoiceStatus] = mapped_column(SAEnum(InvoiceStatus), default=InvoiceStatus.DRAFT, nullable=False)
    invoice_number: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0"), nullable=False)
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0"), nullable=False)
    total: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    amount_paid: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0"), nullable=False)
    amount_remaining: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    line_items: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    subscription: Mapped[Subscription] = relationship("Subscription", back_populates="invoices")
    payments: Mapped[list[Payment]] = relationship("Payment", back_populates="invoice", cascade="all, delete-orphan")

    @property
    def is_paid(self) -> bool:
        """Check if invoice is fully paid."""
        return self.status == InvoiceStatus.PAID

    @property
    def is_overdue(self) -> bool:
        """Check if invoice is past due."""
        if self.due_date is None or self.is_paid:
            return False
        return datetime.utcnow() > self.due_date


class Payment(Base):
    """Payment record for an invoice.

    Tracks individual payment transactions including method, amount, and status.

    Attributes:
        id: Unique payment identifier.
        invoice_id: Associated invoice ID.
        user_id: Paying user ID.
        amount: Payment amount.
        currency: Currency code.
        status: Payment status.
        method: Payment method used.
        external_id: External payment processor ID.
        failure_reason: Reason for failed payment.
        refunded_amount: Amount refunded.
        metadata_json: Additional metadata.
        created_at: Creation timestamp.
    """

    __tablename__ = "billing_payments"
    __table_args__ = (
        Index("ix_billing_payments_invoice_id", "invoice_id"),
        Index("ix_billing_payments_user_id", "user_id"),
        Index("ix_billing_payments_status", "status"),
        Index("ix_billing_payments_external_id", "external_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    invoice_id: Mapped[str] = mapped_column(String(36), ForeignKey("billing_invoices.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    status: Mapped[PaymentStatus] = mapped_column(SAEnum(PaymentStatus), default=PaymentStatus.PENDING, nullable=False)
    method: Mapped[PaymentMethod] = mapped_column(SAEnum(PaymentMethod), nullable=False)
    external_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    refunded_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0"), nullable=False)
    metadata_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    invoice: Mapped[Invoice] = relationship("Invoice", back_populates="payments")


class UsageRecord(Base):
    """Record of resource usage for billing purposes.

    Tracks consumption of billable resources for usage-based pricing.

    Attributes:
        id: Unique record identifier.
        user_id: User who consumed the resource.
        subscription_id: Associated subscription ID.
        usage_type: Type of usage recorded.
        quantity: Amount consumed.
        unit_price: Price per unit.
        total_cost: Total cost for this usage.
        recorded_at: When usage was recorded.
        period_start: Start of billing period.
        period_end: End of billing period.
        metadata_json: Additional metadata.
    """

    __tablename__ = "billing_usage_records"
    __table_args__ = (
        Index("ix_billing_usage_records_user_id", "user_id"),
        Index("ix_billing_usage_records_subscription_id", "subscription_id"),
        Index("ix_billing_usage_records_type", "usage_type"),
        Index("ix_billing_usage_records_recorded_at", "recorded_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    subscription_id: Mapped[str] = mapped_column(String(36), ForeignKey("billing_subscriptions.id", ondelete="CASCADE"), nullable=False)
    usage_type: Mapped[UsageType] = mapped_column(SAEnum(UsageType), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    total_cost: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    metadata_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)


class Coupon(Base):
    """Discount coupon for billing.

    Defines discount codes that can be applied to subscriptions.

    Attributes:
        id: Unique coupon identifier.
        code: Coupon code.
        name: Coupon name.
        description: Description of the discount.
        discount_type: Type of discount (percentage or fixed).
        discount_value: Discount value.
        currency: Currency for fixed discounts.
        max_redemptions: Maximum number of times usable.
        times_redeemed: Current redemption count.
        expires_at: Expiration date.
        is_active: Whether coupon is currently active.
        metadata_json: Additional metadata.
        created_at: Creation timestamp.
    """

    __tablename__ = "billing_coupons"
    __table_args__ = (
        Index("ix_billing_coupons_code", "code"),
        UniqueConstraint("code", name="uq_billing_coupons_code"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    discount_type: Mapped[str] = mapped_column(String(16), nullable=False)
    discount_value: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    max_redemptions: Mapped[int | None] = mapped_column(Integer, nullable=True)
    times_redeemed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    metadata_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    @property
    def is_valid(self) -> bool:
        """Check if coupon is currently valid."""
        if not self.is_active:
            return False
        if self.expires_at and datetime.utcnow() > self.expires_at:
            return False
        return not (self.max_redemptions and self.times_redeemed >= self.max_redemptions)


class PaymentMethod(Base):
    """Stored payment method for a user.

    Attributes:
        id: Unique identifier.
        user_id: Owner user ID.
        type: Payment method type.
        provider: Payment provider.
        last4: Last 4 digits for cards.
        expiry_month: Card expiry month.
        expiry_year: Card expiry year.
        is_default: Whether this is the default method.
        external_id: External payment method ID.
        billing_details: Billing address details.
        created_at: Creation timestamp.
    """

    __tablename__ = "billing_payment_methods"
    __table_args__ = (
        Index("ix_billing_payment_methods_user_id", "user_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    type: Mapped[PaymentMethod] = mapped_column(SAEnum(PaymentMethod), nullable=False)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    last4: Mapped[str | None] = mapped_column(String(4), nullable=True)
    expiry_month: Mapped[int | None] = mapped_column(Integer, nullable=True)
    expiry_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    external_id: Mapped[str] = mapped_column(String(255), nullable=False)
    billing_details: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
