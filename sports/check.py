"""Independent checker for the feasibility version of QOBLIB problem 05.

Reports every violated hard constraint of a double round robin timetable. The
semantics follow the ITC2021 problem description; the reference model in
05-sports/misc/itc2mip.py was used to cross check each constraint type.

    python check.py <instance.xml.gz> <solution.(sol|xml[.gz])> [--soft]
"""
from __future__ import annotations

import sys

from robinx import Instance, read_instance, read_solution


def structure_violations(inst: Instance, games: dict) -> list:
    n, S = inst.n, inst.S
    out = []
    pairs = {(h, a) for h in range(n) for a in range(n) if h != a}
    missing = pairs - set(games)
    extra = set(games) - pairs
    if missing:
        out.append(f"{len(missing)} games not scheduled, e.g. {sorted(missing)[:3]}")
    if extra:
        out.append(f"unknown games {sorted(extra)[:3]}")
    for (h, a), s in games.items():
        if not 0 <= s < S:
            out.append(f"game {h} v {a} in slot {s} outside 0..{S-1}")
    # one game per team per slot
    busy = {}
    for (h, a), s in games.items():
        for t in (h, a):
            if (t, s) in busy:
                out.append(f"team {t} plays twice in slot {s}")
            busy[(t, s)] = 1
    if inst.phased:
        half = S // 2
        for h in range(n):
            for a in range(h + 1, n):
                if (h, a) in games and (a, h) in games:
                    first = (games[(h, a)] < half) + (games[(a, h)] < half)
                    if first != 1:
                        out.append(f"pair {h},{a} not split across the two phases")
    return out


def home_table(inst: Instance, games: dict):
    """home[t][s] = 1 if team t plays at home in slot s, 0 away, None if idle."""
    home = [[None] * inst.S for _ in range(inst.n)]
    for (h, a), s in games.items():
        if 0 <= s < inst.S:
            home[h][s] = 1
            home[a][s] = 0
    return home


def breaks(home_row):
    """b[s] = 1 if slot s continues the home/away status of slot s-1."""
    b = [0] * len(home_row)
    for s in range(1, len(home_row)):
        if home_row[s] is not None and home_row[s] == home_row[s - 1]:
            b[s] = 1 if home_row[s] == 1 else -1  # +1 home break, -1 away break
    return b


