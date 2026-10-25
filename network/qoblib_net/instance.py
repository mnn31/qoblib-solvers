"""Instance data for QOBLIB problem 08, Network Design.

The upstream benchmark ships a single hard-coded 24x24 demand matrix; instance
``networkNN`` is its leading NN x NN block.  All demands are multiplied by
INTSCALE = 1000, matching ``08-network/models/integer_lp/d3ver0int.zpl``.
"""

from __future__ import annotations

import numpy as np

INTSCALE = 1000

#: Reference best-known values published in 08-network/solutions/0-info.txt.
#: network05..network10 are proven optimal; the rest are upper bounds only.
BKV = {5: 65500, 6: 101000, 7: 142400, 8: 170231, 9: 196750, 10: 210800,
       11: 238334, 12: 276474, 13: 300620, 14: 343091, 15: 370870,
       16: 397908, 17: 437000, 18: 473375, 19: 492924, 20: 528528,
       21: 569273, 22: 618135, 23: 659369, 24: 663688}
# best known table of ZIB-AOPT/QOBLIB main as of 2026-10-25 (network11 to
# network23 hold this method's own 2026-08-18 values)

PROVEN_OPTIMAL = {5, 6, 7, 8, 9, 10}


def parse_demand(path: str, n: int) -> np.ndarray:
    """Read the QOBLIB demand file and return its leading n x n block (0-indexed).

    Mirrors ``parse_demand_file`` in the official Rust checker.
    """
    rows = []
    for line in open(path):
        line = line.strip()
        if not line.startswith("|"):
            continue
        parts = [p.strip() for p in line.strip("|").split(",")]
        if "|" not in parts[0]:          # column-header row
            continue
        parts[0] = parts[0].split("|", 1)[1].strip()
        rows.append([int(p) for p in parts])
    full = np.array(rows, dtype=np.int64)
    if full.shape != (24, 24):
        raise ValueError(f"expected a 24x24 demand matrix, got {full.shape}")
    return full[:n, :n]


def lower_bounds(n: int, demand: np.ndarray) -> dict:
    """Two cheap combinatorial lower bounds on the maximum arc load.

    ``degree`` -- everything originating at (or destined for) a node must cross
    that node's two out-arcs (in-arcs), so some arc carries at least half of the
    largest row/column sum.

    ``volume`` -- every unit of demand occupies at least one of the 2n arcs.
    """
    out_total = demand.sum(axis=1)
    in_total = demand.sum(axis=0)
    lb_deg = max(out_total.max(), in_total.max()) / 2.0 * INTSCALE
    lb_vol = demand.sum() / (2.0 * n) * INTSCALE
    return {"degree": lb_deg, "volume": lb_vol, "best": max(lb_deg, lb_vol)}
