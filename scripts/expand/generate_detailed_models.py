#!/usr/bin/env python3
"""Generator for large-scale code expansion with detailed implementations.

This generator creates substantial code files with full implementations,
comprehensive docstrings, type annotations, and usage examples.
"""

from pathlib import Path

BASE = Path("/workspace/agent-engine")


def write_file(path: Path, content: str) -> None:
    """Write content to a file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


# ── Extended Backend Modules with Full Implementations ──

def generate_billing_models() -> str:
    """Generate comprehensive billing models."""
    return '''"""Billing and subscription data models.

This module defines all data models for the billing system including
plans, subscriptions, invoices, payments, usage records, and coupons.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Optional

from sqlalchemy import (
    Boolean, DateTime, Enum as SAEnum, Float, ForeignKey,
    Index, Integer, Numeric, String, Text, UniqueConstraint, func, JSON
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.storage.database import Base


class BillingInterval(str, Enum):
    """Billing interval options."""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"
    ONE_TIME = "one_time"


class PlanStatus(str, Enum):
    """Plan status."""
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"
    DEPRECATED = "deprecated"


class SubscriptionStatus(str, Enum):
    """Subscription status."""
    TRIAL = "trial"
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELED = "canceled"
    EXPIRED = "expired"
    PAUSED = "paused"


class InvoiceStatus(str, Enum):
    """Invoice status."""
    DRAFT = "draft"
    OPEN = "open"
    PAID = "paid"
    VOID = "void"
    UNCOLLECTIBLE = "uncollectible"
    REFUNDED = "refunded"


class PaymentStatus(str, Enum):
    """Payment status."""
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELED = "canceled"
    REFUNDED = "refunded"
    DISPUTED = "disputed"


class PaymentMethod(str, Enum):
    """Payment method types."""
    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"
    BANK_TRANSFER = "bank_transfer"
    PAYPAL = "paypal"
    STRIPE = "stripe"
    ALIPAY = "alipay"
    WECHAT = "wechat"
    CRYPTO = "crypto"


class UsageType(str, Enum):
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
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
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
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    subscriptions: Mapped[list["Subscription"]] = relationship("Subscription", back_populates="plan")

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
    trial_start: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    trial_end: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    canceled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    cancel_at_period_end: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    tax_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("0"), nullable=False)
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0"), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    payment_method_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    plan: Mapped["Plan"] = relationship("Plan", back_populates="subscriptions")
    invoices: Mapped[list["Invoice"]] = relationship("Invoice", back_populates="subscription", cascade="all, delete-orphan")

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
    due_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    paid_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    line_items: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    subscription: Mapped["Subscription"] = relationship("Subscription", back_populates="invoices")
    payments: Mapped[list["Payment"]] = relationship("Payment", back_populates="invoice", cascade="all, delete-orphan")

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
    external_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    failure_reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    refunded_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0"), nullable=False)
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    invoice: Mapped["Invoice"] = relationship("Invoice", back_populates="payments")


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
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)


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
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    discount_type: Mapped[str] = mapped_column(String(16), nullable=False)
    discount_value: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    max_redemptions: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    times_redeemed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    @property
    def is_valid(self) -> bool:
        """Check if coupon is currently valid."""
        if not self.is_active:
            return False
        if self.expires_at and datetime.utcnow() > self.expires_at:
            return False
        if self.max_redemptions and self.times_redeemed >= self.max_redemptions:
            return False
        return True


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
    last4: Mapped[Optional[str]] = mapped_column(String(4), nullable=True)
    expiry_month: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    expiry_year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    external_id: Mapped[str] = mapped_column(String(255), nullable=False)
    billing_details: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
