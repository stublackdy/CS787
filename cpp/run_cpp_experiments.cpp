#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <functional>
#include <iostream>
#include <limits>
#include <memory>
#include <numeric>
#include <queue>
#include <random>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <sys/resource.h>
#include <sys/wait.h>
#include <unistd.h>
#include <unordered_map>
#include <unordered_set>
#include <utility>
#include <vector>

using Clock = std::chrono::steady_clock;

struct Edge {
    int u;
    int v;
    int w;
};

struct Graph {
    int n = 0;
    bool directed = false;
    std::vector<Edge> edges;
    std::vector<std::vector<std::pair<int, int>>> adj;

    Graph() = default;

    Graph(int vertices, std::vector<Edge> input_edges, bool is_directed)
        : n(vertices), directed(is_directed), edges(std::move(input_edges)) {
        normalize_edges();
        build_adjacency();
    }

    void normalize_edges() {
        std::unordered_map<long long, int> best;
        best.reserve(edges.size() * 2 + 1);
        for (const auto& e : edges) {
            if (e.u == e.v) {
                continue;
            }
            if (e.u < 0 || e.u >= n || e.v < 0 || e.v >= n) {
                throw std::runtime_error("edge endpoint outside graph range");
            }
            int a = e.u;
            int b = e.v;
            if (!directed && a > b) {
                std::swap(a, b);
            }
            long long key = (static_cast<long long>(a) << 32) ^ static_cast<unsigned int>(b);
            auto it = best.find(key);
            if (it == best.end() || e.w < it->second) {
                best[key] = e.w;
            }
        }

        std::vector<Edge> normalized;
        normalized.reserve(best.size());
        for (const auto& [key, weight] : best) {
            int u = static_cast<int>(key >> 32);
            int v = static_cast<int>(key & 0xffffffffu);
            normalized.push_back({u, v, weight});
        }
        std::sort(normalized.begin(), normalized.end(), [](const Edge& a, const Edge& b) {
            if (a.u != b.u) return a.u < b.u;
            if (a.v != b.v) return a.v < b.v;
            return a.w < b.w;
        });
        edges = std::move(normalized);
    }

    void build_adjacency() {
        adj.assign(n, {});
        for (const auto& e : edges) {
            adj[e.u].push_back({e.v, e.w});
            if (!directed) {
                adj[e.v].push_back({e.u, e.w});
            }
        }
        for (auto& neighbors : adj) {
            std::sort(neighbors.begin(), neighbors.end());
        }
    }

    double average_degree() const {
        if (n == 0) return 0.0;
        long long total = 0;
        for (const auto& neighbors : adj) {
            total += static_cast<long long>(neighbors.size());
        }
        return static_cast<double>(total) / static_cast<double>(n);
    }

    int max_degree() const {
        int best = 0;
        for (const auto& neighbors : adj) {
            best = std::max(best, static_cast<int>(neighbors.size()));
        }
        return best;
    }
};

struct PQStats {
    long long insert_count = 0;
    long long extract_min_count = 0;
    long long decrease_key_count = 0;
    long long successful_decrease_key_count = 0;
    long long comparison_count = 0;
    long long swap_count = 0;
    long long link_count = 0;
    long long cut_count = 0;
    long long meld_count = 0;
    long long node_allocation_count = 0;
    long long pointer_traversal_count = 0;
    long long peak_size = 0;

    void record_size(long long size) {
        peak_size = std::max(peak_size, size);
    }
};

class IPriorityQueue {
public:
    virtual ~IPriorityQueue() = default;
    virtual void insert(int vertex, double key) = 0;
    virtual std::pair<int, double> extract_min() = 0;
    virtual void decrease_key(int vertex, double key) = 0;
    virtual bool empty() const = 0;
    virtual bool contains(int vertex) const = 0;
    virtual const PQStats& stats() const = 0;
    virtual size_t memory_bytes() const = 0;
};

class BinaryHeap : public IPriorityQueue {
    using HeapNode = std::pair<int, double>;
    std::vector<HeapNode> heap_;
    std::vector<int> pos_;
    PQStats stats_;

    bool less_at(int i, int j) {
        stats_.comparison_count++;
        const auto& a = heap_[i];
        const auto& b = heap_[j];
        return std::make_pair(a.second, a.first) < std::make_pair(b.second, b.first);
    }

    void swap_at(int i, int j) {
        stats_.swap_count++;
        std::swap(heap_[i], heap_[j]);
        pos_[heap_[i].first] = i;
        pos_[heap_[j].first] = j;
    }

    void sift_up(int idx) {
        while (idx > 0) {
            int parent = (idx - 1) / 2;
            if (!less_at(idx, parent)) break;
            swap_at(idx, parent);
            idx = parent;
        }
    }

    void sift_down(int idx) {
        int size = static_cast<int>(heap_.size());
        while (true) {
            int left = idx * 2 + 1;
            int right = left + 1;
            int smallest = idx;
            if (left < size && less_at(left, smallest)) smallest = left;
            if (right < size && less_at(right, smallest)) smallest = right;
            if (smallest == idx) break;
            swap_at(idx, smallest);
            idx = smallest;
        }
    }

public:
    explicit BinaryHeap(int n) : pos_(n, -1) {}

    void insert(int vertex, double key) override {
        stats_.insert_count++;
        heap_.push_back({vertex, key});
        pos_[vertex] = static_cast<int>(heap_.size()) - 1;
        stats_.record_size(heap_.size());
        sift_up(pos_[vertex]);
    }

    std::pair<int, double> extract_min() override {
        stats_.extract_min_count++;
        auto result = heap_.front();
        auto last = heap_.back();
        heap_.pop_back();
        pos_[result.first] = -1;
        if (!heap_.empty()) {
            heap_[0] = last;
            pos_[last.first] = 0;
            sift_down(0);
        }
        return result;
    }

