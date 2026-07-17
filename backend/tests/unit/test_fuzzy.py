from utils.fuzzy import (
    adjust_company_confidence,
    company_suffix_boost,
    fuzzy_contains_keyword,
    looks_like_false_positive_acronym,
    text_similarity,
)


class TestFuzzyContainsKeyword:
    def test_exact_keyword_present(self):
        assert fuzzy_contains_keyword("patient date of birth: 1990") is True

    def test_abbreviation_present(self):
        assert fuzzy_contains_keyword("dob 01/01/1990") is True

    def test_typo_tolerant_match(self):
        assert fuzzy_contains_keyword("date of  birth :") is True

    def test_no_keyword_in_unrelated_text(self):
        assert fuzzy_contains_keyword("invoice due date: 1990") is False

    def test_empty_window(self):
        assert fuzzy_contains_keyword("   ") is False


class TestCompanySuffixBoost:
    def test_known_suffix_scores_high(self):
        assert company_suffix_boost("Acme Corp") > 0.8

    def test_known_suffix_with_period_scores_high(self):
        assert company_suffix_boost("Globex Inc.") > 0.8

    def test_no_suffix_scores_low(self):
        assert company_suffix_boost("Banana") < 0.5

    def test_empty_string_scores_zero(self):
        assert company_suffix_boost("") == 0.0


class TestTextSimilarity:
    def test_identical_strings(self):
        assert text_similarity("Jane Doe", "Jane Doe") == 1.0

    def test_reordered_tokens_still_similar(self):
        assert text_similarity("Doe, Jane", "Jane Doe") > 0.7

    def test_dissimilar_strings(self):
        assert text_similarity("Jane Doe", "192.168.1.1") < 0.4

    def test_empty_strings_are_zero_similarity(self):
        assert text_similarity("", "Jane Doe") == 0.0


class TestLooksLikeFalsePositiveAcronym:
    def test_short_all_caps_token_flagged(self):
        assert looks_like_false_positive_acronym("SSN") is True

    def test_multi_word_name_not_flagged(self):
        assert looks_like_false_positive_acronym("Jane Doe") is False

    def test_lowercase_word_not_flagged(self):
        assert looks_like_false_positive_acronym("company") is False

    def test_long_all_caps_not_flagged(self):
        assert looks_like_false_positive_acronym("INITECHCORP") is False

    def test_empty_string_not_flagged(self):
        assert looks_like_false_positive_acronym("") is False

    def test_bare_number_flagged(self):
        """Regression test from a real document: page/schedule references
        like "104" were tagged COMPANY by spaCy."""
        assert looks_like_false_positive_acronym("104") is True

    def test_lowercase_roman_numeral_flagged(self):
        """Regression test: "xv" (a page-number-style roman numeral in a
        table of contents) was tagged COMPANY."""
        assert looks_like_false_positive_acronym("xv") is True

    def test_uppercase_short_token_still_flagged_by_the_acronym_rule(self):
        """Not a roman-numeral false positive — this is the pre-existing
        short-all-caps rule; a real all-caps company abbreviation that
        happens to only use roman-numeral letters (e.g. "MCI") is a known,
        accepted tradeoff of that unrelated, already-existing rule."""
        assert looks_like_false_positive_acronym("MCI") is True

    def test_currency_symbol_flagged(self):
        assert looks_like_false_positive_acronym("₹") is True

    def test_generic_self_reference_word_flagged(self):
        """Regression test: legal documents capitalize their own defined
        terms ("the Company", "the Board", "the Offer") and NER tags the
        bare capitalized word as an organization."""
        for word in ("Company", "Board", "Offer", "Fiscals"):
            assert looks_like_false_positive_acronym(word) is True, word

    def test_generic_word_as_part_of_a_real_name_not_flagged(self):
        assert looks_like_false_positive_acronym("Vertex Industries") is False

    def test_real_company_name_not_flagged(self):
        assert looks_like_false_positive_acronym("Loksatta") is False


class TestAdjustCompanyConfidence:
    """Regression tests from a real 300-page document: legal/financial text
    constantly capitalizes its own defined terms right after "the"/"our"/
    "this" ("the Offer for Sale", "our Board of Directors", "this Red
    Herring Prospectus"), and NER tags the bare phrase as an organization."""

    def test_discounts_defined_term_after_the(self):
        confidence = adjust_company_confidence("Offer for Sale", 0.9, preceding_word="the")
        assert confidence < 0.75  # must fall below the default review floor

    def test_discounts_defined_term_after_our(self):
        confidence = adjust_company_confidence("Board of Directors", 0.9, preceding_word="our")
        assert confidence < 0.75

    def test_discounts_defined_term_after_this(self):
        confidence = adjust_company_confidence("Red Herring Prospectus", 0.9, preceding_word="this")
        assert confidence < 0.75

    def test_no_preceding_word_is_not_discounted(self):
        confidence = adjust_company_confidence("Board of Directors", 0.9, preceding_word="")
        assert confidence == 0.9

    def test_unrelated_preceding_word_is_not_discounted(self):
        confidence = adjust_company_confidence("Board of Directors", 0.9, preceding_word="joined")
        assert confidence == 0.9

    def test_recognized_company_suffix_overrides_the_discount(self):
        """A real company name can legitimately follow "our"/"the" ("our
        Vertex Industries Ltd.") — a recognized suffix is a strong enough
        signal that it should not be discounted just for the article."""
        confidence = adjust_company_confidence("Vertex Industries Ltd.", 0.9, preceding_word="our")
        assert confidence > 0.9

    def test_acronym_check_takes_priority_over_article_check(self):
        confidence = adjust_company_confidence("SSN", 0.9, preceding_word="the")
        assert confidence == 0.9 * 0.3

    def test_default_preceding_word_is_empty_and_backward_compatible(self):
        """Existing callers that don't pass preceding_word must see
        unchanged behavior."""
        assert adjust_company_confidence("Acme Corp", 0.8) == adjust_company_confidence(
            "Acme Corp", 0.8, preceding_word=""
        )
