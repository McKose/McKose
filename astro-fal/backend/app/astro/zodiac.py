"""Static zodiac data: signs, elements, modalities, polarity, house themes."""

from __future__ import annotations

from enum import Enum


class Element(str, Enum):
    FIRE = "ates"
    EARTH = "toprak"
    AIR = "hava"
    WATER = "su"


class Modality(str, Enum):
    CARDINAL = "oncu"
    FIXED = "sabit"
    MUTABLE = "degisken"


class Sign(str, Enum):
    ARIES = "koc"
    TAURUS = "boga"
    GEMINI = "ikizler"
    CANCER = "yengec"
    LEO = "aslan"
    VIRGO = "basak"
    LIBRA = "terazi"
    SCORPIO = "akrep"
    SAGITTARIUS = "yay"
    CAPRICORN = "oglak"
    AQUARIUS = "kova"
    PISCES = "balik"

    @property
    def index(self) -> int:
        return SIGNS.index(self)

    @property
    def element(self) -> Element:
        return (Element.FIRE, Element.EARTH, Element.AIR, Element.WATER)[self.index % 4]

    @property
    def modality(self) -> Modality:
        return (Modality.CARDINAL, Modality.FIXED, Modality.MUTABLE)[self.index % 3]

    @property
    def is_masculine(self) -> bool:
        # Traditional polarity: fire/air = masculine (yang), earth/water = feminine (yin).
        return self.index % 2 == 0

    @property
    def display(self) -> str:
        return SIGN_NAMES_TR[self]

    @classmethod
    def from_longitude(cls, longitude: float) -> Sign:
        return SIGNS[int((longitude % 360.0) // 30.0)]


SIGNS: list[Sign] = list(Sign)

SIGN_NAMES_TR: dict[Sign, str] = {
    Sign.ARIES: "Koç",
    Sign.TAURUS: "Boğa",
    Sign.GEMINI: "İkizler",
    Sign.CANCER: "Yengeç",
    Sign.LEO: "Aslan",
    Sign.VIRGO: "Başak",
    Sign.LIBRA: "Terazi",
    Sign.SCORPIO: "Akrep",
    Sign.SAGITTARIUS: "Yay",
    Sign.CAPRICORN: "Oğlak",
    Sign.AQUARIUS: "Kova",
    Sign.PISCES: "Balık",
}

ELEMENT_NAMES_TR = {Element.FIRE: "Ateş", Element.EARTH: "Toprak", Element.AIR: "Hava", Element.WATER: "Su"}
MODALITY_NAMES_TR = {Modality.CARDINAL: "Öncü", Modality.FIXED: "Sabit", Modality.MUTABLE: "Değişken"}

# Solar/whole-sign house themes, fed to the LLM as ground truth instead of letting it guess.
HOUSE_THEMES_TR: dict[int, str] = {
    1: "benlik, dış görünüş, yeni başlangıçlar",
    2: "para, kişisel kaynaklar, öz değer",
    3: "iletişim, kardeşler, kısa yolculuklar, yazışmalar",
    4: "ev, aile, kökler, iç huzur",
    5: "aşk, flört, yaratıcılık, keyif",
    6: "günlük iş düzeni, rutinler, iş arkadaşları",
    7: "ortaklıklar, evlilik, ikili ilişkiler, sözleşmeler",
    8: "ortak kaynaklar, borç-alacak, derin bağlar, dönüşüm",
    9: "yüksek öğrenim, uzak yolculuklar, inançlar, hukuk",
    10: "kariyer, statü, hedefler, toplum önündeki imaj",
    11: "arkadaşlar, sosyal çevre, gelecek planları",
    12: "bilinçaltı, geri çekilme, kapanışlar, gizli konular",
}
