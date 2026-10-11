"""CP-SAT feasibility solver for QOBLIB problem 05 (sports timetabling, hard constraints only).

    python solve.py <instance.xml.gz> --seconds 600 --workers 16 --seed 0 --out results/

Model: x[h,a,s] binary for every ordered pair and slot; home[t,s] = sum_a x[t,a,s];
break indicators for the BR constraints; all hard constraints of the instance are
posted as linear constraints. The solution is checked independently with check.py
before anything is written.
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import sys
import time

from ortools.sat.python import cp_model

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from robinx import read_instance, write_solution_sol, write_solution_xml  # noqa: E402
from check import check  # noqa: E402


def build(inst, redundant=False):
    n, S = inst.n, inst.S
    m = cp_model.CpModel()
    x = {}
    for h in range(n):
        for a in range(n):
            if h != a:
                for s in range(S):
                    x[h, a, s] = m.NewBoolVar(f"x_{h}_{a}_{s}")
    home = [[m.NewBoolVar(f"home_{t}_{s}") for s in range(S)] for t in range(n)]
    for h in range(n):
        for a in range(n):
            if h != a:
                m.AddExactlyOne(x[h, a, s] for s in range(S))
    for t in range(n):
        for s in range(S):
            hs = [x[t, a, s] for a in range(n) if a != t]
            aw = [x[h, t, s] for h in range(n) if h != t]
            m.AddExactlyOne(hs + aw)
            m.Add(sum(hs) == home[t][s])
    if inst.phased:
        half = S // 2
        for h in range(n):
            for a in range(h + 1, n):
                m.AddExactlyOne([x[h, a, s] for s in range(half)] + [x[a, h, s] for s in range(half)])
    if redundant:
        # implied by the structure, added for propagation
        for s in range(S):
            m.Add(sum(x[h, a, s] for h in range(n) for a in range(n) if h != a) == n // 2)
            m.Add(sum(home[t][s] for t in range(n)) == n // 2)
        for t in range(n):
            m.Add(sum(home[t]) == n - 1)
            if inst.phased:
                for h0 in (0, S // 2):
                    for a in range(n):
                        if a != t:
                            m.AddExactlyOne([x[t, a, s] for s in range(h0, h0 + S // 2)] +
                                            [x[a, t, s] for s in range(h0, h0 + S // 2)])
    # breaks: bh[t][s] = home[s-1] and home[s]; ba[t][s] = away[s-1] and away[s]
    need_breaks = any(c.tag in ("BR1", "BR2") for c in inst.hard())
    bh = ba = None
    if need_breaks:
        bh = [[None] + [m.NewBoolVar(f"bh_{t}_{s}") for s in range(1, S)] for t in range(n)]
        ba = [[None] + [m.NewBoolVar(f"ba_{t}_{s}") for s in range(1, S)] for t in range(n)]
        for t in range(n):
            for s in range(1, S):
                p, q = home[t][s - 1], home[t][s]
                m.AddBoolAnd([p, q]).OnlyEnforceIf(bh[t][s])
                m.AddBoolOr([p.Not(), q.Not()]).OnlyEnforceIf(bh[t][s].Not())
                m.AddBoolAnd([p.Not(), q.Not()]).OnlyEnforceIf(ba[t][s])
                m.AddBoolOr([p, q]).OnlyEnforceIf(ba[t][s].Not())
    for c in inst.hard():
        tag = c.tag
        if tag == "CA1":
            mx, mode = int(c["max"]), c["mode"]
            slots = c.ints("slots")
            for t in c.ints("teams"):
                terms = [home[t][s] if mode == "H" else home[t][s].Not() for s in slots]
                if mx == 0:
                    for v in terms:
                        m.Add(v == 0)
                else:
                    m.Add(sum(terms) <= mx)
        elif tag == "CA2":
            mx, mode1 = int(c["max"]), c["mode1"]
            slots, t2 = c.ints("slots"), c.ints("teams2")
            for t in c.ints("teams1"):
                terms = []
                for s in slots:
                    for u in t2:
                        if u == t:
                            continue
                        if mode1 in ("H", "HA"):
                            terms.append(x[t, u, s])
                        if mode1 in ("A", "HA"):
                            terms.append(x[u, t, s])
                if mx == 0:
                    for v in terms:
                        m.Add(v == 0)
                elif terms:
                    m.Add(sum(terms) <= mx)
        elif tag == "CA3":
            mx, intp, mode1 = int(c["max"]), int(c["intp"]), c["mode1"]
            t2 = c.ints("teams2")
            for t in c.ints("teams1"):
                per_slot = []
                for s in range(S):
                    terms = []
                    for u in t2:
                        if u == t:
                            continue
                        if mode1 in ("H", "HA"):
                            terms.append(x[t, u, s])
                        if mode1 in ("A", "HA"):
                            terms.append(x[u, t, s])
                    per_slot.append(terms)
                for s in range(intp - 1, S):
                    terms = [v for p in range(s - intp + 1, s + 1) for v in per_slot[p]]
                    if terms:
                        m.Add(sum(terms) <= mx)
        elif tag == "CA4":
            mx, mode1, mode2 = int(c["max"]), c["mode1"], c["mode2"]
            slots, t1, t2 = c.ints("slots"), c.ints("teams1"), c.ints("teams2")

            def terms_at(s):
                out = []
                for u in t1:
                    for v in t2:
                        if u == v:
                            continue
                        if mode1 in ("H", "HA"):
                            out.append(x[u, v, s])
                        if mode1 in ("A", "HA"):
                            out.append(x[v, u, s])
                return out
            if mode2 == "GLOBAL":
                terms = [v for s in slots for v in terms_at(s)]
                if mx == 0:
                    for v in terms:
                        m.Add(v == 0)
                elif terms:
                    m.Add(sum(terms) <= mx)
            else:
                for s in slots:
                    terms = terms_at(s)
                    if mx == 0:
                        for v in terms:
                            m.Add(v == 0)
                    elif terms:
                        m.Add(sum(terms) <= mx)
        elif tag == "GA1":
            mx, mn = int(c["max"]), int(c["min"])
            slots = c.ints("slots")
            terms = [x[h, a, s] for (h, a) in c.meetings() for s in slots]
            if mx == 0:
                for v in terms:
                    m.Add(v == 0)
            else:
                m.Add(sum(terms) <= mx)
            if mn > 0:
                m.Add(sum(terms) >= mn)
        elif tag == "BR1":
            intp, mode2 = int(c["intp"]), c["mode2"]
            slots = [s for s in c.ints("slots") if s > 0]
            for t in c.ints("teams"):
                terms = []
                for s in slots:
                    if mode2 in ("H", "HA"):
                        terms.append(bh[t][s])
                    if mode2 in ("A", "HA"):
                        terms.append(ba[t][s])
                if intp == 0:
                    for v in terms:
                        m.Add(v == 0)
                elif terms:
                    m.Add(sum(terms) <= intp)
        elif tag == "BR2":
            intp = int(c["intp"])
            slots = [s for s in c.ints("slots") if s > 0]
            terms = [b[t][s] for t in c.ints("teams") for s in slots for b in (bh, ba)]
            if terms:
                m.Add(sum(terms) <= intp)
        else:
            raise ValueError(f"unhandled hard constraint {tag}")
    return m, x


def solve(inst, seconds, workers, seed, log=False, redundant=False, params=None):
    t0 = time.time()
    m, x = build(inst, redundant)
    build_s = time.time() - t0
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = seconds
    solver.parameters.num_workers = workers
    solver.parameters.random_seed = seed
    solver.parameters.log_search_progress = log
    if params:
        for kv in params.split():
            k, v = kv.split(":")
            cur = getattr(solver.parameters, k)
            setattr(solver.parameters, k, type(cur)(v) if not isinstance(cur, bool) else v.lower() in ("1", "true"))
    t1 = time.time()
    status = solver.Solve(m)
    solve_s = time.time() - t1
    games = None
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        games = {}
        for (h, a, s), v in x.items():
            if solver.Value(v):
                games[(h, a)] = s
    return {"status": solver.StatusName(status), "build_seconds": build_s, "solve_seconds": solve_s,
            "wall_seconds": time.time() - t0, "num_booleans": solver.NumBooleans(),
            "num_conflicts": solver.NumConflicts(), "num_branches": solver.NumBranches()}, games


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("instance")
    ap.add_argument("--seconds", type=float, default=600)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", default=None)
    ap.add_argument("--log", action="store_true")
    ap.add_argument("--redundant", action="store_true")
    ap.add_argument("--params", default=None, help="extra CP-SAT parameters in text proto form")
    a = ap.parse_args()
    inst = read_instance(a.instance)
    print(f"{inst.name}: {inst.n} teams, {inst.S} slots, phased={inst.phased}, "
          f"{len(inst.hard())} hard / {len(inst.constraints)} constraints", flush=True)
    info, games = solve(inst, a.seconds, a.workers, a.seed, a.log, a.redundant, a.params)
    info.update({"instance": inst.name, "teams": inst.n, "slots": inst.S, "phased": inst.phased,
                 "hard_constraints": len(inst.hard()), "seconds_limit": a.seconds,
                 "workers": a.workers, "seed": a.seed, "redundant": a.redundant, "params": a.params, "machine": platform.node(),
                 "cpu": platform.processor() or platform.machine()})
    if games is not None:
        viol = check(inst, games)
        info["checked_feasible"] = not viol
        if viol:
            print("SOLVER RETURNED A SOLUTION THE CHECKER REJECTS:", viol[:5])
            info["violations"] = viol[:20]
    print(json.dumps({k: v for k, v in info.items() if k != "violations"}), flush=True)
    if a.out:
        os.makedirs(a.out, exist_ok=True)
        tag = f"{inst.name}.s{a.seed}"
        json.dump(info, open(f"{a.out}/{tag}.json", "w"), indent=1)
        if games is not None and info.get("checked_feasible"):
            write_solution_sol(f"{a.out}/{tag}.sol", games, 0,
                               f"instance {inst.name}\nCP-SAT feasibility, seed {a.seed}, {a.workers} workers")
            write_solution_xml(f"{a.out}/{tag}.xml", inst, games, "Manan Gupta")


if __name__ == "__main__":
    main()
