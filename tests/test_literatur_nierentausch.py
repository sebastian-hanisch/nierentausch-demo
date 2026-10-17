"""Literatur-Referenzwerte für den Nierentausch (ORACLE-PLAYBOOK §5.1).

Quellen (alle am 2026-10-17 eingesehen; Werte aus der Quelle, nicht aus dem Code der Demo):

1. National Kidney Foundation, "What Blood Types Match?", https://www.kidney.org/transplantation/livingdonors/what-blood-types-match
   (Abruf 2026-10-17): Lebendspende Niere, Spender -> Empfänger: O -> A, B, AB, O; A -> A, AB; B -> B, AB; AB -> nur AB; Rhesusfaktor
   muss laut Seite nicht passen (so auch im README der Demo). Prüft die ABO-Tabelle `nt_scenario.ABO_COMPAT` gegen die Quelle.
2. Roth, Sönmez & Ünver, "Pairwise Kidney Exchange", NBER Working Paper 10698 (August 2004),
   https://nber.org/system/files/working_papers/w10698/w10698.pdf (PDF-Text selbst extrahiert und gelesen): Lemma 1 (gedruckte Seite 7):
   für je zwei Pareto-effiziente Matchings gilt gleiche Größe, und bei Tausch zwischen mehr als zwei Paaren gilt das nicht mehr; Seite 9
   (Absatz nach Proposition 1): zwei Patienten, die nur mit demselben dritten gegenseitig verträglich sind, schließen sich gegenseitig aus
   (sinngemäß wiedergegeben), und nach Lemma 1 gibt es keinen Zielkonflikt zwischen Priorität und Zahl der Transplantationen. Übertragen
   auf Kappung 2 ohne altruistische Spender: ein Stern aus drei Paaren erlaubt genau einen Paartausch (2 Patienten, von Hand), und die Zahl
   versorgter Patienten hängt nicht von den Qualitäten ab.
   Gelesen wurden nur diese Aussagen; ein Zahlenbeispiel mit Lösung enthält die Arbeit in dieser Fassung für das Modell der Demo nicht
   (Example 1 betrifft Präferenzen mit Prioritäten, nicht Qualitäten).

Nicht eingesehen oder nicht eindeutig (kein Test): Abraham, Blum & Sandholm (2007) zur NP-Schwere bei Kreisen ab Länge 3 (nur Zitat);
die Blutgruppenhäufigkeiten (O 44 %, A 42 %, B 10 %, AB 4 %; Stanford Blood Center nach AABB Technical Manual 18. Aufl.): die Stanford-Seite
war am 2026-10-17 unter der bekannten URL nicht abrufbar, nur über Sekundärseiten (Rhesus-Summen 37,4 + 6,6 = 44 usw.) gesehen.
"""

import itertools
import random

import nt_scenario as S
from nt_exchange import solve


class G:
    def __init__(self, n, n_alt, edges, seed=1):
        self.n, self.n_alt, self.edges, self.seed = n, n_alt, dict(edges), seed

    def edge_quality(self, donor_idx, patient_idx, is_alt_donor):
        return self.edges.get((bool(is_alt_donor), donor_idx, patient_idx))


def patients(sc, cap=2, chain=1):
    return sum(c.size for c in solve(sc, cap, chain).chosen)


def test_abo_table_matches_kidney_org():
    O, A, B, AB = S.O, S.A, S.B, S.AB
    expected = {O: {O, A, B, AB}, A: {A, AB}, B: {B, AB}, AB: {AB}}      # Spender -> Empfänger laut Quelle 1
    for donor in range(4):
        got = {r for r in range(4) if S.ABO_COMPAT[donor][r]}
        assert got == expected[donor], donor
    # umgekehrt gelesen (Empfänger -> mögliche Spender), wie auf der Seite: O nur von O, A von A/O, B von B/O, AB von jedem
    from_donors = {r: {d for d in range(4) if S.ABO_COMPAT[d][r]} for r in range(4)}
    assert from_donors == {O: {O}, A: {A, O}, B: {B, O}, AB: {O, A, B, AB}}


def test_star_of_three_pairs_allows_exactly_one_pairwise_exchange():
    """Paar 2 ist mit Paar 0 und mit Paar 1 gegenseitig verträglich, 0 und 1 untereinander nicht (Quelle 2, Seite 9). Genau ein Tausch (2 Patienten),
    der mit der höheren Qualität gewinnt; auch Kreislänge 3 ändert nichts, da kein Dreierkreis existiert."""
    edges = {(False, 0, 2): 60, (False, 2, 0): 70, (False, 1, 2): 90, (False, 2, 1): 80}
    sc = G(3, 0, edges)
    res = solve(sc, 2, 1)
    assert [c.pairs for c in res.chosen if c.kind == "cycle"] in ([(1, 2)], [(2, 1)])
    assert sum(c.size for c in res.chosen) == 2 and sum(c.quality for c in res.chosen) == 170
    assert patients(sc, 3, 4) == 2


def test_number_of_patients_does_not_depend_on_the_qualities_in_pairwise_exchange():
    """Quelle 2 (Lemma 1, Seite 7): jedes effiziente Matching versorgt dieselbe Zahl Patienten, es gibt keinen Zielkonflikt zwischen Qualität/Priorität und Zahl.
    Hier: Zahl versorgter Patienten bei Kappung 2 = 2 * (größte Paarzahl im Graphen der gegenseitigen Verträglichkeit), unabhängig von den Qualitäten
    (von Hand per Aufzählung gerechnet, nicht mit dem Code der Demo)."""
    def max_pairs(n, mutual):
        best = 0

        def rec(k, used, size):
            nonlocal best
            best = max(best, size)
            for t in range(k, len(mutual)):
                a, b = mutual[t]
                if a not in used and b not in used:
                    rec(t + 1, used | {a, b}, size + 1)
        rec(0, frozenset(), 0)
        return best

    rng = random.Random(77)
    for _ in range(30):
        n = rng.randint(3, 8)
        arcs = [(d, t) for d, t in itertools.permutations(range(n), 2) if rng.random() < 0.45]
        mutual = [(a, b) for a, b in itertools.combinations(range(n), 2) if (a, b) in arcs and (b, a) in arcs]
        want = 2 * max_pairs(n, mutual)
        for _ in range(3):
            sc = G(n, 0, {(False, d, t): rng.randint(40, 99) for d, t in arcs})
            assert patients(sc) == want
