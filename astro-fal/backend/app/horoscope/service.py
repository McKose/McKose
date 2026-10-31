"""Narrative services: deterministic context in, cached LLM text out.

Cache keys never contain user identity for non-personal content, so a daily
horoscope is generated once per (day, sign, perspective) = 36 calls/day total,
independent of user count.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

from pydantic import BaseModel

from app.astro.compatibility import CompatibilityResult
from app.astro.ephemeris import Ephemeris, Planet
from app.astro.events import CalendarEvent, calendar, sky_snapshot
from app.astro.zodiac import Sign
from app.cache import TTLCache
from app.fortune.schemas import Gender
from app.horoscope import prompts as hp
from app.horoscope.prompts import Perspective
from app.llm.base import LLMClient, LLMError

DAY_TTL = 36 * 3600
EVENT_TTL = 30 * 24 * 3600


class DailyHoroscope(BaseModel):
    baslik: str
    paragraflar: list[str]
    yap: list[str]
    yapma: list[str]


class RetroGuide(BaseModel):
    ozet: list[str]
    yap: list[str]
    yapma: list[str]


class CompatibilityNarrative(BaseModel):
    iletisim: str
    tutku: str
    catisma: str
    tavsiye: str


class AstroNarrator:
    def __init__(self, eph: Ephemeris, llm: LLMClient, cache: TTLCache, tz: str = "Europe/Istanbul") -> None:
        self._eph = eph
        self._llm = llm
        self._cache = cache
        self._tz = tz

    async def _generate(self, model: type[BaseModel], **kwargs: Any) -> BaseModel:
        raw = await self._llm.complete_json(**kwargs)
        try:
            return model.model_validate(raw)
        except ValueError as exc:
            raise LLMError(f"{model.__name__} failed validation: {exc}") from exc

    async def daily(self, sign: Sign, day: date, perspective: Perspective) -> tuple[DailyHoroscope, dict]:
        snap = sky_snapshot(self._eph, day, sign, self._tz)
        key = ("daily", day.isoformat(), sign.value, perspective.value, self._llm.model_id, hp.PROMPT_VERSION)

        async def factory() -> BaseModel:
            return await self._generate(
                DailyHoroscope,
                system=hp.daily_system(perspective),
                user=hp.to_payload({"burc": sign.display, "tarih": day, "gokyuzu": snap}),
                schema_name="daily_horoscope",
                schema=hp.DAILY_SCHEMA,
                temperature=0.8,
            )

        text = await self._cache.get_or_create(key, factory, DAY_TTL)
        return text, {"sky": snap}

    def personal_calendar(self, sign: Sign | None, start: datetime, end: datetime) -> list[CalendarEvent]:
        return calendar(self._eph, start, end, reference=sign)

    async def retro_guide(
        self, sign: Sign, planet: Planet, around: datetime, perspective: Perspective
    ) -> tuple[RetroGuide, CalendarEvent]:
        events = [
            e
            for e in calendar(
                self._eph, around - timedelta(days=1), around + timedelta(days=400), sign, planets=[planet], phases=[]
            )
            if e.kind == "retro"
        ]
        if not events:
            raise LookupError(f"{planet.display} için yakın tarihte retro bulunamadı")
        event = events[0]
        key = (
            "retro",
            planet.value,
            event.start.date().isoformat(),
            sign.value,
            perspective.value,
            self._llm.model_id,
            hp.PROMPT_VERSION,
        )

        async def factory() -> BaseModel:
            return await self._generate(
                RetroGuide,
                system=hp.retro_system(perspective),
                user=hp.to_payload({"burc": sign.display, "olay": event}),
                schema_name="retro_guide",
                schema=hp.RETRO_SCHEMA,
                temperature=0.7,
            )

        return await self._cache.get_or_create(key, factory, EVENT_TTL), event

    async def compatibility(
        self,
        result: CompatibilityResult,
        gender_a: Gender,
        gender_b: Gender,
        cacheable: bool,
    ) -> CompatibilityNarrative:
        def label(sign_name: str, g: Gender) -> str:
            return {Gender.FEMALE: f"{sign_name} kadını", Gender.MALE: f"{sign_name} erkeği"}.get(g, sign_name)

        payload = {
            "kisi_a": label(result.sun_pair.a, gender_a),
            "kisi_b": label(result.sun_pair.b, gender_b),
            "genel_skor": result.overall,
            "boyutlar": result.dimensions,
            "gunes_uyumu": result.sun_pair,
            "notlar": result.notes,
        }

        async def factory() -> BaseModel:
            return await self._generate(
                CompatibilityNarrative,
                system=hp.compatibility_system(),
                user=hp.to_payload(payload),
                schema_name="compatibility",
                schema=hp.COMPAT_SCHEMA,
                temperature=0.8,
            )

        if not cacheable:
            return await factory()
        # Sun-sign-only results are a 12x12xgender matrix: generate once, reuse forever.
        key = (
            "compat",
            result.sun_pair.a,
            gender_a.value,
            result.sun_pair.b,
            gender_b.value,
            self._llm.model_id,
            hp.PROMPT_VERSION,
        )
        return await self._cache.get_or_create(key, factory, EVENT_TTL)
