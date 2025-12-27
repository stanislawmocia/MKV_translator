"""
Integration tests for the complete workflow.
"""
import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, Mock
import responses

from subtitle_parser import SubtitleParser, SubtitleEntry
from batch_optimizer import BatchOptimizer
from translator import OpenRouterTranslator


class TestIntegration:
    """Integration tests for complete workflows."""

    def test_parse_batch_translate_write_workflow(self):
        """Test complete workflow: parse -> batch -> translate -> write."""
        # Step 1: Create test SRT file
        srt_content = """1
00:00:01,000 --> 00:00:03,000
Hello, world!

2
00:00:04,000 --> 00:00:06,000
This is a test.

3
00:00:10,000 --> 00:00:12,000
After a gap.
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.srt', delete=False) as f:
            input_path = f.name
            f.write(srt_content)

        output_path = tempfile.mktemp(suffix='.srt')

        try:
            # Step 2: Parse
            entries = SubtitleParser.parse_file(input_path)
            assert len(entries) == 3

            # Step 3: Create batches
            optimizer = BatchOptimizer(min_gap_seconds=3.0, max_batch_size=50)
            batches = optimizer.create_batches(entries)

            # Should create 2 batches due to gap
            assert len(batches) == 2
            assert len(batches[0]) == 2  # Entries 1-2
            assert len(batches[1]) == 1  # Entry 3

            # Step 4: Mock translation
            with responses.RequestsMock() as rsps:
                # Mock API calls for each batch
                rsps.add(
                    responses.POST,
                    "https://openrouter.ai/api/v1/chat/completions",
                    json={
                        "choices": [{
                            "message": {
                                "content": "1|Witaj, świecie!\n2|To jest test."
                            }
                        }]
                    },
                    status=200
                )
                rsps.add(
                    responses.POST,
                    "https://openrouter.ai/api/v1/chat/completions",
                    json={
                        "choices": [{
                            "message": {
                                "content": "3|Po przerwie."
                            }
                        }]
                    },
                    status=200
                )

                translator = OpenRouterTranslator(
                    api_key="test_key",
                    model="test/model",
                    source_language="english",
                    target_language="polish"
                )

                translated = translator.translate_all(
                    entries,
                    batches,
                    delay_between_batches=0
                )

            assert len(translated) == 3
            assert translated[0].text == "Witaj, świecie!"
            assert translated[1].text == "To jest test."
            assert translated[2].text == "Po przerwie."

            # Step 5: Write output
            SubtitleParser.write_srt(translated, output_path)

            # Step 6: Verify output
            output_entries = SubtitleParser.parse_file(output_path)
            assert len(output_entries) == 3
            assert output_entries[0].text == "Witaj, świecie!"
            assert output_entries[1].text == "To jest test."
            assert output_entries[2].text == "Po przerwie."

            # Verify timestamps are preserved
            assert output_entries[0].start_ms == 1000
            assert output_entries[0].end_ms == 3000

        finally:
            os.unlink(input_path)
            if os.path.exists(output_path):
                os.unlink(output_path)

    def test_large_batch_splitting(self):
        """Test handling of many subtitles with intelligent batching."""
        # Create 100 subtitle entries with varying gaps
        entries = []
        current_time = 0

        for i in range(1, 101):
            start_ms = current_time
            end_ms = current_time + 2000

            entries.append(SubtitleEntry(
                index=i,
                start_time=f"00:00:{(start_ms//1000):02d}.{(start_ms%1000):03d}",
                end_time=f"00:00:{(end_ms//1000):02d}.{(end_ms%1000):03d}",
                text=f"Entry {i}",
                start_ms=start_ms,
                end_ms=end_ms
            ))

            # Add varying gaps
            if i % 20 == 0:
                current_time = end_ms + 5000  # Large gap every 20 entries
            else:
                current_time = end_ms + 1000  # Small gap otherwise

        # Test batching
        optimizer = BatchOptimizer(min_gap_seconds=3.0, max_batch_size=50)
        batches = optimizer.create_batches(entries)

        # Should create multiple batches due to gaps and size limits
        assert len(batches) > 1

        # Verify all entries are in batches
        total_entries = sum(len(batch) for batch in batches)
        assert total_entries == 100

        # Get stats
        stats = optimizer.get_batch_stats(batches)
        assert stats['total_batches'] == len(batches)
        assert stats['total_entries'] == 100
        assert stats['max_batch_size'] <= 50

    def test_multiline_preservation(self):
        """Test that multiline subtitles are handled correctly."""
        srt_content = """1
00:00:01,000 --> 00:00:05,000
This is a subtitle
with multiple lines
of text

