"""Kern-Tests: die zwei von Hand nachvollzogenen Lehrbuchkarten NAMENTLICH (nicht nur aggregierte Zahlen - Lehre aus
`stabile-mitbewohner-demo`), Kappung-2-Exaktheit gegen das Orakel, Heuristik-Genauigkeit (EHRLICH berichtet, nicht
auf 0 Abweichungen geschönt), Negativkontrollen, Kopierwächter."""

import nt_constants as C
import nt_oracle as O
import nt_scenario as S
from nt_exchange import solve
from nt_scenario import ABO_COMPAT, SplitMix64


# --- die von Hand nachvollzogenen Lehrbuchkarten, NAMENTLICH ----------------------------------------------------------

def test_chain_example_matches_the_hand_trace():
    """n=6, 1 altruistischer Spender (Seed 100005): bei reinem Paartausch nur 1 Patient (Kette alt->3, Qualität 77).
    Mit Kettenlimit 4 verlängert sich die Kette auf alt->5->1->4->0 (4 Patienten, Qualität 286) - der GESAMTE
    Zugewinn kommt allein aus der Kette, kein Kreis beteiligt."""
    sc = S.chain_example()
    res2 = solve(sc, 2, 1)
    cap2 = next(a for a in res2.attempts if a[0] == "cap2")
    assert cap2[1] == 1 and cap2[2] == 77

    res = solve(sc, 3, 4)
    assert sum(c.size for c in res.chosen) == 4
    assert sum(c.quality for c in res.chosen) == 286
    assert all(c.kind == "chain" for c in res.chosen)
    chain = res.chosen[0]
    assert chain.alt == 0 and chain.pairs == (5, 1, 4, 0)


def test_cycle_example_matches_the_hand_trace():
    """n=6, 1 altruistischer Spender (Seed 100031), als Kontrast: bei Kappung 2 ein 2er-Kreis {1,4} (2 Patienten,
    Qualität 93). Bei Kappung 3 ersetzt ihn ein 3er-Kreis {1,3,4} (3 Patienten, Qualität 183) - hier kommt der
    Zugewinn rein aus der Kreislänge, keine Kette beteiligt."""
    sc = S.cycle_example()
    res2 = solve(sc, 2, 1)
    cap2 = next(a for a in res2.attempts if a[0] == "cap2")
    assert cap2[1] == 2 and cap2[2] == 93

    res = solve(sc, 3, 1)
    assert sum(c.size for c in res.chosen) == 3
    assert sum(c.quality for c in res.chosen) == 183
    assert all(c.kind == "cycle" for c in res.chosen)
    assert res.chosen[0].pairs == (1, 3, 4)


def test_both_examples_agree_with_the_independent_oracle():
    for card_fn, cap, chain_cap, exp_size, exp_q in ((S.chain_example, 3, 4, 4, 286), (S.cycle_example, 3, 1, 3, 183)):
        sc = card_fn()
        _, opt_size, opt_q = O.optimal_selection(sc, cap, chain_cap)
        assert (opt_size, opt_q) == (exp_size, exp_q)


# --- Kappung 2 ist exakt (Maximum-Weight-Matching) ----------------------------------------------------------------------

