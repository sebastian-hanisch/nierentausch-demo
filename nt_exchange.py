"""Kandidatenerzeugung + Auswahl von Kreisen/Ketten unter einer Längenkappung K (Kreise) und einem Kettenlimit
(Ketten, gestartet von einem altruistischen Spender). Kappung 2 (reiner Paartausch + Ketten der Länge 1) ist EXAKT
lösbar (`nt_blossom.py`, Reduktion auf Maximum-Weight-Matching, siehe README). Kreislänge >= 3 ist NP-schwer
(Abraham, Blum & Sandholm 2007) - die hier verwendete Mehrfachstart-Greedy-Heuristik hat KEINEN Optimalitätsbeweis;
ihre gemessene Lücke gegen `nt_oracle.py` (nur kleine n, in den Tests) ist die App eigener, ehrlicher Beweis ihrer
Grenzen, kein Makel, der versteckt wird.

**Sicherheitsnetz, real gemessen als notwendig (siehe Plan/README):** ohne es kann der allgemeine (K>=3 und/oder
Kettenlimit > 1) Modus sichtbar SCHLECHTER abschneiden als der eingeschränkte, aber exakt gelöste Kappung-2-
Spezialfall - eine naive Greedy-Sortierung verlor in Messungen 37 von 100 Karten gegen die exakte Kappung-2-Lösung,
obwohl ihr Kandidatenraum strikt größer war. Deshalb wird das exakte Kappung-2-Ergebnis IMMER als zusätzlicher
Kandidat mitgeführt (`_cap2_candidate`) und nur verworfen, wenn die Heuristik selbst mindestens ebenso gut abschnitt.

Aufwand = gezählte Operationen (erzeugte Kandidaten + geprüfte Kombinationsschritte), nie Sekunden."""

from dataclasses import dataclass

import nt_blossom as BL
from nt_scenario import SplitMix64

GREEDY_ORDERS = (
    ("size_then_quality", lambda c: (-c.size, -c.quality)),
    ("quality_then_size", lambda c: (-c.quality, -c.size)),
    ("ratio", lambda c: (-c.quality / c.size, -c.size)),
)
N_RANDOM_RESTARTS = 8
RESTART_STREAM_XOR = 0x524553544152545F


@dataclass(frozen=True)
class Candidate:
    kind: str           # "cycle" oder "chain"
    pairs: tuple          # beteiligte Paar-Indizes, in Reihenfolge des Kreises/der Kette
    alt: int                # altruistischer Spender-Index (nur bei Ketten), sonst -1
    quality: int

    @property
    def size(self):
        return len(self.pairs)


def _edges_by_donor(sc):
    """pair_edges[i] = [(Patient j, Qualität), ...] von Paar i's Spender; alt_edges[a] = ... von altrustischem Spender a."""
    pair_edges = [[] for _ in range(sc.n)]
    alt_edges = [[] for _ in range(sc.n_alt)]
    for i in range(sc.n):
        for p in range(sc.n):
            if i == p:
                continue
            q = sc.edge_quality(i, p, False)
            if q is not None:
                pair_edges[i].append((p, q))
    for a in range(sc.n_alt):
        for p in range(sc.n):
            q = sc.edge_quality(a, p, True)
            if q is not None:
                alt_edges[a].append((p, q))
    return pair_edges, alt_edges


def generate_candidates(sc, cap, chain_cap):
    """Alle Kreise (Länge 2..cap) und Ketten (Länge 1..chain_cap). Reines Aufzählen, kein Pruning nach Güte."""
    pair_edges, alt_edges = _edges_by_donor(sc)
    candidates = []
    ops = 0

    def dfs_cycle(start, cur, path, quality_sum, depth):
        nonlocal ops
        for nxt, q in pair_edges[cur]:
            ops += 1
            if nxt == start and depth >= 1:
                candidates.append(Candidate("cycle", tuple(path), -1, quality_sum + q))
                continue
            if nxt > start and nxt not in path and depth + 1 < cap:
                dfs_cycle(start, nxt, path + [nxt], quality_sum + q, depth + 1)

    for start in range(sc.n):
        dfs_cycle(start, start, [start], 0, 0)

    def dfs_chain(alt, cur_donor_is_alt, cur, path, quality_sum, depth):
        nonlocal ops
        edges = alt_edges[alt] if cur_donor_is_alt else pair_edges[cur]
        for nxt, q in edges:
            ops += 1
            if nxt in path:
                continue
            new_path = path + [nxt]
            candidates.append(Candidate("chain", tuple(new_path), alt, quality_sum + q))
            if depth + 1 < chain_cap:
                dfs_chain(alt, False, nxt, new_path, quality_sum + q, depth + 1)

    for a in range(sc.n_alt):
        dfs_chain(a, True, -1, [], 0, 0)

    return candidates, ops


def _conflicts(chosen_pairs, chosen_alts, c):
    if c.alt >= 0 and c.alt in chosen_alts:
        return True
    return any(p in chosen_pairs for p in c.pairs)


def _greedy(candidates, order_key):
    ordered = sorted(candidates, key=order_key)
    chosen, chosen_pairs, chosen_alts, ops = [], set(), set(), 0
    for c in ordered:
        ops += 1
        if not _conflicts(chosen_pairs, chosen_alts, c):
            chosen.append(c)
            chosen_pairs.update(c.pairs)
            if c.alt >= 0:
                chosen_alts.add(c.alt)
    return chosen, ops


