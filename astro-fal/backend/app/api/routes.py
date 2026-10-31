from __future__ import annotations

from dataclasses import asdict
from datetime import UTC, date, datetime, time, timedelta
from typing import Annotated
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from pydantic import BaseModel, field_validator, model_validator

from app.astro.compatibility import chart_compatibility, person_chart, sun_sign_compatibility
from app.astro.ephemeris import Ephemeris, Planet
from app.astro.events import sky_snapshot
from app.astro.zodiac import Sign
from app.fortune.imaging import MAX_UPLOAD_BYTES
from app.fortune.pipeline import FortunePipeline
from app.fortune.schemas import Focus, Gender, RelationshipStatus
from app.horoscope.prompts import Perspective, default_perspective
from app.horoscope.service import AstroNarrator

router = APIRouter(prefix="/v1")
MAX_CALENDAR_DAYS = 400


def eph(request: Request) -> Ephemeris:
    return request.app.state.ephemeris


def narrator(request: Request) -> AstroNarrator:
    return request.app.state.narrator


def pipeline(request: Request) -> FortunePipeline:
    return request.app.state.fortune


def _check_tz(tz: str) -> str:
    try:
        ZoneInfo(tz)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise ValueError(f"unknown IANA timezone: {tz}") from exc
    return tz


# ---- astro (pure computation, no LLM) ---------------------------------------


@router.get("/astro/sun-sign")
def sun_sign(
    e: Annotated[Ephemeris, Depends(eph)],
    birth_date: date,
    birth_time: time | None = None,
    tz: str = "Europe/Istanbul",
):
    try:
        _check_tz(tz)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    r = e.sun_sign(birth_date, birth_time, tz)
    return {
        "sign": r.sign.value,
        "sign_name": r.sign.display,
        "sun_longitude": round(r.sun_longitude, 4),
        "cusp_ambiguous": r.cusp_ambiguous,
        "alternative": r.alternative.value if r.alternative else None,
        "message": "Güneş burç sınırında; kesin sonuç için doğum saatini girin." if r.cusp_ambiguous else None,
    }


@router.get("/astro/sky")
def sky(e: Annotated[Ephemeris, Depends(eph)], sign: Sign, day: date | None = None, tz: str = "Europe/Istanbul"):
    return asdict(sky_snapshot(e, day or datetime.now(ZoneInfo(tz)).date(), sign, tz))


@router.get("/astro/calendar")
def astro_calendar(
    n: Annotated[AstroNarrator, Depends(narrator)],
    start: date,
    end: date,
    sign: Sign | None = None,
):
    if end < start or (end - start).days > MAX_CALENDAR_DAYS:
        raise HTTPException(422, f"range must be 0..{MAX_CALENDAR_DAYS} days")
    s = datetime.combine(start, time(0), tzinfo=UTC)
    t = datetime.combine(end, time(0), tzinfo=UTC) + timedelta(days=1)
    return [asdict(ev) for ev in n.personal_calendar(sign, s, t)]


# ---- narratives (LLM) -------------------------------------------------------


class PerspectiveMixin(BaseModel):
    gender: Gender = Gender.UNSPECIFIED
    perspective: Perspective | None = None  # overrides the gender default

    def resolved_perspective(self) -> Perspective:
        return self.perspective or default_perspective(self.gender)


class DailyRequest(PerspectiveMixin):
    sign: Sign
    day: date | None = None


@router.post("/horoscope/daily")
async def daily(req: DailyRequest, request: Request, n: Annotated[AstroNarrator, Depends(narrator)]):
    day = req.day or datetime.now(ZoneInfo(request.app.state.settings.default_tz)).date()
    text, ctx = await n.daily(req.sign, day, req.resolved_perspective())
    return {
        "sign": req.sign.value,
        "day": day,
        "perspective": req.resolved_perspective(),
        "horoscope": text,
        "sky": asdict(ctx["sky"]),
    }


