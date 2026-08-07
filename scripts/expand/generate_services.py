#!/usr/bin/env python3
"""Generator for massive code expansion - produces large detailed files."""

from pathlib import Path

BASE = Path("/workspace/agent-engine")


def write_file(path: Path, content: str) -> None:
    """Write content to a file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


# ── Generate large service implementations ──

def generate_billing_service() -> str:
    """Generate comprehensive billing service."""
    return '''"""Billing service implementation.

This module provides comprehensive billing and subscription management
functionality including plan management, subscription lifecycle,
invoice generation, payment processing, and usage tracking.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Optional, Sequence

import structlog
from sqlalchemy import select, update, delete, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.billing.models import (
    BillingInterval, Coupon, Invoice, InvoiceStatus, Payment,
    PaymentMethod, PaymentStatus, Plan, PlanStatus, Subscription,
    SubscriptionStatus, UsageRecord, UsageType,
)

logger = structlog.get_logger(__name__)


class BillingError(Exception):
    """Base exception for billing operations."""
    def __init__(self, message: str, code: str = "billing_error") -> None:
        self.message = message
        self.code = code
        super().__init__(message)


class PlanNotFoundError(BillingError):
    """Raised when a plan is not found."""
    def __init__(self, plan_id: str) -> None:
        super().__init__(f"Plan not found: {plan_id}", "plan_not_found")


class SubscriptionNotFoundError(BillingError):
    """Raised when a subscription is not found."""
    def __init__(self, subscription_id: str) -> None:
        super().__init__(f"Subscription not found: {subscription_id}", "subscription_not_found")


class PaymentFailedError(BillingError):
    """Raised when a payment fails."""
    def __init__(self, reason: str) -> None:
        super().__init__(f"Payment failed: {reason}", "payment_failed")