def test_cap2_matches_the_oracle_exactly():
    """60 unabhängige Kreuzprüfungen (n=4..9): Kappung 2 (`nt_blossom.py`) ist beweisbar exakt - 0 Abweichungen
    erwartet, hier selbst nachgerechnet."""
    total = mismatches = 0
    for n in (4, 5, 6, 7, 8, 9):
        for sd in C.DIST_SEEDS[:10]:
            sc = S.generate(n, max(1, n // 4), sd, 60)
            res = solve(sc, 2, 1)
            cap2 = next(a for a in res.attempts if a[0] == "cap2")
            _, opt_size, opt_q = O.optimal_selection(sc, 2, 1)
            total += 1
            if (cap2[1], cap2[2]) != (opt_size, opt_q):
                mismatches += 1
    assert total == 60
    assert mismatches == 0


# --- Heuristik-Genauigkeit, EHRLICH berichtet (Lehre: nie auf "0 Abweichungen" schönen) -----------------------------

def test_heuristic_accuracy_is_honestly_reported():
    """80 Kreuzprüfungen (n=6..9, 20 feste Karten): die Mehrfachstart-Heuristik ist NICHT immer exakt - der
    tatsächliche Trefferanteil wird geprüft, nicht auf 0 Abweichungen geschönt."""
    from nt_evaluation import heuristic_accuracy
    r = heuristic_accuracy(60)
    assert r["total"] == 80
    assert r["exact"] == 58                 # ehrlich: NICHT 80/80
    assert r["mean_gap"] == 0.15
    assert r["max_gap"] == 2


def test_safety_net_guarantees_general_mode_never_loses_to_cap2():
    """Über 100 feste Karten: die volle Mehrfachstart-Heuristik MIT Sicherheitsnetz unterbietet nie das exakte
    Kappung-2-Ergebnis (0 von 100) - ohne Sicherheitsnetz passiert das real (siehe test_naive_can_lose_to_cap2)."""
    losses = 0
    for sd in C.DIST_SEEDS:
        sc = S.generate(25, 3, sd, 60)
        res = solve(sc, 3, 4)
        cap2 = next(a for a in res.attempts if a[0] == "cap2")
        best = (sum(c.size for c in res.chosen), sum(c.quality for c in res.chosen))
        if best < (cap2[1], cap2[2]):
            losses += 1
    assert losses == 0


def test_naive_single_order_greedy_can_lose_to_cap2_without_the_safety_net():
    """Reale, gemessene Warnung (siehe Plan/README): eine EINFACHE, unsortierte Greedy-Reihenfolge (ohne
    Mehrfachstart, ohne Sicherheitsnetz) verliert auf 58 von 100 Standardkarten gegen die exakte Kappung-2-Lösung -
    obwohl ihr Kandidatenraum strikt größer ist. Genau deshalb ist das Sicherheitsnetz nicht optional."""
    from nt_evaluation import naive_vs_cap2
    r = naive_vs_cap2(25, 3, 60)
    assert r["total"] == 100
    assert r["naive_losses"] == 58
    assert r["multi_losses"] == 0


# --- Negativkontrollen ---------------------------------------------------------------------------------------------

def test_isolated_pair_stays_unmatched():
    """Ein Paar ohne jede Kompatibilitätskante bleibt in jedem Modus unversorgt."""
    sc = S.generate(20, 2, 100000, 60)
    res = solve(sc, 3, 4)
    matched = {p for c in res.chosen for p in c.pairs}
    all_pairs_in_candidates = set()
    from nt_exchange import generate_candidates
    cands, _ = generate_candidates(sc, 3, 4)
    for c in cands:
        all_pairs_in_candidates.update(c.pairs)
    isolated = set(range(sc.n)) - all_pairs_in_candidates
    assert not (isolated & matched)


def test_empty_pool_solves_to_nothing():
    sc = S.Scenario((), (), (), (), 0, 60)
    res = solve(sc, 3, 4)
    assert res.chosen == ()
    assert res.n_candidates == 0


def test_no_altruistic_donors_means_no_chains():
    sc = S.generate(20, 0, 100000, 60)
    res = solve(sc, 3, 4)
    assert all(c.kind == "cycle" for c in res.chosen)


def test_abo_table_matches_the_medical_convention():
    """UNOS/National Kidney Foundation/Cedars-Sinai: O -> jeder, A -> A/AB, B -> B/AB, AB -> nur AB."""
    O_, A_, B_, AB_ = 0, 1, 2, 3
    assert ABO_COMPAT[O_] == (True, True, True, True)
    assert ABO_COMPAT[A_] == (False, True, False, True)
    assert ABO_COMPAT[B_] == (False, False, True, True)
    assert ABO_COMPAT[AB_] == (False, False, False, True)


def test_both_pool_entry_paths_actually_occur():
    """Real geprüft (nicht nur theoretisch möglich): unter den erzeugten Paaren gibt es sowohl ABO-unverträgliche
    als auch ABO-VERTRÄGLICHE (nur am Crossmatch gescheiterte) Kombinationen - ohne den zweiten Pfad wäre der Pool
    wieder fast bipartit (siehe `test_sens_max_zero_reproduces_the_near_bipartite_structure` in
    test_scenario_and_evaluation.py)."""
    sc = S.generate(2000, 0, 100000, 60)
    abo_incompatible = sum(1 for i in range(sc.n) if not ABO_COMPAT[sc.donor_type[i]][sc.patient_type[i]])
    abo_compatible_crossmatch_failed = sc.n - abo_incompatible
    assert abo_incompatible > 0
    assert abo_compatible_crossmatch_failed > 0


# --- Kopierwächter --------------------------------------------------------------------------------------------------

def test_splitmix64_vector():
    rng = SplitMix64(42)
    assert [rng.next() for _ in range(3)] == [13679457532755275413, 2949826092126892291, 5139283748462763858]


def test_blood_weights_sum_to_100_and_match_stanford_aabb():
    assert sum(S.BLOOD_WEIGHTS) == 100
    assert S.BLOOD_WEIGHTS == (44, 42, 10, 4)


def test_generate_is_reproducible():
    sc1 = S.generate(20, 3, 97, 60)
    sc2 = S.generate(20, 3, 97, 60)
    assert sc1 == sc2
