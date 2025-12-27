"""
Shared pytest fixtures and configuration.
"""
import pytest
import tempfile
import os
from pathlib import Path

from subtitle_parser import SubtitleEntry


@pytest.fixture
def temp_srt_file():
    """Create a temporary SRT file for testing."""
    content = """1
00:00:01,000 --> 00:00:03,500
Hello, world!

2
00:00:04,000 --> 00:00:06,500
This is a test.

3
00:00:12,000 --> 00:00:15,500
After a gap.
"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.srt', delete=False) as f:
        f.write(content)
        temp_path = f.name

    yield temp_path

    # Cleanup
    if os.path.exists(temp_path):
        os.unlink(temp_path)


@pytest.fixture
def temp_vtt_file():
    """Create a temporary VTT file for testing."""
    content = """WEBVTT

00:00:01.000 --> 00:00:03.500
Hello from VTT!

00:00:04.000 --> 00:00:06.500
This is a WebVTT test.
"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.vtt', delete=False) as f:
        f.write(content)
        temp_path = f.name

    yield temp_path

    # Cleanup
    if os.path.exists(temp_path):
        os.unlink(temp_path)


@pytest.fixture
def sample_entries():
    """Create sample subtitle entries for testing."""
    return [
        SubtitleEntry(
            index=1,
            start_time="00:00:01.000",
            end_time="00:00:03.500",
            text="First subtitle",
            start_ms=1000,
            end_ms=3500
        ),
        SubtitleEntry(
            index=2,
            start_time="00:00:04.000",
            end_time="00:00:06.500",
            text="Second subtitle",
            start_ms=4000,
            end_ms=6500
        ),
        SubtitleEntry(
            index=3,
            start_time="00:00:12.000",
            end_time="00:00:15.500",
            text="Third subtitle after gap",
            start_ms=12000,
            end_ms=15500
        )
    ]


@pytest.fixture
def temp_output_file():
    """Create a temporary output file path."""
    fd, temp_path = tempfile.mkstemp(suffix='.srt')
    os.close(fd)
    os.unlink(temp_path)  # Remove the file, just use the path

    yield temp_path

    # Cleanup
    if os.path.exists(temp_path):
        os.unlink(temp_path)


@pytest.fixture
def mock_api_key():
    """Provide a mock API key for testing."""
    return "test_api_key_12345"


@pytest.fixture
def mock_openrouter_response():
    """Provide a mock OpenRouter API response."""
    return {
        "choices": [
            {
                "message": {
                    "content": "1|Translated text"
                }
            }
        ]
    }
