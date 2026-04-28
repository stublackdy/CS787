"""Handle-based binary min-heap."""

from __future__ import annotations

from priority_queue_project.pq_stats import PriorityQueueStats


class BinaryHeap:
    """Array-backed binary heap with true decrease-key support."""

    def __init__(self) -> None:
        self.heap: list[tuple[int, float]] = []
        self.pos: dict[int, int] = {}
        self.stats = PriorityQueueStats()

    def insert(self, vertex: int, key: float) -> None:
        if vertex in self.pos:
            raise ValueError(f"vertex {vertex} is already in the heap")

        self.stats.insert_count += 1
        self.heap.append((vertex, key))
        self.pos[vertex] = len(self.heap) - 1
        self.stats.record_size(len(self.heap))
        self._sift_up(len(self.heap) - 1)

    def extract_min(self) -> tuple[int, float]:
        if not self.heap:
            raise IndexError("extract_min from an empty heap")

        self.stats.extract_min_count += 1
        min_vertex, min_key = self.heap[0]
        last = self.heap.pop()
        del self.pos[min_vertex]

        if self.heap:
            self.heap[0] = last
            self.pos[last[0]] = 0
            self._sift_down(0)

        return min_vertex, min_key

    def decrease_key(self, vertex: int, new_key: float) -> None:
        self.stats.decrease_key_count += 1
        if vertex not in self.pos:
            return

        index = self.pos[vertex]
        old_vertex, old_key = self.heap[index]
        self.stats.comparison_count += 1
        if new_key >= old_key:
            return

        self.stats.successful_decrease_key_count += 1
        self.heap[index] = (old_vertex, new_key)
        self._sift_up(index)

    def empty(self) -> bool:
        return not self.heap

    def contains(self, vertex: int) -> bool:
        return vertex in self.pos

    def _sift_up(self, index: int) -> None:
        while index > 0:
            parent = (index - 1) // 2
            if not self._less(index, parent):
                break
            self._swap(index, parent)
            index = parent

    def _sift_down(self, index: int) -> None:
        size = len(self.heap)
        while True:
            left = 2 * index + 1
            right = left + 1
            smallest = index

            if left < size and self._less(left, smallest):
                smallest = left
            if right < size and self._less(right, smallest):
                smallest = right
            if smallest == index:
                break

            self._swap(index, smallest)
            index = smallest

    def _less(self, i: int, j: int) -> bool:
        self.stats.comparison_count += 1
        vertex_i, key_i = self.heap[i]
        vertex_j, key_j = self.heap[j]
        return (key_i, vertex_i) < (key_j, vertex_j)

    def _swap(self, i: int, j: int) -> None:
        self.stats.swap_count += 1
        self.heap[i], self.heap[j] = self.heap[j], self.heap[i]
        self.pos[self.heap[i][0]] = i
        self.pos[self.heap[j][0]] = j