def _shuffle(items, rng):
    items = list(items)
    for i in range(len(items) - 1, 0, -1):
        j = rng.below(i + 1)
        items[i], items[j] = items[j], items[i]
    return items


def _score(chosen):
    return (sum(c.size for c in chosen), sum(c.quality for c in chosen))


def _cap2_as_candidates(sc):
    """Löst Kappung 2 exakt (`nt_blossom.py`) und übersetzt das Ergebnis in Candidate-Objekte fürs Sicherheitsnetz."""
    ms = _build_match_scenario(sc)
    if ms.n == 0 or not any(ms.adj):
        return []
    res = BL.run(ms, maxcardinality=False, record=False)
    out = []
    for i, j in res.pairs:
        lbl_i, lbl_j = ms.labels[i], ms.labels[j]
        q = -int(ms.cost[i, j])
        if lbl_i[0] == "alt":
            out.append(Candidate("chain", (lbl_j[1],), lbl_i[1], q))
        elif lbl_j[0] == "alt":
            out.append(Candidate("chain", (lbl_i[1],), lbl_j[1], q))
        else:
            out.append(Candidate("cycle", (lbl_i[1], lbl_j[1]), -1, q))
    return out


@dataclass(frozen=True)
class MatchScenario:
    n: int
    adj: tuple
    cost: object
    labels: tuple    # labels[node] = ("pair", i) oder ("alt", a)


def _build_match_scenario(sc):
    """Ungerichteter Hilfsgraph für Kappung 2: Knoten = Paare + altruistische Spender. Kante Paar i - Paar j nur bei
    GEGENSEITIGER Verträglichkeit (Gewicht = Summe beider Qualitäten als NEGATIVE Kosten, siehe `nt_blossom.py`s
    Dokumentation - `maxcardinality=False` + `cost = -Qualität` maximiert Qualität direkt, ohne Kardinalitätszwang
    und ohne den (maxcost+1)-Trick, der hier fehl am Platz wäre). Kante altruistischer Spender a - Paar i bei
    einseitiger Verträglichkeit (Domino-Spende, Kettenlänge 1)."""
    import numpy as np
    n_pairs, n_alt = sc.n, sc.n_alt
    n = n_pairs + n_alt
    labels = tuple([("pair", i) for i in range(n_pairs)] + [("alt", a) for a in range(n_alt)])
    cost = np.zeros((n, n), dtype=np.int64)
    adj = [[] for _ in range(n)]
    for i in range(n_pairs):
        for j in range(i + 1, n_pairs):
            q_ij = sc.edge_quality(i, j, False)
            q_ji = sc.edge_quality(j, i, False)
            if q_ij is not None and q_ji is not None:
                cost[i, j] = cost[j, i] = -(q_ij + q_ji)
                adj[i].append(j)
                adj[j].append(i)
    for a in range(n_alt):
        node_a = n_pairs + a
        for i in range(n_pairs):
            q = sc.edge_quality(a, i, True)
            if q is not None:
                cost[node_a, i] = cost[i, node_a] = -q
                adj[node_a].append(i)
                adj[i].append(node_a)
    adj = [sorted(a) for a in adj]
    return MatchScenario(n, tuple(adj), cost, labels)


@dataclass(frozen=True)
class Result:
    chosen: tuple         # gewählte Candidate-Objekte
    source: str             # "cap2" oder ein GREEDY_ORDERS-Name oder "random_<k>" - welcher Versuch gewonnen hat
    steps: int
    n_candidates: int
    attempts: tuple          # ((Quelle, Anzahl Patienten, Qualität), ...) - jeder Versuch, für die Auswertung


def solve(sc, cap, chain_cap, record=True):
    candidates, gen_ops = generate_candidates(sc, cap, chain_cap)
    attempts = []
    best_chosen, best_source, best_score, total_ops = (), "none", (0, 0), gen_ops

    cap2_cands = _cap2_as_candidates(sc)
    chosen, ops = _greedy(cap2_cands, lambda c: (-c.size, -c.quality))
    total_ops += ops
    score = _score(chosen)
    attempts.append(("cap2", score[0], score[1]))
    if score > best_score:
        best_chosen, best_source, best_score = tuple(chosen), "cap2", score

    for name, key in GREEDY_ORDERS:
        chosen, ops = _greedy(candidates, key)
        total_ops += ops
        score = _score(chosen)
        attempts.append((name, score[0], score[1]))
        if score > best_score:
            best_chosen, best_source, best_score = tuple(chosen), name, score

    rng = SplitMix64(sc.seed ^ RESTART_STREAM_XOR)
    for k in range(N_RANDOM_RESTARTS):
        shuffled = _shuffle(candidates, rng)
        chosen, ops = _greedy(shuffled, lambda c: 0)
        total_ops += ops
        score = _score(chosen)
        attempts.append((f"random_{k}", score[0], score[1]))
        if score > best_score:
            best_chosen, best_source, best_score = tuple(chosen), f"random_{k}", score

    return Result(best_chosen, best_source, total_ops, len(candidates), tuple(attempts))
