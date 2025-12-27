#!/usr/bin/env python3
"""
MKV Subtitle Translator - Main CLI interface

Supports:
1. Extracting and translating subtitles from video files (MKV, MP4, etc.)
2. Translating standalone subtitle files (SRT, VTT)
"""
import os
import sys
import argparse
from pathlib import Path
from dotenv import load_dotenv

from subtitle_extractor import SubtitleExtractor
from subtitle_parser import SubtitleParser
from batch_optimizer import BatchOptimizer
from translator import OpenRouterTranslator


def extract_and_translate_video(
    video_file: str,
    output_file: str,
    track_index: int,
    translator: OpenRouterTranslator,
    batch_optimizer: BatchOptimizer
):
    """Extract subtitles from video and translate them."""
    print(f"\n{'='*60}")
    print(f"MODE: Extract from Video + Translate")
    print(f"{'='*60}")
    print(f"Input video: {video_file}")
    print(f"Output file: {output_file}")

    # Step 1: Extract subtitles
    print(f"\n[1/5] Extracting subtitles from video...")
    extractor = SubtitleExtractor()

    # List available tracks
    tracks = extractor.list_subtitle_tracks(video_file)
    if not tracks:
        print("Error: No subtitle tracks found in video file")
        return False

    print(f"\nAvailable subtitle tracks:")
    for i, track in enumerate(tracks):
        print(f"  {i}: {track['language']} ({track['codec']}) - {track.get('track_name', 'N/A')}")

    # Extract the specified track
    temp_subtitle_file = "temp_extracted.srt"
    success = extractor.extract_subtitle(video_file, temp_subtitle_file, track_index)

    if not success:
        print(f"Error: Failed to extract subtitle track {track_index}")
        return False

    print(f"✓ Subtitles extracted to {temp_subtitle_file}")

    # Step 2: Parse subtitles
    print(f"\n[2/5] Parsing subtitles...")
    entries = SubtitleParser.parse_file(temp_subtitle_file)
    print(f"✓ Parsed {len(entries)} subtitle entries")

    # Step 3: Create batches
    print(f"\n[3/5] Creating intelligent batches...")
    batches = batch_optimizer.create_batches(entries)
    batch_optimizer.print_batch_summary(batches)

    # Step 4: Translate
    print(f"\n[4/5] Translating subtitles...")
    translated_entries = translator.translate_all(entries, batches)

    # Step 5: Write output
    print(f"\n[5/5] Writing translated subtitles...")
    SubtitleParser.write_srt(translated_entries, output_file)
    print(f"✓ Translated subtitles saved to: {output_file}")

    # Cleanup temp file
    if os.path.exists(temp_subtitle_file):
        os.remove(temp_subtitle_file)

    print(f"\n{'='*60}")
    print(f"✓ SUCCESS! Translation complete.")
    print(f"{'='*60}\n")
    return True


def translate_subtitle_file(
    subtitle_file: str,
    output_file: str,
    translator: OpenRouterTranslator,
    batch_optimizer: BatchOptimizer
):
    """Translate a standalone subtitle file."""
    print(f"\n{'='*60}")
    print(f"MODE: Translate Subtitle File")
    print(f"{'='*60}")
    print(f"Input subtitle: {subtitle_file}")
    print(f"Output file: {output_file}")

    # Step 1: Parse subtitles
    print(f"\n[1/4] Parsing subtitles...")
    entries = SubtitleParser.parse_file(subtitle_file)
    print(f"✓ Parsed {len(entries)} subtitle entries")

    # Step 2: Create batches
    print(f"\n[2/4] Creating intelligent batches...")
    batches = batch_optimizer.create_batches(entries)
    batch_optimizer.print_batch_summary(batches)

    # Step 3: Translate
    print(f"\n[3/4] Translating subtitles...")
    translated_entries = translator.translate_all(entries, batches)

    # Step 4: Write output
    print(f"\n[4/4] Writing translated subtitles...")
    SubtitleParser.write_srt(translated_entries, output_file)
    print(f"✓ Translated subtitles saved to: {output_file}")

    print(f"\n{'='*60}")
    print(f"✓ SUCCESS! Translation complete.")
    print(f"{'='*60}\n")
    return True


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Translate subtitles from video files or subtitle files using OpenRouter',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Translate subtitles from MKV file
  python main.py --video movie.mkv --output movie_pl.srt

  # Translate standalone subtitle file
  python main.py --subtitle movie.srt --output movie_pl.srt

  # Specify subtitle track and custom settings
  python main.py --video movie.mkv --track 1 --output movie_pl.srt --target polish
        """
    )

    # Input options
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument(
        '--video', '-v',
        help='Path to video file (MKV, MP4, etc.)'
    )
    input_group.add_argument(
        '--subtitle', '-s',
        help='Path to subtitle file (SRT, VTT)'
    )

    # Output options
    parser.add_argument(
        '--output', '-o',
        required=True,
        help='Output subtitle file path'
    )

    # Video-specific options
    parser.add_argument(
        '--track', '-t',
        type=int,
        default=0,
        help='Subtitle track index to extract (default: 0)'
    )

    # Translation options
    parser.add_argument(
        '--target',
        help='Target language (overrides .env)'
    )
    parser.add_argument(
        '--source',
        help='Source language (overrides .env)'
    )
    parser.add_argument(
        '--model',
        help='OpenRouter model to use (overrides .env)'
    )

    # Batch options
    parser.add_argument(
        '--min-gap',
        type=float,
        help='Minimum gap in seconds for batch splitting (default: 3.0)'
    )
    parser.add_argument(
        '--max-batch-size',
        type=int,
        help='Maximum entries per batch (default: 50)'
    )

    args = parser.parse_args()

    # Load environment variables
    load_dotenv()

    # Get configuration
    api_key = os.getenv('OPENROUTER_API_KEY')
    if not api_key:
        print("Error: OPENROUTER_API_KEY not found in environment")
        print("Please create a .env file with your OpenRouter API key")
        print("See .env.example for reference")
        return 1

    model = args.model or os.getenv('OPENROUTER_MODEL', 'anthropic/claude-3.5-sonnet')
    target_lang = args.target or os.getenv('TARGET_LANGUAGE', 'polish')
    source_lang = args.source or os.getenv('SOURCE_LANGUAGE', 'english')

    min_gap = args.min_gap or float(os.getenv('MIN_GAP_SECONDS', '3.0'))
    max_batch_size = args.max_batch_size or int(os.getenv('MAX_BATCH_SIZE', '50'))

    # Initialize components
    translator = OpenRouterTranslator(
        api_key=api_key,
        model=model,
        source_language=source_lang,
        target_language=target_lang
    )

    batch_optimizer = BatchOptimizer(
        min_gap_seconds=min_gap,
        max_batch_size=max_batch_size
    )

    # Process based on input type
    try:
        if args.video:
            # Video mode: extract + translate
            if not Path(args.video).exists():
                print(f"Error: Video file not found: {args.video}")
                return 1

            success = extract_and_translate_video(
                args.video,
                args.output,
                args.track,
                translator,
                batch_optimizer
            )
        else:
            # Subtitle mode: translate only
            if not Path(args.subtitle).exists():
                print(f"Error: Subtitle file not found: {args.subtitle}")
                return 1

            success = translate_subtitle_file(
                args.subtitle,
                args.output,
                translator,
                batch_optimizer
            )

        return 0 if success else 1

    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        return 1
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
