"""Eigenschaftstests (metamorph) für den Nierentausch (ORACLE-PLAYBOOK §5.2, Verfahrenstyp Optimierung/Matching). Die vorhandenen Tests
vergleichen Kappung 2 mit zwei Aufzählungen und die Heuristik mit dem Brute-Force-Orakel auf festen Karten; hier wird die EINGABE verändert
und die Beziehung der Ausgaben geprüft. Für beliebige, kontrollierte Kompatibilitätsgraphen dient ein kleines Duck-Typing-Szenario (`G`)
mit denselben Schnittstellen wie `nt_scenario.Scenario` (n, n_alt, seed, edge_quality).

Exakte Größen (Kappung 2 mit Kettenlimit 1: `solve(sc, 2, 1)`, laut README exakt über Matching; Orakel `optimal_selection` für n <= 7) werden
auf Gleichheit geprüft, die Heuristik (Kappung 3, Kette 4) nur zwischen den sicheren Schranken Kappung-2-Optimum <= Heuristik <= Orakel.

1. Gültigkeit jeder Auswahl und individuelle Rationalität: Kandidaten paarweise disjunkt, jeder versorgte Patient erhält über eine vorhandene
   (kompatible) Kante einen Spender, Kreislängen 2..cap, Kettenlängen 1..chain_cap, Ketten beginnen bei einem altruistischen Spender,
   gemeldete Qualität = Summe der Kantenqualitäten; auf zufälligen Graphen und auf Karten des echten Generators.
2. Umnummerieren der Paare und altruistischen Spender: die Kandidatenmenge wird nur abgebildet, Kappung-2-Optimum und Orakel-Optimum bleiben
   gleich, Heuristik bleibt zwischen den Schranken.
3. Qualitäten mit c > 0 multipliziert: Patientenzahl gleich, Qualität c-fach (Kappung 2 und Orakel).
4. Alle Qualitäten um k verschoben: gleiche Patientenzahl, Qualität + k * Patientenzahl (jeder versorgte Patient entspricht genau einer Kante;
   Ziel ist lexikografisch erst Patienten, dann Qualität).
5. Zusätzliche Option verschlechtert das Optimum nie: weitere Kante, weiterer altruistischer Spender, größere Kreis- oder Kettengrenze; auf
   dem echten Generator senkt höhere Sensibilisierung die Optima nie (Kantenmenge schrumpft, Qualitäten bleiben).
6. Pfeile umkehren (ohne altruistische Spender): Kreise bleiben Kreise, Zahl der Kreise je Länge, Kappung-2- und Orakel-Optimum bleiben gleich.
7. Randfälle: leerer Pool, ein Paar, keine Kante, vollständiger Graph, nur altruistische Spender, gleiche Qualitäten (Gleichstände).
"""

import random
from dataclasses import replace

import pytest

import nt_scenario as S
from nt_exchange import generate_candidates, solve
from nt_oracle import optimal_selection


class G:
    """Kompatibilitätsgraph mit frei wählbaren Kanten: edges[(ist_altruistisch, Spender, Patient)] = Qualität."""

    def __init__(self, n, n_alt, edges, seed=1):
        self.n, self.n_alt, self.edges, self.seed = n, n_alt, dict(edges), seed

    def edge_quality(self, donor_idx, patient_idx, is_alt_donor):
        return self.edges.get((bool(is_alt_donor), donor_idx, patient_idx))


def rand_graph(rng, n, n_alt, p, qmax=99):
    edges = {}
    for d in range(n):
        for t in range(n):
            if d != t and rng.random() < p:
                edges[(False, d, t)] = rng.randint(40, qmax)
    for a in range(n_alt):
        for t in range(n):
            if rng.random() < p:
                edges[(True, a, t)] = rng.randint(40, qmax)
    return G(n, n_alt, edges, seed=rng.randint(1, 10 ** 6))


def graphs(seed, count, nmin=2, nmax=7, alt_max=2):
    rng = random.Random(seed)
    for _ in range(count):
        n = rng.randint(nmin, nmax)
        yield rand_graph(rng, n, rng.randint(0, alt_max), rng.choice([0.2, 0.4, 0.7]))


def value(res):
    return (sum(c.size for c in res.chosen), sum(c.quality for c in res.chosen))


def cap2(sc):
    return value(solve(sc, 2, 1))


def exact(sc, cap=3, chain=4):
    _, size, quality = optimal_selection(sc, cap, chain)
    return (size, quality)


def heuristic(sc, cap=3, chain=4):
    return value(solve(sc, cap, chain))


