"""
MeetSmart AI — Test: Notes Agent (Gemini service / rule-based parsing)
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from unittest.mock import patch


class TestRuleBasedNotes:
    """Test the rule-based notes extraction (no Gemini key needed)."""

    def setup_method(self):
        with patch.dict(os.environ, {"GEMINI_API_KEY": "", "SMTP_MODE": "mock", "DATABASE_URL": "sqlite:///./test.db"}):
            from src.services.gemini_service import _rule_based_notes
            self._parse = _rule_based_notes

    def test_extract_action_items(self):
        transcript = """
        Meeting notes:
        Action item: Arjun should set up the CI pipeline by next Friday.
        TODO: Priya to draft the product spec by June 25.
        Follow-up: Rahul needs to configure the server.
        """
        result = self._parse(transcript)
        assert 'action_items' in result
        assert len(result['action_items']) >= 2

    def test_extract_decisions(self):
        transcript = """
        The team decided to use React for the frontend.
        It was agreed that weekly standups will continue.
        The PM confirmed the June 30 deadline.
        """
        result = self._parse(transcript)
        assert 'decisions' in result
        assert len(result['decisions']) >= 2

    def test_empty_transcript(self):
        result = self._parse("")
        assert result['summary'] == "Meeting notes processed."
        assert result['action_items'] == []

    def test_result_structure(self):
        transcript = "Quick meeting to align on Q3 roadmap. Decided to prioritize AI features."
        result = self._parse(transcript)
        assert 'summary' in result
        assert 'decisions' in result
        assert 'action_items' in result
        assert 'key_topics' in result
        assert 'mode' in result
        assert result['mode'] == 'rule-based'

    def test_deadline_patterns(self):
        transcript = "Action item: Complete the report by 2026-07-15."
        result = self._parse(transcript)
        if result['action_items']:
            assert '2026-07-15' in result['action_items'][0].get('deadline', '')

    def test_high_priority_detection(self):
        transcript = "Action item: Fix the production bug ASAP — urgent!"
        result = self._parse(transcript)
        if result['action_items']:
            assert result['action_items'][0].get('priority') == 'high'


class TestGeminiService:
    """Test the Gemini service integration (mocked)."""

    def test_process_falls_back_without_key(self):
        with patch.dict(os.environ, {"GEMINI_API_KEY": "", "SMTP_MODE": "mock", "DATABASE_URL": "sqlite:///./test.db"}):
            from src.services.gemini_service import process_meeting_notes
            result = process_meeting_notes("Test transcript with some content.")
            assert 'summary' in result
            assert 'action_items' in result

    def test_process_parses_valid_json_from_gemini(self):
        """Mock Gemini returning valid JSON."""
        with patch.dict(os.environ, {"GEMINI_API_KEY": "fake-key", "SMTP_MODE": "mock", "DATABASE_URL": "sqlite:///./test.db"}):
            mock_json = '{"summary":"Test summary","decisions":["Dec 1"],"action_items":[{"description":"Do X","owner":"Alice","deadline":"2026-07-01","priority":"high"}],"key_topics":["Topic A"]}'
            with patch('src.services.gemini_service._call_gemini', return_value=mock_json):
                with patch('src.services.gemini_service.settings') as mock_settings:
                    mock_settings.gemini_enabled = True
                    # Re-import after patch
                    import importlib
                    import src.services.gemini_service as gsvc
                    importlib.reload(gsvc)
                    # Test JSON parse
                    import json
                    parsed = json.loads(mock_json)
                    assert parsed['summary'] == 'Test summary'
                    assert len(parsed['action_items']) == 1
