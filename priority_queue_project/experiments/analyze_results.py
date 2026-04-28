"""Analyze experiment CSV output and compute derived structural metrics."""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path
import sys
from typing import Any

if __package__ in (None, ""):
    sys.path.append(str(Path(__file__).resolve().parents[2]))


DERIVED_METRICS = [
    "decrease_key_per_extract",
    "successful_decrease_key_rate",
    "edge_scan_per_extract",
    "peak_heap_size",
    "comparison_count",
    "swap_count",
    "link_count",
    "cut_count",
    "meld_count",
]

DIJKSTRA_DERIVED_METRICS = ["successful_relax_rate"]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="Experiment result CSV")
    parser.add_argument(
        "--summary-output",
        type=Path,
        default=Path("priority_queue_summary.csv"),
        help="CSV path for grouped summary metrics",
    )
    args = parser.parse_args()

    rows = load_rows(args.input)
    derived = [with_derived_metrics(row) for row in rows]
    summary = summarize(derived)
    write_csv(args.summary_output, summary)
    print_summary(summary)
    print(f"\nWrote grouped summary to {args.summary_output}")


def load_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as csv_file:
        return list(csv.DictReader(csv_file))


def with_derived_metrics(row: dict[str, Any]) -> dict[str, Any]:
    output = dict(row)
    decrease_key_count = _number(row.get("decrease_key_count"))
    extract_min_count = _number(row.get("extract_min_count"))
    successful_decrease_key_count = _number(row.get("successful_decrease_key_count"))
    relax_attempt_count = _number(row.get("relax_attempt_count"))
    successful_relax_count = _number(row.get("successful_relax_count"))
    edge_scan_count = _number(row.get("edge_scan_count"))

    output["decrease_key_per_extract"] = _ratio(decrease_key_count, extract_min_count)
    output["successful_decrease_key_rate"] = _ratio(successful_decrease_key_count, decrease_key_count)
    if row.get("algorithm") == "dijkstra":
        output["successful_relax_rate"] = _ratio(successful_relax_count, relax_attempt_count)
    output["edge_scan_per_extract"] = _ratio(edge_scan_count, extract_min_count)
    output["peak_heap_size"] = _number(row.get("peak_size"))
    output["comparison_count"] = _number(row.get("comparison_count"))
    output["swap_count"] = _number(row.get("swap_count"))
    output["link_count"] = _number(row.get("link_count"))
    output["cut_count"] = _number(row.get("cut_count"))
    output["meld_count"] = _number(row.get("meld_count"))
    return output


def summarize(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str, str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        key = (
            str(row.get("algorithm", "")),
            str(row.get("graph_family", "")),
            str(row.get("graph_size", "")),
            str(row.get("graph_parameters", "")),
            str(row.get("heap_type", "")),
        )
        groups[key].append(row)

    summary_rows: list[dict[str, Any]] = []
    for (algorithm, graph_family, graph_size, graph_parameters, heap_type), group_rows in sorted(groups.items()):
        summary: dict[str, Any] = {
            "algorithm": algorithm,
            "graph_family": graph_family,
            "graph_size": graph_size,
            "graph_parameters": graph_parameters,
            "heap_type": heap_type,
            "row_count": len(group_rows),
        }
        for metric in _derived_metrics_for_algorithm(algorithm):
            summary[f"mean_{metric}"] = _mean(_number(row.get(metric)) for row in group_rows)
        summary_rows.append(summary)
    return summary_rows


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return

    preferred = ["algorithm", "graph_family", "graph_size", "graph_parameters", "heap_type", "row_count"]
    fieldnames = preferred + sorted({key for row in rows for key in row if key not in preferred})
    with path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def print_summary(rows: list[dict[str, Any]]) -> None:
    if not rows:
        print("No rows to summarize.")
        return

    columns = [
        "algorithm",
        "graph_family",
        "graph_size",
        "graph_parameters",
        "heap_type",
        "row_count",
        "mean_decrease_key_per_extract",
        "mean_successful_decrease_key_rate",
        "mean_edge_scan_per_extract",
        "mean_peak_heap_size",
        "mean_comparison_count",
        "mean_swap_count",
        "mean_link_count",
        "mean_cut_count",
        "mean_meld_count",
    ]
    if any("mean_successful_relax_rate" in row for row in rows):
        columns.insert(8, "mean_successful_relax_rate")
    widths = {
        column: max(len(column), *(len(_format(row.get(column))) for row in rows))
        for column in columns
    }

    print(" | ".join(column.ljust(widths[column]) for column in columns))
    print("-+-".join("-" * widths[column] for column in columns))
    for row in rows:
        print(" | ".join(_format(row.get(column)).ljust(widths[column]) for column in columns))


def _ratio(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0


def _derived_metrics_for_algorithm(algorithm: str) -> list[str]:
    if algorithm == "dijkstra":
        return DERIVED_METRICS + DIJKSTRA_DERIVED_METRICS
    return DERIVED_METRICS


def _mean(values: Any) -> float:
    items = list(values)
    return sum(items) / len(items) if items else 0.0


def _number(value: Any) -> float:
    if value in (None, ""):
        return 0.0
    return float(value)


def _format(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


if __name__ == "__main__":
    main()
