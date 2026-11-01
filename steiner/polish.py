"""Exact per-net polishing and large neighbourhood search for 04-steiner.

route.py produces a node-disjoint packing with greedy Steiner trees. The
greedy construction is only an approximation, so a feasible packing can be
improved net by net: fix every other net, delete their nodes from the grid,
and replace the net's tree by a minimum Steiner tree of the remaining graph.
Nets have at most six terminals, so the exact tree is cheap with the
Dreyfus-Wagner recursion driven by Dijkstra (Erickson, Monma and Veinott):
one shortest path computation per terminal subset, done in C by scipy.

On top of that a large neighbourhood search rips up two or three nets at a
time and re-inserts them exactly in every order, optionally with small random
node costs on the first net so that it leaves room for the next one.

Usage:
    python polish.py <instance_dir> <in.sol> <out.sol> [--seconds S] [--seed N]
"""
import argparse
import itertools
import random
import sys
import time

import numpy as np
import scipy.sparse as sp
import scipy.sparse.csgraph as cg

from route import load_instance, write_solution

INF = np.inf


class Grid:
    """Undirected graph in arrays, plus exact Steiner trees on node subsets."""

    def __init__(self, adj):
        self.adj = adj
        self.N = max(adj) + 1
        rows, cols, w = [], [], []
        for u, nb in adj.items():
            for v, c in nb.items():
                rows.append(u)
                cols.append(v)
                w.append(c)
        self.rows = np.array(rows, dtype=np.int64)
        self.cols = np.array(cols, dtype=np.int64)
        self.w = np.array(w, dtype=np.float64)
        if self.w.min() <= 0:
            raise ValueError("arc costs must be positive")
        self.calls = 0

    def exact_tree(self, allowed, terminals, node_cost=None):
        """Minimum Steiner tree for `terminals` inside the nodes where
        `allowed` is True. Returns (cost, set of (min,max) edges) with cost
        measured in the original arc costs, or (None, None) if disconnected.
        `node_cost` is an optional array of extra cost for entering a node,
        used only to perturb the search; the returned cost ignores it."""
        self.calls += 1
        N = self.N
        m = allowed[self.rows] & allowed[self.cols]
        r, c, w = self.rows[m], self.cols[m], self.w[m]
        if node_cost is not None:
            w = w + node_cost[c]
        terms = list(terminals)
        k = len(terms)
        if k == 1:
            return 0, set()
        base = sp.csr_matrix((w, (r, c)), shape=(N + 1, N + 1))
        D, P = {}, {}
        for i, t in enumerate(terms):
            d, p = cg.dijkstra(base, directed=True, indices=t, return_predecessors=True)
            D[1 << i], P[1 << i] = d[:N], p[:N]
        full = (1 << k) - 1
        for S in range(1, full + 1):
            if S & (S - 1) == 0 or S == full:
                continue
            M = np.full(N, INF)
            s1 = (S - 1) & S
            while s1:
                s2 = S ^ s1
                if s1 < s2:
                    M = np.minimum(M, D[s1] + D[s2])
                s1 = (s1 - 1) & S
            fin = np.nonzero(np.isfinite(M))[0]
            rr = np.concatenate([r, np.full(len(fin), N, dtype=np.int64)])
            cc = np.concatenate([c, fin])
            ww = np.concatenate([w, M[fin]])
            A = sp.csr_matrix((ww, (rr, cc)), shape=(N + 1, N + 1))
            d, p = cg.dijkstra(A, directed=True, indices=N, return_predecessors=True)
            D[S], P[S] = d[:N], p[:N]
        root = terms[0]
        S = full ^ 1
        # the full set is never needed: the tree for terms[1:] rooted at terms[0]
        # is just the merge at the root, done here by hand
        M = np.full(N, INF)
        s1 = (S - 1) & S
        best_split, best = None, INF
        # value at the root only
        s1 = (S - 1) & S
        cand = []
        while s1:
            s2 = S ^ s1
            if s1 < s2:
                cand.append((D[s1][root] + D[s2][root], s1, s2))
            s1 = (s1 - 1) & S
        cand.append((D[S][root], S, 0))
        val, s1, s2 = min(cand)
        if not np.isfinite(val):
            return None, None
        edges = set()

        def walk(S, v):
            """Add the edges of the tree behind D[S][v]."""
            p = P[S]
            u = v
            if S & (S - 1) == 0:
                while p[u] >= 0:
                    edges.add((min(u, p[u]), max(u, p[u])))
                    u = p[u]
                return
            while p[u] != N:
                if p[u] < 0:
                    raise RuntimeError("broken predecessor chain")
                edges.add((min(u, p[u]), max(u, p[u])))
                u = p[u]
            target = D[S][u]
            a = (S - 1) & S
            while a:
                b = S ^ a
                if a < b and abs(D[a][u] + D[b][u] - target) <= 1e-6 * max(1.0, target):
                    walk(a, u)
                    walk(b, u)
                    return
                a = (a - 1) & S
            raise RuntimeError("no split reproduces the merge value")

        if s2 == 0:
            walk(S, root)
        else:
            walk(s1, root)
            walk(s2, root)
        cost = sum(self.adj[u][v] for (u, v) in edges)
        return cost, edges


