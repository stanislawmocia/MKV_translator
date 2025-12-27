"""
Tests for batch_optimizer module.
"""
import pytest
from batch_optimizer import BatchOptimizer
from subtitle_parser import SubtitleEntry


class TestBatchOptimizer:
    """Test BatchOptimizer class."""

    def create_entry(self, index, start_ms, end_ms):
        """Helper to create a subtitle entry."""
        return SubtitleEntry(
            index=index,
            start_time=f"00:00:{start_ms//1000:02d}.{start_ms%1000:03d}",
            end_time=f"00:00:{end_ms//1000:02d}.{end_ms%1000:03d}",
            text=f"Entry {index}",
            start_ms=start_ms,
            end_ms=end_ms
        )

    def test_create_batches_empty(self):
        """Test creating batches with empty list."""
        optimizer = BatchOptimizer()
        batches = optimizer.create_batches([])
        assert batches == []

    def test_create_batches_single_entry(self):
        """Test creating batches with single entry."""
        optimizer = BatchOptimizer()
        entries = [self.create_entry(1, 1000, 2000)]
        batches = optimizer.create_batches(entries)

        assert len(batches) == 1
        assert len(batches[0]) == 1
        assert batches[0][0].index == 1

    def test_create_batches_no_gaps(self):
        """Test creating batches when there are no significant gaps."""
        optimizer = BatchOptimizer(min_gap_seconds=3.0, max_batch_size=50)

        # Create 5 entries with 1-second gaps (less than min_gap)
        entries = []
        for i in range(5):
            start_ms = i * 2000
            end_ms = start_ms + 1000
            entries.append(self.create_entry(i + 1, start_ms, end_ms))

        batches = optimizer.create_batches(entries)

        # Should create single batch since no gaps >= 3 seconds
        assert len(batches) == 1
        assert len(batches[0]) == 5

    def test_create_batches_with_gaps(self):
        """Test creating batches with significant gaps."""
        optimizer = BatchOptimizer(min_gap_seconds=3.0, max_batch_size=50)

        entries = [
            self.create_entry(1, 1000, 2000),    # Gap of 1s
            self.create_entry(2, 3000, 4000),    # Gap of 1s
            self.create_entry(3, 5000, 6000),    # Gap of 5s (> 3s) -> split here
            self.create_entry(4, 11000, 12000),  # Gap of 1s
            self.create_entry(5, 13000, 14000),  # End
        ]

        batches = optimizer.create_batches(entries)

        # Should create 2 batches: [1,2,3] and [4,5]
        assert len(batches) == 2
        assert len(batches[0]) == 3
        assert len(batches[1]) == 2

    def test_create_batches_max_size_limit(self):
        """Test creating batches respects max_batch_size."""
        optimizer = BatchOptimizer(min_gap_seconds=10.0, max_batch_size=3)

        # Create 7 entries with no significant gaps
        entries = []
        for i in range(7):
            start_ms = i * 1000
            end_ms = start_ms + 500
            entries.append(self.create_entry(i + 1, start_ms, end_ms))

        batches = optimizer.create_batches(entries)

        # Should split into batches of max 3 entries
        assert len(batches) == 3  # 3 + 3 + 1
        assert len(batches[0]) == 3
        assert len(batches[1]) == 3
        assert len(batches[2]) == 1

    def test_create_batches_mixed_gaps_and_size(self):
        """Test batching with both gap and size constraints."""
        optimizer = BatchOptimizer(min_gap_seconds=5.0, max_batch_size=3)

        entries = [
            self.create_entry(1, 1000, 2000),    # Batch 1 start
            self.create_entry(2, 3000, 4000),
            self.create_entry(3, 5000, 6000),    # Batch 1 end (max size 3)
            self.create_entry(4, 7000, 8000),    # Batch 2 start
            self.create_entry(5, 9000, 10000),   # Gap of 6s after this -> split
            self.create_entry(6, 16000, 17000),  # Batch 3 start
        ]

        batches = optimizer.create_batches(entries)

        # Should create 3 batches
        assert len(batches) == 3
        assert len(batches[0]) == 3  # Entries 1-3 (max size)
        assert len(batches[1]) == 2  # Entries 4-5 (gap split)
        assert len(batches[2]) == 1  # Entry 6

    def test_create_smart_batches(self):
        """Test smart batching returns batch-gap tuples."""
        optimizer = BatchOptimizer(min_gap_seconds=3.0, max_batch_size=50)

        entries = [
            self.create_entry(1, 1000, 2000),
            self.create_entry(2, 3000, 4000),
            self.create_entry(3, 9000, 10000),  # 5s gap before this
        ]

        batches_with_gaps = optimizer.create_smart_batches(entries)

        assert len(batches_with_gaps) == 2
        assert len(batches_with_gaps[0][0]) == 2  # First batch has 2 entries
        assert batches_with_gaps[0][1] >= 3.0     # Gap is >= 3 seconds

    def test_get_batch_stats_empty(self):
        """Test getting statistics for empty batch list."""
        optimizer = BatchOptimizer()
        stats = optimizer.get_batch_stats([])

        assert stats['total_batches'] == 0
        assert stats['total_entries'] == 0
        assert stats['avg_batch_size'] == 0
        assert stats['min_batch_size'] == 0
        assert stats['max_batch_size'] == 0

    def test_get_batch_stats(self):
        """Test getting statistics for batches."""
        optimizer = BatchOptimizer()

        entries1 = [self.create_entry(i, i * 1000, (i + 1) * 1000) for i in range(1, 6)]
        entries2 = [self.create_entry(i, i * 1000, (i + 1) * 1000) for i in range(6, 9)]
        entries3 = [self.create_entry(10, 10000, 11000)]

        batches = [entries1, entries2, entries3]
        stats = optimizer.get_batch_stats(batches)

        assert stats['total_batches'] == 3
        assert stats['total_entries'] == 9
        assert stats['avg_batch_size'] == 3.0
        assert stats['min_batch_size'] == 1
        assert stats['max_batch_size'] == 5

    def test_print_batch_summary(self, capsys):
        """Test printing batch summary."""
        optimizer = BatchOptimizer()

        entries = [self.create_entry(i, i * 1000, (i + 1) * 1000) for i in range(1, 4)]
        batches = [entries]

        optimizer.print_batch_summary(batches)

        captured = capsys.readouterr()
        assert "Batch Summary" in captured.out
        assert "Total batches: 1" in captured.out
        assert "Total entries: 3" in captured.out

    def test_create_batches_exact_gap_boundary(self):
        """Test batching when gap equals min_gap_seconds exactly."""
        optimizer = BatchOptimizer(min_gap_seconds=3.0, max_batch_size=50)

        entries = [
            self.create_entry(1, 1000, 2000),
            self.create_entry(2, 5000, 6000),  # Gap is exactly 3.0s
            self.create_entry(3, 7000, 8000),
        ]

        batches = optimizer.create_batches(entries)

        # Gap of exactly 3.0s should trigger a split
        assert len(batches) == 2
        assert len(batches[0]) == 1
        assert len(batches[1]) == 2

    def test_create_batches_many_small_gaps(self):
        """Test batching with many small gaps below threshold."""
        optimizer = BatchOptimizer(min_gap_seconds=2.0, max_batch_size=100)

        # Create 20 entries with 1s gaps (below threshold)
        entries = []
        for i in range(20):
            start_ms = i * 1500
            end_ms = start_ms + 500
            entries.append(self.create_entry(i + 1, start_ms, end_ms))

        batches = optimizer.create_batches(entries)

        # Should create single batch
        assert len(batches) == 1
        assert len(batches[0]) == 20

    def test_create_batches_alternating_gaps(self):
        """Test batching with alternating small and large gaps."""
        optimizer = BatchOptimizer(min_gap_seconds=4.0, max_batch_size=50)

        entries = [
            self.create_entry(1, 1000, 2000),
            self.create_entry(2, 3000, 4000),    # Small gap (1s)
            self.create_entry(3, 9000, 10000),   # Large gap (5s) -> split
            self.create_entry(4, 11000, 12000),  # Small gap (1s)
            self.create_entry(5, 17000, 18000),  # Large gap (5s) -> split
            self.create_entry(6, 19000, 20000),  # Small gap (1s)
        ]

        batches = optimizer.create_batches(entries)

        # Should create 3 batches
        assert len(batches) == 3
        assert [len(b) for b in batches] == [2, 2, 2]

    def test_batch_optimizer_custom_settings(self):
        """Test BatchOptimizer with custom settings."""
        # Very strict settings
        optimizer = BatchOptimizer(min_gap_seconds=1.0, max_batch_size=2)

        entries = [
            self.create_entry(1, 1000, 2000),
            self.create_entry(2, 3500, 4500),  # 1.5s gap -> split
            self.create_entry(3, 5000, 6000),
        ]

        batches = optimizer.create_batches(entries)

        # With max_batch_size=2 and gaps >= 1.0s
        assert len(batches) >= 2
