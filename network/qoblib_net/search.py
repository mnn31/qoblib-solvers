"""Metropolis search over topologies: simulated annealing and parallel tempering.

Both routines treat the topology as the state and the exact min-congestion LP
as the energy.  Moves are the degree-preserving exchanges from ``topology``, so
every state visited is a feasible 2-in/2-out digraph by construction and only
strong connectivity has to be re-checked.
"""

from __future__ import annotations

import math
import time

import numpy as np

from . import topology as topo
from .oracle import CongestionOracle


def anneal(n, demand, seconds=60.0, seed=0, start=None, t_hot=0.05, t_cold=0.0005,
           p_triple=0.15, on_improve=None):
    """Single-chain simulated annealing.  Temperatures are fractions of the
    starting energy, so the schedule transfers across instance sizes."""
    rng = np.random.default_rng(seed)
    orc = CongestionOracle(n, demand)

    cur = list(start) if start is not None else topo.random_topology(n, rng)
    cur_e = orc.energy(cur)
    while not math.isfinite(cur_e):
        cur = topo.random_topology(n, rng)
        cur_e = orc.energy(cur)

    best, best_e = list(cur), cur_e
    t0, t1 = t_hot * cur_e, t_cold * cur_e
    start_time = time.time()
    evals = 0

    while True:
        elapsed = time.time() - start_time
        if elapsed >= seconds:
            break
        temp = t0 * (t1 / t0) ** (elapsed / seconds)

        cand = topo.propose(cur, rng, p_triple)
        if cand is None or not topo.is_strongly_connected(n, cand):
            continue
        e = orc.energy(cand)
        evals += 1
        if not math.isfinite(e):
            continue
        if e <= cur_e or rng.random() < math.exp(-(e - cur_e) / temp):
            cur, cur_e = cand, e
            if e < best_e - 1e-6:
                best, best_e = list(cand), e
                if on_improve:
                    on_improve(best_e, elapsed)

    return {"arcs": best, "energy": best_e, "evals": evals,
            "seconds": time.time() - start_time, "seed": seed}


def parallel_tempering(n, demand, seconds=600.0, replicas=8, seed=0, start=None,
                       t_hot=0.06, t_cold=0.002, swap_every=40, p_triple=0.15,
                       on_improve=None):
    """Replica-exchange Metropolis.

    ``replicas`` chains sit on a geometric temperature ladder; every
    ``swap_every`` proposals adjacent chains attempt an exchange with the usual
    acceptance  min(1, exp((1/T_r - 1/T_{r+1}) (E_r - E_{r+1}))).  Hot chains
    supply diversity, the cold chain does the refining.
    """
    rng = np.random.default_rng(seed)
    orc = CongestionOracle(n, demand)

    if start is None:
        chains = [topo.random_topology(n, rng) for _ in range(replicas)]
    elif isinstance(start[0], tuple):        # one topology, replicated
        chains = [list(start) for _ in range(replicas)]
    else:                                    # explicit list of topologies
        chains = [list(s) for s in start]

    energies = [orc.energy(c) for c in chains]
    scale = min(e for e in energies if math.isfinite(e))
    temps = [scale * t_hot * (t_cold / t_hot) ** (r / max(1, replicas - 1))
             for r in range(replicas)][::-1]      # index 0 = coldest

    bi = min(range(replicas), key=lambda r: energies[r])
    best, best_e = list(chains[bi]), energies[bi]

    start_time = time.time()
    evals = props = swaps = 0
    # incumbent trajectory for time-to-solution analysis: (seconds, best-so-far),
    # recorded whenever the best improves.  The first entry is the starting
    # incumbent, so the series is non-increasing by construction.
    trajectory = [{"Time": 0.0, "Incumbent": math.ceil(best_e - 1e-6)}]

    while time.time() - start_time < seconds:
        for r in range(replicas):
            # check the budget per proposal, not per sweep, so a run cannot
            # drift past its wall-clock budget inside the replica loop
            if time.time() - start_time >= seconds:
                break
            cand = topo.propose(chains[r], rng, p_triple)
            props += 1
            if cand is None or not topo.is_strongly_connected(n, cand):
                continue
            e = orc.energy(cand)
            evals += 1
            if not math.isfinite(e):
                continue
            de = e - energies[r]
            if de <= 0 or rng.random() < math.exp(-de / temps[r]):
                chains[r], energies[r] = cand, e
                if e < best_e - 1e-6:
                    best, best_e = list(cand), e
                    now = time.time() - start_time
                    val = math.ceil(best_e - 1e-6)
                    if val < trajectory[-1]["Incumbent"]:
                        trajectory.append({"Time": round(now, 6), "Incumbent": val})
                    if on_improve:
                        on_improve(best_e, now)
        if props % swap_every < replicas:
            for r in range(replicas - 1):
                delta = (1.0 / temps[r] - 1.0 / temps[r + 1]) * (energies[r] - energies[r + 1])
                if delta >= 0 or rng.random() < math.exp(delta):
                    chains[r], chains[r + 1] = chains[r + 1], chains[r]
                    energies[r], energies[r + 1] = energies[r + 1], energies[r]
                    swaps += 1

    elapsed = time.time() - start_time
    # the last entry marks the end of the run, so time-to-solution is the Time of
    # the first entry whose Incumbent equals the final best
    if trajectory[-1]["Time"] < elapsed:
        trajectory.append({"Time": round(elapsed, 6),
                           "Incumbent": trajectory[-1]["Incumbent"]})
    return {"arcs": best, "energy": best_e, "evals": evals, "swaps": swaps,
            "seconds": elapsed, "seed": seed, "temps": temps,
            "trajectory": trajectory}
