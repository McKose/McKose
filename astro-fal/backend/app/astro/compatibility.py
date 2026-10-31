"""Sign compatibility scoring.

Element, modality and polarity are not independent inputs: all three are fully
determined by the angular distance between two signs (0..6 signs apart). So a
sun-sign-only score has exactly 7 possible values. We keep the component
breakdown for transparency, and add multi-factor scoring (Moon, Mercury, Venus,
Mars) when birth dates are available, which is what actually differentiates
couples and maps onto the narrative dimensions (emotion, communication,
passion, conflict).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time
from zoneinfo import ZoneInfo

from app.astro.ephemeris import Ephemeris, Planet
from app.astro.zodiac import ELEMENT_NAMES_TR, MODALITY_NAMES_TR, Element, Sign

_COMPATIBLE_ELEMENTS = {frozenset({Element.FIRE, Element.AIR}), frozenset({Element.EARTH, Element.WATER})}

W_ELEMENT, W_MODALITY, W_POLARITY = 0.60, 0.25, 0.15

ASPECT_NAMES_TR = {
    0: "kavuşum (aynı burç)",
    1: "yarım altmışlık (komşu burç)",
    2: "altmışlık (sekstil)",
    3: "kare",
    4: "üçgen (trigon)",
    5: "yüz ellilik (quincunx)",
    6: "karşıt (opozisyon)",
}


def sign_distance(a: Sign, b: Sign) -> int:
    d = (b.index - a.index) % 12
    return min(d, 12 - d)


@dataclass(frozen=True)
class PairScore:
    a: str
    b: str
    distance: int
    aspect: str
    element_relation: str
    modality_relation: str
    element_score: float
    modality_score: float
    polarity_score: float
    score: int  # 0..100


def pair_score(a: Sign, b: Sign) -> PairScore:
    if a.element == b.element:
        e_rel, e = "aynı element", 1.0
    elif frozenset({a.element, b.element}) in _COMPATIBLE_ELEMENTS:
        e_rel, e = "tamamlayıcı elementler", 0.8
    else:
        e_rel, e = "zorlayıcı elementler", 0.3
    # Same modality = square/opposition/conjunction: rivalry over the same mode of action.
    if a.modality == b.modality:
        m_rel, m = "aynı nitelik", 0.4
    else:
        m_rel, m = "farklı nitelik", 0.7
    p = 1.0 if a.is_masculine == b.is_masculine else 0.3
    total = W_ELEMENT * e + W_MODALITY * m + W_POLARITY * p
    d = sign_distance(a, b)
    return PairScore(
        a=a.display,
        b=b.display,
        distance=d,
        aspect=ASPECT_NAMES_TR[d],
        element_relation=f"{e_rel} ({ELEMENT_NAMES_TR[a.element]}–{ELEMENT_NAMES_TR[b.element]})",
        modality_relation=f"{m_rel} ({MODALITY_NAMES_TR[a.modality]}–{MODALITY_NAMES_TR[b.modality]})",
        element_score=e,
        modality_score=m,
        polarity_score=p,
        score=round(total * 100),
    )


@dataclass(frozen=True)
class PersonChart:
    sun: Sign
    moon: Sign
    mercury: Sign
    venus: Sign
    mars: Sign
    moon_uncertain: bool


def person_chart(eph: Ephemeris, birth_date: date, birth_time: time | None, tz: str) -> PersonChart:
    moment = datetime.combine(birth_date, birth_time or time(12, 0), tzinfo=ZoneInfo(tz))
    pos = eph.positions(moment)
    return PersonChart(
        sun=pos[Planet.SUN].sign,
        moon=pos[Planet.MOON].sign,
        mercury=pos[Planet.MERCURY].sign,
        venus=pos[Planet.VENUS].sign,
        mars=pos[Planet.MARS].sign,
        moon_uncertain=birth_time is None and eph.moon_sign_is_ambiguous(birth_date, tz),
    )


@dataclass(frozen=True)
class DimensionScore:
    name: str
    score: int
    basis: str


@dataclass(frozen=True)
class CompatibilityResult:
    overall: int
    sun_pair: PairScore
    dimensions: list[DimensionScore]
    notes: list[str]


# (dimension, weight in overall)
_DIM_WEIGHTS = {"temel_uyum": 0.25, "duygusal": 0.20, "iletisim": 0.15, "tutku": 0.25, "catisma_yonetimi": 0.15}


def sun_sign_compatibility(a: Sign, b: Sign) -> CompatibilityResult:
    sp = pair_score(a, b)
    return CompatibilityResult(
        overall=sp.score,
        sun_pair=sp,
        dimensions=[DimensionScore("temel_uyum", sp.score, f"Güneş {sp.a}–{sp.b}: {sp.aspect}")],
        notes=["Sadece Güneş burcu kullanıldı; doğum tarihleri verilirse Ay, Merkür, Venüs ve Mars da hesaba katılır."],
    )


def chart_compatibility(a: PersonChart, b: PersonChart) -> CompatibilityResult:
    sun = pair_score(a.sun, b.sun)
    moon = pair_score(a.moon, b.moon)
    merc = pair_score(a.mercury, b.mercury)
    vm1, vm2 = pair_score(a.venus, b.mars), pair_score(a.mars, b.venus)
    mars = pair_score(a.mars, b.mars)
    dims = [
        DimensionScore("temel_uyum", sun.score, f"Güneş {sun.a}–{sun.b}: {sun.aspect}"),
        DimensionScore("duygusal", moon.score, f"Ay {moon.a}–{moon.b}: {moon.aspect}"),
        DimensionScore("iletisim", merc.score, f"Merkür {merc.a}–{merc.b}: {merc.aspect}"),
        DimensionScore(
            "tutku",
            round((vm1.score + vm2.score) / 2),
            f"Venüs {vm1.a}–Mars {vm1.b}: {vm1.aspect}; Mars {vm2.a}–Venüs {vm2.b}: {vm2.aspect}",
        ),
        DimensionScore("catisma_yonetimi", mars.score, f"Mars {mars.a}–{mars.b}: {mars.aspect}"),
    ]
    overall = round(sum(_DIM_WEIGHTS[d.name] * d.score for d in dims))
    notes = []
    if a.moon_uncertain or b.moon_uncertain:
        notes.append("Doğum saati bilinmediği için Ay burcu kesin değil; duygusal uyum skoru yaklaşık.")
    return CompatibilityResult(overall=overall, sun_pair=sun, dimensions=dims, notes=notes)
