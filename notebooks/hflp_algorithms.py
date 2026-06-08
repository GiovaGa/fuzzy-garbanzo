"""
hflp_algorithms.py
==================
Algorithms for the two-level, globally-inclusive, nested
Hierarchical Facility Location Problem (HFLP).

Problem formulation follows Daskin (1995) and Sahin & Sural (2007):

  Sets:
    I  – demand nodes
    J  – candidate Level-1 (lower) facility sites
    J' – candidate Level-2 (upper) facility sites  (here J' = J)

  Parameters:
    h_i   – demand at node i
    d_ij  – shortest-path distance from demand node i to candidate j
    p1    – number of Level-1 facilities to open
    p2    – number of Level-2 facilities to open  (p2 <= p1)

  Objective (globally-inclusive, minimize total demand-weighted travel):
    min  sum_i sum_j  h_i * d_ij * Y_ij
       + sum_i sum_j' h_i * d_ij' * X_ij'

  Constraints:
    * Each demand assigned to exactly one L1 and one L2 facility.
    * Assignment only to open facilities.
    * Exactly p1 (resp. p2) L1 (resp. L2) facilities open.
    * Nesting: every L2 site must also be open as an L1 site.

Algorithms implemented
----------------------
1. build_distance_matrix   – utility: all-pairs shortest paths
2. make_random_graph       – Erdos-Renyi graph with Euclidean weights
3. make_grid_graph         – m x n grid graph with unit weights
4. make_hflp_instance      – assemble an instance dict
5. eval_solution           – evaluate a (lv1_set, lv2_set) solution
6. simulated_annealing_hflp – SA metaheuristic
7. solve_hflp_ilp           – exact ILP via PuLP/CBC
8. genetic_algorithm_hflp   – GA metaheuristic  ← NEW
9. plot_solution            – visualise a solution on the graph
10. plot_convergence_history – plot cost / temperature over iterations
11. compare_bar             – bar chart comparing algorithms
"""

import math
import random
import time
import warnings

import numpy as np
import networkx as nx
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.lines import Line2D
import pulp

warnings.filterwarnings("ignore")

# ---------------------------------------------------------------------------
# 1. Distance matrix
# ---------------------------------------------------------------------------

def build_distance_matrix(G):
    """Compute all-pairs shortest-path distances.

    Uses edge weights when present, hop count otherwise.

    Returns
    -------
    dist  : ndarray, shape (n, n)
    nodes : list of node labels in index order
    """
    nodes = list(G.nodes())
    node_idx = {v: i for i, v in enumerate(nodes)}
    n = len(nodes)
    dist = np.full((n, n), np.inf)

    if nx.is_weighted(G):
        lengths = dict(nx.all_pairs_dijkstra_path_length(G, weight="weight"))
    else:
        lengths = dict(nx.all_pairs_shortest_path_length(G))

    for u, row in lengths.items():
        for v, d in row.items():
            dist[node_idx[u], node_idx[v]] = d
    return dist, nodes


# ---------------------------------------------------------------------------
# 2. Graph generators
# ---------------------------------------------------------------------------

def make_random_graph(n=20, p=0.25, seed=42):
    """Erdos-Renyi random *connected* graph with Euclidean edge weights."""
    rng = random.Random(seed)
    while True:
        G = nx.erdos_renyi_graph(n, p, seed=rng.randint(0, 10_000))
        if nx.is_connected(G):
            break
    pos = {v: (rng.random(), rng.random()) for v in G.nodes()}
    for u, v in G.edges():
        x1, y1 = pos[u]
        x2, y2 = pos[v]
        G[u][v]["weight"] = math.hypot(x2 - x1, y2 - y1)
    nx.set_node_attributes(G, pos, "pos")
    return G


def make_grid_graph(m=5, n=5):
    """m x n grid graph with unit edge weights."""
    G = nx.grid_2d_graph(m, n)
    mapping = {(i, j): i * n + j for i, j in G.nodes()}
    G = nx.relabel_nodes(G, mapping)
    pos = {i * n + j: (j, -i) for i in range(m) for j in range(n)}
    for u, v in G.edges():
        G[u][v]["weight"] = 1.0
    nx.set_node_attributes(G, pos, "pos")
    return G


