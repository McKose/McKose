"""Deterministic offline LLM for tests and local development (LLM_PROVIDER=fake).

Produces schema-valid output derived from the request payload so the whole API
can be exercised end-to-end without network or API keys.
"""

from __future__ import annotations

import json
from typing import Any

from app.llm.base import ImageInput

_FILLER = (
    "Fincanındaki bu işaret sana sabırla ilerlemeni ve içindeki sesi dinlemeni söylüyor. "
    "Önündeki günlerde küçük ama anlamlı adımlar atacaksın ve çevrendeki insanlar bunu fark edecek. "
    "Acele etmeden, kendine güvenerek yürüdüğünde kapılar birer birer aralanacak. "
    "Kalbinden geçen dileğin için sabırlı ol; zamanı geldiğinde her şey yerli yerine oturacak."
)


class FakeLLM:
    def __init__(self, model_id: str = "fake-llm", overrides: dict[str, list[dict[str, Any]]] | None = None) -> None:
        self.model_id = model_id
        self.calls: list[dict[str, Any]] = []
        # schema_name -> queue of canned responses (consumed in order), for tests
        self._overrides = overrides or {}

    async def complete_json(
        self,
        *,
        system: str,
        user: str,
        schema_name: str,
        schema: dict[str, Any],
        images: list[ImageInput] | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1200,
    ) -> dict[str, Any]:
        self.calls.append({"schema_name": schema_name, "user": user, "images": len(images or [])})
        queue = self._overrides.get(schema_name)
        if queue:
            return queue.pop(0)
        return getattr(self, f"_{schema_name}")(user)

    @staticmethod
    def _coffee_symbols(_: str) -> dict[str, Any]:
        return {
            "fincan_gecerli": True,
            "red_nedeni": None,
            "gorsel_kalitesi": "iyi",
            "baskin_ton": "dengeli",
            "semboller": [
                {"sembol": "kus", "bolge": "kenar", "fotograf": 1, "boyut": "orta", "guven": 0.86, "detay": None},
                {"sembol": "yol", "bolge": "kulp_karsisi", "fotograf": 2, "boyut": "buyuk", "guven": 0.78, "detay": None},
                {"sembol": "harf", "bolge": "kulp_yani", "fotograf": 1, "boyut": "kucuk", "guven": 0.66, "detay": "M"},
                {"sembol": "dag", "bolge": "dip", "fotograf": 2, "boyut": "orta", "guven": 0.41, "detay": None},
            ],
        }

    @staticmethod
    def _coffee_reading(user: str) -> dict[str, Any]:
        payload = json.loads(user.split("\n\nÖNCEKİ")[0])
        names = [s["ad"] for s in payload["semboller"]]
        ids = [s["kimlik"] for s in payload["semboller"]]
        paragraphs = [f"{names[i % len(names)]} işaretine bakıyorum. {_FILLER}" for i in range(3)]
        return {"paragraflar": paragraphs, "kullanilan_semboller": ids}

    @staticmethod
    def _daily_horoscope(user: str) -> dict[str, Any]:
        p = json.loads(user)
        moon = next(pl for pl in p["gokyuzu"]["planets"] if pl["planet"] == "Ay")
        return {
            "baslik": f"{p['burc']} için {p['tarih']}",
            "paragraflar": [f"Ay bugün {moon['house']}. evinde ({moon['house_theme']}). {_FILLER}"] * 3,
            "yap": ["Planını yazıya dök", "Bir dostunu ara"],
            "yapma": ["Aceleyle söz verme", "Gece geç saatte önemli mesaj atma"],
        }

    @staticmethod
    def _retro_guide(user: str) -> dict[str, Any]:
        e = json.loads(user)["olay"]
        return {
            "ozet": [f"{e['title']} {e['house']}. evinde: {e['house_theme']}. {_FILLER}", _FILLER],
            "yap": ["Eski dosyaları gözden geçir", "Yedek al", "Sözleşmeleri iki kez oku"],
            "yapma": ["Yeni cihaz satın alma", "Aceleyle imza atma", "Eski tartışmaları alevlendirme"],
        }

    @staticmethod
    def _compatibility(user: str) -> dict[str, Any]:
        p = json.loads(user)
        return {
            "iletisim": f"{p['kisi_a']} ile {p['kisi_b']} arasında iletişim: {_FILLER}",
            "tutku": f"Genel skor {p['genel_skor']}. {_FILLER}",
            "catisma": _FILLER,
            "tavsiye": "Haftada bir akşamı telefonsuz geçirin. Kararları birlikte yazıya dökün.",
        }