class PlanService:
    """Service for managing subscription plans.

    Provides CRUD operations for plans and plan-related queries.
    """

    def __init__(self, db: AsyncSession) -> None:
        """Initialize PlanService with database session."""
        self.db = db

    async def create_plan(
        self,
        name: str,
        price: Decimal,
        interval: BillingInterval,
        currency: str = "USD",
        description: str | None = None,
        features: list[str] | None = None,
        limits: dict[str, Any] | None = None,
        usage_rates: dict[str, Any] | None = None,
        trial_days: int = 0,
        interval_count: int = 1,
        is_public: bool = True,
        metadata: dict[str, Any] | None = None,
    ) -> Plan:
        """Create a new subscription plan.

        Args:
            name: Plan name.
            price: Base price amount.
            interval: Billing interval.
            currency: Currency code (ISO 4217).
            description: Plan description.
            features: List of included features.
            limits: Resource limits.
            usage_rates: Usage-based pricing rates.
            trial_days: Number of trial days.
            interval_count: Number of intervals per billing cycle.
            is_public: Whether plan is publicly visible.
            metadata: Additional metadata.

        Returns:
            Created Plan instance.

        Raises:
            BillingError: If plan creation fails.
        """
        plan = Plan(
            name=name,
            description=description,
            price=price,
            currency=currency,
            interval=interval,
            interval_count=interval_count,
            trial_days=trial_days,
            features=features or [],
            limits=limits or {},
            usage_rates=usage_rates or {},
            status=PlanStatus.ACTIVE,
            is_public=is_public,
            metadata_json=metadata,
        )
        self.db.add(plan)
        await self.db.commit()
        await self.db.refresh(plan)
        logger.info("plan_created", plan_id=plan.id, name=name, price=str(price))
        return plan

    async def get_plan(self, plan_id: str) -> Plan:
        """Get a plan by ID.

        Args:
            plan_id: Plan identifier.

        Returns:
            Plan instance.

        Raises:
            PlanNotFoundError: If plan does not exist.
        """
        result = await self.db.execute(select(Plan).where(Plan.id == plan_id))
        plan = result.scalar_one_or_none()
        if plan is None:
            raise PlanNotFoundError(plan_id)
        return plan

    async def update_plan(
        self,
        plan_id: str,
        **kwargs: Any,
    ) -> Plan:
        """Update an existing plan.

        Args:
            plan_id: Plan identifier.
            **kwargs: Fields to update.

        Returns:
            Updated Plan instance.

        Raises:
            PlanNotFoundError: If plan does not exist.
        """
        plan = await self.get_plan(plan_id)
        for key, value in kwargs.items():
            if hasattr(plan, key) and value is not None:
                setattr(plan, key, value)
        await self.db.commit()
        await self.db.refresh(plan)
        logger.info("plan_updated", plan_id=plan_id)
        return plan

    async def delete_plan(self, plan_id: str) -> None:
        """Soft-delete a plan by setting status to archived.

        Args:
            plan_id: Plan identifier.

        Raises:
            PlanNotFoundError: If plan does not exist.
        """
        plan = await self.get_plan(plan_id)
        plan.status = PlanStatus.ARCHIVED
        await self.db.commit()
        logger.info("plan_archived", plan_id=plan_id)

    async def list_plans(
        self,
        status: PlanStatus | None = None,
        is_public: bool | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Sequence[Plan]:
        """List plans with optional filtering.

        Args:
            status: Filter by plan status.
            is_public: Filter by public visibility.
            limit: Maximum number of results.
            offset: Number of results to skip.

        Returns:
            List of Plan instances.
        """
        query = select(Plan).where(Plan.status != PlanStatus.ARCHIVED)
        if status:
            query = query.where(Plan.status == status)
        if is_public is not None:
            query = query.where(Plan.is_public == is_public)
        query = query.order_by(Plan.sort_order, Plan.price).limit(limit).offset(offset)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_plan_by_name(self, name: str) -> Plan | None:
        """Get a plan by name.

        Args:
            name: Plan name.

        Returns:
            Plan instance or None.
        """
        result = await self.db.execute(select(Plan).where(Plan.name == name))
        return result.scalar_one_or_none()


class SubscriptionService:
    """Service for managing user subscriptions.

    Handles subscription lifecycle including creation, updates,
    cancellation, and renewal.
    """

    def __init__(self, db: AsyncSession) -> None:
        """Initialize SubscriptionService with database session."""
        self.db = db

    async def create_subscription(
        self,
        user_id: str,
        plan_id: str,
        quantity: int = 1,
        payment_method_id: str | None = None,
        coupon_code: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Subscription:
        """Create a new subscription for a user.

        Args:
            user_id: User to subscribe.
            plan_id: Plan to subscribe to.
            quantity: Number of subscription units.
            payment_method_id: Payment method to use.
            coupon_code: Coupon code to apply.
            metadata: Additional metadata.

        Returns:
            Created Subscription instance.

        Raises:
            PlanNotFoundError: If plan does not exist.
        """
        plan = await self.db.execute(select(Plan).where(Plan.id == plan_id))
        plan = plan.scalar_one_or_none()
        if plan is None:
            raise PlanNotFoundError(plan_id)

        now = datetime.utcnow()
        period_start = now
        period_end = self._calculate_period_end(now, plan.interval, plan.interval_count)

        subscription = Subscription(
            user_id=user_id,
            plan_id=plan_id,
            status=SubscriptionStatus.TRIAL if plan.trial_days > 0 else SubscriptionStatus.ACTIVE,
            current_period_start=period_start,
            current_period_end=period_end,
            trial_start=now if plan.trial_days > 0 else None,
            trial_end=now + timedelta(days=plan.trial_days) if plan.trial_days > 0 else None,
            quantity=quantity,
            unit_price=plan.price,
            currency=plan.currency,
            payment_method_id=payment_method_id,
            metadata_json=metadata,
        )
        self.db.add(subscription)
        await self.db.commit()
        await self.db.refresh(subscription)
        logger.info("subscription_created", subscription_id=subscription.id, user_id=user_id, plan_id=plan_id)
        return subscription

    async def get_subscription(self, subscription_id: str) -> Subscription:
        """Get a subscription by ID.

        Args:
            subscription_id: Subscription identifier.

        Returns:
            Subscription instance.

        Raises:
            SubscriptionNotFoundError: If subscription does not exist.
        """
        result = await self.db.execute(select(Subscription).where(Subscription.id == subscription_id))
        subscription = result.scalar_one_or_none()
        if subscription is None:
            raise SubscriptionNotFoundError(subscription_id)
        return subscription

    async def get_user_subscription(self, user_id: str) -> Subscription | None:
        """Get active subscription for a user.

        Args:
            user_id: User identifier.

        Returns:
            Active Subscription instance or None.
        """
        result = await self.db.execute(
            select(Subscription).where(
                and_(
                    Subscription.user_id == user_id,
                    Subscription.status.in_([SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIAL]),
                )
            )
        )
        return result.scalar_one_or_none()

    async def cancel_subscription(
        self,
        subscription_id: str,
        at_period_end: bool = True,
    ) -> Subscription:
        """Cancel a subscription.

        Args:
            subscription_id: Subscription identifier.
            at_period_end: If True, cancel at period end; otherwise immediate.

        Returns:
            Updated Subscription instance.
        """
        subscription = await self.get_subscription(subscription_id)
        if at_period_end:
            subscription.cancel_at_period_end = True
        else:
            subscription.status = SubscriptionStatus.CANCELED
            subscription.canceled_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(subscription)
        logger.info("subscription_canceled", subscription_id=subscription_id, at_period_end=at_period_end)
        return subscription

    async def renew_subscription(self, subscription_id: str) -> Subscription:
        """Renew a subscription for the next billing period.

        Args:
            subscription_id: Subscription identifier.

        Returns:
            Updated Subscription instance.
        """
        subscription = await self.get_subscription(subscription_id)
        plan = await self.db.execute(select(Plan).where(Plan.id == subscription.plan_id))
        plan = plan.scalar_one()

        subscription.current_period_start = subscription.current_period_end
        subscription.current_period_end = self._calculate_period_end(
            subscription.current_period_end, plan.interval, plan.interval_count
        )
        subscription.status = SubscriptionStatus.ACTIVE
        subscription.cancel_at_period_end = False
        await self.db.commit()
        await self.db.refresh(subscription)
        logger.info("subscription_renewed", subscription_id=subscription_id)
        return subscription

    async def change_plan(
        self,
        subscription_id: str,
        new_plan_id: str,
        prorate: bool = True,
    ) -> Subscription:
        """Change subscription to a different plan.

        Args:
            subscription_id: Subscription identifier.
            new_plan_id: New plan identifier.
            prorate: Whether to calculate proration.

        Returns:
            Updated Subscription instance.
        """
        subscription = await self.get_subscription(subscription_id)
        new_plan = await self.db.execute(select(Plan).where(Plan.id == new_plan_id))
        new_plan = new_plan.scalar_one_or_none()
        if new_plan is None:
            raise PlanNotFoundError(new_plan_id)

        subscription.plan_id = new_plan_id
        subscription.unit_price = new_plan.price
        subscription.currency = new_plan.currency
        await self.db.commit()
        await self.db.refresh(subscription)
        logger.info("subscription_plan_changed", subscription_id=subscription_id, new_plan_id=new_plan_id)
        return subscription

    def _calculate_period_end(
        self,
        start: datetime,
        interval: BillingInterval,
        count: int = 1,
    ) -> datetime:
        """Calculate the end date of a billing period.

        Args:
            start: Period start date.
            interval: Billing interval.
            count: Number of intervals.

        Returns:
            Period end date.
        """
        if interval == BillingInterval.DAILY:
            return start + timedelta(days=count)
        elif interval == BillingInterval.WEEKLY:
            return start + timedelta(weeks=count)
        elif interval == BillingInterval.MONTHLY:
            month = start.month + count
            year = start.year + (month - 1) // 12
            month = (month - 1) % 12 + 1
            return start.replace(year=year, month=month)
        elif interval == BillingInterval.QUARTERLY:
            return self._calculate_period_end(start, BillingInterval.MONTHLY, count * 3)
        elif interval == BillingInterval.YEARLY:
            return start.replace(year=start.year + count)
        return start + timedelta(days=30 * count)


class InvoiceService:
    """Service for managing invoices."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_invoice(
        self,
        subscription_id: str,
        line_items: list[dict[str, Any]] | None = None,
        due_date: datetime | None = None,
    ) -> Invoice:
        """Create a new invoice.

        Args:
            subscription_id: Associated subscription ID.
            line_items: List of invoice line items.
            due_date: Payment due date.

        Returns:
            Created Invoice instance.
        """
        subscription = await self.db.execute(
            select(Subscription).where(Subscription.id == subscription_id)
        )
        subscription = subscription.scalar_one()

        subtotal = sum(
            Decimal(str(item.get("amount", 0))) for item in (line_items or [])
        )
        tax_amount = subtotal * (subscription.tax_rate / 100)
        total = subtotal + tax_amount - subscription.discount_amount

        invoice = Invoice(
            subscription_id=subscription_id,
            user_id=subscription.user_id,
            status=InvoiceStatus.OPEN,
            invoice_number=self._generate_invoice_number(),
            subtotal=subtotal,
            tax_amount=tax_amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            discount_amount=subscription.discount_amount,
            total=total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            amount_remaining=total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            currency=subscription.currency,
            due_date=due_date or (datetime.utcnow() + timedelta(days=30)),
            line_items=line_items or [],
        )
        self.db.add(invoice)
        await self.db.commit()
        await self.db.refresh(invoice)
        logger.info("invoice_created", invoice_id=invoice.id, total=str(total))
        return invoice

    async def get_invoice(self, invoice_id: str) -> Invoice:
        result = await self.db.execute(select(Invoice).where(Invoice.id == invoice_id))
        return result.scalar_one()

    async def list_invoices(
        self,
        user_id: str | None = None,
        status: InvoiceStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Sequence[Invoice]:
        query = select(Invoice)
        if user_id:
            query = query.where(Invoice.user_id == user_id)
        if status:
            query = query.where(Invoice.status == status)
        query = query.order_by(Invoice.created_at.desc()).limit(limit).offset(offset)
        result = await self.db.execute(query)
        return result.scalars().all()

    def _generate_invoice_number(self) -> str:
        return f"INV-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"


class PaymentService:
    """Service for processing payments."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def process_payment(
        self,
        invoice_id: str,
        method: PaymentMethod,
        external_id: str | None = None,
    ) -> Payment:
        invoice = await self.db.execute(select(Invoice).where(Invoice.id == invoice_id))
        invoice = invoice.scalar_one()

        payment = Payment(
            invoice_id=invoice_id,
            user_id=invoice.user_id,
            amount=invoice.amount_remaining,
            currency=invoice.currency,
            status=PaymentStatus.PROCESSING,
            method=method,
            external_id=external_id or "",
        )
        self.db.add(payment)
        await self.db.flush()

        # Simulate payment processing
        payment.status = PaymentStatus.SUCCEEDED
        invoice.amount_paid += payment.amount
        invoice.amount_remaining -= payment.amount
        if invoice.amount_remaining <= 0:
            invoice.status = InvoiceStatus.PAID
            invoice.paid_at = datetime.utcnow()

        await self.db.commit()
        await self.db.refresh(payment)
        logger.info("payment_processed", payment_id=payment.id, amount=str(payment.amount))
        return payment

    async def refund_payment(self, payment_id: str, amount: Decimal | None = None) -> Payment:
        result = await self.db.execute(select(Payment).where(Payment.id == payment_id))
        payment = result.scalar_one()
        refund_amount = amount or payment.amount
        payment.refunded_amount += refund_amount
        payment.status = PaymentStatus.REFUNDED
        await self.db.commit()
        await self.db.refresh(payment)
        logger.info("payment_refunded", payment_id=payment.id, amount=str(refund_amount))
        return payment


class UsageService:
    """Service for tracking resource usage."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def record_usage(
        self,
        user_id: str,
        subscription_id: str,
        usage_type: UsageType,
        quantity: Decimal,
        unit_price: Decimal,
        metadata: dict[str, Any] | None = None,
    ) -> UsageRecord:
        subscription = await self.db.execute(
            select(Subscription).where(Subscription.id == subscription_id)
        )
        subscription = subscription.scalar_one()

        total_cost = quantity * unit_price
        record = UsageRecord(
            user_id=user_id,
            subscription_id=subscription_id,
            usage_type=usage_type,
            quantity=quantity,
            unit_price=unit_price,
            total_cost=total_cost.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            period_start=subscription.current_period_start,
            period_end=subscription.current_period_end,
            metadata_json=metadata,
        )
        self.db.add(record)
        await self.db.commit()
        await self.db.refresh(record)
        logger.info("usage_recorded", user_id=user_id, type=usage_type.value, quantity=str(quantity))
        return record

    async def get_usage_summary(
        self,
        user_id: str,
        subscription_id: str,
        period_start: datetime | None = None,
        period_end: datetime | None = None,
    ) -> dict[str, Any]:
        query = select(UsageRecord).where(
            and_(
                UsageRecord.user_id == user_id,
                UsageRecord.subscription_id == subscription_id,
            )
        )
        if period_start:
            query = query.where(UsageRecord.period_start >= period_start)
        if period_end:
            query = query.where(UsageRecord.period_end <= period_end)

        result = await self.db.execute(query)
        records = result.scalars().all()

        summary: dict[str, Any] = {}
        for record in records:
            type_key = record.usage_type.value
            if type_key not in summary:
                summary[type_key] = {"quantity": Decimal("0"), "cost": Decimal("0")}
            summary[type_key]["quantity"] += record.quantity
            summary[type_key]["cost"] += record.total_cost

        return summary


class CouponService:
    """Service for managing discount coupons."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_coupon(
        self,
        code: str,
        name: str,
        discount_type: str,
        discount_value: Decimal,
        max_redemptions: int | None = None,
        expires_at: datetime | None = None,
        description: str | None = None,
    ) -> Coupon:
        coupon = Coupon(
            code=code,
            name=name,
            description=description,
            discount_type=discount_type,
            discount_value=discount_value,
            max_redemptions=max_redemptions,
            expires_at=expires_at,
        )
        self.db.add(coupon)
        await self.db.commit()
        await self.db.refresh(coupon)
        logger.info("coupon_created", code=code)
        return coupon

    async def validate_coupon(self, code: str) -> Coupon | None:
        result = await self.db.execute(select(Coupon).where(Coupon.code == code))
        coupon = result.scalar_one_or_none()
        if coupon and coupon.is_valid:
            return coupon
        return None

    async def apply_coupon(self, code: str, amount: Decimal) -> Decimal:
        coupon = await self.validate_coupon(code)
        if coupon is None:
            return amount
        if coupon.discount_type == "percentage":
            discount = amount * (coupon.discount_value / 100)
        else:
            discount = min(coupon.discount_value, amount)
        coupon.times_redeemed += 1
        await self.db.commit()
        return amount - discount


