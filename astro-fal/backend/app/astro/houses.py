"""House mapping. Deterministic: the LLM receives the house, it never computes it.

Without birth time/place we use *solar houses* (whole-sign houses counted from
the Sun sign), the standard basis of sun-sign horoscopes. With birth time and
place we use whole-sign houses from the rising sign, which is more personal.
"""

from __future__ import annotations

from app.astro.zodiac import HOUSE_THEMES_TR, Sign


def whole_sign_house(reference: Sign, target: Sign) -> int:
    """House (1..12) that ``target`` occupies when ``reference`` is the 1st house."""
    return (target.index - reference.index) % 12 + 1


def house_theme(house: int) -> str:
    return HOUSE_THEMES_TR[house]
