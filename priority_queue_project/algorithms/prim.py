"""Prim's minimum-spanning-tree algorithm using the shared priority queue interface."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict, dataclass
import math

from priority_queue_project.graph import Graph
from priority_queue_project.pq_stats import PriorityQueue


@dataclass
class PrimStats:
    edge_scan_count: int = 0
    successful_key_update_count: int = 0
    visited_vertex_count: int = 0
    mst_weight: float = 0.0

    def to_dict(self) -> dict[str, int | float]:
        return asdict(self)


def prim(
    graph: Graph,
    start: int,
    pq_factory: Callable[[], PriorityQueue],
) -> tuple[float, PrimStats]:
    """Compute the MST weight for the component containing ``start``."""

    if graph.directed:
        raise ValueError("Prim's algorithm requires an undirected graph")
    if start < 0 or start >= graph.num_vertices:
        raise ValueError("start is outside the graph")

    best_key = [math.inf] * graph.num_vertices
    visited = [False] * graph.num_vertices
    stats = PrimStats()
    pq = pq_factory()

    best_key[start] = 0.0
    pq.insert(start, 0.0)

    while not pq.empty():
        vertex, key = pq.extract_min()
        if visited[vertex]:
            continue

        visited[vertex] = True
        stats.visited_vertex_count += 1
        stats.mst_weight += key

        for neighbor, weight in graph.adjacency[vertex]:
            if weight <= 0:
                raise ValueError("Prim's algorithm requires positive edge weights")

            stats.edge_scan_count += 1
            if not visited[neighbor] and weight < best_key[neighbor]:
                best_key[neighbor] = float(weight)
                stats.successful_key_update_count += 1
                if pq.contains(neighbor):
                    pq.decrease_key(neighbor, float(weight))
                else:
                    pq.insert(neighbor, float(weight))

    return stats.mst_weight, stats