class RetroRequest(PerspectiveMixin):
    sign: Sign
    planet: Planet = Planet.MERCURY
    around: datetime | None = None


@router.post("/astro/retro-guide")
async def retro_guide(req: RetroRequest, n: Annotated[AstroNarrator, Depends(narrator)]):
    around = req.around or datetime.now(UTC)
    if around.tzinfo is None:
        around = around.replace(tzinfo=UTC)
    try:
        guide, event = await n.retro_guide(req.sign, req.planet, around, req.resolved_perspective())
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    return {"event": asdict(event), "guide": guide}


class Person(BaseModel):
    gender: Gender = Gender.UNSPECIFIED
    sign: Sign | None = None
    birth_date: date | None = None
    birth_time: time | None = None
    tz: str = "Europe/Istanbul"

    @field_validator("tz")
    @classmethod
    def _valid_tz(cls, v: str) -> str:
        return _check_tz(v)

    @model_validator(mode="after")
    def _need_sign_or_date(self) -> Person:
        if self.sign is None and self.birth_date is None:
            raise ValueError("either sign or birth_date is required")
        return self


class CompatibilityRequest(BaseModel):
    a: Person
    b: Person
    narrate: bool = True


@router.post("/compatibility")
async def compatibility(
    req: CompatibilityRequest,
    e: Annotated[Ephemeris, Depends(eph)],
    n: Annotated[AstroNarrator, Depends(narrator)],
):
    detailed = req.a.birth_date is not None and req.b.birth_date is not None
    if detailed:
        ca = person_chart(e, req.a.birth_date, req.a.birth_time, req.a.tz)
        cb = person_chart(e, req.b.birth_date, req.b.birth_time, req.b.tz)
        result = chart_compatibility(ca, cb)
    else:
        sa = req.a.sign or e.sun_sign(req.a.birth_date, req.a.birth_time, req.a.tz).sign
        sb = req.b.sign or e.sun_sign(req.b.birth_date, req.b.birth_time, req.b.tz).sign
        result = sun_sign_compatibility(sa, sb)
    body = {"mode": "chart" if detailed else "sun_sign", "result": asdict(result)}
    if req.narrate:
        body["narrative"] = await n.compatibility(result, req.a.gender, req.b.gender, cacheable=not detailed)
    return body


# ---- coffee reading ---------------------------------------------------------


@router.post("/fortune/coffee")
async def coffee(
    p: Annotated[FortunePipeline, Depends(pipeline)],
    photos: Annotated[list[UploadFile], File(description="1: kulp tarafı, 2: kulp karşısı, 3: tabak")],
    focus: Annotated[Focus, Form()] = Focus.GENERAL,
    gender: Annotated[Gender, Form()] = Gender.UNSPECIFIED,
    relationship: Annotated[RelationshipStatus, Form()] = RelationshipStatus.UNSPECIFIED,
    sign: Annotated[Sign | None, Form()] = None,
    age: Annotated[int | None, Form(ge=18, le=120)] = None,
    name: Annotated[str | None, Form(max_length=40)] = None,
):
    # Read at most limit+1 bytes so oversize files are rejected without buffering them fully.
    raws = [await f.read(MAX_UPLOAD_BYTES + 1) for f in photos]
    profile = {
        "focus": focus.value,
        "gender": gender.value,
        "relationship": relationship.value,
        "sign": sign.display if sign else None,
        "age": age,
        "name": name,
    }
    r = await p.run(raws, profile)
    return {
        "paragraphs": r.paragraphs,
        "symbols": [s.model_dump(mode="json") for s in r.symbols],
        "used_symbols": r.used_symbols,
        "dominant_tone": r.dominant_tone,
        "meta": {
            "vision_model": r.vision_model,
            "text_model": r.text_model,
            "prompt_version": r.prompt_version,
            "warnings": r.warnings,
        },
        "disclaimer": "Bu yorum eğlence amaçlıdır; sağlık, hukuk veya finans kararlarında dayanak alınmamalıdır.",
    }