'''


# Generate billing models
write_file(BASE / "app" / "modules" / "billing" / "models.py", generate_billing_models())
print("Generated billing models")


def generate_notification_models() -> str:
    """Generate comprehensive notification models."""
    return '''"""Notification system data models.

This module defines all data models for the notification system including
notification templates, delivery records, user preferences, and device tokens.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import (
    Boolean, DateTime, Enum as SAEnum, ForeignKey,
    Index, Integer, String, Text, UniqueConstraint, func, JSON
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.storage.database import Base


class NotificationType(str, Enum):
    """Types of notifications."""
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


class NotificationChannel(str, Enum):
    """Delivery channels for notifications."""
    IN_APP = "in_app"
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"
    WEBHOOK = "webhook"
    SLACK = "slack"
    DISCORD = "discord"
    TELEGRAM = "telegram"


class NotificationStatus(str, Enum):
    """Status of notification delivery."""
    PENDING = "pending"
    QUEUED = "queued"
    SENDING = "sending"
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    FAILED = "failed"
    CANCELED = "canceled"
    RETRYING = "retrying"


class NotificationPriority(str, Enum):
    """Notification priority levels."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"
    CRITICAL = "critical"


class NotificationTemplate(Base):
    """Reusable notification template.

    Defines the structure and content of notifications that can be sent
    through various channels.

    Attributes:
        id: Unique template identifier.
        name: Template name.
        description: Template description.
        type: Notification type.
        channel: Delivery channel.
        subject: Email/SMS subject line.
        body_template: Template body with variable placeholders.
        html_template: HTML version for email.
        variables: List of template variables.
        locale: Language locale.
        version: Template version.
        is_active: Whether template is active.
        metadata_json: Additional metadata.
        created_at: Creation timestamp.
        updated_at: Last update timestamp.
    """

    __tablename__ = "notification_templates"
    __table_args__ = (
        Index("ix_notification_templates_name", "name"),
        Index("ix_notification_templates_type", "type"),
        Index("ix_notification_templates_channel", "channel"),
        UniqueConstraint("name", "locale", "channel", name="uq_notification_template"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    type: Mapped[NotificationType] = mapped_column(SAEnum(NotificationType), nullable=False)
    channel: Mapped[NotificationChannel] = mapped_column(SAEnum(NotificationChannel), nullable=False)
    subject: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    body_template: Mapped[str] = mapped_column(Text, nullable=False)
    html_template: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    variables: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    locale: Mapped[str] = mapped_column(String(16), default="en", nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class Notification(Base):
    """Individual notification instance.

    Represents a single notification sent to a user through a specific channel.

    Attributes:
        id: Unique notification identifier.
        user_id: Recipient user ID.
        template_id: Source template ID.
        type: Notification type.
        channel: Delivery channel.
        priority: Notification priority.
        status: Current delivery status.
        subject: Notification subject.
        body: Notification body content.
        data: Additional data for template rendering.
        sent_at: When notification was sent.
        delivered_at: When notification was delivered.
        read_at: When notification was read.
        error_message: Error message if delivery failed.
        retry_count: Number of delivery retries.
        max_retries: Maximum allowed retries.
        scheduled_at: Scheduled delivery time.
        metadata_json: Additional metadata.
        created_at: Creation timestamp.
    """

    __tablename__ = "notifications"
    __table_args__ = (
        Index("ix_notifications_user_id", "user_id"),
        Index("ix_notifications_status", "status"),
        Index("ix_notifications_type", "type"),
        Index("ix_notifications_channel", "channel"),
        Index("ix_notifications_created_at", "created_at"),
        Index("ix_notifications_scheduled_at", "scheduled_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    template_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("notification_templates.id", ondelete="SET NULL"), nullable=True)
    type: Mapped[NotificationType] = mapped_column(SAEnum(NotificationType), nullable=False)
    channel: Mapped[NotificationChannel] = mapped_column(SAEnum(NotificationChannel), nullable=False)
    priority: Mapped[NotificationPriority] = mapped_column(SAEnum(NotificationPriority), default=NotificationPriority.NORMAL, nullable=False)
    status: Mapped[NotificationStatus] = mapped_column(SAEnum(NotificationStatus), default=NotificationStatus.PENDING, nullable=False)
    subject: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    data: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    delivered_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    read_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_retries: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    scheduled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    @property
    def is_read(self) -> bool:
        """Check if notification has been read."""
        return self.read_at is not None

    @property
    def is_failed(self) -> bool:
        """Check if notification delivery failed."""
        return self.status == NotificationStatus.FAILED

    @property
    def can_retry(self) -> bool:
        """Check if notification can be retried."""
        return self.retry_count < self.max_retries and self.status == NotificationStatus.FAILED


class NotificationPreference(Base):
    """User notification preferences.

    Controls which notifications a user receives and through which channels.

    Attributes:
        id: Unique preference identifier.
        user_id: Associated user ID.
        type: Notification type preference applies to.
        channel: Channel preference applies to.
        enabled: Whether this notification type/channel is enabled.
        quiet_hours_start: Start of quiet hours.
        quiet_hours_end: End of quiet hours.
        quiet_hours_timezone: Timezone for quiet hours.
        created_at: Creation timestamp.
        updated_at: Last update timestamp.
    """

    __tablename__ = "notification_preferences"
    __table_args__ = (
        Index("ix_notification_preferences_user_id", "user_id"),
        UniqueConstraint("user_id", "type", "channel", name="uq_notification_preference"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    type: Mapped[NotificationType] = mapped_column(SAEnum(NotificationType), nullable=False)
    channel: Mapped[NotificationChannel] = mapped_column(SAEnum(NotificationChannel), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    quiet_hours_start: Mapped[Optional[str]] = mapped_column(String(5), nullable=True)
    quiet_hours_end: Mapped[Optional[str]] = mapped_column(String(5), nullable=True)
    quiet_hours_timezone: Mapped[str] = mapped_column(String(64), default="UTC", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class DeviceToken(Base):
    """Device token for push notifications.

    Stores device registration tokens for mobile push notifications.

    Attributes:
        id: Unique token identifier.
        user_id: Device owner user ID.
        token: Device registration token.
        platform: Device platform (ios, android, web).
        device_name: Human-readable device name.
        device_model: Device model identifier.
        os_version: Operating system version.
        app_version: Application version.
        is_active: Whether token is still valid.
        last_used_at: Last time token was used.
        created_at: Creation timestamp.
    """

    __tablename__ = "device_tokens"
    __table_args__ = (
        Index("ix_device_tokens_user_id", "user_id"),
        Index("ix_device_tokens_token", "token"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token: Mapped[str] = mapped_column(String(512), nullable=False)
    platform: Mapped[str] = mapped_column(String(16), nullable=False)
    device_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    device_model: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    os_version: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    app_version: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class WebhookEndpoint(Base):
    """Webhook endpoint configuration.

    Defines webhook endpoints that receive event notifications.

    Attributes:
        id: Unique endpoint identifier.
        user_id: Owner user ID.
        url: Webhook URL.
        secret: Signing secret for verification.
        events: List of events to subscribe to.
        is_active: Whether webhook is active.
        failure_count: Consecutive failure count.
        last_success_at: Last successful delivery.
        last_failure_at: Last failed delivery.
        created_at: Creation timestamp.
    """

    __tablename__ = "webhook_endpoints"
    __table_args__ = (
        Index("ix_webhook_endpoints_user_id", "user_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    url: Mapped[str] = mapped_column(String(512), nullable=False)
    secret: Mapped[str] = mapped_column(String(255), nullable=False)
    events: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    failure_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_success_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_failure_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
'''


write_file(BASE / "app" / "modules" / "notifications" / "models.py", generate_notification_models())
print("Generated notification models")

# Generate audit models
def generate_audit_models() -> str:
    return '''"""Audit logging data models.

This module defines data models for comprehensive audit logging including
audit events, API call logs, and data change history.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import (
    Boolean, DateTime, Enum as SAEnum, ForeignKey,
    Index, Integer, String, Text, func, JSON
)
from sqlalchemy.dialects.postgresql import JSONB, INET
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.storage.database import Base


class AuditEventType(str, Enum):
    """Types of audit events."""
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    LOGIN = "login"
    LOGOUT = "logout"
    LOGIN_FAILED = "login_failed"
    PASSWORD_CHANGE = "password_change"
    PASSWORD_RESET = "password_reset"
    PERMISSION_CHANGE = "permission_change"
    ROLE_CHANGE = "role_change"
    API_CALL = "api_call"
    DATA_EXPORT = "data_export"
    DATA_IMPORT = "data_import"
    SETTINGS_CHANGE = "settings_change"
    BILLING_EVENT = "billing_event"
    SECURITY_EVENT = "security_event"
    SYSTEM_EVENT = "system_event"
    USER_ACTION = "user_action"
    WORKFLOW_ACTION = "workflow_action"


class AuditSeverity(str, Enum):
    """Severity levels for audit events."""
    DEBUG = "debug"
    INFO = "info"
    NOTICE = "notice"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"
    ALERT = "alert"
    EMERGENCY = "emergency"


class AuditLog(Base):
    """Comprehensive audit log entry.

    Records all significant actions and events in the system for
    security, compliance, and debugging purposes.

    Attributes:
        id: Unique log entry identifier.
        event_type: Type of event.
        severity: Event severity level.
        user_id: User who performed the action.
        user_email: User email at time of event.
        resource_type: Type of resource affected.
        resource_id: ID of affected resource.
        action: Action performed.
        description: Human-readable description.
        before_state: State before the change.
        after_state: State after the change.
        ip_address: Source IP address.
        user_agent: Client user agent.
        request_id: Associated request ID.
        session_id: Associated session ID.
        metadata_json: Additional metadata.
        created_at: Event timestamp.
    """

    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_logs_event_type", "event_type"),
        Index("ix_audit_logs_user_id", "user_id"),
        Index("ix_audit_logs_resource", "resource_type", "resource_id"),
        Index("ix_audit_logs_created_at", "created_at"),
        Index("ix_audit_logs_severity", "severity"),
        Index("ix_audit_logs_ip_address", "ip_address"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    event_type: Mapped[AuditEventType] = mapped_column(SAEnum(AuditEventType), nullable=False)
    severity: Mapped[AuditSeverity] = mapped_column(SAEnum(AuditSeverity), default=AuditSeverity.INFO, nullable=False)
    user_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    user_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    resource_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    resource_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    before_state: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    after_state: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    request_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    session_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class ApiCallLog(Base):
    """Log of API calls for monitoring and debugging.

    Attributes:
        id: Unique log identifier.
        request_id: Request correlation ID.
        user_id: Authenticated user ID.
        method: HTTP method.
        path: Request path.
        query_params: Query parameters.
        request_body: Request body (truncated).
        response_status: HTTP status code.
        response_body: Response body (truncated).
        duration_ms: Request duration in milliseconds.
        ip_address: Client IP address.
        user_agent: Client user agent.
        created_at: Request timestamp.
    """

    __tablename__ = "api_call_logs"
    __table_args__ = (
        Index("ix_api_call_logs_user_id", "user_id"),
        Index("ix_api_call_logs_path", "path"),
        Index("ix_api_call_logs_created_at", "created_at"),
        Index("ix_api_call_logs_status", "response_status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    request_id: Mapped[str] = mapped_column(String(64), nullable=False)
    user_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    method: Mapped[str] = mapped_column(String(8), nullable=False)
    path: Mapped[str] = mapped_column(String(512), nullable=False)
    query_params: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    request_body: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    response_status: Mapped[int] = mapped_column(Integer, nullable=False)
    response_body: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class DataChangeHistory(Base):
    """Track changes to important data entities.

    Provides a detailed history of data modifications for compliance
    and rollback purposes.

    Attributes:
        id: Unique history identifier.
        entity_type: Type of entity changed.
        entity_id: ID of changed entity.
        field_name: Name of changed field.
        old_value: Previous value.
        new_value: New value.
        changed_by: User who made the change.
        change_reason: Reason for the change.
        created_at: Change timestamp.
    """

    __tablename__ = "data_change_history"
    __table_args__ = (
        Index("ix_data_change_history_entity", "entity_type", "entity_id"),
        Index("ix_data_change_history_changed_by", "changed_by"),
        Index("ix_data_change_history_created_at", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(36), nullable=False)
    field_name: Mapped[str] = mapped_column(String(128), nullable=False)
    old_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    new_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    changed_by: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    change_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
'''


write_file(BASE / "app" / "modules" / "audit" / "models.py", generate_audit_models())
print("Generated audit models")

print("Phase 2 complete: detailed models generated")
