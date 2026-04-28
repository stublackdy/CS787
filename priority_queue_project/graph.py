"""Graph abstraction used by the experiments.

The project assumes vertices are contiguous integers in ``[0, n - 1]``.
The ``Graph`` class stores a normalized weighted edge list and an adjacency
list built from that edge list.
"""

from __future__ import annotations

from dataclasses import dataclass
import random
from typing import Iterable, Sequence


@dataclass(frozen=True)
class Edge:
    """A weighted edge from ``u`` to ``v``."""

    u: int
    v: int
    weight: int


RawEdge = Edge | Sequence[int | float | None]


class Graph:
    """Weighted graph with both edge-list and adjacency-list representations."""

    def __init__(
        self,
        num_vertices: int,
        edges: Iterable[RawEdge] | None = None,
        *,
        directed: bool = False,
        seed: int = 0,
        remove_self_loops: bool = True,
        merge_duplicates: bool = True,
    ) -> None:
        if num_vertices < 0:
            raise ValueError("num_vertices must be non-negative")

        self.num_vertices = num_vertices
        self.directed = directed
        self.edges: list[Edge] = self._normalize_edges(
            list(edges or []),
            seed=seed,
            remove_self_loops=remove_self_loops,
            merge_duplicates=merge_duplicates,
        )
        self.adjacency: list[list[tuple[int, int]]] = self.build_adjacency_list()

    @classmethod
    def from_edge_list(
        cls,
        num_vertices: int,
        edges: Iterable[RawEdge],
        *,
        directed: bool = False,
        seed: int = 0,
        remove_self_loops: bool = True,
        merge_duplicates: bool = True,
    ) -> "Graph":
        """Construct a graph from a raw edge list.

        Edges may be ``Edge`` instances, ``(u, v)`` tuples, or ``(u, v, w)``
        tuples. Missing weights are filled with deterministic positive weights.
        """

        return cls(
            num_vertices,
            edges,
            directed=directed,
            seed=seed,
            remove_self_loops=remove_self_loops,
            merge_duplicates=merge_duplicates,
        )

    @property
    def num_edges(self) -> int:
        """Return the number of normalized weighted edges."""

        return len(self.edges)

    def remove_self_loop_edges(self) -> None:
        """Remove self-loops from the current edge list and rebuild adjacency."""

        self.edges = [edge for edge in self.edges if edge.u != edge.v]
        self.adjacency = self.build_adjacency_list()

    def merge_duplicate_edges(self) -> None:
        """Merge duplicate edges, keeping the smallest weight for each pair."""

        self.edges = self._merge_edges(self.edges)
        self.adjacency = self.build_adjacency_list()

    def build_adjacency_list(self) -> list[list[tuple[int, int]]]:
        """Build and return an adjacency list as ``[(neighbor, weight), ...]``."""

        adjacency: list[list[tuple[int, int]]] = [[] for _ in range(self.num_vertices)]
        for edge in self.edges:
            adjacency[edge.u].append((edge.v, edge.weight))
            if not self.directed:
                adjacency[edge.v].append((edge.u, edge.weight))

        for neighbors in adjacency:
            neighbors.sort(key=lambda item: item[0])
        return adjacency

    def statistics(self) -> dict[str, int | float | bool]:
        """Return basic graph statistics."""

        degrees = [len(neighbors) for neighbors in self.adjacency]
        avg_degree = sum(degrees) / self.num_vertices if self.num_vertices else 0.0
        return {
            "num_vertices": self.num_vertices,
            "num_edges": self.num_edges,
            "average_degree": avg_degree,
            "maximum_degree": max(degrees, default=0),
            "directed": self.directed,
        }

    def _normalize_edges(
        self,
        raw_edges: list[RawEdge],
        *,
        seed: int,
        remove_self_loops: bool,
        merge_duplicates: bool,
    ) -> list[Edge]:
        rng = random.Random(seed)
        normalized: list[Edge] = []

        for raw_edge in raw_edges:
            edge = self._coerce_edge(raw_edge, rng)
            self._validate_vertex(edge.u)
            self._validate_vertex(edge.v)
            if remove_self_loops and edge.u == edge.v:
                continue
            if edge.weight <= 0:
                raise ValueError("edge weights must be positive")
            normalized.append(edge)

        if merge_duplicates:
            normalized = self._merge_edges(normalized)
        return sorted(normalized, key=lambda edge: (edge.u, edge.v, edge.weight))

    def _coerce_edge(self, raw_edge: RawEdge, rng: random.Random) -> Edge:
        if isinstance(raw_edge, Edge):
            return raw_edge

        if len(raw_edge) not in (2, 3):
            raise ValueError("edges must be Edge, (u, v), or (u, v, weight)")

        u = int(raw_edge[0])
        v = int(raw_edge[1])
        weight_value = raw_edge[2] if len(raw_edge) == 3 else None
        weight = rng.randint(1, 100) if weight_value is None else int(weight_value)
        return Edge(u, v, weight)

    def _validate_vertex(self, vertex: int) -> None:
        if vertex < 0 or vertex >= self.num_vertices:
            raise ValueError(f"vertex {vertex} is outside [0, {self.num_vertices - 1}]")

    def _merge_edges(self, edges: Iterable[Edge]) -> list[Edge]:
        best: dict[tuple[int, int], int] = {}
        for edge in edges:
            key = (edge.u, edge.v) if self.directed else (min(edge.u, edge.v), max(edge.u, edge.v))
            if key not in best or edge.weight < best[key]:
                best[key] = edge.weight
        return [Edge(u, v, weight) for (u, v), weight in best.items()]

