from typing import Dict, Literal

from typing_extensions import TypeAlias

NumberingLangT: TypeAlias = Literal[
    "arabic",
    "chinese_simple",
    "chinese_traditional",
    "roman",
    "roman_lower",
    "letter_upper",
    "letter_lower",
    "greek_upper",
    "greek_lower",
    "circled",
    "parenthesized",
    "japanese_kanji",
    "japanese_kana",
    "arabic_indic",
    "devanagari",
    "hebrew",
    "tian_gan",
    "di_zhi",
    "emoji",
]

numbering_systems: Dict[int, Dict[NumberingLangT, str]] = {
    # 基础数字
    1: {
        "arabic": "1",
        "chinese_simple": "一",
        "chinese_traditional": "壹",
        "roman": "I",
        "roman_lower": "i",
        "letter_upper": "A",
        "letter_lower": "a",
        "greek_upper": "Α",  # Alpha
        "greek_lower": "α",
        "circled": "①",
        "parenthesized": "⑴",
        "japanese_kanji": "一",
        "japanese_kana": "いち",
        "arabic_indic": "١",  # Arabic numeral 1
        "devanagari": "१",  # Hindi/Sanskrit
        "hebrew": "א",  # Aleph
        "tian_gan": "甲",  # 天干
        "di_zhi": "子",  # 地支
        "emoji": "1️⃣",
    },
    2: {
        "arabic": "2",
        "chinese_simple": "二",
        "chinese_traditional": "貳",
        "roman": "II",
        "roman_lower": "ii",
        "letter_upper": "B",
        "letter_lower": "b",
        "greek_upper": "Β",  # Beta
        "greek_lower": "β",
        "circled": "②",
        "parenthesized": "⑵",
        "japanese_kanji": "二",
        "japanese_kana": "に",
        "arabic_indic": "٢",
        "devanagari": "२",
        "hebrew": "ב",  # Bet
        "tian_gan": "乙",
        "di_zhi": "丑",
        "emoji": "2️⃣",
    },
    3: {
        "arabic": "3",
        "chinese_simple": "三",
        "chinese_traditional": "叁",
        "roman": "III",
        "roman_lower": "iii",
        "letter_upper": "C",
        "letter_lower": "c",
        "greek_upper": "Γ",  # Gamma
        "greek_lower": "γ",
        "circled": "③",
        "parenthesized": "⑶",
        "japanese_kanji": "三",
        "japanese_kana": "さん",
        "arabic_indic": "٣",
        "devanagari": "३",
        "hebrew": "ג",  # Gimel
        "tian_gan": "丙",
        "di_zhi": "寅",
        "emoji": "3️⃣",
    },
    4: {
        "arabic": "4",
        "chinese_simple": "四",
        "chinese_traditional": "肆",
        "roman": "IV",
        "roman_lower": "iv",
        "letter_upper": "D",
        "letter_lower": "d",
        "greek_upper": "Δ",  # Delta
        "greek_lower": "δ",
        "circled": "④",
        "parenthesized": "⑷",
        "japanese_kanji": "四",
        "japanese_kana": "し／よん",
        "arabic_indic": "٤",
        "devanagari": "४",
        "hebrew": "ד",  # Dalet
        "tian_gan": "丁",
        "di_zhi": "卯",
        "emoji": "4️⃣",
    },
    5: {
        "arabic": "5",
        "chinese_simple": "五",
        "chinese_traditional": "伍",
        "roman": "V",
        "roman_lower": "v",
        "letter_upper": "E",
        "letter_lower": "e",
        "greek_upper": "Ε",  # Epsilon
        "greek_lower": "ε",
        "circled": "⑤",
        "parenthesized": "⑸",
        "japanese_kanji": "五",
        "japanese_kana": "ご",
        "arabic_indic": "٥",
        "devanagari": "५",
        "hebrew": "ה",  # He
        "tian_gan": "戊",
        "di_zhi": "辰",
        "emoji": "5️⃣",
    },
    6: {
        "arabic": "6",
        "chinese_simple": "六",
        "chinese_traditional": "陸",
        "roman": "VI",
        "roman_lower": "vi",
        "letter_upper": "F",
        "letter_lower": "f",
        "greek_upper": "Ζ",  # Zeta
        "greek_lower": "ζ",
        "circled": "⑥",
        "parenthesized": "⑹",
        "japanese_kanji": "六",
        "japanese_kana": "ろく",
        "arabic_indic": "٦",
        "devanagari": "६",
        "hebrew": "ו",  # Vav
        "tian_gan": "己",
        "di_zhi": "巳",
        "emoji": "6️⃣",
    },
    7: {
        "arabic": "7",
        "chinese_simple": "七",
        "chinese_traditional": "柒",
        "roman": "VII",
        "roman_lower": "vii",
        "letter_upper": "G",
        "letter_lower": "g",
        "greek_upper": "Η",  # Eta
        "greek_lower": "η",
        "circled": "⑦",
        "parenthesized": "⑺",
        "japanese_kanji": "七",
        "japanese_kana": "しち／なな",
        "arabic_indic": "٧",
        "devanagari": "७",
        "hebrew": "ז",  # Zayin
        "tian_gan": "庚",
        "di_zhi": "午",
        "emoji": "7️⃣",
    },
    8: {
        "arabic": "8",
        "chinese_simple": "八",
        "chinese_traditional": "捌",
        "roman": "VIII",
        "roman_lower": "viii",
        "letter_upper": "H",
        "letter_lower": "h",
        "greek_upper": "Θ",  # Theta
        "greek_lower": "θ",
        "circled": "⑧",
        "parenthesized": "⑻",
        "japanese_kanji": "八",
        "japanese_kana": "はち",
        "arabic_indic": "٨",
        "devanagari": "८",
        "hebrew": "ח",  # Het
        "tian_gan": "辛",
        "di_zhi": "未",
        "emoji": "8️⃣",
    },
    9: {
        "arabic": "9",
        "chinese_simple": "九",
        "chinese_traditional": "玖",
        "roman": "IX",
        "roman_lower": "ix",
        "letter_upper": "I",
        "letter_lower": "i",
        "greek_upper": "Ι",  # Iota
        "greek_lower": "ι",
        "circled": "⑨",
        "parenthesized": "⑼",
        "japanese_kanji": "九",
        "japanese_kana": "きゅう／く",
        "arabic_indic": "٩",
        "devanagari": "९",
        "hebrew": "ט",  # Tet
        "tian_gan": "壬",
        "di_zhi": "申",
        "emoji": "9️⃣",
    },
    10: {
        "arabic": "10",
        "chinese_simple": "十",
        "chinese_traditional": "拾",
        "roman": "X",
        "roman_lower": "x",
        "letter_upper": "J",
        "letter_lower": "j",
        "greek_upper": "Κ",  # Kappa
        "greek_lower": "κ",
        "circled": "⑩",
        "parenthesized": "⑽",
        "japanese_kanji": "十",
        "japanese_kana": "じゅう",
        "arabic_indic": "١٠",
        "devanagari": "१०",
        "hebrew": "י",  # Yod
        "tian_gan": "癸",
        "di_zhi": "酉",
        "emoji": "🔟",  # 10的emoji是特殊符号
    },
}


def numbering(num: int, lang: NumberingLangT):
    try:
        return numbering_systems[num][lang]
    except KeyError:
        return str(num)


class UserInput:
    def __init__(self, index: int = 1, numbering_lang: NumberingLangT = "arabic"):
        self.index = index
        self.numbering_lang = numbering_lang

    def incr(self, n: int = 1):
        self.index += n

    def decr(self, n: int = 1):
        self.index -= n

    @property
    def index_str(self):
        return f"{numbering(self.index, self.numbering_lang)}. "

    def __call__(self, prompt: str = None):
        r = input(f"{self.index_str}{prompt}")
        self.incr(1)
        return r


def print_to_user(*args, sep=" ", end="\n", flush=False, **kwargs):
    return print(*args, sep=sep, end=end, flush=flush, **kwargs)
