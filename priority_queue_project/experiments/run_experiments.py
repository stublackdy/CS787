"""Run structural priority-queue experiments and write results to CSV."""

from __future__ import annotations

import argparse
from collections.abc import Callable
import csv
from pathlib import Path
import sys
from typing import Any

if __package__ in (None, ""):
    sys.path.append(str(Path(__file__).resolve().parents[2]))

from priority_queue_project.algorithms.dijkstra import dijkstra
from priority_queue_project.algorithms.prim import prim
from priority_queue_project.graph import Graph
from priority_queue_project.graph_generators import (
    dense_erdos_renyi_graph,
    grid_2d_graph,
    sparse_erdos_renyi_graph,
)
from priority_queue_project.heaps.binary_heap import BinaryHeap
from priority_queue_project.heaps.fibonacci_heap import FibonacciHeap
from priority_queue_project.heaps.pairing_heap import PairingHeap
from priority_queue_project.pq_stats import PriorityQueue
from priority_queue_project.snap_loader import SNAP_DATASETS, load_snap_graph


HeapFactory = Callable[[], PriorityQueue]


HEAPS: dict[str, HeapFactory] = {
    "binary": BinaryHeap,
    "pairing": PairingHeap,
    "fibonacci": FibonacciHeap,
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("priority_queue_results.csv"),
        help="CSV output path",
    )
    parser.add_argument(
        "--seeds",
        type=int,
        nargs="+",
        default=[0, 1, 2],
        help="Seeds used to generate graph instances",
    )
    parser.add_argument(
        "--graph-source",
        choices=["synthetic", "snap"],
        default="synthetic",
        help="Graph source used for this experiment run",
    )
    parser.add_argument(
        "--snap-dataset",
        choices=sorted(SNAP_DATASETS),
        help="SNAP dataset name when --graph-source=snap",
    )
    parser.add_argument(
        "--snap-data-dir",
        type=Path,
        default=Path("data/snap"),
        help="Directory containing SNAP edge-list files",
    )
    parser.add_argument(
        "--snap-path",
        type=Path,
        help="Explicit SNAP edge-list path; overrides --snap-data-dir lookup",
    )
    parser.add_argument(
        "--snap-max-edges",
        type=int,
        help="Optional maximum number of raw SNAP edges to load",
    )
    parser.add_argument(
        "--snap-max-vertices",
        type=int,
        help="Optional maximum number of SNAP vertices to load before reindexing",
    )
    parser.add_argument(
        "--snap-keep-components",
        action="store_true",
        help="Keep all loaded SNAP components instead of taking the largest component",
    )
    args = parser.parse_args()

    rows = run_experiments(
        args.seeds,
        graph_source=args.graph_source,
        snap_dataset=args.snap_dataset,
        snap_data_dir=args.snap_data_dir,
        snap_path=args.snap_path,
        snap_max_edges=args.snap_max_edges,
        snap_max_vertices=args.snap_max_vertices,
        snap_largest_component=not args.snap_keep_components,
    )
    write_csv(args.output, rows)
    print(f"Wrote {len(rows)} experiment rows to {args.output}")