    void decrease_key(int vertex, double new_key) override {
        stats_.decrease_key_count++;
        int idx = pos_[vertex];
        if (idx < 0) return;
        stats_.comparison_count++;
        if (new_key >= heap_[idx].second) return;
        stats_.successful_decrease_key_count++;
        heap_[idx].second = new_key;
        sift_up(idx);
    }

    bool empty() const override { return heap_.empty(); }
    bool contains(int vertex) const override { return vertex >= 0 && vertex < static_cast<int>(pos_.size()) && pos_[vertex] >= 0; }
    const PQStats& stats() const override { return stats_; }
    size_t memory_bytes() const override {
        return heap_.capacity() * sizeof(HeapNode) + pos_.capacity() * sizeof(int);
    }
};

class PairingHeap : public IPriorityQueue {
    struct Node {
        int vertex;
        double key;
        Node* parent = nullptr;
        Node* child = nullptr;
        Node* sibling = nullptr;
        Node* prev = nullptr;
    };

    Node* root_ = nullptr;
    std::vector<Node*> handles_;
    std::vector<Node> nodes_;
    int size_ = 0;
    PQStats stats_;

    static bool node_less(Node* a, Node* b) {
        return std::make_pair(a->key, a->vertex) < std::make_pair(b->key, b->vertex);
    }

    Node* meld(Node* a, Node* b) {
        if (!a) return b;
        if (!b) return a;
        stats_.meld_count++;
        stats_.comparison_count++;
        if (node_less(b, a)) std::swap(a, b);
        stats_.link_count++;
        b->parent = a;
        b->prev = nullptr;
        b->sibling = a->child;
        if (a->child) {
            a->child->prev = b;
        }
        a->child = b;
        return a;
    }

    Node* two_pass(Node* child) {
        std::vector<Node*> paired;
        Node* cur = child;
        while (cur) {
            stats_.pointer_traversal_count++;
            Node* first = cur;
            Node* second = cur->sibling;
            Node* next = second ? second->sibling : nullptr;
            first->parent = nullptr;
            first->prev = nullptr;
            first->sibling = nullptr;
            if (second) {
                stats_.pointer_traversal_count++;
                second->parent = nullptr;
                second->prev = nullptr;
                second->sibling = nullptr;
                paired.push_back(meld(first, second));
            } else {
                paired.push_back(first);
            }
            cur = next;
        }
        Node* root = nullptr;
        for (auto it = paired.rbegin(); it != paired.rend(); ++it) {
            root = meld(root, *it);
        }
        return root;
    }

    void cut(Node* node) {
        Node* parent = node->parent;
        if (!parent) return;
        stats_.cut_count++;
        if (parent->child == node) {
            parent->child = node->sibling;
            if (node->sibling) {
                node->sibling->prev = nullptr;
            }
        } else {
            if (node->prev) {
                node->prev->sibling = node->sibling;
            }
            if (node->sibling) {
                node->sibling->prev = node->prev;
            }
        }
        node->parent = nullptr;
        node->prev = nullptr;
        node->sibling = nullptr;
    }

public:
    explicit PairingHeap(int n) : handles_(n, nullptr) {
        nodes_.reserve(n);
    }

    void insert(int vertex, double key) override {
        stats_.insert_count++;
        stats_.node_allocation_count++;
        nodes_.push_back(Node{vertex, key});
        Node* node = &nodes_.back();
        handles_[vertex] = node;
        root_ = meld(root_, node);
        size_++;
        stats_.record_size(size_);
    }

    std::pair<int, double> extract_min() override {
        stats_.extract_min_count++;
        Node* old = root_;
        handles_[old->vertex] = nullptr;
        root_ = two_pass(old->child);
        if (root_) root_->parent = nullptr;
        size_--;
        return {old->vertex, old->key};
    }

    void decrease_key(int vertex, double new_key) override {
        stats_.decrease_key_count++;
        Node* node = handles_[vertex];
        if (!node) return;
        stats_.comparison_count++;
        if (new_key >= node->key) return;
        stats_.successful_decrease_key_count++;
        node->key = new_key;
        if (node != root_) {
            cut(node);
            root_ = meld(root_, node);
        }
    }

    bool empty() const override { return root_ == nullptr; }
    bool contains(int vertex) const override { return vertex >= 0 && vertex < static_cast<int>(handles_.size()) && handles_[vertex] != nullptr; }
    const PQStats& stats() const override { return stats_; }
    size_t memory_bytes() const override {
        return nodes_.capacity() * sizeof(Node) + handles_.capacity() * sizeof(Node*);
    }
};

class FibonacciHeap : public IPriorityQueue {
    struct Node {
        int vertex;
        double key;
        int degree = 0;
        bool mark = false;
        Node* parent = nullptr;
        Node* child = nullptr;
        Node* left = nullptr;
        Node* right = nullptr;
    };

    Node* min_ = nullptr;
    std::vector<Node*> handles_;
    std::vector<Node> nodes_;
    std::vector<Node*> roots_buffer_;
    std::vector<Node*> degree_table_;
    std::vector<int> touched_degrees_;
    int size_ = 0;
    PQStats stats_;

    static bool node_less(Node* a, Node* b) {
        if (a->key != b->key) return a->key < b->key;
        return a->vertex < b->vertex;
    }

    void insert_after(Node* existing, Node* node) {
        stats_.pointer_traversal_count++;
        node->left = existing;
        node->right = existing->right;
        existing->right->left = node;
        existing->right = node;
    }

    void remove_from_list(Node* node) {
        stats_.pointer_traversal_count++;
        node->left->right = node->right;
        node->right->left = node->left;
        node->left = node;
        node->right = node;
    }

