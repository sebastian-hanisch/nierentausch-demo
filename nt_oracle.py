"""Orakel für Tests: exakte Optimierung über ALLE erzeugten Kandidaten (Kreise/Ketten), unabhängig von
`nt_exchange.py`s Heuristik hergeleitet. Nutzt DIESELBE Kandidatenerzeugung (`nt_exchange.generate_candidates`, rein
kombinatorisch, kein Pruning nach Güte - das Erzeugen selbst ist unumstritten), sucht aber die auswahloptimale
disjunkte Teilmenge über eine EIGENE, unabhängige Suche (Tiefensuche mit oberer Schranke fürs Abschneiden - das ist
zulässiges Optimierungs-Pruning, nicht das bei `hr_oracle.py`/`tt_oracle.py` gefundene ungültige Muster "Korrektheit
schon während der Konstruktion beurteilen": hier wird nie eine TEILAUSWAHL für gültig oder optimal erklärt, nur ein
Ast abgeschnitten, dessen bestmögliche Fortsetzung nachweislich nicht mehr an das bisher beste Ergebnis heranreicht).

Nur für kleine n gedacht (`PRACTICAL_MAX_N`, real gemessen, nicht durch Analogie zu anderen Orakeln geschätzt: nach
der Korrektur der Paar-Erzeugung - siehe `nt_scenario.py`s Moduldoku, "Was nicht funktioniert hat" - ist der
Kompatibilitätsgraph dichter, und die Suche verlangsamt sich entsprechend früher als in einem ersten, zu optimistischen
Versuch: bei K=3/Kettenlimit=4 blieb der schlechteste beobachtete Fall bis n=9 unter 0,13 s über 40 Karten, bei n=12
schon über 2 s. `PRACTICAL_MAX_N=9` lässt Sicherheitsabstand, deckt sich mit `hr_oracle.py`/`tt_oracle.py`)."""

from nt_exchange import generate_candidates

PRACTICAL_MAX_N = 9


def optimal_selection(sc, cap, chain_cap):
    """Beste disjunkte Kandidatenauswahl (lexikografisch: zuerst Patientenzahl, dann Qualität). Rückgabe:
    (gewählte Candidate-Liste, Patientenzahl, Qualität)."""
    candidates, _ = generate_candidates(sc, cap, chain_cap)
    n = sc.n
    candidates_sorted = sorted(candidates, key=lambda c: (-c.size, -c.quality))
    best = {"size": 0, "quality": 0, "chosen": ()}
    all_pairs = set(range(n))

    # Suffix-Vereinigung der noch erreichbaren Paare ab Index idx - eine engere, aber billige obere Schranke als
    # "jedes verbleibende Paar koennte noch versorgt werden" (die reine Paarzahl ignoriert, dass viele Paare ab
    # einer bestimmten Position im Kandidaten-Suffix gar nicht mehr vorkommen).
    n_cand = len(candidates_sorted)
    coverable_suffix = [frozenset()] * (n_cand + 1)
    acc = set()
    for i in range(n_cand - 1, -1, -1):
        acc = acc | set(candidates_sorted[i].pairs)
        coverable_suffix[i] = frozenset(acc)

    def dfs(idx, chosen_pairs, chosen_alts, chosen, cur_size, cur_quality):
        if cur_size > best["size"] or (cur_size == best["size"] and cur_quality > best["quality"]):
            best["size"], best["quality"], best["chosen"] = cur_size, cur_quality, tuple(chosen)
        if idx >= n_cand:
            return
        remaining = all_pairs - chosen_pairs
        ub = cur_size + len(remaining & coverable_suffix[idx])
        if ub < best["size"]:
            return
        for j in range(idx, len(candidates_sorted)):
            c = candidates_sorted[j]
            if any(p in chosen_pairs for p in c.pairs) or (c.alt >= 0 and c.alt in chosen_alts):
                continue
            chosen.append(c)
            new_alts = chosen_alts | ({c.alt} if c.alt >= 0 else set())
            dfs(j + 1, chosen_pairs | set(c.pairs), new_alts, chosen, cur_size + c.size, cur_quality + c.quality)
            chosen.pop()

    dfs(0, frozenset(), frozenset(), [], 0, 0)
    return best["chosen"], best["size"], best["quality"]
