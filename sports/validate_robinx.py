"""Run the official RobinX validator on every .xml timetable in a results directory.

    python validate_robinx.py --robinx /workspace/robinx/RobinX --instances <dir> results/p600

Writes <name>.robinx.json next to each timetable with the reported infeasibility
and soft objective, and rewrites the ObjectiveValue element so the file carries the
validator's own numbers.
"""
import argparse, glob, gzip, json, os, re, subprocess, sys, tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from robinx import read_instance, read_solution_sol, write_solution_xml  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dirs", nargs="+")
    ap.add_argument("--robinx", required=True)
    ap.add_argument("--instances", required=True)
    a = ap.parse_args()
    files = {os.path.basename(p).replace(".xml.gz", ""): p for p in glob.glob(f"{a.instances}/*/*.xml.gz")}
    ok = bad = 0
    for d in a.dirs:
        for sf in sorted(glob.glob(f"{d}/*.sol")):
            xf = sf[:-4] + ".xml"
            name = os.path.basename(sf).split(".s")[0]
            inst_path = files[name]
            inst = read_instance(inst_path); games = read_solution_sol(sf)
            write_solution_xml(xf, inst, games, "Manan Gupta")
            with tempfile.NamedTemporaryFile("w", suffix=".xml", delete=False) as tf:
                tf.write(gzip.open(inst_path, "rt").read())
            r = subprocess.run([a.robinx, "-i", tf.name, "-s", xf], capture_output=True, text=True)
            os.unlink(tf.name)
            out = r.stdout + r.stderr
            m = re.search(r"Objective:\s+(\d+)\s+(\d+)", out)
            rec = {"timetable": os.path.basename(xf), "returncode": r.returncode,
                   "infeasibility": int(m.group(1)) if m else None,
                   "soft_objective": int(m.group(2)) if m else None,
                   "exceptions": [l.strip() for l in out.splitlines() if "[Exception" in l][:5]}
            if m and rec["infeasibility"] == 0:
                ok += 1
                write_solution_xml(xf, inst, games, "Manan Gupta", objective=rec["soft_objective"])
                tmp2 = _tmp(inst_path)
                r2 = subprocess.run([a.robinx, "-i", tmp2, "-s", xf], capture_output=True, text=True)
                os.unlink(tmp2)
                rec["revalidated_clean"] = "[Exception" not in (r2.stdout + r2.stderr) and \
                    re.search(r"Objective:\s+0\s+", r2.stdout + r2.stderr) is not None
            else:
                bad += 1
            json.dump(rec, open(xf[:-4] + ".robinx.json", "w"), indent=1)
            print(name, rec["infeasibility"], rec["soft_objective"], rec.get("revalidated_clean"), flush=True)
    print(f"RobinX: {ok} feasible, {bad} not")


def _tmp(inst_path):
    tf = tempfile.NamedTemporaryFile("w", suffix=".xml", delete=False)
    tf.write(gzip.open(inst_path, "rt").read()); tf.close()
    return tf.name


if __name__ == "__main__":
    main()