    void splice_into_root_list(Node* list) {
        if (!list) return;
        if (!min_) {
            min_ = list;
            return;
        }

        stats_.pointer_traversal_count++;
        Node* root_right = min_->right;
        Node* list_left = list->left;
        min_->right = list;
        list->left = min_;
        list_left->right = root_right;
        root_right->left = list_left;
    }

    void ensure_degree_slot(int degree) {
        if (degree >= static_cast<int>(degree_table_.size())) {
            degree_table_.resize(degree + 1, nullptr);
        }
    }

    void add_root(Node* node) {
        node->parent = nullptr;
        if (!min_) {
            node->left = node;
            node->right = node;
            min_ = node;
            return;
        }
        insert_after(min_, node);
        stats_.comparison_count++;
        if (node_less(node, min_)) min_ = node;
    }

    void heap_link(Node* child, Node* parent) {
        stats_.link_count++;
        remove_from_list(child);
        child->parent = parent;
        child->mark = false;
        child->left = child;
        child->right = child;
        if (!parent->child) {
            parent->child = child;
        } else {
            stats_.pointer_traversal_count++;
            Node* first = parent->child;
            child->left = first;
            child->right = first->right;
            first->right->left = child;
            first->right = child;
        }
        parent->degree++;
    }

    void consolidate() {
        roots_buffer_.clear();
        if (min_) {
            Node* cur = min_;
            do {
                roots_buffer_.push_back(cur);
                stats_.pointer_traversal_count++;
                cur = cur->right;
            } while (cur != min_);
        }

        for (Node* root : roots_buffer_) {
            if (root->parent) continue;
            Node* x = root;
            int d = x->degree;
            while (true) {
                ensure_degree_slot(d);
                Node* y = degree_table_[d];
                if (!y) {
                    degree_table_[d] = x;
                    touched_degrees_.push_back(d);
                    break;
                }
                stats_.comparison_count++;
                if (node_less(y, x)) std::swap(x, y);
                heap_link(y, x);
                degree_table_[d] = nullptr;
                d = x->degree;
            }
        }

        Node* head = nullptr;
        Node* best = nullptr;
        Node* last = nullptr;
        for (int degree : touched_degrees_) {
            Node* node = degree_table_[degree];
            if (node) {
                node->parent = nullptr;
                if (!head) {
                    node->left = node;
                    node->right = node;
                    head = node;
                    best = node;
                    last = node;
                } else {
                    stats_.pointer_traversal_count++;
                    node->left = last;
                    node->right = head;
                    last->right = node;
                    head->left = node;
                    last = node;
                    stats_.comparison_count++;
                    if (node_less(node, best)) best = node;
                }
            }
            degree_table_[degree] = nullptr;
        }
        min_ = best;
        touched_degrees_.clear();
    }

    void cut(Node* node, Node* parent) {
        stats_.cut_count++;
        if (node->right == node) {
            parent->child = nullptr;
        } else {
            if (parent->child == node) parent->child = node->right;
            remove_from_list(node);
        }
        parent->degree--;
        node->parent = nullptr;
        node->mark = false;
        node->left = node;
        node->right = node;
        add_root(node);
    }

    void cascading_cut(Node* node) {
        while (Node* parent = node->parent) {
            if (!node->mark) {
                node->mark = true;
                return;
            }
            cut(node, parent);
            node = parent;
        }
    }

public:
    explicit FibonacciHeap(int n) : handles_(n, nullptr) {
        nodes_.reserve(n);
        roots_buffer_.reserve(n);
        degree_table_.reserve(64);
        touched_degrees_.reserve(64);
    }

    void insert(int vertex, double key) override {
        stats_.insert_count++;
        stats_.node_allocation_count++;
        nodes_.emplace_back();
        Node* node = &nodes_.back();
        node->vertex = vertex;
        node->key = key;
        node->left = node;
        node->right = node;
        handles_[vertex] = node;
        add_root(node);
        size_++;
        stats_.record_size(size_);
    }

    std::pair<int, double> extract_min() override {
        stats_.extract_min_count++;
        Node* z = min_;
        Node* child_list = z->child;
        if (child_list) {
            Node* child = child_list;
            do {
                child->parent = nullptr;
                child->mark = false;
                stats_.pointer_traversal_count++;
                child = child->right;
            } while (child != child_list);
        }

        if (z->right == z) {
            min_ = child_list;
        } else {
            Node* next = z->right;
            remove_from_list(z);
            min_ = next;
            splice_into_root_list(child_list);
        }

        z->child = nullptr;
        z->left = z;
        z->right = z;
        handles_[z->vertex] = nullptr;
        size_--;
        if (min_) consolidate();
        return {z->vertex, z->key};
    }

    void decrease_key(int vertex, double new_key) override {
        stats_.decrease_key_count++;
        Node* node = handles_[vertex];
        if (!node) return;
        stats_.comparison_count++;
        if (new_key >= node->key) return;
        stats_.successful_decrease_key_count++;
        node->key = new_key;
        Node* parent = node->parent;
        if (parent) {
            stats_.comparison_count++;
            if (node_less(node, parent)) {
                cut(node, parent);
                cascading_cut(parent);
            }
        } else if (node != min_) {
            stats_.comparison_count++;
            if (node_less(node, min_)) min_ = node;
        }
    }

    bool empty() const override { return size_ == 0; }
    bool contains(int vertex) const override { return vertex >= 0 && vertex < static_cast<int>(handles_.size()) && handles_[vertex] != nullptr; }
    const PQStats& stats() const override { return stats_; }
    size_t memory_bytes() const override {
        return nodes_.capacity() * sizeof(Node)
            + handles_.capacity() * sizeof(Node*)
            + degree_table_.capacity() * sizeof(Node*);
    }
};

struct AlgoStats {
    long long edge_scan_count = 0;
    long long relax_attempt_count = 0;
    long long successful_relax_count = 0;
    long long reachable_vertex_count = 0;
    double distance_checksum = 0.0;
    long long successful_key_update_count = 0;
    long long visited_vertex_count = 0;
    double mst_weight = 0.0;
    size_t priority_queue_memory_bytes = 0;
};

