"""Pure, model-free tests for DetectionPipeline's merge/corroboration/
normalization algorithms — constructed PIIEntity objects in, no detector or
NLP model needed, so these run fast and pin down the exact merge semantics."""
from services.detection_service import DetectionPipeline
from schemas.common import PIIEntity, PIIType, TextSpan


def _entity(
    pii_type=PIIType.PERSON,
    start=0,
    end=8,
    raw_value="Jane Doe",
    confidence=0.85,
    source_detector="test_detector",
    entity_id=None,
):
    return PIIEntity(
        id=entity_id or f"det_{start}_{end}_{source_detector}",
        pii_type=pii_type,
        span=TextSpan(start=start, end=end),
        raw_value=raw_value,
        confidence=confidence,
        source_detector=source_detector,
    )


class TestMergeOverlaps:
    def test_higher_confidence_wins_overlap(self):
        low = _entity(start=0, end=10, confidence=0.6, source_detector="a")
        high = _entity(start=5, end=15, confidence=0.9, source_detector="b")
        merged = DetectionPipeline._merge_overlaps([low, high])
        assert merged == [high]

    def test_non_overlapping_entities_both_kept(self):
        first = _entity(start=0, end=8, source_detector="a")
        second = _entity(start=20, end=28, source_detector="b")
        merged = DetectionPipeline._merge_overlaps([first, second])
        assert merged == [first, second]

    def test_result_is_ordered_by_start(self):
        first = _entity(start=20, end=28, source_detector="a")
        second = _entity(start=0, end=8, source_detector="b")
        merged = DetectionPipeline._merge_overlaps([first, second])
        assert [e.span.start for e in merged] == [0, 20]

    def test_tie_breaks_on_earlier_start(self):
        first = _entity(start=0, end=8, confidence=0.8, source_detector="a")
        second = _entity(start=4, end=12, confidence=0.8, source_detector="b")
        merged = DetectionPipeline._merge_overlaps([first, second])
        assert merged == [first]

    def test_three_way_overlap_keeps_single_winner(self):
        entities = [
            _entity(start=0, end=10, confidence=0.7, source_detector="a"),
            _entity(start=2, end=12, confidence=0.95, source_detector="b"),
            _entity(start=5, end=9, confidence=0.8, source_detector="c"),
        ]
        merged = DetectionPipeline._merge_overlaps(entities)
        assert len(merged) == 1
        assert merged[0].confidence == 0.95

    def test_deterministic_match_wins_despite_lower_confidence_when_it_contains_fragments(self):
        """Regression test: two NER engines independently (and wrongly)
        tagging a *substring* of a street address as a company, at higher
        confidence than the correct full-address regex match, must not beat
        the regex match — it structurally contains both fragments."""
        address = _entity(
            pii_type=PIIType.ADDRESS, start=0, end=45,
            raw_value="742 Evergreen Terrace, Springfield, IL 62704",
            confidence=0.88, source_detector="regex_detector",
        )
        company_fragment_one = _entity(
            pii_type=PIIType.COMPANY, start=4, end=21, raw_value="Evergreen Terrace",
            confidence=0.90, source_detector="spacy_ner_detector",
        )
        company_fragment_two = _entity(
            pii_type=PIIType.COMPANY, start=37, end=45, raw_value="IL 62704",
            confidence=0.90, source_detector="presidio_detector",
        )
        merged = DetectionPipeline._merge_overlaps([address, company_fragment_one, company_fragment_two])
        assert merged == [address]

    def test_containment_rule_does_not_apply_to_statistical_sources(self):
        """The override is specific to deterministic (regex/date) detectors —
        a lower-confidence NER guess should not get to evict a
        higher-confidence NER guess just because it spans more text."""
        small_high_confidence = _entity(
            pii_type=PIIType.COMPANY, start=4, end=21, raw_value="Evergreen Terrace",
            confidence=0.90, source_detector="presidio_detector",
        )
        large_low_confidence = _entity(
            pii_type=PIIType.PERSON, start=0, end=45,
            raw_value="742 Evergreen Terrace, Springfield, IL 62704",
            confidence=0.5, source_detector="spacy_ner_detector",
        )
        merged = DetectionPipeline._merge_overlaps([small_high_confidence, large_low_confidence])
        assert merged == [small_high_confidence]

    def test_containment_rule_requires_full_containment(self):
        """A deterministic match that only *partially* overlaps a
        higher-confidence statistical entity doesn't qualify — only full
        containment is treated as "this is the same information, more
        precisely delimited"."""
        partial_overlap_regex = _entity(
            pii_type=PIIType.ADDRESS, start=10, end=20,
            confidence=0.88, source_detector="regex_detector",
        )
        higher_confidence_other = _entity(
            pii_type=PIIType.COMPANY, start=0, end=15,
            confidence=0.95, source_detector="presidio_detector",
        )
        merged = DetectionPipeline._merge_overlaps([partial_overlap_regex, higher_confidence_other])
        assert merged == [higher_confidence_other]


