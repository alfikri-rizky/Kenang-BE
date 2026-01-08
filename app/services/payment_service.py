"""
Payment service for handling Midtrans payment gateway integration.
Supports Indonesian payment methods: GoPay, OVO, DANA, Bank Transfer, etc.
"""

import hashlib
import secrets
from datetime import datetime
from typing import Dict, Optional

import midtransclient
import structlog

from app.core.config import settings
from app.core.exceptions import BusinessException
from app.data.subscription_plans import get_plan

logger = structlog.get_logger(__name__)


class PaymentService:
    """Service for handling payments through Midtrans"""

    def __init__(self):
        if not settings.MIDTRANS_SERVER_KEY or not settings.MIDTRANS_CLIENT_KEY:
            logger.warning(
                "midtrans_not_configured", message="Midtrans API keys not set"
            )
            self.snap = None
        else:
            self.snap = midtransclient.Snap(
                is_production=settings.MIDTRANS_IS_PRODUCTION,
                server_key=settings.MIDTRANS_SERVER_KEY,
                client_key=settings.MIDTRANS_CLIENT_KEY,
            )

    def _generate_order_id(self, user_id: str) -> str:
        """Generate unique order ID for a transaction"""
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        random_suffix = secrets.token_hex(4)
        return f"SUB-{user_id[:8]}-{timestamp}-{random_suffix}"

    async def create_checkout_session(
        self,
        user_id: str,
        user_phone: str,
        user_name: str,
        plan_id: str,
        payment_method: Optional[str] = None,
    ) -> Dict[str, str]:
        """
        Create Midtrans Snap checkout session for subscription payment.

        Args:
            user_id: User ID
            user_phone: User phone number (for customer details)
            user_name: User display name
            plan_id: Subscription plan ID
            payment_method: Optional preferred payment method

        Returns:
            Dict with redirect_url, token, and order_id

        Raises:
            BusinessException: If Midtrans is not configured or API call fails
        """
        if not self.snap:
            raise BusinessException(
                code="PAYMENT_NOT_CONFIGURED",
                message="Layanan pembayaran tidak tersedia saat ini. Silakan hubungi admin.",
            )

        plan = get_plan(plan_id)
        if not plan:
            raise BusinessException(
                code="INVALID_PLAN",
                message="Paket subscription tidak ditemukan.",
            )

        if plan.price_idr == 0:
            raise BusinessException(
                code="FREE_PLAN_NOT_PURCHASABLE",
                message="Paket gratis tidak perlu dibeli.",
            )

        order_id = self._generate_order_id(user_id)

        transaction_details = {
            "order_id": order_id,
            "gross_amount": plan.price_idr,
        }

        item_details = [
            {
                "id": plan.plan_id,
                "price": plan.price_idr,
                "quantity": 1,
                "name": f"Kenang {plan.name_id}",
                "category": "subscription",
            }
        ]

        customer_details = {
            "first_name": user_name or "Pengguna Kenang",
            "phone": user_phone,
        }

        # Enable all Indonesian payment methods
        enabled_payments = [
            "gopay",
            "shopeepay",
            "other_qris",  # For DANA, OVO, etc. via QRIS
            "bca_va",
            "bni_va",
            "bri_va",
            "permata_va",
            "other_va",
            "credit_card",
        ]

        # If user specified a preferred payment method, prioritize it
        if payment_method:
            enabled_payments.insert(0, payment_method)

        transaction = {
            "transaction_details": transaction_details,
            "item_details": item_details,
            "customer_details": customer_details,
            "enabled_payments": enabled_payments,
            "callbacks": {
                "finish": f"{settings.APP_URL}/payment/success",
                "error": f"{settings.APP_URL}/payment/error",
                "pending": f"{settings.APP_URL}/payment/pending",
            },
        }

        try:
            response = self.snap.create_transaction(transaction)

            logger.info(
                "checkout_session_created",
                order_id=order_id,
                user_id=user_id,
                plan_id=plan_id,
                amount_idr=plan.price_idr,
            )

            return {
                "redirect_url": response["redirect_url"],
                "token": response["token"],
                "order_id": order_id,
            }

        except Exception as e:
            logger.error(
                "checkout_session_creation_failed",
                user_id=user_id,
                plan_id=plan_id,
                error=str(e),
            )
            raise BusinessException(
                code="PAYMENT_API_ERROR",
                message="Gagal membuat sesi pembayaran. Silakan coba lagi.",
            )

    def verify_signature(
        self,
        order_id: str,
        status_code: str,
        gross_amount: str,
        signature_key: str,
    ) -> bool:
        """
        Verify Midtrans webhook signature to ensure authenticity.

        Args:
            order_id: Transaction order ID
            status_code: Transaction status code
            gross_amount: Transaction amount
            signature_key: Signature from Midtrans webhook

        Returns:
            True if signature is valid, False otherwise
        """
        if not settings.MIDTRANS_SERVER_KEY:
            logger.error(
                "signature_verification_failed", reason="Server key not configured"
            )
            return False

        # Create signature string: order_id + status_code + gross_amount + server_key
        signature_string = (
            f"{order_id}{status_code}{gross_amount}{settings.MIDTRANS_SERVER_KEY}"
        )

        # Generate SHA512 hash
        calculated_signature = hashlib.sha512(signature_string.encode()).hexdigest()

        is_valid = calculated_signature == signature_key

        if not is_valid:
            logger.warning(
                "invalid_webhook_signature",
                order_id=order_id,
                provided_signature=signature_key[:16] + "...",
                calculated_signature=calculated_signature[:16] + "...",
            )

        return is_valid

    def parse_payment_notification(self, payload: dict) -> Dict[str, str]:
        """
        Parse Midtrans payment notification payload.

        Args:
            payload: Webhook payload from Midtrans

        Returns:
            Dictionary with parsed payment information

        Reference:
            https://docs.midtrans.com/reference/notification-response-body
        """
        order_id = payload.get("order_id", "")
        transaction_status = payload.get("transaction_status", "")
        fraud_status = payload.get("fraud_status", "accept")
        status_code = payload.get("status_code", "")
        gross_amount = payload.get("gross_amount", "")
        signature_key = payload.get("signature_key", "")
        payment_type = payload.get("payment_type", "")
        transaction_id = payload.get("transaction_id", "")
        transaction_time = payload.get("transaction_time", "")

        # Map Midtrans transaction_status to our PaymentStatus
        # https://docs.midtrans.com/reference/transaction-status
        status_mapping = {
            "capture": "success" if fraud_status == "accept" else "pending",
            "settlement": "success",
            "pending": "pending",
            "deny": "failed",
            "expire": "expired",
            "cancel": "failed",
            "refund": "refunded",
            "partial_refund": "refunded",
        }

        payment_status = status_mapping.get(transaction_status, "pending")

        return {
            "order_id": order_id,
            "transaction_id": transaction_id,
            "transaction_status": transaction_status,
            "payment_status": payment_status,
            "payment_type": payment_type,
            "gross_amount": gross_amount,
            "status_code": status_code,
            "signature_key": signature_key,
            "transaction_time": transaction_time,
            "fraud_status": fraud_status,
        }

    def map_midtrans_payment_type(self, midtrans_payment_type: str) -> str:
        """
        Map Midtrans payment_type to our PaymentMethod enum.

        Args:
            midtrans_payment_type: Payment type from Midtrans (e.g., 'gopay', 'bank_transfer')

        Returns:
            Our internal payment method string
        """
        # Midtrans payment types: gopay, shopeepay, qris, bank_transfer, echannel, credit_card, etc.
        mapping = {
            "gopay": "gopay",
            "shopeepay": "shopeepay",
            "qris": "dana",  # QRIS can be DANA, OVO, etc. - default to dana
            "bank_transfer": "bank_transfer_bca",  # Default to BCA
            "bca_va": "bank_transfer_bca",
            "bni_va": "bank_transfer_bni",
            "bri_va": "bank_transfer_bri",
            "permata_va": "bank_transfer_mandiri",
            "echannel": "bank_transfer_mandiri",
            "credit_card": "credit_card",
        }

        return mapping.get(midtrans_payment_type, midtrans_payment_type)
