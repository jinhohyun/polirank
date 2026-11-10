"""
PoliRank - 국회의원 고품질 만화풍/캐리커쳐 (Cartoon/Caricature) SVG 아바타 정밀 생성기 (299인 자동 대응)
성별(gender), 나이대(age), 정당 컬러(tie_color), 직책(chair_pin), 고유 인상을 정밀 반영
"""
import hashlib
from typing import Dict, Any, Optional

MEMBER_CARICATURE_PROFILES: Dict[str, Dict[str, Any]] = {
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
        "special_feature": "silver_temple",
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
        "special_feature": "sharp_jawline",
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
        "special_feature": "sharp_young_eye",
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
        "special_feature": "pearl_earring",
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
        "special_feature": "warm_eye_smile",
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
        "special_feature": "gold_rim",
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
        "special_feature": "thick_horn_rim",
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
        "special_feature": "sharp_clear_eyes",
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
        "special_feature": "scholar_smile",
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
        "special_feature": "wise_wrinkles",
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
        "special_feature": "anchor_eyes",
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
        "special_feature": "soft_smile",
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
        "special_feature": "round_cheeks",
    },
    "우원식": {
        "gender": "male",
        "hair_type": "silver_dignified",
        "hair_color": "#94A3B8",
        "skin_tone": "#F9E4D4",
        "glasses": True,
        "glasses_frame": "#475569",
        "expression": "dignified_speaker",
        "tie_color": "#004EA2",
        "suit_color": "#0F172A",
        "special_feature": "wise_wrinkles",
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
        "special_feature": "fighter_spirit",
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
        "special_feature": "youth_jaw",
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
        "special_feature": "strategist_look",
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
        "special_feature": "climate_expert",
    },
}

MALE_HAIR_STYLES = [
    "neat_side_part",
    "youth_two_eight_part",
    "sharp_dandy",
    "forehead_clean",
    "dynamic_crop",
    "classic_part",
]

FEMALE_HAIR_STYLES = [
    "soft_medium_wave",
    "elegant_volume_bob",
    "anchor_bob",
    "smart_lob",
    "energetic_short_perm",
]

SKIN_TONES_MALE = ["#FCE5D8", "#F9DFCE", "#FDE6D2", "#F7DAC8"]
SKIN_TONES_FEMALE = ["#FFF2E8", "#FFF0E6", "#FEEFE6", "#FFF4ED"]
GLASSES_FRAMES = ["#1E293B", "#334155", "#4A5568", "#B8860B", "#111827"]
EXPRESSIONS = [
    "warm_gentle_smile",
    "confident_smile",
    "intellectual_calm",
    "bright_intellect",
    "charismatic_leader",
]