2
00:00:06,000 --> 00:00:10,000
Single line
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.srt', delete=False) as f:
            input_path = f.name
            f.write(srt_content)

        try:
            entries = SubtitleParser.parse_file(input_path)

            # Multiline should be joined with spaces
            assert entries[0].text == "This is a subtitle with multiple lines of text"
            assert entries[1].text == "Single line"

        finally:
            os.unlink(input_path)

    def test_timestamp_precision_preservation(self):
        """Test that timestamp precision is preserved through workflow."""
        entries = [
            SubtitleEntry(
                index=1,
                start_time="00:00:01.123",
                end_time="00:00:03.456",
                text="Original text",
                start_ms=1123,
                end_ms=3456
            )
        ]

        output_path = tempfile.mktemp(suffix='.srt')

        try:
            SubtitleParser.write_srt(entries, output_path)

            # Read back
            parsed = SubtitleParser.parse_file(output_path)

            # Verify millisecond precision
            assert parsed[0].start_ms == 1123
            assert parsed[0].end_ms == 3456

        finally:
            if os.path.exists(output_path):
                os.unlink(output_path)

    def test_empty_subtitle_handling(self):
        """Test handling of empty or whitespace-only subtitles."""
        srt_content = """1
00:00:01,000 --> 00:00:03,000


2
00:00:04,000 --> 00:00:06,000
Valid entry
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.srt', delete=False) as f:
            input_path = f.name
            f.write(srt_content)

        try:
            entries = SubtitleParser.parse_file(input_path)

            # Should handle empty entries gracefully
            # Either skip them or preserve them
            assert len(entries) >= 1
            assert any(e.text == "Valid entry" for e in entries)

        finally:
            os.unlink(input_path)

    @responses.activate
    def test_translation_error_handling(self):
        """Test that translation errors are handled gracefully."""
        entries = [
            SubtitleEntry(
                index=1,
                start_time="00:00:01.000",
                end_time="00:00:03.000",
                text="Test",
                start_ms=1000,
                end_ms=3000
            )
        ]

        # Mock API failure
        responses.add(
            responses.POST,
            "https://openrouter.ai/api/v1/chat/completions",
            json={"error": "API error"},
            status=500
        )

        translator = OpenRouterTranslator(
            api_key="test_key",
            model="test/model"
        )

        batches = [entries]

        # Should not crash, but return original entries
        result = translator.translate_all(entries, batches, delay_between_batches=0)

        # Should return something (either original or empty)
        assert isinstance(result, list)

    def test_vtt_to_srt_conversion(self):
        """Test converting VTT to SRT format."""
        vtt_content = """WEBVTT

00:00:01.000 --> 00:00:03.000
First subtitle

00:00:04.000 --> 00:00:06.000
Second subtitle
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.vtt', delete=False) as f:
            input_path = f.name
            f.write(vtt_content)

        output_path = tempfile.mktemp(suffix='.srt')

        try:
            # Parse VTT
            entries = SubtitleParser.parse_file(input_path)
            assert len(entries) == 2

            # Write as SRT
            SubtitleParser.write_srt(entries, output_path)

            # Verify SRT was created
            assert os.path.exists(output_path)

            # Parse the SRT
            srt_entries = SubtitleParser.parse_file(output_path)
            assert len(srt_entries) == 2
            assert srt_entries[0].text == "First subtitle"

        finally:
            os.unlink(input_path)
            if os.path.exists(output_path):
                os.unlink(output_path)

    def test_batch_size_boundary_conditions(self):
        """Test batching at exact max_batch_size boundaries."""
        # Create exactly 50 entries (default max_batch_size)
        entries = []
        for i in range(50):
            entries.append(SubtitleEntry(
                index=i + 1,
                start_time=f"00:00:{i:02d}.000",
                end_time=f"00:00:{i:02d}.500",
                text=f"Entry {i+1}",
                start_ms=i * 1000,
                end_ms=i * 1000 + 500
            ))

        optimizer = BatchOptimizer(min_gap_seconds=10.0, max_batch_size=50)
        batches = optimizer.create_batches(entries)

        # Should create exactly 1 batch
        assert len(batches) == 1
        assert len(batches[0]) == 50

        # Add one more entry
        entries.append(SubtitleEntry(
            index=51,
            start_time="00:00:50.000",
            end_time="00:00:50.500",
            text="Entry 51",
            start_ms=50000,
            end_ms=50500
        ))

        batches = optimizer.create_batches(entries)

        # Should now create 2 batches
        assert len(batches) == 2
        assert len(batches[0]) == 50
        assert len(batches[1]) == 1
