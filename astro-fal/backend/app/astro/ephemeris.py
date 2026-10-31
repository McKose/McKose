"""Swiss Ephemeris wrapper: positions, retrograde stations, lunations, sun sign.

All astronomy is computed here, never by the LLM. Times are UTC internally.

Default mode is the built-in Moshier analytical ephemeris (no data files needed,
sub-arcsecond for planets, a few arcseconds for the Moon). That is far below the
precision any sign/house decision needs. Set ``SWISSEPH_PATH`` to use the .se1
files instead.

LICENSE NOTE: Swiss Ephemeris / pyswisseph are AGPL-3.0 unless a commercial
license is bought from Astrodienst. See docs/ARCHITECTURE.md §6.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from enum import Enum
from zoneinfo import ZoneInfo

import swisseph as swe

from app.astro.zodiac import Sign


class Planet(str, Enum):
    SUN = "gunes"
    MOON = "ay"
    MERCURY = "merkur"
    VENUS = "venus"
    MARS = "mars"
    JUPITER = "jupiter"
    SATURN = "saturn"
    URANUS = "uranus"
    NEPTUNE = "neptun"
    PLUTO = "pluton"

    @property
    def swe_id(self) -> int:
        return _SWE_IDS[self]

    @property
    def display(self) -> str:
        return PLANET_NAMES_TR[self]


_SWE_IDS = {
    Planet.SUN: swe.SUN,
    Planet.MOON: swe.MOON,
    Planet.MERCURY: swe.MERCURY,
    Planet.VENUS: swe.VENUS,
    Planet.MARS: swe.MARS,
    Planet.JUPITER: swe.JUPITER,
    Planet.SATURN: swe.SATURN,
    Planet.URANUS: swe.URANUS,
    Planet.NEPTUNE: swe.NEPTUNE,
    Planet.PLUTO: swe.PLUTO,
}

PLANET_NAMES_TR = {
    Planet.SUN: "Güneş",
    Planet.MOON: "Ay",
    Planet.MERCURY: "Merkür",
    Planet.VENUS: "Venüs",
    Planet.MARS: "Mars",
    Planet.JUPITER: "Jüpiter",
    Planet.SATURN: "Satürn",
    Planet.URANUS: "Uranüs",
    Planet.NEPTUNE: "Neptün",
    Planet.PLUTO: "Plüton",
}

# Sun and Moon never go retrograde (geocentric).
RETROGRADE_CAPABLE = [p for p in Planet if p not in (Planet.SUN, Planet.MOON)]


class LunarPhase(str, Enum):
    NEW_MOON = "yeniay"
    FIRST_QUARTER = "ilk_dordun"
    FULL_MOON = "dolunay"
    LAST_QUARTER = "son_dordun"


_PHASE_ANGLES = {
    LunarPhase.NEW_MOON: 0.0,
    LunarPhase.FIRST_QUARTER: 90.0,
    LunarPhase.FULL_MOON: 180.0,
    LunarPhase.LAST_QUARTER: 270.0,
}

# Sun moves ~0.9856 deg/day. Inside this margin of a cusp, a birth date without
# a birth time cannot decide the sign (±12 h of motion).
SUN_CUSP_MARGIN_DEG = 0.5
_BISECT_TOL_DAYS = 1.0 / 1440 / 4  # 15 s


@dataclass(frozen=True)
class PlanetPosition:
    planet: Planet
    longitude: float  # tropical ecliptic, degrees [0, 360)
    speed: float  # degrees/day; < 0 means retrograde

    @property
    def sign(self) -> Sign:
        return Sign.from_longitude(self.longitude)

    @property
    def degree_in_sign(self) -> float:
        return self.longitude % 30.0

    @property
    def retrograde(self) -> bool:
        return self.speed < 0


@dataclass(frozen=True)
class RetrogradePeriod:
    planet: Planet
    station_retrograde: datetime
    station_direct: datetime
    longitude_start: float
    longitude_end: float

    @property
    def sign_start(self) -> Sign:
        return Sign.from_longitude(self.longitude_start)

    @property
    def sign_end(self) -> Sign:
        return Sign.from_longitude(self.longitude_end)


@dataclass(frozen=True)
class Lunation:
    phase: LunarPhase
    moment: datetime
    moon_longitude: float

    @property
    def sign(self) -> Sign:
        return Sign.from_longitude(self.moon_longitude)


@dataclass(frozen=True)
class SunSignResult:
    sign: Sign
    sun_longitude: float
    cusp_ambiguous: bool  # True if birth time is unknown and the Sun is near a cusp
    alternative: Sign | None


class Ephemeris:
    def __init__(self, ephe_path: str | None = None) -> None:
        if ephe_path:
            swe.set_ephe_path(ephe_path)
            self._flags = swe.FLG_SWIEPH | swe.FLG_SPEED
        else:
            self._flags = swe.FLG_MOSEPH | swe.FLG_SPEED

    # ---- primitives -----------------------------------------------------

    @staticmethod
    def to_jd(moment: datetime) -> float:
        if moment.tzinfo is None:
            raise ValueError("datetime must be timezone-aware")
        u = moment.astimezone(UTC)
        hours = u.hour + u.minute / 60 + (u.second + u.microsecond / 1e6) / 3600
        return swe.julday(u.year, u.month, u.day, hours)

    @staticmethod
    def from_jd(jd: float) -> datetime:
        y, m, d, h = swe.revjul(jd)
        return (datetime(y, m, d, tzinfo=UTC) + timedelta(hours=h)).replace(microsecond=0)

    def position(self, planet: Planet, moment: datetime) -> PlanetPosition:
        return self._position_jd(planet, self.to_jd(moment))

    def _position_jd(self, planet: Planet, jd: float) -> PlanetPosition:
        xx, _ = swe.calc_ut(jd, planet.swe_id, self._flags)
        return PlanetPosition(planet=planet, longitude=xx[0] % 360.0, speed=xx[3])

    def positions(self, moment: datetime) -> dict[Planet, PlanetPosition]:
        jd = self.to_jd(moment)
        return {p: self._position_jd(p, jd) for p in Planet}

    # ---- sun sign -------------------------------------------------------

    def sun_sign(self, birth_date: date, birth_time: time | None, tz: str) -> SunSignResult:
        """Sun sign from the ephemeris, not from a fixed date table.

        Fixed tables are wrong for ~1-2 days around each cusp because ingress
        times drift by year; that is exactly where users notice errors.
        """
        local = datetime.combine(birth_date, birth_time or time(12, 0), tzinfo=ZoneInfo(tz))
        lon = self.position(Planet.SUN, local).longitude
        sign = Sign.from_longitude(lon)
        if birth_time is not None:
            return SunSignResult(sign, lon, False, None)
        deg = lon % 30.0
        if deg < SUN_CUSP_MARGIN_DEG:
            return SunSignResult(sign, lon, True, Sign.from_longitude(lon - 30.0))
        if deg > 30.0 - SUN_CUSP_MARGIN_DEG:
            return SunSignResult(sign, lon, True, Sign.from_longitude(lon + 30.0))
        return SunSignResult(sign, lon, False, None)

    def moon_sign_is_ambiguous(self, birth_date: date, tz: str) -> bool:
        """True if the Moon (12-15 deg/day) changes sign during the local birth day."""
        z = ZoneInfo(tz)
        start = datetime.combine(birth_date, time(0, 0), tzinfo=z)
        end = start + timedelta(days=1)
        return self.position(Planet.MOON, start).sign != self.position(Planet.MOON, end).sign

    def ascendant(self, moment: datetime, latitude: float, longitude: float) -> float:
        _, ascmc = swe.houses_ex(self.to_jd(moment), latitude, longitude, b"W")
        return ascmc[0] % 360.0

    # ---- event search ---------------------------------------------------

    @staticmethod
    def _bisect(f: Callable[[float], float], a: float, b: float) -> float:
        fa = f(a)
        while b - a > _BISECT_TOL_DAYS:
            m = (a + b) / 2
            fm = f(m)
            if (fm < 0) == (fa < 0):
                a, fa = m, fm
            else:
                b = m
        return (a + b) / 2

    def _stations(self, planet: Planet, jd_start: float, jd_end: float, step: float = 1.0) -> list[tuple[float, bool]]:
        """Zero crossings of longitudinal speed: (jd, True=turns retrograde)."""
        speed = lambda jd: self._position_jd(planet, jd).speed
        out: list[tuple[float, bool]] = []
        jd, prev = jd_start, speed(jd_start)
        while jd < jd_end:
            nxt_jd = min(jd + step, jd_end)
            nxt = speed(nxt_jd)
            if (prev < 0) != (nxt < 0):
                out.append((self._bisect(speed, jd, nxt_jd), nxt < 0))
            jd, prev = nxt_jd, nxt
        return out

    def retrograde_periods(self, start: datetime, end: datetime, planets: list[Planet] | None = None) -> list[RetrogradePeriod]:
        """Retrograde periods overlapping [start, end].

        Scans with a margin so periods that began before ``start`` or end after
        ``end`` are returned complete. Outer planets stay retrograde ~5 months,
        the longest gap between stations is ~13 months (Mars), hence 420 days.
        """
        margin = 420.0
        jd0, jd1 = self.to_jd(start), self.to_jd(end)
        result: list[RetrogradePeriod] = []
        for planet in planets or RETROGRADE_CAPABLE:
            stations = self._stations(planet, jd0 - margin, jd1 + margin)
            for i, (jd_sr, to_retro) in enumerate(stations):
                if not to_retro or i + 1 >= len(stations):
                    continue
                jd_sd = stations[i + 1][0]
                if jd_sd < jd0 or jd_sr > jd1:
                    continue
                result.append(
                    RetrogradePeriod(
                        planet=planet,
                        station_retrograde=self.from_jd(jd_sr),
                        station_direct=self.from_jd(jd_sd),
                        longitude_start=self._position_jd(planet, jd_sr).longitude,
                        longitude_end=self._position_jd(planet, jd_sd).longitude,
                    )
                )
        return sorted(result, key=lambda r: r.station_retrograde)

    def _elongation(self, jd: float) -> float:
        return (self._position_jd(Planet.MOON, jd).longitude - self._position_jd(Planet.SUN, jd).longitude) % 360.0

    def lunations(self, start: datetime, end: datetime, phases: list[LunarPhase] | None = None) -> list[Lunation]:
        """Exact moments of the main lunar phases within [start, end].

        Moon-Sun elongation grows ~12.2 deg/day, so a 1-day step can never skip
        a 90-degree phase boundary.
        """
        jd0, jd1 = self.to_jd(start), self.to_jd(end)
        result: list[Lunation] = []
        for phase in phases or list(LunarPhase):
            target = _PHASE_ANGLES[phase]
            # Signed distance to target in (-180, 180]; crosses - -> + at the phase.
            f = lambda jd, t=target: ((self._elongation(jd) - t + 180.0) % 360.0) - 180.0
            jd, prev = jd0, f(jd0)
            while jd < jd1:
                nxt_jd = min(jd + 1.0, jd1)
                nxt = f(nxt_jd)
                if prev < 0 <= nxt:
                    hit = self._bisect(f, jd, nxt_jd)
                    result.append(Lunation(phase, self.from_jd(hit), self._position_jd(Planet.MOON, hit).longitude))
                jd, prev = nxt_jd, nxt
        return sorted(result, key=lambda lu: lu.moment)

    def moon_phase_at(self, moment: datetime) -> tuple[float, float]:
        """(elongation degrees, illuminated fraction 0..1)."""
        e = self._elongation(self.to_jd(moment))
        return e, (1 - math.cos(math.radians(e))) / 2
