"""Szenario- und Auswertungsmodule: Struktur, Konsistenz, feste Karten."""

import nt_constants as C
import nt_evaluation as ev
import nt_scenario as S
from nt_scenario import ABO_COMPAT


def test_incompatible_pairs_are_never_abo_and_crossmatch_ok_simultaneously():
    """Jedes erzeugte Paar hat einen Spender, der entweder ABO-unverträglich ist ODER dessen ABO-Verträglichkeit nur
    deshalb im Pool landet, weil die Erzeugung selbst das Crossmatch scheitern ließ (kann nicht direkt am fertigen
    Paar nachgeprüft werden, da der Erzeugungs-Wurf nicht gespeichert wird - stattdessen wird die STRUKTURELLE
    Konsequenz geprüft: alle vier Blutgruppen kommen sowohl als Spender- als auch als Patiententyp vor, was bei
    reiner ABO-Ausschlussregel unmöglich wäre, siehe `nt_scenario.py`s Moduldoku)."""
    sc = S.generate(3000, 0, 100000, 60)
    donor_types = set(sc.donor_type)
    patient_types = set(sc.patient_type)
    assert donor_types == {0, 1, 2, 3}          # inkl. O-Spender (bei reiner ABO-Regel strukturell unmöglich)
    assert patient_types == {0, 1, 2, 3}        # inkl. AB-Patienten (bei reiner ABO-Regel strukturell unmöglich)


def test_o_donors_are_underrepresented_relative_to_population():
    """Realer, in Kidney-Paired-Donation-Registern bekannter Selektionseffekt: O-Spender sind unter den
    unverträglichen Paaren gegenüber ihrem Bevölkerungsanteil (44 %) unterrepräsentiert - kein Fehler."""
    sc = S.generate(3000, 0, 100000, 60)
    o_share = sum(1 for t in sc.donor_type if t == 0) / sc.n
    assert o_share < 0.35


def test_ab_patients_are_rare_but_possible():
    sc = S.generate(3000, 0, 100000, 60)
    ab_share = sum(1 for t in sc.patient_type if t == 3) / sc.n
    assert 0.0 < ab_share < 0.10


def test_sens_max_zero_reproduces_the_near_bipartite_structure():
    """Negativkontrolle/Erklärung: OHNE die Crossmatch-Regel (sens_max=0) ist der Pool wieder fast bipartit - O-
    Spender und AB-Patienten verschwinden fast vollständig, 3er-Kreise werden extrem selten."""
    sc = S.generate(2000, 0, 100000, 0)
    o_share = sum(1 for t in sc.donor_type if t == 0) / sc.n
    assert o_share == 0.0


def test_edge_quality_is_reproducible():
    sc = S.generate(20, 2, 55, 60)
    q1 = sc.edge_quality(0, 5, False)
    q2 = sc.edge_quality(0, 5, False)
    assert q1 == q2


def test_analyse_and_verdict_roundtrip():
    sc = S.generate(25, 3, C.DEFAULT_SEED, 60)
    a = ev.analyse(sc, 3, 4)
    d = ev.verdict(a)
    assert d["n"] == 25
    assert 0 <= d["matched"] <= 25
    assert d["gain_over_cap2"] >= 0


def test_distribution_shape():
    d = ev.distribution(10, 2, 60, 2, 1, C.DIST_SEEDS[:20])
    assert d["n_seeds"] == 20
    assert 0 <= d["matched_share"]["mean"] <= 1
    assert abs(sum(d["length_hist_share"].values()) - 1.0) < 1e-9


def test_altruistic_contribution_is_non_negative_on_average():
    r = ev.altruistic_contribution(20, 60, 3, 3, 4, C.DIST_SEEDS[:20])
    assert r["matched_gain"]["mean"] >= 0


def test_effort_scaling_grows_with_n():
    rows = ev.effort_scaling(60, (10, 20, 25), C.DIST_SEEDS[:3])
    steps = [r["steps"] for r in rows]
    assert steps == sorted(steps)
