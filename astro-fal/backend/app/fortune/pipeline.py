"""Two-stage coffee reading chain.

    photos ─► image gate ─► [stage 1: vision → closed-vocabulary symbols JSON]
           ─► deterministic filter ─► [stage 2: text model → 3-paragraph reading]
           ─► validators (structure, symbol subset, hallucination guard) ─► 1 retry

Stage 1 and stage 2 can use different models: vision quality matters in
stage 1, latency/cost and Turkish prose quality in stage 2.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field

from pydantic import ValidationError

from app.fortune import prompts
from app.fortune.imaging import prepare_image
from app.fortune.schemas import (
    SYMBOL_EXTRACTION_SCHEMA,
    DetectedSymbol,
    Reading,
    SymbolExtraction,
    reading_schema,
)
from app.fortune.symbols import SYMBOLS
from app.llm.base import ImageInput, LLMClient, LLMError

log = logging.getLogger(__name__)

MIN_CONFIDENCE = 0.5
MIN_SYMBOLS = 2
MAX_SYMBOLS = 7
PARAGRAPHS = 3
MIN_WORDS, MAX_WORDS = 40, 160
_SIZE_WEIGHT = {"kucuk": 0.8, "orta": 1.0, "buyuk": 1.2}


class FortuneRejected(Exception):
    def __init__(self, code: str, message_tr: str) -> None:
        super().__init__(code)
        self.code = code
        self.message_tr = message_tr


@dataclass
class FortuneResult:
    paragraphs: list[str]
    symbols: list[DetectedSymbol]
    used_symbols: list[str]
    dominant_tone: str
    vision_model: str
    text_model: str
    prompt_version: str = prompts.PROMPT_VERSION
    warnings: list[str] = field(default_factory=list)


def tr_lower(text: str) -> str:
    return text.replace("I", "ı").replace("İ", "i").lower()


def select_symbols(extraction: SymbolExtraction) -> list[DetectedSymbol]:
    """Drop low-confidence detections, dedupe by id, keep the strongest few."""
    best: dict[str, DetectedSymbol] = {}
    for s in extraction.semboller:
        if s.guven < MIN_CONFIDENCE:
            continue
        cur = best.get(s.sembol)
        if cur is None or s.guven * _SIZE_WEIGHT[s.boyut.value] > cur.guven * _SIZE_WEIGHT[cur.boyut.value]:
            best[s.sembol] = s
    ranked = sorted(best.values(), key=lambda s: s.guven * _SIZE_WEIGHT[s.boyut.value], reverse=True)
    return ranked[:MAX_SYMBOLS]


def hallucinated_symbols(text: str, allowed: set[str]) -> list[str]:
    """Lexicon symbols mentioned in ``text`` that stage 1 did not detect.

    Best-effort: only symbols with distinctive check terms are scanned, and a
    mention immediately followed by "burç" (e.g. "Balık burcu") is ignored.
    """
    low = tr_lower(text)
    found = []
    for sid, sym in SYMBOLS.items():
        if sid in allowed or not sym.check_terms:
            continue
        for term in sym.check_terms:
            if re.search(rf"(?<!\w)(?:{term})(?!\s+burc)", low):
                found.append(sid)
                break
    return found


def validate_reading(reading: Reading, allowed: set[str]) -> tuple[list[str], list[str]]:
    """Returns (hard_errors, soft_errors). Hard errors block delivery after the retry."""
    hard, soft = [], []
    if len(reading.paragraflar) != PARAGRAPHS:
        hard.append(f"tam {PARAGRAPHS} paragraf olmalı, {len(reading.paragraflar)} geldi")
    for i, p in enumerate(reading.paragraflar, 1):
        n = len(p.split())
        if not MIN_WORDS <= n <= MAX_WORDS:
            hard.append(f"{i}. paragraf {n} kelime; {MIN_WORDS}-{MAX_WORDS} arası olmalı")
    extra = set(reading.kullanilan_semboller) - allowed
    if extra:
        hard.append(f"listede olmayan semboller kullanıldı: {sorted(extra)}")
    if len(set(reading.kullanilan_semboller) & allowed) < min(MIN_SYMBOLS, len(allowed)):
        soft.append(f"en az {MIN_SYMBOLS} tespit edilen sembole değinilmeli")
    ghost = hallucinated_symbols(" ".join(reading.paragraflar), allowed)
    if ghost:
        soft.append(f"fincanda olmayan sembollerden bahsedildi: {', '.join(SYMBOLS[g].name for g in ghost)}")
    return hard, soft


class FortunePipeline:
    def __init__(self, vision: LLMClient, text: LLMClient) -> None:
        self._vision = vision
        self._text = text

    async def extract(self, photos: list[bytes]) -> SymbolExtraction:
        images = [ImageInput(prepare_image(p).data) for p in photos]
        raw = await self._vision.complete_json(
            system=prompts.STAGE1_SYSTEM,
            user=prompts.stage1_user(),
            schema_name="coffee_symbols",
            schema=SYMBOL_EXTRACTION_SCHEMA,
            images=images,
            temperature=0.2,
            max_tokens=800,
        )
        try:
            return SymbolExtraction.model_validate(raw)
        except ValidationError as exc:
            raise LLMError(f"stage 1 output failed validation: {exc}") from exc

    async def run(self, photos: list[bytes], profile: dict) -> FortuneResult:
        if len(photos) != 3:
            raise FortuneRejected("photo_count", "Lütfen fincanın iki tarafından ve tabaktan toplam 3 fotoğraf yükle.")

        extraction = await self.extract(photos)
        if not extraction.fincan_gecerli:
            raise FortuneRejected(
                "not_a_cup",
                f"Fotoğraflarda telveli bir fincan göremedim. {extraction.red_nedeni or ''}".strip(),
            )
        symbols = select_symbols(extraction)
        if len(symbols) < MIN_SYMBOLS:
            raise FortuneRejected(
                "too_few_symbols",
                "Telvedeki şekiller seçilemedi. Fincanı tamamen soğumuş halde, gün ışığında tekrar çek.",
            )

        allowed = {s.sembol for s in symbols}
        sym_dicts = [s.model_dump(mode="json") for s in symbols]
        feedback: str | None = None
        # Best deliverable so far: structurally valid (no hard errors), possibly with soft warnings.
        reading: Reading | None = None
        soft: list[str] = []
        for attempt in range(2):
            raw = await self._text.complete_json(
                system=prompts.STAGE2_SYSTEM,
                user=prompts.stage2_user(profile, sym_dicts, extraction.baskin_ton.value, feedback),
                schema_name="coffee_reading",
                schema=reading_schema(sorted(allowed)),
                temperature=0.85,
                max_tokens=1500,
            )
            try:
                candidate = Reading.model_validate(raw)
            except ValidationError as exc:
                feedback = "çıktı şemaya uymuyor"
                log.warning("stage 2 schema failure (attempt %d): %s", attempt, exc)
                continue
            hard, cand_soft = validate_reading(candidate, allowed)
            if not hard and (reading is None or len(cand_soft) <= len(soft)):
                reading, soft = candidate, cand_soft
            if not hard and not cand_soft:
                break
            feedback = "; ".join(hard + cand_soft)
            log.warning("stage 2 validation (attempt %d): %s", attempt, feedback)

        if reading is None:
            raise LLMError(f"stage 2 produced no structurally valid reading: {feedback}")
        return FortuneResult(
            paragraphs=reading.paragraflar,
            symbols=symbols,
            used_symbols=[s for s in reading.kullanilan_semboller if s in allowed],
            dominant_tone=extraction.baskin_ton.value,
            vision_model=self._vision.model_id,
            text_model=self._text.model_id,
            warnings=soft,
        )