std::unique_ptr<IPriorityQueue> make_heap(const std::string& type, int n) {
    if (type == "binary") return std::make_unique<BinaryHeap>(n);
    if (type == "pairing") return std::make_unique<PairingHeap>(n);
    if (type == "fibonacci") return std::make_unique<FibonacciHeap>(n);
    throw std::runtime_error("unknown heap type: " + type);
}

std::pair<double, AlgoStats> dijkstra(const Graph& g, int source, const std::string& heap_type) {
    const double INF = std::numeric_limits<double>::infinity();
    std::vector<double> dist(g.n, INF);
    std::vector<char> finalized(g.n, 0);
    AlgoStats stats;
    auto pq = make_heap(heap_type, g.n);
    dist[source] = 0.0;
    pq->insert(source, 0.0);

    while (!pq->empty()) {
        auto [v, d] = pq->extract_min();
        if (finalized[v]) continue;
        finalized[v] = 1;
        stats.reachable_vertex_count++;
        for (const auto& [to, weight] : g.adj[v]) {
            stats.edge_scan_count++;
            if (finalized[to]) continue;
            stats.relax_attempt_count++;
            double cand = d + weight;
            if (cand < dist[to]) {
                dist[to] = cand;
                stats.successful_relax_count++;
                if (pq->contains(to)) {
                    pq->decrease_key(to, cand);
                } else {
                    pq->insert(to, cand);
                }
            }
        }
    }

    for (double d : dist) {
        if (std::isfinite(d)) stats.distance_checksum += d;
    }
    stats.priority_queue_memory_bytes = pq->memory_bytes();
    return {stats.distance_checksum, stats};
}

std::pair<double, AlgoStats> prim(const Graph& g, int start, const std::string& heap_type) {
    const double INF = std::numeric_limits<double>::infinity();
    std::vector<double> best(g.n, INF);
    std::vector<char> visited(g.n, 0);
    AlgoStats stats;
    auto pq = make_heap(heap_type, g.n);
    best[start] = 0.0;
    pq->insert(start, 0.0);

    while (!pq->empty()) {
        auto [v, key] = pq->extract_min();
        if (visited[v]) continue;
        visited[v] = 1;
        stats.visited_vertex_count++;
        stats.mst_weight += key;
        for (const auto& [to, weight] : g.adj[v]) {
            stats.edge_scan_count++;
            if (!visited[to] && weight < best[to]) {
                best[to] = weight;
                stats.successful_key_update_count++;
                if (pq->contains(to)) {
                    pq->decrease_key(to, weight);
                } else {
                    pq->insert(to, weight);
                }
            }
        }
    }
    stats.priority_queue_memory_bytes = pq->memory_bytes();
    return {stats.mst_weight, stats};
}

std::vector<std::pair<int, int>> all_edges(int n) {
    std::vector<std::pair<int, int>> edges;
    for (int u = 0; u < n; ++u) {
        for (int v = u + 1; v < n; ++v) {
            edges.push_back({u, v});
        }
    }
    return edges;
}

std::vector<std::pair<int, int>> random_tree_edges(int n, std::mt19937& rng) {
    std::vector<std::pair<int, int>> edges;
    for (int v = 1; v < n; ++v) {
        std::uniform_int_distribution<int> dist(0, v - 1);
        edges.push_back({dist(rng), v});
    }
    return edges;
}

Graph weighted_graph_from_pairs(int n, const std::vector<std::pair<int, int>>& pairs, int seed) {
    std::mt19937 rng(seed);
    std::uniform_int_distribution<int> weight_dist(1, 100);
    std::vector<Edge> edges;
    edges.reserve(pairs.size());
    for (auto [u, v] : pairs) {
        edges.push_back({u, v, weight_dist(rng)});
    }
    return Graph(n, std::move(edges), false);
}

Graph sparse_er(int n, int m, int seed) {
    std::mt19937 rng(seed);
    auto chosen = random_tree_edges(n, rng);
    std::set<std::pair<int, int>> chosen_set(chosen.begin(), chosen.end());
    auto candidates = all_edges(n);
    std::vector<std::pair<int, int>> remaining;
    for (auto e : candidates) {
        if (!chosen_set.count(e)) remaining.push_back(e);
    }
    std::shuffle(remaining.begin(), remaining.end(), rng);
    for (int i = 0; static_cast<int>(chosen.size()) < m && i < static_cast<int>(remaining.size()); ++i) {
        chosen.push_back(remaining[i]);
    }
    return weighted_graph_from_pairs(n, chosen, seed);
}

Graph dense_er(int n, double p, int seed) {
    std::mt19937 rng(seed);
    auto chosen = random_tree_edges(n, rng);
    std::set<std::pair<int, int>> chosen_set(chosen.begin(), chosen.end());
    std::uniform_real_distribution<double> prob(0.0, 1.0);
    for (auto e : all_edges(n)) {
        if (!chosen_set.count(e) && prob(rng) < p) {
            chosen.push_back(e);
        }
    }
    return weighted_graph_from_pairs(n, chosen, seed);
}

Graph grid_graph(int rows, int cols, int seed) {
    std::vector<std::pair<int, int>> pairs;
    auto vertex = [cols](int r, int c) { return r * cols + c; };
    for (int r = 0; r < rows; ++r) {
        for (int c = 0; c < cols; ++c) {
            if (c + 1 < cols) pairs.push_back({vertex(r, c), vertex(r, c + 1)});
            if (r + 1 < rows) pairs.push_back({vertex(r, c), vertex(r + 1, c)});
        }
    }
    return weighted_graph_from_pairs(rows * cols, pairs, seed);
}

