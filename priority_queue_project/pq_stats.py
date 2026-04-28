"""Priority queue operation counters."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Protocol


@dataclass
class PriorityQueueStats:
    """Counters common to all heap implementations."""

    insert_count: int = 0
    extract_min_count: int = 0
    decrease_key_count: int = 0
    successful_decrease_key_count: int = 0
    comparison_count: int = 0
    swap_count: int = 0
    link_count: int = 0
    cut_count: int = 0
    meld_count: int = 0
    node_allocation_count: int = 0
    pointer_traversal_count: int = 0
    peak_size: int = 0

    def record_size(self, size: int) -> None:
        """Update the peak queue size after a size-changing operation."""

        if size > self.peak_size:
            self.peak_size = size

    def to_dict(self) -> dict[str, int]:
        """Return a plain dictionary suitable for CSV output."""

        return asdict(self)


class PriorityQueue(Protocol):
    """Common priority queue interface used by graph algorithms."""

    stats: PriorityQueueStats

    def insert(self, vertex: int, key: float) -> None:
        """Insert ``vertex`` with the given priority key."""

    def extract_min(self) -> tuple[int, float]:
        """Remove and return the ``(vertex, key)`` pair with minimum key."""

    def decrease_key(self, vertex: int, new_key: float) -> None:
        """Decrease ``vertex`` to ``new_key`` if the new key is smaller."""

    def empty(self) -> bool:
        """Return whether the priority queue is empty."""

    def contains(self, vertex: int) -> bool:
        """Return whether ``vertex`` is currently present in the queue."""

