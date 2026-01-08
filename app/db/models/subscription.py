from enum import Enum

from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Index, String
from sqlalchemy.orm import relationship

from app.db.base import Base, TimestampMixin, UUIDMixin


class PlanId(str, Enum):
    FREE = "free"
    PERSONAL = "personal"
    PLUS = "plus"
    PREMIUM = "premium"
    TIM = "tim"
    CINTA = "cinta"
    KELUARGA_YEARLY = "keluarga_yearly"
    ALUMNI = "alumni"


class SubscriptionStatus(str, Enum):
    ACTIVE = "active"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    PAST_DUE = "past_due"
    PENDING = "pending"


class PaymentMethod(str, Enum):
    GOPAY = "gopay"
    OVO = "ovo"
    DANA = "dana"
    SHOPEEPAY = "shopeepay"
    BANK_TRANSFER_BCA = "bank_transfer_bca"
    BANK_TRANSFER_BNI = "bank_transfer_bni"
    BANK_TRANSFER_BRI = "bank_transfer_bri"
    BANK_TRANSFER_MANDIRI = "bank_transfer_mandiri"
    CREDIT_CARD = "credit_card"


class PaymentStatus(str, Enum):
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    REFUNDED = "refunded"
    EXPIRED = "expired"


class PaymentProvider(str, Enum):
    MIDTRANS = "midtrans"


class Subscription(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "subscriptions"

    user_id = Column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    plan_id = Column(String(50), nullable=False)
    status = Column(String(20), default=SubscriptionStatus.PENDING.value, nullable=False)
    payment_provider = Column(String(20), nullable=True)
    payment_provider_subscription_id = Column(String(255), nullable=True)
    current_period_start = Column(DateTime(timezone=True), nullable=True)
    current_period_end = Column(DateTime(timezone=True), nullable=True)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="subscriptions")
    payments = relationship(
        "Payment", back_populates="subscription", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_subscriptions_user_id", "user_id"),
        Index("idx_subscriptions_status", "status"),
        Index("idx_subscriptions_plan_id", "plan_id"),
    )


class Payment(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "payments"

    user_id = Column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    subscription_id = Column(
        String(36), ForeignKey("subscriptions.id", ondelete="SET NULL"), nullable=True
    )
    amount_idr = Column(BigInteger, nullable=False)
    payment_method = Column(String(50), nullable=True)
    payment_provider = Column(String(20), nullable=True)
    payment_provider_transaction_id = Column(String(255), nullable=True)
    status = Column(String(20), default=PaymentStatus.PENDING.value, nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    metadata = Column(String(1000), nullable=True)

    user = relationship("User", foreign_keys=[user_id])
    subscription = relationship("Subscription", back_populates="payments")

    __table_args__ = (
        Index("idx_payments_user_id", "user_id"),
        Index("idx_payments_subscription_id", "subscription_id"),
        Index("idx_payments_status", "status"),
        Index("idx_payments_created_at", "created_at"),
    )
