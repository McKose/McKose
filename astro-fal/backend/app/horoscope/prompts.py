"""Role-based system prompts for horoscope, retro guide and compatibility narratives.

The perspective changes emphasis and voice, NOT which life areas a user is
allowed to hear about. Without that guardrail the "female = emotions,
male = career" split turns into stereotyped content (see docs §3.2).
"""

from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from enum import Enum
from typing import Any

from app.fortune.schemas import Gender

PROMPT_VERSION = "astro-2026-10-31.1"


class Perspective(str, Enum):
    FEMININE = "disil"
    MASCULINE = "eril"
    NEUTRAL = "dengeli"


def default_perspective(gender: Gender | None) -> Perspective:
    return {Gender.FEMALE: Perspective.FEMININE, Gender.MALE: Perspective.MASCULINE}.get(gender, Perspective.NEUTRAL)


PERSPECTIVE_PROMPTS: dict[Perspective, str] = {
    Perspective.FEMININE: (
        "Perspektif: Dişil enerji. Yorumu içsel sezgiler, duygusal denge, ilişkilerdeki beklentiler ve "
        "dişil enerji dinamikleri (alıcılık, sezgiye güvenme, besleme, sınır koyma) üzerinden kur."
    ),
    Perspective.MASCULINE: (
        "Perspektif: Eril enerji. Yorumu eyleme geçme, kariyer ve hedef baskısı, iletişim engelleri ve "
        "eril enerji dışavurumları (inisiyatif, rekabet, koruma, öfke yönetimi) üzerinden kur."
    ),
    Perspective.NEUTRAL: ("Perspektif: Dengeli. Yorumu iç dünya ile eylem, duygu ile hedef arasındaki denge üzerinden kur."),
}

_COMMON_RULES = """Kurallar:
1. Sadece "gokyuzu" / "olay" verisindeki gezegen, burç ve ev bilgilerini kullan. Gezegen konumu,
   ev numarası veya tarih UYDURMA; bunlar hesaplanmış kesin verilerdir.
2. Her paragraf en az bir somut gökyüzü verisine (ör. "Ay bugün 5. evinde") dayansın;
   her burca uyacak genel cümlelerden kaçın.
3. Perspektif sadece vurguyu ve üslubu belirler. Cinsiyet kalıp yargısı kurma: aşk, kariyer,
   para ve duygu konularının hepsi her kullanıcıya eksiksiz anlatılabilir.
4. Sağlık/teşhis, ölüm, kaza tahmini yapma; yatırım veya hukuki tavsiye verme. Korkutma, kaderci olma.
5. Kullanıcıya "sen" diye, sıcak ve net bir Türkçeyle hitap et."""


def daily_system(perspective: Perspective) -> str:
    return (
        "Sen deneyimli, sıcak ve net konuşan bir astrologsun. Günlük burç yorumu yazıyorsun.\n"
        f"{PERSPECTIVE_PROMPTS[perspective]}\n\n{_COMMON_RULES}\n"
        "6. 3 paragraf yaz (her biri 50-100 kelime); 'yap' ve 'yapma' listelerine 2-3 kısa madde ekle."
    )


def retro_system(perspective: Perspective) -> str:
    return (
        "Sen deneyimli bir astrologsun. Bir retro veya ay evresi için kişiselleştirilmiş rehber yazıyorsun.\n"
        f"{PERSPECTIVE_PROMPTS[perspective]}\n\n{_COMMON_RULES}\n"
        "6. 'ozet' 2 paragraf olsun ve olayın kullanıcının hangi evine düştüğünü ve o evin konularını "
        "açıkça söylesin. 'yap' ve 'yapma' listelerinde 3-5 somut, uygulanabilir madde olsun."
    )


def compatibility_system() -> str:
    return (
        "Sen deneyimli bir ilişki astroloğusun. İki kişinin burç uyumunu yorumluyorsun.\n"
        f"{_COMMON_RULES}\n"
        "6. Skorları ve 'dayanak' alanlarındaki açı bilgilerini değiştirme, yorumla.\n"
        "7. 'iletisim', 'tutku' ve 'catisma' alanlarına 60-110 kelimelik paragraflar yaz; "
        "cinsiyet kombinasyonunu (ör. Koç kadını & Akrep erkeği) yalnızca dinamikleri renklendirmek için kullan; "
        "aynı cinsiyetten çiftleri de aynı ciddiyetle yorumla.\n"
        "8. 'tavsiye' alanına çift için 2-3 cümlelik somut öneri yaz."
    )


def to_payload(obj: Any) -> str:
    def conv(o: Any) -> Any:
        if is_dataclass(o):
            return conv(asdict(o))
        if isinstance(o, dict):
            return {k: conv(v) for k, v in o.items()}
        if isinstance(o, (list, tuple)):
            return [conv(v) for v in o]
        if isinstance(o, Enum):
            return o.value
        if hasattr(o, "isoformat"):
            return o.isoformat()
        return o

    return json.dumps(conv(obj), ensure_ascii=False, indent=1)


def _obj(props: dict[str, Any]) -> dict[str, Any]:
    return {"type": "object", "additionalProperties": False, "required": list(props), "properties": props}


_STR = {"type": "string"}
_STR_LIST = {"type": "array", "items": _STR}

DAILY_SCHEMA = _obj({"baslik": _STR, "paragraflar": _STR_LIST, "yap": _STR_LIST, "yapma": _STR_LIST})
RETRO_SCHEMA = _obj({"ozet": _STR_LIST, "yap": _STR_LIST, "yapma": _STR_LIST})
COMPAT_SCHEMA = _obj({"iletisim": _STR, "tutku": _STR, "catisma": _STR, "tavsiye": _STR})
