"""Negotiated-congestion rip-up-and-reroute for QOBLIB 04-steiner.

Node-disjoint Steiner tree packing on the QOBLIB multi-layer grid instances.
PathFinder-style: every net is routed by a greedy Steiner heuristic (repeated
multi-source Dijkstra from the partial tree to the nearest unconnected terminal)
on node costs that grow with present and historical overuse. Iterate until no
node is shared by two nets, then prune non-terminal leaves and do a few
cost-reducing reroute passes with other nets' nodes forbidden.

Usage:
    python route.py <instance_dir> <out.sol> [--seed N] [--max-iter N] [--polish N]

Output format matches check_steiner: one "u v net" line per tree edge.
"""
import sys
import heapq
import random
import time
import argparse
from collections import defaultdict


def read_lines(path):
    with open(path) as f:
        for line in f:
            s = line.strip()
            if s and not s.startswith("#"):
                yield s.split()


def load_instance(d):
    n_nodes = None
    for t in read_lines(f"{d}/param.dat"):
        if t[0] == "nodes":
            n_nodes = int(t[1])
    adj = defaultdict(dict)
    for t in read_lines(f"{d}/arcs.dat"):
        u, v, c = int(t[0]), int(t[1]), int(t[2])
        adj[u][v] = c
        adj[v][u] = c
    terms = defaultdict(list)
    for t in read_lines(f"{d}/terms.dat"):
        terms[int(t[1])].append(int(t[0]))
    return n_nodes, adj, terms


def steiner_tree(adj, terminals, node_cost, forbidden, rng):
    """Greedy Steiner tree. Returns set of undirected edges (min,max) and node set.

    node_cost: dict node -> additive cost for entering that node (congestion).
    forbidden: set of nodes that cannot be used (other nets' terminals).
    """
    terminals = list(terminals)
    rng.shuffle(terminals)
    tree_nodes = {terminals[0]}
    tree_edges = set()
    remaining = set(terminals[1:])
    while remaining:
        # multi-source Dijkstra from tree_nodes to nearest remaining terminal
        dist = {u: 0.0 for u in tree_nodes}
        prev = {}
        pq = [(0.0, u) for u in tree_nodes]
        heapq.heapify(pq)
        target = None
        while pq:
            dcur, u = heapq.heappop(pq)
            if dcur > dist.get(u, float("inf")):
                continue
            if u in remaining:
                target = u
                break
            for v, c in adj[u].items():
                if v in forbidden and v not in remaining:
                    continue
                nd = dcur + c + node_cost.get(v, 0.0)
                if nd < dist.get(v, float("inf")):
                    dist[v] = nd
                    prev[v] = u
                    heapq.heappush(pq, (nd, v))
        if target is None:
            return None, None
        # walk back
        u = target
        while u not in tree_nodes:
            p = prev[u]
            tree_edges.add((min(u, p), max(u, p)))
            tree_nodes.add(u)
            u = p
        remaining.discard(target)
    return tree_edges, tree_nodes


def prune(tree_edges, terminals):
    """Remove non-terminal leaves repeatedly."""
    deg = defaultdict(int)
    inc = defaultdict(set)
    for (u, v) in tree_edges:
        deg[u] += 1
        deg[v] += 1
        inc[u].add((u, v))
        inc[v].add((u, v))
    tset = set(terminals)
    edges = set(tree_edges)
    stack = [u for u in deg if deg[u] == 1 and u not in tset]
    while stack:
        u = stack.pop()
        if u in tset or deg[u] != 1:
            continue
        (e,) = tuple(inc[u])
        edges.discard(e)
        inc[u].discard(e)
        w = e[0] if e[1] == u else e[1]
        inc[w].discard(e)
        deg[u] -= 1
        deg[w] -= 1
        if deg[w] == 1 and w not in tset:
            stack.append(w)
    nodes = set()
    for (u, v) in edges:
        nodes.add(u)
        nodes.add(v)
    nodes |= tset
    return edges, nodes


