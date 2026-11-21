import re
from pydantic import BaseModel

class GuardrailResult(BaseModel):
    allowed: bool
    reason: str = ""
    sanitized_text: str = ""

# Common prompt-injection patterns
INJECTION_PATTERNS = [
    r"ignore (all )?(previous|prior) instructions",
    r"disregard your system prompt",
    r"you are now in developer mode",
    r"override (all )?safety rules",
]

# India housing & rental discriminatory/exclusionary patterns (active when region == "IN")
INDIA_HOUSING_PATTERNS = [
    # 1. Religion & Caste-based exclusions (Article 15 / SC/ST Act protections)
    r"\b(hindu|muslim|christian|sikh|jain|parsi|brahmin|upper\s*caste)\s*(only|preferred|tenants?\s*only)\b",
    r"\bno\s*(muslims?|christians?|dalits?|sc/st|lower\s*caste)\b",
    r"\b(caste|religion)\s*bar\b",

    # 2. Dietary restrictions (commonly used as a proxy for caste/religious exclusion in India)
    r"\b(pure\s*)?veg(etarian)?s?\s*(only|preferred)\b",
    r"\bno\s*non[-\s]?veg\b",

    # 3. Marital status & Household type (very common in Indian metro cities)
    r"\b(family|families|married\s*couples?)\s*only\b",
    r"\bno\s*(bachelors?|unmarried|singles?|live[-\s]?in)\b",

    # 4. Gender-specific restrictions (often legal for PGs/hostels, but flagged in general apartments)
    r"\b(boys|girls|males?|females?|men|women|working\s*(men|women))\s*only\b",
    r"\bno\s*(boys|girls|male\s*guests?|opposite\s*sex)\b",

    # 5. Regional / Linguistic / Nationality exclusions
    r"\b(locals?|maharashtrians?|kannadigas?|tamils?|gujaratis?|north\s*indians?|south\s*indians?)\s*only\b",
    r"\bno\s*(foreigners?|africans?|nigerians?|north\s*indians?|south\s*indians?)\b",
]

# Indian PII patterns (Aadhaar, PAN, Indian Mobile, 16-digit Card)
PII_PATTERNS = [
    (r"\b[2-9]\d{3}[\s-]?\d{4}[\s-]?\d{4}\b", "[REDACTED-AADHAAR]"),
    (r"\b[A-Z]{5}\d{4}[A-Z]\b", "[REDACTED-PAN]"),
    (r"\b(?:\+91[\s-]?)?[6-9]\d{9}\b", "[REDACTED-PHONE]"),
    (r"\b(?:\d[ -]*?){16}\b", "[REDACTED-CARD]"),
]

def check_input_guardrails(text: str, compliance_region: str = "IN") -> GuardrailResult:
    """Validate user input against prompt injection and Indian housing guidelines."""
    lowered = text.lower()

    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, lowered):
            return GuardrailResult(
                allowed=False,
                reason="Potential prompt injection detected.",
            )

    if compliance_region.upper() == "IN":
        for pattern in INDIA_HOUSING_PATTERNS:
            if re.search(pattern, lowered):
                return GuardrailResult(
                    allowed=False,
                    reason="Request conflicts with IN housing compliance guidelines.",
                )

    return GuardrailResult(allowed=True, sanitized_text=text)


def redact_output_pii(text: str) -> str:
    """Scrub sensitive PII patterns from agent responses before returning to users."""
    cleaned = text
    for pattern, replacement in PII_PATTERNS:
        cleaned = re.sub(pattern, replacement, cleaned)
    return cleaned