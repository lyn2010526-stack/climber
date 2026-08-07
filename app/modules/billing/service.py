"""Billing service implementation.

This module provides comprehensive billing and subscription management
functionality including plan management, subscription lifecycle,
invoice generation, payment processing, and usage tracking.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

import structlog
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.billing.models import (
    BillingInterval,
    Coupon,
    Invoice,
    InvoiceStatus,
    Payment,
    PaymentMethod,
    PaymentStatus,
    Plan,
    PlanStatus,
    Subscription,
    SubscriptionStatus,
    UsageRecord,
    UsageType,
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

    async def create_plan(self, *args: Any, **kwargs: Any) -> Any:
        """Create a plan."""
        return await self.plans.create_plan(*args, **kwargs)

    async def get_plan(self, *args: Any, **kwargs: Any) -> Any:
        """Get a plan by id."""
        return await self.plans.get_plan(*args, **kwargs)

    async def update_plan(self, *args: Any, **kwargs: Any) -> Any:
        """Update a plan."""
        return await self.plans.update_plan(*args, **kwargs)

    async def delete_plan(self, *args: Any, **kwargs: Any) -> Any:
        """Delete a plan."""
        return await self.plans.delete_plan(*args, **kwargs)

    async def list_plans(self, *args: Any, **kwargs: Any) -> Any:
        """List plans."""
        return await self.plans.list_plans(*args, **kwargs)

    async def subscribe_user(self, *args: Any, **kwargs: Any) -> Any:
        """Create a subscription for a user."""
        return await self.subscriptions.create_subscription(*args, **kwargs)

    async def cancel_subscription(self, *args: Any, **kwargs: Any) -> Any:
        """Cancel a subscription."""
        return await self.subscriptions.cancel_subscription(*args, **kwargs)

    async def create_invoice(self, *args: Any, **kwargs: Any) -> Any:
        """Create an invoice."""
        return await self.invoices.create_invoice(*args, **kwargs)

    async def process_payment(self, *args: Any, **kwargs: Any) -> Any:
        """Process a payment."""
        return await self.payments.process_payment(*args, **kwargs)

    async def record_usage(self, *args: Any, **kwargs: Any) -> Any:
        """Record usage."""
        return await self.usage.record_usage(*args, **kwargs)

    async def list(self, *args: Any, **kwargs: Any) -> Any:
        """List plans."""
        return {}
