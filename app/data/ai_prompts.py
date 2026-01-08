from typing import Dict, List

AI_PROMPTS: Dict[str, Dict[str, List[str]]] = {
    "keluarga": {
        "general": [
            "Siapa saja yang ada di foto ini?",
            "Di mana foto ini diambil?",
            "Kapan kira-kira foto ini diambil?",
        ],
        "childhood": [
            "Ceritakan tentang rumah masa kecil Anda",
            "Apa permainan favorit Anda waktu kecil?",
            "Siapa teman bermain Anda waktu kecil?",
        ],
        "family_history": [
            "Bagaimana kakek-nenek Anda bertemu?",
            "Apa tradisi keluarga yang paling Anda sukai?",
            "Ceritakan tentang leluhur keluarga",
        ],
        "wisdom": [
            "Apa pelajaran hidup terpenting yang Anda pelajari?",
            "Apa harapan Anda untuk cucu-cucu?",
            "Apa artinya keluarga bagi Anda?",
        ],
    },
    "pasangan": {
        "beginning": [
            "Kapan pertama kali kalian bertemu?",
            "Apa kesan pertama kamu tentang pasanganmu?",
            "Ceritakan tentang kencan pertama kalian",
        ],
        "journey": [
            "Momen apa yang membuat kamu jatuh cinta?",
            "Tantangan apa yang pernah kalian hadapi bersama?",
            "Liburan paling berkesan bersama pasangan?",
        ],
        "milestones": [
            "Ceritakan tentang hari pernikahan kalian",
            "Kapan kamu tahu dia 'yang satu'?",
            "Apa momen paling romantis dalam hubungan ini?",
        ],
        "reflection": [
            "Apa yang kamu sukai dari pasanganmu?",
            "Apa rahasia hubungan kalian?",
            "Apa harapanmu untuk masa depan bersama?",
        ],
    },
    "sahabat": {
        "beginning": [
            "Bagaimana kalian pertama kali bertemu?",
            "Apa kesan pertama tentang sahabatmu ini?",
            "Kapan kalian mulai dekat?",
        ],
        "memories": [
            "Momen paling gila yang pernah kalian alami bersama?",
            "Ceritakan liburan atau trip bersama yang berkesan",
            "Apa kejadian lucu yang selalu kalian ingat?",
        ],
        "bond": [
            "Kenapa persahabatan ini spesial bagi kamu?",
            "Apa yang sudah kalian lewati bersama?",
            "Bagaimana sahabatmu ini mendukungmu?",
        ],
        "reflection": [
            "Apa yang kamu kagumi dari sahabatmu?",
            "Apa pelajaran dari persahabatan ini?",
            "Apa harapanmu untuk persahabatan kalian?",
        ],
    },
    "rekan_kerja": {
        "work_memories": [
            "Ceritakan proyek paling berkesan yang kalian kerjakan",
            "Apa tantangan terbesar yang pernah tim hadapi?",
            "Momen kemenangan apa yang masih diingat?",
        ],
        "culture": [
            "Bagaimana budaya kerja di tim/perusahaan ini?",
            "Tradisi atau ritual tim yang unik?",
            "Apa yang membuat tim ini spesial?",
        ],
        "people": [
            "Siapa mentor yang paling berpengaruh?",
            "Ceritakan tentang rekan kerja favoritmu",
            "Apa pelajaran terbesar dari bos/manager?",
        ],
        "reflection": [
            "Apa pencapaian yang paling membanggakan?",
            "Kalau ada satu hal yang diingat tentang tim ini, apa itu?",
            "Apa nasihat untuk orang yang baru bergabung?",
        ],
    },
    "komunitas": {
        "community": [
            "Apa yang membuat komunitas ini spesial?",
            "Bagaimana komunitas ini dimulai?",
            "Momen paling berkesan bersama komunitas?",
        ],
        "impact": [
            "Apa dampak komunitas ini bagi hidupmu?",
            "Apa yang sudah komunitas ini capai bersama?",
            "Siapa sosok penting dalam komunitas ini?",
        ],
        "memories": [
            "Ceritakan acara/event yang paling memorable",
            "Tradisi komunitas yang unik?",
            "Momen lucu atau mengharukan bersama?",
        ],
    },
    "mentor": {
        "guidance": [
            "Pelajaran terpenting apa yang kamu dapat dari mentor?",
            "Bagaimana mentormu membentuk karirmu?",
            "Nasihat apa yang selalu kamu ingat?",
        ],
        "relationship": [
            "Bagaimana kamu bertemu dengan mentormu?",
            "Apa momen breakthrough dalam hubungan mentorship ini?",
            "Apa yang kamu kagumi dari mentormu?",
        ],
    },
    "pribadi": {
        "daily": [
            "Apa yang kamu rasakan hari ini?",
            "Apa yang kamu syukuri hari ini?",
            "Apa yang ingin kamu ingat tentang hari ini?",
        ],
        "reflection": [
            "Apa pencapaian yang kamu banggakan?",
            "Apa impian yang ingin kamu capai?",
            "Apa pelajaran hidup terbesarmu?",
        ],
        "future": [
            "Apa harapanmu untuk 5 tahun ke depan?",
            "Kalau bisa bicara ke diri sendiri 10 tahun lalu, apa yang akan kamu katakan?",
            "Apa yang ingin kamu tinggalkan sebagai legacy?",
        ],
    },
}


def get_prompts_by_circle_type(circle_type: str) -> Dict[str, List[str]]:
    return AI_PROMPTS.get(circle_type, AI_PROMPTS["pribadi"])


def get_all_prompts_flat(circle_type: str) -> List[str]:
    prompts = get_prompts_by_circle_type(circle_type)
    return [prompt for category_prompts in prompts.values() for prompt in category_prompts]


def get_random_prompts(circle_type: str, count: int = 3) -> List[str]:
    import random
    
    all_prompts = get_all_prompts_flat(circle_type)
    return random.sample(all_prompts, min(count, len(all_prompts)))