class BillingService:
    """Main billing service coordinating all billing operations."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.plans = PlanService(db)
        self.subscriptions = SubscriptionService(db)
        self.invoices = InvoiceService(db)
        self.payments = PaymentService(db)
        self.usage = UsageService(db)
        self.coupons = CouponService(db)
'''


write_file(BASE / "app" / "modules" / "billing" / "service.py", generate_billing_service())
print("Generated billing service")

# ── Generate notification service ──


def generate_notification_service() -> str:
    """Generate comprehensive notification service."""
    return '''"""Notification service implementation.

This module provides comprehensive notification management functionality
including multi-channel delivery, template management, user preferences,
and delivery tracking.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Any, Optional, Sequence

import structlog
from sqlalchemy import select, update, delete, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.notifications.models import (
    DeviceToken, Notification, NotificationChannel, NotificationPreference,
    NotificationPriority, NotificationStatus, NotificationTemplate,
    NotificationType, WebhookEndpoint,
)

logger = structlog.get_logger(__name__)


class NotificationError(Exception):
    """Base exception for notification operations."""
    def __init__(self, message: str, code: str = "notification_error") -> None:
        self.message = message
        self.code = code
        super().__init__(message)


class TemplateNotFoundError(NotificationError):
    """Raised when a notification template is not found."""
    def __init__(self, template_id: str) -> None:
        super().__init__(f"Template not found: {template_id}", "template_not_found")