Graph dijkstra_decrease_key_stress_graph(int k, int r) {
    int n = 1 + k + r;
    int c = r + 1;
    int b = k * c + r + k + 1;
    std::vector<Edge> edges;
    edges.reserve(static_cast<size_t>(k) + static_cast<size_t>(r) + static_cast<size_t>(k) * static_cast<size_t>(r));

    auto rank = [r](int i, int j) {
        return (i % 2 == 1) ? j : (r + 1 - j);
    };

    for (int i = 1; i <= k; ++i) {
        int a = i;
        edges.push_back({0, a, i});
    }
    for (int j = 1; j <= r; ++j) {
        int t = k + j;
        edges.push_back({0, t, b + j});
    }
    for (int i = 1; i <= k; ++i) {
        int a = i;
        for (int j = 1; j <= r; ++j) {
            int t = k + j;
            int weight = (b - i * c + rank(i, j)) - i;
            edges.push_back({a, t, weight});
        }
    }
    return Graph(n, std::move(edges), true);
}

Graph prim_decrease_key_stress_graph(int k, int r) {
    int n = 1 + k + r;
    int c = r + 1;
    int b = k * c + r + k + 1;
    std::vector<Edge> edges;
    edges.reserve(static_cast<size_t>(k) + static_cast<size_t>(r) + static_cast<size_t>(k) * static_cast<size_t>(r));

    auto rank = [r](int i, int j) {
        return (i % 2 == 1) ? j : (r + 1 - j);
    };

    for (int i = 1; i <= k; ++i) {
        int a = i;
        edges.push_back({0, a, i});
    }
    for (int j = 1; j <= r; ++j) {
        int t = k + j;
        edges.push_back({0, t, b + j});
    }
    for (int i = 1; i <= k; ++i) {
        int a = i;
        for (int j = 1; j <= r; ++j) {
            int t = k + j;
            int weight = b - i * c + rank(i, j);
            edges.push_back({a, t, weight});
        }
    }
    return Graph(n, std::move(edges), false);
}

Graph largest_component(const Graph& g) {
    std::vector<char> seen(g.n, 0);
    std::vector<int> best;
    for (int start = 0; start < g.n; ++start) {
        if (seen[start]) continue;
        std::vector<int> comp;
        std::vector<int> stack = {start};
        seen[start] = 1;
        while (!stack.empty()) {
            int v = stack.back();
            stack.pop_back();
            comp.push_back(v);
            for (const auto& [to, _] : g.adj[v]) {
                if (!seen[to]) {
                    seen[to] = 1;
                    stack.push_back(to);
                }
            }
        }
        if (comp.size() > best.size()) best = std::move(comp);
    }
    if (static_cast<int>(best.size()) == g.n) return g;

    std::vector<int> remap(g.n, -1);
    std::sort(best.begin(), best.end());
    for (int i = 0; i < static_cast<int>(best.size()); ++i) remap[best[i]] = i;
    std::vector<Edge> edges;
    for (const auto& e : g.edges) {
        if (remap[e.u] >= 0 && remap[e.v] >= 0) {
            edges.push_back({remap[e.u], remap[e.v], e.w});
        }
    }
    return Graph(static_cast<int>(best.size()), std::move(edges), false);
}

std::string shell_quote(const std::string& path) {
    std::string out = "'";
    for (char c : path) {
        if (c == '\'') out += "'\\''";
        else out += c;
    }
    out += "'";
    return out;
}

bool file_exists(const std::string& path) {
    std::ifstream f(path);
    return f.good();
}

std::string snap_path(const std::string& dataset, const std::string& data_dir) {
    std::string txt = data_dir + "/" + dataset + ".txt";
    if (file_exists(txt)) return txt;
    std::string gz = txt + ".gz";
    if (file_exists(gz)) return gz;
    return "";
}

std::vector<std::pair<int, int>> read_snap_pairs(const std::string& path, long long max_edges, int max_vertices) {
    std::unordered_map<long long, int> id_map;
    std::vector<std::pair<int, int>> pairs;
    id_map.reserve(100000);
    pairs.reserve(max_edges > 0 && max_edges < 10000000 ? static_cast<size_t>(max_edges) : 100000);

    auto map_vertex = [&](long long original) -> int {
        auto it = id_map.find(original);
        if (it != id_map.end()) return it->second;
        if (max_vertices > 0 && static_cast<int>(id_map.size()) >= max_vertices) return -1;
        int next = static_cast<int>(id_map.size());
        id_map[original] = next;
        return next;
    };

    auto handle_line = [&](const std::string& line) {
        if (line.empty() || line[0] == '#') return;
        std::istringstream iss(line);
        long long a, b;
        if (!(iss >> a >> b)) return;
        int u = map_vertex(a);
        int v = map_vertex(b);
        if (u >= 0 && v >= 0) pairs.push_back({u, v});
    };

    if (path.size() >= 3 && path.substr(path.size() - 3) == ".gz") {
        std::string cmd = "gzip -dc " + shell_quote(path) + " 2>/dev/null";
        FILE* pipe = popen(cmd.c_str(), "r");
        if (!pipe) throw std::runtime_error("failed to open gzip pipe for " + path);
        char buffer[1 << 15];
        while (fgets(buffer, sizeof(buffer), pipe)) {
            handle_line(buffer);
            if (max_edges > 0 && static_cast<long long>(pairs.size()) >= max_edges) break;
        }
        pclose(pipe);
    } else {
        std::ifstream in(path);
        if (!in) throw std::runtime_error("failed to open " + path);
        std::string line;
        while (std::getline(in, line)) {
            handle_line(line);
            if (max_edges > 0 && static_cast<long long>(pairs.size()) >= max_edges) break;
        }
    }
    return pairs;
}

