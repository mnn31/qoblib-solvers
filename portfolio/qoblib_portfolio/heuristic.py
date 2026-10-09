"""Restricted-state chain heuristic for QOBLIB problem 06 (large instances).

The exact solver in ``solver.py`` enumerates every feasible per-period
portfolio and runs a dynamic program over the chain of periods.  That is
impossible from a050 upwards (100 to 800 groups, budgets 20 to 100).  This
module keeps the chain structure but replaces the full state set with a small
pool of good candidate portfolios per period:

1. Per-period local search.  Each period on its own is a small integer convex
   quadratic program (the risk matrix is a scaled covariance, so it is PSD).
   We run a best-improvement local search with add, remove and swap moves,
   evaluating every move exactly in integers from the incremental gradient
   ``q = R u``.  Neighbouring periods enter as "anchors": the rebalancing cost
   ``delta_t . |u - v|`` is separable, so its change under a unit move is a
   sign times ``delta_t[g]`` and stays exact.
2. Candidate pools.  For every period we collect the independent local
   optimum, kicked restarts, and local optima pulled towards candidates of the
   neighbouring periods (forward and backward sweeps), so that the chain DP has
   cheap rebalancing options available.
3. Restricted chain DP.  The exact chain recursion of ``solve_exact`` is run
   over the pools (K states per period instead of all feasible states), using
   ``Coefficients.period_cost`` for the state costs and the same integer
   rebalancing cost, so every value is exact for the reference model.
4. Coordinate descent.  The DP schedule is refined period by period with the
   neighbours fixed; the refined states are added to the pools and steps 3 and
   4 repeat for a few rounds, with random kicks for diversification.

Everything is integer arithmetic on the coefficients built by
``model.Coefficients``, so the value reported here is exactly what the official
checker computes.  The final schedule is always re-evaluated with
``solver.objective`` before it is returned.
"""

from __future__ import annotations

import time

import numpy as np

from .model import Coefficients
from .solver import objective

BIG = np.int64(1) << np.int64(60)


