# Astro-Fal — Kahve Falı & Astroloji Backend'i

Multimodal kahve falı, cinsiyet perspektifli günlük burç, retro / ay evresi takvimi ve burç uyumu
için FastAPI backend çekirdeği.

- **Astronomi:** Swiss Ephemeris (`pyswisseph`). Retro, yeniay/dolunay ve burç geçişleri dakika
  hassasiyetiyle hesaplanır; LLM'e tahmin ettirilmez.
- **Yapay zeka:** Sağlayıcıdan bağımsız, OpenAI-uyumlu istemci (OpenAI veya Gemini). Structured
  outputs ile şema zorlaması, kapalı sembol sözlüğü, çıktı doğrulama + retry.
- **Mimari, kararlar, maliyet hesabı ve riskler:** [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md)

## Kurulum

```bash
cd astro-fal/backend
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env    # LLM_PROVIDER=fake ile anahtar gerekmeden çalışır
```

```bash
uvicorn app.main:create_app --factory --reload
```

```bash
pytest
```

Swagger arayüzü: <http://localhost:8000/docs>

`LLM_PROVIDER=fake` deterministik, offline yanıtlar üretir. Tüm API uçtan uca anahtar olmadan
denenebilir. Gerçek model için `LLM_PROVIDER=openai|gemini` ve `LLM_API_KEY` ayarlayın.

## API

| Uç nokta | LLM | Açıklama |
|---|---|---|
| `GET /v1/astro/sun-sign` | — | Güneş burcu (ephemeris ile); doğum saati yoksa burç sınırı uyarısı |
| `GET /v1/astro/sky` | — | Günlük gökyüzü: gezegenler, burç, derece, retro, ilgili burca göre ev |
| `GET /v1/astro/calendar` | — | Tarih aralığındaki retrolar + yeniay/dolunay; `sign` verilirse ev ve tema |
| `POST /v1/horoscope/daily` | ✔ (cache) | Günlük burç; perspektif `disil / eril / dengeli` |
| `POST /v1/astro/retro-guide` | ✔ (cache) | Retronun düştüğü eve göre "yap / yapma" rehberi |
| `POST /v1/compatibility` | ✔ | Burç uyumu; iki doğum tarihi verilirse 5 boyutlu çok faktörlü skor |
| `POST /v1/fortune/coffee` | ✔✔ | 3 fotoğraf (kulp tarafı, kulp karşısı, tabak) + profil → 3 paragraflık fal |

Örnek:

```bash
curl -s "localhost:8000/v1/astro/calendar?start=2026-11-01&end=2026-12-31&sign=yengec"
```

```bash
curl -s -X POST localhost:8000/v1/fortune/coffee \
  -F photos=@kulp.jpg -F photos=@karsi.jpg -F photos=@tabak.jpg \
  -F focus=kariyer -F gender=kadin -F relationship=bekar -F age=29
```

## Proje yapısı

```
backend/
  app/
    astro/       ephemeris, zodiac, houses, events (takvim), compatibility
    fortune/     imaging (görüntü kapısı), symbols (sözlük), schemas, prompts, pipeline
    horoscope/   perspektif promptları, anlatı servisi (cache'li)
    llm/         arayüz, OpenAI-uyumlu istemci, FakeLLM
    api/         FastAPI router
    cache.py     TTL + single-flight cache
    main.py      app factory
  tests/         ephemeris (yayımlanmış 2024 olaylarıyla), uyum, fal hattı, API, LLM istemcisi
```

> ⚠️ **Lisans:** Swiss Ephemeris / `pyswisseph` AGPL-3.0'dır. Kapalı kaynak ticari kullanım için
> Astrodienst lisansı gerekir. Alternatifler için bkz. ARCHITECTURE.md §5.3.
