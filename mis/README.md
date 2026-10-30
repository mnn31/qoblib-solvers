# Independent set search for 07-independentset

Two searches for the maximum independent set instances in QOBLIB.

`frb_tabu.cpp` is for the frb instances (Xu's Model RB, the BHOSLIB set). Those
graphs are k cliques of d consecutive vertices, so an independent set of size k
is one vertex per clique with no edge between them. That is a binary CSP, and it
also proves that no independent set is larger than k. The search keeps a complete
assignment and minimises conflicting pairs with a tabu rule in the style of
Galinier and Hao (1997), plus constraint weights that go up on pairs in conflict
every so many iterations. New best assignments become independent sets through a
small exact vertex cover of their conflicts.

`numvc.cpp` is a plain graph local search after NuMVC (Cai, Su, Luo and Sattar,
JAIR 2013), used on the instances with no clique partition.

`check_clique_partition.py` checks the clique structure of a graph, which is the
whole optimality proof for an frb row whose value equals k.

    c++ -O3 -std=c++17 -march=native -o frb_tabu frb_tabu.cpp
    ./frb_tabu frb59-26-2.gph 59 26 out.sol 3000 11 59 2000
    python check_clique_partition.py frb59-26-2.gph 59 26

The arguments are graph, k, d, output, seconds, seed, target size and weight
period. A run is deterministic given its seed, apart from where the time limit
falls.

These are not state of the art. ULSA (Rosin 2014, arXiv:1411.7480) is faster on
these instances and reports 99 on frb100-40. Ugurlu (2026, arXiv:2609.02804,
preprint) reports a size 100 certificate for frb100-40.
