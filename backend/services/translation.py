"""
Translation layer.

Converts a common meaning_key into text for the selected output language.
This is a small, fixed vocabulary (the recognizable sign set), so a
structured dictionary is used instead of calling an external LLM per sign -
faster, cheaper, and fully deterministic for a demo.

Kept as a standalone data structure so it's easy to extend with more
meaning keys/languages later without touching any other module.
"""

from __future__ import annotations

from typing import Optional

TRANSLATIONS: dict[str, dict[str, str]] = {
    "HELLO": {
        "en": "Hello",
        "ta": "வணக்கம்",
        "hi": "नमस्ते",
        "te": "నమస్కారం",
        "ml": "നമസ്കാരം",
        "kn": "ನಮಸ್ಕಾರ",
    },
    "THANK_YOU": {
        "en": "Thank you",
        "ta": "நன்றி",
        "hi": "धन्यवाद",
        "te": "ధన్యవాదాలు",
        "ml": "നന്ദി",
        "kn": "ಧನ್ಯವಾದಗಳು",
    },
    "PLEASE": {
        "en": "Please",
        "ta": "தயவு செய்து",
        "hi": "कृपया",
        "te": "దయచేసి",
        "ml": "ദയവായി",
        "kn": "ದಯವಿಟ್ಟು",
    },
    "YES": {
        "en": "Yes",
        "ta": "ஆம்",
        "hi": "हाँ",
        "te": "అవును",
        "ml": "അതെ",
        "kn": "ಹೌದು",
    },
    "NO": {
        "en": "No",
        "ta": "இல்லை",
        "hi": "नहीं",
        "te": "కాదు",
        "ml": "ഇല്ല",
        "kn": "ಇಲ್ಲ",
    },
    "GOOD": {
        "en": "Good",
        "ta": "நல்லது",
        "hi": "अच्छा",
        "te": "మంచిది",
        "ml": "നല്ലത്",
        "kn": "ಒಳ್ಳೆಯದು",
    },
    "GOOD_MORNING": {
        "en": "Good morning",
        "ta": "காலை வணக்கம்",
        "hi": "सुप्रभात",
        "te": "శుభోదయం",
        "ml": "സുപ്രഭാതം",
        "kn": "ಶುಭೋದಯ",
    },
    "HOW_ARE_YOU": {
        "en": "How are you?",
        "ta": "எப்படி இருக்கிறீர்கள்?",
        "hi": "आप कैसे हैं?",
        "te": "మీరు ఎలా ఉన్నారు?",
        "ml": "സുഖമാണോ?",
        "kn": "ಹೇಗಿದ್ದೀರಿ?",
    },
}


def translate(meaning_key: str, language: str) -> Optional[str]:
    """Return the translated text for a meaning key + language code, or
    None if either is unsupported."""
    entry = TRANSLATIONS.get(meaning_key.upper())
    if entry is None:
        return None
    return entry.get(language)


def is_supported_language(language: str) -> bool:
    return language in {"en", "ta", "hi", "te", "ml", "kn"}
