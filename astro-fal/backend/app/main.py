"""App factory. Run with: uvicorn app.main:create_app --factory"""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.routes import router
from app.astro.ephemeris import Ephemeris
from app.cache import TTLCache
from app.config import Settings, get_settings
from app.fortune.imaging import ImageRejected
from app.fortune.pipeline import FortunePipeline, FortuneRejected
from app.horoscope.service import AstroNarrator
from app.llm.base import LLMClient, LLMError
from app.llm.fake import FakeLLM
from app.llm.openai_compat import OpenAICompatClient

log = logging.getLogger(__name__)


def build_llms(settings: Settings) -> tuple[LLMClient, LLMClient]:
    base_url, vision_model, text_model = settings.resolved()
    if settings.llm_provider == "fake":
        return FakeLLM("fake-vision"), FakeLLM("fake-text")
    if not settings.llm_api_key:
        raise RuntimeError("LLM_API_KEY is required unless LLM_PROVIDER=fake")

    def mk(model: str) -> OpenAICompatClient:
        return OpenAICompatClient(
            api_key=settings.llm_api_key, model_id=model, base_url=base_url, timeout_s=settings.llm_timeout_s
        )

    return mk(vision_model), mk(text_model)


def create_app(settings: Settings | None = None, vision: LLMClient | None = None, text: LLMClient | None = None) -> FastAPI:
    settings = settings or get_settings()
    if vision is None or text is None:
        vision, text = build_llms(settings)

    app = FastAPI(title="Astro-Fal API", version="0.1.0")
    app.state.settings = settings
    app.state.ephemeris = Ephemeris(settings.swisseph_path)
    app.state.narrator = AstroNarrator(app.state.ephemeris, text, TTLCache(), settings.default_tz)
    app.state.fortune = FortunePipeline(vision, text)
    app.include_router(router)

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok", "llm_provider": settings.llm_provider}

    @app.exception_handler(FortuneRejected)
    @app.exception_handler(ImageRejected)
    async def rejected(_: Request, exc: FortuneRejected | ImageRejected) -> JSONResponse:
        return JSONResponse(status_code=422, content={"code": exc.code, "message": exc.message_tr})

    @app.exception_handler(LLMError)
    async def llm_failed(_: Request, exc: LLMError) -> JSONResponse:
        log.error("LLM failure: %s", exc)
        return JSONResponse(
            status_code=502,
            content={"code": "llm_unavailable", "message": "Yorum şu an oluşturulamadı, lütfen biraz sonra tekrar dene."},
        )

    return app
