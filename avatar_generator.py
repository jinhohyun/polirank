"""
PoliRank - 국회의원 고품질 만화풍/캐리커쳐 (Cartoon/Caricature) SVG 아바타 정밀 생성기
32인 의원별 고유 인상(헤어스타일, 눈매, 안경, 연륜 주름, 표정, 정당 패션) 정밀 반영
"""
import hashlib
from typing import Dict, Any

MEMBER_CARICATURE_PROFILES = {
    "이재명": {
        "gender": "male",
        "hair_type": "silver_tinted_part",
        "hair_color": "#3B4252",
        "skin_tone": "#FCE5D8",
        "glasses": True,
        "glasses_frame": "#4C566A",
        "expression": "charismatic_leader",
        "tie_color": "#004EA2",
        "suit_color": "#0F172A",
        "special_feature": "silver_temple"
    },
    "조국": {
        "gender": "male",
        "hair_type": "sharp_dandy",
        "hair_color": "#1A1A1A",
        "skin_tone": "#FDF0E6",
        "glasses": False,
        "expression": "intellectual_calm",
        "tie_color": "#002B49",
        "suit_color": "#002B49",
        "special_feature": "sharp_jawline"
    },
    "이준석": {
        "gender": "male",
        "hair_type": "youth_two_eight_part",
        "hair_color": "#2A2421",
        "skin_tone": "#FBEAE0",
        "glasses": False,
        "expression": "smart_witty_smirk",
        "tie_color": "#FF7920",
        "suit_color": "#1E293B",
        "special_feature": "sharp_young_eye"
    },
    "나경원": {
        "gender": "female",
        "hair_type": "elegant_volume_bob",
        "hair_color": "#3A281E",
        "skin_tone": "#FFF4ED",
        "glasses": False,
        "expression": "confident_smile",
        "tie_color": "#E61E2B",
        "suit_color": "#E61E2B",
        "suit_type": "jacket_scarf",
        "special_feature": "pearl_earring"
    },
    "박찬대": {
        "gender": "male",
        "hair_type": "neat_side_part",
        "hair_color": "#2C3437",
        "skin_tone": "#FCE5D8",
        "glasses": True,
        "glasses_frame": "#4A5568",
        "expression": "warm_gentle_smile",
        "tie_color": "#004EA2",
        "suit_color": "#1E293B",
        "special_feature": "warm_eye_smile"
    },
    "추경호": {
        "gender": "male",
        "hair_type": "classic_part",
        "hair_color": "#4A4E51",
        "skin_tone": "#FDE6D2",
        "glasses": True,
        "glasses_frame": "#B8860B",
        "expression": "thoughtful_bureaucrat",
        "tie_color": "#E61E2B",
        "suit_color": "#1E293B",
        "special_feature": "gold_rim"
    },
    "정청래": {
        "gender": "male",
        "hair_type": "dynamic_crop",
        "hair_color": "#1C1C1E",
        "skin_tone": "#F6D8C8",
        "glasses": True,
        "glasses_frame": "#111827",
        "expression": "fierce_determined_grin",
        "tie_color": "#004EA2",
        "suit_color": "#0F172A",
        "special_feature": "thick_horn_rim"
    },
    "용혜인": {
        "gender": "female",
        "hair_type": "modern_teal_bob",
        "hair_color": "#1C1C1E",
        "skin_tone": "#FFF0E6",
        "glasses": False,
        "expression": "passionate_bright",
        "tie_color": "#00D2C4",
        "suit_color": "#00D2C4",
        "suit_type": "modern_teal",
        "special_feature": "sharp_clear_eyes"
    },
    "안철수": {
        "gender": "male",
        "hair_type": "forehead_clean",
        "hair_color": "#3A3D40",
        "skin_tone": "#FDEBD0",
        "glasses": False,
        "expression": "gentle_scholar",
        "tie_color": "#E61E2B",
        "suit_color": "#1E293B",
        "special_feature": "scholar_smile"
    },
    "박지원": {
        "gender": "male",
        "hair_type": "silver_elder",
        "hair_color": "#CBD5E1",
        "skin_tone": "#FBE0CF",
        "glasses": True,
        "glasses_frame": "#1F2937",
        "expression": "veteran_wrinkle_smile",
        "tie_color": "#004EA2",
        "suit_color": "#1E293B",
        "special_feature": "wise_wrinkles"
    },
    "배현진": {
        "gender": "female",
        "hair_type": "anchor_bob",
        "hair_color": "#281D14",
        "skin_tone": "#FFF4ED",
        "glasses": False,
        "expression": "sharp_elegant",
        "tie_color": "#E61E2B",
        "suit_color": "#E61E2B",
        "suit_type": "jacket_scarf",
        "special_feature": "anchor_eyes"
    },
    "고민정": {
        "gender": "female",
        "hair_type": "soft_medium_wave",
        "hair_color": "#3B261D",
        "skin_tone": "#FFF2E8",
        "glasses": False,
        "expression": "warm_smile",
        "tie_color": "#004EA2",
        "suit_color": "#004EA2",
        "suit_type": "jacket_scarf",
        "special_feature": "soft_smile"
    },
    "천하람": {
        "gender": "male",
        "hair_type": "round_neat",
        "hair_color": "#2A2A2A",
        "skin_tone": "#FCEAE0",
        "glasses": True,
        "glasses_frame": "#334155",
        "expression": "friendly_smile",
        "tie_color": "#FF7920",
        "suit_color": "#1E293B",
        "special_feature": "round_cheeks"
    },
    "우원식": {
        "gender": "male",
        "hair_type": "silver_dignified",
        "hair_color": "#94A3B8",
        "skin_tone": "#F9E4D4",
        "glasses": True,
        "glasses_frame": "#475569",
        "expression": "dignified_speaker",
        "tie_color": "#475569",
        "suit_color": "#0F172A",
        "special_feature": "speaker_presence"
    },
    "서영교": {
        "gender": "female",
        "hair_type": "energetic_short_perm",
        "hair_color": "#2D241E",
        "skin_tone": "#FEEFE6",
        "glasses": False,
        "expression": "resolute_passionate",
        "tie_color": "#004EA2",
        "suit_color": "#004EA2",
        "suit_type": "jacket_scarf",
        "special_feature": "fighter_spirit"
    },
    "김재섭": {
        "gender": "male",
        "hair_type": "youth_volume",
        "hair_color": "#23272A",
        "skin_tone": "#FCEADE",
        "glasses": False,
        "expression": "confident_youth",
        "tie_color": "#E61E2B",
        "suit_color": "#1E293B",
        "special_feature": "youth_jaw"
    },
    "윤건영": {
        "gender": "male",
        "hair_type": "neat_side_part",
        "hair_color": "#333A42",
        "skin_tone": "#FCE5D8",
        "glasses": True,
        "glasses_frame": "#1E293B",
        "expression": "thoughtful_strategist",
        "tie_color": "#004EA2",
        "suit_color": "#1E293B",
        "special_feature": "strategist_look"
    },
    "이소영": {
        "gender": "female",
        "hair_type": "smart_lob",
        "hair_color": "#241F1C",
        "skin_tone": "#FFF2E8",
        "glasses": False,
        "expression": "bright_intellect",
        "tie_color": "#004EA2",
        "suit_color": "#004EA2",
        "suit_type": "jacket_scarf",
        "special_feature": "climate_expert"
    }
}

