"""RapidFuzz-backed fuzzy matching used to make the detection engine more
robust than exact string/regex checks alone: context-keyword lookups that
tolerate punctuation or typo noise, a company-suffix gazetteer used to score
how "company-shaped" a NER candidate is, and a text-similarity helper used to
corroborate two detectors that independently found the same value."""
from __future__ import annotations

from rapidfuzz import fuzz, process

DOB_CONTEXT_KEYWORDS: tuple[str, ...] = (
    "date of birth",
    "dob",
    "born",
    "birth date",
    "birthdate",
    "birthday",
    "b-day",
)

COMPANY_SUFFIXES: tuple[str, ...] = (
    "inc",
    "incorporated",
    "corp",
    "corporation",
    "llc",
    "l.l.c.",
    "ltd",
    "limited",
    "co",
    "company",
    "group",
    "holdings",
    "technologies",
    "industries",
    "enterprises",
    "partners",
    "llp",
    "plc",
)


def fuzzy_contains_keyword(
    window: str, keywords: tuple[str, ...] = DOB_CONTEXT_KEYWORDS, threshold: float = 85.0
) -> bool:
    """True if any keyword plausibly appears in `window`, tolerating minor
    punctuation or typo noise (e.g. "Date of  Birth:" or "D.O.B-")."""
    if not window.strip():
        return False
    for keyword in keywords:
        if keyword in window:  # cheap exact check first
            return True
        if fuzz.partial_ratio(keyword, window) >= threshold:
            return True
    return False


def company_suffix_boost(candidate: str) -> float:
    """0.0-1.0 signal: how strongly the candidate's trailing token resembles
    a known company suffix (Inc, Corp, LLC, ...). A high score_cutoff is
    deliberate: fuzz.ratio on short, generic words is noisy (e.g. "Terrace"
    vs "Partners" scores ~55 purely from shared letters) — only a near-exact
    match should count as a real suffix, not a partial-credit ratio."""
    tokens = candidate.strip().strip(".,").split()
    if not tokens:
        return 0.0
    tail = tokens[-1].lower().strip(".,")
    match = process.extractOne(tail, COMPANY_SUFFIXES, scorer=fuzz.ratio, score_cutoff=90)
    if match is None:
        return 0.0
    _, score, _ = match
    return score / 100.0


def text_similarity(a: str, b: str) -> float:
    """0.0-1.0 similarity, token-order independent — handles the small
    boundary drift between two detectors' matches of the same value."""
    if not a or not b:
        return 0.0
    return fuzz.token_sort_ratio(a, b) / 100.0


def looks_like_false_positive_acronym(candidate: str) -> bool:
    """Guards against spaCy tagging short all-caps form labels (SSN, DOB,
    IP, ...) as an organization — a common false positive on tabular/form text."""
    stripped = candidate.strip()
    return bool(stripped) and stripped.isupper() and len(stripped) <= 5 and " " not in stripped


def adjust_company_confidence(candidate_text: str, base_confidence: float) -> float:
    """The single place COMPANY confidence gets shaped, shared by every NER
    adapter (spaCy, Presidio, ...) so a false positive isn't fixed in one
    engine and left live in another: discount short all-caps acronyms (a
    common false positive on form/tabular text — "SSN", "DOB", "IP"), and
    reward a recognized company suffix."""
    if looks_like_false_positive_acronym(candidate_text):
        return base_confidence * 0.3
    boost = company_suffix_boost(candidate_text)
    return min(0.97, base_confidence + boost * 0.15)
