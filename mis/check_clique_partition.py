#!/usr/bin/env python3
"""Checks that a graph is k cliques of d consecutive vertices, which proves that
no independent set has more than k vertices.
    python check_clique_partition.py <graph.gph> <k> <d>"""
import sys
path, k, d = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
edges, n = set(), None
for line in open(path):
    if line.startswith("p"):
        n = int(line.split()[2])
    elif line.startswith("e"):
        _, a, b = line.split()
        a, b = int(a) - 1, int(b) - 1
        if a != b:
            edges.add((min(a, b), max(a, b)))
if n != k * d:
    sys.exit(f"{n} vertices is not {k} times {d}")
missing = sum(1 for g in range(k) for a in range(g * d, (g + 1) * d) for b in range(a + 1, (g + 1) * d) if (a, b) not in edges)
if missing:
    sys.exit(f"{missing} edges missing inside the cliques")
print(f"{path}: {k} cliques of {d} vertices, so every independent set has at most {k} vertices")
