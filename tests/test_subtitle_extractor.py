"""
Tests for subtitle_extractor module.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import subprocess
import json

from subtitle_extractor import SubtitleExtractor


class TestSubtitleExtractor:
    """Test SubtitleExtractor class."""

    @patch('subtitle_extractor.subprocess.run')
    def test_check_mkvextract_available(self, mock_run):
        """Test checking if mkvextract is available."""
        mock_run.return_value = Mock(returncode=0)

        extractor = SubtitleExtractor()

        assert extractor.has_mkvextract is True
        mock_run.assert_called()

    @patch('subtitle_extractor.subprocess.run')
    def test_check_mkvextract_not_available(self, mock_run):
        """Test checking if mkvextract is not available but ffmpeg is."""
        # First call for mkvextract fails, second for ffmpeg succeeds
        mock_run.side_effect = [
            FileNotFoundError(),  # mkvextract not found
            Mock(returncode=0)     # ffmpeg found
        ]

        extractor = SubtitleExtractor()

        assert extractor.has_mkvextract is False
        assert extractor.has_ffmpeg is True

    @patch('subtitle_extractor.subprocess.run')
    def test_check_ffmpeg_available(self, mock_run):
        """Test checking if ffmpeg is available."""
        # First call for mkvextract fails, second for ffmpeg succeeds
        mock_run.side_effect = [
            FileNotFoundError(),  # mkvextract not found
            Mock(returncode=0)     # ffmpeg found
        ]

        extractor = SubtitleExtractor()

        assert extractor.has_mkvextract is False
        assert extractor.has_ffmpeg is True

    @patch('subtitle_extractor.subprocess.run')
    def test_no_tools_available_raises_error(self, mock_run):
        """Test that error is raised when no tools are available."""
        mock_run.side_effect = FileNotFoundError()

        with pytest.raises(RuntimeError) as exc_info:
            SubtitleExtractor()

        assert "Neither mkvextract nor ffmpeg found" in str(exc_info.value)

    @patch('subtitle_extractor.subprocess.run')
    def test_list_mkv_tracks(self, mock_run):
        """Test listing subtitle tracks in MKV file."""
        # Mock mkvextract available
        mock_run.return_value = Mock(returncode=0)
        extractor = SubtitleExtractor()

        # Mock mkvmerge output
        mkv_info = {
            "tracks": [
                {
                    "id": 0,
                    "type": "video",
                    "codec": "h264"
                },
                {
                    "id": 1,
                    "type": "audio",
                    "codec": "aac"
                },
                {
                    "id": 2,
                    "type": "subtitles",
                    "codec": "SubRip/SRT",
                    "properties": {
                        "language": "eng",
                        "track_name": "English"
                    }
                },
                {
                    "id": 3,
                    "type": "subtitles",
                    "codec": "SubRip/SRT",
                    "properties": {
                        "language": "pol",
                        "track_name": "Polish"
                    }
                }
            ]
        }

        mock_run.return_value = Mock(
            returncode=0,
            stdout=json.dumps(mkv_info)
        )

        # Create a temporary file to test with
        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.mkv') as f:
            tracks = extractor.list_subtitle_tracks(f.name)

        assert len(tracks) == 2
        assert tracks[0]['index'] == 2
        assert tracks[0]['language'] == 'eng'
        assert tracks[0]['codec'] == 'SubRip/SRT'
        assert tracks[1]['index'] == 3
        assert tracks[1]['language'] == 'pol'

    @patch('subtitle_extractor.subprocess.run')
    def test_list_ffmpeg_tracks(self, mock_run):
        """Test listing subtitle tracks using ffprobe."""
        # Mock ffprobe output
        ffprobe_info = {
            "streams": [
                {
                    "index": 0,
                    "codec_type": "video"
                },
                {
                    "index": 1,
                    "codec_type": "subtitle",
                    "codec_name": "srt",
                    "tags": {
                        "language": "eng",
                        "title": "English"
                    }
                }
            ]
        }

        # Mock ffmpeg available (mkvextract not available)
        mock_run.side_effect = [
            FileNotFoundError(),  # mkvextract check
            Mock(returncode=0),   # ffmpeg check
            Mock(returncode=0, stdout=json.dumps(ffprobe_info))  # ffprobe call
        ]
        extractor = SubtitleExtractor()

        # Create a temporary file to test with
        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.mp4') as f:
            tracks = extractor._list_ffmpeg_tracks(f.name)

        assert len(tracks) == 1
        assert tracks[0]['index'] == 1
        assert tracks[0]['language'] == 'eng'

    @patch('subtitle_extractor.subprocess.run')
    def test_extract_mkv_subtitle_success(self, mock_run):
        """Test successful subtitle extraction from MKV."""
        mock_run.return_value = Mock(returncode=0)
        extractor = SubtitleExtractor()

        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.mkv', delete=False) as input_file:
            input_path = input_file.name

        with tempfile.NamedTemporaryFile(suffix='.srt', delete=False) as output_file:
            output_path = output_file.name

        try:
            # Reset mock to clear initialization calls
            mock_run.reset_mock()
            mock_run.return_value = Mock(returncode=0)

            result = extractor._extract_mkv_subtitle(input_path, output_path, 0)

            assert result is True
            mock_run.assert_called_once()

            # Verify mkvextract was called with correct arguments
            call_args = mock_run.call_args[0][0]
            assert call_args[0] == 'mkvextract'
            assert input_path in call_args
            assert 'tracks' in call_args
            assert f'0:{output_path}' in call_args

        finally:
            import os
            os.unlink(input_path)
            os.unlink(output_path)

    @patch('subtitle_extractor.subprocess.run')
    def test_extract_mkv_subtitle_failure(self, mock_run):
        """Test failed subtitle extraction from MKV."""
        mock_run.return_value = Mock(returncode=0)
        extractor = SubtitleExtractor()

        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.mkv', delete=False) as input_file:
            input_path = input_file.name

        with tempfile.NamedTemporaryFile(suffix='.srt', delete=False) as output_file:
            output_path = output_file.name

        try:
            # Mock extraction failure
            mock_run.side_effect = subprocess.CalledProcessError(
                1, 'mkvextract', stderr=b'Error extracting'
            )

            result = extractor._extract_mkv_subtitle(input_path, output_path, 0)

            assert result is False

        finally:
            import os
            os.unlink(input_path)
            os.unlink(output_path)

    @patch('subtitle_extractor.subprocess.run')
    def test_extract_ffmpeg_subtitle_success(self, mock_run):
        """Test successful subtitle extraction with ffmpeg."""
        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as input_file:
            input_path = input_file.name

        with tempfile.NamedTemporaryFile(suffix='.srt', delete=False) as output_file:
            output_path = output_file.name

        try:
            # Mock ffmpeg available and extraction success
            mock_run.side_effect = [
                FileNotFoundError(),  # mkvextract check
                Mock(returncode=0),   # ffmpeg check
                Mock(returncode=0)    # ffmpeg extraction call
            ]
            extractor = SubtitleExtractor()

            result = extractor._extract_ffmpeg_subtitle(input_path, output_path, 1)

            assert result is True

            # Verify ffmpeg was called with correct arguments
            call_args = mock_run.call_args[0][0]
            assert call_args[0] == 'ffmpeg'
            assert '-i' in call_args
            assert input_path in call_args
            assert '-map' in call_args
            assert '0:1' in call_args
            assert output_path in call_args

        finally:
            import os
            os.unlink(input_path)
            os.unlink(output_path)

    @patch('subtitle_extractor.subprocess.run')
    def test_extract_subtitle_file_not_found(self, mock_run):
        """Test extracting from non-existent file raises error."""
        mock_run.return_value = Mock(returncode=0)
        extractor = SubtitleExtractor()

        with pytest.raises(FileNotFoundError):
            extractor.extract_subtitle(
                '/nonexistent/file.mkv',
                '/tmp/output.srt',
                0
            )

    @patch('subtitle_extractor.subprocess.run')
    def test_extract_subtitle_creates_output_directory(self, mock_run):
        """Test that extraction creates output directory if needed."""
        mock_run.return_value = Mock(returncode=0)
        extractor = SubtitleExtractor()

        import tempfile
        import os

        with tempfile.NamedTemporaryFile(suffix='.mkv', delete=False) as input_file:
            input_path = input_file.name

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, 'subdir', 'output.srt')

            # Reset mock
            mock_run.reset_mock()
            mock_run.return_value = Mock(returncode=0)

            try:
                result = extractor.extract_subtitle(input_path, output_path, 0)

                # Directory should be created
                assert os.path.exists(os.path.dirname(output_path))

            finally:
                os.unlink(input_path)

    @patch('subtitle_extractor.subprocess.run')
    def test_list_tracks_empty_result(self, mock_run):
        """Test listing tracks when no subtitles are found."""
        mock_run.return_value = Mock(returncode=0)
        extractor = SubtitleExtractor()

        # Mock mkvmerge output with no subtitle tracks
        mkv_info = {
            "tracks": [
                {
                    "id": 0,
                    "type": "video",
                    "codec": "h264"
                }
            ]
        }

        mock_run.return_value = Mock(
            returncode=0,
            stdout=json.dumps(mkv_info)
        )

        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.mkv') as f:
            tracks = extractor.list_subtitle_tracks(f.name)

        assert len(tracks) == 0
