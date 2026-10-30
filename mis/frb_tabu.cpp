// Tabu search for the frb independent set instances (Xu's Model RB, BHOSLIB).
// The graph is k cliques of d consecutive vertices, so an independent set of
// size k is one vertex per clique with no edge between them: a binary CSP.
// The search keeps a complete assignment and minimises conflicting pairs, in
// the style of Galinier and Hao's tabu search for CSP, with constraint weights
// that grow on pairs in conflict every weight_period iterations (0 turns them
// off, a negative value raises them at local minima instead). Each new best
// assignment is turned into an independent set by a vertex cover of its conflicts.
//   frb_tabu <graph.gph> <k> <d> <out.sol> <seconds> <seed> [stop_at_size] [weight_period]
#include <algorithm>
#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <sstream>
#include <string>
#include <vector>
using namespace std;
typedef unsigned long long u64;
static u64 st[2];
static inline u64 rotl(u64 x, int k) { return (x << k) | (x >> (64 - k)); }
static inline u64 rnd() { u64 a = st[0], b = st[1], r = a + b; b ^= a; st[0] = rotl(a, 24) ^ b ^ (b << 16); st[1] = rotl(b, 37); return r; }
static inline unsigned rnd(unsigned n) { return (unsigned)(((rnd() >> 32) * n) >> 32); }
int n, k, d;
vector<int> off, to;           // adjacency without the edges inside a clique
vector<int> wt;                // weight per arc, kept symmetric through mate
vector<int> mate;              // index of the reverse arc
vector<int> gam;               // weighted conflicts of a vertex with the assignment
vector<int> x;                 // chosen vertex per clique
vector<int> sel;               // 1 if chosen
vector<long long> tabu;
static bool mvc(vector<pair<int,int>> &E, int budget, vector<int> &cover) {
    int idx = -1;
    for (size_t i = 0; i < E.size(); i++) {
        bool hit = false;
        for (int c : cover) if (E[i].first == c || E[i].second == c) hit = true;
        if (!hit) { idx = i; break; }
    }
    if (idx < 0) return true;
    if (budget == 0) return false;
    cover.push_back(E[idx].first);
    if (mvc(E, budget - 1, cover)) return true;
    cover.pop_back();
    cover.push_back(E[idx].second);
    if (mvc(E, budget - 1, cover)) return true;
    cover.pop_back();
    return false;
}
int main(int argc, char **argv) {
    if (argc < 7) { fprintf(stderr, "usage\n"); return 2; }
    k = atoi(argv[2]); d = atoi(argv[3]);
    double limit = atof(argv[5]); unsigned seed = atoi(argv[6]);
    int stop = argc > 7 ? atoi(argv[7]) : k;
    long long period = argc > 8 ? atoll(argv[8]) : 0;
    st[0] = 0x9E3779B97F4A7C15ULL * (seed + 1); st[1] = 0xBF58476D1CE4E5B9ULL ^ (u64)seed * 0x94D049BB133111EBULL;
    for (int i = 0; i < 20; i++) rnd();
    ifstream f(argv[1]); string line; vector<pair<int,int>> E;
    while (getline(f, line)) {
        if (line.empty()) continue;
        if (line[0] == 'p') { string a, b; int mm; stringstream ss(line); ss >> a >> b >> n >> mm; }
        else if (line[0] == 'e') { stringstream ss(line); string a; int u, v; ss >> a >> u >> v; u--; v--;
            if (u > v) swap(u, v);
            if (u != v && u / d != v / d) E.push_back({u, v}); }
    }
    if (n != k * d) { fprintf(stderr, "n != k*d\n"); return 2; }
    sort(E.begin(), E.end()); E.erase(unique(E.begin(), E.end()), E.end());
    vector<int> deg(n, 0); for (auto &e : E) { deg[e.first]++; deg[e.second]++; }
    off.assign(n + 1, 0); for (int i = 0; i < n; i++) off[i + 1] = off[i] + deg[i];
    to.resize(2 * E.size()); wt.assign(2 * E.size(), 1); mate.resize(2 * E.size());
    { vector<int> p(off.begin(), off.end() - 1);
      for (auto &e : E) { int a = p[e.first]++, b = p[e.second]++; to[a] = e.second; to[b] = e.first; mate[a] = b; mate[b] = a; } }
    gam.assign(n, 0); sel.assign(n, 0); x.resize(k); tabu.assign(n, 0);
    auto t0 = chrono::steady_clock::now();
    auto now = [&] { return chrono::duration<double>(chrono::steady_clock::now() - t0).count(); };
    int best = -1; long long it = 0, best_f = 1LL << 60;
    auto place = [&](int v) { sel[v] = 1; for (int i = off[v]; i < off[v + 1]; i++) gam[to[i]] += wt[i]; };
    auto drop = [&](int v) { sel[v] = 0; for (int i = off[v]; i < off[v + 1]; i++) gam[to[i]] -= wt[i]; };
    auto rawconf = [&] {
        vector<pair<int,int>> C;
        for (int c = 0; c < k; c++) { int v = x[c];
            for (int i = off[v]; i < off[v + 1]; i++) if (sel[to[i]] && to[i] > v) C.push_back({v, to[i]}); }
        return C;
    };
    auto report = [&] {
        auto C = rawconf();
        int kc = 0, lim = k - best - 1; vector<int> cover; bool ok = false;
        if (C.size() <= 20) {
            for (; kc <= lim; kc++) { cover.clear(); if (mvc(C, kc, cover)) { ok = true; break; } }
        } else {
            // too many conflicts for the exact cover, take the busiest vertex until none is left
            vector<pair<int,int>> R = C;
            while (!R.empty()) {
                vector<pair<int,int>> cnt; for (auto &e : R) { cnt.push_back({e.first, 0}); cnt.push_back({e.second, 0}); }
                int bestv = -1, bestc = -1;
                for (auto &q : cnt) { int c = 0; for (auto &e : R) if (e.first == q.first || e.second == q.first) c++; if (c > bestc) { bestc = c; bestv = q.first; } }
                cover.push_back(bestv);
                vector<pair<int,int>> T; for (auto &e : R) if (e.first != bestv && e.second != bestv) T.push_back(e);
                R.swap(T);
            }
            kc = cover.size(); ok = kc <= lim;
        }
        if (!ok) return;
        int sz = k - kc;
        if (sz > best) {
            best = sz; vector<int> out;
            for (int c = 0; c < k; c++) if (find(cover.begin(), cover.end(), x[c]) == cover.end()) out.push_back(x[c] + 1);
            sort(out.begin(), out.end());
            ofstream o(argv[4]); o << "# Tabu search on the clique partition, seed " << seed << "\n# Objective value = " << best << "\n";
            for (int v : out) o << v << "\n";
            printf("%.3f %d it %lld\n", now(), best, it); fflush(stdout);
        }
    };
    auto start = [&] {
        fill(sel.begin(), sel.end(), 0); fill(gam.begin(), gam.end(), 0); fill(wt.begin(), wt.end(), 1);
        for (int c = 0; c < k; c++) x[c] = c * d + rnd(d);
        for (int c = 0; c < k; c++) place(x[c]);
        fill(tabu.begin(), tabu.end(), 0); best_f = 1LL << 60;
    };
    start();
    int cl[4096];
    while (true) {
        if ((it & 4095) == 0 && now() > limit) break;
        it++;
        int nc = 0; long long f2 = 0;
        for (int c = 0; c < k; c++) { int g = gam[x[c]]; if (g) { cl[nc++] = c; f2 += g; } }
        long long fc = f2 / 2;
        if (fc < best_f) best_f = fc;
        if (nc == 0) { report(); break; }
        if (nc <= 2 * (k - best - 1) + 2) {
            int raw = 0; for (int i = 0; i < nc; i++) { int v = x[cl[i]]; for (int j = off[v]; j < off[v + 1]; j++) if (sel[to[j]]) raw++; }
            if (raw / 2 <= k - best + 2) { report(); if (best >= stop) break; }
        }
        int bd = 1 << 30, bv = -1, bc = -1, ties = 0;
        for (int i = 0; i < nc; i++) {
            int c = cl[i], cur = gam[x[c]], s = c * d;
            for (int v = s; v < s + d; v++) {
                if (v == x[c]) continue;
                int dl = gam[v] - cur;
                if (tabu[v] > it && !(fc + dl < best_f)) continue;
                if (dl < bd) { bd = dl; bv = v; bc = c; ties = 1; }
                else if (dl == bd && rnd(++ties) == 0) { bv = v; bc = c; }
            }
        }
        if (bv < 0) { int c = cl[rnd(nc)]; bc = c; bv = c * d + rnd(d); if (bv == x[c]) continue; }
        int old = x[bc];
        drop(old); place(bv); x[bc] = bv;
        tabu[old] = it + rnd(10) + (long long)(0.6 * nc);
        if ((period > 0 && it % period == 0) || (period < 0 && bd >= 0)) {
            // raise the weight of every pair in conflict right now
            for (int c = 0; c < k; c++) { int v = x[c];
                for (int j = off[v]; j < off[v + 1]; j++) if (sel[to[j]] && to[j] > v) {
                    wt[j]++; wt[mate[j]]++; gam[to[j]]++; gam[v]++; } }
        }
        if (period != 0 && (it & 0xFFFFF) == 0) {
            // keep the weights bounded: halve them all and rebuild the conflict counts
            for (auto &q : wt) q = (q + 1) / 2;
            fill(gam.begin(), gam.end(), 0);
            for (int c = 0; c < k; c++) { int v = x[c]; for (int j = off[v]; j < off[v + 1]; j++) gam[to[j]] += wt[j]; }
            best_f = 1LL << 60;
        }
    }
    fprintf(stderr, "iterations %lld best %d time %.1f\n", it, best, now());
    return 0;
}
