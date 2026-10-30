// Self avoiding walk search for low autocorrelation binary sequences, after
// lssOrel (Boskovic, Brglez, Brest, Applied Soft Computing 2017). Each walk starts
// from a random sequence and always moves to the best neighbour it has not visited
// in this walk, for a fixed number of steps, then starts over.
//   lss <L> <skew|full> <out.sol> <seconds> <seed> <target_energy> [walk_factor]
// skew searches skew-symmetric sequences of odd length, flipping a position and
// its mirror together. full flips one position at a time, any length.
//   lss <L> near<M> <out.sol> <seconds> <seed> <target_energy> [walk_factor] [polish_margin]
// near walks over skew-symmetric sequences of odd length M close to L. At every
// step it cuts each window of length L out of the skew sequence, or extends it
// with bits at the ends when M < L, and any candidate within polish_margin percent
// of the best energy so far gets a steepest descent with single flips.
#include <algorithm>
#include <chrono>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <vector>
using namespace std;
typedef unsigned long long u64;
static u64 st[2];
static inline u64 rotl(u64 x, int k) { return (x << k) | (x >> (64 - k)); }
static inline u64 rnd() { u64 a = st[0], b = st[1], r = a + b; b ^= a; st[0] = rotl(a, 24) ^ b ^ (b << 16); st[1] = rotl(b, 37); return r; }
static inline unsigned rnd(unsigned n) { return (unsigned)(((rnd() >> 32) * n) >> 32); }
static int L;
static int32_t Pbuf[1024], Cbuf[512];
static int32_t *const P = Pbuf + 340;   // zero padded on both sides
static int32_t *const C = Cbuf;
static inline void build() {
    memset(C, 0, sizeof(Cbuf));
    for (int k = 1; k < L; k++) { int s = 0; for (int i = 0; i + k < L; i++) s += P[i] * P[i + k]; C[k] = s; }
}
static inline int energy() { int e = 0; for (int k = 1; k < L; k++) e += C[k] * C[k]; return e; }
static inline int eval1(int a) {
    const int32_t sa = P[a]; const int32_t *up = P + a, *dn = P + a; int e = 0;
    #pragma clang loop vectorize(enable) interleave(enable)
    for (int k = 1; k < L; k++) { int c = C[k] - 2 * sa * (up[k] + dn[-k]); e += c * c; }
    return e;
}
static inline int eval2(int a, int b) {
    const int32_t sa = P[a], sb = P[b]; const int32_t *ua = P + a, *ub = P + b; int e = 0;
    #pragma clang loop vectorize(enable) interleave(enable)
    for (int k = 1; k < L; k++) { int c = C[k] - 2 * (sa * (ua[k] + ua[-k]) + sb * (ub[k] + ub[-k])); e += c * c; }
    int k0 = b - a, c0 = C[k0] - 2 * (sa * (ua[k0] + ua[-k0]) + sb * (ub[k0] + ub[-k0]));
    int c1 = c0 + 4 * sa * sb;
    return e - c0 * c0 + c1 * c1;
}
static inline void flip(int a) {
    const int32_t sa = P[a];
    for (int k = 1; k < L; k++) C[k] -= 2 * sa * (P[a + k] + P[a - k]);
    P[a] = -sa;
}
// candidate sequences are copied into P and polished with single flips
static int polish(const int8_t *q, int n, vector<int8_t> &out) {
    memset(Pbuf, 0, sizeof(Pbuf)); int sv = L; L = n;
    for (int i = 0; i < n; i++) P[i] = q[i];
    build(); int e = energy();
    while (true) {
        int be = e, bi = -1;
        for (int i = 0; i < n; i++) { int x = eval1(i); if (x < be) { be = x; bi = i; } }
        if (bi < 0) break;
        flip(bi); e = be;
    }
    out.resize(n); for (int i = 0; i < n; i++) out[i] = (int8_t)P[i];
    L = sv; return e;
}
static inline int quick(const int8_t *q, int n) {
    int e = 0;
    for (int k = 1; k < n; k++) { int c = 0; for (int i = 0; i + k < n; i++) c += q[i] * q[i + k]; e += c * c; }
    return e;
}
int main(int argc, char **argv) {
    if (argc < 7) { fprintf(stderr, "usage\n"); return 2; }
    L = atoi(argv[1]); bool skew = !strcmp(argv[2], "skew"); int N = L, M = 0;
    if (!strncmp(argv[2], "near", 4)) { M = atoi(argv[2] + 4); L = M; skew = true; }
    double margin = argc > 8 ? atof(argv[8]) / 100.0 : 0.15;
    double limit = atof(argv[4]); unsigned seed = atoi(argv[5]); int target = atoi(argv[6]);
    double wf = argc > 7 ? atof(argv[7]) : 8.0;
    if (skew && L % 2 == 0) { fprintf(stderr, "skew needs odd length\n"); return 2; }
    st[0] = 0x9E3779B97F4A7C15ULL * (seed + 1); st[1] = 0xBF58476D1CE4E5B9ULL ^ (u64)seed * 0x94D049BB133111EBULL;
    for (int i = 0; i < 20; i++) rnd();
    int c = (L - 1) / 2, nv = skew ? c + 1 : L;
    vector<u64> z(nv); for (auto &q : z) q = rnd();
    const int TS = 1 << 16; vector<u64> tab(TS, 0); vector<int> stamp(TS, 0); int cur = 0;
    auto seen = [&](u64 h) { unsigned i = h & (TS - 1); while (stamp[i] == cur) { if (tab[i] == h) return true; i = (i + 1) & (TS - 1); } return false; };
    auto mark = [&](u64 h) { unsigned i = h & (TS - 1); while (stamp[i] == cur) i = (i + 1) & (TS - 1); stamp[i] = cur; tab[i] = h; };
    int walk = (int)(wf * (skew ? (L + 1) / 2 : L));
    auto t0 = chrono::steady_clock::now();
    auto now = [&] { return chrono::duration<double>(chrono::steady_clock::now() - t0).count(); };
    int best = 1 << 30; long long walks = 0, probes = 0, polished = 0; double base = 1e9;
    while (true) {
        if ((walks & 63) == 0 && now() > limit) break;
        walks++; cur++;
        memset(Pbuf, 0, sizeof(Pbuf));
        if (skew) {
            for (int i = 0; i <= c; i++) P[i] = (rnd() & 1) ? 1 : -1;
            for (int i = 1; i <= c; i++) P[c + i] = (i & 1 ? -1 : 1) * P[c - i];
        } else for (int i = 0; i < L; i++) P[i] = (rnd() & 1) ? 1 : -1;
        build();
        u64 h = rnd(); mark(h);
        for (int step = 0; step < walk; step++) {
            int be = 1 << 30, bi = -1, ties = 0;
            for (int i = 0; i < nv; i++) {
                if (seen(h ^ z[i])) continue;
                int e = (skew && i < c) ? eval2(i, L - 1 - i) : eval1(i);
                if (e < be) { be = e; bi = i; ties = 1; }
                else if (e == be && rnd(++ties) == 0) bi = i;
            }
            probes += nv;
            if (bi < 0) break;
            if (skew && bi < c) { flip(bi); flip(L - 1 - bi); } else flip(bi);
            h ^= z[bi]; mark(h);
            if (M) {
                // every window or extension of this skew sequence, polished if promising
                int8_t q[512]; vector<int8_t> res;
                int cnt = M > N ? M - N + 1 : 1 << (2 * 0 + (N - M));
                int ext = M < N ? N - M : 0;
                for (int v = 0; v < cnt * (ext ? ext + 1 : 1); v++) {
                    if (!ext) { for (int i = 0; i < N; i++) q[i] = (int8_t)P[v + i]; }
                    else {
                        int left = v / cnt, bits = v % cnt;   // left bits before, ext-left after
                        for (int i = 0; i < left; i++) q[i] = (bits >> i & 1) ? 1 : -1;
                        for (int i = 0; i < M; i++) q[left + i] = (int8_t)P[i];
                        for (int i = 0; i < ext - left; i++) q[left + M + i] = (bits >> (left + i) & 1) ? 1 : -1;
                    }
                    int qe = quick(q, N);
                    if (qe < base * (1 + margin)) {
                        int32_t saveP[1024], saveC[512]; memcpy(saveP, Pbuf, sizeof(Pbuf)); memcpy(saveC, Cbuf, sizeof(Cbuf));
                        int pe = polish(q, N, res);
                        memcpy(Pbuf, saveP, sizeof(Pbuf)); memcpy(Cbuf, saveC, sizeof(Cbuf));
                        polished++;
                        if (pe < base) base = pe;
                        if (pe < best) {
                            best = pe;
                            ofstream o(argv[3]); o << "# Energy: " << best << "\n# self avoiding walk search near skew length " << M << ", seed " << seed << "\n";
                            for (int i = 0; i < N; i++) o << (res[i] > 0 ? 1 : 0) << "\n";
                            printf("%.3f %d probes %lld\n", now(), best, probes); fflush(stdout);
                            if (best <= target) goto done;
                        }
                    }
                }
                continue;
            }
            if (be < best) {
                best = be;
                if (energy() != be) { fprintf(stderr, "energy mismatch\n"); return 3; }
                ofstream o(argv[3]); o << "# Energy: " << best << "\n# self avoiding walk search, seed " << seed << "\n";
                for (int i = 0; i < L; i++) o << (P[i] > 0 ? 1 : 0) << "\n";
                printf("%.3f %d probes %lld\n", now(), best, probes); fflush(stdout);
                if (best <= target) goto done;
            }
        }
    }
done:
    fprintf(stderr, "walks %lld probes %lld polished %lld best %d time %.1f\n", walks, probes, polished, best, now());
    return 0;
}
