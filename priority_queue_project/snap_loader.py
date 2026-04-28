"""Load selected SNAP edge-list datasets into the local Graph abstraction."""

from __future__ import annotations

import gzip
from pathlib import Path
from typing import Iterable, TextIO

from priority_queue_project.graph import Edge, Graph


SNAP_DATASETS = {
    "ca-GrQc": {"directed": False, "filenames": ("ca-GrQc.txt", "ca-GrQc.txt.gz")},
    "roadNet-PA": {"directed": False, "filenames": ("roadNet-PA.txt", "roadNet-PA.txt.gz")},
    "roadNet-CA": {"directed": False, "filenames": ("roadNet-CA.txt", "roadNet-CA.txt.gz")},
}


def load_snap_graph(
    dataset_name: str,
    *,
    data_dir: Path,
    path: Path | None = None,
    seed: int = 0,
    max_edges: int | None = None,
    max_vertices: int | None = None,
    largest_component: bool = True,
) -> Graph:
    """Load a supported SNAP dataset as an undirected weighted Graph.

    SNAP files are unweighted edge lists with arbitrary integer node IDs. This
    loader maps observed node IDs to contiguous IDs and lets Graph assign
    deterministic positive weights from the supplied seed.
    """

    if dataset_name not in SNAP_DATASETS:
        supported = ", ".join(sorted(SNAP_DATASETS))
        raise ValueError(f"unsupported SNAP dataset {dataset_name!r}; supported: {supported}")
    if max_edges is not None and max_edges < 0:
        raise ValueError("max_edges must be non-negative")
    if max_vertices is not None and max_vertices < 0:
        raise ValueError("max_vertices must be non-negative")

    dataset_info = SNAP_DATASETS[dataset_name]
    edge_path = path or resolve_snap_path(dataset_name, data_dir)
    raw_edges, num_vertices = _read_snap_edges(
        edge_path,
        max_edges=max_edges,
        max_vertices=max_vertices,
    )
    graph = Graph.from_edge_list(
        num_vertices,
        raw_edges,
        directed=bool(dataset_info["directed"]),
        seed=seed,
    )
    if largest_component and not graph.directed:
        graph = largest_connected_component(graph)
    return graph


def resolve_snap_path(dataset_name: str, data_dir: Path) -> Path:
    """Return the first matching dataset path under ``data_dir``."""

    dataset_info = SNAP_DATASETS[dataset_name]
    for filename in dataset_info["filenames"]:
        candidate = data_dir / filename
        if candidate.exists():
            return candidate
    names = ", ".join(str(data_dir / filename) for filename in dataset_info["filenames"])
    raise FileNotFoundError(f"could not find {dataset_name}; expected one of: {names}")


def largest_connected_component(graph: Graph) -> Graph:
    """Return an induced subgraph for the largest connected component."""

    if graph.directed:
        raise ValueError("largest_connected_component expects an undirected graph")

    seen: set[int] = set()
    best_component: list[int] = []
    for vertex in range(graph.num_vertices):
        if vertex in seen:
            continue
        component = _component_vertices(graph, vertex, seen)
        if len(component) > len(best_component):
            best_component = component

    if len(best_component) == graph.num_vertices:
        return graph

    component_set = set(best_component)
    remap = {old: new for new, old in enumerate(sorted(best_component))}
    edges = [
        Edge(remap[edge.u], remap[edge.v], edge.weight)
        for edge in graph.edges
        if edge.u in component_set and edge.v in component_set
    ]
    return Graph.from_edge_list(len(best_component), edges, directed=False)


def _read_snap_edges(
    path: Path,
    *,
    max_edges: int | None,
    max_vertices: int | None,
) -> tuple[list[tuple[int, int]], int]:
    vertex_map: dict[int, int] = {}
    edges: list[tuple[int, int]] = []

    with _open_text(path) as file_obj:
        for line in file_obj:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue

            parts = stripped.split()
            if len(parts) < 2:
                continue

            original_u = int(parts[0])
            original_v = int(parts[1])
            u = _mapped_vertex(original_u, vertex_map, max_vertices)
            v = _mapped_vertex(original_v, vertex_map, max_vertices)
            if u is None or v is None:
                continue
            edges.append((u, v))
            if max_edges is not None and len(edges) >= max_edges:
                break

    return edges, len(vertex_map)


def _mapped_vertex(
    original_vertex: int,
    vertex_map: dict[int, int],
    max_vertices: int | None,
) -> int | None:
    if original_vertex in vertex_map:
        return vertex_map[original_vertex]
    if max_vertices is not None and len(vertex_map) >= max_vertices:
        return None
    vertex_map[original_vertex] = len(vertex_map)
    return vertex_map[original_vertex]


def _component_vertices(graph: Graph, start: int, seen: set[int]) -> list[int]:
    component: list[int] = []
    stack = [start]
    seen.add(start)
    while stack:
        vertex = stack.pop()
        component.append(vertex)
        for neighbor, _ in graph.adjacency[vertex]:
            if neighbor not in seen:
                seen.add(neighbor)
                stack.append(neighbor)
    return component


def _open_text(path: Path) -> Iterable[str]:
    if path.suffix == ".gz":
        return gzip.open(path, "rt", encoding="utf-8")
    return path.open("r", encoding="utf-8")

