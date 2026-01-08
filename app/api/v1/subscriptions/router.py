"""
API router for subscription and payment endpoints.
"""

from typing import List

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.api.v1.subscriptions.schemas import (
    CancelSubscriptionRequest,
    CheckoutRequest,
    CheckoutResponse,
    MidtransWebhookPayload,
    PaymentResponse,
    PlanLimits,
    PlanResponse,
    SubscriptionResponse,
    WebhookResponse,
)
from app.core.exceptions import BusinessException, NotFoundException
from app.db.models import User
from app.db.models.subscription import Payment, PaymentProvider, PaymentStatus
from app.services.payment_service import PaymentService
from app.services.subscription_service import SubscriptionService
import structlog

router = APIRouter()
logger = structlog.get_logger(__name__)


@router.get(
    "/plans",
    response_model=List[PlanResponse],
    status_code=status.HTTP_200_OK,
    summary="Daftar paket subscription",
    description="Mendapatkan daftar semua paket subscription yang tersedia dengan harga dan fitur.",
)
async def get_subscription_plans(
    include_free: bool = False,
) -> List[PlanResponse]:
    """Get list of available subscription plans"""
    # Note: We don't need db here as plans are static data
    subscription_service = SubscriptionService(db=None)  # type: ignore
    plans = await subscription_service.get_available_plans(include_free=include_free)

    return [
        PlanResponse(
            plan_id=plan.plan_id,
            name_id=plan.name_id,
            name_en=plan.name_en,
            description_id=plan.description_id,
            price_idr=plan.price_idr,
            billing_cycle=plan.billing_cycle,
            features=plan.features,
            limits=PlanLimits(**plan.limits),
            is_popular=plan.is_popular,
            recommended_for=plan.recommended_for,
        )
        for plan in plans
    ]


