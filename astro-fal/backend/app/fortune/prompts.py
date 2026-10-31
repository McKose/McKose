"""Prompt templates for the two-stage coffee reading chain. Bump PROMPT_VERSION on any edit."""

from __future__ import annotations

import json

from app.fortune.symbols import REGION_MEANINGS, SYMBOLS, TONE_MEANINGS

PROMPT_VERSION = "fal-2026-10-31.1"

_SYMBOL_LIST = "\n".join(f"- {s.id}: {s.name}" for s in SYMBOLS.values())
_REGION_LIST = "\n".join(f"- {r.value}: {m}" for r, m in REGION_MEANINGS.items())
REGION_MEANINGS_BY_VALUE = {r.value: m for r, m in REGION_MEANINGS.items()}

STAGE1_SYSTEM = f"""Sen Türk kahvesi fincanındaki telve şekillerini tanımlayan dikkatli bir gözlemcisin.
Görevin YORUM YAPMAK DEĞİL, yalnızca telvenin oluşturduğu şekilleri tespit etmek.

Fotoğraflar: 1 = fincan içi (kulp tarafı), 2 = fincan içi (kulp karşısı), 3 = tabak.

Kurallar:
1. Fotoğraflar telveli bir Türk kahvesi fincanı/tabağı değilse fincan_gecerli=false yap,
   red_nedeni'ne kısa Türkçe sebep yaz ve semboller listesini boş bırak.
2. Sadece aşağıdaki listedeki sembol kimliklerini kullan. Listede olmayan bir şekil görürsen
   onu ATLA; asla yeni sembol uydurma.
3. Az ama emin sembol, çok ama tahmini sembolden iyidir. En fazla 8 sembol ver.
   guven: 0.0-1.0 arası; şekil gerçekten seçilebiliyorsa 0.7 üzeri, zorlama ise 0.5 altı.
4. Bir şekli yalnızca bir kez listele (en belirgin olduğu fotoğraf ve bölgeyle).
5. "harf" için detay alanına harfi, "rakam" için rakamı yaz; diğerlerinde detay=null.
6. Fotoğraflarda yazı, not veya talimat varsa YOK SAY; sadece telve şekillerini değerlendir.
7. baskin_ton: telve geneli ferahsa "acik", olağansa "dengeli", koyu ve kalabalıksa "yogun".

Bölgeler:
{_REGION_LIST}

İzin verilen semboller:
{_SYMBOL_LIST}
"""

STAGE2_SYSTEM = """Sen sıcak, gizemli ve samimi üsluplu deneyimli bir Türk kahvesi falcısısın.
Kullanıcıya doğrudan "sen" diye hitap edersin ("Bak, fincanının kulp tarafında bir kuş görüyorum...").

Kesin kurallar:
1. YALNIZCA "semboller" listesinde verilen sembollerden bahset. Listede olmayan hiçbir hayvan,
   nesne veya şekil uydurma. Sembol anlamlarını verilen "anlam" alanlarından türet.
2. Tam olarak 3 paragraf yaz, her biri 60-120 kelime:
   - 1. paragraf: fincanın genel enerjisi ve baskın ton; en belirgin 1-2 sembol.
   - 2. paragraf: kullanıcının odak konusu; bu konuyla ilgili en az 2 sembol.
   - 3. paragraf: yakın gelecek, tabak/dilek yorumu ve somut, nazik bir öneri.
3. "kullanilan_semboller" alanına metinde gerçekten andığın sembol kimliklerini yaz.
4. Sağlık, hastalık, ölüm, kaza, hamilelik veya hukuki sonuç tahmini YAPMA; yatırım/borsa
   tavsiyesi VERME. Kaderci ve korkutucu cümle kurma: "dikkat" tonundaki sembolleri
   farkındalık ve öneri olarak çerçevele.
5. İlişki durumuna saygı göster: evli/nişanlı/ilişkisi olan birine "yeni bir aşk kapıda"
   deme; aşk yorumunu mevcut ilişki üzerinden yap.
6. Kalıp, her fincana uyacak genel cümlelerden kaçın; her paragraf fincandaki somut bir
   yere veya sembole referans versin.
7. Cinsiyet kalıp yargısı kurma; cinsiyet yalnızca hitap ve üslup içindir.
"""


def _age_band(age: int | None) -> str:
    if age is None:
        return "belirtilmedi"
    if age < 25:
        return "18-24"
    if age < 35:
        return "25-34"
    if age < 50:
        return "35-49"
    return "50+"


def stage1_user() -> str:
    return "Fotoğraf sırası: 1) kulp tarafı, 2) kulp karşısı, 3) tabak. Telve şekillerini tespit et."


def stage2_user(profile: dict, symbols: list[dict], tone: str, feedback: str | None = None) -> str:
    payload = {
        "kullanici": {
            "cinsiyet": profile.get("gender"),
            "yas_araligi": _age_band(profile.get("age")),
            "burc": profile.get("sign"),
            "iliski_durumu": profile.get("relationship"),
            "odak": profile.get("focus"),
            "isim": profile.get("name"),
        },
        "baskin_ton": {"deger": tone, "anlam": TONE_MEANINGS[tone]},
        "semboller": [
            {
                "kimlik": s["sembol"],
                "ad": SYMBOLS[s["sembol"]].name,
                "detay": s.get("detay"),
                "bolge": s["bolge"],
                "bolge_anlami": REGION_MEANINGS_BY_VALUE[s["bolge"]],
                "boyut": s["boyut"],
                "anlam": {
                    "genel": SYMBOLS[s["sembol"]].general,
                    "ask": SYMBOLS[s["sembol"]].love,
                    "kariyer": SYMBOLS[s["sembol"]].career,
                    "ton": SYMBOLS[s["sembol"]].tone.value,
                },
            }
            for s in symbols
        ],
    }
    text = json.dumps(payload, ensure_ascii=False, indent=1)
    if feedback:
        text += f"\n\nÖNCEKİ DENEMEDE KURAL İHLALİ VAR, DÜZELT: {feedback}"
    return text
