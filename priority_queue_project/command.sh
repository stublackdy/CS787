#!/usr/bin/env bash
# Helper commands for the priority queue experiments.
#
# Default environment:
#   MAMBA_ENV=bot

# Number of default seed samples used by experiment modes when no seeds are
# provided on the command line. DEFAULT_SAMPLE_COUNT=5 means seeds 0 1 2 3 4.
DEFAULT_SAMPLE_COUNT=10
DEFAULT_SYN_RESULTS_CSV="results/syn_results.csv"
DEFAULT_SYN_SUMMARY_CSV="results/syn_summary.csv"
SNAP_DATA_DIR="data/snap"
SNAP_MAX_EDGES=50000
SNAP_MAX_VERTICES=
SNAP_USE_LARGEST_COMPONENT=1
CPP_RESULTS_CSV="results/cpp_results.csv"
CPP_SUMMARY_CSV="results/cpp_summary.csv"
CPP_REPEATS=3
CPP_STRESS_LEVEL="full"

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
MAMBA_ENV="${MAMBA_ENV:-bot}"

default_seeds() {
    local seeds=()
    local i
    for ((i = 0; i < DEFAULT_SAMPLE_COUNT; i++)); do
        seeds+=("$i")
    done
    printf '%s\n' "${seeds[@]}"
}

run_python() {
    micromamba run -n "$MAMBA_ENV" python3 "$@"
}

show_help() {
    cat <<'EOF'
Usage:
  bash command.sh syn [output_csv] [summary_csv] [seed ...]
  bash command.sh ca-GrQc [output_csv] [summary_csv] [seed ...]
  bash command.sh roadNet-PA [output_csv] [summary_csv] [seed ...]
  bash command.sh roadNet-CA [output_csv] [summary_csv] [seed ...]
  bash command.sh cpp [output_csv] [summary_csv]
  bash command.sh all

Samples:
  If no seeds are provided, each mode uses DEFAULT_SAMPLE_COUNT near the top of
  this file and generate seeds from 0 to DEFAULT_SAMPLE_COUNT - 1.

SNAP:
  Put SNAP files under data/snap by default, for example ca-GrQc.txt or
  roadNet-PA.txt.gz. Adjust SNAP_DATA_DIR, SNAP_MAX_EDGES, SNAP_MAX_VERTICES,
  and SNAP_USE_LARGEST_COMPONENT near the top of this file.

C++:
  cpp builds cpp/run_cpp_experiments and runs synthetic plus available SNAP
  datasets into one detail CSV, then writes a grouped summary CSV. Adjust
  CPP_REPEATS and CPP_STRESS_LEVEL near the top of this file.

Environment:
  MAMBA_ENV=bot by default. Override it with an existing micromamba env, e.g.
  MAMBA_ENV=jepa bash command.sh syn
EOF
}

cmd="${1:-help}"
shift || true

cd "$PROJECT_ROOT"

case "$cmd" in
    syn)
        output_csv="${1:-$DEFAULT_SYN_RESULTS_CSV}"
        summary_csv="${2:-$DEFAULT_SYN_SUMMARY_CSV}"
        if [[ $# -gt 0 ]]; then
            shift
        fi
        if [[ $# -gt 0 ]]; then
            shift
        fi
        seeds=("$@")
        if [[ ${#seeds[@]} -eq 0 ]]; then
            mapfile -t seeds < <(default_seeds)
        fi
        mkdir -p "$(dirname "$output_csv")" "$(dirname "$summary_csv")"
        run_python -m priority_queue_project.experiments.run_experiments \
            --graph-source synthetic \
            --output "$output_csv" \
            --seeds "${seeds[@]}"
        run_python -m priority_queue_project.experiments.analyze_results \
            "$output_csv" \
            --summary-output "$summary_csv"
        ;;
    ca-GrQc|roadNet-PA|roadNet-CA)
        dataset="$cmd"
        output_csv="${1:-results/${dataset}_results.csv}"
        summary_csv="${2:-results/${dataset}_summary.csv}"
        if [[ $# -gt 0 ]]; then
            shift
        fi
        if [[ $# -gt 0 ]]; then
            shift
        fi
        seeds=("$@")
        if [[ ${#seeds[@]} -eq 0 ]]; then
            mapfile -t seeds < <(default_seeds)
        fi

        snap_args=(
            --graph-source snap
            --snap-dataset "$dataset"
            --snap-data-dir "$SNAP_DATA_DIR"
        )
        if [[ -n "${SNAP_MAX_EDGES:-}" ]]; then
            snap_args+=(--snap-max-edges "$SNAP_MAX_EDGES")
        fi
        if [[ -n "${SNAP_MAX_VERTICES:-}" ]]; then
            snap_args+=(--snap-max-vertices "$SNAP_MAX_VERTICES")
        fi
        if [[ "$SNAP_USE_LARGEST_COMPONENT" == "0" ]]; then
            snap_args+=(--snap-keep-components)
        fi

        mkdir -p "$(dirname "$output_csv")" "$(dirname "$summary_csv")"
        run_python -m priority_queue_project.experiments.run_experiments \
            "${snap_args[@]}" \
            --output "$output_csv" \
            --seeds "${seeds[@]}"
        run_python -m priority_queue_project.experiments.analyze_results \
            "$output_csv" \
            --summary-output "$summary_csv"
        ;;
    cpp)
        output_csv="${1:-$CPP_RESULTS_CSV}"
        summary_csv="${2:-$CPP_SUMMARY_CSV}"
        cpp_args=(
            --mode all
            --output "$output_csv"
            --sample-count "$DEFAULT_SAMPLE_COUNT"
            --repeats "$CPP_REPEATS"
            --stress-level "$CPP_STRESS_LEVEL"
            --snap-data-dir "$SNAP_DATA_DIR"
        )
        if [[ -n "${SNAP_MAX_EDGES:-}" ]]; then
            cpp_args+=(--snap-max-edges "$SNAP_MAX_EDGES")
        fi
        if [[ -n "${SNAP_MAX_VERTICES:-}" ]]; then
            cpp_args+=(--snap-max-vertices "$SNAP_MAX_VERTICES")
        fi
        if [[ "$SNAP_USE_LARGEST_COMPONENT" == "0" ]]; then
            cpp_args+=(--keep-components)
        fi

        mkdir -p "$(dirname "$output_csv")" "$(dirname "$summary_csv")"
        make -C cpp
        ./cpp/run_cpp_experiments "${cpp_args[@]}"
        run_python -m priority_queue_project.experiments.analyze_cpp_results \
            "$output_csv" \
            --summary-output "$summary_csv"
        ;;
    all)
        bash "$SCRIPT_DIR/command.sh" syn
        bash "$SCRIPT_DIR/command.sh" ca-GrQc
        bash "$SCRIPT_DIR/command.sh" roadNet-PA
        bash "$SCRIPT_DIR/command.sh" roadNet-CA
        bash "$SCRIPT_DIR/command.sh" cpp
        ;;
    help|-h|--help)
        show_help
        ;;
    *)
        echo "Unknown command: $cmd" >&2
        show_help >&2
        exit 1
        ;;
esac