@router.post(
    "/checkout",
    response_model=CheckoutResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Buat sesi checkout pembayaran",
    description="Membuat sesi checkout Midtrans untuk membeli subscription. "
    "Client akan redirect ke URL yang diberikan untuk menyelesaikan pembayaran.",
)
async def create_checkout(
    request: CheckoutRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CheckoutResponse:
    """Create Midtrans checkout session"""
    payment_service = PaymentService()

    # Create checkout session
    checkout_data = await payment_service.create_checkout_session(
        user_id=current_user.id,
        user_phone=current_user.phone_number,
        user_name=current_user.display_name or current_user.name or "Pengguna Kenang",
        plan_id=request.plan_id,
        payment_method=request.payment_method,
    )

    # Create pending payment record
    from app.data.subscription_plans import get_plan_price

    amount_idr = get_plan_price(request.plan_id)

    payment = Payment(
        user_id=current_user.id,
        subscription_id=None,  # Will be linked after successful payment
        amount_idr=amount_idr,
        payment_method=request.payment_method,
        payment_provider=PaymentProvider.MIDTRANS.value,
        payment_provider_transaction_id=checkout_data["order_id"],
        status=PaymentStatus.PENDING.value,
    )

    db.add(payment)
    await db.commit()

    logger.info(
        "checkout_created",
        user_id=current_user.id,
        plan_id=request.plan_id,
        order_id=checkout_data["order_id"],
    )

    return CheckoutResponse(
        redirect_url=checkout_data["redirect_url"],
        token=checkout_data["token"],
        order_id=checkout_data["order_id"],
    )


@router.get(
    "/current",
    response_model=SubscriptionResponse,
    status_code=status.HTTP_200_OK,
    summary="Subscription aktif saat ini",
    description="Mendapatkan informasi subscription aktif pengguna saat ini.",
)
async def get_current_subscription(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SubscriptionResponse:
    """Get user's current active subscription"""
    subscription_service = SubscriptionService(db)

    subscription = await subscription_service.get_current_subscription(current_user.id)

    if not subscription:
        raise NotFoundException("Subscription tidak ditemukan. Kamu sedang menggunakan paket gratis.")

    return SubscriptionResponse(
        id=subscription.id,
        user_id=subscription.user_id,
        plan_id=subscription.plan_id,
        status=subscription.status,
        payment_provider=subscription.payment_provider,
        current_period_start=subscription.current_period_start,
        current_period_end=subscription.current_period_end,
        cancelled_at=subscription.cancelled_at,
        created_at=subscription.created_at,
    )


@router.post(
    "/cancel",
    response_model=SubscriptionResponse,
    status_code=status.HTTP_200_OK,
    summary="Batalkan subscription",
    description="Membatalkan subscription aktif. Bisa segera atau di akhir periode.",
)
async def cancel_subscription(
    request: CancelSubscriptionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SubscriptionResponse:
    """Cancel active subscription"""
    subscription_service = SubscriptionService(db)

    # Get current subscription
    subscription = await subscription_service.get_current_subscription(current_user.id)

    if not subscription:
        raise NotFoundException("Subscription tidak ditemukan.")

    # Cancel subscription
    cancelled_subscription = await subscription_service.cancel_subscription(
        subscription_id=subscription.id,
        user_id=current_user.id,
        immediate=request.immediate,
    )

    return SubscriptionResponse(
        id=cancelled_subscription.id,
        user_id=cancelled_subscription.user_id,
        plan_id=cancelled_subscription.plan_id,
        status=cancelled_subscription.status,
        payment_provider=cancelled_subscription.payment_provider,
        current_period_start=cancelled_subscription.current_period_start,
        current_period_end=cancelled_subscription.current_period_end,
        cancelled_at=cancelled_subscription.cancelled_at,
        created_at=cancelled_subscription.created_at,
    )


@router.get(
    "/history",
    response_model=List[PaymentResponse],
    status_code=status.HTTP_200_OK,
    summary="Riwayat pembayaran",
    description="Mendapatkan riwayat pembayaran pengguna.",
)
async def get_payment_history(
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[PaymentResponse]:
    """Get user's payment history"""
    subscription_service = SubscriptionService(db)

    payments = await subscription_service.get_payment_history(
        user_id=current_user.id,
        limit=limit,
        offset=offset,
    )

    return [
        PaymentResponse(
            id=payment.id,
            user_id=payment.user_id,
            subscription_id=payment.subscription_id,
            amount_idr=payment.amount_idr,
            payment_method=payment.payment_method,
            payment_provider=payment.payment_provider,
            payment_provider_transaction_id=payment.payment_provider_transaction_id,
            status=payment.status,
            completed_at=payment.completed_at,
            created_at=payment.created_at,
        )
        for payment in payments
    ]


@router.post(
    "/webhooks/midtrans",
    response_model=WebhookResponse,
    status_code=status.HTTP_200_OK,
    summary="Webhook Midtrans",
    description="Endpoint untuk menerima notifikasi pembayaran dari Midtrans.",
)
async def midtrans_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> WebhookResponse:
    """
    Handle payment notification webhook from Midtrans.
    This endpoint is called by Midtrans when payment status changes.
    """
    try:
        # Parse request body
        payload = await request.json()

        logger.info("webhook_received", payload=payload)

        payment_service = PaymentService()

        # Parse notification
        notification = payment_service.parse_payment_notification(payload)

        # Verify signature
        is_valid = payment_service.verify_signature(
            order_id=notification["order_id"],
            status_code=notification["status_code"],
            gross_amount=notification["gross_amount"],
            signature_key=notification["signature_key"],
        )

        if not is_valid:
            logger.error("webhook_invalid_signature", order_id=notification["order_id"])
            raise BusinessException(
                code="INVALID_SIGNATURE",
                message="Signature tidak valid",
            )

        order_id = notification["order_id"]
        payment_status = notification["payment_status"]
        transaction_id = notification["transaction_id"]
        payment_type = notification["payment_type"]

        # Find payment by order_id (stored in payment_provider_transaction_id)
        from sqlalchemy import select

        query = select(Payment).where(Payment.payment_provider_transaction_id == order_id)
        result = await db.execute(query)
        payment = result.scalar_one_or_none()

        if not payment:
            logger.error("webhook_payment_not_found", order_id=order_id)
            raise NotFoundException(f"Pembayaran dengan order_id {order_id} tidak ditemukan")

        # Check for duplicate notification (idempotency)
        if payment.status == PaymentStatus.SUCCESS.value and payment_status == "success":
            logger.info("webhook_duplicate_success", order_id=order_id)
            return WebhookResponse(
                status="ok",
                message="Pembayaran sudah diproses sebelumnya",
                order_id=order_id,
            )

        # Update payment status
        old_status = payment.status
        payment.status = payment_status

        if payment_status == "success":
            from datetime import datetime

            payment.completed_at = datetime.utcnow()
            payment.payment_method = payment_service.map_midtrans_payment_type(payment_type)

        await db.flush()

        # If payment successful, create/activate subscription
        if payment_status == "success" and old_status != PaymentStatus.SUCCESS.value:
            subscription_service = SubscriptionService(db)

            # Extract plan_id from order_id format: SUB-{user_id}-{timestamp}-{random}
            # But we need to get it from payment record. For now, we'll need to store it.
            # Let's check if there's a pending subscription or create new one

            # Get plan_id from the payment amount (reverse lookup)
            from app.data.subscription_plans import get_all_plans

            plan_id = None
            for plan in get_all_plans():
                if plan.price_idr == payment.amount_idr:
                    plan_id = plan.plan_id
                    break

            if not plan_id:
                logger.error(
                    "webhook_plan_not_found",
                    order_id=order_id,
                    amount=payment.amount_idr,
                )
                raise BusinessException(
                    code="PLAN_NOT_FOUND",
                    message="Tidak bisa menentukan paket dari jumlah pembayaran",
                )

            # Create subscription
            subscription = await subscription_service.create_subscription(
                user_id=payment.user_id,
                plan_id=plan_id,
                payment_id=payment.id,
            )

            # Link payment to subscription
            payment.subscription_id = subscription.id

            logger.info(
                "subscription_activated",
                order_id=order_id,
                subscription_id=subscription.id,
                plan_id=plan_id,
            )

        await db.commit()

        logger.info(
            "webhook_processed",
            order_id=order_id,
            old_status=old_status,
            new_status=payment_status,
        )

        return WebhookResponse(
            status="ok",
            message="Notifikasi pembayaran berhasil diproses",
            order_id=order_id,
        )

    except Exception as e:
        logger.error("webhook_processing_error", error=str(e))
        # Always return 200 to Midtrans to prevent retries on our errors
        # But log the error for debugging
        try:
            body = await request.json()
            order_id = body.get("order_id", "unknown")
        except:
            order_id = "unknown"

        return WebhookResponse(
            status="error",
            message=str(e),
            order_id=order_id,
        )
