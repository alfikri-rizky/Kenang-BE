"""
API schemas for subscription endpoints.
"""

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class PlanLimits(BaseModel):
    """Subscription plan limits"""

    max_circles: Optional[int] = Field(
        None, description="Maksimum lingkaran (None = unlimited)"
    )
    max_photos_per_circle: Optional[int] = Field(
        None, description="Maksimum foto per lingkaran"
    )
    max_stories: Optional[int] = Field(None, description="Maksimum cerita audio")
    storage_mb: Optional[int] = Field(None, description="Storage dalam MB")
    max_members_per_circle: Optional[int] = Field(
        None, description="Maksimum anggota per lingkaran"
    )


class PlanResponse(BaseModel):
    """Response schema for subscription plan"""

    plan_id: str = Field(..., description="ID paket")
    name_id: str = Field(..., description="Nama paket dalam Bahasa Indonesia")
    name_en: str = Field(..., description="Nama paket dalam Bahasa Inggris")
    description_id: str = Field(..., description="Deskripsi paket")
    price_idr: int = Field(..., description="Harga dalam Rupiah")
    billing_cycle: str = Field(
        ..., description="Siklus pembayaran: monthly, yearly, one_time, lifetime"
    )
    features: List[str] = Field(..., description="Daftar fitur yang tersedia")
    limits: PlanLimits = Field(..., description="Batas penggunaan untuk paket ini")
    is_popular: bool = Field(False, description="Apakah paket ini populer/rekomendasi")
    recommended_for: List[str] = Field(
        default_factory=list, description="Rekomendasi untuk siapa paket ini"
    )

    class Config:
        from_attributes = True


class CheckoutRequest(BaseModel):
    """Request to create checkout session"""

    plan_id: str = Field(..., description="ID paket yang ingin dibeli")
    payment_method: Optional[str] = Field(
        None,
        description="Metode pembayaran yang diinginkan: gopay, ovo, dana, shopeepay, bank_transfer, dll",
    )


class CheckoutResponse(BaseModel):
    """Response from checkout session creation"""

    redirect_url: str = Field(
        ..., description="URL untuk redirect ke halaman pembayaran Midtrans"
    )
    token: str = Field(..., description="Token pembayaran dari Midtrans")
    order_id: str = Field(..., description="Order ID untuk tracking pembayaran")


class SubscriptionResponse(BaseModel):
    """Response schema for subscription"""

    id: str = Field(..., description="ID subscription")
    user_id: str = Field(..., description="ID pengguna")
    plan_id: str = Field(..., description="ID paket")
    status: str = Field(..., description="Status: active, cancelled, expired, pending")
    payment_provider: Optional[str] = Field(None, description="Provider pembayaran")
    current_period_start: Optional[datetime] = Field(
        None, description="Tanggal mulai periode subscription"
    )
    current_period_end: Optional[datetime] = Field(
        None, description="Tanggal akhir periode subscription"
    )
    cancelled_at: Optional[datetime] = Field(
        None, description="Tanggal dibatalkan (jika ada)"
    )
    created_at: datetime = Field(..., description="Tanggal dibuat")

    class Config:
        from_attributes = True


class CancelSubscriptionRequest(BaseModel):
    """Request to cancel subscription"""

    immediate: bool = Field(
        False,
        description="Jika True, batalkan segera. Jika False, batalkan di akhir periode.",
    )


class PaymentResponse(BaseModel):
    """Response schema for payment"""

    id: str = Field(..., description="ID pembayaran")
    user_id: Optional[str] = Field(None, description="ID pengguna")
    subscription_id: Optional[str] = Field(None, description="ID subscription terkait")
    amount_idr: int = Field(..., description="Jumlah pembayaran dalam Rupiah")
    payment_method: Optional[str] = Field(None, description="Metode pembayaran")
    payment_provider: Optional[str] = Field(None, description="Provider pembayaran")
    payment_provider_transaction_id: Optional[str] = Field(
        None, description="Transaction ID dari provider"
    )
    status: str = Field(
        ..., description="Status: pending, success, failed, refunded, expired"
    )
    completed_at: Optional[datetime] = Field(
        None, description="Tanggal pembayaran selesai"
    )
    created_at: datetime = Field(..., description="Tanggal dibuat")

    class Config:
        from_attributes = True


class MidtransWebhookPayload(BaseModel):
    """Webhook payload from Midtrans"""

    order_id: str = Field(..., description="Order ID dari sistem kita")
    transaction_id: str = Field(..., description="Transaction ID dari Midtrans")
    transaction_status: str = Field(..., description="Status transaksi dari Midtrans")
    transaction_time: str = Field(..., description="Waktu transaksi")
    payment_type: str = Field(
        ..., description="Tipe pembayaran (gopay, bank_transfer, dll)"
    )
    gross_amount: str = Field(..., description="Total pembayaran")
    status_code: str = Field(..., description="Kode status")
    signature_key: str = Field(..., description="Signature untuk verifikasi")
    fraud_status: Optional[str] = Field("accept", description="Status fraud check")
    # Additional optional fields from Midtrans
    bank: Optional[str] = Field(None, description="Bank name (for bank transfer)")
    va_numbers: Optional[List[Dict]] = Field(
        None, description="VA numbers (for bank transfer)"
    )
    biller_code: Optional[str] = Field(None, description="Biller code (for Mandiri)")
    bill_key: Optional[str] = Field(None, description="Bill key (for Mandiri)")


class WebhookResponse(BaseModel):
    """Response for webhook"""

    status: str = Field(..., description="Status pemrosesan webhook")
    message: str = Field(..., description="Pesan hasil pemrosesan")
    order_id: str = Field(..., description="Order ID yang diproses")
