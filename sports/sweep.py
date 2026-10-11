"""Run solve.py over a list of instances, strictly one at a time, resumable.

    python sweep.py --list open_instances.txt --instances <dir> --out results/pod --seconds 600 --workers 16

Instances that already have a result JSON for this seed are skipped, so the
sweep can be stopped and restarted. Instances are solved in order of size.
"""
import argparse, glob, json, os, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", required=True)
    ap.add_argument("--instances", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--seconds", type=float, default=600)
    ap.add_argument("--workers", type=int, default=16)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--only-unsolved", default=None, help="skip instances with a feasible .sol in this dir")
    a = ap.parse_args()
    names = [l.strip() for l in open(a.list) if l.strip()]
    files = {os.path.basename(p).replace(".xml.gz", ""): p for p in glob.glob(f"{a.instances}/*/*.xml.gz")}
    os.makedirs(a.out, exist_ok=True)
    solved_elsewhere = set()
    if a.only_unsolved:
        solved_elsewhere = {os.path.basename(p).split(".s")[0] for p in glob.glob(f"{a.only_unsolved}/*.sol")}
    todo = []
    for n in names:
        if n not in files:
            print("missing instance", n); continue
        if n in solved_elsewhere:
            continue
        if os.path.exists(f"{a.out}/{n}.s{a.seed}.json"):
            continue
        todo.append(n)
    todo.sort(key=lambda n: (os.path.getsize(files[n]), n))
    print(f"{len(todo)} instances to run, {a.seconds}s each, {a.workers} workers", flush=True)
    for i, n in enumerate(todo):
        t0 = time.time()
        cmd = [sys.executable, f"{HERE}/solve.py", files[n], "--seconds", str(a.seconds),
               "--workers", str(a.workers), "--seed", str(a.seed), "--out", a.out]
        r = subprocess.run(cmd, capture_output=True, text=True)
        last = (r.stdout.strip().splitlines() or ["?"])[-1]
        try:
            st = json.loads(last)["status"]
        except Exception:
            st = "ERROR " + (r.stderr.strip().splitlines() or ["?"])[-1][:200]
        print(f"[{i+1}/{len(todo)}] {n}: {st} in {time.time()-t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