Graph load_snap_graph(const std::string& dataset, const std::string& data_dir, int seed, long long max_edges, int max_vertices, bool use_largest) {
    std::string path = snap_path(dataset, data_dir);
    if (path.empty()) {
        throw std::runtime_error("missing SNAP dataset file for " + dataset + " under " + data_dir);
    }
    auto pairs = read_snap_pairs(path, max_edges, max_vertices);
    int n = 0;
    for (auto [u, v] : pairs) n = std::max(n, std::max(u, v) + 1);
    Graph graph = weighted_graph_from_pairs(n, pairs, seed);
    if (use_largest) graph = largest_component(graph);
    return graph;
}

struct GraphCase {
    std::string source;
    std::string family;
    std::string parameters;
    Graph graph;
    std::vector<std::string> algorithms;
    std::vector<int> dijkstra_sources;

    GraphCase(
        std::string graph_source,
        std::string graph_family,
        std::string graph_parameters,
        Graph graph_value,
        std::vector<std::string> algorithm_names = {"dijkstra", "prim"},
        std::vector<int> dijkstra_source_vertices = {}
    )
        : source(std::move(graph_source)),
          family(std::move(graph_family)),
          parameters(std::move(graph_parameters)),
          graph(std::move(graph_value)),
          algorithms(std::move(algorithm_names)),
          dijkstra_sources(std::move(dijkstra_source_vertices)) {}
};

std::vector<GraphCase> synthetic_suite(int seed, const std::string& stress_level) {
    std::vector<GraphCase> cases;
    for (int n : {25, 50, 100}) {
        int m = std::min(3 * n, n * (n - 1) / 2);
        cases.push_back({"synthetic", "sparse_er_nm", "n=" + std::to_string(n) + ",m=" + std::to_string(m), sparse_er(n, m, seed)});
    }
    for (auto [n, p] : std::vector<std::pair<int, double>>{{25, 0.20}, {50, 0.12}, {100, 0.08}}) {
        std::ostringstream label;
        label << "n=" << n << ",p=" << p;
        cases.push_back({"synthetic", "medium_er_np", label.str(), dense_er(n, p, seed)});
    }
    for (auto [n, p] : std::vector<std::pair<int, double>>{{25, 0.35}, {50, 0.25}, {100, 0.18}}) {
        std::ostringstream label;
        label << "n=" << n << ",p=" << p;
        cases.push_back({"synthetic", "dense_er_np", label.str(), dense_er(n, p, seed)});
    }
    for (auto [n, p] : std::vector<std::pair<int, double>>{{25, 0.65}, {50, 0.50}, {100, 0.35}}) {
        std::ostringstream label;
        label << "n=" << n << ",p=" << p;
        cases.push_back({"synthetic", "superdense_er_np", label.str(), dense_er(n, p, seed)});
    }
    for (auto [r, c] : std::vector<std::pair<int, int>>{{5, 5}, {8, 8}, {10, 10}}) {
        cases.push_back({"synthetic", "grid_2d", "rows=" + std::to_string(r) + ",cols=" + std::to_string(c), grid_graph(r, c, seed)});
    }
    if (seed == 0 && stress_level != "none") {
        std::vector<std::pair<int, int>> stress_parameters;
        if (stress_level == "small") {
            stress_parameters = {{5, 20}, {10, 50}};
        } else if (stress_level == "full") {
            stress_parameters = {{50, 1000}, {100, 2000}, {1, 2000}};
        } else {
            throw std::runtime_error("unknown stress level: " + stress_level);
        }

        for (auto [k, r] : stress_parameters) {
            int c = r + 1;
            int b = k * c + r + k + 1;
            cases.push_back({
                "synthetic",
                "dijkstra_decrease_key_stress",
                "k=" + std::to_string(k) + ",r=" + std::to_string(r) + ",C=" + std::to_string(c) + ",B=" + std::to_string(b) + ",rank=alternating_reverse",
                dijkstra_decrease_key_stress_graph(k, r),
                {"dijkstra"},
                {0},
            });
            cases.push_back({
                "synthetic",
                "prim_decrease_key_stress",
                "k=" + std::to_string(k) + ",r=" + std::to_string(r) + ",C=" + std::to_string(c) + ",B=" + std::to_string(b) + ",rank=alternating_reverse",
                prim_decrease_key_stress_graph(k, r),
                {"prim"},
                {},
            });
        }
    }
    return cases;
}

std::vector<int> source_vertices(int n) {
    std::set<int> sources = {0, n / 2, n - 1};
    std::vector<int> out;
    for (int s : sources) if (s >= 0 && s < n) out.push_back(s);
    return out;
}

double median(std::vector<double> values) {
    if (values.empty()) return 0.0;
    std::sort(values.begin(), values.end());
    size_t mid = values.size() / 2;
    if (values.size() % 2 == 1) return values[mid];
    return (values[mid - 1] + values[mid]) / 2.0;
}

std::string csv_escape(const std::string& value) {
    if (value.find_first_of(",\"\n") == std::string::npos) return value;
    std::string out = "\"";
    for (char c : value) {
        if (c == '"') out += "\"\"";
        else out += c;
    }
    out += "\"";
    return out;
}

struct ChildRunResult {
    double output_value = 0.0;
    double runtime_ms = 0.0;
    long long max_rss_kbytes = 0;
    AlgoStats stats;
};

struct BenchmarkResult {
    double output_value = 0.0;
    double runtime_ms = 0.0;
    double mean_runtime_ms = 0.0;
    double median_runtime_ms = 0.0;
    double min_runtime_ms = 0.0;
    double max_runtime_ms = 0.0;
    long long max_rss_kbytes = 0;
    double median_max_rss_kbytes = 0.0;
    AlgoStats stats;
};

