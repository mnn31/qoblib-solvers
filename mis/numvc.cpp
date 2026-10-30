// NuMVC style local search for minimum vertex cover (Cai, Su, Luo, Sattar, JAIR 2013),
// used for maximum independent set: the complement of a vertex cover is independent.
// Two stage exchange, edge weighting with forgetting, configuration checking.
//   numvc <graph.gph> <out.sol> <seconds> <seed> [stop_at_size]
#include <algorithm>
#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <iostream>
#include <random>
#include <sstream>
#include <string>
#include <vector>
using namespace std;
struct Arc { int to, e; };
int n, m;
vector<int> eu, ev, w, off, uncov, upos, in_c, conf, clist, cpos;
vector<Arc> arcs;
vector<long long> dscore, ts;
long long total_w = 0;
inline void add_unc(int e) { upos[e] = uncov.size(); uncov.push_back(e); }
inline void del_unc(int e) { int p = upos[e], l = uncov.back(); uncov[p] = l; upos[l] = p; uncov.pop_back(); }
inline void add_c(int v) { cpos[v] = clist.size(); clist.push_back(v); }
inline void del_c(int v) { int p = cpos[v], l = clist.back(); clist[p] = l; cpos[l] = p; clist.pop_back(); }
void add(int v) {
    in_c[v] = 1; dscore[v] = -dscore[v]; add_c(v);
    for (int i = off[v]; i < off[v + 1]; i++) {
        int u = arcs[i].to, e = arcs[i].e;
        if (!in_c[u]) { dscore[u] -= w[e]; conf[u] = 1; del_unc(e); } else dscore[u] += w[e];
    }
}
void rem(int v) {
    in_c[v] = 0; dscore[v] = -dscore[v]; conf[v] = 0; del_c(v);
    for (int i = off[v]; i < off[v + 1]; i++) {
        int u = arcs[i].to, e = arcs[i].e;
        if (!in_c[u]) { dscore[u] += w[e]; conf[u] = 1; add_unc(e); } else dscore[u] -= w[e];
    }
}
void forget() {
    fill(dscore.begin(), dscore.end(), 0); total_w = 0;
    for (int e = 0; e < m; e++) {
        w[e] = (int)(0.3 * w[e]); if (w[e] < 1) w[e] = 1; total_w += w[e];
        int a = eu[e], b = ev[e];
        if (in_c[a] + in_c[b] == 0) { dscore[a] += w[e]; dscore[b] += w[e]; }
        else if (in_c[a] + in_c[b] == 1) { if (in_c[a]) dscore[a] -= w[e]; else dscore[b] -= w[e]; }
    }
}
int main(int argc, char **argv) {
    if (argc < 5) { cerr << "usage\n"; return 2; }
    double limit = atof(argv[3]); unsigned seed = atoi(argv[4]); int stop = argc > 5 ? atoi(argv[5]) : 1 << 30;
    ifstream f(argv[1]); string line;
    while (getline(f, line)) {
        if (line.empty()) continue;
        if (line[0] == 'p') { string a, b; int mm; stringstream ss(line); ss >> a >> b >> n >> mm; }
        else if (line[0] == 'e') { stringstream ss(line); string a; int u, v; ss >> a >> u >> v; if (u != v) { eu.push_back(u - 1); ev.push_back(v - 1); } }
    }
    // drop duplicate edges
    { vector<pair<int,int>> E; for (size_t i = 0; i < eu.size(); i++) E.push_back({min(eu[i], ev[i]), max(eu[i], ev[i])});
      sort(E.begin(), E.end()); E.erase(unique(E.begin(), E.end()), E.end());
      eu.clear(); ev.clear(); for (auto &p : E) { eu.push_back(p.first); ev.push_back(p.second); } }
    m = eu.size();
    vector<int> deg(n, 0); for (int e = 0; e < m; e++) { deg[eu[e]]++; deg[ev[e]]++; }
    off.assign(n + 1, 0); for (int i = 0; i < n; i++) off[i + 1] = off[i] + deg[i];
    arcs.resize(2 * m); { vector<int> p(off.begin(), off.end() - 1);
      for (int e = 0; e < m; e++) { arcs[p[eu[e]]++] = {ev[e], e}; arcs[p[ev[e]]++] = {eu[e], e}; } }
    w.assign(m, 1); upos.assign(m, 0); in_c.assign(n, 0); conf.assign(n, 1); cpos.assign(n, 0);
    dscore.assign(n, 0); ts.assign(n, 0); total_w = m;
    for (int e = 0; e < m; e++) { add_unc(e); dscore[eu[e]]++; dscore[ev[e]]++; }
    mt19937 rng(seed);
    auto t0 = chrono::steady_clock::now();
    auto now = [&] { return chrono::duration<double>(chrono::steady_clock::now() - t0).count(); };
    while (!uncov.empty()) { int b = -1; for (int v = 0; v < n; v++) if (!in_c[v] && (b < 0 || dscore[v] > dscore[b])) b = v; add(b); }
    for (int v = 0; v < n; v++) if (in_c[v] && dscore[v] == 0) rem(v);
    long long gamma = (long long)(0.5 * n), step = 1, cleanup = 0;
    int best = -1, tabu = -1; vector<int> best_set;
    auto save = [&] {
        int sz = n - (int)clist.size();
        if (sz > best) {
            best = sz; best_set.clear(); for (int v = 0; v < n; v++) if (!in_c[v]) best_set.push_back(v + 1);
            ofstream o(argv[2]); o << "# NuMVC style local search, seed " << seed << "\n# Objective value = " << best << "\n";
            for (int v : best_set) o << v << "\n";
            printf("%.3f %d\n", now(), best); fflush(stdout);
        }
    };
    double tt = 0;
    while (true) {
        if (uncov.empty()) {
            save(); if (best >= stop || clist.empty()) break;
            int b = clist[0]; for (int v : clist) if (dscore[v] > dscore[b]) b = v; rem(b); continue;
        }
        if ((step & 1023) == 0 && (tt = now()) > limit) break;
        int u = -1;
        for (int v : clist) { if (v == tabu) continue;
            if (u < 0 || dscore[v] > dscore[u] || (dscore[v] == dscore[u] && ts[v] < ts[u])) u = v; }
        rem(u);
        int e = uncov[rng() % uncov.size()], a = eu[e], b = ev[e], v;
        if (!conf[a]) v = b; else if (!conf[b]) v = a;
        else if (dscore[a] > dscore[b] || (dscore[a] == dscore[b] && ts[a] < ts[b])) v = a; else v = b;
        add(v); ts[u] = ts[v] = step; tabu = v;
        for (int x : uncov) { w[x]++; dscore[eu[x]]++; dscore[ev[x]]++; }
        total_w += uncov.size();
        if (total_w > gamma * m) forget();
        step++;
    }
    fprintf(stderr, "steps %lld best %d time %.1f\n", step, best, now());
    return 0;
}
