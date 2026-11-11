"""Inner problem: route the demand on a fixed topology to minimise congestion.

Given the arc set, choosing the flow is a min-congestion multicommodity flow
problem.  It is an LP, and on this instance family the LP optimum coincides
with the integral optimum up to the 1/1000 scaling (verified against every
published reference solution), so the search uses the LP value as its energy
and an integral routing is recovered once, at the end.
"""

from __future__ import annotations

import numpy as np
import highspy

from .instance import INTSCALE

INF = highspy.kHighsInf


def _build_rows(n, arcs, d):
    """Column layout: f[k, arc] for every commodity k and arc whose head != k, then z."""
    col, c = {}, 0
    for k in range(n):
        for ai, (u, v) in enumerate(arcs):
            if v == k:
                continue
            col[(k, ai)] = c
            c += 1
    zcol, ncols = c, c + 1

    starts, idx, val, rlo, rhi = [], [], [], [], []

    def add_row(entries, lo, hi):
        starts.append(len(idx))
        for cc, vv in entries:
            idx.append(cc)
            val.append(vv)
        rlo.append(lo)
        rhi.append(hi)

    # conservation: net inflow of commodity k at node i equals the demand d[k,i]
    for k in range(n):
        for i in range(n):
            if i == k:
                continue
            ent = {}
            for ai, (u, v) in enumerate(arcs):
                cc = col.get((k, ai))
                if cc is None:
                    continue
                if v == i:
                    ent[cc] = ent.get(cc, 0.0) + 1.0
                if u == i:
                    ent[cc] = ent.get(cc, 0.0) - 1.0
            add_row(list(ent.items()), d[k, i], d[k, i])
    # congestion: total load on each arc is at most z
    for ai in range(len(arcs)):
        ent = [(col[(k, ai)], 1.0) for k in range(n) if (k, ai) in col]
        ent.append((zcol, -1.0))
        add_row(ent, -INF, 0.0)

    return col, zcol, ncols, starts, idx, val, rlo, rhi


class CongestionOracle:
    """Exact min-congestion routing for a given topology.

    ``energy`` returns the LP value (fast, used inside the search).
    ``integral`` returns a certified integral routing (used to emit a solution).
    """

    def __init__(self, n: int, demand: np.ndarray):
        self.n = n
        self.d = demand.astype(float) * INTSCALE

    def _model(self, arcs, integral: bool):
        n = self.n
        col, zcol, ncols, starts, idx, val, rlo, rhi = _build_rows(n, arcs, self.d)
        h = highspy.Highs()
        h.setOptionValue("output_flag", False)
        h.setOptionValue("presolve", "off")
        h.setOptionValue("threads", 1)
        cost = np.zeros(ncols)
        cost[zcol] = 1.0
        h.addVars(ncols, np.zeros(ncols), np.full(ncols, INF))
        h.changeColsCost(ncols, np.arange(ncols, dtype=np.int32), cost)
        h.addRows(len(rlo), np.array(rlo), np.array(rhi), len(idx),
                  np.array(starts, dtype=np.int32),
                  np.array(idx, dtype=np.int32), np.array(val))
        if integral:
            h.changeColsIntegrality(
                ncols, np.arange(ncols, dtype=np.int32),
                np.full(ncols, highspy.HighsVarType.kInteger))
        return h, col, zcol

    def energy(self, arcs) -> float:
        h, _, zcol = self._model(arcs, integral=False)
        h.run()
        if h.getModelStatus() != highspy.HighsModelStatus.kOptimal:
            return float("inf")
        return h.getSolution().col_value[zcol]

    def integral(self, arcs, time_limit: float = 300.0):
        """Returns (z, flow_values, column_index_map) with every flow an integer."""
        h, col, zcol = self._model(arcs, integral=True)
        h.setOptionValue("time_limit", time_limit)
        h.setOptionValue("mip_rel_gap", 0.0)
        h.run()
        st = h.getModelStatus()
        if st not in (highspy.HighsModelStatus.kOptimal,
                      highspy.HighsModelStatus.kTimeLimit):
            return float("inf"), None, None
        sol = h.getSolution()
        if not sol.value_valid:
            return float("inf"), None, None
        return sol.col_value[zcol], np.array(sol.col_value), col
