"""
Module for parsing and writing subtitle files in various formats.
"""
import re
from dataclasses import dataclass
from typing import List, Optional
from pathlib import Path


@dataclass
class SubtitleEntry:
    """Represents a single subtitle entry."""
    index: int
    start_time: str  # Original timestamp format
    end_time: str  # Original timestamp format
    text: str
    start_ms: int  # Start time in milliseconds
    end_ms: int  # End time in milliseconds


class SubtitleParser:
    """Parser for subtitle files (SRT, VTT, etc.)."""

    @staticmethod
    def parse_file(file_path: str) -> List[SubtitleEntry]:
        """
        Parse a subtitle file and return list of entries.

        Supports: SRT, VTT
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"Subtitle file not found: {file_path}")

        extension = file_path.suffix.lower()

        if extension == '.srt':
            return SubtitleParser._parse_srt(file_path)
        elif extension == '.vtt':
            return SubtitleParser._parse_vtt(file_path)
        else:
            # Try to parse as SRT by default
            return SubtitleParser._parse_srt(file_path)

    @staticmethod
    def _parse_srt(file_path: Path) -> List[SubtitleEntry]:
        """Parse SRT subtitle file."""
        # Try different encodings
        encodings = ['utf-8', 'latin-1', 'cp1252']
        content = None

        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    content = f.read()
                break
            except UnicodeDecodeError:
                continue

        if content is None:
            # Try with chardet as last resort
            try:
                import chardet
                with open(file_path, 'rb') as f:
                    raw_data = f.read()
                    detected = chardet.detect(raw_data)
                    encoding = detected['encoding'] or 'utf-8'
                with open(file_path, 'r', encoding=encoding) as f:
                    content = f.read()
            except:
                raise ValueError(f"Could not decode file: {file_path}")

        # Split into blocks
        blocks = re.split(r'\n\s*\n', content.strip())

        entries = []
        for block in blocks:
            if not block.strip():
                continue

            lines = block.strip().split('\n')
            if len(lines) < 3:
                continue

            # First line should be the index
            try:
                index = int(lines[0].strip())
            except ValueError:
                # Skip malformed blocks
                continue

            # Second line should be timestamps
            timestamp_line = lines[1].strip()
            match = re.match(
                r'(\d{2}:\d{2}:\d{2}[,\.]\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}[,\.]\d{3})',
                timestamp_line
            )

            if not match:
                continue

            start_time = match.group(1).replace(',', '.')
            end_time = match.group(2).replace(',', '.')

            # Remaining lines are the text
            text = ' '.join(lines[2:])

            # Convert to milliseconds
            start_ms = SubtitleParser._time_to_ms(start_time)
            end_ms = SubtitleParser._time_to_ms(end_time)

            entries.append(SubtitleEntry(
                index=index,
                start_time=start_time,
                end_time=end_time,
                text=text,
                start_ms=start_ms,
                end_ms=end_ms
            ))

        return entries

    @staticmethod
    def _parse_vtt(file_path: Path) -> List[SubtitleEntry]:
        """Parse WebVTT subtitle file."""
        entries = []
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Remove WEBVTT header (just the first line)
        content = re.sub(r'^WEBVTT\s*\n', '', content)

        # Split into blocks
        blocks = re.split(r'\n\n+', content.strip())

        for idx, block in enumerate(blocks, 1):
            if not block.strip():
                continue

            lines = block.strip().split('\n')

            # Find timestamp line
            timestamp_line = None
            text_start = 0

            for i, line in enumerate(lines):
                if '-->' in line:
                    timestamp_line = line
                    text_start = i + 1
                    break

            if not timestamp_line:
                continue

            # Parse timestamps
            match = re.match(
                r'(\d{2}:\d{2}:\d{2}\.\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}\.\d{3})',
                timestamp_line
            )

            if match:
                start_time = match.group(1)
                end_time = match.group(2)
                text = ' '.join(lines[text_start:])

                # Convert to milliseconds
                start_ms = SubtitleParser._time_to_ms(start_time)
                end_ms = SubtitleParser._time_to_ms(end_time)

                entries.append(SubtitleEntry(
                    index=idx,
                    start_time=start_time,
                    end_time=end_time,
                    text=text,
                    start_ms=start_ms,
                    end_ms=end_ms
                ))

        return entries

    @staticmethod
    def _time_to_ms(time_str: str) -> int:
        """Convert time string (HH:MM:SS.mmm or HH:MM:SS,mmm) to milliseconds."""
        time_str = time_str.replace(',', '.')
        parts = time_str.split(':')
        hours = int(parts[0])
        minutes = int(parts[1])
        seconds_parts = parts[2].split('.')
        seconds = int(seconds_parts[0])
        milliseconds = int(seconds_parts[1]) if len(seconds_parts) > 1 else 0

        return (hours * 3600000 + minutes * 60000 +
                seconds * 1000 + milliseconds)

    @staticmethod
    def _ms_to_time(ms: int) -> str:
        """Convert milliseconds to SRT time format (HH:MM:SS,mmm)."""
        hours = ms // 3600000
        ms %= 3600000
        minutes = ms // 60000
        ms %= 60000
        seconds = ms // 1000
        milliseconds = ms % 1000

        return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"

    @staticmethod
    def write_srt(entries: List[SubtitleEntry], output_path: str):
        """Write subtitle entries to SRT file."""
        # Create output directory if needed
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            for entry in entries:
                # Format: index, timestamp, text, blank line
                # Ensure time format uses comma (SRT standard)
                start_time = entry.start_time.replace('.', ',')
                end_time = entry.end_time.replace('.', ',')

                f.write(f"{entry.index}\n")
                f.write(f"{start_time} --> {end_time}\n")
                f.write(f"{entry.text}\n")
                f.write("\n")

    @staticmethod
    def calculate_gap(entry1: SubtitleEntry, entry2: SubtitleEntry) -> float:
        """
        Calculate gap in seconds between two subtitle entries.

        Returns:
            Gap in seconds (positive if there's a gap, negative if overlapping)
        """
        return (entry2.start_ms - entry1.end_ms) / 1000.0
