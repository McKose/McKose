# Nonstop Studio Kartepe — Web Sitesi Geliştirme Planı

> Domain: **nonstopstudio.tr**
> İşletme: Nonstop Studio (Kartepe / Kocaeli — spor salonu & fitness stüdyosu)
> Instagram: https://www.instagram.com/nonstopkartepe
> Durum: Planlama (kod henüz yazılmadı)

Bu doküman, sitenin sıfırdan canlıya alınması için yapılacak tüm işleri en ince
ayrıntısına kadar listeler. Her ana başlık altında somut "todo" maddeleri vardır.

---

## 0. Özet & Hedefler

**Amaç:** Salonun dijital vitrini olacak, mobil öncelikli, hızlı ve SEO uyumlu
bir tanıtım sitesi. Birincil iş hedefi: ziyaretçiyi **deneme dersi / üyelik
başvurusu**na yönlendirmek ve **WhatsApp + telefon + konum** ile temasa geçirmek.

**Başarı kriterleri (KPI):**
- [ ] Mobilde Lighthouse Performance ≥ 90, SEO ≥ 95, Accessibility ≥ 90
- [ ] İlk içerik boyaması (LCP) < 2.5s (4G)
- [ ] "deneme dersi" / "iletişim" CTA tıklama oranı ölçülebilir (analytics)
- [ ] Google'da "Kartepe spor salonu / fitness" aramalarında görünürlük

**Kapsam (v1):** Tanıtım sitesi (statik içerik + iletişim/başvuru formu).
**Kapsam dışı (v2+):** Online ödeme, üye paneli, otomatik rezervasyon takvimi.

---

## 1. Keşif & İçerik Toplama (Discovery)

Kod yazmadan önce müşteriden (salon sahibi) toplanması gereken içerikler.
Bu adım tamamlanmadan tasarım kesinleşmemeli.

- [ ] **Marka kimliği:** Logo (SVG/PNG, yüksek çözünürlük), marka renkleri,
      varsa kurumsal font tercihi
- [ ] **İşletme bilgileri:** Tam açık adres, telefon, WhatsApp hattı, e-posta,
      vergi/ticari unvan (footer & KVKK için)
- [ ] **Çalışma saatleri:** Hafta içi / hafta sonu açılış-kapanış
- [ ] **Hizmetler / dersler listesi:** (ör. Fitness/serbest çalışma, Fonksiyonel
      antrenman, Pilates/Reformer, Grup dersleri, Kişisel antrenman/PT, Kardiyo,
      Kadınlara özel saatler vb.) — her biri için kısa açıklama
- [ ] **Ders programı:** Haftalık grup ders takvimi (gün/saat/eğitmen)
- [ ] **Üyelik paketleri & fiyatlar:** (aylık/3 aylık/yıllık, PT paketleri) —
      fiyat gösterilecek mi yoksa "bilgi al" mı olacak karar verilmeli
- [ ] **Eğitmen kadrosu:** İsim, unvan/uzmanlık, foto, kısa bio
- [ ] **Görsel materyal:** Salon iç/dış fotoğrafları, ekipman, ders anları
      (yüksek çözünürlük; gerekirse profesyonel çekim planla)
- [ ] **Sosyal kanıt:** Üye yorumları/referanslar, Google yorumları, üye sayısı
- [ ] **Sosyal medya linkleri:** Instagram, Facebook, TikTok, YouTube (varsa)
- [ ] **Google Business profili:** Var mı? Yoksa açılmalı (harita + yorumlar için)
- [ ] **Dil:** Tek dil TR mi, yoksa TR/EN çift dil mi? (turizm bölgesi → EN değerli olabilir)

---

## 2. Domain, Altyapı & Hosting

`.tr` uzantılı domain TRABIS/nic.tr üzerinden yönetilir.

- [ ] nonstopstudio.tr DNS yönetim paneline erişim sağla (kayıt firması)
- [ ] Hosting/deploy platformu: **Vercel** (öneri) — Next.js için yerel destek,
      ücretsiz SSL, global CDN, otomatik önizleme
- [ ] Vercel projesine custom domain ekle: `nonstopstudio.tr` + `www.nonstopstudio.tr`
- [ ] DNS kayıtları:
  - [ ] `A` kaydı (apex `nonstopstudio.tr`) → Vercel IP **veya** ANAME/ALIAS
  - [ ] `CNAME` (`www`) → `cname.vercel-dns.com`
  - [ ] www → apex (veya apex → www) **301 yönlendirme** tek kanonik adres için