class PeriodModel:
    """Everything needed to evaluate moves inside one period exactly."""

    def __init__(self, coef: Coefficients, t: int):
        self.t = t
        G = coef.G
        self.G = G
        self.quad = coef.lam != 0
        self.R = coef.risk[t] if self.quad else None
        self.diag = self.R.diagonal().copy() if self.quad else np.zeros(G, dtype=np.int64)
        lin = coef.short[t].astype(np.int64).copy()
        if t < coef.t_end:
            lin -= coef.ret[t]
        if t == 0:
            lin += coef.delta[0]
        if t == coef.t_end:
            lin += coef.delta[coef.t_end]
        self.lin = lin
        self.tau = coef.tau.astype(np.int64)
        self.ub = int(coef.ub)
        self.B = int(coef.budget)
        self.lo_total = max(0, self.B - ((1 << coef.cs2) - 1))
        self.capital = int(coef.capital)
        self.smax = (1 << coef.cs1) - 1
        # cash bonus for each slack value, evaluated bit by bit like the model
        cashval = np.zeros(self.smax + 1, dtype=np.int64)
        for s in range(self.smax + 1):
            cashval[s] = sum(int(coef.cash[k]) for k in range(coef.cs1) if (s >> k) & 1)
        self.cashval = cashval
        # swap (g, h) changes net by tau_g - tau_h in {-2, 0, 2}; index 0, 1, 2
        self.didx = ((self.tau[:, None] - self.tau[None, :]) + 2) // 2
        # pair add (g, h) changes net by tau_g + tau_h, same index convention
        self.sidx = ((self.tau[:, None] + self.tau[None, :]) + 2) // 2
        self.eye = np.eye(G, dtype=bool)

    # ------------------------------------------------------------------
    def feasible(self, u: np.ndarray) -> bool:
        if u.min() < 0 or u.max() > self.ub:
            return False
        total = int(u.sum())
        if total < self.lo_total or total > self.B:
            return False
        slack = self.capital - int(u @ self.tau)
        return 0 <= slack <= self.smax

    def cash_change(self, slack: int, d: int) -> int:
        """Cost change of the cash term when the net position changes by d."""
        ns = slack - d
        if ns < 0 or ns > self.smax:
            return int(BIG)
        return int(self.cashval[slack] - self.cashval[ns])

    # ------------------------------------------------------------------
    def local_search(self, u0: np.ndarray, anchors=(), max_iter: int | None = None,
                     linear: bool = False, forbid: np.ndarray | None = None,
                     risk_scale: tuple[int, int] | None = None) -> np.ndarray:
        """Best-improvement local search on period cost plus anchor terms.

        ``anchors`` is a sequence of (w, v): adds ``sum_g w[g] * |u[g] - v[g]|``
        to the objective, the exact rebalancing cost towards neighbour v.
        ``linear`` drops the risk term (used only to build diverse starts).
        ``forbid`` is a boolean mask of groups that may not be increased.
        ``risk_scale`` = (num, den) runs the search on the risk matrix scaled by
        num/den (floor), a continuation start; the pool re-evaluates exactly.
        Returns a feasible local optimum (add, remove, swap, pair add, pair
        remove neighbourhood).
        """
        G, tau = self.G, self.tau
        u = u0.astype(np.int64).copy()
        assert self.feasible(u), "local_search needs a feasible start"
        quad = self.quad and not linear
        R, diag = self.R, self.diag
        if quad and risk_scale is not None and risk_scale[0] != risk_scale[1]:
            R = (self.R * risk_scale[0]) // risk_scale[1]
            diag = R.diagonal().copy()
        q = R @ u if quad else None
        total = int(u.sum())
        slack = self.capital - int(u @ tau)
        if max_iter is None:
            max_iter = 20 * self.B + 400
        anchors = [(np.asarray(w, dtype=np.int64), np.asarray(v, dtype=np.int64)) for w, v in anchors]
        allow = np.ones(G, dtype=bool) if forbid is None else ~np.asarray(forbid, dtype=bool)

        for _ in range(max_iter):
            if quad:
                base_add = diag + 2 * q + self.lin
                base_rem = diag - 2 * q - self.lin
            else:
                base_add = self.lin.copy()
                base_rem = -self.lin
            for w, v in anchors:
                base_add = base_add + np.where(u >= v, w, -w)
                base_rem = base_rem + np.where(u <= v, w, -w)

            # cash change by net move d, for d in {-2, -1, 0, 1, 2}
            cd = {d: self.cash_change(slack, d) for d in (-2, -1, 0, 1, 2)}
            cash_add = np.where(tau > 0, cd[1], cd[-1]).astype(np.int64)
            cash_rem = np.where(tau > 0, cd[-1], cd[1]).astype(np.int64)

            best_gain, best_move = 0, None
            if total < self.B:
                add = base_add + cash_add
                add = np.where((u < self.ub) & allow, add, BIG)
                g = int(add.argmin())
                if add[g] < best_gain:
                    best_gain, best_move = int(add[g]), ("add", g)
            if total > self.lo_total:
                rem = base_rem + cash_rem
                rem = np.where(u > 0, rem, BIG)
                h = int(rem.argmin())
                if rem[h] < best_gain:
                    best_gain, best_move = int(rem[h]), ("rem", h)

            if best_move is None:
                # two-unit moves, needed because a hedged long/short pair can be
                # profitable while each leg alone is not (and the net cap can
                # force a long to come with a short)
                can_add = (u < self.ub) & allow
                can_rem = (u > 0)
                # swap: add one unit of g, remove one unit of h
                cdv = np.array([cd[-2], cd[0], cd[2]], dtype=np.int64)
                sw = base_add[:, None] + base_rem[None, :] + cdv[self.didx]
                if quad:
                    sw = sw - 2 * R
                sw = np.where(can_add[:, None] & can_rem[None, :] & ~self.eye, sw, BIG)
                flat = int(sw.argmin())
                g, h = divmod(flat, G)
                if sw[g, h] < best_gain:
                    best_gain, best_move = int(sw[g, h]), ("swap", g, h)
                if total + 2 <= self.B:
                    pa = base_add[:, None] + base_add[None, :] + cdv[self.sidx]
                    if quad:
                        pa = pa + 2 * R
                    pa = np.where(can_add[:, None] & can_add[None, :] & ~self.eye, pa, BIG)
                    flat = int(pa.argmin())
                    g, h = divmod(flat, G)
                    if pa[g, h] < best_gain:
                        best_gain, best_move = int(pa[g, h]), ("add2", g, h)
                if total - 2 >= self.lo_total:
                    cdr = np.array([cd[2], cd[0], cd[-2]], dtype=np.int64)
                    pr = base_rem[:, None] + base_rem[None, :] + cdr[self.sidx]
                    if quad:
                        pr = pr + 2 * R
                    pr = np.where(can_rem[:, None] & can_rem[None, :] & ~self.eye, pr, BIG)
                    flat = int(pr.argmin())
                    g, h = divmod(flat, G)
                    if pr[g, h] < best_gain:
                        best_gain, best_move = int(pr[g, h]), ("rem2", g, h)

            if best_move is None:
                break
            kind = best_move[0]
            if kind == "add":
                g = best_move[1]
                u[g] += 1
                total += 1
                slack -= int(tau[g])
                if quad:
                    q += R[:, g]
            elif kind == "rem":
                h = best_move[1]
                u[h] -= 1
                total -= 1
                slack += int(tau[h])
                if quad:
                    q -= R[:, h]
            elif kind == "swap":
                g, h = best_move[1], best_move[2]
                u[g] += 1
                u[h] -= 1
                slack -= int(tau[g] - tau[h])
                if quad:
                    q += R[:, g] - R[:, h]
            elif kind == "add2":
                g, h = best_move[1], best_move[2]
                u[g] += 1
                u[h] += 1
                total += 2
                slack -= int(tau[g] + tau[h])
                if quad:
                    q += R[:, g] + R[:, h]
            else:
                g, h = best_move[1], best_move[2]
                u[g] -= 1
                u[h] -= 1
                total -= 2
                slack += int(tau[g] + tau[h])
                if quad:
                    q -= R[:, g] + R[:, h]
        return u

    def repair(self, u: np.ndarray) -> np.ndarray:
        """Restore feasibility after units were dropped, by removing units of the
        opposite direction with the smallest removal cost.  Totals only shrink."""
        u = u.astype(np.int64).copy()
        for _ in range(4 * self.G):
            slack = self.capital - int(u @ self.tau)
            if 0 <= slack <= self.smax:
                break
            want_short = slack > self.smax     # net too low: drop a short unit
            gains = self.removal_gains(u, ignore_cash=True)
            gains = np.where((self.tau < 0) == want_short, gains, BIG)
            g = int(gains.argmin())
            assert gains[g] < BIG, "repair failed"
            u[g] -= 1
        assert self.feasible(u)
        return u

    def removal_gains(self, u: np.ndarray, ignore_cash: bool = False) -> np.ndarray:
        """Exact period-cost change of removing one unit of each group (BIG if not allowed).

        ``ignore_cash`` drops the cash term, for use on infeasible states during repair."""
        u = u.astype(np.int64)
        slack = self.capital - int(u @ self.tau)
        q = self.R @ u if self.quad else np.zeros(self.G, dtype=np.int64)
        rem = self.diag - 2 * q - self.lin
        if not ignore_cash:
            cd = {d: self.cash_change(slack, d) for d in (-1, 1)}
            rem = rem + np.where(self.tau > 0, cd[-1], cd[1])
        ok = (u > 0) & (int(u.sum()) - 1 >= self.lo_total)
        return np.where(ok, rem, BIG)

    # ------------------------------------------------------------------
    def cost(self, u: np.ndarray, anchors=()) -> int:
        """Exact period cost plus anchor terms (same integers as period_cost)."""
        u = u.astype(np.int64)
        c = int(u @ self.lin)
        if self.quad:
            c += int(u @ (self.R @ u))
        slack = self.capital - int(u @ self.tau)
        c -= int(self.cashval[slack])
        for w, v in anchors:
            c += int(np.abs(u - v) @ w)
        return c

    _grids: dict = {}

    @classmethod
    def _grid(cls, k: int, ub: int) -> np.ndarray:
        key = (k, ub)
        if key not in cls._grids:
            g = np.indices((ub + 1,) * k).reshape(k, -1).T
            cls._grids[key] = np.ascontiguousarray(g, dtype=np.int64)
        return cls._grids[key]

    def solve_subset(self, u: np.ndarray, idx: np.ndarray, anchors=()):
        """Exact optimum over the groups in idx with all other groups fixed.

        Enumerates every assignment in {0..ub}^k, evaluates all of them in
        one vectorized exact integer computation, and returns (new_u, cost)."""
        idx = np.asarray(idx, dtype=np.int64)
        k = len(idx)
        V = self._grid(k, self.ub)
        uF = u.astype(np.int64).copy()
        uF[idx] = 0
        total_F = int(uF.sum())
        net_F = int(uF @ self.tau)
        totals = total_F + V.sum(axis=1)
        slack = self.capital - (net_F + V @ self.tau[idx])
        ok = (totals <= self.B) & (totals >= self.lo_total) & (slack >= 0) & (slack <= self.smax)
        lin = self.lin[idx].copy()
        cost = np.zeros(len(V), dtype=np.int64)
        if self.quad:
            RII = self.R[np.ix_(idx, idx)]
            lin = lin + 2 * (self.R[idx] @ uF)
            cost += np.einsum("sa,ab,sb->s", V, RII, V)
        cost += V @ lin
        for w, v in anchors:
            cost += np.abs(V - v[idx][None, :]) @ w[idx]
        cost -= self.cashval[np.clip(slack, 0, self.smax)]
        cost = np.where(ok, cost, BIG)
        best = int(cost.argmin())
        new = uF.copy()
        new[idx] = V[best]
        return new, self.cost(new, anchors)

    def choose_subset(self, u: np.ndarray, k: int, rng: np.random.Generator, mode: int) -> np.ndarray:
        """Pick k groups to free: a risk-coupling cluster around a held group,
        or held groups plus the best groups to add, or random."""
        G = self.G
        support = np.flatnonzero(u > 0)
        chosen: list[int] = []
        if mode == 0 and self.quad and len(support):
            g = int(rng.choice(support))
            chosen.append(g)
            coupling = np.abs(self.R[g]).astype(np.int64)
            coupling[g] = -1
            for h in np.argsort(-coupling, kind="stable")[: k - 1]:
                chosen.append(int(h))
        elif mode == 1 and len(support):
            take = min(len(support), max(1, k // 2))
            chosen += [int(g) for g in rng.choice(support, size=take, replace=False)]
            q = self.R @ u if self.quad else np.zeros(G, dtype=np.int64)
            add = self.diag + 2 * q + self.lin
            add[u >= self.ub] = BIG
            for h in np.argsort(add, kind="stable"):
                if len(chosen) >= k:
                    break
                if int(h) not in chosen:
                    chosen.append(int(h))
        elif mode == 2 and len(support):
            # whole assets (long and short group together) from the support
            assets = sorted({int(g) // 2 for g in support})
            rng.shuffle(assets)
            for i in assets:
                if len(chosen) + 2 > k:
                    break
                chosen += [2 * i, 2 * i + 1]
            q = self.R @ u if self.quad else np.zeros(G, dtype=np.int64)
            add = self.diag + 2 * q + self.lin
            for h in np.argsort(add, kind="stable"):
                if len(chosen) >= k:
                    break
                if int(h) not in chosen:
                    chosen.append(int(h))
        while len(chosen) < min(k, G):
            h = int(rng.integers(G))
            if h not in chosen:
                chosen.append(h)
        return np.array(chosen[:k], dtype=np.int64)

    def lns(self, u0: np.ndarray, anchors=(), rng: np.random.Generator | None = None,
            iters: int = 30, k: int = 7) -> np.ndarray:
        """Exact large-neighbourhood polishing: repeatedly free k groups and
        re-solve them exactly.  Escapes hedge clusters that unit moves cannot
        dissolve (removing any one leg of a hedge looks worse, removing the
        whole hedge is better)."""
        if rng is None:
            rng = np.random.default_rng(0)
        anchors = [(np.asarray(w, dtype=np.int64), np.asarray(v, dtype=np.int64)) for w, v in anchors]
        u = u0.astype(np.int64).copy()
        cur = self.cost(u, anchors)
        k = min(k, self.G)
        for it in range(iters):
            idx = self.choose_subset(u, k, rng, it % 4)
            new, c = self.solve_subset(u, idx, anchors)
            if c < cur:
                u, cur = new, c
                u = self.local_search(u, anchors)
                cur = self.cost(u, anchors)
        return u

    # ------------------------------------------------------------------
    def kick(self, u0: np.ndarray, k: int, rng: np.random.Generator) -> np.ndarray:
        """Apply k random feasible unit moves (swaps mostly) for diversification."""
        u = u0.astype(np.int64).copy()
        tau = self.tau
        for _ in range(k):
            total = int(u.sum())
            slack = self.capital - int(u @ tau)
            r = rng.random()
            if r < 0.6 and total > 0:
                src = np.flatnonzero(u > 0)
                dst = np.flatnonzero(u < self.ub)
                for _try in range(20):
                    h = int(rng.choice(src))
                    g = int(rng.choice(dst))
                    if g == h:
                        continue
                    ns = slack - int(tau[g] - tau[h])
                    if 0 <= ns <= self.smax:
                        u[g] += 1
                        u[h] -= 1
                        break
            elif r < 0.8 and total < self.B:
                dst = np.flatnonzero(u < self.ub)
                for _try in range(20):
                    g = int(rng.choice(dst))
                    ns = slack - int(tau[g])
                    if 0 <= ns <= self.smax:
                        u[g] += 1
                        break
            elif total > self.lo_total:
                src = np.flatnonzero(u > 0)
                if len(src) == 0:
                    continue
                for _try in range(20):
                    h = int(rng.choice(src))
                    ns = slack + int(tau[h])
                    if 0 <= ns <= self.smax:
                        u[h] -= 1
                        break
        assert self.feasible(u)
        return u


# ----------------------------------------------------------------------
class Pools:
    """Per-period candidate states with exact period costs, deduplicated."""

    def __init__(self, coef: Coefficients):
        self.coef = coef
        self.keys = [dict() for _ in range(coef.T)]
        self.states = [[] for _ in range(coef.T)]
        self.costs = [[] for _ in range(coef.T)]

    def add(self, t: int, u: np.ndarray) -> bool:
        key = u.tobytes()
        if key in self.keys[t]:
            return False
        self.keys[t][key] = len(self.states[t])
        self.states[t].append(u.astype(np.int64).copy())
        self.costs[t].append(int(self.coef.period_cost(t, u[None, :])[0]))
        return True

    def matrix(self, t: int) -> np.ndarray:
        return np.stack(self.states[t])

    def cost_array(self, t: int) -> np.ndarray:
        return np.array(self.costs[t], dtype=np.int64)

    def best(self, t: int, k: int) -> list[np.ndarray]:
        order = np.argsort(self.cost_array(t), kind="stable")[:k]
        return [self.states[t][i] for i in order]

    def size(self) -> int:
        return sum(len(s) for s in self.states)


def restricted_dp(coef: Coefficients, pools: Pools):
    """Exact chain DP over the candidate pools.  Returns (value, (T, G) schedule)."""
    T, t_end = coef.T, coef.t_end
    S = [pools.matrix(t) for t in range(T)]
    C = [pools.cost_array(t) for t in range(T)]

    last_arg = int(C[t_end].argmin())
    best_last = int(C[t_end][last_arg])
    out = np.zeros((T, coef.G), dtype=np.int64)
    out[t_end] = S[t_end][last_arg]
    if T == 1:
        return best_last, out

    f = C[0].copy()
    back = []
    for t in range(1, t_end):
        d = coef.delta[t]
        trans = np.abs(S[t][:, None, :] - S[t - 1][None, :, :]) @ d   # (K_t, K_{t-1})
        tot = trans + f[None, :]
        back.append(tot.argmin(axis=1))
        f = tot.min(axis=1) + C[t]
    s = int(f.argmin())
    value = int(f[s]) + best_last
    for t in range(t_end - 1, -1, -1):
        out[t] = S[t][s]
        if t > 0:
            s = int(back[t - 1][s])
    return value, out


def anchors_for(coef: Coefficients, U: np.ndarray, t: int):
    """Rebalancing anchors of period t given the rest of schedule U."""
    anchors = []
    if 1 <= t <= coef.t_end - 1:
        anchors.append((coef.delta[t], U[t - 1]))
    if t + 1 <= coef.t_end - 1:
        anchors.append((coef.delta[t + 1], U[t + 1]))
    return anchors


def coordinate_descent(coef: Coefficients, periods: list[PeriodModel], U: np.ndarray,
                       pools: Pools | None = None, max_sweeps: int = 20,
                       rng: np.random.Generator | None = None, lns_iters: int = 0, lns_k: int = 7):
    """Re-optimize one period at a time with its neighbours fixed."""
    U = U.copy()
    value = objective(coef, U)
    for _ in range(max_sweeps):
        improved = False
        for t in list(range(coef.T)) + list(range(coef.T - 2, 0, -1)):
            anchors = anchors_for(coef, U, t)
            u = periods[t].local_search(U[t], anchors)
            if lns_iters > 0:
                u = periods[t].lns(u, anchors, rng=rng, iters=lns_iters, k=lns_k)
            if np.array_equal(u, U[t]):
                continue
            trial = U.copy()
            trial[t] = u
            v = objective(coef, trial)
            if v < value:
                U, value, improved = trial, v, True
                if pools is not None:
                    pools.add(t, u)
        if not improved:
            break
    return value, U


def period_multistart(pm: PeriodModel, pools: Pools, t: int, kicks: int, kick_size: int,
                      rng: np.random.Generator, loo: int = 8, lns_iters: int = 30,
                      lns_k: int = 7) -> np.ndarray:
    """Independent optimum of one period: several starts, kicks, leave-one-out.

    Starts: the empty portfolio, and the return-only greedy fill (risk ignored),
    which lands in a different basin at high lambda where profitable hedged
    structures need several units at once.  Then ``kicks`` iterated kicks, and
    ``loo`` leave-one-out restarts: drop one of the cheapest-to-remove groups
    of the best state, forbid it, and re-optimize.  These second-best
    structures are what the chain DP needs when the best per-period state is
    expensive to rebalance into.  Every local optimum met goes into the pool.
    Returns the best state found.
    """
    zero = np.zeros(pm.G, dtype=np.int64)
    starts = [zero]
    if pm.quad:
        # continuation: optimize with the risk scaled 0, 1/4, 1/2, warm-starting
        # each stage from the last, so hedged multi-unit structures are built
        # while risk is weak and then pruned instead of never being reached
        u = pm.local_search(zero, linear=True)
        starts.append(u)
        for num in (1, 2):
            u = pm.local_search(u, risk_scale=(num, 4))
            starts.append(u)
    best, best_cost = None, None
    for s in starts:
        u = pm.local_search(s)
        pools.add(t, u)
        c = int(pools.coef.period_cost(t, u[None, :])[0])
        if best is None or c < best_cost:
            best, best_cost = u, c
    for _ in range(kicks):
        v = pm.local_search(pm.kick(best, kick_size, rng))
        pools.add(t, v)
        c = int(pools.coef.period_cost(t, v[None, :])[0])
        if c < best_cost:
            best, best_cost = v, c
    gains = pm.removal_gains(best)
    cand = [int(g) for g in np.argsort(gains, kind="stable") if gains[g] < BIG][:loo]
    forbid = np.zeros(pm.G, dtype=bool)
    for g in cand:
        start = best.copy()
        start[g] = 0
        start = pm.repair(start)
        forbid[:] = False
        forbid[g] = True
        v = pm.local_search(start, forbid=forbid)
        pools.add(t, v)
        c = int(pools.coef.period_cost(t, v[None, :])[0])
        if c < best_cost:
            best, best_cost = v, c
    if lns_iters > 0:
        v = pm.lns(best, rng=rng, iters=lns_iters, k=lns_k)
        pools.add(t, v)
        c = int(pools.coef.period_cost(t, v[None, :])[0])
        if c < best_cost:
            best, best_cost = v, c
    return best


def solve_heuristic(coef: Coefficients, rounds: int = 4, kicks: int = 3, kick_size: int | None = None,
                    loo: int = 8, seed_width: int = 6, chain_kicks: int = 4, anchor_weights=(1, 2),
                    lns_iters: int = 30, lns_k: int = 7, cd_lns_iters: int = 10,
                    seed: int = 0, time_limit: float | None = None, verbose: bool = False):
    """Restricted-state chain heuristic.  Returns (value, (T, G) schedule, info).

    rounds        : DP + coordinate descent + kick rounds (stops early when stuck)
    kicks         : kicked restarts per period in the independent phase
    kick_size     : random unit moves per kick (default budget / 5, at least 2)
    loo           : leave-one-out restarts per period (second-best structures)
    seed_width    : neighbour states each period is chained from, per direction
    chain_kicks   : kick-and-descend attempts on the incumbent schedule per round
    anchor_weights: multipliers of the rebalancing cost used when chaining, so
                    the pools hold states at several distances from neighbours
    lns_iters     : exact large-neighbourhood steps polishing each period's best
    lns_k         : groups freed per step ((ub+1)^k assignments enumerated)
    cd_lns_iters  : large-neighbourhood steps per period inside coordinate descent
    time_limit    : soft wall-clock limit in seconds for the search phase
    """
    t0 = time.time()
    rng = np.random.default_rng(seed)
    T, t_end, G = coef.T, coef.t_end, coef.G
    periods = [PeriodModel(coef, t) for t in range(T)]
    pools = Pools(coef)
    if kick_size is None:
        kick_size = max(2, coef.budget // 5)

    def out_of_time():
        return time_limit is not None and time.time() - t0 > time_limit

    # phase 1: independent per-period optima from several starts plus kicks
    for t in range(T):
        period_multistart(periods[t], pools, t, kicks, kick_size, rng, loo=loo,
                          lns_iters=lns_iters, lns_k=lns_k)
    if verbose:
        print(f"    phase 1 done, {pools.size()} states  [{time.time() - t0:.1f}s]")

    # phase 2: chained optima, forward then backward, so rebalancing can be cheap
    for t in range(1, t_end):
        for v in pools.best(t - 1, seed_width):
            for m in anchor_weights:
                pools.add(t, periods[t].local_search(v, [(m * coef.delta[t], v)]))
    for t in range(t_end - 2, -1, -1):
        for v in pools.best(t + 1, seed_width):
            for m in anchor_weights:
                pools.add(t, periods[t].local_search(v, [(m * coef.delta[t + 1], v)]))
    if verbose:
        print(f"    phase 2 done, {pools.size()} states  [{time.time() - t0:.1f}s]")

    # phase 3 and 4: DP over pools, coordinate descent, repeat with kicks
    best_value, best_U = restricted_dp(coef, pools)
    assert objective(coef, best_U) == best_value
    history = [best_value]
    for r in range(rounds):
        if out_of_time():
            break
        value, U = coordinate_descent(coef, periods, best_U, pools, rng=rng,
                                      lns_iters=cd_lns_iters, lns_k=lns_k)
        if value < best_value:
            best_value, best_U = value, U
        for _ in range(chain_kicks):
            if out_of_time():
                break
            # kick a few periods of the incumbent and descend again
            U = best_U.copy()
            n_kick = int(rng.integers(1, min(T, 3) + 1))
            for t in rng.choice(T, size=n_kick, replace=False):
                U[t] = periods[t].kick(U[t], kick_size, rng)
            value, U = coordinate_descent(coef, periods, U, pools, rng=rng,
                                          lns_iters=cd_lns_iters, lns_k=lns_k)
            if value < best_value:
                best_value, best_U = value, U
        value, U = restricted_dp(coef, pools)
        if value < best_value:
            best_value, best_U = value, U
        history.append(best_value)
        if verbose:
            print(f"    round {r + 1}: best {best_value}, {pools.size()} states  [{time.time() - t0:.1f}s]")
        if len(history) >= 3 and history[-1] == history[-2] == history[-3]:
            break

    check = objective(coef, best_U)
    assert check == best_value, "schedule does not reproduce its own value"
    for t in range(T):
        assert periods[t].feasible(best_U[t]), f"period {t} infeasible"
    info = {"seconds": time.time() - t0, "pool_states": pools.size(),
            "rounds": len(history) - 1, "history": history, "pools": pools}
    return best_value, best_U, info