def route(d, seed=0, max_iter=200, polish=3, log=print):
    rng = random.Random(seed)
    n_nodes, adj, terms = load_instance(d)
    nets = sorted(terms)
    term_owner = {}
    for k in nets:
        for t in terms[k]:
            term_owner[t] = k
    all_terms = set(term_owner)

    pres_fac = 0.5
    hist = defaultdict(float)
    trees = {}
    nodes_of = {}
    t0 = time.time()
    # Some seeds stall with one or two nodes that two nets both insist on,
    # while the pressure factor grows without bound. After a stall of this
    # kind, one of the nets through a contested node is forced to detour
    # around it, which breaks the tie the penalties cannot.
    stall = 0
    forced = defaultdict(set)
    for it in range(max_iter):
        # occupancy from current trees
        occ = defaultdict(int)
        for k in nets:
            for u in nodes_of.get(k, ()):
                occ[u] += 1
        for k in nets:
            # rip up net k
            for u in nodes_of.get(k, ()):
                occ[u] -= 1
            node_cost = {}
            for u, c in occ.items():
                if c > 0:
                    node_cost[u] = pres_fac * c + hist[u]
            forbidden = (all_terms - set(terms[k])) | forced[k]
            e, nn = steiner_tree(adj, terms[k], node_cost, forbidden, rng)
            if e is None and forced[k]:
                forced[k].clear()
                forbidden = all_terms - set(terms[k])
                e, nn = steiner_tree(adj, terms[k], node_cost, forbidden, rng)
            if e is None:
                raise RuntimeError(f"net {k} unroutable")
            e, nn = prune(e, terms[k])
            trees[k] = e
            nodes_of[k] = nn
            for u in nn:
                occ[u] += 1
        over = [u for u, c in occ.items() if c > 1]
        for u in over:
            hist[u] += 1.0
        cost = sum(adj[u][v] for k in nets for (u, v) in trees[k])
        log(f"iter {it:3d} overused {len(over):5d} cost {cost} pres {pres_fac:.2f} t={time.time()-t0:.1f}s")
        if not over:
            break
        pres_fac = min(pres_fac * 1.5, 1e6)
        stall = stall + 1 if len(over) <= 3 else 0
        if stall >= 15:
            u = rng.choice(over)
            users = [k for k in nets if u in nodes_of.get(k, ())]
            if users:
                forced[rng.choice(users)].add(u)
            stall = 0
    else:
        return None, None

    # polish: reroute each net with others' nodes forbidden, keep if cheaper
    for p in range(polish):
        improved = False
        for k in nets:
            used_others = set()
            for j in nets:
                if j != k:
                    used_others |= nodes_of[j]
            old = sum(adj[u][v] for (u, v) in trees[k])
            best_e, best_c = trees[k], old
            for _ in range(4):
                e, nn = steiner_tree(adj, terms[k], {}, used_others | (all_terms - set(terms[k])), rng)
                if e is None:
                    continue
                e, nn = prune(e, terms[k])
                c = sum(adj[u][v] for (u, v) in e)
                if c < best_c:
                    best_e, best_c = e, c
            if best_c < old:
                trees[k] = best_e
                nodes_of[k] = prune(best_e, terms[k])[1]
                improved = True
        cost = sum(adj[u][v] for k in nets for (u, v) in trees[k])
        log(f"polish {p} cost {cost}")
        if not improved:
            break
    return trees, adj


def write_solution(path, trees, adj):
    cost = sum(adj[u][v] for k in trees for (u, v) in trees[k])
    with open(path, "w") as f:
        f.write(f"# Cost: {cost}\n")
        for k in sorted(trees):
            for (u, v) in sorted(trees[k]):
                f.write(f"{u} {v} {k}\n")
    return cost


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("instance_dir")
    ap.add_argument("out")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--max-iter", type=int, default=200)
    ap.add_argument("--polish", type=int, default=3)
    a = ap.parse_args()
    trees, adj = route(a.instance_dir, a.seed, a.max_iter, a.polish)
    if trees is None:
        print("FAILED: did not converge")
        sys.exit(1)
    c = write_solution(a.out, trees, adj)
    print(f"wrote {a.out} cost {c}")
