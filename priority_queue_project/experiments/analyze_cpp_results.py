"""Create grouped summaries for C++ benchmark CSV output."""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path
import statistics
from typing import Any


GROUP_COLUMNS = [
    "algorithm",
    "graph_source",
    "graph_family",
    "graph_size",
    "graph_parameters",
    "heap_type",
]

METRIC_COLUMNS = [
    "runtime_ms",
    "mean_runtime_ms",
    "median_runtime_ms",
    "min_runtime_ms",
    "max_runtime_ms",
    "max_rss_kbytes",
    "median_max_rss_kbytes",
    "priority_queue_memory_bytes",
    "edge_scan_count",
    "relax_attempt_count",
    "successful_relax_count",
    "successful_key_update_count",
]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="C++ benchmark detail CSV")
    parser.add_argument(
        "--summary-output",
        type=Path,
        default=Path("results/cpp_summary.csv"),
        help="Grouped C++ summary CSV",
    )
    args = parser.parse_args()

    rows = load_rows(args.input)
    summary = summarize(rows)
    write_csv(args.summary_output, summary)
    print(f"Wrote C++ summary rows to {args.summary_output}")


def load_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as csv_file:
        return list(csv.DictReader(csv_file))


def summarize(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, ...], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        key = tuple(row.get(column, "") for column in GROUP_COLUMNS)
        groups[key].append(row)

    summaries: list[dict[str, Any]] = []
    for key, group_rows in sorted(groups.items()):
        summary: dict[str, Any] = dict(zip(GROUP_COLUMNS, key))
        summary["row_count"] = len(group_rows)
        summary["runtime_measurement"] = _unique_or_mixed(group_rows, "runtime_measurement")
        summary["rss_measurement"] = _unique_or_mixed(group_rows, "rss_measurement")

        for metric in METRIC_COLUMNS:
            values = [_number(row.get(metric)) for row in group_rows if row.get(metric) not in (None, "")]
            if not values:
                continue
            summary[f"mean_{metric}"] = sum(values) / len(values)
            summary[f"median_{metric}"] = statistics.median(values)
            summary[f"min_{metric}"] = min(values)
            summary[f"max_{metric}"] = max(values)

        summaries.append(summary)
    return summaries


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return

    preferred = GROUP_COLUMNS + ["row_count", "runtime_measurement", "rss_measurement"]
    fieldnames = preferred + sorted({key for row in rows for key in row if key not in preferred})
    with path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _unique_or_mixed(rows: list[dict[str, str]], column: str) -> str:
    values = {row.get(column, "") for row in rows}
    return values.pop() if len(values) == 1 else "mixed"


def _number(value: str | None) -> float:
    if value in (None, ""):
        return 0.0
    return float(value)


if __name__ == "__main__":
    main()

