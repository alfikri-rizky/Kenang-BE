"""
Subscription plan definitions for Kenang.
Contains pricing, features, and limits for each subscription tier.
"""

from typing import Dict, List, Optional

from app.db.models.subscription import PlanId


class SubscriptionPlan:
    """Subscription plan data structure"""

    def __init__(
        self,
        plan_id: str,
        name_id: str,
        name_en: str,
        description_id: str,
        price_idr: int,
        billing_cycle: str,
        features: List[str],
        limits: Dict[str, Optional[int]],
        is_popular: bool = False,
        recommended_for: Optional[List[str]] = None,
    ):
        self.plan_id = plan_id
        self.name_id = name_id
        self.name_en = name_en
        self.description_id = description_id
        self.price_idr = price_idr
        self.billing_cycle = billing_cycle
        self.features = features
        self.limits = limits
        self.is_popular = is_popular
        self.recommended_for = recommended_for or []

    def to_dict(self) -> dict:
        return {
            "plan_id": self.plan_id,
            "name_id": self.name_id,
            "name_en": self.name_en,
            "description_id": self.description_id,
            "price_idr": self.price_idr,
            "billing_cycle": self.billing_cycle,
            "features": self.features,
            "limits": self.limits,
            "is_popular": self.is_popular,
            "recommended_for": self.recommended_for,
        }


