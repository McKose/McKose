"""Deterministic astrological context: daily sky snapshot and event calendar.

These structures are what the LLM is allowed to talk about. Everything here is
computed; the prompt layer only verbalises it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from app.astro.ephemeris import Ephemeris, LunarPhase, Planet, RetrogradePeriod
from app.astro.houses import house_theme, whole_sign_house
from app.astro.zodiac import Sign

# Traditional significations, used to build "do / don't" guidance deterministically.
RETRO_THEMES_TR: dict[Planet, str] = {
    Planet.MERCURY: "iletişim, sözleşmeler, teknoloji, ulaşım, yazışmalar",
    Planet.VENUS: "ilişkiler, eski sevgililer, para harcamaları, estetik kararlar",
    Planet.MARS: "enerji, motivasyon, çatışmalar, yeni girişimler",
    Planet.JUPITER: "büyüme planları, inançlar, eğitim, şans beklentileri",
    Planet.SATURN: "sorumluluklar, yapı, uzun vadeli taahhütler",
    Planet.URANUS: "ani değişimler, özgürlük ihtiyacı, sürprizler",
    Planet.NEPTUNE: "hayaller, sezgiler, belirsizlik, idealizasyon",
    Planet.PLUTO: "güç dengeleri, derin dönüşüm, kontrol konuları",
}

LUNATION_THEMES_TR: dict[LunarPhase, str] = {
    LunarPhase.NEW_MOON: "niyet koyma, yeni başlangıç, tohum ekme",
    LunarPhase.FIRST_QUARTER: "harekete geçme, engelleri aşma, karar",
    LunarPhase.FULL_MOON: "doruk, sonuç alma, farkındalık, bırakma",
    LunarPhase.LAST_QUARTER: "değerlendirme, temizlik, kapanış",
}

LUNATION_NAMES_TR = {
    LunarPhase.NEW_MOON: "Yeniay",
    LunarPhase.FIRST_QUARTER: "İlk Dördün",
    LunarPhase.FULL_MOON: "Dolunay",
    LunarPhase.LAST_QUARTER: "Son Dördün",
}


@dataclass
class PlanetInHouse:
    planet: str
    sign: str
    degree: float
    retrograde: bool
    house: int
    house_theme: str


@dataclass
class SkySnapshot:
    """Sky at local noon of ``day`` mapped onto a reference sign's solar houses."""

    day: date
    reference_sign: str
    moon_phase_deg: float
    moon_illumination: float
    planets: list[PlanetInHouse]
    ingresses_today: list[str] = field(default_factory=list)
    lunation_today: str | None = None


@dataclass
class CalendarEvent:
    kind: str  # "retro" | "lunation"
    title: str
    start: datetime
    end: datetime | None
    sign: str
    house: int | None
    house_theme: str | None
    themes: str
    detail: str


def sky_snapshot(eph: Ephemeris, day: date, reference: Sign, tz: str = "Europe/Istanbul") -> SkySnapshot:
    z = ZoneInfo(tz)
    noon = datetime.combine(day, time(12, 0), tzinfo=z)
    day_start = datetime.combine(day, time(0, 0), tzinfo=z)
    day_end = day_start + timedelta(days=1)

    start_pos, noon_pos, end_pos = eph.positions(day_start), eph.positions(noon), eph.positions(day_end)
    planets = [
        PlanetInHouse(
            planet=p.display,
            sign=pos.sign.display,
            degree=round(pos.degree_in_sign, 1),
            retrograde=pos.retrograde,
            house=whole_sign_house(reference, pos.sign),
            house_theme=house_theme(whole_sign_house(reference, pos.sign)),
        )
        for p, pos in noon_pos.items()
    ]
    ingresses = [f"{p.display} {end_pos[p].sign.display} burcuna geçiyor" for p in Planet if start_pos[p].sign != end_pos[p].sign]
    lunations = eph.lunations(day_start, day_end)
    elong, illum = eph.moon_phase_at(noon)
    return SkySnapshot(
        day=day,
        reference_sign=reference.display,
        moon_phase_deg=round(elong, 1),
        moon_illumination=round(illum, 3),
        planets=planets,
        ingresses_today=ingresses,
        lunation_today=(f"{LUNATION_NAMES_TR[lunations[0].phase]} {lunations[0].sign.display} burcunda" if lunations else None),
    )


def _retro_event(r: RetrogradePeriod, reference: Sign | None) -> CalendarEvent:
    house = whole_sign_house(reference, r.sign_start) if reference else None
    detail = (
        f"{r.planet.display}, {r.sign_start.display} {r.longitude_start % 30:.0f}° noktasında geri harekete başlar, "
        f"{r.sign_end.display} {r.longitude_end % 30:.0f}° noktasında düzelir."
    )
    if r.sign_start != r.sign_end:
        detail += f" Retro süresince {r.sign_end.display} burcuna geri döner"
        if reference:
            detail += f" ({whole_sign_house(reference, r.sign_end)}. ev konuları da etkilenir)"
        detail += "."
    return CalendarEvent(
        kind="retro",
        title=f"{r.planet.display} Retrosu",
        start=r.station_retrograde,
        end=r.station_direct,
        sign=r.sign_start.display,
        house=house,
        house_theme=house_theme(house) if house else None,
        themes=RETRO_THEMES_TR[r.planet],
        detail=detail,
    )


def calendar(
    eph: Ephemeris,
    start: datetime,
    end: datetime,
    reference: Sign | None = None,
    planets: list[Planet] | None = None,
    phases: list[LunarPhase] | None = None,
) -> list[CalendarEvent]:
    events = [_retro_event(r, reference) for r in eph.retrograde_periods(start, end, planets)]
    for lu in eph.lunations(start, end, phases or [LunarPhase.NEW_MOON, LunarPhase.FULL_MOON]):
        house = whole_sign_house(reference, lu.sign) if reference else None
        events.append(
            CalendarEvent(
                kind="lunation",
                title=f"{LUNATION_NAMES_TR[lu.phase]} — {lu.sign.display}",
                start=lu.moment,
                end=None,
                sign=lu.sign.display,
                house=house,
                house_theme=house_theme(house) if house else None,
                themes=LUNATION_THEMES_TR[lu.phase],
                detail=f"Ay {lu.sign.display} {lu.moon_longitude % 30:.0f}° noktasında.",
            )
        )
    return sorted(events, key=lambda e: e.start)