def transform(sc, f_edge, n_alt=None, n=None):
    return G(sc.n if n is None else n, sc.n_alt if n_alt is None else n_alt, {k: f_edge(k, q) for k, q in sc.edges.items()}, sc.seed)


def relabelled(sc, sigma, tau):
    return G(sc.n, sc.n_alt, {(a, tau[d] if a else sigma[d], sigma[t]): q for (a, d, t), q in sc.edges.items()}, sc.seed)


def canon(c, sigma=None, tau=None):
    pairs = list(c.pairs)
    alt = c.alt
    if sigma is not None:
        pairs = [sigma[p] for p in pairs]
        alt = tau[alt] if alt >= 0 else -1
    if c.kind == "cycle":
        k = pairs.index(min(pairs))
        pairs = pairs[k:] + pairs[:k]
    return (c.kind, tuple(pairs), alt, c.quality)


# --- 1. Gültigkeit und individuelle Rationalität ------------------------------------------------------------------------------


def check_valid(sc, res, cap, chain):
    used_pairs, used_alts = set(), set()
    patients = quality = 0
    for c in res.chosen:
        assert not (set(c.pairs) & used_pairs), "ein Paar zweimal versorgt"
        used_pairs |= set(c.pairs)
        if c.kind == "cycle":
            assert 2 <= len(c.pairs) <= cap and c.alt == -1
            q = 0
            for k, d in enumerate(c.pairs):
                t = c.pairs[(k + 1) % len(c.pairs)]
                e = sc.edge_quality(d, t, False)
                assert e is not None, "Kreis über nicht kompatible Kante"
                q += e
        else:
            assert 1 <= len(c.pairs) <= chain and c.alt >= 0 and c.alt not in used_alts
            used_alts.add(c.alt)
            q, donor, is_alt = 0, c.alt, True
            for t in c.pairs:
                e = sc.edge_quality(donor, t, is_alt)
                assert e is not None, "Kette über nicht kompatible Kante"
                q += e
                donor, is_alt = t, False
        assert q == c.quality
        patients += len(c.pairs)
        quality += q
    assert (patients, quality) == value(res)


def test_selection_is_valid_and_individually_rational_on_random_graphs():
    for k, sc in enumerate(graphs(11, 40, nmax=9, alt_max=3)):
        cap, chain = (2, 1) if k % 3 == 0 else (3, 4)
        check_valid(sc, solve(sc, cap, chain), cap, chain)


def test_selection_is_valid_on_the_real_generator():
    for seed in range(100000, 100030):
        sc = S.generate(8 + seed % 5, seed % 4, seed, 60)
        check_valid(sc, solve(sc, 3, 4), 3, 4)
        check_valid(sc, solve(sc, 2, 1), 2, 1)


# --- 2. Umnummerieren ---------------------------------------------------------------------------------------------------------


def test_relabeling_maps_candidates_and_keeps_exact_optima():
    rng = random.Random(22)
    for sc in graphs(22, 30, nmax=7):
        sigma, tau = list(range(sc.n)), list(range(sc.n_alt))
        rng.shuffle(sigma)
        rng.shuffle(tau)
        sc2 = relabelled(sc, sigma, tau)
        c1, _ = generate_candidates(sc, 3, 4)
        c2, _ = generate_candidates(sc2, 3, 4)
        assert len(c1) == len(c2)
        assert {canon(c, sigma, tau) for c in c1} == {canon(c) for c in c2}
        assert cap2(sc) == cap2(sc2)
        assert exact(sc) == exact(sc2)
        h1, h2 = heuristic(sc), heuristic(sc2)
        for h in (h1, h2):
            assert cap2(sc) <= h <= exact(sc)


# --- 3. Skalierung der Qualität -----------------------------------------------------------------------------------------------


def test_scaling_qualities_scales_quality_and_keeps_patients():
    rng = random.Random(33)
    for sc in graphs(33, 30, nmax=7):
        c = rng.choice([2, 3])
        sc2 = transform(sc, lambda k, q: c * q)
        (p1, q1), (p2, q2) = cap2(sc), cap2(sc2)
        assert p2 == p1 and q2 == c * q1
        (p1, q1), (p2, q2) = exact(sc), exact(sc2)
        assert p2 == p1 and q2 == c * q1


# --- 4. Verschiebung der Qualität ---------------------------------------------------------------------------------------------


def test_shifting_qualities_adds_k_per_served_patient():
    rng = random.Random(44)
    for sc in graphs(44, 30, nmax=7):
        k = rng.choice([1, 7, 50])
        sc2 = transform(sc, lambda key, q: q + k)
        (p1, q1), (p2, q2) = cap2(sc), cap2(sc2)
        assert p2 == p1 and q2 == q1 + k * p1
        (p1, q1), (p2, q2) = exact(sc), exact(sc2)
        assert p2 == p1 and q2 == q1 + k * p1


