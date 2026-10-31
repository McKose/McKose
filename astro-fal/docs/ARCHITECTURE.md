# Astro-Fal — Mimari, Tasarım Kararları ve Spesifikasyon İncelemesi

> Kapsam: Kahve falı (multimodal), cinsiyet perspektifli günlük burç, retro/ay evresi takvimi,
> burç uyumu. Bu doküman hem uygulanan backend çekirdeğini hem de orijinal spesifikasyona
> yönelik düzeltme/itirazları içerir.
> Durum: Backend çekirdeği + 50 test hazır (`backend/`). Mobil istemci henüz yok.

---

## 1. Genel Mimari

```
 Mobil (Flutter önerilir)                      Backend (FastAPI, stateless)
 ┌─────────────────────┐   HTTPS/JSON    ┌───────────────────────────────────────────────┐
 │ Kamera + kılavuz    │ ──────────────► │ /v1/fortune/coffee                            │
 │ overlay (3 kare)    │  multipart JPEG │   Aşama 0: görüntü kapısı (Pillow)            │
 │ Profil, burç, takvim│                 │   Aşama 1: vision LLM → kapalı sözlük JSON    │
 └─────────────────────┘                 │   Aşama 2: text LLM → 3 paragraf JSON         │
                                         │   Aşama 3: doğrulayıcılar (+1 retry)          │
                                         │                                               │
                                         │ /v1/astro/*  (LLM yok, saf hesap)             │
                                         │   Swiss Ephemeris → konum, retro, ay evresi   │
                                         │   ev hesabı (solar/whole-sign)                │
                                         │                                               │
                                         │ /v1/horoscope/daily, /retro-guide, /compat.   │
                                         │   deterministik bağlam → LLM → TTL cache      │
                                         └───────────────────────────────────────────────┘
                                                 │                  │
                                         OpenAI-uyumlu API     Redis (prod) / bellek (dev)
                                         (OpenAI | Gemini)
```

**Temel ilke:** LLM hiçbir şey *hesaplamaz*. Gezegen konumu, retro tarihi, ev numarası, uyum
skoru ve fincandaki sembol listesi deterministik katmanda üretilir; LLM yalnızca bunları
**sözelleştirir**. Halüsinasyonun asıl panzehiri prompt değil, bu sorumluluk ayrımıdır.

### Modül haritası

| Modül | Dosya | Sorumluluk |
|---|---|---|
| Ephemeris | `app/astro/ephemeris.py` | Konum/hız, retro istasyonları (kök bulma), ay evreleri, Güneş burcu, yükselen |
| Ev hesabı | `app/astro/houses.py` | `ev = (hedef_burç − referans_burç) mod 12 + 1` |
| Olaylar | `app/astro/events.py` | Günlük gökyüzü özeti, kişisel takvim (retro + yeniay/dolunay + ev + tema) |
| Uyum | `app/astro/compatibility.py` | Element/nitelik/polarite skoru; doğum tarihli çok faktörlü uyum |
| Fal hattı | `app/fortune/*` | Görüntü kapısı, sembol sözlüğü, şemalar, promptlar, pipeline + doğrulayıcılar |
| Anlatı | `app/horoscope/*` | Perspektif promptları, günlük burç / retro rehberi / uyum anlatısı, cache |
| LLM | `app/llm/*` | Sağlayıcıdan bağımsız arayüz, OpenAI-uyumlu HTTP istemcisi, offline `FakeLLM` |

---

## 2. Doğrulama: Astroloji Motoru Ne Kadar Doğru?

Motor, bağımsız yayımlanmış 2024 olay zamanlarıyla test edildi (`tests/test_ephemeris.py`):

| Olay (UTC) | Yayımlanan | Motor | Fark |
|---|---|---|---|
| Merkür retro başlangıcı | 01.04.2024 22:14, 27°13′ Koç | 22:14:34, 27.2186° | < 1 dk |
| Merkür düzelme | 25.04.2024 12:54, 15°58′ Koç | 12:54:11 | < 1 dk |
| Merkür retro (iki burç) | 05.08 04:56 Başak → 28.08 21:14 Aslan | 04:56 / 21:14 | < 1 dk |
| Yeniay (tam güneş tutulması) | 08.04.2024 18:21 | 18:20:55 | < 1 dk |
| Dolunay | 23.04.2024 23:49 | 23:48:59 | < 1 dk |
| Haziran gündönümü (Yengeç girişi) | 20.06.2024 20:51 | 20:51:00 | < 1 dk |

