"""Read RobinX instances and solutions for QOBLIB problem 05 (sports timetabling).

Only what the feasibility version of the benchmark needs: the double round robin
structure (teams, slots, phased or not) and the constraint list with every
attribute kept as given. Soft constraints are parsed too so a checker can
report them, but the benchmark ignores them.
"""
from __future__ import annotations

import gzip
import os
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field


def _open(path):
    return gzip.open(path, "rt") if path.endswith(".gz") else open(path)


def _ints(s):
    s = (s or "").strip()
    return [int(v) for v in s.split(";") if v != ""]


@dataclass
class Constraint:
    tag: str
    hard: bool
    attrib: dict

    def ints(self, key):
        return _ints(self.attrib.get(key))

    def __getitem__(self, key):
        return self.attrib[key]

    def meetings(self):
        out = []
        for m in (self.attrib.get("meetings") or "").split(";"):
            m = m.strip()
            if m:
                h, a = m.split(",")
                out.append((int(h), int(a)))
        return out


@dataclass
class Instance:
    name: str
    teams: list
    slots: list
    phased: bool
    constraints: list = field(default_factory=list)

    @property
    def n(self):
        return len(self.teams)

    @property
    def S(self):
        return len(self.slots)

    def hard(self):
        return [c for c in self.constraints if c.hard]


def read_instance(path: str) -> Instance:
    root = ET.parse(_open(path)).getroot()
    name = os.path.basename(path)
    for ext in (".gz", ".xml"):
        if name.endswith(ext):
            name = name[: -len(ext)]
    teams = sorted(int(t.attrib["id"]) for t in root.findall(".//Teams/team"))
    slots = sorted(int(s.attrib["id"]) for s in root.findall(".//Slots/slot"))
    gm = root.find(".//gameMode")
    phased = gm is not None and (gm.text or "").strip() == "P"
    nrr = root.find(".//numberRoundRobin")
    assert nrr is not None and nrr.text.strip() == "2", "only double round robins are handled"
    assert teams == list(range(len(teams))) and slots == list(range(len(slots)))
    assert len(slots) == 2 * (len(teams) - 1), "time constrained double round robin expected"
    cons = []
    croot = root.find("Constraints")
    if croot is not None:
        for grp in croot:
            for e in grp:
                if re.fullmatch(r"(CA|BR|GA|FA|SE)\d", e.tag):
                    cons.append(Constraint(e.tag, e.attrib.get("type", "HARD") == "HARD", dict(e.attrib)))
    return Instance(name, teams, slots, phased, cons)


# A schedule is a dict {(home, away): slot}.

def read_solution_xml(path: str) -> dict:
    root = ET.parse(_open(path)).getroot()
    games = {}
    for g in root.iter("ScheduledMatch"):
        h, a, s = int(g.attrib["home"]), int(g.attrib["away"]), int(g.attrib["slot"])
        assert (h, a) not in games, f"duplicate game {h} v {a}"
        games[(h, a)] = s
    return games


def read_solution_sol(path: str) -> dict:
    games = {}
    for line in _open(path):
        t = line.split()
        if len(t) >= 2 and t[0].startswith("x#") and float(t[1]) > 0.5:
            _, h, a, s = t[0].split("#")
            games[(int(h), int(a))] = int(s)
    return games


def read_solution(path: str) -> dict:
    p = path[:-3] if path.endswith(".gz") else path
    return read_solution_xml(path) if p.endswith(".xml") else read_solution_sol(path)


def write_solution_sol(path: str, games: dict, objective=0, comment=None):
    with open(path, "w") as f:
        f.write(f"# Objective value = {objective}\n")
        if comment:
            for line in comment.splitlines():
                f.write(f"# {line}\n")
        for (h, a), s in sorted(games.items(), key=lambda kv: (kv[1], kv[0])):
            f.write(f"x#{h}#{a}#{s} 1\n")


def write_solution_xml(path: str, inst: Instance, games: dict, contributor: str,
                       date=(11, 10, 2026), objective=0, solution_name=None):
    """RobinX solution file. `objective` is the soft constraint penalty reported by
    the RobinX validator for this timetable (0 if unknown); infeasibility is 0."""
    d, mo, y = date
    lines = ['<?xml version="1.0" encoding="UTF-8"?>', "<Solution>", "    <MetaData>",
             f"        <InstanceName>{inst.name}.xml</InstanceName>",
             f"        <SolutionName>{solution_name or inst.name + '_CPSAT.xml'}</SolutionName>",
             f"        <Contributor>{contributor}</Contributor>",
             f'        <Date day="{d}" month="{mo}" year="{y}"/>',
             f'        <ObjectiveValue infeasibility="0" objective="{objective}"/>',
             "    </MetaData>", "    <Games>"]
    for (h, a), s in sorted(games.items(), key=lambda kv: (kv[1], kv[0])):
        lines.append(f'        <ScheduledMatch home="{h}" away="{a}" slot="{s}"/>')
    lines += ["    </Games>", "</Solution>", ""]
    with open(path, "w") as f:
        f.write("\n".join(lines))