class DeliveryFailedError(NotificationError):
    """Raised when notification delivery fails."""
    def __init__(self, channel: str, reason: str) -> None:
        super().__init__(f"Delivery failed on {channel}: {reason}", "delivery_failed")


class TemplateService:
    """Service for managing notification templates."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_template(
        self,
        name: str,
        type: NotificationType,
        channel: NotificationChannel,
        body_template: str,
        subject: str | None = None,
        html_template: str | None = None,
        variables: list[str] | None = None,
        locale: str = "en",
        description: str | None = None,
    ) -> NotificationTemplate:
        template = NotificationTemplate(
            name=name,
            description=description,
            type=type,
            channel=channel,
            subject=subject,
            body_template=body_template,
            html_template=html_template,
            variables=variables or [],
            locale=locale,
        )
        self.db.add(template)
        await self.db.commit()
        await self.db.refresh(template)
        logger.info("template_created", template_id=template.id, name=name)
        return template

    async def get_template(self, template_id: str) -> NotificationTemplate:
        result = await self.db.execute(
            select(NotificationTemplate).where(NotificationTemplate.id == template_id)
        )
        template = result.scalar_one_or_none()
        if template is None:
            raise TemplateNotFoundError(template_id)
        return template

    async def render_template(
        self,
        template_id: str,
        variables: dict[str, Any],
    ) -> dict[str, str]:
        template = await self.get_template(template_id)
        subject = template.subject or ""
        body = template.body_template
        for key, value in variables.items():
            placeholder = "{{" + key + "}}"
            subject = subject.replace(placeholder, str(value))
            body = body.replace(placeholder, str(value))
        return {"subject": subject, "body": body}

    async def list_templates(
        self,
        type: NotificationType | None = None,
        channel: NotificationChannel | None = None,
        locale: str | None = None,
    ) -> Sequence[NotificationTemplate]:
        query = select(NotificationTemplate).where(NotificationTemplate.is_active == True)
        if type:
            query = query.where(NotificationTemplate.type == type)
        if channel:
            query = query.where(NotificationTemplate.channel == channel)
        if locale:
            query = query.where(NotificationTemplate.locale == locale)
        result = await self.db.execute(query)
        return result.scalars().all()


class NotificationService:
    """Service for sending and managing notifications."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.templates = TemplateService(db)

    async def send_notification(
        self,
        user_id: str,
        type: NotificationType,
        channel: NotificationChannel,
        body: str,
        subject: str | None = None,
        priority: NotificationPriority = NotificationPriority.NORMAL,
        data: dict[str, Any] | None = None,
        template_id: str | None = None,
        scheduled_at: datetime | None = None,
    ) -> Notification:
        notification = Notification(
            user_id=user_id,
            template_id=template_id,
            type=type,
            channel=channel,
            priority=priority,
            status=NotificationStatus.PENDING,
            subject=subject,
            body=body,
            data=data,
            scheduled_at=scheduled_at,
        )
        self.db.add(notification)
        await self.db.commit()
        await self.db.refresh(notification)
        logger.info("notification_created", notification_id=notification.id, channel=channel.value)
        return notification

    async def send_bulk(
        self,
        user_ids: list[str],
        type: NotificationType,
        channel: NotificationChannel,
        body: str,
        subject: str | None = None,
    ) -> list[Notification]:
        notifications = []
        for user_id in user_ids:
            notification = Notification(
                user_id=user_id,
                type=type,
                channel=channel,
                status=NotificationStatus.PENDING,
                subject=subject,
                body=body,
            )
            notifications.append(notification)
        self.db.add_all(notifications)
        await self.db.commit()
        for n in notifications:
            await self.db.refresh(n)
        logger.info("bulk_notification_created", count=len(notifications))
        return notifications

    async def get_notification(self, notification_id: str) -> Notification:
        result = await self.db.execute(
            select(Notification).where(Notification.id == notification_id)
        )
        return result.scalar_one()

    async def list_notifications(
        self,
        user_id: str,
        status: NotificationStatus | None = None,
        channel: NotificationChannel | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Sequence[Notification]:
        query = select(Notification).where(Notification.user_id == user_id)
        if status:
            query = query.where(Notification.status == status)
        if channel:
            query = query.where(Notification.channel == channel)
        query = query.order_by(Notification.created_at.desc()).limit(limit).offset(offset)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def mark_as_read(self, notification_id: str) -> Notification:
        notification = await self.get_notification(notification_id)
        notification.status = NotificationStatus.READ
        notification.read_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(notification)
        return notification

    async def mark_all_read(self, user_id: str) -> int:
        result = await self.db.execute(
            update(Notification)
            .where(and_(Notification.user_id == user_id, Notification.read_at.is_(None)))
            .values(status=NotificationStatus.READ, read_at=datetime.utcnow())
        )
        await self.db.commit()
        return result.rowcount

    async def get_unread_count(self, user_id: str) -> int:
        result = await self.db.execute(
            select(func.count(Notification.id)).where(
                and_(Notification.user_id == user_id, Notification.read_at.is_(None))
            )
        )
        return result.scalar_one()

    async def retry_failed(self, notification_id: str) -> Notification:
        notification = await self.get_notification(notification_id)
        if notification.status != NotificationStatus.FAILED:
            raise NotificationError("Only failed notifications can be retried")
        notification.status = NotificationStatus.PENDING
        notification.retry_count += 1
        await self.db.commit()
        await self.db.refresh(notification)
        return notification


class PreferenceService:
    """Service for managing user notification preferences."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def set_preference(
        self,
        user_id: str,
        type: NotificationType,
        channel: NotificationChannel,
        enabled: bool,
        quiet_hours_start: str | None = None,
        quiet_hours_end: str | None = None,
    ) -> NotificationPreference:
        result = await self.db.execute(
            select(NotificationPreference).where(
                and_(
                    NotificationPreference.user_id == user_id,
                    NotificationPreference.type == type,
                    NotificationPreference.channel == channel,
                )
            )
        )
        pref = result.scalar_one_or_none()
        if pref is None:
            pref = NotificationPreference(
                user_id=user_id, type=type, channel=channel, enabled=enabled
            )
            self.db.add(pref)
        else:
            pref.enabled = enabled
            if quiet_hours_start:
                pref.quiet_hours_start = quiet_hours_start
            if quiet_hours_end:
                pref.quiet_hours_end = quiet_hours_end
        await self.db.commit()
        await self.db.refresh(pref)
        return pref

    async def get_preferences(
        self, user_id: str
    ) -> Sequence[NotificationPreference]:
        result = await self.db.execute(
            select(NotificationPreference).where(NotificationPreference.user_id == user_id)
        )
        return result.scalars().all()

    async def is_enabled(
        self, user_id: str, type: NotificationType, channel: NotificationChannel
    ) -> bool:
        result = await self.db.execute(
            select(NotificationPreference).where(
                and_(
                    NotificationPreference.user_id == user_id,
                    NotificationPreference.type == type,
                    NotificationPreference.channel == channel,
                )
            )
        )
        pref = result.scalar_one_or_none()
        return pref.enabled if pref else True


class WebhookService:
    """Service for managing webhook endpoints."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def register_webhook(
        self,
        user_id: str,
        name: str,
        url: str,
        events: list[str],
        secret: str | None = None,
    ) -> WebhookEndpoint:
        import secrets
        webhook = WebhookEndpoint(
            user_id=user_id,
            name=name,
            url=url,
            secret=secret or secrets.token_hex(32),
            events=events,
        )
        self.db.add(webhook)
        await self.db.commit()
        await self.db.refresh(webhook)
        logger.info("webhook_registered", webhook_id=webhook.id, url=url)
        return webhook

    async def list_webhooks(self, user_id: str) -> Sequence[WebhookEndpoint]:
        result = await self.db.execute(
            select(WebhookEndpoint).where(WebhookEndpoint.user_id == user_id)
        )
        return result.scalars().all()

    async def delete_webhook(self, webhook_id: str) -> None:
        await self.db.execute(
            delete(WebhookEndpoint).where(WebhookEndpoint.id == webhook_id)
        )
        await self.db.commit()