# ---------------------------------------------------------------------------
# 3. Instance builder
# ---------------------------------------------------------------------------

def make_hflp_instance(G, p1, p2, demand_seed=7):
    """Build a HFLP instance dict from a graph.

    Parameters
    ----------
    G           : NetworkX graph
    p1          : int – number of Level-1 facilities to open
    p2          : int – number of Level-2 facilities (p2 <= p1)
    demand_seed : int – RNG seed for demand vector

    Returns
    -------
    dict with keys: G, nodes, n, dist, demand, p1, p2
    """
    assert p2 <= p1, "Level-2 count must be <= Level-1 count (nesting)"
    dist, nodes = build_distance_matrix(G)
    n = len(nodes)
    rng = np.random.RandomState(demand_seed)
    demand = rng.randint(1, 10, size=n).astype(float)
    return {
        "G": G,
        "nodes": nodes,
        "n": n,
        "dist": dist,
        "demand": demand,
        "p1": p1,
        "p2": p2,
    }


# ---------------------------------------------------------------------------
# 4. Solution evaluator
# ---------------------------------------------------------------------------

def eval_solution(inst, lv1_set, lv2_set):
    """Evaluate total demand-weighted distance for a solution.

    Globally-inclusive: each demand node is independently assigned to the
    nearest open facility at each level.

    Returns
    -------
    total_cost : float
    assign_lv1 : ndarray of shape (n,) – index of assigned L1 facility
    assign_lv2 : ndarray of shape (n,) – index of assigned L2 facility
    """
    dist, demand = inst["dist"], inst["demand"]
    n = inst["n"]
    lv1 = list(lv1_set)
    lv2 = list(lv2_set)

    cost = 0.0
    assign_lv1 = np.zeros(n, dtype=int)
    assign_lv2 = np.zeros(n, dtype=int)

    for i in range(n):
        best1 = min(lv1, key=lambda j: dist[i, j])
        assign_lv1[i] = best1
        cost += demand[i] * dist[i, best1]

        best2 = min(lv2, key=lambda j: dist[i, j])
        assign_lv2[i] = best2
        cost += demand[i] * dist[i, best2]

    return cost, assign_lv1, assign_lv2


# ---------------------------------------------------------------------------
# 5. Simulated Annealing
# ---------------------------------------------------------------------------

