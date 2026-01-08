from fastapi import APIRouter, Depends, status

from app.api.deps import get_current_user
from app.api.v1.ai.schemas import (
    EnhanceStoryRequest,
    EnhanceStoryResponse,
    FollowUpQuestionsResponse,
    GenerateFollowUpRequest,
    GetPromptsRequest,
    PromptsResponse,
    SuggestTitleRequest,
    SuggestTitleResponse,
)
from app.db.models import User
from app.services.ai_service import AIService

router = APIRouter()


@router.post(
    "/prompts",
    response_model=PromptsResponse,
    status_code=status.HTTP_200_OK,
    summary="Dapatkan prompts AI untuk lingkaran",
    description="Mendapatkan daftar prompts kontekstual berdasarkan tipe lingkaran.",
)
async def get_prompts(
    request: GetPromptsRequest,
    current_user: User = Depends(get_current_user),
) -> PromptsResponse:
    ai_service = AIService()

    prompts = ai_service.get_circle_prompts(
        circle_type=request.circle_type,
        category=request.category,
        count=request.count,
        randomize=request.randomize,
    )

    return PromptsResponse(
        prompts=prompts,
        circle_type=request.circle_type,
        category=request.category,
    )


@router.post(
    "/enhance",
    response_model=EnhanceStoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Sempurnakan transkrip cerita",
    description="Menggunakan AI untuk menyempurnakan tata bahasa dan keterbacaan transkrip.",
)
async def enhance_story(
    request: EnhanceStoryRequest,
    current_user: User = Depends(get_current_user),
) -> EnhanceStoryResponse:
    ai_service = AIService()

    result = await ai_service.enhance_story_transcript(
        transcript=request.transcript,
        circle_type=request.circle_type,
        context=request.context,
    )

    return EnhanceStoryResponse(
        enhanced_text=result["enhanced_text"],
        improvements=result.get("improvements", []),
        tone=result.get("tone", "netral"),
        original_length=len(request.transcript),
        enhanced_length=len(result["enhanced_text"]),
    )


@router.post(
    "/follow-up",
    response_model=FollowUpQuestionsResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate pertanyaan lanjutan",
    description="Menggunakan AI untuk membuat pertanyaan lanjutan berdasarkan cerita.",
)
async def generate_follow_up_questions(
    request: GenerateFollowUpRequest,
    current_user: User = Depends(get_current_user),
) -> FollowUpQuestionsResponse:
    ai_service = AIService()

    questions = await ai_service.generate_follow_up_questions(
        transcript=request.transcript,
        circle_type=request.circle_type,
        count=request.count,
    )

    return FollowUpQuestionsResponse(
        questions=questions,
        circle_type=request.circle_type,
    )


@router.post(
    "/suggest-title",
    response_model=SuggestTitleResponse,
    status_code=status.HTTP_200_OK,
    summary="Sarankan judul cerita",
    description="Menggunakan AI untuk menyarankan judul yang menarik untuk cerita.",
)
async def suggest_title(
    request: SuggestTitleRequest,
    current_user: User = Depends(get_current_user),
) -> SuggestTitleResponse:
    ai_service = AIService()

    title = await ai_service.suggest_story_title(
        transcript=request.transcript,
        max_length=request.max_length,
    )

    return SuggestTitleResponse(title=title)