- Varsayılan mod: Swiss Ephemeris'in dahili **Moshier** efemerisi (veri dosyası gerekmez).
  Hassasiyeti gezegenlerde yay saniyesinin altında, Ay'da birkaç yay saniyesi. Burç/ev kararı
  için gereken hassasiyetin (~0.5°) çok altında.
- Retro tespiti: boylamsal hız (`FLG_SPEED`) işaret değiştirdiğinde 1 günlük tarama + ikiye
  bölme ile 15 sn hassasiyet. Pencere ±420 gün genişletilir; böylece pencereden önce başlamış
  retro dönemler eksiksiz döner.
- Ay evresi: Ay−Güneş elongasyonu günde ~12.2° arttığı için 1 günlük adım 90°'lik bir evre
  sınırını atlayamaz.

---

## 3. Spesifikasyona İtirazlar ve Düzeltmeler

### 3.1 "LLM, olayın hangi eve düştüğünü hesaplayarak…" — **Yanlış katman**
Bu, spesifikasyonun kendi ilkesiyle ("tahmin ettirme, hesapla") çelişiyor. Ev hesabı tek satırlık
modüler aritmetik; LLM'e bıraktığınızda %100 doğru olması gereken bir bilgiyi olasılıksal hale
getirirsiniz.

- **Uygulanan:** `whole_sign_house()`; doğum saati yoksa Güneş burcundan **solar evler** (güneş
  burcu yorumlarının standardı), doğum saati+yeri varsa yükselen burçtan whole-sign evler.
- LLM'e giden veri: `{"title": "Merkür Retrosu", "house": 10, "house_theme": "kariyer, statü…"}`.

### 3.2 Kadın/Erkek perspektifi — **Ürün ve marka riski**
"Kadın → duygular/ilişki, erkek → kariyer/eylem" eşlemesi, birebir uygulanırsa kalıp yargı üretir:
kariyer odaklı kadın kullanıcı sürekli "duygusal denge", ilişki odaklı erkek kullanıcı sürekli
"hedef baskısı" okur. Sonuç: düşük kişiselleştirme algısı, olumsuz yorumlar, sosyal medya riski.
Ayrıca "belirtmek istemiyorum" diyen kullanıcılar ve aynı cinsiyetten çiftler için tanımsız.

- **Uygulanan çözüm (spesifikasyonu korur, riski giderir):**
  - Perspektif ayrı bir parametre: `disil | eril | dengeli`. Varsayılanı cinsiyetten türetilir,
    kullanıcı değiştirebilir.
  - Ortak kural: *"Perspektif sadece vurguyu ve üslubu belirler; aşk, kariyer, para, duygu
    konularının hepsi her kullanıcıya eksiksiz anlatılabilir."*
  - Cinsiyet belirtmeyen kullanıcıya `dengeli` perspektif uygulanır.
- Not: Dişil/eril kavramı astrolojinin kendi içinde de var (Ateş/Hava eril, Toprak/Su dişil
  burçlar). Pazarlamada bunu cinsiyetten çok enerji dili olarak konumlamak daha savunulabilir.

### 3.3 "Sinastri" — **Yanlış terim ve sığ algoritma**
Gerçek sinastri, iki tam doğum haritası (tarih + saat + yer) arasındaki gezegen açılarıdır.
Tarif edilen şey **Güneş burcu uyumu**. Daha önemlisi: element, nitelik ve polarite birbirinden
bağımsız değil, üçü de iki burç arasındaki **açısal mesafe** (0–6 burç) ile tamamen belirlenir:

