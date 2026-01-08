from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.api.v1.circles.schemas import (
    AddMemberRequest,
    CircleDetailResponse,
    CircleListResponse,
    CircleMemberResponse,
    CircleResponse,
    CreateCircleRequest,
    CreateInviteRequest,
    DeleteCircleResponse,
    InviteResponse,
    JoinCircleRequest,
    JoinCircleResponse,
    LeaveCircleResponse,
    MemberListResponse,
    MemberResponse,
    UpdateCircleRequest,
    UpdateMemberRequest,
)
from app.core.config import settings
from app.db.models import User
from app.services.circle_service import CircleService
from app.services.invite_service import InviteService

router = APIRouter()


@router.post(
    "",
    response_model=CircleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Buat lingkaran baru",
    description="Membuat lingkaran baru. User yang membuat otomatis menjadi admin.",
)
async def create_circle(
    request: CreateCircleRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CircleResponse:
    circle_service = CircleService(db)
    circle = await circle_service.create_circle(
        user_id=current_user.id,
        name=request.name,
        circle_type=request.type.value,
        description=request.description,
        cover_photo_url=request.cover_photo_url,
        privacy=request.privacy.value,
    )

    stats = await circle_service.get_circle_stats(circle.id)

    return CircleResponse(
        id=circle.id,
        name=circle.name,
        type=circle.type,
        description=circle.description,
        cover_photo_url=circle.cover_photo_url,
        privacy=circle.privacy,
        member_count=stats["member_count"],
        story_count=stats["story_count"],
        photo_count=stats["photo_count"],
        current_user_role="admin",
        created_by=circle.created_by,
        created_at=circle.created_at,
        updated_at=circle.updated_at,
    )


@router.get(
    "",
    response_model=CircleListResponse,
    status_code=status.HTTP_200_OK,
    summary="Dapatkan daftar lingkaran user",
    description="Mengembalikan semua lingkaran yang user ikuti.",
)
async def get_my_circles(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CircleListResponse:
    circle_service = CircleService(db)
    circles = await circle_service.get_user_circles(current_user.id)

    circle_responses = []
    for circle in circles:
        stats = await circle_service.get_circle_stats(circle.id)

        user_membership = next(
            (m for m in circle.memberships if m.user_id == current_user.id), None
        )

        circle_responses.append(
            CircleResponse(
                id=circle.id,
                name=circle.name,
                type=circle.type,
                description=circle.description,
                cover_photo_url=circle.cover_photo_url,
                privacy=circle.privacy,
                member_count=stats["member_count"],
                story_count=stats["story_count"],
                photo_count=stats["photo_count"],
                current_user_role=user_membership.role if user_membership else None,
                created_by=circle.created_by,
                created_at=circle.created_at,
                updated_at=circle.updated_at,
            )
        )

    return CircleListResponse(circles=circle_responses, total=len(circle_responses))


@router.get(
    "/{circle_id}",
    response_model=CircleDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Dapatkan detail lingkaran",
    description="Mengembalikan detail lengkap lingkaran termasuk anggota.",
)
async def get_circle_detail(
    circle_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CircleDetailResponse:
    circle_service = CircleService(db)
    circle = await circle_service.get_circle_by_id(circle_id, current_user.id)
    stats = await circle_service.get_circle_stats(circle_id)

    memberships, circle_members = await circle_service.get_circle_members(
        circle_id, current_user.id
    )

    member_responses = []
    for membership in memberships:
        member_responses.append(
            CircleMemberResponse(
                id=membership.id,
                user_id=membership.user_id,
                display_name=membership.user.display_name if membership.user else None,
                avatar_url=membership.user.avatar_url if membership.user else None,
                role=membership.role,
                custom_label=membership.custom_label,
                joined_at=membership.joined_at,
                is_current_user=(membership.user_id == current_user.id),
            )
        )

    for circle_member in circle_members:
        member_responses.append(
            CircleMemberResponse(
                id=circle_member.id,
                user_id=None,
                display_name=circle_member.name,
                avatar_url=circle_member.avatar_url,
                role="viewer",
                custom_label=circle_member.custom_label,
                joined_at=None,
                is_current_user=False,
            )
        )

    user_membership = next(
        (m for m in memberships if m.user_id == current_user.id), None
    )

    return CircleDetailResponse(
        id=circle.id,
        name=circle.name,
        type=circle.type,
        description=circle.description,
        cover_photo_url=circle.cover_photo_url,
        privacy=circle.privacy,
        member_count=stats["member_count"],
        story_count=stats["story_count"],
        photo_count=stats["photo_count"],
        current_user_role=user_membership.role if user_membership else None,
        created_by=circle.created_by,
        created_at=circle.created_at,
        updated_at=circle.updated_at,
        members=member_responses,
        invite_code=circle.invite_code,
        invite_code_expires_at=circle.invite_code_expires_at,
    )


@router.patch(
    "/{circle_id}",
    response_model=CircleResponse,
    status_code=status.HTTP_200_OK,
    summary="Perbarui lingkaran",
    description="Memperbarui informasi lingkaran. Hanya admin yang bisa.",
)
async def update_circle(
    circle_id: str,
    request: UpdateCircleRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CircleResponse:
    circle_service = CircleService(db)
    circle = await circle_service.update_circle(
        circle_id=circle_id,
        user_id=current_user.id,
        name=request.name,
        description=request.description,
        cover_photo_url=request.cover_photo_url,
        privacy=request.privacy.value if request.privacy else None,
    )

    stats = await circle_service.get_circle_stats(circle_id)

    user_membership = next(
        (m for m in circle.memberships if m.user_id == current_user.id), None
    )

    return CircleResponse(
        id=circle.id,
        name=circle.name,
        type=circle.type,
        description=circle.description,
        cover_photo_url=circle.cover_photo_url,
        privacy=circle.privacy,
        member_count=stats["member_count"],
        story_count=stats["story_count"],
        photo_count=stats["photo_count"],
        current_user_role=user_membership.role if user_membership else None,
        created_by=circle.created_by,
        created_at=circle.created_at,
        updated_at=circle.updated_at,
    )


@router.delete(
    "/{circle_id}",
    response_model=DeleteCircleResponse,
    status_code=status.HTTP_200_OK,
    summary="Hapus lingkaran",
    description="Soft delete lingkaran. Hanya admin yang bisa.",
)
async def delete_circle(
    circle_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DeleteCircleResponse:
    circle_service = CircleService(db)
    await circle_service.delete_circle(circle_id, current_user.id)

    return DeleteCircleResponse()


@router.get(
    "/{circle_id}/members",
    response_model=MemberListResponse,
    status_code=status.HTTP_200_OK,
    summary="Dapatkan daftar anggota lingkaran",
)
async def get_circle_members(
    circle_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MemberListResponse:
    circle_service = CircleService(db)
    memberships, circle_members = await circle_service.get_circle_members(
        circle_id, current_user.id
    )

    member_responses = []
    for membership in memberships:
        member_responses.append(
            MemberResponse(
                id=membership.id,
                circle_id=circle_id,
                user_id=membership.user_id,
                name=None,
                display_name=membership.user.display_name if membership.user else None,
                avatar_url=membership.user.avatar_url if membership.user else None,
                role=membership.role,
                custom_label=membership.custom_label,
                joined_at=membership.joined_at,
            )
        )

    for circle_member in circle_members:
        member_responses.append(
            MemberResponse(
                id=circle_member.id,
                circle_id=circle_id,
                user_id=None,
                name=circle_member.name,
                display_name=circle_member.name,
                avatar_url=circle_member.avatar_url,
                role="viewer",
                custom_label=circle_member.custom_label,
                joined_at=None,
            )
        )

    return MemberListResponse(members=member_responses, total=len(member_responses))


@router.post(
    "/{circle_id}/members",
    response_model=MemberResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Tambah anggota ke lingkaran",
    description="Menambahkan anggota baru. Hanya admin yang bisa.",
)
async def add_member(
    circle_id: str,
    request: AddMemberRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MemberResponse:
    circle_service = CircleService(db)
    membership, circle_member = await circle_service.add_member(
        circle_id=circle_id,
        admin_user_id=current_user.id,
        user_id=request.user_id,
        name=request.name,
        role=request.role.value,
        custom_label=request.custom_label,
    )

    if membership:
        return MemberResponse(
            id=membership.id,
            circle_id=circle_id,
            user_id=membership.user_id,
            name=None,
            display_name=membership.user.display_name if membership.user else None,
            avatar_url=membership.user.avatar_url if membership.user else None,
            role=membership.role,
            custom_label=membership.custom_label,
            joined_at=membership.joined_at,
        )
    else:
        return MemberResponse(
            id=circle_member.id,
            circle_id=circle_id,
            user_id=None,
            name=circle_member.name,
            display_name=circle_member.name,
            avatar_url=circle_member.avatar_url,
            role="viewer",
            custom_label=circle_member.custom_label,
            joined_at=None,
        )


@router.patch(
    "/{circle_id}/members/{membership_id}",
    response_model=MemberResponse,
    status_code=status.HTTP_200_OK,
    summary="Perbarui role anggota",
    description="Mengubah role atau label anggota. Hanya admin yang bisa.",
)
async def update_member_role(
    circle_id: str,
    membership_id: str,
    request: UpdateMemberRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MemberResponse:
    circle_service = CircleService(db)
    membership = await circle_service.update_member_role(
        circle_id=circle_id,
        membership_id=membership_id,
        admin_user_id=current_user.id,
        role=request.role.value if request.role else None,
        custom_label=request.custom_label,
    )

    return MemberResponse(
        id=membership.id,
        circle_id=circle_id,
        user_id=membership.user_id,
        name=None,
        display_name=membership.user.display_name if membership.user else None,
        avatar_url=membership.user.avatar_url if membership.user else None,
        role=membership.role,
        custom_label=membership.custom_label,
        joined_at=membership.joined_at,
    )


@router.delete(
    "/{circle_id}/members/{membership_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Hapus anggota dari lingkaran",
    description="Menghapus anggota. Hanya admin yang bisa.",
)
async def remove_member(
    circle_id: str,
    membership_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    circle_service = CircleService(db)
    await circle_service.remove_member(circle_id, membership_id, current_user.id)


@router.post(
    "/{circle_id}/invites",
    response_model=InviteResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Buat kode undangan",
    description="Membuat kode undangan untuk bergabung ke lingkaran. Hanya admin yang bisa.",
)
async def create_invite(
    circle_id: str,
    request: CreateInviteRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> InviteResponse:
    circle_service = CircleService(db)
    await circle_service._check_access(
        circle_id, current_user.id, required_role="admin"
    )

    invite_service = InviteService(db)
    invite = await invite_service.create_invite(
        circle_id=circle_id,
        invited_by=current_user.id,
        role=request.role.value,
        custom_label=request.custom_label,
        max_uses=request.max_uses,
    )

    invite_url = f"{settings.APP_URL}/join/{invite.invite_code}"

    return InviteResponse(
        id=invite.id,
        circle_id=invite.circle_id,
        invite_code=invite.invite_code,
        invite_url=invite_url,
        assigned_role=invite.assigned_role,
        assigned_label=invite.assigned_label,
        max_uses=invite.max_uses,
        use_count=invite.use_count,
        expires_at=invite.expires_at,
        created_at=invite.created_at,
    )


@router.post(
    "/join",
    response_model=JoinCircleResponse,
    status_code=status.HTTP_200_OK,
    summary="Bergabung ke lingkaran via kode undangan",
)
async def join_circle(
    request: JoinCircleRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> JoinCircleResponse:
    invite_service = InviteService(db)
    circle = await invite_service.join_circle_via_invite(
        request.invite_code, current_user.id
    )

    circle_service = CircleService(db)
    stats = await circle_service.get_circle_stats(circle.id)

    return JoinCircleResponse(
        circle=CircleResponse(
            id=circle.id,
            name=circle.name,
            type=circle.type,
            description=circle.description,
            cover_photo_url=circle.cover_photo_url,
            privacy=circle.privacy,
            member_count=stats["member_count"],
            story_count=stats["story_count"],
            photo_count=stats["photo_count"],
            current_user_role="contributor",
            created_by=circle.created_by,
            created_at=circle.created_at,
            updated_at=circle.updated_at,
        )
    )


@router.post(
    "/{circle_id}/leave",
    response_model=LeaveCircleResponse,
    status_code=status.HTTP_200_OK,
    summary="Keluar dari lingkaran",
)
async def leave_circle(
    circle_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> LeaveCircleResponse:
    circle_service = CircleService(db)
    await circle_service.leave_circle(circle_id, current_user.id)

    return LeaveCircleResponse()