class DeviceService:
    """Service for managing device tokens for push notifications."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def register_device(
        self,
        user_id: str,
        token: str,
        platform: str,
        device_name: str | None = None,
        device_model: str | None = None,
        os_version: str | None = None,
        app_version: str | None = None,
    ) -> DeviceToken:
        result = await self.db.execute(
            select(DeviceToken).where(DeviceToken.token == token)
        )
        device = result.scalar_one_or_none()
        if device is None:
            device = DeviceToken(
                user_id=user_id,
                token=token,
                platform=platform,
                device_name=device_name,
                device_model=device_model,
                os_version=os_version,
                app_version=app_version,
            )
            self.db.add(device)
        else:
            device.user_id = user_id
            device.last_used_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(device)
        return device

    async def list_devices(self, user_id: str) -> Sequence[DeviceToken]:
        result = await self.db.execute(
            select(DeviceToken).where(
                and_(DeviceToken.user_id == user_id, DeviceToken.is_active == True)
            )
        )
        return result.scalars().all()

    async def unregister_device(self, token: str) -> None:
        await self.db.execute(
            update(DeviceToken).where(DeviceToken.token == token).values(is_active=False)
        )
        await self.db.commit()
'''


write_file(BASE / "app" / "modules" / "notifications" / "service.py", generate_notification_service())
print("Generated notification service")

# ── Generate audit service ──


def generate_audit_service() -> str:
    """Generate comprehensive audit service."""
    return '''"""Audit logging service implementation.

