"""Auswertung: eine Karte (`analyse`, `verdict`), viele Karten (`distribution`), Kappungs-Vergleich (2 vs. 3 vs. frei),
Beitrag altruistischer Spender, Aufwand gegen Größe. Ziel ist immer zuerst die PATIENTENZAHL (lexikografisch), dann
die Qualität - wie bei echten Kidney-Exchange-Programmen. Mittel und Median stehen immer zusammen."""

from dataclasses import dataclass
from functools import lru_cache

import numpy as np

import nt_constants as C
from nt_exchange import solve
from nt_scenario import build, generate


@dataclass
class Analysis:
    scenario: object
    cap: int
    chain_cap: int
    result: object


def analyse(sc, cap=C.DEFAULT_CAP, chain_cap=C.DEFAULT_CHAIN_CAP):
    return Analysis(sc, cap, chain_cap, solve(sc, cap, chain_cap))


def _mean_median(values):
    if not values:
        return {"mean": None, "median": None}
    return {"mean": float(np.mean(values)), "median": float(np.median(values))}


def verdict(a):
    sc, res = a.scenario, a.result
    n = sc.n
    matched = sum(c.size for c in res.chosen)
    quality = sum(c.quality for c in res.chosen)
    n_cycles = sum(1 for c in res.chosen if c.kind == "cycle")
    n_chains = sum(1 for c in res.chosen if c.kind == "chain")
    lengths = sorted((c.size for c in res.chosen), reverse=True)
    cap2 = next((att for att in res.attempts if att[0] == "cap2"), ("cap2", 0, 0))
    return {"n": n, "n_alt": sc.n_alt, "matched": matched, "unmatched": n - matched, "quality": quality,
            "n_cycles": n_cycles, "n_chains": n_chains, "lengths": tuple(lengths), "source": res.source,
            "steps": res.steps, "n_candidates": res.n_candidates, "cap2_matched": cap2[1], "cap2_quality": cap2[2],
            "gain_over_cap2": matched - cap2[1]}


def scenario_from_settings(net, n, n_alt, seed, sens_max):
    return build(net, n, n_alt, seed, sens_max)


# --- viele Karten ----------------------------------------------------------------------------------------------------

@lru_cache(maxsize=256)
def cell_rows(n, n_alt, sens_max, cap, chain_cap, seeds):
    rows = []
    for sd in seeds:
        sc = generate(n, n_alt, sd, sens_max)
        res = solve(sc, cap, chain_cap)
        cap2 = next(att for att in res.attempts if att[0] == "cap2")
        matched = sum(c.size for c in res.chosen)
        quality = sum(c.quality for c in res.chosen)
        lengths = tuple(c.size for c in res.chosen)
        rows.append({"matched": matched, "quality": quality, "cap2_matched": cap2[1], "cap2_quality": cap2[2],
                     "steps": res.steps, "lengths": lengths, "n_cycles": len(lengths)})
    return tuple(rows)


def _med(values):
    return float(np.median(values)) if len(values) else None


def distribution(n, n_alt, sens_max, cap=C.DEFAULT_CAP, chain_cap=C.DEFAULT_CHAIN_CAP, seeds=C.DIST_SEEDS):
    rows = cell_rows(n, n_alt, sens_max, cap, chain_cap, tuple(seeds))
    matched_share = [r["matched"] / n for r in rows]
    cap2_share = [r["cap2_matched"] / n for r in rows]
    all_lengths = [L for r in rows for L in r["lengths"]]
    length_hist = {L: sum(1 for x in all_lengths if x == L) for L in sorted(set(all_lengths))}
    return {"n_seeds": len(seeds), "matched_share": _mean_median(matched_share), "cap2_share": _mean_median(cap2_share),
            "quality": _mean_median([r["quality"] for r in rows]), "cap2_quality": _mean_median([r["cap2_quality"] for r in rows]),
            "steps": _mean_median([r["steps"] for r in rows]), "n_cycles": _mean_median([r["n_cycles"] for r in rows]),
            "n_candidates_total": len(all_lengths), "length_hist": length_hist,
            "length_hist_share": {L: c / max(len(all_lengths), 1) for L, c in length_hist.items()}}


def altruistic_contribution(n, sens_max, n_alt, cap=C.DEFAULT_CAP, chain_cap=C.DEFAULT_CHAIN_CAP, seeds=C.DIST_SEEDS):
    with_rows = cell_rows(n, n_alt, sens_max, cap, chain_cap, tuple(seeds))
    without_rows = cell_rows(n, 0, sens_max, cap, chain_cap, tuple(seeds))
    d_matched = [w["matched"] - wo["matched"] for w, wo in zip(with_rows, without_rows)]
    d_quality = [w["quality"] - wo["quality"] for w, wo in zip(with_rows, without_rows)]
    return {"matched_gain": _mean_median(d_matched), "quality_gain": _mean_median(d_quality)}


def naive_vs_cap2(n, n_alt, sens_max, cap=C.DEFAULT_CAP, chain_cap=C.DEFAULT_CHAIN_CAP, seeds=C.DIST_SEEDS):
    """Wie oft verliert die naive (einfach sortierte) Greedy-Reihenfolge gegen die exakte Kappung-2-Lösung, und wie
    oft (dank Mehrfachstart + Sicherheitsnetz) das GESAMTERGEBNIS? Ehrliche Zähler, keine geschönten 0-Werte."""
    naive_losses = multi_losses = total = 0
    for sd in seeds:
        sc = generate(n, n_alt, sd, sens_max)
        res = solve(sc, cap, chain_cap)
        cap2 = next(att for att in res.attempts if att[0] == "cap2")
        naive = next(att for att in res.attempts if att[0] == "size_then_quality")
        best = (sum(c.size for c in res.chosen), sum(c.quality for c in res.chosen))
        total += 1
        if (naive[1], naive[2]) < (cap2[1], cap2[2]):
            naive_losses += 1
        if best < (cap2[1], cap2[2]):
            multi_losses += 1
    return {"total": total, "naive_losses": naive_losses, "multi_losses": multi_losses}


@lru_cache(maxsize=8)
def effort_scaling(sens_max, ns=C.EFFORT_NS, seeds=C.EFFORT_SEEDS, cap=C.DEFAULT_CAP, chain_cap=C.DEFAULT_CHAIN_CAP):
    out = []
    for n in ns:
        n_alt = max(1, n // 8)
        steps = []
        for sd in seeds:
            sc = generate(n, n_alt, sd, sens_max)
            steps.append(solve(sc, cap, chain_cap).steps)
        out.append({"n": n, "steps": float(np.mean(steps))})
    return tuple(out)


@lru_cache(maxsize=8)
def heuristic_accuracy(sens_max, ns=(6, 7, 8, 9), seeds=C.ORACLE_SEEDS, cap=C.DEFAULT_CAP, chain_cap=C.DEFAULT_CHAIN_CAP):
    """Heuristik gegen `nt_oracle.py` an kleinen Karten - ehrliche Trefferquote, keine geschönten 0-Abweichungen."""
    import nt_oracle as O
    exact = total = 0
    gaps = []
    for n in ns:
        for sd in seeds:
            sc = generate(n, 1, sd, sens_max)
            res = solve(sc, cap, chain_cap)
            best = (sum(c.size for c in res.chosen), sum(c.quality for c in res.chosen))
            _, opt_size, opt_q = O.optimal_selection(sc, cap, chain_cap)
            total += 1
            if best == (opt_size, opt_q):
                exact += 1
            gaps.append(opt_size - best[0])
    return {"exact": exact, "total": total, "mean_gap": float(np.mean(gaps)), "max_gap": max(gaps)}
