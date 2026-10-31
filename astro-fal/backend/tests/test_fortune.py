import asyncio
import io

import pytest
from PIL import Image

from app.fortune.imaging import ImageRejected, prepare_image
from app.fortune.pipeline import FortunePipeline, FortuneRejected, hallucinated_symbols, select_symbols, validate_reading
from app.fortune.schemas import SYMBOL_EXTRACTION_SCHEMA, Reading, SymbolExtraction
from app.fortune.symbols import SYMBOL_IDS
from app.llm.base import LLMError
from app.llm.fake import FakeLLM
from tests.conftest import make_photo

PROFILE = {"focus": "kariyer", "gender": "kadin", "relationship": "bekar", "sign": "Yengeç", "age": 29, "name": None}
GOOD_P = "Fincanında belirgin bir kuş görüyorum ve bu sana yakında güzel bir haber geleceğini söylüyor. " * 4


def run(coro):
    return asyncio.run(coro)


# ---- image gate -------------------------------------------------------------


def test_prepare_image_downsizes_and_strips_exif():
    exif = Image.Exif()
    exif[0x8825] = {2: (41.0, 0.0, 0.0)}  # GPSInfo
    buf = io.BytesIO()
    Image.open(io.BytesIO(make_photo(1, size=(3000, 2000)))).save(buf, format="JPEG", exif=exif)
    out = prepare_image(buf.getvalue())
    assert max(out.width, out.height) == 1024
    assert not Image.open(io.BytesIO(out.data)).getexif()


@pytest.mark.parametrize(
    "raw,code",
    [
        (b"not an image", "not_an_image"),
        (make_photo(brightness=20), "too_dark"),
        (make_photo(blank=True), "blurry"),
        (make_photo(fmt="GIF"), "unsupported_format"),
    ],
)
def test_prepare_image_rejections(raw, code):
    with pytest.raises(ImageRejected) as ei:
        prepare_image(raw)
    assert ei.value.code == code


# ---- schemas & selection ----------------------------------------------------


def test_stage1_schema_enum_matches_lexicon():
    items = SYMBOL_EXTRACTION_SCHEMA["properties"]["semboller"]["items"]
    assert items["properties"]["sembol"]["enum"] == SYMBOL_IDS
    assert set(items["required"]) == set(items["properties"])


def test_select_symbols_filters_dedupes_and_ranks():
    ext = SymbolExtraction.model_validate(
        {
            "fincan_gecerli": True,
            "red_nedeni": None,
            "gorsel_kalitesi": "iyi",
            "baskin_ton": "yogun",
            "semboller": [
                {"sembol": "kus", "bolge": "kenar", "fotograf": 1, "boyut": "kucuk", "guven": 0.6, "detay": None},
                {"sembol": "kus", "bolge": "orta", "fotograf": 2, "boyut": "buyuk", "guven": 0.9, "detay": None},
                {"sembol": "yilan", "bolge": "dip", "fotograf": 2, "boyut": "orta", "guven": 0.3, "detay": None},
                {"sembol": "balik", "bolge": "tabak", "fotograf": 3, "boyut": "orta", "guven": 0.7, "detay": None},
            ],
        }
    )
    sel = select_symbols(ext)
    assert [s.sembol for s in sel] == ["kus", "balik"]
    assert sel[0].bolge.value == "orta"


def test_unknown_symbol_rejected_by_validator():
    with pytest.raises(ValueError):
        SymbolExtraction.model_validate(
            {
                "fincan_gecerli": True,
                "red_nedeni": None,
                "gorsel_kalitesi": "iyi",
                "baskin_ton": "acik",
                "semboller": [
                    {"sembol": "ejderha", "bolge": "kenar", "fotograf": 1, "boyut": "orta", "guven": 0.9, "detay": None}
                ],
            }
        )


# ---- hallucination guard ----------------------------------------------------


def test_hallucination_guard_detects_inflected_forms():
    assert hallucinated_symbols("Fincanının dibinde bir yılanın kıvrıldığını görüyorum.", {"kus"}) == ["yilan"]
    assert hallucinated_symbols("Tabakta küçük bir balığa benzeyen şekil var.", {"kus"}) == ["balik"]
    assert hallucinated_symbols("Uçağa binip uzaklara gideceksin.", set()) == ["ucak"]


def test_hallucination_guard_ignores_zodiac_and_common_words():
    text = "Balık burcu olarak bu noktada kuşkuların olabilir; işler yolunda, çarpıcı bir dönem, filmler izle."
    assert hallucinated_symbols(text, set()) == []


def test_hallucination_guard_allows_detected():
    assert hallucinated_symbols("Kuşun getirdiği haber...", {"kus"}) == []


def test_validate_reading_rules():
    ok = Reading(paragraflar=[GOOD_P] * 3, kullanilan_semboller=["kus", "yol"])
    assert validate_reading(ok, {"kus", "yol"}) == ([], [])
    two = Reading(paragraflar=[GOOD_P] * 2, kullanilan_semboller=["kus"])
    hard, _ = validate_reading(two, {"kus", "yol"})
    assert any("3 paragraf" in h for h in hard)
    ghost = Reading(paragraflar=[GOOD_P + " Bir de yılan var."] * 3, kullanilan_semboller=["kus", "yol"])
    hard, soft = validate_reading(ghost, {"kus", "yol"})
    assert not hard and any("Yılan" in s for s in soft)


# ---- pipeline ---------------------------------------------------------------


def test_pipeline_happy_path(photos):
    vision, text = FakeLLM("v"), FakeLLM("t")
    r = run(FortunePipeline(vision, text).run(photos, PROFILE))
    assert len(r.paragraphs) == 3
    # low-confidence "dag" (0.41) is filtered out before stage 2
    assert {s.sembol for s in r.symbols} == {"kus", "yol", "harf"}
    assert vision.calls[0]["images"] == 3
    assert '"dag"' not in text.calls[0]["user"]
    assert r.warnings == []


def test_pipeline_rejects_non_cup(photos):
    vision = FakeLLM(
        overrides={
            "coffee_symbols": [
                {
                    "fincan_gecerli": False,
                    "red_nedeni": "Fotoğrafta bir kedi var.",
                    "gorsel_kalitesi": "iyi",
                    "baskin_ton": "acik",
                    "semboller": [],
                }
            ]
        }
    )
    with pytest.raises(FortuneRejected) as ei:
        run(FortunePipeline(vision, FakeLLM()).run(photos, PROFILE))
    assert ei.value.code == "not_a_cup"


def test_pipeline_retries_once_on_hallucination(photos):
    bad = {"paragraflar": [GOOD_P + " Bir yılan görüyorum."] * 3, "kullanilan_semboller": ["kus"]}
    text = FakeLLM(overrides={"coffee_reading": [bad]})
    r = run(FortunePipeline(FakeLLM(), text).run(photos, PROFILE))
    assert len(text.calls) == 2
    assert "KURAL İHLALİ" in text.calls[1]["user"]
    assert r.warnings == []


def test_pipeline_fails_on_repeated_structural_errors(photos):
    bad = {"paragraflar": ["kısa"], "kullanilan_semboller": ["kus"]}
    text = FakeLLM(overrides={"coffee_reading": [bad, dict(bad)]})
    with pytest.raises(LLMError):
        run(FortunePipeline(FakeLLM(), text).run(photos, PROFILE))


def test_pipeline_requires_three_photos(photos):
    with pytest.raises(FortuneRejected):
        run(FortunePipeline(FakeLLM(), FakeLLM()).run(photos[:2], PROFILE))
