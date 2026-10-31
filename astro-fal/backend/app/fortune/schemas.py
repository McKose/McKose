"""Stage-1 / stage-2 contracts: JSON schemas sent to the model + Pydantic validators.

Schemas stay inside the strict structured-output subset (every property
required, additionalProperties false, no numeric bounds); bounds are enforced
by Pydantic after the call.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.fortune.symbols import SYMBOL_IDS, SYMBOLS, Region


class Gender(str, Enum):
    FEMALE = "kadin"
    MALE = "erkek"
    UNSPECIFIED = "belirtilmedi"


class RelationshipStatus(str, Enum):
    SINGLE = "bekar"
    DATING = "iliskisi_var"
    ENGAGED = "nisanli"
    MARRIED = "evli"
    COMPLICATED = "karisik"
    UNSPECIFIED = "belirtilmedi"


class Focus(str, Enum):
    GENERAL = "genel"
    LOVE = "ask"
    CAREER = "kariyer"
    MONEY = "para"


class Size(str, Enum):
    SMALL = "kucuk"
    MEDIUM = "orta"
    LARGE = "buyuk"


class Quality(str, Enum):
    GOOD = "iyi"
    FAIR = "orta"
    POOR = "kotu"


class DominantTone(str, Enum):
    LIGHT = "acik"
    BALANCED = "dengeli"
    DENSE = "yogun"


class DetectedSymbol(BaseModel):
    sembol: str = Field(json_schema_extra={"enum": SYMBOL_IDS})
    bolge: Region
    fotograf: int = Field(ge=1, le=3)
    boyut: Size
    guven: float = Field(ge=0.0, le=1.0)
    detay: str | None = None  # e.g. the letter for "harf", the number for "rakam"

    @field_validator("sembol")
    @classmethod
    def _known_symbol(cls, v: str) -> str:
        if v not in SYMBOLS:
            raise ValueError(f"unknown symbol id: {v}")
        return v


class SymbolExtraction(BaseModel):
    fincan_gecerli: bool
    red_nedeni: str | None
    gorsel_kalitesi: Quality
    baskin_ton: DominantTone
    semboller: list[DetectedSymbol]


class Reading(BaseModel):
    paragraflar: list[str]
    kullanilan_semboller: list[str]


def _enum(values: list[str]) -> dict[str, Any]:
    return {"type": "string", "enum": values}


def _nullable_str() -> dict[str, Any]:
    return {"type": ["string", "null"]}


SYMBOL_EXTRACTION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["fincan_gecerli", "red_nedeni", "gorsel_kalitesi", "baskin_ton", "semboller"],
    "properties": {
        "fincan_gecerli": {"type": "boolean"},
        "red_nedeni": _nullable_str(),
        "gorsel_kalitesi": _enum([q.value for q in Quality]),
        "baskin_ton": _enum([t.value for t in DominantTone]),
        "semboller": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["sembol", "bolge", "fotograf", "boyut", "guven", "detay"],
                "properties": {
                    "sembol": _enum(SYMBOL_IDS),
                    "bolge": _enum([r.value for r in Region]),
                    "fotograf": {"type": "integer"},
                    "boyut": _enum([s.value for s in Size]),
                    "guven": {"type": "number"},
                    "detay": _nullable_str(),
                },
            },
        },
    },
}


def reading_schema(allowed_symbols: list[str]) -> dict[str, Any]:
    """Stage-2 schema; ``kullanilan_semboller`` is restricted to what stage 1 saw."""
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["paragraflar", "kullanilan_semboller"],
        "properties": {
            "paragraflar": {"type": "array", "items": {"type": "string"}},
            "kullanilan_semboller": {"type": "array", "items": _enum(allowed_symbols)},
        },
    }
