"""
Tests for subtitle_parser module.
"""
import pytest
from pathlib import Path
import tempfile
import os

from subtitle_parser import SubtitleParser, SubtitleEntry


class TestSubtitleParser:
    """Test SubtitleParser class."""

    def test_time_to_ms_with_comma(self):
        """Test converting SRT time format with comma to milliseconds."""
        result = SubtitleParser._time_to_ms("00:01:23,456")
        assert result == 83456  # 1*60*1000 + 23*1000 + 456

    def test_time_to_ms_with_dot(self):
        """Test converting time format with dot to milliseconds."""
        result = SubtitleParser._time_to_ms("00:01:23.456")
        assert result == 83456

    def test_time_to_ms_zero(self):
        """Test converting zero time."""
        result = SubtitleParser._time_to_ms("00:00:00.000")
        assert result == 0

    def test_time_to_ms_hours(self):
        """Test converting time with hours."""
        result = SubtitleParser._time_to_ms("01:30:45.123")
        assert result == 5445123  # 1*3600*1000 + 30*60*1000 + 45*1000 + 123

    def test_ms_to_time(self):
        """Test converting milliseconds back to SRT time format."""
        result = SubtitleParser._ms_to_time(83456)
        assert result == "00:01:23,456"

    def test_ms_to_time_zero(self):
        """Test converting zero milliseconds."""
        result = SubtitleParser._ms_to_time(0)
        assert result == "00:00:00,000"

    def test_ms_to_time_hours(self):
        """Test converting milliseconds with hours."""
        result = SubtitleParser._ms_to_time(5445123)
        assert result == "01:30:45,123"

    def test_parse_srt_basic(self):
        """Test parsing a basic SRT file."""
        srt_content = """1
00:00:01,000 --> 00:00:03,500
Hello, world!

2
00:00:04,000 --> 00:00:06,500
This is a test.
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.srt', delete=False) as f:
            f.write(srt_content)
            temp_path = f.name

        try:
            entries = SubtitleParser.parse_file(temp_path)

            assert len(entries) == 2

            assert entries[0].index == 1
            assert entries[0].text == "Hello, world!"
            assert entries[0].start_ms == 1000
            assert entries[0].end_ms == 3500

            assert entries[1].index == 2
            assert entries[1].text == "This is a test."
            assert entries[1].start_ms == 4000
            assert entries[1].end_ms == 6500
        finally:
            os.unlink(temp_path)

    def test_parse_srt_multiline_text(self):
        """Test parsing SRT with multiline subtitle text."""
        srt_content = """1
00:00:01,000 --> 00:00:03,500
Line one
Line two
Line three

2
00:00:04,000 --> 00:00:06,500
Single line
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.srt', delete=False) as f:
            f.write(srt_content)
            temp_path = f.name

        try:
            entries = SubtitleParser.parse_file(temp_path)

            assert len(entries) == 2
            assert entries[0].text == "Line one Line two Line three"
            assert entries[1].text == "Single line"
        finally:
            os.unlink(temp_path)

    def test_parse_srt_with_dot_separator(self):
        """Test parsing SRT with dot as decimal separator."""
        srt_content = """1
00:00:01.000 --> 00:00:03.500
Test with dots
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.srt', delete=False) as f:
            f.write(srt_content)
            temp_path = f.name

        try:
            entries = SubtitleParser.parse_file(temp_path)

            assert len(entries) == 1
            assert entries[0].start_ms == 1000
            assert entries[0].end_ms == 3500
        finally:
            os.unlink(temp_path)

    def test_parse_vtt_basic(self):
        """Test parsing a basic VTT file."""
        vtt_content = """WEBVTT

00:00:01.000 --> 00:00:03.500
Hello from VTT!

