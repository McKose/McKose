"""Provider-agnostic LLM interface. Every call returns schema-validated JSON."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class ImageInput:
    data: bytes
    mime_type: str = "image/jpeg"


class LLMError(RuntimeError):
    pass


class LLMClient(Protocol):
    model_id: str

    async def complete_json(
        self,
        *,
        system: str,
        user: str,
        schema_name: str,
        schema: dict[str, Any],
        images: list[ImageInput] | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1200,
    ) -> dict[str, Any]: ...
