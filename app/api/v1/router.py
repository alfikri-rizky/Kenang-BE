from fastapi import APIRouter

from app.api.v1.ai.router import router as ai_router
from app.api.v1.auth.router import router as auth_router
from app.api.v1.circles.router import router as circles_router
from app.api.v1.photos.router import router as photos_router
from app.api.v1.public.router import router as public_router
from app.api.v1.stories.router import router as stories_router
from app.api.v1.subscriptions.router import router as subscriptions_router
from app.api.v1.users.router import router as users_router

api_router = APIRouter()

api_router.include_router(auth_router, prefix="/auth", tags=["Authentication"])
api_router.include_router(users_router, prefix="/users", tags=["Users"])
api_router.include_router(circles_router, prefix="/circles", tags=["Circles"])
api_router.include_router(photos_router, tags=["Photos"])
api_router.include_router(stories_router, tags=["Stories"])
api_router.include_router(ai_router, prefix="/ai", tags=["AI"])
api_router.include_router(
    subscriptions_router, prefix="/subscriptions", tags=["Subscriptions"]
)
api_router.include_router(public_router, prefix="/public", tags=["Public"])
