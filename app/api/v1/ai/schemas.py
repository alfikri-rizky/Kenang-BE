from typing import List, Optional

from pydantic import BaseModel, Field


class GetPromptsRequest(BaseModel):
    circle_type: str = Field(
        ..., description="Tipe lingkaran (keluarga, pasangan, sahabat, dll)"
    )
    category: Optional[str] = Field(None, description="Kategori prompts (opsional)")
    count: int = Field(3, ge=1, le=10, description="Jumlah prompts yang diinginkan")
    randomize: bool = Field(True, description="Acak prompts atau tidak")


class PromptsResponse(BaseModel):
    prompts: List[str] = Field(..., description="Daftar prompts")
    circle_type: str = Field(..., description="Tipe lingkaran")
    category: Optional[str] = Field(None, description="Kategori jika diminta")


class EnhanceStoryRequest(BaseModel):
    transcript: str = Field(
        ..., min_length=10, description="Transkrip cerita yang akan disempurnakan"
    )
    circle_type: str = Field(..., description="Tipe lingkaran untuk konteks")
    context: Optional[str] = Field(
        None, max_length=500, description="Konteks tambahan (opsional)"
    )


class EnhanceStoryResponse(BaseModel):
    enhanced_text: str = Field(..., description="Transkrip yang telah disempurnakan")
    improvements: List[str] = Field(..., description="Daftar perbaikan yang dilakukan")
    tone: str = Field(..., description="Nada/emosi cerita")
    original_length: int = Field(..., description="Panjang teks asli")
    enhanced_length: int = Field(..., description="Panjang teks yang disempurnakan")


class GenerateFollowUpRequest(BaseModel):
    transcript: str = Field(..., min_length=10, description="Transkrip cerita")
    circle_type: str = Field(..., description="Tipe lingkaran untuk konteks")
    count: int = Field(3, ge=1, le=5, description="Jumlah pertanyaan lanjutan")


class FollowUpQuestionsResponse(BaseModel):
    questions: List[str] = Field(..., description="Daftar pertanyaan lanjutan")
    circle_type: str = Field(..., description="Tipe lingkaran")


class SuggestTitleRequest(BaseModel):
    transcript: str = Field(..., min_length=10, description="Transkrip cerita")
    max_length: int = Field(60, ge=20, le=100, description="Panjang maksimal judul")


class SuggestTitleResponse(BaseModel):
    title: str = Field(..., description="Judul yang disarankan")
