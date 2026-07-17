"""LabeledFieldDetector: a deterministic, model-free fallback for full names
in "Label: Value" form contexts. Pure regex logic — no spaCy/Presidio needed,
so these tests run instantly and pin down the exact matching rules."""
from detectors.labeled_field_detector import LabeledFieldDetector
from schemas.common import PIIType


def _values(entities):
    return [e.raw_value for e in entities]


class TestSupports:
    def test_supports_only_person(self):
        detector = LabeledFieldDetector()
        assert detector.supports(PIIType.PERSON) is True
        assert detector.supports(PIIType.COMPANY) is False
        assert detector.supports(PIIType.EMAIL) is False


class TestLabeledNameDetection:
    def test_detects_name_after_applicant_colon(self):
        """Regression test: spaCy/Presidio return zero entities for this
        exact input — a real, verified NER miss, not a hypothetical one."""
        detector = LabeledFieldDetector()
        entities = detector.detect("Applicant: Rashi Patil", {PIIType.PERSON})
        assert _values(entities) == ["Rashi Patil"]

    def test_detects_name_after_applicant_name_label(self):
        detector = LabeledFieldDetector()
        entities = detector.detect("Applicant Name: Rashi Patil", {PIIType.PERSON})
        assert _values(entities) == ["Rashi Patil"]

    def test_detects_name_after_dear_salutation(self):
        detector = LabeledFieldDetector()
        entities = detector.detect("Dear Rohan Dey, thank you for applying.", {PIIType.PERSON})
        assert _values(entities) == ["Rohan Dey"]

    def test_detects_name_after_contact_person(self):
        detector = LabeledFieldDetector()
        entities = detector.detect("Contact Person: Priya Nair", {PIIType.PERSON})
        assert _values(entities) == ["Priya Nair"]

    def test_detects_name_after_authorized_signatory(self):
        detector = LabeledFieldDetector()
        entities = detector.detect("Authorized Signatory: Vikram Rao", {PIIType.PERSON})
        assert _values(entities) == ["Vikram Rao"]

    def test_detects_hyphenated_and_apostrophe_names(self):
        detector = LabeledFieldDetector()
        entities = detector.detect("Signed by: Al-Rashid O'Brien", {PIIType.PERSON})
        assert _values(entities) == ["Al-Rashid O'Brien"]

    def test_ignores_pii_types_not_requested(self):
        detector = LabeledFieldDetector()
        entities = detector.detect("Applicant: Rashi Patil", set())
        assert entities == []


class TestCrossParagraphSafety:
    def test_does_not_bleed_across_paragraph_break_into_next_label(self):
        """Regression test: an earlier version used \\s+ for the inter-word
        gap, which matches newlines — a name immediately followed by a
        blank-line-separated next field ("Rashi Patil\\n\\nEmail: ...") got
        swallowed whole as "Rashi Patil Email", destroying the next line."""
        detector = LabeledFieldDetector()
        text = "Applicant: Rashi Patil\n\nEmail: rashi.patil@gmail.com"
        entities = detector.detect(text, {PIIType.PERSON})
        assert _values(entities) == ["Rashi Patil"]

    def test_span_matches_raw_value_in_source_text(self):
        detector = LabeledFieldDetector()
        text = "Applicant: Rashi Patil\n\nEmail: rashi.patil@gmail.com"
        entities = detector.detect(text, {PIIType.PERSON})
        for entity in entities:
            assert text[entity.span.start : entity.span.end] == entity.raw_value


class TestFalsePositiveGuards:
    def test_does_not_match_bare_name_label(self):
        """Bare "Name:" is deliberately excluded — too ambiguous (company,
        product, file, document name are all common) — NER remains the
        primary signal for that case."""
        detector = LabeledFieldDetector()
        entities = detector.detect("Name: Rohan Dey", {PIIType.PERSON})
        assert entities == []

    def test_does_not_match_single_capitalized_word(self):
        detector = LabeledFieldDetector()
        entities = detector.detect("Applicant: Confidential", {PIIType.PERSON})
        assert entities == []

    def test_rejects_dear_customer_service_as_a_name(self):
        detector = LabeledFieldDetector()
        entities = detector.detect("Dear Customer Service, please respond.", {PIIType.PERSON})
        assert entities == []

    def test_rejects_dear_team(self):
        detector = LabeledFieldDetector()
        entities = detector.detect("Dear Hiring Team, thanks for your time.", {PIIType.PERSON})
        assert entities == []

    def test_no_match_when_no_trigger_label_present(self):
        detector = LabeledFieldDetector()
        entities = detector.detect("Rashi Patil went to the market.", {PIIType.PERSON})
        assert entities == []


class TestGenericRoleNounsNeedAColon:
    """Regression tests from a real IPO prospectus: "Promoter" and
    "Director" are constantly the first word of an unrelated defined legal
    term in formal financial/legal documents, not a "Label: Name" field —
    without requiring a literal colon, these produced real false positives
    ("Selling Shareholders" and "Identification Number" tagged as PERSON)."""

    def test_promoter_selling_shareholder_is_not_a_name(self):
        detector = LabeledFieldDetector()
        text = "Each of the Promoter Selling Shareholders, severally and not jointly, confirms..."
        entities = detector.detect(text, {PIIType.PERSON})
        assert entities == []

    def test_director_identification_number_is_not_a_name(self):
        detector = LabeledFieldDetector()
        entities = detector.detect("Director Identification Number\n\nDepository Participant", {PIIType.PERSON})
        assert entities == []

    def test_promoter_with_colon_still_matches(self):
        detector = LabeledFieldDetector()
        entities = detector.detect("Promoter: Rashi Patil", {PIIType.PERSON})
        assert _values(entities) == ["Rashi Patil"]

    def test_director_with_colon_still_matches(self):
        detector = LabeledFieldDetector()
        entities = detector.detect("Director: John Smith", {PIIType.PERSON})
        assert _values(entities) == ["John Smith"]

    def test_signatory_witness_guarantor_require_colon_too(self):
        detector = LabeledFieldDetector()
        assert detector.detect("Signatory Authority rests with the board.", {PIIType.PERSON}) == []
        assert detector.detect("Witness Statements were collected.", {PIIType.PERSON}) == []
        assert _values(detector.detect("Witness: Amit Verma", {PIIType.PERSON})) == ["Amit Verma"]


class TestConfidence:
    def test_confidence_clears_default_review_floor(self):
        """Must clear the platform's default 0.75 confidence floor to be
        useful as a standalone recall safety net (see PolicyService's
        DEFAULT_CONFIDENCE_FLOOR)."""
        detector = LabeledFieldDetector()
        entities = detector.detect("Applicant: Rashi Patil", {PIIType.PERSON})
        assert entities[0].confidence >= 0.75