ChildRunResult parse_child_result(const std::string& text) {
    std::istringstream iss(text);
    ChildRunResult result;
    iss >> result.output_value
        >> result.runtime_ms
        >> result.stats.reachable_vertex_count
        >> result.stats.visited_vertex_count
        >> result.stats.edge_scan_count
        >> result.stats.relax_attempt_count
        >> result.stats.successful_relax_count
        >> result.stats.successful_key_update_count;
    if (!iss) {
        throw std::runtime_error("failed to parse child benchmark output: " + text);
    }
    return result;
}

ChildRunResult run_once_in_child(
    const Graph& graph,
    const std::string& algorithm,
    const std::string& heap,
    int source
) {
    int pipe_fd[2];
    if (pipe(pipe_fd) != 0) {
        throw std::runtime_error("pipe failed");
    }

    pid_t pid = fork();
    if (pid < 0) {
        close(pipe_fd[0]);
        close(pipe_fd[1]);
        throw std::runtime_error("fork failed");
    }

    if (pid == 0) {
        close(pipe_fd[0]);
        try {
            AlgoStats stats;
            double output_value = 0.0;
            auto start = Clock::now();
            if (algorithm == "dijkstra") {
                auto result = dijkstra(graph, source, heap);
                output_value = result.first;
                stats = result.second;
            } else {
                auto result = prim(graph, source, heap);
                output_value = result.first;
                stats = result.second;
            }
            auto stop = Clock::now();
            double runtime_ms = std::chrono::duration<double, std::milli>(stop - start).count();

            FILE* out = fdopen(pipe_fd[1], "w");
            if (!out) _exit(3);
            std::fprintf(
                out,
                "%.17g %.17g %lld %lld %lld %lld %lld %lld\n",
                output_value,
                runtime_ms,
                stats.reachable_vertex_count,
                stats.visited_vertex_count,
                stats.edge_scan_count,
                stats.relax_attempt_count,
                stats.successful_relax_count,
                stats.successful_key_update_count
            );
            std::fclose(out);
            _exit(0);
        } catch (const std::exception& ex) {
            std::string message = std::string("child benchmark failed: ") + ex.what() + "\n";
            ssize_t ignored = write(STDERR_FILENO, message.data(), message.size());
            (void)ignored;
            close(pipe_fd[1]);
            _exit(2);
        }
    }

    close(pipe_fd[1]);
    std::string output;
    char buffer[256];
    while (true) {
        ssize_t n = read(pipe_fd[0], buffer, sizeof(buffer));
        if (n > 0) {
            output.append(buffer, buffer + n);
        } else if (n == 0) {
            break;
        } else {
            close(pipe_fd[0]);
            throw std::runtime_error("read from child pipe failed");
        }
    }
    close(pipe_fd[0]);

    struct rusage usage {};
    int status = 0;
    if (wait4(pid, &status, 0, &usage) < 0) {
        throw std::runtime_error("wait4 failed");
    }
    if (!WIFEXITED(status) || WEXITSTATUS(status) != 0) {
        throw std::runtime_error("child benchmark exited unsuccessfully");
    }

    ChildRunResult result = parse_child_result(output);
    result.max_rss_kbytes = usage.ru_maxrss;
    return result;
}

std::pair<double, AlgoStats> run_algorithm_once(
    const Graph& graph,
    const std::string& algorithm,
    const std::string& heap,
    int source
) {
    if (algorithm == "dijkstra") {
        return dijkstra(graph, source, heap);
    }
    return prim(graph, source, heap);
}

BenchmarkResult run_benchmark(
    const Graph& graph,
    const std::string& algorithm,
    const std::string& heap,
    int source,
    int repeats
) {
    std::vector<double> runtimes;
    std::vector<double> rss_values;
    BenchmarkResult aggregate;

    // Runtime is measured in-process so tiny synthetic graphs are not dominated
    // by fork/wait scheduling effects. RSS is measured separately below.
    for (int r = 0; r < repeats; ++r) {
        auto start = Clock::now();
        auto run = run_algorithm_once(graph, algorithm, heap, source);
        auto stop = Clock::now();
        aggregate.output_value = run.first;
        aggregate.stats = run.second;
        runtimes.push_back(std::chrono::duration<double, std::milli>(stop - start).count());
    }

    aggregate.mean_runtime_ms = std::accumulate(runtimes.begin(), runtimes.end(), 0.0) / runtimes.size();
    aggregate.median_runtime_ms = median(runtimes);
    aggregate.runtime_ms = aggregate.median_runtime_ms;
    aggregate.min_runtime_ms = *std::min_element(runtimes.begin(), runtimes.end());
    aggregate.max_runtime_ms = *std::max_element(runtimes.begin(), runtimes.end());

    for (int r = 0; r < repeats; ++r) {
        ChildRunResult memory_run = run_once_in_child(graph, algorithm, heap, source);
        rss_values.push_back(static_cast<double>(memory_run.max_rss_kbytes));
        aggregate.max_rss_kbytes = std::max(aggregate.max_rss_kbytes, memory_run.max_rss_kbytes);
    }
    aggregate.median_max_rss_kbytes = median(rss_values);
    return aggregate;
}

struct Args {
    std::string mode = "all";
    std::string output = "results/cpp_results.csv";
    std::string snap_data_dir = "data/snap";
    int sample_count = 3;
    int repeats = 3;
    long long snap_max_edges = 50000;
    int snap_max_vertices = 0;
    bool largest_component = true;
    std::string stress_level = "full";
};