def tree_nodes(edges, terminals):
    nodes = set(terminals)
    for u, v in edges:
        nodes.add(u)
        nodes.add(v)
    return nodes


def read_solution(path):
    trees = {}
    for line in open(path):
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        u, v, k = map(int, s.split())
        trees.setdefault(k, set()).add((min(u, v), max(u, v)))
    return trees


class Packing:
    def __init__(self, grid, terms, trees):
        self.g = grid
        self.terms = terms
        self.nets = sorted(terms)
        self.trees = {k: set(trees.get(k, ())) for k in self.nets}
        self.nodes = {k: tree_nodes(self.trees[k], terms[k]) for k in self.nets}
        self.cost = {k: sum(grid.adj[u][v] for (u, v) in self.trees[k]) for k in self.nets}
        self.on_change = None

    def note(self):
        """Tell the caller the current total, for the incumbent time series."""
        if self.on_change:
            self.on_change(self.total())

    def total(self):
        return sum(self.cost.values())

    def allowed_for(self, free_nets):
        """Nodes not used by any net outside `free_nets`."""
        allowed = np.ones(self.g.N, dtype=bool)
        for j in self.nets:
            if j not in free_nets:
                allowed[list(self.nodes[j])] = False
        # terminals of the free nets other than the one being routed are
        # handled by the caller
        return allowed

    def set_tree(self, k, edges):
        self.trees[k] = set(edges)
        self.nodes[k] = tree_nodes(edges, self.terms[k])
        self.cost[k] = sum(self.g.adj[u][v] for (u, v) in edges)

    def polish_pass(self, log):
        """Exact re-optimisation of every net with the others fixed."""
        improved = False
        for k in self.nets:
            allowed = self.allowed_for({k})
            c, e = self.g.exact_tree(allowed, self.terms[k])
            if c is not None and c < self.cost[k]:
                log(f"  net {k}: {self.cost[k]} -> {c}")
                self.set_tree(k, e)
                self.note()
                improved = True
        return improved

    def reinsert(self, group, order, rng=None, noise=0.0):
        """Rip up `group` and route it exactly in `order`. Returns
        (total cost of the group, {net: edges}) or (None, None)."""
        allowed = self.allowed_for(set(group))
        out, tot = {}, 0
        for idx, k in enumerate(order):
            a = allowed.copy()
            for j in group:
                if j != k and j not in out:
                    a[list(self.terms[j])] = False
            nc = None
            if noise > 0 and idx < len(order) - 1 and rng is not None:
                nc = rng.random(self.g.N) * noise
            c, e = self.g.exact_tree(a, self.terms[k], nc)
            if c is None:
                return None, None
            out[k] = e
            tot += c
            allowed[list(tree_nodes(e, self.terms[k]))] = False
        return tot, out

    def touching(self):
        """Pairs of nets whose trees are adjacent in the grid."""
        nb = {}
        for k in self.nets:
            s = set()
            for u in self.nodes[k]:
                s.update(self.g.adj[u])
            nb[k] = s
        pairs = []
        for a, b in itertools.combinations(self.nets, 2):
            if nb[a] & self.nodes[b]:
                pairs.append((a, b))
        return pairs

    def snapshot(self):
        return {k: set(e) for k, e in self.trees.items()}

    def restore(self, snap):
        for k, e in snap.items():
            self.set_tree(k, e)

    def lns(self, seconds, rng, log, group_sizes=(2, 2, 3, 3, 4), noise_levels=(0.0, 0.3, 1.0),
            stale_limit=150):
        """Large neighbourhood search with occasional kicks. When no group
        move has paid off for `stale_limit` iterations the search accepts one
        random noisy re-insertion even if it is worse, polishes from there and
        keeps going. The best packing seen is restored at the end."""
        t0 = time.time()
        it = 0
        pairs = self.touching()
        best_total, best_snap = self.total(), self.snapshot()
        stale = 0
        kicks = 0
        while time.time() - t0 < seconds:
            it += 1
            size = int(rng.choice(group_sizes))
            if pairs and rng.random() < 0.8:
                a, b = pairs[rng.integers(len(pairs))]
                group = {a, b}
                while len(group) < size:
                    cands = [y for (x, y) in pairs if x in group and y not in group] + \
                            [x for (x, y) in pairs if y in group and x not in group]
                    if not cands:
                        break
                    group.add(cands[rng.integers(len(cands))])
            else:
                group = set(rng.choice(self.nets, size=min(size, len(self.nets)), replace=False).tolist())
            group = sorted(group)
            old = sum(self.cost[k] for k in group)
            best, best_trees = old, None
            orders = list(itertools.permutations(group))
            if len(orders) > 6:
                rng.shuffle(orders)
                orders = orders[:6]
            for order in orders:
                for noise in noise_levels:
                    tot, trees = self.reinsert(group, order, rng, noise)
                    if tot is not None and tot < best:
                        best, best_trees = tot, trees
            if best_trees is not None:
                for k, e in best_trees.items():
                    self.set_tree(k, e)
                self.note()
                while self.polish_pass(log):
                    pass
                pairs = self.touching()
                log(f"  lns it {it} group {group}: {old} -> {best}  total {self.total()}  t={time.time()-t0:.0f}s")
            if self.total() < best_total:
                best_total, best_snap = self.total(), self.snapshot()
                stale = 0
            else:
                stale += 1
            if stale >= stale_limit:
                # kick: a noisy re-insertion of a random group, accepted blindly
                size = int(rng.choice((2, 3)))
                group = sorted(rng.choice(self.nets, size=min(size, len(self.nets)), replace=False).tolist())
                order = list(group)
                rng.shuffle(order)
                tot, trees = self.reinsert(group, order, rng, noise=2.0)
                if trees is not None:
                    for k, e in trees.items():
                        self.set_tree(k, e)
                    while self.polish_pass(lambda *a: None):
                        pass
                    pairs = self.touching()
                    kicks += 1
                    log(f"  kick {kicks} at it {it}: total {self.total()} (best {best_total})")
                stale = 0
        if self.total() > best_total:
            self.restore(best_snap)
        log(f"  lns done: {it} iterations, {kicks} kicks, best {best_total}")
        return it


def improve(inst_dir, trees, seconds, seed, log=print, on_change=None):
    n_nodes, adj, terms = load_instance(inst_dir)
    grid = Grid(adj)
    pk = Packing(grid, terms, trees)
    pk.on_change = on_change
    pk.note()
    rng = np.random.default_rng(seed)
    log(f"start {pk.total()}")
    while pk.polish_pass(log):
        pass
    log(f"after exact polish {pk.total()}")
    if seconds > 0:
        its = pk.lns(seconds, rng, log)
        log(f"after lns ({its} iterations) {pk.total()}")
    return pk.trees, adj


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("instance_dir")
    ap.add_argument("sol_in")
    ap.add_argument("sol_out")
    ap.add_argument("--seconds", type=float, default=60.0)
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()
    trees = read_solution(a.sol_in)
    trees, adj = improve(a.instance_dir, trees, a.seconds, a.seed)
    c = write_solution(a.sol_out, trees, adj)
    print(f"wrote {a.sol_out} cost {c}")