| Mesafe | Açı | Element | Nitelik | Skor |
|---|---|---|---|---|
| 0 | Kavuşum (aynı burç) | aynı | aynı | 85 |
| 1 | Yarım altmışlık | zorlayıcı | farklı | 40 |
| 2 | Sekstil | tamamlayıcı | farklı | 80 |
| 3 | Kare | zorlayıcı | aynı | 32 |
| 4 | Trigon | aynı | farklı | 92 |
| 5 | Quincunx | zorlayıcı | farklı | 40 |
| 6 | Karşıt | tamamlayıcı | aynı | 73 |

Skor = 0.60·element + 0.25·nitelik + 0.15·polarite. 78 benzersiz burç çifti için yalnızca **7 farklı
sonuç** var (test: `test_score_depends_only_on_sign_distance`). Ayrıca polarite, element uyumuyla
birebir aynı bilgiyi taşır, ek bilgi katmaz.

- **Uygulanan iyileştirme:** İki kişinin doğum tarihi verilirse **çok faktörlü uyum**:

| Boyut | Gezegen çifti | Ağırlık |
|---|---|---|
| Temel uyum | Güneş–Güneş | 0.25 |
| Duygusal | Ay–Ay | 0.20 |
| İletişim | Merkür–Merkür | 0.15 |
| Tutku | Venüs(A)–Mars(B) ve Mars(A)–Venüs(B) | 0.25 |
| Çatışma yönetimi | Mars–Mars | 0.15 |

  Bu boyutlar, spesifikasyondaki "iletişim, tutku, çatışma" anlatı başlıklarına doğrudan veri
  sağlar. Ay günde 12–15° hareket ettiğinden, doğum saati yoksa ve Ay o gün burç değiştiriyorsa
  `moon_uncertain` bayrağı ve açıklama notu döner (1980–1989 taramasında günlerin %44'ü).
- Ağırlıklar ürün kararıdır, astronomik gerçek değildir; A/B test ile ayarlanmalı.

### 3.4 "Vision API" — **Klasik vision servisleri işe yaramaz**
Google Cloud Vision / AWS Rekognition gibi etiketleme servisleri gerçek nesneler için eğitilmiştir.
Telve fotoğrafına "cup, coffee, brown, pattern" döner, "balık" veya "yol" dönmez. Telvede şekil
görmek bir **pareidolia** görevidir ve multimodal bir LLM (GPT-4o sınıfı, Gemini Flash vb.)
gerektirir.

### 3.5 Aşama 1 JSON'u — **Çok zayıf sözleşme**
`{"semboller": ["balık","dağ"], "baskın_ton": "yoğun"}` şunları taşımıyor: fincan geçerli mi,
sembol nerede (geleneksel yorumda bölge anlamı değiştirir), ne kadar emin, görüntü kalitesi.
Serbest metin sembol adı ise modelin istediği şeyi uydurmasına izin verir.

**Uygulanan sözleşme** (`app/fortune/schemas.py`):

```json
{
  "fincan_gecerli": true,
  "red_nedeni": null,
  "gorsel_kalitesi": "iyi | orta | kotu",
  "baskin_ton": "acik | dengeli | yogun",
  "semboller": [
    {"sembol": "<45 kimlikten biri, enum>", "bolge": "kenar|orta|dip|kulp_yani|kulp_karsisi|tabak",
     "fotograf": 1, "boyut": "kucuk|orta|buyuk", "guven": 0.86, "detay": "M"}
  ]
}
```

- **Kapalı sözlük:** `sembol` alanı JSON-schema `enum` ile 45 geleneksel sembolle sınırlı
  (`app/fortune/symbols.py`). Model listede olmayan bir şekli ifade edemez.
- **Structured outputs** (`response_format: json_schema, strict: true`): "JSON döndür lütfen"
  yerine sağlayıcı seviyesinde şema zorlaması. Ardından Pydantic ile sınır kontrolü.
- **Deterministik filtre:** `guven < 0.5` atılır, aynı sembol tekilleştirilir, en güçlü 7 sembol
  kalır. 2'den az sembol kalırsa fal **üretilmez**, kullanıcıdan yeniden çekim istenir
  (uydurma fal yerine dürüst ret).

### 3.6 İki aşama yetmez, dört aşama gerekir

| Aşama | Ne yapar | Neden |
|---|---|---|
| 0. Görüntü kapısı | Format/boyut kontrolü, decompression-bomb koruması, EXIF yönü + **metadata silme**, 1024 px'e küçültme, karanlık/parlak/bulanık reddi | Token harcamadan önce çöpü eler; GPS gibi kişisel veriyi siler (KVKK) |
| 1. Sembol çıkarımı | Vision LLM, düşük sıcaklık (0.2), kapalı sözlük | Algı ve yorum ayrı tutulur |
| 2. Anlatı | Text LLM (0.85), semboller + **sözlükteki geleneksel anlamlar** + profil | Anlam modelin hayal gücünden değil, küratörlü sözlükten gelir |
| 3. Doğrulama | Tam 3 paragraf, 40–160 kelime, `kullanilan_semboller ⊆ tespit edilenler`, halüsinasyon taraması → ihlalde geri bildirimle **1 retry** | Prompt'a güvenmek yerine çıktıyı ölçmek |

Halüsinasyon taraması, tespit edilmemiş sembollerin Türkçe çekimli hallerini arar ("yılanın",
"balığa", "uçağa"). Gündelik dilde veya deyimlerde geçen kelimeler ("bu noktada", "kuşku",
"çarpıcı", "çiçek açmak", "işler yolunda") ve burç adları ("Balık burcu") bilinçli olarak
hariç tutuldu. Bu taramalar testlerle sabitlendi.

### 3.7 Model seçimi — **GPT-4o-mini görüntüde ucuz değil**
OpenAI'nin fiyatlandırmasında GPT-4o-mini, görüntü girişini GPT-4o'dan ~33 kat daha fazla tokene
çevirir (512 px tile başına 5.667'ye karşı 170 token). Token fiyatı ~16,7 kat ucuz olduğundan
**görüntü girişi 4o-mini'de GPT-4o'nun ~2 katı tutar**. Çıktı ve sistem promptu eklendiğinde ise
Aşama 1'in toplam maliyeti iki modelde **neredeyse eşittir**. Yani GPT-4o, daha güçlü görsel
algıyı aynı fiyata verir. Aşağıdaki hesap bilinen son liste fiyatlarıyla yapılmış bir büyüklük
tahminidir; **canlıya çıkmadan önce güncel fiyatlarla doğrulayın**.

Varsayımlar: 3 görüntü × 1024×768 (yüksek detay = 4 tile/görüntü), Aşama 1 sistem promptu ~1.000
token + çıktı ~400 token; Aşama 2 ~2.000 giriş + ~700 çıkış token (Türkçe, İngilizceye göre
~1,5–2 kat token), %10 retry. Fiyatlar ($/1M giriş–çıkış): 4o-mini 0,15–0,60; 4o 2,50–10;
Gemini 2.5 Flash 0,30–2,50.

| Konfigürasyon | Aşama 1 | Aşama 2 | Fal başına | Günde 10.000 fal |
|---|---|---|---|---|
| 4o-mini + 4o-mini | (3×25.501 + 1.000) giriş + 400 çıkış ≈ $0,0119 | ≈ $0,0008 | **≈ $0,013** | ≈ $127 |
| 4o (görüntü) + 4o-mini (metin) | (3×765 + 1.000) giriş + 400 çıkış ≈ $0,0122 | ≈ $0,0008 | **≈ $0,013** | ≈ $130 |
| Gemini Flash + Gemini Flash | (~3×800 + 1.000) giriş + 400 çıkış ≈ $0,0020 | ≈ $0,0026 | **≈ $0,005** | ≈ $46 |

- OpenAI tarafında kalınacaksa: Aşama 1 için GPT-4o sınıfı, Aşama 2 için mini model mantıklı.
  4o-mini'de `detail: low` görüntü başına 2.833 tokene düşer, fakat görüntü 512 px'e indirildiği
  için telve detayı kaybolur. Önerilmez.
- Gemini 2.5 Flash'ta "thinking" tokenları çıktı olarak faturalanır; bu iş yükü için düşünme
  bütçesi kapatılmalı/kısılmalı, yoksa Aşama 2 maliyeti birkaç katına çıkabilir.

- Mimari, sağlayıcıyı konfigürasyon değişikliğine indirger: tek bir OpenAI-uyumlu HTTP istemcisi
  hem OpenAI'ye hem Gemini'nin OpenAI-uyumlu endpoint'ine konuşur. Aşama 1 ve Aşama 2 için ayrı
  model seçilebilir (`VISION_MODEL`, `TEXT_MODEL`).
- **Karar kriteri fiyat değil, Aşama 1 kalitesi olmalı:** 100–200 etiketli fincan fotoğrafından
  oluşan bir değerlendirme seti ile sembol kesinliği (precision) ve tekrar tutarlılığı ölçülmeli
  (bkz. §5.2).
- `gemini-2.5-flash` varsayılanı ve Gemini'nin `strict` JSON-schema desteği (özellikle
  `additionalProperties`) entegrasyon testinde doğrulanmalı.

### 3.8 Günlük burç — **Kullanıcı başına üretim gereksiz**
Günlük burç kişisel değildir: (gün, burç, perspektif) = 12 × 3 = **günde 36 üretim**, kullanıcı
sayısından bağımsız. ~2.000 token/üretim ile günlük maliyet birkaç sent. Uygulamada cache
anahtarı `(gün, burç, perspektif, model, prompt_version)`; single-flight kilidi sayesinde
eşzamanlı 1.000 istek tek LLM çağrısı yapar. Burç uyumu (Güneş-burcu modu) için 12×12×cinsiyet
matrisi de bir kez üretilip saklanır.

Daha da önemlisi: her yorum o günün **gerçek gökyüzüne** dayanır (Ay'ın evi, retrolar, burç
geçişleri, ay evresi). "Jenerik cümle" sorununu çözen şey bu veri farklılığıdır.

---

## 4. Mobil İstemci Önerisi

| Kriter | Flutter | React Native (Expo) |
|---|---|---|
| Özel animasyonlu, "mistik" UI | ✔ Kendi render motoru, platformlar arası birebir görünüm | Reanimated/Skia ile mümkün, daha fazla emek |
| Kamera + kılavuz overlay | `camera` paketi | `react-native-vision-camera` (olgun) |
| OTA güncelleme | Shorebird (üçüncü parti, ücretli) | EAS Update (yerleşik) |
| Ekip yetkinliği | Dart | TypeScript (web ekibiyle paylaşılabilir) |

**Öneri:** İçerik ve promptlar zaten sunucuda olduğu için OTA avantajı sınırlı. UI animasyon
ağırlıklı olduğundan **Flutter** önerilir. Ekip TypeScript ağırlıklıysa React Native + Expo.
Her iki durumda da:
- Fotoğraf istemcide **JPEG'e** çevrilmeli (iOS varsayılanı HEIC; sunucu HEIC kabul etmiyor).
- Çekim ekranında 3 adımlı kılavuz: kulp tarafı → kulp karşısı → tabak; fincanı soğumuş ve
  ters çevrilmiş halde, gün ışığında, flaşsız.

---

## 5. Üretime Geçiş Öncesi Yapılacaklar

### 5.1 Altyapı
- [ ] Kahve falı uç noktasını **asenkron iş kuyruğuna** taşı (ör. arq/Celery + Redis): yükleme →
      `job_id` → push bildirimi. Senkron istek 8–15 sn sürer ve mobil ağda kopmaya açıktır;
      kuyruk ayrıca hız sınırlama ve "falcı fincanına bakıyor" UX'i sağlar.
- [ ] `TTLCache` → Redis (arayüz aynı).
- [ ] Kimlik doğrulama + kullanıcı başına hız sınırı (ör. günlük ücretsiz fal kotası).
- [ ] Gözlemlenebilirlik: model, prompt_version, Aşama 1 sembol sayısı, doğrulama ihlal oranı,
      retry oranı, gecikme (p50/p95), fal başına maliyet.

### 5.2 Kalite
- [ ] **Tekrar tutarlılığı:** Aynı fotoğraflar iki kez işlendiğinde sembol kümeleri ne kadar
      örtüşüyor? (Jaccard benzerliği; hedef ≥ 0.6). Kullanıcılar aynı fincanı tekrar yükleyip
      bambaşka fal gördüğünde güven kaybolur. Önlem: görüntülerin perceptual hash'i ile 24 saatlik
      sonuç cache'i.
- [ ] Etiketli değerlendirme seti (100–200 fincan) ile sembol kesinliği; sağlayıcı/model kararını
      bu sete göre ver.
- [ ] Görüntü kapısı eşikleri (`MIN_BRIGHTNESS`, `MIN_EDGE_VARIANCE`) gerçek yüklemelerle kalibre
      edilmeli; şu an sentetik verilerle doğrulandı.
- [ ] Sembol sözlüğü ve bölge anlamları bir içerik editörü/falcı tarafından gözden geçirilmeli
      (yöreden yöreye değişir).

### 5.3 Hukuk ve Platform Riskleri

| Risk | Etki | Önlem |
|---|---|---|
| **App Store 4.3 (spam)** — Apple yönergeleri falcılık uygulamalarını "doymuş kategori" olarak açıkça anar ve benzersiz, yüksek kaliteli deneyim sunmayanları reddeder | iOS yayını engellenebilir | Ephemeris tabanlı kişisel takvim, gerçek gökyüzüne dayalı yorum gibi ayırt edici özellikleri inceleme notunda vurgula; şablon/klon görünümden kaçın |
| **Swiss Ephemeris lisansı** — `pyswisseph` ve Swiss Ephemeris AGPL-3.0; ticari kapalı kaynak kullanım için Astrodienst'ten profesyonel lisans gerekir. AGPL ağ üzerinden sunulan yazılımda kaynak açma yükümlülüğü doğurur | Hukuki | (a) Astrodienst ticari lisansı satın al, (b) backend'i AGPL ile aç, (c) MIT lisanslı Skyfield + JPL DE440s'e geç (ev hesabı için yükselen formülü eklenir). `Ephemeris` sınıfı tek dosyada izole, geçiş maliyeti düşük |
| **flatlib** | Bakımsız; eski `pyswisseph` 2.08'e sabitli, AGPL sorunu aynen geçerli | Kullanılmadı, önerilmez |
| **KVKK — yurt dışına aktarım** — Fotoğraf, doğum tarihi ve ilişki durumu OpenAI/Google'a (ABD) gönderiliyor. 2024 değişikliğiyle (7499 s. Kanun) md. 9 kapsamında standart sözleşme ve Kurul'a bildirim gerekir | Hukuki/idari para cezası | Açık aydınlatma metni + aktarım rızası, standart sözleşme, fotoğrafları işlem sonrası saklamama, log'larda kişisel veri tutmama. Hukuk danışmanıyla doğrulayın |
| **Hassas çıkarım** — Uyumda cinsiyet kombinasyonu, cinsel yönelim hakkında dolaylı bilgi verebilir | KVKK özel nitelikli veri riski | Bu alanı opsiyonel tut, kalıcı saklama, analitiğe gönderme |
| **Psikolojik zarar / bağımlılık** | Marka ve etik | Sağlık/ölüm/kaza/hamilelik tahmini yasak (prompt kuralı), "eğlence amaçlıdır" uyarısı, 18+ yaş sınırı (API `age ≥ 18` zorlar) |
| **Prompt injection** — Fincan fotoğrafına yazılmış talimat | Model davranışı | Aşama 1 promptu görüntüdeki yazıları yok sayar; çıktı kapalı sözlükle sınırlı olduğu için etki alanı dar |

---

## 6. Açık Kararlar

1. **Ephemeris lisansı:** Ticari lisans mı, AGPL mi, Skyfield mi? (§5.3, canlıdan önce zorunlu)
2. **Mobil çatı:** Flutter mı, React Native mi? (§4)
3. **LLM sağlayıcısı:** Değerlendirme seti sonuçlarına göre (§3.7, §5.2).
4. **Perspektif varsayılanı:** Cinsiyetten türetilsin mi, yoksa onboarding'de kullanıcıya mı sorulsun?
5. **Uyum ağırlıkları:** Ürün kararı; A/B test önerilir.
6. **Monetizasyon:** Fal kotası / bekleme süresi / abonelik. Maliyet tablosuna (§3.7) göre
   fal başına birim maliyet ≈ $0,005–$0,013.