Args parse_args(int argc, char** argv) {
    Args args;
    for (int i = 1; i < argc; ++i) {
        std::string key = argv[i];
        auto require_value = [&](const std::string& option) -> std::string {
            if (i + 1 >= argc) throw std::runtime_error("missing value for " + option);
            return argv[++i];
        };
        if (key == "--mode") args.mode = require_value(key);
        else if (key == "--output") args.output = require_value(key);
        else if (key == "--snap-data-dir") args.snap_data_dir = require_value(key);
        else if (key == "--sample-count") args.sample_count = std::stoi(require_value(key));
        else if (key == "--repeats") args.repeats = std::stoi(require_value(key));
        else if (key == "--snap-max-edges") args.snap_max_edges = std::stoll(require_value(key));
        else if (key == "--snap-max-vertices") args.snap_max_vertices = std::stoi(require_value(key));
        else if (key == "--stress-level") args.stress_level = require_value(key);
        else if (key == "--keep-components") args.largest_component = false;
        else throw std::runtime_error("unknown argument: " + key);
    }
    return args;
}

int main(int argc, char** argv) {
    Args args = parse_args(argc, argv);
    std::ofstream out(args.output);
    if (!out) throw std::runtime_error("failed to open output " + args.output);

    out << "graph_source,graph_family,graph_size,graph_num_edges,graph_average_degree,graph_maximum_degree,"
        << "graph_parameters,seed,algorithm,heap_type,start_vertex,output_value,"
        << "runtime_ms,mean_runtime_ms,median_runtime_ms,min_runtime_ms,max_runtime_ms,"
        << "repeats,runtime_measurement,rss_measurement,max_rss_kbytes,median_max_rss_kbytes,reachable_vertex_count,visited_vertex_count,edge_scan_count,"
        << "relax_attempt_count,successful_relax_count,successful_key_update_count,priority_queue_memory_bytes\n";

    std::vector<std::string> heap_types = {"binary", "pairing", "fibonacci"};
    std::vector<std::string> snap_datasets;
    if (args.mode == "all") snap_datasets = {"ca-GrQc", "roadNet-PA", "roadNet-CA"};
    else if (args.mode == "ca-GrQc" || args.mode == "roadNet-PA" || args.mode == "roadNet-CA") snap_datasets = {args.mode};

    for (int seed = 0; seed < args.sample_count; ++seed) {
        std::vector<GraphCase> cases;
        if (args.mode == "all" || args.mode == "syn") {
            auto syn = synthetic_suite(seed, args.stress_level);
            cases.insert(cases.end(), std::make_move_iterator(syn.begin()), std::make_move_iterator(syn.end()));
        }
        for (const auto& dataset : snap_datasets) {
            std::string path = snap_path(dataset, args.snap_data_dir);
            if (path.empty()) {
                std::cerr << "warning: skipping missing SNAP dataset " << dataset << " under " << args.snap_data_dir << "\n";
                continue;
            }
            Graph graph = load_snap_graph(dataset, args.snap_data_dir, seed, args.snap_max_edges, args.snap_max_vertices, args.largest_component);
            std::string params = "dataset=" + dataset + ",component=" + (args.largest_component ? std::string("largest") : std::string("all"));
            if (args.snap_max_edges > 0) params += ",max_edges=" + std::to_string(args.snap_max_edges);
            if (args.snap_max_vertices > 0) params += ",max_vertices=" + std::to_string(args.snap_max_vertices);
            cases.push_back({"snap", "snap_" + dataset, params, std::move(graph)});
        }

        for (const auto& gc : cases) {
            bool run_dijkstra = std::find(gc.algorithms.begin(), gc.algorithms.end(), "dijkstra") != gc.algorithms.end();
            bool run_prim = std::find(gc.algorithms.begin(), gc.algorithms.end(), "prim") != gc.algorithms.end();

            std::vector<int> dijkstra_sources = gc.dijkstra_sources.empty()
                ? source_vertices(gc.graph.n)
                : gc.dijkstra_sources;
            if (run_dijkstra) for (int source : dijkstra_sources) {
                for (const auto& heap : heap_types) {
                    BenchmarkResult result = run_benchmark(gc.graph, "dijkstra", heap, source, args.repeats);
                    out << gc.source << "," << gc.family << "," << gc.graph.n << "," << gc.graph.edges.size() << ","
                        << gc.graph.average_degree() << "," << gc.graph.max_degree() << "," << csv_escape(gc.parameters) << ","
                        << seed << ",dijkstra," << heap << "," << source << "," << result.output_value << ","
                        << result.runtime_ms << "," << result.mean_runtime_ms << "," << result.median_runtime_ms << ","
                        << result.min_runtime_ms << "," << result.max_runtime_ms << ","
                        << args.repeats << ",in_process_steady_clock,child_process_wait4,"
                        << result.max_rss_kbytes << "," << result.median_max_rss_kbytes << ","
                        << result.stats.reachable_vertex_count << ",,"
                        << result.stats.edge_scan_count << "," << result.stats.relax_attempt_count << ","
                        << result.stats.successful_relax_count << ",,"
                        << result.stats.priority_queue_memory_bytes << "\n";
                }
            }

            if (run_prim) for (const auto& heap : heap_types) {
                BenchmarkResult result = run_benchmark(gc.graph, "prim", heap, 0, args.repeats);
                out << gc.source << "," << gc.family << "," << gc.graph.n << "," << gc.graph.edges.size() << ","
                    << gc.graph.average_degree() << "," << gc.graph.max_degree() << "," << csv_escape(gc.parameters) << ","
                    << seed << ",prim," << heap << ",0," << result.output_value << ","
                    << result.runtime_ms << "," << result.mean_runtime_ms << "," << result.median_runtime_ms << ","
                    << result.min_runtime_ms << "," << result.max_runtime_ms << ","
                    << args.repeats << ",in_process_steady_clock,child_process_wait4,"
                    << result.max_rss_kbytes << "," << result.median_max_rss_kbytes << ",,"
                    << result.stats.visited_vertex_count << ","
                    << result.stats.edge_scan_count << ",,,"
                    << result.stats.successful_key_update_count << ","
                    << result.stats.priority_queue_memory_bytes << "\n";
            }
        }
    }

    std::cout << "Wrote C++ experiment rows to " << args.output << "\n";
    return 0;
}

