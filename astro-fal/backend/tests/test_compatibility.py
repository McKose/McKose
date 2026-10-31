from datetime import date, time
from itertools import combinations_with_replacement

from app.astro.compatibility import chart_compatibility, pair_score, person_chart, sign_distance, sun_sign_compatibility
from app.astro.ephemeris import Ephemeris
from app.astro.zodiac import SIGNS, Sign


def test_symmetric_and_bounded():
    for a, b in combinations_with_replacement(SIGNS, 2):
        s1, s2 = pair_score(a, b), pair_score(b, a)
        assert s1.score == s2.score
        assert 0 <= s1.score <= 100


def test_score_depends_only_on_sign_distance():
    # Element, modality and polarity are all functions of the distance -> 7 distinct scores.
    by_distance: dict[int, set[int]] = {}
    for a, b in combinations_with_replacement(SIGNS, 2):
        by_distance.setdefault(sign_distance(a, b), set()).add(pair_score(a, b).score)
    assert sorted(by_distance) == list(range(7))
    assert all(len(v) == 1 for v in by_distance.values())


def test_traditional_ordering():
    trine = pair_score(Sign.ARIES, Sign.LEO).score
    sextile = pair_score(Sign.ARIES, Sign.GEMINI).score
    opposition = pair_score(Sign.ARIES, Sign.LIBRA).score
    square = pair_score(Sign.ARIES, Sign.CANCER).score
    quincunx = pair_score(Sign.ARIES, Sign.SCORPIO).score
    assert trine > sextile > opposition > quincunx >= square


def test_aries_scorpio_example():
    r = sun_sign_compatibility(Sign.ARIES, Sign.SCORPIO)
    assert r.sun_pair.aspect.startswith("yüz ellilik")
    assert "zorlayıcı" in r.sun_pair.element_relation


def test_chart_compatibility_dimensions():
    eph = Ephemeris()
    a = person_chart(eph, date(1992, 3, 28), time(9, 30), "Europe/Istanbul")
    b = person_chart(eph, date(1990, 11, 5), None, "Europe/Istanbul")
    assert a.sun == Sign.ARIES and b.sun == Sign.SCORPIO
    r = chart_compatibility(a, b)
    assert {d.name for d in r.dimensions} == {"temel_uyum", "duygusal", "iletisim", "tutku", "catisma_yonetimi"}
    assert 0 <= r.overall <= 100
    assert not a.moon_uncertain