def _build_dynamic_profile(
    name: str,
    party_color: str,
    gender: Optional[str] = None,
    age: Optional[int] = None,
) -> Dict[str, Any]:
    """299명 전원에 대해 성별·나이대·정당컬러·해시 기반 개성 있는 캐리커쳐 프로필 생성"""
    seed_str = f"{name}_{gender or ''}_{age or ''}"
    digest = hashlib.md5(seed_str.encode("utf-8")).hexdigest()
    h1 = int(digest[0:8], 16)
    h2 = int(digest[8:16], 16)
    h3 = int(digest[16:24], 16)

    resolved_gender = gender if gender in ("male", "female") else ("female" if (h1 % 4 == 0) else "male")
    is_female = resolved_gender == "female"
    resolved_age = age if age is not None else (40 + (h2 % 30))

    # 나이대별 헤어 컬러 & 연륜 주름
    if resolved_age >= 66:
        hair_color = "#CBD5E1" if (h3 % 2 == 0) else "#94A3B8"
        special = "wise_wrinkles"
    elif resolved_age >= 58:
        hair_color = "#4A525A" if (h3 % 2 == 0) else "#64748B"
        special = "wise_wrinkles" if (h2 % 2 == 0) else "standard"
    elif resolved_age < 45:
        hair_color = "#1A1A1A" if (h3 % 2 == 0) else "#2A2421"
        special = "pearl_earring" if is_female and (h2 % 2 == 0) else "youth_glow"
    else:
        hair_color = "#2C3437" if (h3 % 2 == 0) else "#3B2F2F"
        special = "pearl_earring" if is_female and (h2 % 3 == 0) else "standard"

    if is_female:
        hair_type = FEMALE_HAIR_STYLES[h1 % len(FEMALE_HAIR_STYLES)]
        skin_tone = SKIN_TONES_FEMALE[h2 % len(SKIN_TONES_FEMALE)]
        glasses = (h3 % 5 == 0)
        suit_color = party_color if (h2 % 3 != 0) else "#1E293B"
    else:
        if resolved_age >= 66 and (h1 % 2 == 0):
            hair_type = "silver_elder"
        elif resolved_age < 45 and (h1 % 2 == 0):
            hair_type = "youth_two_eight_part"
        else:
            hair_type = MALE_HAIR_STYLES[h1 % len(MALE_HAIR_STYLES)]
        skin_tone = SKIN_TONES_MALE[h2 % len(SKIN_TONES_MALE)]
        glasses = (h3 % 3 == 0) or (resolved_age >= 58 and (h3 % 2 == 0))
        suit_color = "#0F172A" if (h2 % 2 == 0) else "#1E293B"

    return {
        "gender": resolved_gender,
        "hair_type": hair_type,
        "hair_color": hair_color,
        "skin_tone": skin_tone,
        "glasses": glasses,
        "glasses_frame": GLASSES_FRAMES[h2 % len(GLASSES_FRAMES)],
        "expression": EXPRESSIONS[h3 % len(EXPRESSIONS)],
        "tie_color": party_color,
        "suit_color": suit_color,
        "suit_type": "jacket_scarf" if is_female else "standard_suit",
        "special_feature": special,
    }


