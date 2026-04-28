"""Basic pairing heap with node handles."""

from __future__ import annotations

from dataclasses import dataclass

from priority_queue_project.pq_stats import PriorityQueueStats


@dataclass
class _PairingNode:
    vertex: int
    key: float
    parent: "_PairingNode | None" = None
    child: "_PairingNode | None" = None
    sibling: "_PairingNode | None" = None


class PairingHeap:
    """Pairing heap supporting insert, extract-min, and decrease-key."""

    def __init__(self) -> None:
        self.root: _PairingNode | None = None
        self.handles: dict[int, _PairingNode] = {}
        self.size = 0
        self.stats = PriorityQueueStats()

    def insert(self, vertex: int, key: float) -> None:
        if vertex in self.handles:
            raise ValueError(f"vertex {vertex} is already in the heap")

        self.stats.insert_count += 1
        self.stats.node_allocation_count += 1
        node = _PairingNode(vertex, key)
        self.handles[vertex] = node
        self.root = self._meld(self.root, node)
        self.size += 1
        self.stats.record_size(self.size)

    def extract_min(self) -> tuple[int, float]:
        if self.root is None:
            raise IndexError("extract_min from an empty heap")

        self.stats.extract_min_count += 1
        old_root = self.root
        del self.handles[old_root.vertex]
        self.size -= 1

        child = old_root.child
        old_root.child = None
        self.root = self._two_pass_pair(child)
        if self.root is not None:
            self.root.parent = None
        return old_root.vertex, old_root.key

    def decrease_key(self, vertex: int, new_key: float) -> None:
        self.stats.decrease_key_count += 1
        node = self.handles.get(vertex)
        if node is None:
            return

        self.stats.comparison_count += 1
        if new_key >= node.key:
            return

        self.stats.successful_decrease_key_count += 1
        node.key = new_key
        if node is self.root:
            return

        self._cut(node)
        self.root = self._meld(self.root, node)

    def empty(self) -> bool:
        return self.root is None

    def contains(self, vertex: int) -> bool:
        return vertex in self.handles

    def _two_pass_pair(self, first_child: _PairingNode | None) -> _PairingNode | None:
        if first_child is None:
            return None

        paired_roots: list[_PairingNode] = []
        current = first_child
        while current is not None:
            self.stats.pointer_traversal_count += 1
            first = current
            second = current.sibling
            next_pair = second.sibling if second is not None else None

            first.parent = None
            first.sibling = None
            if second is not None:
                self.stats.pointer_traversal_count += 1
                second.parent = None
                second.sibling = None
                paired_roots.append(self._meld(first, second))
            else:
                paired_roots.append(first)

            current = next_pair

        root = paired_roots.pop()
        while paired_roots:
            root = self._meld(paired_roots.pop(), root)
        return root

    def _meld(
        self,
        first: _PairingNode | None,
        second: _PairingNode | None,
    ) -> _PairingNode | None:
        if first is None:
            return second
        if second is None:
            return first

        self.stats.meld_count += 1
        self.stats.comparison_count += 1
        if self._node_less(second, first):
            first, second = second, first

        self._link(parent=first, child=second)
        return first

    def _link(self, *, parent: _PairingNode, child: _PairingNode) -> None:
        self.stats.link_count += 1
        child.parent = parent
        child.sibling = parent.child
        parent.child = child

    def _cut(self, node: _PairingNode) -> None:
        parent = node.parent
        if parent is None:
            return

        self.stats.cut_count += 1
        if parent.child is node:
            parent.child = node.sibling
        else:
            previous = parent.child
            while previous is not None and previous.sibling is not node:
                self.stats.pointer_traversal_count += 1
                previous = previous.sibling
            if previous is None:
                raise RuntimeError("pairing heap parent/child links are inconsistent")
            self.stats.pointer_traversal_count += 1
            previous.sibling = node.sibling

        node.parent = None
        node.sibling = None

    @staticmethod
    def _node_less(first: _PairingNode, second: _PairingNode) -> bool:
        return (first.key, first.vertex) < (second.key, second.vertex)