# --- 5. Zusätzliche Optionen --------------------------------------------------------------------------------------------------


def test_extra_options_never_hurt():
    rng = random.Random(55)
    done = 0
    for sc in graphs(55, 40, nmin=3, nmax=7):
        free = [(False, d, t) for d in range(sc.n) for t in range(sc.n) if d != t and (False, d, t) not in sc.edges]
        free += [(True, a, t) for a in range(sc.n_alt) for t in range(sc.n) if (True, a, t) not in sc.edges]
        if free:
            more = G(sc.n, sc.n_alt, {**sc.edges, rng.choice(free): rng.randint(40, 99)}, sc.seed)
            assert cap2(more) >= cap2(sc)
            assert exact(more) >= exact(sc)
            done += 1
        new_alt = rand_graph(rng, sc.n, sc.n_alt + 1, 0.4)
        merged = G(sc.n, sc.n_alt + 1, {**sc.edges, **{k: q for k, q in new_alt.edges.items() if k[0] and k[1] == sc.n_alt}}, sc.seed)
        assert cap2(merged) >= cap2(sc) and exact(merged) >= exact(sc)
        assert exact(sc, 3, 4) >= exact(sc, 2, 4) >= exact(sc, 2, 1)
        assert exact(sc, 3, 4) >= exact(sc, 3, 1) >= exact(sc, 2, 1)
    assert done >= 30


def test_higher_sensitization_never_helps_on_the_real_generator():
    changed = 0
    for seed in range(100000, 100040):
        sc = S.generate(5 + seed % 3, 1 + seed % 2, seed, 40)
        worse = replace(sc, sensitization=tuple(min(99, s + 30) for s in sc.sensitization))
        assert cap2(worse) <= cap2(sc)
        assert exact(worse) <= exact(sc)
        changed += cap2(worse) != cap2(sc)
    assert changed >= 3


def test_removing_an_altruistic_donor_never_helps_on_the_real_generator():
    for seed in range(100000, 100030):
        sc = S.generate(6 + seed % 2, 2, seed, 40)
        fewer = replace(sc, alt_type=sc.alt_type[:1])
        assert cap2(fewer) <= cap2(sc)
        assert exact(fewer) <= exact(sc)


# --- 6. Pfeile umkehren (ohne altruistische Spender) -------------------------------------------------------------------------


def test_reversing_all_arcs_keeps_cycle_counts_and_optima():
    for sc in graphs(66, 30, nmax=7, alt_max=0):
        rev = G(sc.n, 0, {(False, t, d): q for (a, d, t), q in sc.edges.items()}, sc.seed)
        c1, _ = generate_candidates(sc, 3, 4)
        c2, _ = generate_candidates(rev, 3, 4)
        for length in (2, 3):
            assert sum(1 for c in c1 if c.size == length) == sum(1 for c in c2 if c.size == length)
        assert cap2(sc) == cap2(rev)
        assert exact(sc) == exact(rev)


# --- 7. Randfälle -------------------------------------------------------------------------------------------------------------


def test_edge_cases():
    assert cap2(G(0, 0, {})) == (0, 0) and heuristic(G(0, 0, {})) == (0, 0)
    assert exact(G(0, 0, {})) == (0, 0)
    assert heuristic(G(1, 0, {})) == (0, 0)                                              # ein Paar kann nicht mit sich selbst tauschen
    assert heuristic(G(5, 2, {})) == (0, 0)                                              # keine einzige kompatible Kante
    assert heuristic(G(3, 0, {(False, 0, 1): 50, (False, 1, 2): 60})) == (0, 0)          # Kette von Pfeilen ohne Rückkehr ist kein Kreis
    assert heuristic(G(2, 0, {(False, 0, 1): 50, (False, 1, 0): 60})) == (2, 110)         # einfacher Paartausch
    only_alt = G(2, 1, {(True, 0, 0): 45, (False, 0, 1): 55})                            # nur eine Kette: alt -> 0 -> 1
    assert heuristic(only_alt) == (2, 100) and cap2(only_alt) == (1, 45)
    complete = G(5, 0, {(False, d, t): 70 for d in range(5) for t in range(5) if d != t})  # lauter gleiche Qualitäten: Gleichstände
    assert cap2(complete) == (4, 280) and exact(complete) == (5, 350) == heuristic(complete)
    assert exact(complete, 2, 1) == (4, 280)
