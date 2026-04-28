# Priority Queue Experiments for Dijkstra and Prim

## 1. Overview

This project compares priority queue behavior in Dijkstra's shortest-path algorithm and Prim's minimum-spanning-tree algorithm.

The project has two parts:

- Python prototype: focuses on structural and algorithmic metrics rather than wall-clock performance, such as decrease-key counts, edge scans, links, cuts, melds, and peak heap size.
- C++ benchmark: implements the same three priority queues and two graph algorithms, then measures runtime and memory-related metrics such as `runtime_ms`, `median_runtime_ms`, `max_rss_kbytes`, and `priority_queue_memory_bytes`.

Priority queues implemented:

- Binary heap
- Pairing heap
- Fibonacci heap

Algorithms implemented:

- Dijkstra's algorithm
- Prim's algorithm

Supported graph sources:

- Synthetic graphs
- SNAP `ca-GrQc`
- SNAP `roadNet-PA`
- SNAP `roadNet-CA`
- C++-only decrease-key stress graphs

## 2. Data Download and Placement

SNAP datasets are expected under:

```bash
/home/cwang922/Project/CS787/data/snap/
```

Both `.txt` and `.txt.gz` files are supported. Using `.txt.gz` directly is recommended; decompression is not required.

Download commands:

```bash
cd /home/cwang922/Project/CS787
mkdir -p data/snap

wget -P data/snap https://snap.stanford.edu/data/ca-GrQc.txt.gz
wget -P data/snap https://snap.stanford.edu/data/roadNet-PA.txt.gz
wget -P data/snap https://snap.stanford.edu/data/roadNet-CA.txt.gz
```

Expected paths:

```bash
data/snap/ca-GrQc.txt.gz
data/snap/roadNet-PA.txt.gz
data/snap/roadNet-CA.txt.gz
```

Relevant configuration in `priority_queue_project/command.sh`:

```bash
SNAP_DATA_DIR="data/snap"
SNAP_MAX_EDGES=50000
SNAP_MAX_VERTICES=
SNAP_USE_LARGEST_COMPONENT=1
```

Meaning:

- `SNAP_MAX_EDGES=50000`: read at most the first 50,000 raw SNAP edges.
- `SNAP_MAX_VERTICES=`: do not impose a vertex limit.
- `SNAP_USE_LARGEST_COMPONENT=1`: run experiments on the largest connected component after loading.

## 3. Project Structure

```text
CS787/
├── README.md
├── cpp/
│   ├── Makefile
│   └── run_cpp_experiments.cpp
├── data/
│   └── snap/
│       ├── ca-GrQc.txt.gz
│       ├── roadNet-PA.txt.gz
│       └── roadNet-CA.txt.gz
├── priority_queue_project/
│   ├── __init__.py
│   ├── command.sh
│   ├── graph.py
│   ├── graph_generators.py
│   ├── pq_stats.py
│   ├── snap_loader.py
│   ├── algorithms/
│   │   ├── __init__.py
│   │   ├── dijkstra.py
│   │   └── prim.py
│   ├── heaps/
│   │   ├── __init__.py
│   │   ├── binary_heap.py
│   │   ├── pairing_heap.py
│   │   └── fibonacci_heap.py
│   ├── experiments/
│   │   ├── __init__.py
│   │   ├── run_experiments.py
│   │   ├── analyze_results.py
│   │   └── analyze_cpp_results.py
│   └── tests/
│       ├── __init__.py
│       └── test_correctness.py
└── results/
    ├── syn_results.csv
    ├── syn_summary.csv
    ├── ca-GrQc_results.csv
    ├── ca-GrQc_summary.csv
    ├── roadNet-PA_results.csv
    ├── roadNet-PA_summary.csv
    ├── roadNet-CA_results.csv
    ├── roadNet-CA_summary.csv
    ├── cpp_results.csv
    └── cpp_summary.csv
```

Directory summary:

- `priority_queue_project/`: Python package for the prototype.
- `priority_queue_project/heaps/`: Python priority queue implementations.
- `priority_queue_project/algorithms/`: Python Dijkstra and Prim implementations.
- `priority_queue_project/experiments/`: Python experiment runners and analysis scripts.
- `priority_queue_project/tests/`: Python correctness tests.
- `cpp/`: C++ benchmark implementation and build file.
- `data/snap/`: SNAP dataset files.
- `results/`: CSV output files.

## 4. `command.sh` Modes

