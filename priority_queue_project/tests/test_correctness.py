"""Correctness tests comparing heap implementations."""

from __future__ import annotations

import math
from pathlib import Path
import tempfile
import unittest

from priority_queue_project.algorithms.dijkstra import dijkstra
from priority_queue_project.algorithms.prim import prim
from priority_queue_project.experiments.analyze_results import summarize, with_derived_metrics
from priority_queue_project.experiments.run_experiments import generate_graph_suite, run_experiments
from priority_queue_project.graph import Graph
from priority_queue_project.graph_generators import dense_erdos_renyi_graph, sparse_erdos_renyi_graph
from priority_queue_project.heaps.binary_heap import BinaryHeap
from priority_queue_project.heaps.fibonacci_heap import FibonacciHeap
from priority_queue_project.heaps.pairing_heap import PairingHeap
from priority_queue_project.snap_loader import load_snap_graph


HEAPS = {
    "binary": BinaryHeap,
    "pairing": PairingHeap,
    "fibonacci": FibonacciHeap,
}


class CorrectnessTests(unittest.TestCase):
    def test_dijkstra_hand_written_graph(self) -> None:
        graph = Graph.from_edge_list(
            5,
            [
                (0, 1, 4),
                (0, 2, 1),
                (2, 1, 2),
                (1, 3, 1),
                (2, 3, 5),
                (3, 4, 3),
            ],
            directed=True,
        )
        expected = [0.0, 3.0, 1.0, 4.0, 7.0]

        for heap_name, heap_factory in HEAPS.items():
            with self.subTest(heap=heap_name):
                distances, stats = dijkstra(graph, 0, heap_factory)
                self.assertEqual(expected, distances)
                self.assertEqual(5, stats.reachable_vertex_count)

    def test_prim_hand_written_graph(self) -> None:
        graph = Graph.from_edge_list(
            5,
            [
                (0, 1, 4),
                (0, 2, 1),
                (2, 1, 2),
                (1, 3, 1),
                (2, 3, 5),
                (3, 4, 3),
            ],
            directed=False,
        )

        for heap_name, heap_factory in HEAPS.items():
            with self.subTest(heap=heap_name):
                mst_weight, stats = prim(graph, 0, heap_factory)
                self.assertEqual(7.0, mst_weight)
                self.assertEqual(5, stats.visited_vertex_count)

    def test_randomized_small_graphs_match_binary_heap(self) -> None:
        for seed in range(10):
            for n in range(2, 12):
                graph = dense_erdos_renyi_graph(n, 0.35, seed=seed)
                self._assert_dijkstra_matches_binary(graph, source=0)
                self._assert_prim_matches_binary(graph)

    def test_random_graph_generators_can_create_connected_undirected_graphs(self) -> None:
        for seed in range(10):
            with self.subTest(generator="sparse", seed=seed):
                graph = sparse_erdos_renyi_graph(25, 40, seed=seed, connected=True)
                self.assertEqual(graph.num_vertices, _reachable_count(graph, 0))

            with self.subTest(generator="dense", seed=seed):
                graph = dense_erdos_renyi_graph(25, 0.05, seed=seed, connected=True)
                self.assertEqual(graph.num_vertices, _reachable_count(graph, 0))

    def test_er_generators_default_to_standard_unconditioned_sampling(self) -> None:
        graph = dense_erdos_renyi_graph(25, 0.0, seed=0)
        self.assertEqual(0, graph.num_edges)

    def test_experiment_graph_suite_uses_connected_graphs(self) -> None:
        for family, parameters, graph in generate_graph_suite(seed=0):
            with self.subTest(family=family, parameters=parameters):
                self.assertEqual(graph.num_vertices, _reachable_count(graph, 0))

    def test_snap_loader_reindexes_and_keeps_largest_component(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "ca-GrQc.txt"
            path.write_text(
                "\n".join(
                    [
                        "# FromNodeId ToNodeId",
                        "10 20",
                        "20 30",
                        "100 101",
                    ]
                ),
                encoding="utf-8",
            )

            graph = load_snap_graph("ca-GrQc", data_dir=Path(tmp_dir), seed=0)

            self.assertEqual(3, graph.num_vertices)
            self.assertEqual(2, graph.num_edges)
            self.assertEqual(3, _reachable_count(graph, 0))

    def test_snap_experiment_source_runs_on_loaded_dataset(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "ca-GrQc.txt"
            path.write_text("10 20\n20 30\n30 40\n", encoding="utf-8")

            rows = run_experiments(
                [0],
                graph_source="snap",
                snap_dataset="ca-GrQc",
                snap_data_dir=Path(tmp_dir),
            )

            self.assertEqual(12, len(rows))
            self.assertTrue(all(row["graph_source"] == "snap" for row in rows))
            self.assertTrue(all(row["graph_family"] == "snap_ca-GrQc" for row in rows))

    def test_dijkstra_relax_attempts_skip_finalized_neighbors(self) -> None:
        graph = Graph.from_edge_list(
            3,
            [
                (0, 1, 1),
                (0, 2, 10),
                (1, 2, 1),
                (2, 0, 1),
            ],
            directed=True,
        )

        _, stats = dijkstra(graph, 0, BinaryHeap)

        self.assertEqual(4, stats.edge_scan_count)
        self.assertEqual(3, stats.relax_attempt_count)
        self.assertEqual(3, stats.successful_relax_count)

    def test_prim_summary_skips_relax_rate_metric(self) -> None:
        prim_row = with_derived_metrics(
            {
                "algorithm": "prim",
                "graph_family": "grid_2d",
                "graph_size": "25",
                "graph_parameters": "rows=5,cols=5",
                "heap_type": "binary",
                "decrease_key_count": "1",
                "extract_min_count": "5",
                "successful_decrease_key_count": "1",
                "edge_scan_count": "8",
                "peak_size": "3",
                "comparison_count": "7",
            }
        )
        summary = summarize([prim_row])

        self.assertNotIn("successful_relax_rate", prim_row)
        self.assertNotIn("mean_successful_relax_rate", summary[0])
        self.assertEqual("rows=5,cols=5", summary[0]["graph_parameters"])

    def test_fibonacci_decrease_key_counts_min_update_comparison(self) -> None:
        heap = FibonacciHeap()
        heap.insert(0, 10)
        heap.insert(1, 20)
        before = heap.stats.comparison_count

        heap.decrease_key(1, 5)

        self.assertEqual(before + 2, heap.stats.comparison_count)

    def _assert_dijkstra_matches_binary(self, graph: Graph, source: int) -> None:
        baseline, _ = dijkstra(graph, source, BinaryHeap)
        for heap_name, heap_factory in HEAPS.items():
            with self.subTest(algorithm="dijkstra", heap=heap_name, vertices=graph.num_vertices):
                distances, _ = dijkstra(graph, source, heap_factory)
                self.assertEqual(_canonical_distances(baseline), _canonical_distances(distances))

    def _assert_prim_matches_binary(self, graph: Graph) -> None:
        baseline, _ = prim(graph, 0, BinaryHeap)
        for heap_name, heap_factory in HEAPS.items():
            with self.subTest(algorithm="prim", heap=heap_name, vertices=graph.num_vertices):
                mst_weight, _ = prim(graph, 0, heap_factory)
                self.assertEqual(baseline, mst_weight)


def _canonical_distances(distances: list[float]) -> list[float | str]:
    return ["inf" if math.isinf(distance) else distance for distance in distances]


def _reachable_count(graph: Graph, source: int) -> int:
    seen = {source}
    stack = [source]
    while stack:
        vertex = stack.pop()
        for neighbor, _ in graph.adjacency[vertex]:
            if neighbor not in seen:
                seen.add(neighbor)
                stack.append(neighbor)
    return len(seen)


if __name__ == "__main__":
    unittest.main()
