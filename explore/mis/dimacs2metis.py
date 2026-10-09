#!/usr/bin/env python3
"""Convert a DIMACS clique-format graph (p edge n m / e u v) to METIS format
for KaMIS. Duplicate and reversed edge listings are merged; self loops dropped.
Usage: dimacs2metis.py in.gph out.graph"""
import sys
src, dst = sys.argv[1], sys.argv[2]
n = 0; adj = None
for line in open(src):
    if line.startswith("p"):
        n = int(line.split()[2]); adj = [set() for _ in range(n + 1)]
    elif line.startswith("e"):
        _, u, v = line.split(); u, v = int(u), int(v)
        if u != v:
            adj[u].add(v); adj[v].add(u)
m = sum(len(a) for a in adj[1:]) // 2
with open(dst, "w") as f:
    f.write(f"{n} {m}\n")
    for i in range(1, n + 1):
        f.write(" ".join(map(str, sorted(adj[i]))) + "\n")
print(f"{src}: n={n} m={m}")
