from utils.text import context_window, normalize_text, preceding_word


class TestNormalizeText:
    def test_nfkc_normalizes_compatibility_characters(self):
        assert normalize_text("ＡＢＣ") == "ABC"  # fullwidth A B C

    def test_preserves_ordinary_ascii_unchanged(self):
        assert normalize_text("Jane Doe") == "Jane Doe"


class TestContextWindow:
    def test_returns_lowercase_window_around_span(self):
        text = "Patient Date of Birth: 03/14/1990, recorded at intake."
        window = context_window(text, text.index("03/14/1990"), text.index("03/14/1990") + 10, radius=15)
        assert "date of birth" in window

    def test_clamps_to_string_bounds(self):
        text = "short"
        window = context_window(text, 0, len(text), radius=100)
        assert window == "short"


class TestPrecedingWord:
    def test_returns_the_word_immediately_before_a_span(self):
        text = "Reach out to the Offer for Sale team."
        idx = text.index("Offer for Sale")
        assert preceding_word(text, idx) == "the"

    def test_returns_empty_string_at_start_of_text(self):
        text = "Offer for Sale begins today."
        assert preceding_word(text, 0) == ""

    def test_skips_trailing_whitespace_before_the_span(self):
        text = "our   Board of Directors"
        idx = text.index("Board")
        assert preceding_word(text, idx) == "our"

    def test_returns_empty_string_when_preceded_by_punctuation_only(self):
        text = "(Board of Directors)"
        assert preceding_word(text, 1) == ""