Run all commands from the script directory:

```bash
cd /home/cwang922/Project/CS787/priority_queue_project
```

The default Python environment is the existing micromamba environment `bot`:

```bash
MAMBA_ENV=bot
```

### `syn`

Runs Python experiments on synthetic graphs and writes both detail and summary CSV files.

```bash
bash command.sh syn
```

Default outputs:

```text
results/syn_results.csv
results/syn_summary.csv
```

Custom output paths and seeds:

```bash
bash command.sh syn results/my_syn_results.csv results/my_syn_summary.csv 0 1 2
```

### `ca-GrQc`

Runs Python experiments on the SNAP `ca-GrQc` dataset.

```bash
bash command.sh ca-GrQc
```

Default outputs:

```text
results/ca-GrQc_results.csv
results/ca-GrQc_summary.csv
```

### `roadNet-PA`

Runs Python experiments on the SNAP `roadNet-PA` dataset.

```bash
bash command.sh roadNet-PA
```

Default outputs:

```text
results/roadNet-PA_results.csv
results/roadNet-PA_summary.csv
```

### `roadNet-CA`

Runs Python experiments on the SNAP `roadNet-CA` dataset.

```bash
bash command.sh roadNet-CA
```

Default outputs:

```text
results/roadNet-CA_results.csv
results/roadNet-CA_summary.csv
```

### `cpp`

Builds and runs the C++ benchmark. It covers synthetic graphs and available SNAP datasets, then writes one detail CSV and one grouped summary CSV.

```bash
bash command.sh cpp
```

Default outputs:

```text
results/cpp_results.csv
results/cpp_summary.csv
```

C++ configuration:

```bash
CPP_RESULTS_CSV="results/cpp_results.csv"
CPP_SUMMARY_CSV="results/cpp_summary.csv"
CPP_REPEATS=3
CPP_STRESS_LEVEL="full"
```

### `all`

Runs every mode in sequence.

```bash
bash command.sh all
```

Execution order:

```text
syn
ca-GrQc
roadNet-PA
roadNet-CA
cpp
```

## 5. Datasets, Data Structures, and Algorithms

### Synthetic Datasets

Synthetic graph families:

- `sparse_er_nm`: sparse Erdos-Renyi graph specified by `n` and `m`.
- `medium_er_np`: medium-density Erdos-Renyi graph specified by `n` and `p`.
- `dense_er_np`: higher-density Erdos-Renyi graph.
- `superdense_er_np`: even denser Erdos-Renyi graph.
- `grid_2d`: two-dimensional grid graph.

Python synthetic experiments do not include stress graphs. C++ synthetic experiments additionally include:

- `dijkstra_decrease_key_stress`
- `prim_decrease_key_stress`

The stress graphs are used only for C++ extreme-case performance testing.

### SNAP Datasets

`ca-GrQc`:

- Arxiv General Relativity collaboration network.
- Undirected graph.
- Official size: about 5,242 nodes and 14,496 edges.

`roadNet-PA`:

- Pennsylvania road network.
- Undirected graph.
- Official size: about 1,088,092 nodes and 1,541,898 edges.

`roadNet-CA`:

- California road network.
- Undirected graph.
- Official size: about 1,965,206 nodes and 2,766,607 edges.

By default, roadNet experiments do not load the full graph. They are limited by `SNAP_MAX_EDGES=50000`.

### Graph Representation

Python `Graph` stores:

- number of vertices
- directed flag
- weighted edge list
- adjacency list

It supports:

- self-loop removal
- duplicate edge merging
- deterministic positive weight assignment when weights are missing
- graph statistics

C++ `Graph` stores:

- `n`
- `directed`
- `edges`
- `adj`

It also normalizes edges, removes duplicates, and builds adjacency lists.

### Priority Queues

Binary heap:

- array-based heap
- vertex-to-position handle array
- true decrease-key

Pairing heap:

- node pool
- parent/child/sibling/prev pointers
- two-pass pairing in extract-min
- cut and meld in decrease-key

Fibonacci heap:

- node pool
- circular root and child lists
- reusable degree table in consolidation
- cut and cascading cut
- child-list splicing during extract-min

### Algorithms

Dijkstra:

- Requires positive edge weights.
- Uses only the shared priority queue interface.
- Reports distance checksum and relax/edge-scan metrics.

Prim:

