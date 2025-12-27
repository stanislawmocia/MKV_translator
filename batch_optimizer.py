"""
Module for intelligently splitting subtitles into batches based on dialogue gaps.
"""
from typing import List, Tuple
from subtitle_parser import SubtitleEntry, SubtitleParser


class BatchOptimizer:
    """Optimizes subtitle batching based on dialogue gaps."""

    def __init__(self, min_gap_seconds: float = 3.0, max_batch_size: int = 50):
        """
        Initialize batch optimizer.

        Args:
            min_gap_seconds: Minimum gap in seconds to consider as batch boundary
            max_batch_size: Maximum number of entries in a single batch
        """
        self.min_gap_seconds = min_gap_seconds
        self.max_batch_size = max_batch_size

    def create_batches(
        self,
        entries: List[SubtitleEntry]
    ) -> List[List[SubtitleEntry]]:
        """
        Split subtitle entries into batches based on dialogue gaps.

        Strategy:
        1. Look for gaps >= min_gap_seconds between subtitles
        2. Respect max_batch_size limit
        3. Prefer natural breaks (longer gaps) over forced splits

        Args:
            entries: List of subtitle entries

        Returns:
            List of batches, where each batch is a list of subtitle entries
        """
        if not entries:
            return []

        batches = []
        current_batch = []

        for i, entry in enumerate(entries):
            current_batch.append(entry)

            # Check if we should end the current batch
            should_split = False

            # Check max batch size
            if len(current_batch) >= self.max_batch_size:
                should_split = True

            # Check gap to next entry
            if i < len(entries) - 1:
                next_entry = entries[i + 1]
                gap = SubtitleParser.calculate_gap(entry, next_entry)

                # If gap is significant and we have some entries, split here
                if gap >= self.min_gap_seconds and len(current_batch) > 0:
                    should_split = True

            # Last entry always ends a batch
            if i == len(entries) - 1:
                should_split = True

            if should_split:
                batches.append(current_batch)
                current_batch = []

        return batches

    def create_smart_batches(
        self,
        entries: List[SubtitleEntry]
    ) -> List[Tuple[List[SubtitleEntry], float]]:
        """
        Create batches with metadata about gap quality.

        Returns:
            List of tuples: (batch, gap_before_next_batch)
        """
        if not entries:
            return []

        batches_with_gaps = []
        current_batch = []
        best_gap_in_batch = 0.0
        best_gap_index = -1

        for i, entry in enumerate(entries):
            current_batch.append(entry)

            # Track the best gap in this batch
            if i < len(entries) - 1:
                next_entry = entries[i + 1]
                gap = SubtitleParser.calculate_gap(entry, next_entry)

                if gap > best_gap_in_batch:
                    best_gap_in_batch = gap
                    best_gap_index = len(current_batch) - 1

            # Check if we must split (max size reached)
            must_split = len(current_batch) >= self.max_batch_size

            # Check if we have a good natural break
            natural_break = (
                i < len(entries) - 1 and
                best_gap_in_batch >= self.min_gap_seconds
            )

            # Last entry
            is_last = i == len(entries) - 1

            if must_split or natural_break or is_last:
                # If we have a good gap in the middle of a large batch, split there
                if must_split and best_gap_index > 0 and not natural_break:
                    # Split at the best gap found
                    first_part = current_batch[:best_gap_index + 1]
                    second_part = current_batch[best_gap_index + 1:]

                    batches_with_gaps.append((first_part, best_gap_in_batch))

                    # Continue with second part
                    current_batch = second_part
                    best_gap_in_batch = 0.0
                    best_gap_index = -1
                else:
                    # Normal split
                    batches_with_gaps.append((current_batch, best_gap_in_batch))
                    current_batch = []
                    best_gap_in_batch = 0.0
                    best_gap_index = -1

        return batches_with_gaps

    def get_batch_stats(self, batches: List[List[SubtitleEntry]]) -> dict:
        """
        Get statistics about the batching.

        Returns:
            Dictionary with statistics
        """
        if not batches:
            return {
                'total_batches': 0,
                'total_entries': 0,
                'avg_batch_size': 0,
                'min_batch_size': 0,
                'max_batch_size': 0
            }

        batch_sizes = [len(batch) for batch in batches]

        return {
            'total_batches': len(batches),
            'total_entries': sum(batch_sizes),
            'avg_batch_size': sum(batch_sizes) / len(batch_sizes),
            'min_batch_size': min(batch_sizes),
            'max_batch_size': max(batch_sizes)
        }

    def print_batch_summary(self, batches: List[List[SubtitleEntry]]):
        """Print a summary of the batches."""
        stats = self.get_batch_stats(batches)

        print(f"\n{'='*60}")
        print(f"Batch Summary:")
        print(f"{'='*60}")
        print(f"Total batches: {stats['total_batches']}")
        print(f"Total entries: {stats['total_entries']}")
        print(f"Average batch size: {stats['avg_batch_size']:.1f}")
        print(f"Min batch size: {stats['min_batch_size']}")
        print(f"Max batch size: {stats['max_batch_size']}")
        print(f"{'='*60}\n")

        # Show first few entries of each batch
        for i, batch in enumerate(batches[:5], 1):  # Show first 5 batches
            print(f"Batch {i} ({len(batch)} entries):")
            if batch:
                print(f"  First: [{batch[0].start_time}] {batch[0].text[:50]}...")
                if len(batch) > 1:
                    print(f"  Last:  [{batch[-1].start_time}] {batch[-1].text[:50]}...")

                # Calculate gap to next batch
                if i < len(batches):
                    next_batch = batches[i]
                    gap = SubtitleParser.calculate_gap(batch[-1], next_batch[0])
                    print(f"  Gap to next batch: {gap:.2f}s")
            print()

        if len(batches) > 5:
            print(f"... and {len(batches) - 5} more batches\n")
