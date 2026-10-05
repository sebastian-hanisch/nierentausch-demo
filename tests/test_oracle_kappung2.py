"""Unabhängiges Orakel (reine Aufzählung, kein Blossom, kein Greedy): Kappung 2 muss das LEXIKOGRAFISCHE Optimum treffen
(zuerst Patientenzahl, dann Qualität), und die Kandidatenerzeugung muss mit einer Permutations-Aufzählung übereinstimmen.

Regression: ein reines Qualitätsgewicht im Matching (Summe der Kantenqualitäten 40-99) wählte auf manchen Karten zwei
hochwertige Kanten statt drei etwas schlechterer, verschenkte also Patienten (z. B. n=6, Seed 52: 2 statt 3 Patienten).
Das Orakel (`scipy.optimize.milp` / `networkx.max_weight_matching` in der Vorab-Messung) lag auf 2 von 100 festen Karten
(n=25) anders als die Demo; die 60 kleinen Karten in test_exchange.py hatten das nie getroffen."""

from itertools import permutations

import nt_scenario as S
from nt_exchange import generate_candidates, solve


def _best_matching(sc):
    """Lexikografisch bestes Matching (Patienten, Qualität) durch vollständige Aufzählung aller Kantenmengen."""
    edges = []
    for i in range(sc.n):
        for j in range(i + 1, sc.n):
            a, b = sc.edge_quality(i, j, False), sc.edge_quality(j, i, False)
            if a is not None and b is not None:
                edges.append((("p", i), ("p", j), 2, a + b))
    for a in range(sc.n_alt):
        for p in range(sc.n):
            q = sc.edge_quality(a, p, True)
            if q is not None:
                edges.append((("a", a), ("p", p), 1, q))
    best = [(0, 0)]

    def rec(k, used, size, quality):
        best[0] = max(best[0], (size, quality))
        for t in range(k, len(edges)):
            u, v, sz, q = edges[t]
            if u not in used and v not in used:
                rec(t + 1, used | {u, v}, size + sz, quality + q)

    rec(0, frozenset(), 0, 0)
    return best[0]


def test_cap2_is_lexicographically_optimal_on_known_trouble_cards():
    for n, seed in ((6, 52), (6, 238), (7, 222), (8, 3)):
        sc = S.generate(n, 2, seed, 60)
        cap2 = next(a for a in solve(sc, 2, 1).attempts if a[0] == "cap2")
        assert (cap2[1], cap2[2]) == _best_matching(sc), (n, seed)


def test_cap2_is_lexicographically_optimal_on_random_small_cards():
    for sd in range(100, 160):
        n = 4 + sd % 5
        sc = S.generate(n, sd % 3, sd, (30, 60, 90)[sd % 3])
        cap2 = next(a for a in solve(sc, 2, 1).attempts if a[0] == "cap2")
        assert (cap2[1], cap2[2]) == _best_matching(sc), (n, sd)


def test_general_mode_never_below_exact_cap2_optimum():
    for sd in range(200, 230):
        sc = S.generate(6 + sd % 4, 1, sd, 60)
        res = solve(sc, 3, 4)
        got = (sum(c.size for c in res.chosen), sum(c.quality for c in res.chosen))
        assert got >= _best_matching(sc)


def _permutation_candidates(sc, cap, chain_cap):
    """Kreise (Länge 2..cap) und Ketten (1..chain_cap) über Permutationen statt Tiefensuche."""
    out = set()
    for L in range(2, cap + 1):
        for perm in permutations(range(sc.n), L):
            if perm[0] != min(perm):
                continue
            qs = [sc.edge_quality(perm[k], perm[(k + 1) % L], False) for k in range(L)]
            if None not in qs:
                out.add(("cycle", perm, -1, sum(qs)))
    for a in range(sc.n_alt):
        for L in range(1, chain_cap + 1):
            for perm in permutations(range(sc.n), L):
                qs = [sc.edge_quality(a, perm[0], True)] + [sc.edge_quality(perm[k], perm[k + 1], False) for k in range(L - 1)]
                if None not in qs:
                    out.add(("chain", perm, a, sum(qs)))
    return out


def test_candidate_generation_matches_permutation_enumeration():
    for sd in range(300, 312):
        sc = S.generate(6, 2, sd, 30)
        cands, _ = generate_candidates(sc, 3, 3)
        got = [(c.kind, c.pairs, c.alt, c.quality) for c in cands]
        assert len(got) == len(set(got))
        assert set(got) == _permutation_candidates(sc, 3, 3)
