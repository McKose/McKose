import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.llm.fake import FakeLLM
from app.main import create_app


@pytest.fixture
def text_llm() -> FakeLLM:
    return FakeLLM("fake-text")


@pytest.fixture
def client(text_llm) -> TestClient:
    return TestClient(create_app(Settings(llm_provider="fake"), vision=FakeLLM("fake-vision"), text=text_llm))


def test_health(client):
    assert client.get("/health").json()["status"] == "ok"


def test_sun_sign_endpoint_flags_cusp(client):
    r = client.get("/v1/astro/sun-sign", params={"birth_date": "2024-06-20"}).json()
    assert r["cusp_ambiguous"] is True and r["message"]
    r = client.get("/v1/astro/sun-sign", params={"birth_date": "1990-07-15", "birth_time": "08:30"}).json()
    assert r["sign"] == "yengec" and r["cusp_ambiguous"] is False
    assert client.get("/v1/astro/sun-sign", params={"birth_date": "1990-07-15", "tz": "Mars/Olympus"}).status_code == 422


def test_calendar_personalised_houses(client):
    events = client.get("/v1/astro/calendar", params={"start": "2024-04-01", "end": "2024-04-30", "sign": "yengec"}).json()
    retro = next(e for e in events if e["kind"] == "retro" and e["title"].startswith("Merkür"))
    # Mercury retro in Aries -> 10th solar house for Cancer (career)
    assert retro["house"] == 10 and "kariyer" in retro["house_theme"]
    full = next(e for e in events if e["title"].startswith("Dolunay"))
    assert full["sign"] == "Akrep" and full["house"] == 5


def test_calendar_range_limit(client):
    assert client.get("/v1/astro/calendar", params={"start": "2024-01-01", "end": "2026-01-01"}).status_code == 422


def test_daily_horoscope_is_cached_per_sign_day_perspective(client, text_llm):
    body = {"sign": "akrep", "day": "2026-10-31", "gender": "kadin"}
    r1 = client.post("/v1/horoscope/daily", json=body).json()
    r2 = client.post("/v1/horoscope/daily", json=body).json()
    assert r1 == r2 and r1["perspective"] == "disil"
    assert len(text_llm.calls) == 1
    client.post("/v1/horoscope/daily", json={**body, "perspective": "dengeli"})
    assert len(text_llm.calls) == 2


def test_retro_guide(client):
    r = client.post("/v1/astro/retro-guide", json={"sign": "yengec", "planet": "merkur", "around": "2024-03-25T00:00:00Z"}).json()
    assert r["event"]["house"] == 10
    assert len(r["guide"]["yap"]) >= 3


def test_compatibility_modes(client, text_llm):
    sun = client.post(
        "/v1/compatibility", json={"a": {"sign": "koc", "gender": "kadin"}, "b": {"sign": "akrep", "gender": "erkek"}}
    ).json()
    assert sun["mode"] == "sun_sign" and "Koç kadını" in sun["narrative"]["iletisim"]
    chart = client.post(
        "/v1/compatibility",
        json={"a": {"birth_date": "1992-03-28", "birth_time": "09:30"}, "b": {"birth_date": "1990-11-05"}, "narrate": False},
    ).json()
    assert chart["mode"] == "chart" and len(chart["result"]["dimensions"]) == 5
    assert client.post("/v1/compatibility", json={"a": {"gender": "kadin"}, "b": {"sign": "koc"}}).status_code == 422


def test_coffee_endpoint(client, photos):
    files = [("photos", (f"{i}.jpg", p, "image/jpeg")) for i, p in enumerate(photos)]
    r = client.post(
        "/v1/fortune/coffee", files=files, data={"focus": "ask", "gender": "kadin", "relationship": "evli", "age": "34"}
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert len(body["paragraphs"]) == 3 and body["disclaimer"]


def test_coffee_endpoint_rejects_bad_image(client, photos):
    files = [("photos", ("a.jpg", b"garbage", "image/jpeg"))] + [
        ("photos", (f"{i}.jpg", p, "image/jpeg")) for i, p in enumerate(photos[:2])
    ]
    r = client.post("/v1/fortune/coffee", files=files)
    assert r.status_code == 422 and r.json()["code"] == "not_an_image"


def test_coffee_endpoint_enforces_adult_age(client, photos):
    files = [("photos", (f"{i}.jpg", p, "image/jpeg")) for i, p in enumerate(photos)]
    assert client.post("/v1/fortune/coffee", files=files, data={"age": "15"}).status_code == 422
