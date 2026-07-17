from schemas.common import PIIType


def _values(entities, pii_type):
    return [e.raw_value for e in entities if e.pii_type == pii_type]


class TestSupports:
    def test_supports_all_regex_types(self, regex_detector):
        for pii_type in (
            PIIType.SSN,
            PIIType.CREDIT_CARD,
            PIIType.PHONE,
            PIIType.EMAIL,
            PIIType.IP_ADDRESS,
            PIIType.ADDRESS,
        ):
            assert regex_detector.supports(pii_type) is True

    def test_does_not_support_nlp_only_types(self, regex_detector):
        assert regex_detector.supports(PIIType.PERSON) is False
        assert regex_detector.supports(PIIType.COMPANY) is False
        assert regex_detector.supports(PIIType.DOB) is False


class TestSSN:
    def test_detects_formatted_ssn(self, regex_detector):
        entities = regex_detector.detect("SSN: 234-56-7890.", {PIIType.SSN})
        assert _values(entities, PIIType.SSN) == ["234-56-7890"]
        assert entities[0].confidence >= 0.9

    def test_ignores_unformatted_digits(self, regex_detector):
        entities = regex_detector.detect("Order number 234567890123", {PIIType.SSN})
        assert _values(entities, PIIType.SSN) == []


class TestCreditCard:
    def test_detects_luhn_valid_card(self, regex_detector):
        entities = regex_detector.detect("Card: 4539148803436467", {PIIType.CREDIT_CARD})
        assert _values(entities, PIIType.CREDIT_CARD) == ["4539148803436467"]

    def test_rejects_luhn_invalid_number(self, regex_detector):
        entities = regex_detector.detect("Card: 4539148803436468", {PIIType.CREDIT_CARD})
        assert _values(entities, PIIType.CREDIT_CARD) == []

    def test_detects_card_with_spaces(self, regex_detector):
        entities = regex_detector.detect("Card: 4539 1488 0343 6467", {PIIType.CREDIT_CARD})
        assert len(_values(entities, PIIType.CREDIT_CARD)) == 1


class TestEmail:
    def test_detects_email(self, regex_detector):
        entities = regex_detector.detect("Contact jane.doe@example.com now", {PIIType.EMAIL})
        assert _values(entities, PIIType.EMAIL) == ["jane.doe@example.com"]

    def test_no_false_positive_on_plain_text(self, regex_detector):
        entities = regex_detector.detect("no email here", {PIIType.EMAIL})
        assert entities == []


class TestPhone:
    def test_detects_dashed_phone(self, regex_detector):
        entities = regex_detector.detect("Call 555-123-4567 today", {PIIType.PHONE})
        assert _values(entities, PIIType.PHONE) == ["555-123-4567"]

    def test_detects_parenthesized_phone(self, regex_detector):
        entities = regex_detector.detect("Call (415) 555-0199 today", {PIIType.PHONE})
        assert _values(entities, PIIType.PHONE) == ["(415) 555-0199"]


class TestIpAddress:
    def test_detects_valid_ipv4(self, regex_detector):
        entities = regex_detector.detect("Login from 192.168.1.15", {PIIType.IP_ADDRESS})
        assert _values(entities, PIIType.IP_ADDRESS) == ["192.168.1.15"]

    def test_rejects_out_of_range_octets(self, regex_detector):
        entities = regex_detector.detect("Not an IP: 999.999.999.999", {PIIType.IP_ADDRESS})
        assert _values(entities, PIIType.IP_ADDRESS) == []

    def test_detects_ipv6(self, regex_detector):
        entities = regex_detector.detect(
            "Host 2001:0db8:85a3:0000:0000:8a2e:0370:7334", {PIIType.IP_ADDRESS}
        )
        assert len(_values(entities, PIIType.IP_ADDRESS)) == 1


class TestAddress:
    def test_detects_full_street_address(self, regex_detector):
        text = "Mail to 742 Evergreen Terrace, Springfield, IL 62704 please."
        entities = regex_detector.detect(text, {PIIType.ADDRESS})
        values = _values(entities, PIIType.ADDRESS)
        assert values
        assert values[0].startswith("742 Evergreen Terrace")

    def test_detects_six_digit_indian_pin_code(self, regex_detector):
        """Regression test: a 6-digit PIN code used to get truncated to 5
        digits by the ZIP group, which then failed the downstream
        word-boundary safety check and silently dropped the whole address."""
        text = "Address: 14 Residency Road, Bengaluru, KA 560025"
        entities = regex_detector.detect(text, {PIIType.ADDRESS})
        values = _values(entities, PIIType.ADDRESS)
        assert values == ["14 Residency Road, Bengaluru, KA 560025"]

    def test_span_includes_full_postal_code_not_truncated(self, regex_detector):
        text = "Ship to 100 Main St, Springfield, IL 987654 today."
        entities = regex_detector.detect(text, {PIIType.ADDRESS})
        values = _values(entities, PIIType.ADDRESS)
        assert values
        assert values[0].endswith("987654")

    def test_does_not_match_short_suffix_abbreviation_inside_an_unrelated_word(self, regex_detector):
        """Regression test from a real document: "2023 Short Term
        Borrowings" (a financial table heading) was matching "2023 Short
        Ter" as a street address — "Ter" (Terrace) is a valid suffix
        abbreviation and matched as a prefix of "Term" with no word-boundary
        check stopping it."""
        text = "2023 Short Term Borrowings increased year over year."
        entities = regex_detector.detect(text, {PIIType.ADDRESS})
        assert entities == []

    def test_does_not_match_dr_inside_an_unrelated_word(self, regex_detector):
        text = "12 New Drought conditions were reported across the region."
        entities = regex_detector.detect(text, {PIIType.ADDRESS})
        assert entities == []


class TestSpanIntegrity:
    def test_span_matches_raw_value_in_source_text(self, regex_detector):
        text = "Email jane.doe@example.com and SSN 234-56-7890 on file."
        entities = regex_detector.detect(text, {PIIType.EMAIL, PIIType.SSN})
        for entity in entities:
            assert text[entity.span.start : entity.span.end] == entity.raw_value
