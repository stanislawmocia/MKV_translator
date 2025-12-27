"""
Module for extracting subtitles from MKV and other media files.
"""
import os
import json
import subprocess
from pathlib import Path
from typing import Optional, List


class SubtitleExtractor:
    """Extract subtitles from media files using mkvextract or ffmpeg."""

    def __init__(self):
        self.has_mkvextract = self._check_mkvextract()
        self.has_ffmpeg = self._check_ffmpeg()

        if not self.has_mkvextract and not self.has_ffmpeg:
            raise RuntimeError(
                "Neither mkvextract nor ffmpeg found. "
                "Please install mkvtoolnix or ffmpeg."
            )

    def _check_mkvextract(self) -> bool:
        """Check if mkvextract is available."""
        try:
            subprocess.run(
                ['mkvextract', '--version'],
                capture_output=True,
                check=True
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def _check_ffmpeg(self) -> bool:
        """Check if ffmpeg is available."""
        try:
            subprocess.run(
                ['ffmpeg', '-version'],
                capture_output=True,
                check=True
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def list_subtitle_tracks(self, media_file: str) -> List[dict]:
        """
        List all subtitle tracks in a media file.

        Returns:
            List of dicts with 'index', 'language', 'codec' information
        """
        media_path = Path(media_file)
        if not media_path.exists():
            raise FileNotFoundError(f"Media file not found: {media_file}")

        if self.has_mkvextract and media_path.suffix.lower() == '.mkv':
            return self._list_mkv_tracks(media_file)
        elif self.has_ffmpeg:
            return self._list_ffmpeg_tracks(media_file)
        else:
            raise RuntimeError("No suitable tool available for this file type")

    def _list_mkv_tracks(self, mkv_file: str) -> List[dict]:
        """List subtitle tracks using mkvmerge."""
        try:
            result = subprocess.run(
                ['mkvmerge', '-J', mkv_file],
                capture_output=True,
                text=True,
                check=True
            )
            import json
            info = json.loads(result.stdout)

            subtitles = []
            for track in info.get('tracks', []):
                if track['type'] == 'subtitles':
                    subtitles.append({
                        'index': track['id'],
                        'language': track.get('properties', {}).get('language', 'und'),
                        'codec': track['codec'],
                        'track_name': track.get('properties', {}).get('track_name', '')
                    })
            return subtitles
        except (subprocess.CalledProcessError, json.JSONDecodeError) as e:
            print(f"Error listing MKV tracks: {e}")
            return []

    def _list_ffmpeg_tracks(self, media_file: str) -> List[dict]:
        """List subtitle tracks using ffprobe."""
        try:
            result = subprocess.run(
                [
                    'ffprobe', '-v', 'quiet',
                    '-print_format', 'json',
                    '-show_streams',
                    media_file
                ],
                capture_output=True,
                text=True,
                check=True
            )
            import json
            info = json.loads(result.stdout)

            subtitles = []
            for stream in info.get('streams', []):
                if stream.get('codec_type') == 'subtitle':
                    subtitles.append({
                        'index': stream['index'],
                        'language': stream.get('tags', {}).get('language', 'und'),
                        'codec': stream.get('codec_name', 'unknown'),
                        'track_name': stream.get('tags', {}).get('title', '')
                    })
            return subtitles
        except (subprocess.CalledProcessError, json.JSONDecodeError) as e:
            print(f"Error listing tracks with ffprobe: {e}")
            return []

    def extract_subtitle(
        self,
        media_file: str,
        output_file: str,
        track_index: int = 0
    ) -> bool:
        """
        Extract subtitle track from media file.

        Args:
            media_file: Path to input media file
            output_file: Path to output subtitle file
            track_index: Index of subtitle track to extract (default: 0)

        Returns:
            True if extraction was successful
        """
        media_path = Path(media_file)
        if not media_path.exists():
            raise FileNotFoundError(f"Media file not found: {media_file}")

        # Create output directory if it doesn't exist
        Path(output_file).parent.mkdir(parents=True, exist_ok=True)

        if self.has_mkvextract and media_path.suffix.lower() == '.mkv':
            return self._extract_mkv_subtitle(media_file, output_file, track_index)
        elif self.has_ffmpeg:
            return self._extract_ffmpeg_subtitle(media_file, output_file, track_index)
        else:
            raise RuntimeError("No suitable tool available")

    def _extract_mkv_subtitle(
        self,
        mkv_file: str,
        output_file: str,
        track_index: int
    ) -> bool:
        """Extract subtitle using mkvextract."""
        try:
            subprocess.run(
                [
                    'mkvextract',
                    mkv_file,
                    'tracks',
                    f'{track_index}:{output_file}'
                ],
                check=True,
                capture_output=True
            )
            return True
        except subprocess.CalledProcessError as e:
            print(f"Error extracting subtitle: {e.stderr.decode()}")
            return False

    def _extract_ffmpeg_subtitle(
        self,
        media_file: str,
        output_file: str,
        track_index: int
    ) -> bool:
        """Extract subtitle using ffmpeg."""
        try:
            subprocess.run(
                [
                    'ffmpeg', '-y',
                    '-i', media_file,
                    '-map', f'0:{track_index}',
                    output_file
                ],
                check=True,
                capture_output=True
            )
            return True
        except subprocess.CalledProcessError as e:
            print(f"Error extracting subtitle: {e.stderr.decode()}")
            return False