def _render_hair_svg(hair_type: str, hair_color: str, is_female: bool) -> str:
    """헤어스타일 유형별 SVG 패스 생성"""
    if hair_type == "youth_two_eight_part":
        return f"""
        <path d="M 28 44 C 26 22 46 10 68 10 C 92 10 112 20 110 44 C 105 28 86 18 68 18 C 50 18 36 28 28 44 Z" fill="{hair_color}" />
        <path d="M 38 18 C 50 14 62 13 80 18 C 96 22 108 30 110 42 C 102 30 88 24 74 23 C 58 22 46 26 38 18 Z" fill="#4B382A" opacity="0.65"/>
        <path d="M 27 44 C 25 54 28 64 30 68 C 31 58 30 48 33 44 Z" fill="{hair_color}" />
        <path d="M 111 44 C 113 54 110 64 108 68 C 107 58 108 48 105 44 Z" fill="{hair_color}" />
        """
    if hair_type in ("silver_elder", "silver_dignified"):
        return f"""
        <path d="M 30 46 C 28 20 50 12 70 12 C 90 12 112 20 110 46 C 102 28 86 18 70 18 C 52 18 38 28 30 46 Z" fill="{hair_color}" />
        <path d="M 32 38 C 44 24 66 18 88 22 C 98 24 106 30 108 40 C 98 30 86 24 72 23 C 54 22 40 30 32 38 Z" fill="#F1F5F9" opacity="0.88"/>
        <path d="M 28 46 C 26 56 29 66 31 70 C 31 60 30 50 33 46 Z" fill="{hair_color}" />
        <path d="M 112 46 C 114 56 111 66 109 70 C 109 60 110 50 107 46 Z" fill="{hair_color}" />
        """
    if hair_type == "sharp_dandy":
        return f"""
        <path d="M 28 44 C 28 20 50 11 70 11 C 92 11 112 20 112 44 C 108 26 88 18 70 18 C 50 18 34 28 28 44 Z" fill="{hair_color}" />
        <path d="M 30 38 C 45 22 72 18 96 26 C 104 30 110 36 112 44 C 104 32 90 26 75 25 C 55 24 40 32 30 38 Z" fill="{hair_color}" />
        <path d="M 27 44 C 25 54 27 65 29 68 C 30 58 29 48 32 44 Z" fill="{hair_color}" />
        <path d="M 113 44 C 115 54 113 65 111 68 C 110 58 111 48 108 44 Z" fill="{hair_color}" />
        """
    if hair_type == "forehead_clean":
        return f"""
        <path d="M 30 44 C 29 22 48 13 70 13 C 92 13 111 22 110 44 C 104 30 88 22 70 22 C 52 22 36 30 30 44 Z" fill="{hair_color}" />
        <path d="M 29 44 C 28 53 29 60 31 64 L 33 46 Z" fill="{hair_color}" />
        <path d="M 111 44 C 112 53 111 60 109 64 L 107 46 Z" fill="{hair_color}" />
        """
    if hair_type == "dynamic_crop":
        return f"""
        <path d="M 29 43 C 28 19 46 10 70 10 C 94 10 112 19 111 43 C 104 28 90 20 70 20 C 50 20 36 28 29 43 Z" fill="{hair_color}" />
        <path d="M 44 16 L 52 24 L 62 15 L 72 23 L 84 15 L 94 24" stroke="{hair_color}" stroke-width="3" fill="none" stroke-linecap="round"/>
        """
    if is_female:
        if hair_type in ("anchor_bob", "elegant_volume_bob", "modern_teal_bob"):
            return f"""
            <path d="M 25 46 C 23 18 46 10 70 10 C 94 10 117 18 115 46 C 117 65 112 82 103 88 C 103 74 106 60 104 48 C 96 28 84 18 70 18 C 54 18 42 28 36 48 C 34 60 37 74 37 88 C 28 82 23 65 25 46 Z" fill="{hair_color}" />
            <path d="M 32 39 C 46 23 68 19 90 22 C 102 24 109 31 112 41 C 100 32 86 27 70 27 C 54 27 42 33 32 39 Z" fill="{hair_color}" opacity="0.92"/>
            """
        if hair_type == "energetic_short_perm":
            return f"""
            <path d="M 26 45 C 23 19 44 9 70 9 C 96 9 117 19 114 45 C 113 58 109 68 104 72 C 104 60 105 49 102 42 C 95 26 83 19 70 19 C 56 19 44 26 38 42 C 35 49 36 60 36 72 C 31 68 27 58 26 45 Z" fill="{hair_color}" />
            <path d="M 34 36 C 48 22 72 20 96 28 C 103 32 108 38 110 43 C 96 32 76 28 56 30 C 44 31 38 35 34 36 Z" fill="{hair_color}" />
            """
        return f"""
        <path d="M 24 46 C 22 18 46 10 70 10 C 94 10 118 18 116 46 C 118 68 114 88 105 96 C 105 82 107 65 105 50 C 98 28 84 18 70 18 C 54 18 40 28 35 50 C 33 65 35 82 35 96 C 26 88 22 68 24 46 Z" fill="{hair_color}" />
        <path d="M 30 40 C 44 24 66 20 88 22 C 100 24 108 32 112 42 C 102 32 88 28 72 28 C 54 28 42 34 30 40 Z" fill="{hair_color}" opacity="0.9"/>
        """
    return f"""
    <path d="M 30 44 C 28 22 48 12 70 12 C 92 12 112 22 110 44 C 104 28 88 18 70 18 C 50 18 36 28 30 44 Z" fill="{hair_color}" />
    <path d="M 34 38 C 48 24 70 20 90 25 C 100 28 108 35 110 44 C 100 34 88 28 72 28 C 54 28 42 34 34 38 Z" fill="{hair_color}" opacity="0.9"/>
    """