class TestBoostCorroborated:
    def test_independent_agreeing_detectors_boost_confidence(self):
        regex_hit = _entity(
            pii_type=PIIType.SSN, start=0, end=11, raw_value="234-56-7890",
            confidence=0.8, source_detector="regex_detector",
        )
        presidio_hit = _entity(
            pii_type=PIIType.SSN, start=0, end=11, raw_value="234-56-7890",
            confidence=0.85, source_detector="presidio_detector",
        )
        boosted = DetectionPipeline._boost_corroborated([regex_hit, presidio_hit])
        for entity in boosted:
            original = regex_hit if entity.source_detector == "regex_detector" else presidio_hit
            assert entity.confidence > original.confidence

    def test_same_detector_does_not_self_corroborate(self):
        one = _entity(start=0, end=8, confidence=0.8, source_detector="regex_detector", entity_id="e1")
        two = _entity(start=1, end=9, confidence=0.8, source_detector="regex_detector", entity_id="e2")
        boosted = DetectionPipeline._boost_corroborated([one, two])
        assert [e.confidence for e in boosted] == [0.8, 0.8]

    def test_dissimilar_overlapping_text_does_not_corroborate(self):
        one = _entity(
            start=0, end=8, raw_value="Jane Doe", confidence=0.8, source_detector="spacy_ner_detector"
        )
        two = _entity(
            pii_type=PIIType.COMPANY, start=0, end=8, raw_value="Zephyr Co",
            confidence=0.8, source_detector="regex_detector",
        )
        boosted = DetectionPipeline._boost_corroborated([one, two])
        assert [e.confidence for e in boosted] == [0.8, 0.8]

    def test_boost_is_capped_at_0_99(self):
        one = _entity(
            pii_type=PIIType.EMAIL, start=0, end=5, raw_value="a@b.co",
            confidence=0.97, source_detector="regex_detector",
        )
        two = _entity(
            pii_type=PIIType.EMAIL, start=0, end=5, raw_value="a@b.co",
            confidence=0.97, source_detector="presidio_detector",
        )
        boosted = DetectionPipeline._boost_corroborated([one, two])
        assert all(e.confidence <= 0.99 for e in boosted)


class TestNormalize:
    def test_trims_trailing_punctuation_and_shrinks_span(self):
        source = "Reach out to jane@example.com, thanks."
        entity = _entity(
            pii_type=PIIType.EMAIL, start=13, end=30,
            raw_value=source[13:30], confidence=0.9,
        )
        assert entity.raw_value == "jane@example.com,"
        normalized = DetectionPipeline._normalize(entity)
        assert normalized.raw_value == "jane@example.com"
        assert source[normalized.span.start : normalized.span.end] == normalized.raw_value

    def test_trims_leading_whitespace(self):
        source = "x  742 Evergreen Terrace y"
        entity = _entity(
            pii_type=PIIType.ADDRESS, start=1, end=len("x  742 Evergreen Terrace"),
            raw_value=source[1 : len("x  742 Evergreen Terrace")], confidence=0.8,
        )
        normalized = DetectionPipeline._normalize(entity)
        assert normalized.raw_value == "742 Evergreen Terrace"
        assert source[normalized.span.start : normalized.span.end] == normalized.raw_value

    def test_rounds_confidence(self):
        entity = _entity(confidence=0.856789123)
        normalized = DetectionPipeline._normalize(entity)
        assert normalized.confidence == 0.8568

    def test_noop_when_already_clean(self):
        entity = _entity(raw_value="Jane Doe", confidence=0.85)
        normalized = DetectionPipeline._normalize(entity)
        assert normalized.raw_value == entity.raw_value
        assert normalized.span == entity.span
        assert normalized.confidence == entity.confidence


class TestFullPipelineRun:
    def test_overlap_resolution_end_to_end(self, monkeypatch):
        """A minimal fake registry proves DetectionPipeline.run() wires
        detect_all -> boost -> merge -> normalize together correctly,
        without needing a real NLP model loaded."""
        from schemas.common import DocumentFormat, ExtractedDocument, TextBlock

        class _FakeRegistry:
            def detect_all(self, text, pii_types):
                return [
                    _entity(
                        pii_type=PIIType.SSN, start=5, end=16,
                        raw_value=text[5:16], confidence=0.97, source_detector="regex_detector",
                    ),
                    _entity(
                        pii_type=PIIType.COMPANY, start=5, end=16,
                        raw_value=text[5:16], confidence=0.8, source_detector="spacy_ner_detector",
                    ),
                ]

        text = "SSN: 234-56-7890."
        document = ExtractedDocument(
            document_id="d1", format=DocumentFormat.DOCX, blocks=[TextBlock(text=text, char_offset=0)]
        )
        pipeline = DetectionPipeline(_FakeRegistry())
        result = pipeline.run(document, {PIIType.SSN, PIIType.COMPANY})

        assert len(result) == 1
        assert result[0].pii_type == PIIType.SSN
        assert text[result[0].span.start : result[0].span.end] == result[0].raw_value