def constraint_violations(inst: Instance, games: dict, include_soft=False) -> list:
    n, S = inst.n, inst.S
    home = home_table(inst, games)
    by_slot = {}
    for (h, a), s in games.items():
        by_slot.setdefault(s, []).append((h, a))
    out = []
    for c in inst.constraints:
        if not c.hard and not include_soft:
            continue
        tag = c.tag
        label = f"{tag}{'' if c.hard else '(soft)'} {c.attrib}"
        if tag == "CA1":
            mx, mn = int(c["max"]), int(c["min"])
            slots, mode = c.ints("slots"), c["mode"]
            for t in c.ints("teams"):
                cnt = sum(1 for s in slots if home[t][s] == (1 if mode == "H" else 0))
                if cnt > mx or cnt < mn:
                    out.append(f"{label}: team {t} has {cnt}")
        elif tag == "CA2":
            mx, mn = int(c["max"]), int(c["min"])
            slots, mode1 = set(c.ints("slots")), c["mode1"]
            t2 = set(c.ints("teams2"))
            for t in c.ints("teams1"):
                cnt = 0
                for (h, a), s in games.items():
                    if s not in slots:
                        continue
                    if mode1 in ("H", "HA") and h == t and a in t2:
                        cnt += 1
                    if mode1 in ("A", "HA") and a == t and h in t2:
                        cnt += 1
                if cnt > mx or cnt < mn:
                    out.append(f"{label}: team {t} has {cnt}")
        elif tag == "CA3":
            mx, intp, mode1 = int(c["max"]), int(c["intp"]), c["mode1"]
            t2 = set(c.ints("teams2"))
            for t in c.ints("teams1"):
                hits = [0] * S
                for (h, a), s in games.items():
                    if mode1 in ("H", "HA") and h == t and a in t2:
                        hits[s] += 1
                    if mode1 in ("A", "HA") and a == t and h in t2:
                        hits[s] += 1
                for s in range(intp - 1, S):
                    cnt = sum(hits[s - intp + 1: s + 1])
                    if cnt > mx:
                        out.append(f"{label}: team {t} has {cnt} in slots {s-intp+1}..{s}")
                        break
        elif tag == "CA4":
            mx, mode1, mode2 = int(c["max"]), c["mode1"], c["mode2"]
            slots = c.ints("slots")
            t1, t2 = set(c.ints("teams1")), set(c.ints("teams2"))

            def count(s):
                cnt = 0
                for (h, a) in by_slot.get(s, []):
                    if mode1 in ("H", "HA") and h in t1 and a in t2:
                        cnt += 1
                    if mode1 in ("A", "HA") and a in t1 and h in t2:
                        cnt += 1
                return cnt
            if mode2 == "GLOBAL":
                cnt = sum(count(s) for s in slots)
                if cnt > mx:
                    out.append(f"{label}: {cnt} games")
            else:
                for s in slots:
                    cnt = count(s)
                    if cnt > mx:
                        out.append(f"{label}: {cnt} games in slot {s}")
        elif tag == "GA1":
            mx, mn = int(c["max"]), int(c["min"])
            slots = set(c.ints("slots"))
            cnt = sum(1 for (h, a) in c.meetings() if (h, a) in games and games[(h, a)] in slots)
            if cnt > mx or cnt < mn:
                out.append(f"{label}: {cnt} of the listed games in the slots")
        elif tag == "BR1":
            intp, mode2 = int(c["intp"]), c["mode2"]
            slots = c.ints("slots")
            for t in c.ints("teams"):
                b = breaks(home[t])
                cnt = 0
                for s in slots:
                    if s == 0:
                        continue
                    if mode2 in ("H", "HA") and b[s] == 1:
                        cnt += 1
                    if mode2 in ("A", "HA") and b[s] == -1:
                        cnt += 1
                if cnt > intp:
                    out.append(f"{label}: team {t} has {cnt} breaks")
        elif tag == "BR2":
            intp = int(c["intp"])
            slots = c.ints("slots")
            cnt = 0
            for t in c.ints("teams"):
                b = breaks(home[t])
                cnt += sum(1 for s in slots if s > 0 and b[s] != 0)
            if cnt > intp:
                out.append(f"{label}: {cnt} breaks in total")
        elif tag == "FA2":
            intp = int(c["intp"])
            slots, teams = c.ints("slots"), c.ints("teams")
            for s in slots:
                hg = {t: sum(1 for p in range(s + 1) if home[t][p] == 1) for t in teams}
                if max(hg.values()) - min(hg.values()) > intp:
                    out.append(f"{label}: home game difference {max(hg.values()) - min(hg.values())} at slot {s}")
                    break
        elif tag == "SE1":
            mn = int(c["min"])
            teams = c.ints("teams")
            for i, h in enumerate(teams):
                for a in teams[i + 1:]:
                    if (h, a) in games and (a, h) in games:
                        gap = abs(games[(h, a)] - games[(a, h)]) - 1
                        if gap < mn:
                            out.append(f"{label}: only {gap} slots between the games of {h} and {a}")
        else:
            out.append(f"unhandled constraint {tag}")
    return out


def check(inst: Instance, games: dict, include_soft=False) -> list:
    v = structure_violations(inst, games)
    if v:
        return v
    return constraint_violations(inst, games, include_soft)


if __name__ == "__main__":
    inst = read_instance(sys.argv[1])
    games = read_solution(sys.argv[2])
    viol = check(inst, games, include_soft="--soft" in sys.argv)
    if viol:
        print(f"{inst.name}: {len(viol)} violations")
        for v in viol[:40]:
            print("  " + v)
        sys.exit(1)
    print(f"{inst.name}: feasible ({len(games)} games, {inst.n} teams, {inst.S} slots, {len(inst.hard())} hard constraints)")