def simulated_annealing_hflp(
    inst,
    T_init=500.0,
    T_min=1e-3,
    alpha=0.995,
    max_iter=10_000,
    seed=0,
    verbose=True,
):
    """Simulated Annealing for the two-level globally-inclusive HFLP.

    Move set
    --------
    swap_lv1 : replace one open L1 facility with a closed node; if the
               removed node was also in L2, move that L2 slot to the new node.
    swap_lv2 : replace one open L2 facility with another L1 node not in L2.

    Acceptance criterion
    --------------------
    P(accept) = 1                     if delta <= 0
              = exp(-delta / T)       otherwise

    Temperature schedule: T <- max(alpha * T, T_min)

    Returns
    -------
    best_lv1, best_lv2 : frozensets of node indices
    best_cost          : float
    history            : list of (iteration, temperature, current_cost, best_cost)
    """
    rng = random.Random(seed)
    n, p1, p2 = inst["n"], inst["p1"], inst["p2"]
    all_nodes = set(range(n))

    # --- initialisation: random open sets ---
    lv1 = set(rng.sample(range(n), p1))
    lv2 = set(rng.sample(list(lv1), p2))   # nested: L2 subset of L1

    cur_cost, _, _ = eval_solution(inst, lv1, lv2)
    best_lv1, best_lv2, best_cost = set(lv1), set(lv2), cur_cost

    T = T_init
    history = [(0, T, cur_cost, best_cost)]

    for it in range(1, max_iter + 1):
        move = rng.choice(["swap_lv1", "swap_lv2"])

        if move == "swap_lv1":
            out = all_nodes - lv1
            if not out:
                continue
            add = rng.choice(list(out))
            rem = rng.choice(list(lv1))
            new_lv1 = (lv1 - {rem}) | {add}
            new_lv2 = (lv2 - {rem}) | {add} if rem in lv2 else set(lv2)
        else:  # swap_lv2
            candidates = lv1 - lv2
            if not candidates:
                continue
            add = rng.choice(list(candidates))
            rem = rng.choice(list(lv2))
            new_lv1 = set(lv1)
            new_lv2 = (lv2 - {rem}) | {add}

        new_cost, _, _ = eval_solution(inst, new_lv1, new_lv2)
        delta = new_cost - cur_cost

        if delta < 0 or rng.random() < math.exp(-delta / T):
            lv1, lv2 = new_lv1, new_lv2
            cur_cost = new_cost
            if cur_cost < best_cost:
                best_lv1, best_lv2, best_cost = set(lv1), set(lv2), cur_cost

        T = max(T * alpha, T_min)

        if it % max(1, max_iter // 10) == 0:
            history.append((it, T, cur_cost, best_cost))
            if verbose:
                print(
                    f"  iter {it:6d} | T={T:.4f} | "
                    f"cur={cur_cost:.2f} | best={best_cost:.2f}"
                )

    return best_lv1, best_lv2, best_cost, history


# ---------------------------------------------------------------------------
# 6. ILP (PuLP / CBC)
# ---------------------------------------------------------------------------

def solve_hflp_ilp(inst, time_limit=120, verbose=False):
    """Solve the globally-inclusive nested two-level HFLP exactly via ILP.

    Uses the assignment-based formulation with CBC through PuLP.

    Returns
    -------
    lv1_set    : set of open L1 facility indices
    lv2_set    : set of open L2 facility indices
    obj_value  : float
    solve_time : float (seconds)
    status     : str
    """
    n, p1, p2 = inst["n"], inst["p1"], inst["p2"]
    dist, demand = inst["dist"], inst["demand"]

    prob = pulp.LpProblem("HFLP", pulp.LpMinimize)

    y = [pulp.LpVariable(f"y_{j}", cat="Binary") for j in range(n)]
    x = [pulp.LpVariable(f"x_{j}", cat="Binary") for j in range(n)]
    Y = [
        [pulp.LpVariable(f"Y_{i}_{j}", cat="Binary") for j in range(n)]
        for i in range(n)
    ]
    X = [
        [pulp.LpVariable(f"X_{i}_{j}", cat="Binary") for j in range(n)]
        for i in range(n)
    ]

    # Objective
    prob += pulp.lpSum(
        demand[i] * dist[i, j] * (Y[i][j] + X[i][j])
        for i in range(n)
        for j in range(n)
        if not np.isinf(dist[i, j])
    )

    # Constraints
    for i in range(n):
        prob += pulp.lpSum(Y[i][j] for j in range(n)) == 1
        prob += pulp.lpSum(X[i][j] for j in range(n)) == 1

    for i in range(n):
        for j in range(n):
            prob += Y[i][j] <= y[j]
            prob += X[i][j] <= x[j]

    prob += pulp.lpSum(y[j] for j in range(n)) == p1
    prob += pulp.lpSum(x[j] for j in range(n)) == p2

    for j in range(n):
        prob += x[j] <= y[j]

    t0 = time.time()
    solver = pulp.PULP_CBC_CMD(msg=int(verbose), timeLimit=time_limit)
    prob.solve(solver)
    solve_time = time.time() - t0

    status = pulp.LpStatus[prob.status]
    obj_val = pulp.value(prob.objective) if prob.status == 1 else float("inf")

    lv1_set = {
        j for j in range(n)
        if pulp.value(y[j]) is not None and pulp.value(y[j]) > 0.5
    }
    lv2_set = {
        j for j in range(n)
        if pulp.value(x[j]) is not None and pulp.value(x[j]) > 0.5
    }

    return lv1_set, lv2_set, obj_val, solve_time, status


# ---------------------------------------------------------------------------
# 7. Genetic Algorithm   ← NEW
# ---------------------------------------------------------------------------

def _random_solution(n, p1, p2, rng):
    """Return a random feasible (lv1, lv2) pair."""
    lv1 = set(rng.sample(range(n), p1))
    lv2 = set(rng.sample(list(lv1), p2))
    return lv1, lv2


def _tournament_select(population, fitnesses, k, rng):
    """Return the index of the winner of a k-way tournament."""
    contestants = rng.sample(range(len(population)), k)
    return min(contestants, key=lambda idx: fitnesses[idx])


def _crossover(lv1_a, lv2_a, lv1_b, lv2_b, p1, p2, rng):
    """Single-point set crossover for a HFLP solution pair.

    Strategy
    --------
    L1: form the union of both parents' L1 sets, then randomly choose p1
        nodes; if the union has < p1 elements (impossible when both sets
        have size p1 and n > p1) fall back to one parent.
    L2: intersect the new L1 set with the union of both parents' L2 sets;
        if there are >= p2 candidates, randomly choose p2; otherwise fill
        from the new L1 set.

    The child always satisfies p1, p2, and the nesting constraint.
    """
    # --- L1 crossover ---
    pool1 = list(lv1_a | lv1_b)
    if len(pool1) >= p1:
        child_lv1 = set(rng.sample(pool1, p1))
    else:
        child_lv1 = set(lv1_a) if rng.random() < 0.5 else set(lv1_b)

    # --- L2 crossover ---
    pool2 = list(child_lv1 & (lv2_a | lv2_b))
    if len(pool2) >= p2:
        child_lv2 = set(rng.sample(pool2, p2))
    else:
        # Not enough shared L2 candidates; fill randomly from child_lv1
        child_lv2 = set(rng.sample(list(child_lv1), p2))

    return child_lv1, child_lv2


def _mutate(lv1, lv2, n, p1, p2, rng, mutation_rate=0.3):
    """Apply random swap mutations to lv1 and lv2.

    Each mutation type is applied independently with probability
    *mutation_rate*.

    swap_lv1 : replace one L1 node with a node not in L1 (propagate to L2
               if the removed node was also in L2).
    swap_lv2 : replace one L2 node with an L1 node not currently in L2.
    """
    all_nodes = set(range(n))
    new_lv1, new_lv2 = set(lv1), set(lv2)

    # L1 mutation
    if rng.random() < mutation_rate:
        out = list(all_nodes - new_lv1)
        if out:
            add = rng.choice(out)
            rem = rng.choice(list(new_lv1))
            new_lv1 = (new_lv1 - {rem}) | {add}
            if rem in new_lv2:
                new_lv2 = (new_lv2 - {rem}) | {add}

    # L2 mutation
    if rng.random() < mutation_rate:
        candidates = list(new_lv1 - new_lv2)
        if candidates:
            add = rng.choice(candidates)
            rem = rng.choice(list(new_lv2))
            new_lv2 = (new_lv2 - {rem}) | {add}

    return new_lv1, new_lv2


def genetic_algorithm_hflp(
    inst,
    pop_size=50,
    max_gen=200,
    tournament_k=3,
    crossover_prob=0.8,
    mutation_rate=0.3,
    elitism=True,
    seed=0,
    verbose=True,
):
    """Genetic Algorithm for the two-level globally-inclusive HFLP.

    Representation
    --------------
    Each individual is a pair (lv1_set, lv2_set) of Python sets.
    The fitness value is the total demand-weighted distance returned by
    eval_solution.

    Operators
    ---------
    Selection  : tournament selection (size k)
    Crossover  : set union crossover (see _crossover)
    Mutation   : random facility swaps (see _mutate)
    Replacement: generational with optional elitism (best individual
                 always survives)

    Parameters
    ----------
    inst          : HFLP instance dict (from make_hflp_instance)
    pop_size      : int   – population size
    max_gen       : int   – number of generations
    tournament_k  : int   – tournament size for selection
    crossover_prob: float – probability of crossover vs. copying a parent
    mutation_rate : float – per-operator mutation probability
    elitism       : bool  – preserve the best individual each generation
    seed          : int   – RNG seed for reproducibility
    verbose       : bool  – print progress every 10% of generations

    Returns
    -------
    best_lv1, best_lv2 : sets of node indices
    best_cost          : float
    history            : list of (generation, best_cost, avg_cost)
    """
    rng = random.Random(seed)
    n, p1, p2 = inst["n"], inst["p1"], inst["p2"]

    # --- Initialise population ---
    population = [_random_solution(n, p1, p2, rng) for _ in range(pop_size)]
    fitnesses = [eval_solution(inst, lv1, lv2)[0] for lv1, lv2 in population]

    best_idx = int(np.argmin(fitnesses))
    best_lv1, best_lv2 = set(population[best_idx][0]), set(population[best_idx][1])
    best_cost = fitnesses[best_idx]

    history = [(0, best_cost, float(np.mean(fitnesses)))]

    for gen in range(1, max_gen + 1):
        new_pop = []
        new_fit = []

        # Elitism: carry the current best individual forward
        if elitism:
            new_pop.append((set(best_lv1), set(best_lv2)))
            new_fit.append(best_cost)

        while len(new_pop) < pop_size:
            # Selection
            idx_a = _tournament_select(population, fitnesses, tournament_k, rng)
            idx_b = _tournament_select(population, fitnesses, tournament_k, rng)
            lv1_a, lv2_a = population[idx_a]
            lv1_b, lv2_b = population[idx_b]

            # Crossover
            if rng.random() < crossover_prob:
                child_lv1, child_lv2 = _crossover(
                    lv1_a, lv2_a, lv1_b, lv2_b, p1, p2, rng
                )
            else:
                # No crossover: copy the fitter parent
                if fitnesses[idx_a] <= fitnesses[idx_b]:
                    child_lv1, child_lv2 = set(lv1_a), set(lv2_a)
                else:
                    child_lv1, child_lv2 = set(lv1_b), set(lv2_b)

            # Mutation
            child_lv1, child_lv2 = _mutate(
                child_lv1, child_lv2, n, p1, p2, rng, mutation_rate
            )

            child_cost, _, _ = eval_solution(inst, child_lv1, child_lv2)
            new_pop.append((child_lv1, child_lv2))
            new_fit.append(child_cost)

        population = new_pop
        fitnesses = new_fit

        # Track best
        cur_best_idx = int(np.argmin(fitnesses))
        if fitnesses[cur_best_idx] < best_cost:
            best_cost = fitnesses[cur_best_idx]
            best_lv1 = set(population[cur_best_idx][0])
            best_lv2 = set(population[cur_best_idx][1])

        if gen % max(1, max_gen // 10) == 0:
            avg_cost = float(np.mean(fitnesses))
            history.append((gen, best_cost, avg_cost))
            if verbose:
                print(
                    f"  gen {gen:5d} | best={best_cost:.2f} | avg={avg_cost:.2f}"
                )

    return best_lv1, best_lv2, best_cost, history


# ---------------------------------------------------------------------------
# 8. Visualisation utilities
# ---------------------------------------------------------------------------

def plot_solution(inst, lv1_set, lv2_set, title="HFLP Solution", ax=None):
    """Draw the graph with colour-coded facilities and assignment arrows."""
    G = inst["G"]
    nodes = inst["nodes"]
    n = inst["n"]
    pos = nx.get_node_attributes(G, "pos")
    if not pos:
        pos = nx.spring_layout(G, seed=42)

    _, assign_lv1, assign_lv2 = eval_solution(inst, lv1_set, lv2_set)

    if ax is None:
        _, ax = plt.subplots(figsize=(9, 6))

    color_map, size_map = [], []
    for idx in range(n):
        if idx in lv2_set:
            color_map.append("#e74c3c")   # red  = L2
            size_map.append(500)
        elif idx in lv1_set:
            color_map.append("#f39c12")   # orange = L1
            size_map.append(350)
        else:
            color_map.append("#3498db")   # blue = demand
            size_map.append(120)

    nx.draw_networkx_edges(G, pos, ax=ax, alpha=0.15, edge_color="gray")

    for i in range(n):
        if nodes[i] not in lv1_set and nodes[i] not in lv2_set:
            fac = nodes[assign_lv1[i]]
            ax.annotate(
                "",
                xy=pos[fac],
                xytext=pos[nodes[i]],
                arrowprops=dict(
                    arrowstyle="->", color="#f39c12", lw=0.8, alpha=0.6
                ),
            )

    for i in range(n):
        if nodes[i] not in lv2_set:
            fac = nodes[assign_lv2[i]]
            ax.annotate(
                "",
                xy=pos[fac],
                xytext=pos[nodes[i]],
                arrowprops=dict(
                    arrowstyle="->",
                    color="#e74c3c",
                    lw=0.8,
                    alpha=0.4,
                    connectionstyle="arc3,rad=0.15",
                ),
            )

    nx.draw_networkx_nodes(
        G, pos, ax=ax, node_color=color_map, node_size=size_map, alpha=0.9
    )
    nx.draw_networkx_labels(G, pos, ax=ax, font_size=7, font_color="white")

    legend_elements = [
        mpatches.Patch(
            color="#e74c3c", label=f"Level-2 facility (p2={inst['p2']})"
        ),
        mpatches.Patch(
            color="#f39c12", label=f"Level-1 facility (p1={inst['p1']})"
        ),
        mpatches.Patch(color="#3498db", label="Demand node"),
        Line2D([0], [0], color="#f39c12", lw=1.5, label="L1 assignment"),
        Line2D([0], [0], color="#e74c3c", lw=1.5, label="L2 assignment"),
    ]
    ax.legend(handles=legend_elements, loc="upper left", fontsize=8)
    ax.set_title(title, fontsize=12, fontweight="bold")
    ax.axis("off")


def plot_convergence_history(history, algo_name="Algorithm", ax=None):
    """Plot best cost (and average cost if available) over iterations/generations.

    history entries can be:
      (iter, temperature, current_cost, best_cost)   – SA format
      (generation, best_cost, avg_cost)               – GA format
    """
    if ax is None:
        _, ax = plt.subplots(figsize=(8, 4))

    if len(history[0]) == 4:
        # SA format
        iters = [h[0] for h in history]
        best  = [h[3] for h in history]
        cur   = [h[2] for h in history]
        ax.plot(iters, cur,  color="steelblue", alpha=0.6, label="Current cost")
        ax.plot(iters, best, color="crimson",   lw=2,      label="Best cost")
        ax.set_xlabel("Iteration")
    else:
        # GA format
        gens  = [h[0] for h in history]
        best  = [h[1] for h in history]
        avg   = [h[2] for h in history]
        ax.plot(gens, avg,  color="steelblue", alpha=0.6, label="Avg cost")
        ax.plot(gens, best, color="crimson",   lw=2,      label="Best cost")
        ax.set_xlabel("Generation")

    ax.set_ylabel("Objective value")
    ax.set_title(f"{algo_name} Convergence")
    ax.legend()
    ax.grid(True, alpha=0.3)


def compare_bar(results, title="Algorithm Comparison"):
    """Bar chart comparing objective values across algorithms.

    Parameters
    ----------
    results : dict  {label: {'cost': float, 'time': float}}
    title   : str
    """
    labels = list(results.keys())
    costs  = [results[k]["cost"] for k in labels]
    times  = [results[k]["time"] for k in labels]

    x = np.arange(len(labels))
    w = 0.4

    fig, axes = plt.subplots(1, 2, figsize=(13, 5))

    # --- cost comparison ---
    ax = axes[0]
    bars = ax.bar(x, costs, w, color=["steelblue", "crimson", "seagreen"][: len(labels)], alpha=0.85)
    for bar, val in zip(bars, costs):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.3 * max(costs) / 100,
            f"{val:.1f}",
            ha="center",
            va="bottom",
            fontsize=9,
        )
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylabel("Total demand-weighted distance")
    ax.set_title(title + " – Objective Value")
    ax.grid(True, axis="y", alpha=0.3)

    # --- time comparison ---
    ax = axes[1]
    bars = ax.bar(x, times, w, color=["steelblue", "crimson", "seagreen"][: len(labels)], alpha=0.85)
    for bar, val in zip(bars, times):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.3 * max(times) / 100,
            f"{val:.2f}s",
            ha="center",
            va="bottom",
            fontsize=9,
        )
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylabel("Wall-clock time (s)")
    ax.set_title(title + " – Runtime")
    ax.grid(True, axis="y", alpha=0.3)

    plt.tight_layout()
    plt.show()