def generate_caricature_svg(name: str, party: str, party_color: str, size: int = 140) -> str:
    """
    의원의 고유 인상과 특색(눈가주름, 안경테 두께, 2:8 헤어, 표정 등)을 정교하게 렌더링한 SVG 반환
    """
    profile = MEMBER_CARICATURE_PROFILES.get(name)
    if not profile:
        h = int(hashlib.md5(name.encode('utf-8')).hexdigest()[:8], 16)
        is_female = (h % 3 == 0)
        profile = {
            "gender": "female" if is_female else "male",
            "hair_type": "soft_medium_wave" if is_female else "neat_side_part",
            "hair_color": "#2C3437" if (h % 2 == 0) else "#4A525A",
            "skin_tone": "#FFF0E5" if is_female else "#FCE5D8",
            "glasses": ((h % 4) == 0),
            "glasses_frame": "#334155",
            "expression": "warm_gentle_smile" if (h % 2 == 0) else "confident_smile",
            "tie_color": party_color,
            "suit_color": "#1E293B",
            "suit_type": "jacket_scarf" if is_female else "standard_suit",
            "special_feature": "standard"
        }

    bg_grad_id = f"grad_{abs(hash(name)) % 10000}"
    hair_type = profile.get("hair_type", "neat_side_part")
    hair_color = profile.get("hair_color", "#2A2D34")
    skin_tone = profile.get("skin_tone", "#FCE5D8")
    glasses = profile.get("glasses", False)
    glasses_frame = profile.get("glasses_frame", "#333333")
    tie_color = profile.get("tie_color", party_color)
    suit_color = profile.get("suit_color", "#1E293B")
    expression = profile.get("expression", "warm_gentle_smile")
    special = profile.get("special_feature", "")
    is_female = (profile.get("gender") == "female")

    # 1. 헤어스타일 드로잉
    if hair_type == "youth_two_eight_part":
        # 이준석 2:8 가르마 & 청년 볼륨
        hair_svg = f"""
        <path d="M 28 44 C 26 22 46 10 68 10 C 92 10 112 20 110 44 C 105 28 86 18 68 18 C 50 18 36 28 28 44 Z" fill="{hair_color}" />
        <!-- 2:8 Sharp Part Line -->
        <path d="M 38 18 C 50 14 62 13 80 18 C 96 22 108 30 110 42 C 102 30 88 24 74 23 C 58 22 46 26 38 18 Z" fill="#4B382A" opacity="0.9"/>
        <path d="M 27 44 C 25 54 28 64 30 68 C 31 58 30 48 33 44 Z" fill="{hair_color}" />
        <path d="M 111 44 C 113 54 110 64 108 68 C 107 58 108 48 105 44 Z" fill="{hair_color}" />
        """
    elif hair_type == "silver_elder":
        # 박지원 연륜 백발
        hair_svg = f"""
        <path d="M 30 46 C 28 20 50 12 70 12 C 90 12 112 20 110 46 C 102 28 86 18 70 18 C 52 18 38 28 30 46 Z" fill="{hair_color}" />
        <path d="M 32 38 C 44 24 66 18 88 22 C 98 24 106 30 108 40 C 98 30 86 24 72 23 C 54 22 40 30 32 38 Z" fill="#F1F5F9" opacity="0.95"/>
        <path d="M 28 46 C 26 56 29 66 31 70 C 31 60 30 50 33 46 Z" fill="{hair_color}" />
        <path d="M 112 46 C 114 56 111 66 109 70 C 109 60 110 50 107 46 Z" fill="{hair_color}" />
        """
    elif hair_type == "sharp_dandy":
        # 조국 샤프 댄디
        hair_svg = f"""
        <path d="M 28 44 C 28 20 50 11 70 11 C 92 11 112 20 112 44 C 108 26 88 18 70 18 C 50 18 34 28 28 44 Z" fill="{hair_color}" />
        <path d="M 30 38 C 45 22 72 18 96 26 C 104 30 110 36 112 44 C 104 32 90 26 75 25 C 55 24 40 32 30 38 Z" fill="{hair_color}" />
        <path d="M 27 44 C 25 54 27 65 29 68 C 30 58 29 48 32 44 Z" fill="{hair_color}" />
        <path d="M 113 44 C 115 54 113 65 111 68 C 110 58 111 48 108 44 Z" fill="{hair_color}" />
        """
    elif is_female:
        # 나경원/배현진/고민정/용혜인/서영교 등 여성 헤어
        hair_svg = f"""
        <path d="M 24 46 C 22 18 46 10 70 10 C 94 10 118 18 116 46 C 118 68 114 88 105 96 C 105 82 107 65 105 50 C 98 28 84 18 70 18 C 54 18 40 28 35 50 C 33 65 35 82 35 96 C 26 88 22 68 24 46 Z" fill="{hair_color}" />
        <path d="M 30 40 C 44 24 66 20 88 22 C 100 24 108 32 112 42 C 102 32 88 28 72 28 C 54 28 42 34 30 40 Z" fill="{hair_color}" opacity="0.9"/>
        """
    else:
        # 이재명/박찬대/정청래 등
        hair_svg = f"""
        <path d="M 30 44 C 28 22 48 12 70 12 C 92 12 112 22 110 44 C 104 28 88 18 70 18 C 50 18 36 28 30 44 Z" fill="{hair_color}" />
        <path d="M 34 38 C 48 24 70 20 90 25 C 100 28 108 35 110 44 C 100 34 88 28 72 28 C 54 28 42 34 34 38 Z" fill="{hair_color}" opacity="0.9"/>
        """

    # 2. 안경 스타일링
    glasses_svg = ""
    if glasses:
        if glasses_frame == "#111827":  # 정청래 굵은 뿔테
            glasses_svg = f"""
            <g stroke="{glasses_frame}" stroke-width="3.5" fill="none" opacity="0.98">
                <rect x="42" y="50" width="24" height="17" rx="3" fill="rgba(255,255,255,0.18)"/>
                <rect x="74" y="50" width="24" height="17" rx="3" fill="rgba(255,255,255,0.18)"/>
                <path d="M 66 57 L 74 57" stroke-width="4"/>
                <path d="M 36 55 L 42 56" />
                <path d="M 98 56 L 104 55" />
            </g>
            """
        elif glasses_frame == "#B8860B":  # 추경호 금테
            glasses_svg = f"""
            <g stroke="#D4AF37" stroke-width="2" fill="none" opacity="0.95">
                <rect x="43" y="51" width="23" height="16" rx="4" fill="rgba(255,255,255,0.2)"/>
                <rect x="74" y="51" width="23" height="16" rx="4" fill="rgba(255,255,255,0.2)"/>
                <path d="M 66 57 L 74 57" />
                <path d="M 37 55 L 43 56" />
                <path d="M 97 56 L 103 55" />
            </g>
            """
        else:  # 일반 세련된 테
            glasses_svg = f"""
            <g stroke="{glasses_frame}" stroke-width="2.2" fill="none" opacity="0.95">
                <rect x="43" y="51" width="23" height="16" rx="4" fill="rgba(255,255,255,0.2)"/>
                <rect x="74" y="51" width="23" height="16" rx="4" fill="rgba(255,255,255,0.2)"/>
                <path d="M 66 57 L 74 57" />
                <path d="M 37 55 L 43 56" />
                <path d="M 97 56 L 103 55" />
            </g>
            """

    # 3. 눈가 주름 & 연륜 표현 (박지원 등)
    wrinkle_svg = ""
    if special == "wise_wrinkles":
        wrinkle_svg = """
        <path d="M 38 56 Q 42 58 40 62" stroke="#A07258" stroke-width="1.2" fill="none" opacity="0.7"/>
        <path d="M 102 56 Q 98 58 100 62" stroke="#A07258" stroke-width="1.2" fill="none" opacity="0.7"/>
        <path d="M 62 70 Q 70 72 78 70" stroke="#A07258" stroke-width="1" fill="none" opacity="0.5"/>
        <path d="M 52 46 Q 70 44 88 46" stroke="#A07258" stroke-width="1" fill="none" opacity="0.6"/>
        """

    # 4. 표정 (눈 & 눈썹 & 입)
    if expression == "smart_witty_smirk":  # 이준석 스마트 미소
        mouth_svg = '<path d="M 62 76 Q 73 74 81 72" stroke="#9B2C2C" stroke-width="2.5" fill="none" stroke-linecap="round" />'
        eyes_svg = """
        <ellipse cx="54" cy="58" rx="3.5" ry="3.8" fill="#1A202C" />
        <circle cx="55.5" cy="56.5" r="1.1" fill="#FFFFFF" />
        <ellipse cx="86" cy="58" rx="3.5" ry="3.8" fill="#1A202C" />
        <circle cx="87.5" cy="56.5" r="1.1" fill="#FFFFFF" />
        <path d="M 47 49 Q 54 46 61 50" stroke="#2D3748" stroke-width="2.5" fill="none" stroke-linecap="round" />
        <path d="M 79 49 Q 86 45 93 47" stroke="#2D3748" stroke-width="2.8" fill="none" stroke-linecap="round" />
        """
    elif expression == "fierce_determined_grin":  # 정청래 강한 눈매
        mouth_svg = '<path d="M 60 76 Q 70 82 80 76" stroke="#8B0000" stroke-width="3" fill="none" stroke-linecap="round" />'
        eyes_svg = """
        <ellipse cx="54" cy="58" rx="3.6" ry="3.6" fill="#0F172A" />
        <circle cx="55.5" cy="56.5" r="1" fill="#FFFFFF" />
        <ellipse cx="86" cy="58" rx="3.6" ry="3.6" fill="#0F172A" />
        <circle cx="87.5" cy="56.5" r="1" fill="#FFFFFF" />
        <path d="M 46 47 L 62 51" stroke="#0F172A" stroke-width="3.2" fill="none" stroke-linecap="round" />
        <path d="M 94 47 L 78 51" stroke="#0F172A" stroke-width="3.2" fill="none" stroke-linecap="round" />
        """
    elif expression == "charismatic_leader":  # 이재명 카리스마
        mouth_svg = '<path d="M 63 76 Q 70 78 77 76" stroke="#9B2C2C" stroke-width="2.5" fill="none" stroke-linecap="round" />'
        eyes_svg = """
        <ellipse cx="54" cy="58" rx="3.5" ry="4" fill="#1A202C" />
        <circle cx="55.5" cy="56.5" r="1.2" fill="#FFFFFF" />
        <ellipse cx="86" cy="58" rx="3.5" ry="4" fill="#1A202C" />
        <circle cx="87.5" cy="56.5" r="1.2" fill="#FFFFFF" />
        <path d="M 47 48 Q 55 46 61 50" stroke="#1E293B" stroke-width="2.8" fill="none" stroke-linecap="round" />
        <path d="M 79 50 Q 85 46 93 48" stroke="#1E293B" stroke-width="2.8" fill="none" stroke-linecap="round" />
        """
    else:  # 기본 온화/단정한 미소
        mouth_svg = '<path d="M 62 76 Q 70 82 78 76" stroke="#9B2C2C" stroke-width="2.5" fill="none" stroke-linecap="round" />'
        eyes_svg = """
        <ellipse cx="54" cy="58" rx="3.5" ry="4" fill="#1A202C" />
        <circle cx="55.5" cy="56.5" r="1.2" fill="#FFFFFF" />
        <ellipse cx="86" cy="58" rx="3.5" ry="4" fill="#1A202C" />
        <circle cx="87.5" cy="56.5" r="1.2" fill="#FFFFFF" />
        <path d="M 48 50 Q 55 47 61 50" stroke="#4A5568" stroke-width="2.5" fill="none" stroke-linecap="round" />
        <path d="M 79 50 Q 85 47 92 50" stroke="#4A5568" stroke-width="2.5" fill="none" stroke-linecap="round" />
        """

    # 5. 의상 & 국회 뱃지
    if is_female:
        outfit_svg = f"""
        <path d="M 34 110 C 34 94 48 90 70 90 C 92 90 106 94 106 110 L 118 140 L 22 140 Z" fill="{suit_color}" />
        <polygon points="70,90 58,118 82,118" fill="#FFFFFF" />
        <polygon points="70,98 62,122 78,122" fill="{party_color}" />
        <circle cx="48" cy="106" r="4.5" fill="#FFD700" stroke="#B7791F" stroke-width="1"/>
        <text x="48" y="108.5" font-size="4" font-weight="bold" fill="#744210" text-anchor="middle">國</text>
        """
    else:
        outfit_svg = f"""
        <path d="M 32 110 C 32 94 46 90 70 90 C 94 90 108 94 108 110 L 122 140 L 18 140 Z" fill="{suit_color}" />
        <polygon points="70,92 56,112 84,112" fill="#FFFFFF" />
        <polygon points="67,100 73,100 76,138 70,140 64,138" fill="{tie_color}" />
        <polygon points="66,97 74,97 72,104 68,104" fill="{tie_color}" />
        <circle cx="46" cy="106" r="4.5" fill="#FFD700" stroke="#B7791F" stroke-width="1"/>
        <text x="46" y="108.5" font-size="4" font-weight="bold" fill="#744210" text-anchor="middle">國</text>
        """

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 140 140" width="{size}" height="{size}">
    <defs>
        <linearGradient id="{bg_grad_id}" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stop-color="{party_color}" stop-opacity="0.22" />
            <stop offset="100%" stop-color="{party_color}" stop-opacity="0.05" />
        </linearGradient>
    </defs>
    <circle cx="70" cy="70" r="66" fill="url(#{bg_grad_id})" stroke="{party_color}" stroke-width="2.5" stroke-opacity="0.45" />
    <path d="M 58 80 L 58 96 C 58 98 82 98 82 96 L 82 80 Z" fill="{skin_tone}" />
    <path d="M 58 84 C 64 88 76 88 82 84 L 82 86 C 76 90 64 90 58 86 Z" fill="#E2C1A8" opacity="0.6"/>
    {outfit_svg}
    <ellipse cx="70" cy="62" rx="34" ry="32" fill="{skin_tone}" />
    <ellipse cx="36" cy="62" rx="4.5" ry="7" fill="{skin_tone}" />
    <ellipse cx="104" cy="62" rx="4.5" ry="7" fill="{skin_tone}" />
    {eyes_svg}
    <ellipse cx="46" cy="67" rx="5" ry="3" fill="#F56565" opacity="0.22" />
    <ellipse cx="94" cy="67" rx="5" ry="3" fill="#F56565" opacity="0.22" />
    <path d="M 70 60 L 68 67 L 72 67" stroke="#D69E2E" stroke-width="1.8" fill="none" stroke-linecap="round" stroke-linejoin="round" opacity="0.6"/>
    {mouth_svg}
    {wrinkle_svg}
    {glasses_svg}
    {hair_svg}
</svg>"""
    return svg