00:00:04.000 --> 00:00:06.500
This is a WebVTT test.
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.vtt', delete=False) as f:
            f.write(vtt_content)
            temp_path = f.name

        try:
            entries = SubtitleParser.parse_file(temp_path)

            assert len(entries) == 2
            assert entries[0].text == "Hello from VTT!"
            assert entries[1].text == "This is a WebVTT test."
        finally:
            os.unlink(temp_path)

    def test_write_srt(self):
        """Test writing SRT file."""
        entries = [
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
            )
        ]

        with tempfile.NamedTemporaryFile(mode='w', suffix='.srt', delete=False) as f:
            temp_path = f.name

        try:
            SubtitleParser.write_srt(entries, temp_path)

            # Read back and verify
            with open(temp_path, 'r', encoding='utf-8') as f:
                content = f.read()

            assert "1\n" in content
            assert "00:00:01,000 --> 00:00:03,500" in content
            assert "First subtitle" in content
            assert "2\n" in content
            assert "00:00:04,000 --> 00:00:06,500" in content
            assert "Second subtitle" in content
        finally:
            os.unlink(temp_path)

    def test_calculate_gap(self):
        """Test calculating gap between subtitle entries."""
        entry1 = SubtitleEntry(
            index=1,
            start_time="00:00:01.000",
            end_time="00:00:03.500",
            text="First",
            start_ms=1000,
            end_ms=3500
        )
        entry2 = SubtitleEntry(
            index=2,
            start_time="00:00:06.500",
            end_time="00:00:09.000",
            text="Second",
            start_ms=6500,
            end_ms=9000
        )

        gap = SubtitleParser.calculate_gap(entry1, entry2)
        assert gap == 3.0  # 6500 - 3500 = 3000ms = 3s

    def test_calculate_gap_no_gap(self):
        """Test calculating gap when subtitles are adjacent."""
        entry1 = SubtitleEntry(
            index=1,
            start_time="00:00:01.000",
            end_time="00:00:03.500",
            text="First",
            start_ms=1000,
            end_ms=3500
        )
        entry2 = SubtitleEntry(
            index=2,
            start_time="00:00:03.500",
            end_time="00:00:06.000",
            text="Second",
            start_ms=3500,
            end_ms=6000
        )

        gap = SubtitleParser.calculate_gap(entry1, entry2)
        assert gap == 0.0

    def test_calculate_gap_overlapping(self):
        """Test calculating gap when subtitles overlap."""
        entry1 = SubtitleEntry(
            index=1,
            start_time="00:00:01.000",
            end_time="00:00:04.000",
            text="First",
            start_ms=1000,
            end_ms=4000
        )
        entry2 = SubtitleEntry(
            index=2,
            start_time="00:00:03.000",
            end_time="00:00:06.000",
            text="Second",
            start_ms=3000,
            end_ms=6000
        )

        gap = SubtitleParser.calculate_gap(entry1, entry2)
        assert gap == -1.0  # Negative = overlapping

    def test_parse_file_not_found(self):
        """Test parsing non-existent file raises error."""
        with pytest.raises(FileNotFoundError):
            SubtitleParser.parse_file("/nonexistent/file.srt")

    def test_parse_empty_srt(self):
        """Test parsing empty SRT file."""
        srt_content = ""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.srt', delete=False) as f:
            f.write(srt_content)
            temp_path = f.name

        try:
            entries = SubtitleParser.parse_file(temp_path)
            assert len(entries) == 0
        finally:
            os.unlink(temp_path)

    def test_parse_malformed_srt(self):
        """Test parsing malformed SRT file skips bad entries."""
        srt_content = """1
00:00:01,000 --> 00:00:03,500
Good entry

not a number
00:00:04,000 --> 00:00:06,500
This should be skipped

3
00:00:07,000 --> 00:00:09,500
Another good entry
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.srt', delete=False) as f:
            f.write(srt_content)
            temp_path = f.name

        try:
            entries = SubtitleParser.parse_file(temp_path)
            # Should only parse entries 1 and 3
            assert len(entries) == 2
            assert entries[0].index == 1
            assert entries[1].index == 3
        finally:
            os.unlink(temp_path)
