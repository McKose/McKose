"""Controlled vocabulary of Turkish coffee-reading symbols.

The vision stage may ONLY emit ids from this table (enforced by JSON-schema
enum). The narrative stage receives the traditional meanings from here, so
interpretations are grounded in a curated lexicon instead of the model's
imagination. Content owners can extend this table without touching prompts.

``check_terms`` are regex fragments (matched at a word start, Turkish-lowercased)
used by the post-generation hallucination guard. Symbols whose words also occur
in ordinary prose or idioms ("yol", "ev", "kalp", "anahtar", "çiçek açmak",
"bu noktada", "kuşku", "çarpıcı") or are zodiac names ("aslan") have none.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Tone(str, Enum):
    POSITIVE = "olumlu"
    NEUTRAL = "notr"
    CAUTION = "dikkat"  # never rendered as doom; framed as "be mindful"


@dataclass(frozen=True)
class Symbol:
    id: str
    name: str
    general: str
    love: str
    career: str
    tone: Tone
    check_terms: tuple[str, ...] = field(default_factory=tuple)


_S = Symbol
SYMBOLS: dict[str, Symbol] = {
    s.id: s
    for s in [
        _S(
            "kus",
            "Kuş",
            "haber, müjde",
            "sevdiğinden haber",
            "iş teklifi haberi",
            Tone.POSITIVE,
            (r"kuş(?:u|un|lar\w*|a|tan)?\b",),
        ),
        _S(
            "kus_surusu",
            "Kuş sürüsü",
            "art arda haberler, kalabalık",
            "çevreden gelen ilgi",
            "birden fazla fırsat",
            Tone.POSITIVE,
        ),
        _S(
            "balik",
            "Balık",
            "kısmet, bereket, para",
            "bereketli bir ilişki dönemi",
            "maddi kazanç",
            Tone.POSITIVE,
            (r"balı[kğ]\w*",),
        ),
        _S("yol", "Yol", "yolculuk, süreç, değişim", "ilişkide yeni bir evre", "kariyerde yön değişimi", Tone.NEUTRAL),
        _S(
            "dag",
            "Dağ",
            "aşılması gereken engel; tepesi başarı",
            "sabır isteyen bir dönem",
            "zorlu ama aşılabilir hedef",
            Tone.CAUTION,
        ),
        _S(
            "yilan",
            "Yılan",
            "kıskançlık, gizli rakip",
            "araya girmek isteyen biri",
            "iş yerinde rekabet",
            Tone.CAUTION,
            (r"yılan\w*",),
        ),
        _S("kalp", "Kalp", "sevgi, duygusal yakınlık", "aşk, karşılıklı duygular", "işini severek yapmak", Tone.POSITIVE),
        _S(
            "kirik_kalp",
            "Kırık kalp",
            "kırgınlık, duygusal yorgunluk",
            "küslük veya kırılganlık",
            "hayal kırıklığından ders",
            Tone.CAUTION,
        ),
        _S(
            "yuzuk",
            "Yüzük",
            "bağlılık, söz, birliktelik",
            "nişan, evlilik, ciddi adım",
            "uzun vadeli anlaşma",
            Tone.POSITIVE,
            (r"yüzü[kğ]\w*",),
        ),
        _S("at", "At", "murat, güç, ilerleme", "arzulanan kavuşma", "hızlı ilerleme, terfi", Tone.POSITIVE),
        _S(
            "anahtar",
            "Anahtar",
            "çözüm, yeni kapı, fırsat",
            "kalbin kapısını açan biri",
            "çözüm bulunan bir mesele",
            Tone.POSITIVE,
        ),
        _S("kapi", "Kapı", "yeni fırsat, eşik", "yeni bir tanışma", "yeni bir iş kapısı", Tone.POSITIVE),
        _S("goz", "Göz", "nazar, dikkat edilen biri", "seni izleyen biri", "üzerindeki dikkat", Tone.CAUTION),
        _S(
            "merdiven",
            "Merdiven",
            "adım adım yükseliş",
            "ilişkide ilerleme",
            "kariyer basamağı, terfi",
            Tone.POSITIVE,
            (r"merdiven\w*",),
        ),
        _S("ev", "Ev", "yuva, aile, ev değişikliği", "birlikte yuva kurma", "çalışma ortamı değişimi", Tone.NEUTRAL),
        _S("agac", "Ağaç", "büyüme, köklenme, aile bağları", "kök salan bir ilişki", "sağlam büyüme", Tone.POSITIVE),
        _S("kopek", "Köpek", "sadık dost", "güvenilir partner", "sadık iş arkadaşı", Tone.POSITIVE, (r"köpe[kğ]\w*",)),
        _S("kedi", "Kedi", "sinsi biri, nankörlük", "samimiyetsiz bir ilgi", "arkadan konuşan biri", Tone.CAUTION, (r"kedi\w*",)),
        _S(
            "fil",
            "Fil",
            "şans, güçlü destek",
            "sağlam bir bağ",
            "güçlü bir destekçi",
            Tone.POSITIVE,
            (r"fil(?:i|in|e|ler\w*)?\b",),
        ),
        _S(
            "deve",
            "Deve",
            "sabır, uzun yol, taşınan yük",
            "sabırla kazanılan ilişki",
            "uzun soluklu emek",
            Tone.NEUTRAL,
            (r"deve\w*",),
        ),
        _S("aslan", "Aslan", "güç, koruyucu, cesaret", "koruyucu bir partner", "liderlik", Tone.POSITIVE),
        _S("kartal", "Kartal", "yüksek mevki, güç", "güçlü ve saygın biri", "yüksek pozisyon", Tone.POSITIVE, (r"kartal\w*",)),
        _S(
            "baykus",
            "Baykuş",
            "sırlar, sezgi, dikkat",
            "söylenmemiş duygular",
            "gizli bilgiye dikkat",
            Tone.CAUTION,
            (r"baykuş\w*",),
        ),
        _S("cicek", "Çiçek", "mutluluk, iltifat", "romantik bir jest", "takdir görme", Tone.POSITIVE),
        _S("gunes", "Güneş", "aydınlık, başarı", "mutlu bir dönem", "parlak başarı", Tone.POSITIVE),
        _S("hilal", "Hilal", "dilek, umut", "kalpte tutulan dilek", "umut veren gelişme", Tone.POSITIVE, (r"hilal\w*",)),
        _S("yildiz", "Yıldız", "şans, dileğin gerçekleşmesi", "şanslı bir tanışma", "şanslı bir fırsat", Tone.POSITIVE),
        _S(
            "harf",
            "Harf",
            "isminin baş harfi önemli biri",
            "bu harfle başlayan biri",
            "bu harfle ilgili bir kişi/kurum",
            Tone.NEUTRAL,
        ),
        _S("rakam", "Rakam", "zaman işareti (gün/hafta/ay)", "gelişmenin zamanı", "sonuç zamanı", Tone.NEUTRAL),
        _S("gemi", "Gemi", "uzaktan haber, yolculuk", "uzaktaki biri", "yurt dışı bağlantısı", Tone.POSITIVE, (r"gemi\w*",)),
        _S(
            "ucak", "Uçak", "uzak yolculuk, hızlı gelişme", "mesafeli ilişki", "hızlı gelişen iş", Tone.POSITIVE, (r"uça[kğ]\w*",)
        ),
        _S(
            "kopru",
            "Köprü",
            "geçiş, uzlaşma",
            "barışma, yakınlaşma",
            "iki taraf arasında arabuluculuk",
            Tone.POSITIVE,
            (r"köprü\w*",),
        ),
        _S(
            "kale",
            "Kale",
            "korunma, güvence",
            "güvende hissetmek",
            "sağlam pozisyon",
            Tone.POSITIVE,
            (r"kale(?:si|ler\w*|nin|yi)?\b",),
        ),
        _S("tac", "Taç", "tanınma, başarı", "değer görmek", "ödül, tanınırlık", Tone.POSITIVE, (r"(?:taç|tacı)\w*",)),
        _S("melek", "Melek", "koruma, iyi niyet", "iyi niyetli biri", "beklenmedik yardım", Tone.POSITIVE, (r"mele[kğ]\w*",)),
        _S(
            "insan_figuru",
            "İnsan figürü",
            "hayatına giren biri",
            "yeni ya da önemli biri",
            "etkili bir kişi",
            Tone.NEUTRAL,
            (r"figür\w*",),
        ),
        _S("el", "El", "yardım, uzanan el", "destek olan biri", "iş birliği", Tone.POSITIVE),
        _S("halka", "Halka", "tamamlanma, döngü", "bir döngünün kapanması", "projenin tamamlanması", Tone.NEUTRAL),
        _S("carpi", "Çarpı", "karar anı, engel", "seçim yapma zamanı", "dur ve düşün", Tone.CAUTION, (r"çarpı(?:sı|lar\w*)?\b",)),
        _S("noktalar", "Nokta kümesi", "para, bolluk", "küçük mutluluklar", "para girişi", Tone.POSITIVE),
        _S("bulut", "Bulut", "belirsizlik, kafa karışıklığı", "netleşmemiş duygular", "belirsiz süreç", Tone.CAUTION),
        _S("hancer", "Hançer", "tartışma, keskin söz", "kırıcı sözlere dikkat", "sert rekabet", Tone.CAUTION, (r"hançer\w*",)),
        _S("mum", "Mum", "dilek, umut ışığı", "sönmeyen umut", "yol gösteren fikir", Tone.POSITIVE, (r"mum(?:u|lar\w*)?\b",)),
        _S("kelebek", "Kelebek", "dönüşüm, hafiflik", "ilişkide tazelenme", "yeni bir döneme geçiş", Tone.POSITIVE),
        _S("dalga", "Dalga", "duygusal dalgalanma", "iniş çıkışlı duygular", "değişken gündem", Tone.NEUTRAL),
    ]
}

SYMBOL_IDS: list[str] = list(SYMBOLS)


class Region(str, Enum):
    RIM = "kenar"
    MIDDLE = "orta"
    BOTTOM = "dip"
    HANDLE_SIDE = "kulp_yani"
    OPPOSITE_HANDLE = "kulp_karsisi"
    SAUCER = "tabak"


# Traditional region conventions (they vary by region/family; documented as such).
REGION_MEANINGS: dict[Region, str] = {
    Region.RIM: "yakın zaman, şu anki gündem",
    Region.MIDDLE: "önümüzdeki haftalar",
    Region.BOTTOM: "kalp/dip: iç dünya, derindeki duygular",
    Region.HANDLE_SIDE: "kişinin kendisi, evi, yakın çevresi",
    Region.OPPOSITE_HANDLE: "dış dünya, uzaktakiler, gelecek kişiler",
    Region.SAUCER: "dilekler, evin ve kalbin hafiflemesi",
}

TONE_MEANINGS = {
    "acik": "telve ferah dağılmış: hafiflik, açık yollar",
    "dengeli": "telve dengeli: olağan, akışında bir dönem",
    "yogun": "telve yoğun: kalabalık gündem, düşünceli bir dönem",
}
