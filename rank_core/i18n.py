"""
Rank Core i18n (Internationalization) Manager
Supports multi-language dictionaries and entity field resolution.
"""

from typing import Dict, Any, Optional

DEFAULT_TRANSLATIONS: Dict[str, Dict[str, str]] = {
    "ko": {
        "rank": "순위",
        "name": "이름",
        "score": "종합 점수",
        "vote": "투표하기",
        "search": "검색...",
        "category": "카테고리",
        "methodology": "산출 방법론",
        "details": "상세 보기",
        "total_count": "총 건수",
        "vote_success": "투표가 성공적으로 반영되었습니다.",
        "not_found": "항목을 찾을 수 없습니다."
    },
    "en": {
        "rank": "Rank",
        "name": "Name",
        "score": "Total Score",
        "vote": "Vote",
        "search": "Search...",
        "category": "Category",
        "methodology": "Methodology",
        "details": "View Details",
        "total_count": "Total Count",
        "vote_success": "Vote successfully recorded.",
        "not_found": "Item not found."
    }
}


class I18nManager:
    def __init__(self, custom_translations: Optional[Dict[str, Dict[str, str]]] = None):
        self.translations = dict(DEFAULT_TRANSLATIONS)
        if custom_translations:
            for lang, mapping in custom_translations.items():
                if lang not in self.translations:
                    self.translations[lang] = {}
                self.translations[lang].update(mapping)

    def get_text(self, key: str, lang: str = "ko") -> str:
        lang_dict = self.translations.get(lang.lower(), self.translations["ko"])
        return lang_dict.get(key, key)

    def resolve_entity_language(self, entity: Dict[str, Any], lang: str = "ko") -> Dict[str, Any]:
        """
        lang가 'en'일 때 name_en, category_en, description_en 등 영문 필드를 최우선 적용
        """
        if lang.lower() != "en":
            return entity

        resolved = dict(entity)
        if entity.get("name_en"):
            resolved["display_name"] = entity["name_en"]
            resolved["name"] = entity["name_en"]

        if entity.get("category_en"):
            resolved["category"] = entity["category_en"]

        if entity.get("description_en"):
            resolved["description"] = entity["description_en"]

        return resolved
