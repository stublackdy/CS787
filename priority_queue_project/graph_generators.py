"""Synthetic graph generators used by the experiment runner."""

from __future__ import annotations

import random

from priority_queue_project.graph import Graph


def sparse_erdos_renyi_graph(
    n: int,
    m: int,
    *,
    directed: bool = False,
    seed: int = 0,
    connected: bool = False,
) -> Graph:
    """Generate an Erdos-Renyi graph by sampling exactly ``m`` edges.

    For undirected graphs, ``connected=True`` first creates a random spanning
    tree and then samples the remaining edges. This keeps Prim experiments from
    silently measuring only one connected component.
    """

    if n < 0:
        raise ValueError("n must be non-negative")

    possible_edges = _all_possible_edges(n, directed)
    if m < 0 or m > len(possible_edges):
        raise ValueError(f"m must be in [0, {len(possible_edges)}]")

    rng = random.Random(seed)
    if connected and not directed:
        chosen = _connected_undirected_edges(n, m, rng)
    else:
        chosen = rng.sample(possible_edges, m)
    weighted_edges = [(u, v, rng.randint(1, 100)) for u, v in chosen]
    return Graph.from_edge_list(n, weighted_edges, directed=directed, seed=seed)


def dense_erdos_renyi_graph(
    n: int,
    p: float,
    *,
    directed: bool = False,
    seed: int = 0,
    connected: bool = False,
) -> Graph:
    """Generate an Erdos-Renyi graph by including each possible edge with probability ``p``.

    For undirected graphs, ``connected=True`` guarantees connectivity by adding
    a random spanning tree before sampling the remaining candidate edges.
    """

    if n < 0:
        raise ValueError("n must be non-negative")
    if p < 0.0 or p > 1.0:
        raise ValueError("p must be in [0, 1]")

    rng = random.Random(seed)
    if connected and not directed:
        chosen = _connected_undirected_edges_by_probability(n, p, rng)
    else:
        chosen = [(u, v) for u, v in _all_possible_edges(n, directed) if rng.random() < p]
    weighted_edges = [(u, v, rng.randint(1, 100)) for u, v in chosen]
    return Graph.from_edge_list(n, weighted_edges, directed=directed, seed=seed)


def grid_2d_graph(
    rows: int,
    cols: int,
    *,
    directed: bool = False,
    seed: int = 0,
) -> Graph:
    """Generate a 2D grid graph with 4-neighbor horizontal and vertical edges."""

    if rows < 0 or cols < 0:
        raise ValueError("rows and cols must be non-negative")

    rng = random.Random(seed)
    edges: list[tuple[int, int, int]] = []

    def vertex(row: int, col: int) -> int:
        return row * cols + col

    for row in range(rows):
        for col in range(cols):
            current = vertex(row, col)
            if col + 1 < cols:
                neighbor = vertex(row, col + 1)
                weight = rng.randint(1, 100)
                edges.append((current, neighbor, weight))
                if directed:
                    edges.append((neighbor, current, weight))
            if row + 1 < rows:
                neighbor = vertex(row + 1, col)
                weight = rng.randint(1, 100)
                edges.append((current, neighbor, weight))
                if directed:
                    edges.append((neighbor, current, weight))

    return Graph.from_edge_list(rows * cols, edges, directed=directed, seed=seed)


def _all_possible_edges(n: int, directed: bool) -> list[tuple[int, int]]:
    if directed:
        return [(u, v) for u in range(n) for v in range(n) if u != v]
    return [(u, v) for u in range(n) for v in range(u + 1, n)]


def _connected_undirected_edges(
    n: int,
    m: int,
    rng: random.Random,
) -> list[tuple[int, int]]:
    minimum_edges = max(0, n - 1)
    if m < minimum_edges:
        raise ValueError(f"m must be at least {minimum_edges} to generate a connected graph")

    tree_edges = _random_spanning_tree_edges(n, rng)
    tree_edge_set = set(tree_edges)
    remaining_edges = [edge for edge in _all_possible_edges(n, directed=False) if edge not in tree_edge_set]
    return tree_edges + rng.sample(remaining_edges, m - len(tree_edges))


def _connected_undirected_edges_by_probability(
    n: int,
    p: float,
    rng: random.Random,
) -> list[tuple[int, int]]:
    tree_edges = _random_spanning_tree_edges(n, rng)
    tree_edge_set = set(tree_edges)
    sampled_edges = [
        edge
        for edge in _all_possible_edges(n, directed=False)
        if edge not in tree_edge_set and rng.random() < p
    ]
    return tree_edges + sampled_edges


def _random_spanning_tree_edges(n: int, rng: random.Random) -> list[tuple[int, int]]:
    edges: list[tuple[int, int]] = []
    for vertex in range(1, n):
        parent = rng.randrange(vertex)
        edges.append((parent, vertex))
    return edges
