"""
Tests for translator module.
"""
import pytest
import responses
from translator import OpenRouterTranslator
from subtitle_parser import SubtitleEntry


class TestOpenRouterTranslator:
    """Test OpenRouterTranslator class."""

    def create_entry(self, index, text, start_ms=1000, end_ms=2000):
        """Helper to create a subtitle entry."""
        return SubtitleEntry(
            index=index,
            start_time=f"00:00:{start_ms//1000:02d}.{start_ms%1000:03d}",
            end_time=f"00:00:{end_ms//1000:02d}.{end_ms%1000:03d}",
            text=text,
            start_ms=start_ms,
            end_ms=end_ms
        )

    def test_translator_initialization(self):
        """Test translator initialization."""
        translator = OpenRouterTranslator(
            api_key="test_key",
            model="test/model",
            source_language="english",
            target_language="polish"
        )

        assert translator.api_key == "test_key"
        assert translator.model == "test/model"
        assert translator.source_language == "english"
        assert translator.target_language == "polish"

    def test_create_translation_prompt(self):
        """Test creating translation prompt."""
        translator = OpenRouterTranslator(
            api_key="test_key",
            model="test/model",
            source_language="english",
            target_language="polish"
        )

        entries = [
            self.create_entry(1, "Hello, world!"),
            self.create_entry(2, "How are you?"),
        ]

        prompt = translator._create_translation_prompt(entries)

        # Check that prompt contains key elements
        assert "english" in prompt.lower()
        assert "polish" in prompt.lower()
        assert "1|Hello, world!" in prompt
        assert "2|How are you?" in prompt
        assert "INDEX|TEXT" in prompt or "index" in prompt.lower()

    def test_parse_translation_response(self):
        """Test parsing translation API response."""
        translator = OpenRouterTranslator(
            api_key="test_key",
            model="test/model"
        )

        original_entries = [
            self.create_entry(1, "Hello", 1000, 2000),
            self.create_entry(2, "World", 3000, 4000),
        ]

        response = """1|Witaj
2|Świat"""

        translated = translator._parse_translation_response(response, original_entries)

        assert len(translated) == 2
        assert translated[0].text == "Witaj"
        assert translated[0].index == 1
        assert translated[0].start_ms == 1000  # Timestamps preserved
        assert translated[0].end_ms == 2000

        assert translated[1].text == "Świat"
        assert translated[1].index == 2
        assert translated[1].start_ms == 3000
        assert translated[1].end_ms == 4000

    def test_parse_translation_response_with_extra_whitespace(self):
        """Test parsing response with extra whitespace."""
        translator = OpenRouterTranslator(
            api_key="test_key",
            model="test/model"
        )

        original_entries = [
            self.create_entry(1, "Hello", 1000, 2000),
        ]

        response = """
        1  |  Witaj with spaces

        """

        translated = translator._parse_translation_response(response, original_entries)

        assert len(translated) == 1
        assert translated[0].text == "Witaj with spaces"

    def test_parse_translation_response_missing_entries(self):
        """Test parsing response with missing entries."""
        translator = OpenRouterTranslator(
            api_key="test_key",
            model="test/model"
        )

        original_entries = [
            self.create_entry(1, "Hello", 1000, 2000),
            self.create_entry(2, "World", 3000, 4000),
        ]

        # Response only has entry 1
        response = """1|Witaj"""

        translated = translator._parse_translation_response(response, original_entries)

        # Should only return what was translated
        assert len(translated) == 1
        assert translated[0].index == 1

    def test_parse_translation_response_invalid_format(self):
        """Test parsing response with invalid format."""
        translator = OpenRouterTranslator(
            api_key="test_key",
            model="test/model"
        )

        original_entries = [
            self.create_entry(1, "Hello", 1000, 2000),
        ]

        # Invalid response (no pipe separator)
        response = """1 Witaj without pipe"""

        translated = translator._parse_translation_response(response, original_entries)

        # Should return empty list
        assert len(translated) == 0

    @responses.activate
    def test_call_api_success(self):
        """Test successful API call."""
        responses.add(
            responses.POST,
            "https://openrouter.ai/api/v1/chat/completions",
            json={
                "choices": [
                    {
                        "message": {
                            "content": "1|Translated text"
                        }
                    }
                ]
            },
            status=200
        )

        translator = OpenRouterTranslator(
            api_key="test_key",
            model="test/model"
        )

        result = translator._call_api("Test prompt")
        assert result == "1|Translated text"

    @responses.activate
    def test_call_api_error(self):
        """Test API call with error response."""
        responses.add(
            responses.POST,
            "https://openrouter.ai/api/v1/chat/completions",
            json={"error": "Invalid API key"},
            status=401
        )

        translator = OpenRouterTranslator(
            api_key="invalid_key",
            model="test/model"
        )

        with pytest.raises(Exception) as exc_info:
            translator._call_api("Test prompt")

        assert "401" in str(exc_info.value)

    @responses.activate
    def test_call_api_unexpected_response(self):
        """Test API call with unexpected response format."""
        responses.add(
            responses.POST,
            "https://openrouter.ai/api/v1/chat/completions",
            json={"unexpected": "format"},
            status=200
        )

        translator = OpenRouterTranslator(
            api_key="test_key",
            model="test/model"
        )

        with pytest.raises(Exception) as exc_info:
            translator._call_api("Test prompt")

        assert "Unexpected" in str(exc_info.value)

    @responses.activate
    def test_translate_batch(self, capsys):
        """Test translating a batch of entries."""
        responses.add(
            responses.POST,
            "https://openrouter.ai/api/v1/chat/completions",
            json={
                "choices": [
                    {
                        "message": {
                            "content": "1|Witaj\n2|Świat"
                        }
                    }
                ]
            },
            status=200
        )

        translator = OpenRouterTranslator(
            api_key="test_key",
            model="test/model",
            source_language="english",
            target_language="polish"
        )

        entries = [
            self.create_entry(1, "Hello", 1000, 2000),
            self.create_entry(2, "World", 3000, 4000),
        ]

        result = translator.translate_batch(entries, 1, 1)

        assert len(result) == 2
        assert result[0].text == "Witaj"
        assert result[1].text == "Świat"

        # Check console output
        captured = capsys.readouterr()
        assert "Translating batch 1/1" in captured.out

    @responses.activate
    def test_translate_batch_with_retry(self, capsys):
        """Test batch translation with retry on mismatch."""
        # First call returns wrong number of entries
        responses.add(
            responses.POST,
            "https://openrouter.ai/api/v1/chat/completions",
            json={
                "choices": [
                    {
                        "message": {
                            "content": "1|Only one"
                        }
                    }
                ]
            },
            status=200
        )

        # Second call returns correct entries
        responses.add(
            responses.POST,
            "https://openrouter.ai/api/v1/chat/completions",
            json={
                "choices": [
                    {
                        "message": {
                            "content": "1|First\n2|Second"
                        }
                    }
                ]
            },
            status=200
        )

        translator = OpenRouterTranslator(
            api_key="test_key",
            model="test/model"
        )

        entries = [
            self.create_entry(1, "Hello", 1000, 2000),
            self.create_entry(2, "World", 3000, 4000),
        ]

        result = translator.translate_batch(entries, 1, 1)

        assert len(result) == 2
        assert result[0].text == "First"
        assert result[1].text == "Second"

        # Check that warning was printed
        captured = capsys.readouterr()
        assert "Warning" in captured.out or "Retrying" in captured.out

    @responses.activate
    def test_translate_all(self, capsys):
        """Test translating all entries in batches."""
        # Mock two API calls (two batches)
        for i in range(2):
            responses.add(
                responses.POST,
                "https://openrouter.ai/api/v1/chat/completions",
                json={
                    "choices": [
                        {
                            "message": {
                                "content": f"{i*2+1}|Batch{i+1}_1\n{i*2+2}|Batch{i+1}_2"
                            }
                        }
                    ]
                },
                status=200
            )

        translator = OpenRouterTranslator(
            api_key="test_key",
            model="test/model"
        )

        all_entries = [
            self.create_entry(1, "Entry 1"),
            self.create_entry(2, "Entry 2"),
            self.create_entry(3, "Entry 3"),
            self.create_entry(4, "Entry 4"),
        ]

        batch1 = all_entries[:2]
        batch2 = all_entries[2:]
        batches = [batch1, batch2]

        result = translator.translate_all(all_entries, batches, delay_between_batches=0)

        assert len(result) == 4
        assert result[0].text == "Batch1_1"
        assert result[1].text == "Batch1_2"
        assert result[2].text == "Batch2_1"
        assert result[3].text == "Batch2_2"

        captured = capsys.readouterr()
        assert "Starting translation" in captured.out
        assert "Translation complete" in captured.out
