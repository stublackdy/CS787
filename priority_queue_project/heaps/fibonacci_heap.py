"""Basic Fibonacci heap with node handles."""

from __future__ import annotations

from dataclasses import dataclass, field

from priority_queue_project.pq_stats import PriorityQueueStats


@dataclass
class _FibNode:
    vertex: int
    key: float
    degree: int = 0
    mark: bool = False
    parent: "_FibNode | None" = None
    child: "_FibNode | None" = None
    left: "_FibNode" = field(init=False, repr=False)
    right: "_FibNode" = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self.left = self
        self.right = self


class FibonacciHeap:
    """Fibonacci heap supporting insert, extract-min, and decrease-key."""

    def __init__(self) -> None:
        self.min_node: _FibNode | None = None
        self.handles: dict[int, _FibNode] = {}
        self.size = 0
        self.stats = PriorityQueueStats()

    def insert(self, vertex: int, key: float) -> None:
        if vertex in self.handles:
            raise ValueError(f"vertex {vertex} is already in the heap")

        self.stats.insert_count += 1
        self.stats.node_allocation_count += 1
        node = _FibNode(vertex, key)
        self.handles[vertex] = node
        self._add_to_root_list(node)
        self.size += 1
        self.stats.record_size(self.size)

    def extract_min(self) -> tuple[int, float]:
        z = self.min_node
        if z is None:
            raise IndexError("extract_min from an empty heap")

        self.stats.extract_min_count += 1
        children = self._iterate_list(z.child)
        for child in children:
            child.parent = None
            child.mark = False
            child.left = child
            child.right = child

        if z.right is z:
            self.min_node = None
        else:
            next_root = z.right
            self._remove_from_list(z)
            self.min_node = next_root

        z.child = None
        z.left = z
        z.right = z
        del self.handles[z.vertex]
        self.size -= 1

        for child in children:
            self._add_to_root_list(child)

        if self.min_node is not None:
            self._consolidate()

        return z.vertex, z.key

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
        parent = node.parent
        if parent is not None:
            self.stats.comparison_count += 1
            if self._node_less(node, parent):
                self._cut(node, parent)
                self._cascading_cut(parent)

        if self.min_node is None:
            self.min_node = node
        else:
            self.stats.comparison_count += 1
            if self._node_less(node, self.min_node):
                self.min_node = node

    def empty(self) -> bool:
        return self.size == 0

    def contains(self, vertex: int) -> bool:
        return vertex in self.handles

    def _consolidate(self) -> None:
        degree_table: list[_FibNode | None] = []
        roots = self._iterate_list(self.min_node)

        for root in roots:
            if root.parent is not None:
                continue
            x = root
            d = x.degree
            while True:
                while d >= len(degree_table):
                    degree_table.append(None)
                y = degree_table[d]
                if y is None:
                    break

                self.stats.comparison_count += 1
                if self._node_less(y, x):
                    x, y = y, x
                self._heap_link(y, x)
                degree_table[d] = None
                d = x.degree

            degree_table[d] = x

        self.min_node = None
        for node in degree_table:
            if node is not None:
                node.left = node
                node.right = node
                self._add_to_root_list(node)

    def _heap_link(self, child: _FibNode, parent: _FibNode) -> None:
        self.stats.link_count += 1
        self._remove_from_list(child)
        child.parent = parent
        child.mark = False
        child.left = child
        child.right = child

        if parent.child is None:
            parent.child = child
        else:
            self._insert_after(parent.child, child)
        parent.degree += 1

    def _cut(self, node: _FibNode, parent: _FibNode) -> None:
        self.stats.cut_count += 1
        if node.right is node:
            parent.child = None
        else:
            if parent.child is node:
                parent.child = node.right
            self._remove_from_list(node)
        parent.degree -= 1

        node.parent = None
        node.mark = False
        node.left = node
        node.right = node
        self._add_to_root_list(node)

    def _cascading_cut(self, node: _FibNode) -> None:
        parent = node.parent
        if parent is None:
            return

        if not node.mark:
            node.mark = True
            return

        self._cut(node, parent)
        self._cascading_cut(parent)

    def _add_to_root_list(self, node: _FibNode) -> None:
        node.parent = None
        if self.min_node is None:
            node.left = node
            node.right = node
            self.min_node = node
            return

        self._insert_after(self.min_node, node)
        self.stats.comparison_count += 1
        if self._node_less(node, self.min_node):
            self.min_node = node

    def _insert_after(self, existing: _FibNode, node: _FibNode) -> None:
        self.stats.pointer_traversal_count += 1
        node.left = existing
        node.right = existing.right
        existing.right.left = node
        existing.right = node

    def _remove_from_list(self, node: _FibNode) -> None:
        self.stats.pointer_traversal_count += 1
        node.left.right = node.right
        node.right.left = node.left
        node.left = node
        node.right = node

    def _iterate_list(self, start: _FibNode | None) -> list[_FibNode]:
        if start is None:
            return []

        nodes: list[_FibNode] = []
        current = start
        while True:
            nodes.append(current)
            self.stats.pointer_traversal_count += 1
            current = current.right
            if current is start:
                break
        return nodes

    @staticmethod
    def _node_less(first: _FibNode, second: _FibNode) -> bool:
        return (first.key, first.vertex) < (second.key, second.vertex)
