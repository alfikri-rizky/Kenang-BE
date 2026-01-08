from typing import List, Optional

import structlog
from openai import AsyncOpenAI

from app.core.config import settings
from app.core.exceptions import BusinessException
from app.data.ai_prompts import get_random_prompts, get_prompts_by_circle_type

logger = structlog.get_logger(__name__)


class AIService:
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY) if settings.OPENAI_API_KEY else None

    def get_circle_prompts(
        self,
        circle_type: str,
        category: Optional[str] = None,
        count: int = 3,
        randomize: bool = True,
    ) -> List[str]:
        if randomize:
            return get_random_prompts(circle_type, count)
        
        prompts_dict = get_prompts_by_circle_type(circle_type)
        
        if category and category in prompts_dict:
            return prompts_dict[category][:count]
        
        all_prompts = []
        for category_prompts in prompts_dict.values():
            all_prompts.extend(category_prompts)
        
        return all_prompts[:count]

    async def enhance_story_transcript(
        self,
        transcript: str,
        circle_type: str,
        context: Optional[str] = None,
    ) -> dict:
        if not self.client:
            raise BusinessException(
                code="AI_NOT_CONFIGURED",
                message="Layanan AI tidak tersedia saat ini.",
            )

        try:
            circle_context = self._get_circle_context(circle_type)
            
            system_prompt = f"""Kamu adalah asisten AI yang membantu menyempurnakan cerita kenangan dalam Bahasa Indonesia.

Konteks: {circle_context}

Tugasmu:
1. Perbaiki tata bahasa dan ejaan jika ada kesalahan
2. Buat cerita lebih mengalir dan mudah dibaca
3. Pertahankan gaya bicara dan emosi asli
4. JANGAN menambah informasi yang tidak ada
5. JANGAN mengubah makna cerita

Kembalikan dalam format JSON:
{{
    "enhanced_text": "versi yang disempurnakan",
    "improvements": ["daftar perbaikan yang dilakukan"],
    "tone": "nada/emosi cerita (hangat/haru/lucu/dll)"
}}"""

            user_prompt = f"Transkrip asli:\n\n{transcript}"
            
            if context:
                user_prompt += f"\n\nKonteks tambahan: {context}"

            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.3,
            )

            import json
            result = json.loads(response.choices[0].message.content)

            logger.info(
                "story_enhanced",
                circle_type=circle_type,
                original_length=len(transcript),
                enhanced_length=len(result.get("enhanced_text", "")),
            )

            return result

        except Exception as e:
            logger.error(
                "story_enhancement_failed",
                circle_type=circle_type,
                error=str(e),
            )
            raise BusinessException(
                code="AI_ENHANCEMENT_FAILED",
                message="Gagal menyempurnakan cerita. Silakan coba lagi.",
            )

    async def generate_follow_up_questions(
        self,
        transcript: str,
        circle_type: str,
        count: int = 3,
    ) -> List[str]:
        if not self.client:
            raise BusinessException(
                code="AI_NOT_CONFIGURED",
                message="Layanan AI tidak tersedia saat ini.",
            )

        try:
            circle_context = self._get_circle_context(circle_type)
            
            system_prompt = f"""Kamu adalah pewawancara yang empati dan penuh perhatian dalam Bahasa Indonesia.

Konteks: {circle_context}

Tugasmu:
1. Baca cerita yang diceritakan pengguna
2. Buat {count} pertanyaan lanjutan yang mendorong mereka bercerita lebih dalam
3. Pertanyaan harus natural, hangat, dan sesuai konteks
4. Hindari pertanyaan yang sudah terjawab
5. Fokus pada emosi dan detail yang belum diungkap

Format: Return array JSON dengan {count} pertanyaan."""

            user_prompt = f"Cerita yang diceritakan:\n\n{transcript}\n\nBuatkan {count} pertanyaan lanjutan."

            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.7,
            )

            import json
            result = json.loads(response.choices[0].message.content)
            
            questions = result.get("questions", [])

            logger.info(
                "follow_up_questions_generated",
                circle_type=circle_type,
                count=len(questions),
            )

            return questions[:count]

        except Exception as e:
            logger.error(
                "follow_up_generation_failed",
                circle_type=circle_type,
                error=str(e),
            )
            raise BusinessException(
                code="AI_GENERATION_FAILED",
                message="Gagal membuat pertanyaan lanjutan. Silakan coba lagi.",
            )

    def _get_circle_context(self, circle_type: str) -> str:
        contexts = {
            "keluarga": "Ini adalah cerita keluarga. Fokus pada ikatan keluarga, tradisi, dan warisan.",
            "pasangan": "Ini adalah cerita pasangan/cinta. Fokus pada perjalanan hubungan, momen spesial, dan komitmen.",
            "sahabat": "Ini adalah cerita persahabatan. Fokus pada petualangan bersama, dukungan, dan kenangan indah.",
            "rekan_kerja": "Ini adalah cerita profesional. Fokus pada kolaborasi, pencapaian, dan pelajaran karir.",
            "komunitas": "Ini adalah cerita komunitas. Fokus pada kebersamaan, dampak sosial, dan tujuan bersama.",
            "mentor": "Ini adalah cerita mentorship. Fokus pada pembelajaran, bimbingan, dan perkembangan pribadi.",
            "pribadi": "Ini adalah cerita personal/refleksi diri. Fokus pada pertumbuhan pribadi, perasaan, dan refleksi.",
        }
        return contexts.get(circle_type, contexts["pribadi"])

    async def suggest_story_title(
        self,
        transcript: str,
        max_length: int = 60,
    ) -> str:
        if not self.client:
            return transcript[:max_length]

        try:
            system_prompt = """Kamu membuat judul singkat dan menarik untuk cerita dalam Bahasa Indonesia.

Aturan:
1. Maksimal 60 karakter
2. Tangkap inti cerita
3. Emosional tapi tidak berlebihan
4. Natural seperti judul buku harian

Contoh bagus:
- "Hari Pertama di Jakarta"
- "Pernikahan Mama dan Papa"
- "Liburan ke Bali Bersama Keluarga"

Return JSON: {"title": "judul cerita"}"""

            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Cerita:\n\n{transcript}"},
                ],
                response_format={"type": "json_object"},
                temperature=0.5,
            )

            import json
            result = json.loads(response.choices[0].message.content)
            title = result.get("title", transcript[:max_length])

            return title[:max_length]

        except Exception as e:
            logger.error("title_suggestion_failed", error=str(e))
            return transcript[:max_length]