- [ ] SSL/HTTPS sertifikası doğrula (Vercel otomatik Let's Encrypt)
- [ ] E-posta: Kurumsal e-posta gerekli mi? (`info@nonstopstudio.tr`) → MX kayıtları
      (Google Workspace / Zoho Mail). Form gönderimi için ayrı (bkz. Bölüm 6)
- [ ] Domain & DNS değişikliklerinin yayılması için 24-48s payı bırak

---

## 3. Teknoloji Yığını (Tech Stack)

Tanıtım sitesi için modern, hızlı, bakımı kolay yığın:

| Katman | Tercih | Not |
|---|---|---|
| Framework | **Next.js (App Router, 14+)** | SSG/ISR, SEO, görsel optimizasyonu |
| Dil | **TypeScript** | Tip güvenliği |
| Stil | **Tailwind CSS** | Hızlı, tutarlı responsive |
| UI bileşenleri | **shadcn/ui** + Radix | Erişilebilir, özelleştirilebilir |
| İkonlar | **lucide-react** | |
| Animasyon | **Framer Motion** | Hafif, scroll/hover efektleri |
| Form | **React Hook Form + Zod** | Doğrulama |
| Form gönderimi | **Resend** (e-posta API) / Vercel Route Handler | Sunucusuz |
| İçerik | İlk etap kod içi veri (TS/JSON); v2'de hafif CMS | bkz. Bölüm 11 |
| Analytics | **Vercel Analytics** + **GA4** | |
| Deploy | **Vercel** | CI/CD entegre |

- [ ] Karar: İçerik nadiren değişiyorsa kod içi veri yeterli. Salon sahibi
      kendi güncellemek isterse → **Sanity** veya **Contentlayer/MDX** (v2)
- [ ] Karar: Çift dil gerekiyorsa `next-intl` ekle

---

## 4. Bilgi Mimarisi & Sayfa Yapısı (Sitemap)

Tek sayfa (one-page scroll) + birkaç alt sayfa hibrit yaklaşım önerilir.

```
/                    Anasayfa (hero + tüm bölümlerin özeti)
/hakkimizda          Hakkımızda / Hikaye
/hizmetler           Dersler & hizmetler (detay)
/program             Haftalık ders programı (takvim)
/uyelik              Üyelik paketleri & fiyatlandırma
/egitmenler          Eğitmen kadrosu
/galeri              Foto/video galeri
/iletisim            İletişim (form + harita + saatler)
/blog                (Opsiyonel — SEO için, v2)
/kvkk                KVKK aydınlatma metni
/gizlilik            Gizlilik & çerez politikası
```

Not: v1'de çoğu bölüm anasayfada tek sayfa olarak; içerik büyürse alt sayfalara
ayrıştır. URL planı SEO için baştan netleştirilmeli.

---

## 5. Anasayfa Bölümleri (Section by Section)

- [ ] **Header / Navbar:** Logo, menü, sticky, mobilde hamburger, sağda
      "Deneme Dersi" CTA butonu
- [ ] **Hero:** Etkileyici salon görseli/video arka plan, başlık (ör.
      "Kartepe'de Durmak Yok!"), alt başlık, iki CTA ("Deneme Dersi Al" +
      "WhatsApp'tan Yaz")
- [ ] **Güven şeridi:** Üye sayısı, eğitmen sayısı, yıl, m² gibi sayaçlar
- [ ] **Hizmetler/Dersler:** Kart grid (ikon + isim + kısa açıklama)
- [ ] **Neden Biz:** Ekipman, hijyen, uzman kadro, esnek saatler vb.
- [ ] **Ders programı önizleme:** Haftalık takvim özeti → /program linki
- [ ] **Üyelik/Fiyat önizleme:** Paket kartları → /uyelik
- [ ] **Eğitmenler:** Kadro önizleme
- [ ] **Galeri:** Lightbox'lı foto grid + Instagram beslemesi
- [ ] **Yorumlar/Referanslar:** Slider
- [ ] **Konum & İletişim:** Google harita embed, adres, saatler, telefon, WhatsApp
- [ ] **CTA bandı:** "İlk dersin bizden" tarzı dönüşüm bandı
- [ ] **Footer:** Logo, hızlı linkler, sosyal medya, adres, KVKK/gizlilik, telif

---

## 6. Özellikler (Features) — Teknik Detay

- [ ] **Responsive tasarım:** Mobil öncelikli; breakpoint'ler sm/md/lg/xl test edilir
- [ ] **Sabit WhatsApp butonu:** Sağ altta yüzen buton → `https://wa.me/<numara>?text=...`
- [ ] **Tıkla-ara:** Tüm telefon numaraları `tel:` linki
- [ ] **İletişim / Deneme dersi formu:**
  - Alanlar: Ad Soyad, Telefon, (e-posta ops.), ilgilenilen hizmet (select),
    mesaj, KVKK onay checkbox
  - React Hook Form + Zod doğrulama
  - Route Handler (`/api/contact`) → Resend ile salon e-postasına + WhatsApp
    yönlendirme seçeneği
  - Spam koruması: honeypot alanı + rate limit (+ ops. Cloudflare Turnstile/hCaptcha)
  - Başarı/hata durumu UI, gönderim sonrası teşekkür mesajı
- [ ] **Instagram beslemesi:** Resmî embed veya `behold.so`/benzeri ile son gönderiler
- [ ] **Google Maps:** Konum embed + "Yol Tarifi Al" linki
- [ ] **Ders programı:** Responsive haftalık tablo (mobilde gün-gün akordeon)
- [ ] **Galeri lightbox:** `yet-another-react-lightbox` vb.
- [ ] **Görsel optimizasyonu:** `next/image`, AVIF/WebP, lazy load, blur placeholder
- [ ] **Animasyonlar:** Scroll reveal, hover; `prefers-reduced-motion` desteği
- [ ] (Ops.) **Çift dil:** TR/EN switcher
- [ ] (Ops.) **Çerez izni banner'ı:** Analytics consent yönetimi

---

## 7. Tasarım Sistemi (Design)

- [ ] **Renk paleti:** Marka renklerinden tema (primary/secondary/accent +
      nötr griler). Spor/enerji teması → koyu zemin + canlı vurgu rengi
- [ ] **Tipografi:** Başlık için güçlü/sporcu font, gövde için okunur sans-serif
      (`next/font` ile self-host — performans)
- [ ] **Tasarım token'ları:** Tailwind `theme.extend` (renk, spacing, radius, shadow)
- [ ] **Bileşen kütüphanesi:** Button, Card, Section, Badge, Accordion, Dialog,
      Form alanları (shadcn/ui tabanlı)
- [ ] **Karanlık tema:** Spor siteleri için koyu tema varsayılan olabilir
- [ ] **Erişilebilirlik:** Kontrast WCAG AA, klavye navigasyonu, alt metinler,
      focus state'ler, ARIA etiketleri
- [ ] (Ops.) **Figma mockup:** Onay öncesi anasayfa + 1 alt sayfa tasarımı

---

## 8. SEO & Performans

- [ ] **Metadata:** Next `metadata` API — her sayfada title/description
- [ ] **Open Graph & Twitter Card:** Paylaşım görselleri (OG image)
- [ ] **Yapısal veri (JSON-LD):** `HealthClub` / `LocalBusiness` schema
      (ad, adres, telefon, açılış saatleri, geo, fiyat aralığı)
- [ ] **sitemap.xml** ve **robots.txt** (Next route ile otomatik)
- [ ] **Kanonik URL'ler** ve www/non-www yönlendirmesi
- [ ] **Yerel SEO:** Google Business Profile, NAP tutarlılığı (Ad-Adres-Telefon)
- [ ] **Performans:** Core Web Vitals optimizasyonu, font/preload, görsel boyutları
- [ ] **Google Search Console** + **Bing Webmaster** doğrulama, sitemap gönderimi
- [ ] **Analytics:** GA4 olay takibi (CTA tıkları, form gönderimi, WhatsApp tık)
- [ ] **Anahtar kelimeler:** "Kartepe spor salonu", "Kartepe fitness", "Kartepe pilates",
      "Kartepe PT" vb. içeriğe doğal yerleştirme

---

## 9. Yasal & Uyumluluk (KVKK)

- [ ] **KVKK Aydınlatma Metni** (form veri toplama için zorunlu)
- [ ] **Açık rıza onayı** form içinde checkbox + metin linki
- [ ] **Gizlilik Politikası** ve **Çerez Politikası** sayfaları
- [ ] **Çerez izni banner'ı** (analytics çerezleri için)
- [ ] İşletme künyesi footer'da (unvan/adres) — şeffaflık

---

## 10. Proje Kurulumu & Geliştirme Adımları

- [ ] `npx create-next-app@latest` (TypeScript, Tailwind, App Router, ESLint)
- [ ] Klasör yapısı:
  ```
  src/
    app/                # rotalar (page.tsx, layout.tsx, api/)
    components/         # ui/, sections/, layout/
    content/           # services.ts, schedule.ts, trainers.ts, pricing.ts
    lib/               # utils, schema (zod), seo
    styles/
    public/            # görseller, logo, og
  ```
- [ ] Tailwind tema + global stiller + font kurulumu
- [ ] shadcn/ui init + temel bileşenler
- [ ] İçerik veri dosyaları (content/) — keşif verisiyle doldur
- [ ] Layout (Navbar + Footer + WhatsApp FAB)
- [ ] Anasayfa bölümlerini sırayla geliştir (Bölüm 5)
- [ ] Alt sayfalar (Bölüm 4)
- [ ] İletişim formu + API route + Resend entegrasyonu
- [ ] SEO katmanı (metadata, sitemap, robots, JSON-LD)
- [ ] Analytics entegrasyonu
- [ ] Erişilebilirlik & responsive geçiş testleri
- [ ] ESLint + Prettier + (ops.) Husky pre-commit

---

## 11. İçerik Yönetimi (CMS) Kararı

- [ ] **v1:** İçerik kod içi (TS/JSON) — en hızlı, en ucuz, bakım geliştiriciyle
- [ ] **v2 (salon sahibi kendi güncellemek isterse):**
  - [ ] Sanity (ücretsiz tier, görsel editör) **veya** MDX/Contentlayer
  - [ ] Düzenlenebilir alanlar: program, fiyatlar, eğitmenler, galeri, blog

---

## 12. CI/CD & Kalite

- [ ] GitHub reposu → Vercel bağlantısı (her push'ta otomatik preview deploy)
- [ ] GitHub Actions: `lint` + `typecheck` + `build` kontrolü (PR'larda)
- [ ] PR önizleme linkleriyle müşteri onayı
- [ ] `main` → production, feature branch → preview akışı
- [ ] (Ops.) Lighthouse CI ile performans regresyon kontrolü

---

## 13. Test & Yayın Öncesi Kontrol Listesi (Launch Checklist)

- [ ] Tüm linkler ve butonlar çalışıyor (telefon, WhatsApp, harita, sosyal)
- [ ] Form gerçek gönderim testi (e-posta ulaşıyor mu, spam koruması)
- [ ] Mobil/tablet/masaüstü cihaz testleri (Safari iOS dahil)
- [ ] Lighthouse skorları hedefte (Bölüm 0)
- [ ] 404 sayfası ve hata durumları
- [ ] Favicon, app icon, OG görselleri
- [ ] Metin/yazım denetimi (Türkçe)
- [ ] KVKK/gizlilik/çerez metinleri yerinde
- [ ] Search Console + sitemap gönderildi
- [ ] Analytics veri akışı doğrulandı
- [ ] DNS/SSL/yönlendirmeler canlıda doğrulandı
- [ ] Yedek & rollback planı (Vercel anlık geri alma)

---

## 14. Yayın Sonrası & Bakım

- [ ] Google Business Profile güncel tutma, yorum yönetimi
- [ ] Aylık içerik güncellemesi (program, kampanya, blog)
- [ ] Analytics raporu (aylık dönüşüm/ziyaret)
- [ ] Bağımlılık güncellemeleri & güvenlik yamaları
- [ ] Yedekleme & alan adı/yenileme takibi

---

## 15. Önerilen Faz Planı (Zaman Çizelgesi)

| Faz | İş | Tahmini |
|---|---|---|
| 1 | Keşif & içerik toplama, marka varlıkları | 2-4 gün |
| 2 | Tasarım sistemi + anasayfa tasarımı/onay | 3-5 gün |
| 3 | Geliştirme (anasayfa + alt sayfalar + form) | 5-8 gün |
| 4 | SEO, analytics, KVKK, içerik girişi | 2-3 gün |
| 5 | Test, domain bağlama, yayın | 1-2 gün |

> Toplam (tek geliştirici): ~2-3 hafta (içeriğin müşteriden gelme hızına bağlı).

---

## Açık Kararlar (Müşteriden Onay Bekleyen)

1. Fiyatlar sitede gösterilecek mi, yoksa "bilgi al" mı?
2. Tek dil (TR) mi, çift dil (TR/EN) mi?
3. İçeriği salon sahibi kendi güncelleyecek mi (CMS gerekli mi)?
4. Blog bölümü v1'de olsun mu?
5. Online rezervasyon/randevu v1 kapsamında mı (yoksa v2)?
6. Kurumsal e-posta (`info@nonstopstudio.tr`) kurulacak mı?
