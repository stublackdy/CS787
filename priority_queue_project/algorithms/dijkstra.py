"""Dijkstra's shortest-path algorithm using the shared priority queue interface."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict, dataclass
import math

from priority_queue_project.graph import Graph
from priority_queue_project.pq_stats import PriorityQueue


@dataclass
class DijkstraStats:
    edge_scan_count: int = 0
    relax_attempt_count: int = 0
    successful_relax_count: int = 0
    reachable_vertex_count: int = 0
    distance_checksum: float = 0.0

    def to_dict(self) -> dict[str, int | float]:
        return asdict(self)


def dijkstra(
    graph: Graph,
    source: int,
    pq_factory: Callable[[], PriorityQueue],
) -> tuple[list[float], DijkstraStats]:
    """Run Dijkstra from ``source`` and return distances plus algorithm stats."""

    if source < 0 or source >= graph.num_vertices:
        raise ValueError("source is outside the graph")

    distances = [math.inf] * graph.num_vertices
    finalized = [False] * graph.num_vertices
    stats = DijkstraStats()
    pq = pq_factory()

    distances[source] = 0.0
    pq.insert(source, 0.0)

    while not pq.empty():
        vertex, current_distance = pq.extract_min()
        if finalized[vertex]:
            continue

        finalized[vertex] = True
        stats.reachable_vertex_count += 1

        for neighbor, weight in graph.adjacency[vertex]:
            if weight <= 0:
                raise ValueError("Dijkstra requires positive edge weights")

            stats.edge_scan_count += 1
            if finalized[neighbor]:
                continue

            stats.relax_attempt_count += 1
            candidate = current_distance + weight
            if candidate < distances[neighbor]:
                distances[neighbor] = candidate
                stats.successful_relax_count += 1
                if pq.contains(neighbor):
                    pq.decrease_key(neighbor, candidate)
                else:
                    pq.insert(neighbor, candidate)

    stats.distance_checksum = sum(distance for distance in distances if math.isfinite(distance))
    return distances, stats
