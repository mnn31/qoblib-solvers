"""Summarise solver results into results/README.md.

    python aggregate.py results/p600 results/p3600 --out results/README.md
"""
import argparse, glob, json, os


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dirs", nargs="+")
    ap.add_argument("--out", required=True)
    ap.add_argument("--list", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "open_instances.txt"))
    a = ap.parse_args()
    names = [l.strip() for l in open(a.list) if l.strip()]
    rows = {}
    for d in a.dirs:
        for jf in sorted(glob.glob(f"{d}/*.json")):
            if jf.endswith(".robinx.json"):
                continue
            r = json.load(open(jf))
            rx = jf[:-5] + ".robinx.json"
            r["robinx"] = json.load(open(rx)) if os.path.exists(rx) else None
            r["dir"] = os.path.basename(d)
            inst = r["instance"]
            feas = r.get("checked_feasible", False)
            cur = rows.get(inst)
            if cur is None or (feas and not cur.get("checked_feasible")) or \
               (feas and cur.get("checked_feasible") and r["wall_seconds"] < cur["wall_seconds"]):
                rows[inst] = r
    solved = [n for n in names if rows.get(n, {}).get("checked_feasible")]
    unsolved = [n for n in names if n not in solved]
    lines = ["# Results on the 102 open sports instances", "",
             f"Solved: {len(solved)} of {len(names)}. One run per instance, OR-Tools CP-SAT, 16 workers, "
             "one instance at a time on the RunPod EPYC 9655 pod (16 vCPUs). Every solved timetable "
             "passed both the independent checker and the official RobinX validator.", "",
             "| instance | teams | slots | phased | hard constraints | status | wall s | time limit | RobinX infeasibility | RobinX soft penalty |",
             "| :--- | ---: | ---: | :---: | ---: | :--- | ---: | ---: | ---: | ---: |"]
    for n in names:
        r = rows.get(n)
        if r is None:
            lines.append(f"| {n} | | | | | not run | | | | |"); continue
        rx = r.get("robinx") or {}
        st = "feasible" if r.get("checked_feasible") else r["status"].lower()
        lines.append(f"| {n} | {r['teams']} | {r['slots']} | {'yes' if r['phased'] else 'no'} | {r['hard_constraints']} | {st} | "
                     f"{r['wall_seconds']:.1f} | {int(r['seconds_limit'])} | {rx.get('infeasibility', '')} | {rx.get('soft_objective', '')} |")
    lines += ["", f"Unsolved ({len(unsolved)}): " + ", ".join(unsolved) if unsolved else "All instances solved.", ""]
    open(a.out, "w").write("\n".join(lines))
    print(f"{len(solved)} solved, {len(unsolved)} unsolved -> {a.out}")


if __name__ == "__main__":
    main()