- Runs on undirected graphs.
- If the graph is disconnected, computes the MST for the connected component containing the start vertex.
- SNAP experiments default to the largest connected component, so Prim usually covers the entire experimental graph.

## 6. Evaluation Metrics

### Python Graph Metrics

- `graph_num_vertices`: number of vertices.
- `graph_num_edges`: number of normalized edges.
- `graph_average_degree`: average degree.
- `graph_maximum_degree`: maximum degree.
- `graph_directed`: whether the graph is directed.

### Python Algorithm Metrics

Dijkstra:

- `edge_scan_count`: number of adjacency edges scanned.
- `relax_attempt_count`: number of relax attempts on non-finalized neighbors.
- `successful_relax_count`: number of relaxations that improved a distance.
- `reachable_vertex_count`: number of finalized reachable vertices.
- `distance_checksum`: sum of all finite shortest-path distances.

Prim:

- `edge_scan_count`: number of adjacency edges scanned.
- `successful_key_update_count`: number of successful Prim key updates.
- `visited_vertex_count`: number of vertices added to the MST/component.
- `mst_weight`: total MST weight for the start component.

### Python Priority Queue Metrics

- `insert_count`: number of insert operations.
- `extract_min_count`: number of extract-min operations.
- `decrease_key_count`: number of decrease-key calls.
- `successful_decrease_key_count`: number of decrease-key calls that actually lowered a key.
- `comparison_count`: number of key comparisons.
- `swap_count`: number of swaps in binary heap.
- `link_count`: number of links in pairing/Fibonacci heaps.
- `cut_count`: number of cuts in pairing/Fibonacci heaps.
- `meld_count`: number of melds in pairing heap.
- `node_allocation_count`: number of heap node allocations.
- `pointer_traversal_count`: number of pointer traversals.
- `peak_size`: maximum priority queue size.

### Python Derived Metrics

`analyze_results.py` produces grouped summaries with derived metrics such as:

- `decrease_key_per_extract = decrease_key_count / extract_min_count`
- `successful_decrease_key_rate = successful_decrease_key_count / decrease_key_count`
- `successful_relax_rate = successful_relax_count / relax_attempt_count`
- `edge_scan_per_extract = edge_scan_count / extract_min_count`
- `peak_heap_size`
- `comparison_count`
- `swap_count`
- `link_count`
- `cut_count`
- `meld_count`

Prim has no relax operation, so `successful_relax_rate` is not summarized for Prim.

### C++ Runtime Metrics

C++ detail output is written to `cpp_results.csv`.

- `runtime_ms`: currently equal to `median_runtime_ms`.
- `mean_runtime_ms`: mean runtime over repeats.
- `median_runtime_ms`: median runtime over repeats.
- `min_runtime_ms`: minimum runtime over repeats.
- `max_runtime_ms`: maximum runtime over repeats.
- `repeats`: number of repeated runs per benchmark.
- `runtime_measurement`: runtime measurement method, currently `in_process_steady_clock`.

Runtime is measured in the parent process around the algorithm call itself, so small graphs are not dominated by fork/wait overhead.

### C++ Memory Metrics

- `rss_measurement`: RSS measurement method, currently `child_process_wait4`.
- `max_rss_kbytes`: maximum child-process RSS over repeats.
- `median_max_rss_kbytes`: median child-process RSS over repeats.
- `priority_queue_memory_bytes`: estimated memory used by the priority queue itself.

`max_rss_kbytes` includes process baseline memory, graph storage, algorithm arrays, and heap memory. It should not be used alone to explain structural memory differences between priority queues.

For priority queue memory comparison, prefer:

```text
priority_queue_memory_bytes
```

Estimation formulas:

Binary heap:

```text
heap.capacity() * sizeof(HeapNode)
+ pos.capacity() * sizeof(int)
```

Pairing heap:

```text
nodes.capacity() * sizeof(PairingNode)
+ handles.capacity() * sizeof(PairingNode*)
```

Fibonacci heap:

```text
nodes.capacity() * sizeof(FibNode)
+ handles.capacity() * sizeof(FibNode*)
+ degree_table.capacity() * sizeof(FibNode*)
```

### C++ Summary Metrics

`analyze_cpp_results.py` produces `cpp_summary.csv`, grouped by:

```text
algorithm
graph_source
graph_family
graph_size
graph_parameters
heap_type
```

For runtime, RSS, heap memory, edge scans, relax attempts, and key-update metrics, it computes:

- mean
- median
- min
- max

