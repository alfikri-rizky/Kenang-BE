"""
Subscription service for managing user subscriptions and plan access.
Handles subscription lifecycle, feature access checks, and tier upgrades.
"""

from datetime import datetime, timedelta
from typing import List, Optional

import structlog
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import BusinessException, ForbiddenException, NotFoundException
from app.data.subscription_plans import (
    SubscriptionPlan,
    get_all_plans,
    get_plan,
    get_purchasable_plans,
)
from app.db.models import SubscriptionTier
from app.db.models.subscription import (
    Payment,
    PaymentProvider,
    PaymentStatus,
    PlanId,
    Subscription,
    SubscriptionStatus,
)
from app.db.models.user import User

logger = structlog.get_logger(__name__)


class SubscriptionService:
    """Service for managing subscriptions"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_available_plans(self, include_free: bool = False) -> List[SubscriptionPlan]:
        """
        Get list of available subscription plans.

        Args:
            include_free: Whether to include FREE plan

        Returns:
            List of subscription plans
        """
        if include_free:
            plans = get_all_plans()
        else:
            plans = get_purchasable_plans()

        logger.info("plans_fetched", count=len(plans), include_free=include_free)
        return plans

    async def get_current_subscription(self, user_id: str) -> Optional[Subscription]:
        """
        Get user's current active subscription.

        Args:
            user_id: User ID

        Returns:
            Active subscription or None if user is on FREE plan

        Raises:
            NotFoundException: If user not found
        """
        # Verify user exists
        user_query = select(User).where(User.id == user_id)
        user_result = await self.db.execute(user_query)
        user = user_result.scalar_one_or_none()

        if not user:
            raise NotFoundException("Pengguna tidak ditemukan")

        # Get active subscription
        query = (
            select(Subscription)
            .where(
                and_(
                    Subscription.user_id == user_id,
                    Subscription.status == SubscriptionStatus.ACTIVE.value,
                )
            )
            .order_by(Subscription.created_at.desc())
        )

        result = await self.db.execute(query)
        subscription = result.scalar_one_or_none()

        return subscription

    async def create_subscription(
        self,
        user_id: str,
        plan_id: str,
        payment_id: str,
    ) -> Subscription:
        """
        Create a new subscription after successful payment.

        Args:
            user_id: User ID
            plan_id: Plan ID
            payment_id: Payment ID that triggered this subscription

        Returns:
            Created subscription

        Raises:
            NotFoundException: If user or payment not found
            BusinessException: If plan is invalid or payment not successful
        """
        # Verify user exists
        user_query = select(User).where(User.id == user_id)
        user_result = await self.db.execute(user_query)
        user = user_result.scalar_one_or_none()

        if not user:
            raise NotFoundException("Pengguna tidak ditemukan")

        # Verify plan exists
        plan = get_plan(plan_id)
        if not plan:
            raise BusinessException(
                code="INVALID_PLAN",
                message="Paket subscription tidak ditemukan.",
            )

        # Verify payment exists and is successful
        payment_query = select(Payment).where(Payment.id == payment_id)
        payment_result = await self.db.execute(payment_query)
        payment = payment_result.scalar_one_or_none()

        if not payment:
            raise NotFoundException("Pembayaran tidak ditemukan")

        if payment.status != PaymentStatus.SUCCESS.value:
            raise BusinessException(
                code="PAYMENT_NOT_SUCCESSFUL",
                message="Pembayaran belum berhasil. Tidak bisa membuat subscription.",
            )

        # Calculate period based on billing cycle
        now = datetime.utcnow()
        if plan.billing_cycle == "monthly":
            period_end = now + timedelta(days=30)
        elif plan.billing_cycle == "yearly":
            period_end = now + timedelta(days=365)
        elif plan.billing_cycle == "one_time":
            # One-time purchases are "lifetime" - set to 100 years
            period_end = now + timedelta(days=36500)
        else:
            period_end = now + timedelta(days=30)  # Default to monthly

        # Create subscription
        subscription = Subscription(
            user_id=user_id,
            plan_id=plan_id,
            status=SubscriptionStatus.ACTIVE.value,
            payment_provider=PaymentProvider.MIDTRANS.value,
            current_period_start=now,
            current_period_end=period_end,
        )

        self.db.add(subscription)
        await self.db.flush()

        # Update user's subscription tier
        tier_mapping = {
            PlanId.FREE.value: SubscriptionTier.FREE.value,
            PlanId.PERSONAL.value: SubscriptionTier.PERSONAL.value,
            PlanId.PLUS.value: SubscriptionTier.PLUS.value,
            PlanId.PREMIUM.value: SubscriptionTier.PREMIUM.value,
            PlanId.CINTA.value: SubscriptionTier.PLUS.value,  # Kenang Cinta → PLUS tier
            PlanId.KELUARGA_YEARLY.value: SubscriptionTier.PLUS.value,  # Kenang Keluarga → PLUS tier
            PlanId.ALUMNI.value: SubscriptionTier.PERSONAL.value,  # Alumni → PERSONAL tier
        }

        new_tier = tier_mapping.get(plan_id, SubscriptionTier.FREE.value)
        user.subscription_tier = new_tier

        await self.db.commit()
        await self.db.refresh(subscription)

        logger.info(
            "subscription_created",
            subscription_id=subscription.id,
            user_id=user_id,
            plan_id=plan_id,
            tier=new_tier,
            period_end=period_end.isoformat(),
        )

        return subscription

    async def cancel_subscription(
        self,
        subscription_id: str,
        user_id: str,
        immediate: bool = False,
    ) -> Subscription:
        """
        Cancel an active subscription.

        Args:
            subscription_id: Subscription ID
            user_id: User ID (for permission check)
            immediate: If True, cancel immediately. If False, cancel at period end.

        Returns:
            Updated subscription

        Raises:
            NotFoundException: If subscription not found
            ForbiddenException: If user doesn't own subscription
            BusinessException: If subscription is not active
        """
        query = select(Subscription).where(Subscription.id == subscription_id)
        result = await self.db.execute(query)
        subscription = result.scalar_one_or_none()

        if not subscription:
            raise NotFoundException("Subscription tidak ditemukan")

        if subscription.user_id != user_id:
            raise ForbiddenException("Kamu tidak punya akses ke subscription ini")

        if subscription.status != SubscriptionStatus.ACTIVE.value:
            raise BusinessException(
                code="SUBSCRIPTION_NOT_ACTIVE",
                message="Subscription tidak aktif. Tidak bisa dibatalkan.",
            )

        now = datetime.utcnow()
        subscription.cancelled_at = now

        if immediate:
            # Cancel immediately - set status to CANCELLED and downgrade to FREE
            subscription.status = SubscriptionStatus.CANCELLED.value
            subscription.current_period_end = now

            # Downgrade user to FREE tier
            user_query = select(User).where(User.id == user_id)
            user_result = await self.db.execute(user_query)
            user = user_result.scalar_one_or_none()
            if user:
                user.subscription_tier = SubscriptionTier.FREE.value

            logger.info(
                "subscription_cancelled_immediate",
                subscription_id=subscription_id,
                user_id=user_id,
            )
        else:
            # Cancel at period end - just mark cancelled_at
            # Background job will change status to CANCELLED when period ends
            logger.info(
                "subscription_cancelled_at_period_end",
                subscription_id=subscription_id,
                user_id=user_id,
                period_end=subscription.current_period_end.isoformat(),
            )

        await self.db.commit()
        await self.db.refresh(subscription)

        return subscription

    async def get_payment_history(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Payment]:
        """
        Get user's payment history.

        Args:
            user_id: User ID
            limit: Maximum number of records
            offset: Offset for pagination

        Returns:
            List of payments
        """
        query = (
            select(Payment)
            .where(Payment.user_id == user_id)
            .order_by(Payment.created_at.desc())
            .limit(limit)
            .offset(offset)
        )

        result = await self.db.execute(query)
        payments = result.scalars().all()

        return list(payments)

    async def check_feature_access(
        self,
        user_id: str,
        feature: str,
    ) -> bool:
        """
        Check if user has access to a specific feature.

        Args:
            user_id: User ID
            feature: Feature name (e.g., "time_capsule", "ai_enhancement")

        Returns:
            True if user has access, False otherwise
        """
        # Get user's current subscription
        subscription = await self.get_current_subscription(user_id)

        # Get user's tier
        user_query = select(User).where(User.id == user_id)
        user_result = await self.db.execute(user_query)
        user = user_result.scalar_one_or_none()

        if not user:
            return False

        tier = user.subscription_tier

        # Feature access matrix
        feature_access = {
            "time_capsule": [
                SubscriptionTier.PLUS.value,
                SubscriptionTier.PREMIUM.value,
            ],
            "ai_enhancement": [
                SubscriptionTier.PLUS.value,
                SubscriptionTier.PREMIUM.value,
            ],
            "export_pdf": [
                SubscriptionTier.PLUS.value,
                SubscriptionTier.PREMIUM.value,
            ],
            "public_sharing": [
                SubscriptionTier.PREMIUM.value,
            ],
            "analytics": [
                SubscriptionTier.PREMIUM.value,
            ],
        }

        allowed_tiers = feature_access.get(feature, [])
        has_access = tier in allowed_tiers

        logger.info(
            "feature_access_check",
            user_id=user_id,
            feature=feature,
            tier=tier,
            has_access=has_access,
        )

        return has_access

    async def expire_subscriptions(self) -> int:
        """
        Background job: Expire subscriptions that have passed their period_end.
        This should be called by a Celery periodic task.

        Returns:
            Number of subscriptions expired
        """
        now = datetime.utcnow()

        # Find active subscriptions that have expired
        query = (
            select(Subscription)
            .where(
                and_(
                    Subscription.status == SubscriptionStatus.ACTIVE.value,
                    Subscription.current_period_end < now,
                )
            )
            .options(selectinload(Subscription.user))
        )

        result = await self.db.execute(query)
        expired_subscriptions = result.scalars().all()

        count = 0
        for subscription in expired_subscriptions:
            subscription.status = SubscriptionStatus.EXPIRED.value

            # Downgrade user to FREE tier
            if subscription.user:
                subscription.user.subscription_tier = SubscriptionTier.FREE.value

            logger.info(
                "subscription_expired",
                subscription_id=subscription.id,
                user_id=subscription.user_id,
                plan_id=subscription.plan_id,
            )

            count += 1

        if count > 0:
            await self.db.commit()
            logger.info("subscriptions_expired_batch", count=count)

        return count