# Subscription plan definitions
SUBSCRIPTION_PLANS: Dict[str, SubscriptionPlan] = {
    PlanId.FREE.value: SubscriptionPlan(
        plan_id=PlanId.FREE.value,
        name_id="Gratis",
        name_en="Free",
        description_id="Coba Kenang untuk kebutuhan dasar",
        price_idr=0,
        billing_cycle="lifetime",
        features=[
            "3 lingkaran maksimal",
            "50 foto per lingkaran",
            "10 cerita audio",
            "Transkripsi otomatis Bahasa Indonesia",
            "Prompt AI untuk memandu rekaman",
            "Storage 500MB",
        ],
        limits={
            "max_circles": 3,
            "max_photos_per_circle": 50,
            "max_stories": 10,
            "storage_mb": 500,
            "max_members_per_circle": 5,
        },
        is_popular=False,
    ),
    PlanId.PERSONAL.value: SubscriptionPlan(
        plan_id=PlanId.PERSONAL.value,
        name_id="Pribadi",
        name_en="Personal",
        description_id="Untuk individu yang ingin menyimpan lebih banyak kenangan",
        price_idr=29_000,
        billing_cycle="monthly",
        features=[
            "10 lingkaran maksimal",
            "200 foto per lingkaran",
            "100 cerita audio",
            "Transkripsi otomatis Bahasa Indonesia & Inggris",
            "Prompt AI untuk memandu rekaman",
            "Edit transkrip hasil AI",
            "Download foto & audio",
            "Storage 5GB",
            "Prioritas support",
        ],
        limits={
            "max_circles": 10,
            "max_photos_per_circle": 200,
            "max_stories": 100,
            "storage_mb": 5_000,
            "max_members_per_circle": 10,
        },
        is_popular=True,
        recommended_for=["Individu", "Keluarga kecil"],
    ),
    PlanId.PLUS.value: SubscriptionPlan(
        plan_id=PlanId.PLUS.value,
        name_id="Plus",
        name_en="Plus",
        description_id="Untuk keluarga besar atau komunitas kecil",
        price_idr=79_000,
        billing_cycle="monthly",
        features=[
            "25 lingkaran maksimal",
            "1.000 foto per lingkaran",
            "500 cerita audio",
            "Transkripsi otomatis multi-bahasa",
            "AI enhancement untuk cerita",
            "Pertanyaan follow-up otomatis",
            "Saran judul otomatis",
            "Kapsul waktu (time capsule)",
            "Export PDF & backup",
            "Storage 20GB",
            "Prioritas support",
        ],
        limits={
            "max_circles": 25,
            "max_photos_per_circle": 1_000,
            "max_stories": 500,
            "storage_mb": 20_000,
            "max_members_per_circle": 25,
        },
        is_popular=False,
        recommended_for=["Keluarga besar", "Komunitas kecil"],
    ),
    PlanId.PREMIUM.value: SubscriptionPlan(
        plan_id=PlanId.PREMIUM.value,
        name_id="Premium",
        name_en="Premium",
        description_id="Unlimited untuk organisasi dan komunitas besar",
        price_idr=149_000,
        billing_cycle="monthly",
        features=[
            "Lingkaran UNLIMITED",
            "Foto UNLIMITED per lingkaran",
            "Cerita audio UNLIMITED",
            "Transkripsi otomatis multi-bahasa",
            "AI enhancement untuk cerita",
            "Pertanyaan follow-up otomatis",
            "Saran judul otomatis",
            "Kapsul waktu (time capsule)",
            "Export PDF & backup",
            "Shared link untuk publik",
            "Custom domain (untuk tim)",
            "Analytics & insights",
            "Storage 100GB",
            "Priority support 24/7",
        ],
        limits={
            "max_circles": None,  # Unlimited
            "max_photos_per_circle": None,
            "max_stories": None,
            "storage_mb": 100_000,
            "max_members_per_circle": None,
        },
        is_popular=False,
        recommended_for=["Organisasi", "Komunitas besar", "Bisnis"],
    ),
    PlanId.CINTA.value: SubscriptionPlan(
        plan_id=PlanId.CINTA.value,
        name_id="Kenang Cinta",
        name_en="Love Memory",
        description_id="Paket spesial untuk pasangan dan pernikahan (one-time purchase)",
        price_idr=299_000,
        billing_cycle="one_time",
        features=[
            "5 lingkaran spesial",
            "500 foto untuk perjalanan cinta",
            "100 cerita audio",
            "Transkripsi otomatis",
            "Timeline perjalanan cinta",
            "Tema khusus pasangan",
            "Export buku kenangan digital",
            "Storage 10GB",
            "Akses selamanya (lifetime)",
        ],
        limits={
            "max_circles": 5,
            "max_photos_per_circle": 500,
            "max_stories": 100,
            "storage_mb": 10_000,
            "max_members_per_circle": 2,
        },
        is_popular=True,
        recommended_for=["Pasangan", "Pernikahan", "Anniversary"],
    ),
    PlanId.KELUARGA_YEARLY.value: SubscriptionPlan(
        plan_id=PlanId.KELUARGA_YEARLY.value,
        name_id="Kenang Keluarga (Tahunan)",
        name_en="Family Memory (Yearly)",
        description_id="Paket hemat untuk keluarga besar dengan pembayaran tahunan",
        price_idr=499_000,
        billing_cycle="yearly",
        features=[
            "20 lingkaran keluarga",
            "2.000 foto per lingkaran",
            "500 cerita audio",
            "Transkripsi otomatis",
            "AI enhancement untuk cerita",
            "Timeline keluarga",
            "Pohon keluarga digital",
            "Export buku keluarga",
            "Storage 50GB",
            "Hemat 50% dari paket Plus bulanan",
        ],
        limits={
            "max_circles": 20,
            "max_photos_per_circle": 2_000,
            "max_stories": 500,
            "storage_mb": 50_000,
            "max_members_per_circle": 50,
        },
        is_popular=False,
        recommended_for=["Keluarga besar", "Reuni keluarga"],
    ),
    PlanId.ALUMNI.value: SubscriptionPlan(
        plan_id=PlanId.ALUMNI.value,
        name_id="Kenang Alumni",
        name_en="Alumni Memory",
        description_id="Per orang untuk komunitas alumni sekolah/kampus",
        price_idr=50_000,
        billing_cycle="per_person_yearly",
        features=[
            "Bergabung dengan lingkaran alumni",
            "Upload foto kenangan sekolah/kampus",
            "Rekam cerita masa-masa kuliah/sekolah",
            "Akses ke foto & cerita alumni lain",
            "Timeline perjalanan alumni",
            "Storage 2GB per orang",
        ],
        limits={
            "max_circles": 3,
            "max_photos_per_circle": 100,
            "max_stories": 50,
            "storage_mb": 2_000,
            "max_members_per_circle": None,  # Unlimited for alumni circles
        },
        is_popular=False,
        recommended_for=["Sekolah", "Kampus", "Alumni"],
    ),
}


def get_plan(plan_id: str) -> Optional[SubscriptionPlan]:
    """Get subscription plan by ID"""
    return SUBSCRIPTION_PLANS.get(plan_id)


def get_all_plans() -> List[SubscriptionPlan]:
    """Get all available subscription plans"""
    return list(SUBSCRIPTION_PLANS.values())


def get_purchasable_plans() -> List[SubscriptionPlan]:
    """Get plans that can be purchased (exclude FREE)"""
    return [plan for plan in SUBSCRIPTION_PLANS.values() if plan.plan_id != PlanId.FREE.value]


def get_plan_price(plan_id: str) -> int:
    """Get price in IDR for a plan"""
    plan = get_plan(plan_id)
    return plan.price_idr if plan else 0


def get_plan_limits(plan_id: str) -> Dict[str, Optional[int]]:
    """Get limits for a plan"""
    plan = get_plan(plan_id)
    return plan.limits if plan else {}
