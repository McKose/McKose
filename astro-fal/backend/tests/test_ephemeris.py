"""Ephemeris checks against independently published 2024 event times (UTC)."""

from datetime import UTC, date, datetime, time, timedelta
from itertools import pairwise

import pytest

from app.astro.ephemeris import Ephemeris, LunarPhase, Planet
from app.astro.houses import whole_sign_house
from app.astro.zodiac import Sign


@pytest.fixture(scope="module")
def eph() -> Ephemeris:
    return Ephemeris()


def close(a: datetime, b: datetime, minutes: float) -> bool:
    return abs((a - b).total_seconds()) <= minutes * 60


def test_mercury_retrograde_april_2024(eph):
    # Published: SR 2024-04-01 22:14 UTC @ 27°13' Aries, SD 2024-04-25 12:54 UTC @ 15°58' Aries
    periods = eph.retrograde_periods(datetime(2024, 4, 10, tzinfo=UTC), datetime(2024, 4, 11, tzinfo=UTC), [Planet.MERCURY])
    assert len(periods) == 1
    r = periods[0]
    assert close(r.station_retrograde, datetime(2024, 4, 1, 22, 14, tzinfo=UTC), 3)
    assert close(r.station_direct, datetime(2024, 4, 25, 12, 54, tzinfo=UTC), 3)
    assert r.sign_start == r.sign_end == Sign.ARIES
    assert r.longitude_start == pytest.approx(27 + 13 / 60, abs=0.02)


def test_mercury_retrograde_spanning_two_signs(eph):
    # Published: SR 2024-08-05 04:56 UTC @ 4°06' Virgo -> SD 2024-08-28 21:14 UTC @ 21°24' Leo
    (r,) = eph.retrograde_periods(datetime(2024, 8, 10, tzinfo=UTC), datetime(2024, 8, 11, tzinfo=UTC), [Planet.MERCURY])
    assert close(r.station_retrograde, datetime(2024, 8, 5, 4, 56, tzinfo=UTC), 3)
    assert close(r.station_direct, datetime(2024, 8, 28, 21, 14, tzinfo=UTC), 3)
    assert (r.sign_start, r.sign_end) == (Sign.VIRGO, Sign.LEO)


def test_period_started_before_window_is_returned_complete(eph):
    # Window fully inside the retrograde; stations lie outside it.
    (r,) = eph.retrograde_periods(datetime(2024, 4, 15, tzinfo=UTC), datetime(2024, 4, 16, tzinfo=UTC), [Planet.MERCURY])
    assert r.station_retrograde.month == 4 and r.station_retrograde.day == 1


def test_sun_and_moon_never_retrograde(eph):
    t0 = datetime(2024, 1, 1, tzinfo=UTC)
    for d in range(0, 366, 7):
        pos = eph.positions(t0 + timedelta(days=d))
        assert not pos[Planet.SUN].retrograde
        assert not pos[Planet.MOON].retrograde


def test_mercury_retrograde_count_per_year(eph):
    rs = eph.retrograde_periods(datetime(2024, 1, 1, tzinfo=UTC), datetime(2024, 12, 31, tzinfo=UTC), [Planet.MERCURY])
    # 2024: Dec-2023/Jan, Apr, Aug, Nov-Dec  -> 4 periods overlapping the year
    assert len(rs) == 4


def test_lunations_april_2024(eph):
    lus = eph.lunations(
        datetime(2024, 4, 1, tzinfo=UTC), datetime(2024, 4, 30, tzinfo=UTC), [LunarPhase.NEW_MOON, LunarPhase.FULL_MOON]
    )
    assert [lu.phase for lu in lus] == [LunarPhase.NEW_MOON, LunarPhase.FULL_MOON]
    new, full = lus
    assert close(new.moment, datetime(2024, 4, 8, 18, 21, tzinfo=UTC), 2)  # total solar eclipse day
    assert new.sign == Sign.ARIES
    assert close(full.moment, datetime(2024, 4, 23, 23, 49, tzinfo=UTC), 2)
    assert full.sign == Sign.SCORPIO


def test_lunation_cadence(eph):
    lus = eph.lunations(datetime(2024, 1, 1, tzinfo=UTC), datetime(2025, 1, 1, tzinfo=UTC))
    # ~49.5 main phases per year; consecutive phases 6.5-8.5 days apart, in cyclic order
    assert 48 <= len(lus) <= 51
    order = list(LunarPhase)
    for a, b in pairwise(lus):
        gap = (b.moment - a.moment).total_seconds() / 86400
        assert 6.5 < gap < 8.5
        assert order.index(b.phase) == (order.index(a.phase) + 1) % 4


def test_sun_sign_cusp_handling(eph):
    # June solstice 2024 = 20 Jun 20:51 UTC = 23:51 Istanbul: Sun enters Cancer.
    assert eph.sun_sign(date(2024, 6, 20), time(23, 0), "Europe/Istanbul").sign == Sign.GEMINI
    assert eph.sun_sign(date(2024, 6, 20), time(23, 59), "Europe/Istanbul").sign == Sign.CANCER
    no_time = eph.sun_sign(date(2024, 6, 20), None, "Europe/Istanbul")
    assert no_time.cusp_ambiguous and {no_time.sign, no_time.alternative} == {Sign.GEMINI, Sign.CANCER}
    mid = eph.sun_sign(date(1990, 7, 15), None, "Europe/Istanbul")
    assert mid.sign == Sign.CANCER and not mid.cusp_ambiguous


def test_historical_timezone_is_applied(eph):
    # Istanbul was UTC+2 in winter 1985 (EET), today it is UTC+3. A 1 h error flips the
    # sign for anyone born within an hour of an ingress.
    from zoneinfo import ZoneInfo

    ist = ZoneInfo("Europe/Istanbul")
    assert datetime(1985, 1, 20, 12, tzinfo=ist).utcoffset() == timedelta(hours=2)
    f = lambda jd: ((eph._position_jd(Planet.SUN, jd).longitude - 300.0 + 180) % 360) - 180
    j0 = eph.to_jd(datetime(1985, 1, 19, tzinfo=UTC))
    ingress_utc = eph.from_jd(eph._bisect(f, j0, j0 + 3))  # Sun enters Aquarius (300°)
    for delta_min, expected in ((-30, Sign.CAPRICORN), (30, Sign.AQUARIUS)):
        local = (ingress_utc + timedelta(hours=2, minutes=delta_min)).replace(tzinfo=None)
        assert eph.sun_sign(local.date(), local.time(), "Europe/Istanbul").sign == expected


def test_whole_sign_house():
    assert whole_sign_house(Sign.ARIES, Sign.ARIES) == 1
    assert whole_sign_house(Sign.ARIES, Sign.LIBRA) == 7
    assert whole_sign_house(Sign.CANCER, Sign.ARIES) == 10
    assert whole_sign_house(Sign.PISCES, Sign.ARIES) == 2


def test_naive_datetime_rejected(eph):
    with pytest.raises(ValueError):
        eph.position(Planet.SUN, datetime(2024, 1, 1))