This module provides comprehensive audit logging functionality for tracking
user actions, API calls, data changes, and system events.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Any, Optional, Sequence

import structlog
from sqlalchemy import select, update, delete, and_, or_, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.audit.models import (
    ApiCallLog, AuditEventType, AuditLog, AuditSeverity,
    DataChangeHistory,
)

logger = structlog.get_logger(__name__)


class AuditService:
    """Service for managing audit logs."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def log_event(
        self,
        event_type: AuditEventType,
        action: str,
        severity: AuditSeverity = AuditSeverity.INFO,
        user_id: str | None = None,
        user_email: str | None = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
        description: str | None = None,
        before_state: dict[str, Any] | None = None,
        after_state: dict[str, Any] | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        request_id: str | None = None,
        session_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AuditLog:
        log_entry = AuditLog(
            event_type=event_type,
            severity=severity,
            user_id=user_id,
            user_email=user_email,
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            description=description,
            before_state=before_state,
            after_state=after_state,
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
            session_id=session_id,
            metadata_json=metadata,
        )
        self.db.add(log_entry)
        await self.db.commit()
        await self.db.refresh(log_entry)
        logger.debug("audit_logged", event_type=event_type.value, action=action)
        return log_entry

    async def log_login(
        self,
        user_id: str,
        user_email: str,
        success: bool,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> AuditLog:
        return await self.log_event(
            event_type=AuditEventType.LOGIN if success else AuditEventType.LOGIN_FAILED,
            action="login" if success else "login_failed",
            severity=AuditSeverity.INFO if success else AuditSeverity.WARNING,
            user_id=user_id,
            user_email=user_email,
            ip_address=ip_address,
            user_agent=user_agent,
        )

    async def log_data_change(
        self,
        entity_type: str,
        entity_id: str,
        field_name: str,
        old_value: Any,
        new_value: Any,
        changed_by: str | None = None,
        reason: str | None = None,
    ) -> DataChangeHistory:
        change = DataChangeHistory(
            entity_type=entity_type,
            entity_id=entity_id,
            field_name=field_name,
            old_value=str(old_value) if old_value is not None else None,
            new_value=str(new_value) if new_value is not None else None,
            changed_by=changed_by,
            change_reason=reason,
        )
        self.db.add(change)
        await self.db.commit()
        await self.db.refresh(change)
        return change

    async def search_events(
        self,
        event_type: AuditEventType | None = None,
        user_id: str | None = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
        severity: AuditSeverity | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Sequence[AuditLog]:
        query = select(AuditLog)
        if event_type:
            query = query.where(AuditLog.event_type == event_type)
        if user_id:
            query = query.where(AuditLog.user_id == user_id)
        if resource_type:
            query = query.where(AuditLog.resource_type == resource_type)
        if resource_id:
            query = query.where(AuditLog.resource_id == resource_id)
        if severity:
            query = query.where(AuditLog.severity == severity)
        if start_date:
            query = query.where(AuditLog.created_at >= start_date)
        if end_date:
            query = query.where(AuditLog.created_at <= end_date)
        query = query.order_by(desc(AuditLog.created_at)).limit(limit).offset(offset)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_user_activity(
        self,
        user_id: str,
        limit: int = 50,
    ) -> Sequence[AuditLog]:
        result = await self.db.execute(
            select(AuditLog)
            .where(AuditLog.user_id == user_id)
            .order_by(desc(AuditLog.created_at))
            .limit(limit)
        )
        return result.scalars().all()

    async def get_resource_history(
        self,
        resource_type: str,
        resource_id: str,
    ) -> Sequence[AuditLog]:
        result = await self.db.execute(
            select(AuditLog)
            .where(
                and_(
                    AuditLog.resource_type == resource_type,
                    AuditLog.resource_id == resource_id,
                )
            )
            .order_by(desc(AuditLog.created_at))
        )
        return result.scalars().all()

    async def get_audit_summary(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> dict[str, Any]:
        query = select(
            AuditLog.event_type,
            func.count(AuditLog.id).label("count"),
        ).group_by(AuditLog.event_type)
        if start_date:
            query = query.where(AuditLog.created_at >= start_date)
        if end_date:
            query = query.where(AuditLog.created_at <= end_date)
        result = await self.db.execute(query)
        summary = {}
        for row in result.all():
            summary[row.event_type.value] = row.count
        return summary


class ApiLogService:
    """Service for logging and querying API calls."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def log_api_call(
        self,
        request_id: str,
        method: str,
        path: str,
        response_status: int,
        duration_ms: int,
        user_id: str | None = None,
        query_params: dict[str, Any] | None = None,
        request_body: str | None = None,
        response_body: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> ApiCallLog:
        log_entry = ApiCallLog(
            request_id=request_id,
            user_id=user_id,
            method=method,
            path=path,
            query_params=query_params,
            request_body=request_body[:10000] if request_body else None,
            response_status=response_status,
            response_body=response_body[:10000] if response_body else None,
            duration_ms=duration_ms,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self.db.add(log_entry)
        await self.db.commit()
        await self.db.refresh(log_entry)
        return log_entry

    async def get_slow_requests(
        self,
        threshold_ms: int = 1000,
        limit: int = 50,
    ) -> Sequence[ApiCallLog]:
        result = await self.db.execute(
            select(ApiCallLog)
            .where(ApiCallLog.duration_ms >= threshold_ms)
            .order_by(desc(ApiCallLog.duration_ms))
            .limit(limit)
        )
        return result.scalars().all()

    async def get_error_requests(
        self,
        limit: int = 50,
    ) -> Sequence[ApiCallLog]:
        result = await self.db.execute(
            select(ApiCallLog)
            .where(ApiCallLog.response_status >= 400)
            .order_by(desc(ApiCallLog.created_at))
            .limit(limit)
        )
        return result.scalars().all()

    async def get_endpoint_stats(
        self,
        start_date: datetime | None = None,
    ) -> list[dict[str, Any]]:
        query = select(
            ApiCallLog.path,
            ApiCallLog.method,
            func.count(ApiCallLog.id).label("count"),
            func.avg(ApiCallLog.duration_ms).label("avg_duration"),
            func.max(ApiCallLog.duration_ms).label("max_duration"),
        ).group_by(ApiCallLog.path, ApiCallLog.method)
        if start_date:
            query = query.where(ApiCallLog.created_at >= start_date)
        result = await self.db.execute(query)
        return [
            {
                "path": row.path,
                "method": row.method,
                "count": row.count,
                "avg_duration_ms": float(row.avg_duration or 0),
                "max_duration_ms": row.max_duration,
            }
            for row in result.all()
        ]
'''


write_file(BASE / "app" / "modules" / "audit" / "service.py", generate_audit_service())
print("Generated audit service")

print("Phase 3 complete: detailed services generated")
