from utils.fuzzy import (
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