def generate_caricature_svg(
    name: str,
    party: str,
    party_color: str,
    size: int = 140,
    gender: Optional[str] = None,
    age: Optional[int] = None,
    committee_role: Optional[str] = None,
) -> str:
    """
    299명 전체 의원의 고유 인상·성별·나이대·정당컬러·직책 핀을 정교하게 렌더링한 SVG 반환
    """
    profile = MEMBER_CARICATURE_PROFILES.get(name)
    # 동명이인(예: 1987년생 초선 박지원 vs 1942년생 5선 박지원) 연령 불일치 시 동적 생성기 사용
    if profile and name == "박지원" and age is not None and age < 60:
        profile = None

    if not profile:
        profile = _build_dynamic_profile(name=name, party_color=party_color, gender=gender, age=age)
    else:
        profile = dict(profile)
        if party_color:
            profile["tie_color"] = party_color

    uid = hashlib.md5(f"{name}_{party}_{age}_{committee_role}".encode("utf-8")).hexdigest()[:10]
    bg_grad_id = f"grad_{uid}"

    hair_type = profile.get("hair_type", "neat_side_part")
    hair_color = profile.get("hair_color", "#2A2D34")
    skin_tone = profile.get("skin_tone", "#FCE5D8")
    glasses = profile.get("glasses", False)
    glasses_frame = profile.get("glasses_frame", "#333333")
    tie_color = profile.get("tie_color", party_color)
    suit_color = profile.get("suit_color", "#1E293B")
    expression = profile.get("expression", "warm_gentle_smile")
    special = profile.get("special_feature", "")
    is_female = (gender == "female") if gender in ("male", "female") else (profile.get("gender") == "female")

    # 1. 헤어스타일 드로잉
    hair_svg = _render_hair_svg(hair_type, hair_color, is_female)

    # 2. 안경 스타일링
    glasses_svg = ""
    if glasses:
        if glasses_frame == "#111827":
            glasses_svg = f"""
            <g stroke="{glasses_frame}" stroke-width="3.4" fill="none" opacity="0.98">
                <rect x="42" y="50" width="24" height="17" rx="3" fill="rgba(255,255,255,0.18)"/>
                <rect x="74" y="50" width="24" height="17" rx="3" fill="rgba(255,255,255,0.18)"/>
                <path d="M 66 57 L 74 57" stroke-width="4"/>
                <path d="M 36 55 L 42 56" />
                <path d="M 98 56 L 104 55" />
            </g>
            """
        elif glasses_frame == "#B8860B":
            glasses_svg = """
            <g stroke="#D4AF37" stroke-width="2" fill="none" opacity="0.95">
                <rect x="43" y="51" width="23" height="16" rx="4" fill="rgba(255,255,255,0.2)"/>
                <rect x="74" y="51" width="23" height="16" rx="4" fill="rgba(255,255,255,0.2)"/>
                <path d="M 66 57 L 74 57" />
                <path d="M 37 55 L 43 56" />
                <path d="M 97 56 L 103 55" />
            </g>
            """
        else:
            glasses_svg = f"""
            <g stroke="{glasses_frame}" stroke-width="2.2" fill="none" opacity="0.95">
                <rect x="43" y="51" width="23" height="16" rx="4" fill="rgba(255,255,255,0.2)"/>
                <rect x="74" y="51" width="23" height="16" rx="4" fill="rgba(255,255,255,0.2)"/>
                <path d="M 66 57 L 74 57" />
                <path d="M 37 55 L 43 56" />
                <path d="M 97 56 L 103 55" />
            </g>
            """

    # 3. 연륜 주름 & 귀걸이 포인트
    extra_face_svg = ""
    if special == "wise_wrinkles":
        extra_face_svg = """
        <path d="M 38 56 Q 42 58 40 62" stroke="#A07258" stroke-width="1.2" fill="none" opacity="0.68"/>
        <path d="M 102 56 Q 98 58 100 62" stroke="#A07258" stroke-width="1.2" fill="none" opacity="0.68"/>
        <path d="M 62 70 Q 70 72 78 70" stroke="#A07258" stroke-width="1" fill="none" opacity="0.48"/>
        <path d="M 52 46 Q 70 44 88 46" stroke="#A07258" stroke-width="1" fill="none" opacity="0.55"/>
        """
    elif special == "pearl_earring" and is_female:
        extra_face_svg = """
        <circle cx="35.5" cy="70" r="2.2" fill="#FFFBEB" stroke="#CBD5E1" stroke-width="0.6"/>
        <circle cx="104.5" cy="70" r="2.2" fill="#FFFBEB" stroke="#CBD5E1" stroke-width="0.6"/>
        """

    # 4. 표정 (눈 & 눈썹 & 입)
    if expression == "smart_witty_smirk":
        mouth_svg = '<path d="M 62 76 Q 73 74 81 72" stroke="#9B2C2C" stroke-width="2.5" fill="none" stroke-linecap="round" />'
        eyes_svg = """
        <ellipse cx="54" cy="58" rx="3.5" ry="3.8" fill="#1A202C" />
        <circle cx="55.5" cy="56.5" r="1.1" fill="#FFFFFF" />
        <ellipse cx="86" cy="58" rx="3.5" ry="3.8" fill="#1A202C" />
        <circle cx="87.5" cy="56.5" r="1.1" fill="#FFFFFF" />
        <path d="M 47 49 Q 54 46 61 50" stroke="#2D3748" stroke-width="2.5" fill="none" stroke-linecap="round" />
        <path d="M 79 49 Q 86 45 93 47" stroke="#2D3748" stroke-width="2.8" fill="none" stroke-linecap="round" />
        """
    elif expression == "fierce_determined_grin":
        mouth_svg = '<path d="M 60 76 Q 70 82 80 76" stroke="#8B0000" stroke-width="3" fill="none" stroke-linecap="round" />'
        eyes_svg = """
        <ellipse cx="54" cy="58" rx="3.6" ry="3.6" fill="#0F172A" />
        <circle cx="55.5" cy="56.5" r="1" fill="#FFFFFF" />
        <ellipse cx="86" cy="58" rx="3.6" ry="3.6" fill="#0F172A" />
        <circle cx="87.5" cy="56.5" r="1" fill="#FFFFFF" />
        <path d="M 46 47 L 62 51" stroke="#0F172A" stroke-width="3.2" fill="none" stroke-linecap="round" />
        <path d="M 94 47 L 78 51" stroke="#0F172A" stroke-width="3.2" fill="none" stroke-linecap="round" />
        """
    elif expression == "charismatic_leader":
        mouth_svg = '<path d="M 63 76 Q 70 78 77 76" stroke="#9B2C2C" stroke-width="2.5" fill="none" stroke-linecap="round" />'
        eyes_svg = """
        <ellipse cx="54" cy="58" rx="3.5" ry="4" fill="#1A202C" />
        <circle cx="55.5" cy="56.5" r="1.2" fill="#FFFFFF" />
        <ellipse cx="86" cy="58" rx="3.5" ry="4" fill="#1A202C" />
        <circle cx="87.5" cy="56.5" r="1.2" fill="#FFFFFF" />
        <path d="M 47 48 Q 55 46 61 50" stroke="#1E293B" stroke-width="2.8" fill="none" stroke-linecap="round" />
        <path d="M 79 50 Q 85 46 93 48" stroke="#1E293B" stroke-width="2.8" fill="none" stroke-linecap="round" />
        """
    elif expression == "confident_smile":
        mouth_svg = '<path d="M 61 75 Q 70 83 79 75" stroke="#B91C1C" stroke-width="2.4" fill="none" stroke-linecap="round" />'
        eyes_svg = """
        <ellipse cx="54" cy="58" rx="3.6" ry="4" fill="#1A202C" />
        <circle cx="55.5" cy="56.5" r="1.2" fill="#FFFFFF" />
        <ellipse cx="86" cy="58" rx="3.6" ry="4" fill="#1A202C" />
        <circle cx="87.5" cy="56.5" r="1.2" fill="#FFFFFF" />
        <path d="M 47 49 Q 54 46 61 49" stroke="#374151" stroke-width="2.4" fill="none" stroke-linecap="round" />
        <path d="M 79 49 Q 86 46 93 49" stroke="#374151" stroke-width="2.4" fill="none" stroke-linecap="round" />
        """
    else:
        mouth_svg = '<path d="M 62 76 Q 70 82 78 76" stroke="#9B2C2C" stroke-width="2.5" fill="none" stroke-linecap="round" />'
        eyes_svg = """
        <ellipse cx="54" cy="58" rx="3.5" ry="4" fill="#1A202C" />
        <circle cx="55.5" cy="56.5" r="1.2" fill="#FFFFFF" />
        <ellipse cx="86" cy="58" rx="3.5" ry="4" fill="#1A202C" />
        <circle cx="87.5" cy="56.5" r="1.2" fill="#FFFFFF" />
        <path d="M 48 50 Q 55 47 61 50" stroke="#4A5568" stroke-width="2.5" fill="none" stroke-linecap="round" />
        <path d="M 79 50 Q 85 47 92 50" stroke="#4A5568" stroke-width="2.5" fill="none" stroke-linecap="round" />
        """

    # 5. 직책 핀 (chair_pin: 위원장/국회의장 황금 별 핀, 간사 실버 핀)
    chair_pin_svg = ""
    if committee_role == "chair":
        chair_pin_svg = """
        <circle cx="94" cy="106" r="5" fill="#FBBF24" stroke="#B45309" stroke-width="1.2"/>
        <text x="94" y="108.5" font-size="6" font-weight="bold" fill="#78350F" text-anchor="middle">★</text>
        """
    elif committee_role == "secretary":
        chair_pin_svg = """
        <circle cx="94" cy="106" r="4.2" fill="#E2E8F0" stroke="#64748B" stroke-width="1"/>
        <text x="94" y="108" font-size="4.5" font-weight="bold" fill="#334155" text-anchor="middle">幹</text>
        """

    # 6. 의상 & 국회 배지
    if is_female:
        outfit_svg = f"""
        <path d="M 34 110 C 34 94 48 90 70 90 C 92 90 106 94 106 110 L 118 140 L 22 140 Z" fill="{suit_color}" />
        <polygon points="70,90 58,118 82,118" fill="#FFFFFF" />
        <polygon points="70,98 62,122 78,122" fill="{tie_color}" />
        <circle cx="48" cy="106" r="4.5" fill="#FFD700" stroke="#B7791F" stroke-width="1"/>
        <text x="48" y="108.5" font-size="4" font-weight="bold" fill="#744210" text-anchor="middle">國</text>
        {chair_pin_svg}
        """
    else:
        outfit_svg = f"""
        <path d="M 32 110 C 32 94 46 90 70 90 C 94 90 108 94 108 110 L 122 140 L 18 140 Z" fill="{suit_color}" />
        <polygon points="70,92 56,112 84,112" fill="#FFFFFF" />
        <polygon points="67,100 73,100 76,138 70,140 64,138" fill="{tie_color}" />
        <polygon points="66,97 74,97 72,104 68,104" fill="{tie_color}" />
        <circle cx="46" cy="106" r="4.5" fill="#FFD700" stroke="#B7791F" stroke-width="1"/>
        <text x="46" y="108.5" font-size="4" font-weight="bold" fill="#744210" text-anchor="middle">國</text>
        {chair_pin_svg}
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
    {extra_face_svg}
    {glasses_svg}
    {hair_svg}
</svg>"""
    return svg
