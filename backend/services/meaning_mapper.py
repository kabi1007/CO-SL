"""
Common meaning layer.

ASL and ISL are different models with different label vocabularies
(different casing, different word sets). This module normalizes each
model's raw label into a shared semantic meaning_key so the translation
layer never needs to know which sign language produced a prediction.

Only meaning keys with a real, verified label mapping below are supported.
Nothing is invented.
"""

from __future__ import annotations

from typing import Optional

# Maps each recognizer's raw label -> shared semantic meaning key.
# ASL labels come from cosl_asl_5words_labels.json (lowercase, per section 9).
# ISL labels come from cosl_isl_5words_labels.json (per section 12).
LABEL_TO_MEANING = {
    "ASL": {
        "hello": "HELLO",
        "thankyou": "THANK_YOU",
        "please": "PLEASE",
        "yes": "YES",
        "no": "NO",
    },
    "ISL": {
        "Hello": "HELLO",
        "Thank_you": "THANK_YOU",
        "Good": "GOOD",
        "Good_Morning": "GOOD_MORNING",
        "How_are_you": "HOW_ARE_YOU",
    },
}


def to_meaning_key(sign_language: str, raw_label: str) -> Optional[str]:
    """Map a recognizer's raw label to a common meaning key.

    Returns None if the label isn't in the known vocabulary for that
    sign language (e.g. an unexpected label index) rather than guessing.
    """
    table = LABEL_TO_MEANING.get(sign_language.upper())
    if table is None:
        return None
    return table.get(raw_label)