def run_experiments(
    seeds: list[int],
    *,
    graph_source: str = "synthetic",
    snap_dataset: str | None = None,
    snap_data_dir: Path = Path("data/snap"),
    snap_path: Path | None = None,
    snap_max_edges: int | None = None,
    snap_max_vertices: int | None = None,
    snap_largest_component: bool = True,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for seed in seeds:
        graph_suite = _graph_suite_for_source(
            graph_source,
            seed=seed,
            snap_dataset=snap_dataset,
            snap_data_dir=snap_data_dir,
            snap_path=snap_path,
            snap_max_edges=snap_max_edges,
            snap_max_vertices=snap_max_vertices,
            snap_largest_component=snap_largest_component,
        )
        for family, parameter_label, graph in graph_suite:
            graph_stats = graph.statistics()
            base_row = {
                "graph_source": graph_source,
                "graph_family": family,
                "graph_parameters": parameter_label,
                "graph_size": graph.num_vertices,
                "seed": seed,
                **_prefixed("graph", graph_stats),
            }

            sources = sorted({0, graph.num_vertices // 2, graph.num_vertices - 1})
            for source in sources:
                if source < 0 or source >= graph.num_vertices:
                    continue
                for heap_name, heap_factory in HEAPS.items():
                    distances, algorithm_stats, pq_stats = _run_dijkstra(
                        graph,
                        source,
                        heap_factory,
                    )
                    rows.append(
                        {
                            **base_row,
                            "algorithm": "dijkstra",
                            "heap_type": heap_name,
                            "start_vertex": source,
                            "output_value": algorithm_stats.distance_checksum,
                            "reachable_output_count": sum(distance < float("inf") for distance in distances),
                            **algorithm_stats.to_dict(),
                            **pq_stats.to_dict(),
                        }
                    )

            for heap_name, heap_factory in HEAPS.items():
                mst_weight, algorithm_stats, pq_stats = _run_prim(graph, 0, heap_factory)
                rows.append(
                    {
                        **base_row,
                        "algorithm": "prim",
                        "heap_type": heap_name,
                        "start_vertex": 0,
                        "output_value": mst_weight,
                        **algorithm_stats.to_dict(),
                        **pq_stats.to_dict(),
                    }
                )
    return rows


def generate_graph_suite(seed: int) -> list[tuple[str, str, Graph]]:
    """Backward-compatible alias for the synthetic graph suite."""

    return generate_synthetic_graph_suite(seed)


def generate_synthetic_graph_suite(seed: int) -> list[tuple[str, str, Graph]]:
    """Create several graph families and sizes for one seed."""

    suite: list[tuple[str, str, Graph]] = []
    for n in (25, 50, 100):
        m = min(3 * n, n * (n - 1) // 2)
        suite.append(
            (
                "sparse_er_nm",
                f"n={n},m={m}",
                sparse_erdos_renyi_graph(n, m, seed=seed, connected=True),
            )
        )

    for n, p in ((25, 0.20), (50, 0.12), (100, 0.08)):
        suite.append(
            (
                "medium_er_np",
                f"n={n},p={p}",
                dense_erdos_renyi_graph(n, p, seed=seed, connected=True),
            )
        )

    for n, p in ((25, 0.35), (50, 0.25), (100, 0.18)):
        suite.append(
            (
                "dense_er_np",
                f"n={n},p={p}",
                dense_erdos_renyi_graph(n, p, seed=seed, connected=True),
            )
        )

    for n, p in ((25, 0.65), (50, 0.50), (100, 0.35)):
        suite.append(
            (
                "superdense_er_np",
                f"n={n},p={p}",
                dense_erdos_renyi_graph(n, p, seed=seed, connected=True),
            )
        )

    for rows, cols in ((5, 5), (8, 8), (10, 10)):
        suite.append(
            (
                "grid_2d",
                f"rows={rows},cols={cols}",
                grid_2d_graph(rows, cols, seed=seed),
            )
        )
    return suite


def generate_snap_graph_suite(
    dataset_name: str,
    *,
    seed: int,
    data_dir: Path,
    path: Path | None = None,
    max_edges: int | None = None,
    max_vertices: int | None = None,
    largest_component: bool = True,
) -> list[tuple[str, str, Graph]]:
    """Create a one-graph suite from a selected SNAP dataset."""

    graph = load_snap_graph(
        dataset_name,
        data_dir=data_dir,
        path=path,
        seed=seed,
        max_edges=max_edges,
        max_vertices=max_vertices,
        largest_component=largest_component,
    )
    parameters = [
        f"dataset={dataset_name}",
        f"component={'largest' if largest_component else 'all'}",
    ]
    if max_edges is not None:
        parameters.append(f"max_edges={max_edges}")
    if max_vertices is not None:
        parameters.append(f"max_vertices={max_vertices}")
    if path is not None:
        parameters.append(f"path={path}")
    return [(f"snap_{dataset_name}", ",".join(parameters), graph)]


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return

    preferred = [
        "algorithm",
        "heap_type",
        "graph_source",
        "graph_family",
        "graph_size",
        "graph_parameters",
        "seed",
        "start_vertex",
        "output_value",
    ]
    fieldnames = preferred + sorted({key for row in rows for key in row if key not in preferred})
    with path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _run_dijkstra(
    graph: Graph,
    source: int,
    heap_factory: HeapFactory,
) -> tuple[list[float], Any, Any]:
    holder: dict[str, PriorityQueue] = {}

    def factory() -> PriorityQueue:
        heap = heap_factory()
        holder["heap"] = heap
        return heap

    distances, stats = dijkstra(graph, source, factory)
    return distances, stats, holder["heap"].stats


def _run_prim(graph: Graph, start: int, heap_factory: HeapFactory) -> tuple[float, Any, Any]:
    holder: dict[str, PriorityQueue] = {}

    def factory() -> PriorityQueue:
        heap = heap_factory()
        holder["heap"] = heap
        return heap

    mst_weight, stats = prim(graph, start, factory)
    return mst_weight, stats, holder["heap"].stats


def _prefixed(prefix: str, values: dict[str, Any]) -> dict[str, Any]:
    return {f"{prefix}_{key}": value for key, value in values.items()}


def _graph_suite_for_source(
    graph_source: str,
    *,
    seed: int,
    snap_dataset: str | None,
    snap_data_dir: Path,
    snap_path: Path | None,
    snap_max_edges: int | None,
    snap_max_vertices: int | None,
    snap_largest_component: bool,
) -> list[tuple[str, str, Graph]]:
    if graph_source == "synthetic":
        return generate_synthetic_graph_suite(seed)
    if graph_source == "snap":
        if snap_dataset is None:
            raise ValueError("--snap-dataset is required when --graph-source=snap")
        return generate_snap_graph_suite(
            snap_dataset,
            seed=seed,
            data_dir=snap_data_dir,
            path=snap_path,
            max_edges=snap_max_edges,
            max_vertices=snap_max_vertices,
            largest_component=snap_largest_component,
        )
    raise ValueError(f"unknown graph source: {graph_source}")


if __name__ == "__main__":
    main()
