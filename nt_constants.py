"""Konstanten, Regler-Grenzen, Presets und feste Seed-Mengen der Demo "Nierentausch"."""

N_MIN, N_MAX, DEFAULT_N = 4, 35, 25          # unverträgliche Paare - Obergrenze real gemessen (nt_evaluation-Messreihe): die
                                              # Kandidatenzahl waechst sehr steil mit n (n=35 im schlechtesten Fall 0,56 s bei
                                              # Kappung 3/Kettenlimit 4, n=40 schon > 1 s); 35 laesst Sicherheitsabstand
N_ALT_MIN, N_ALT_MAX, DEFAULT_N_ALT = 0, 10, 3   # altruistische Spender
SENS_MIN, SENS_MAX, SENS_STEP, DEFAULT_SENS = 0, 90, 10, 60   # Regler "Sensibilisierung (Obergrenze) [%]"
DEFAULT_SEED = 97
SEED_MAX = 2_000_000_000

CAP_MIN, CAP_MAX, DEFAULT_CAP = 2, 3, 3          # Kreis-Höchstlänge - real gemessen: Kappung 4 kombiniert mit hohem n/Kettenlimit
                                                  # kann den Kandidatenraum sprengen (siehe N_MAX-Kommentar), deshalb bei 3 gedeckelt
CHAIN_MIN, CHAIN_MAX, DEFAULT_CHAIN_CAP = 1, 4, 4   # Ketten-Höchstlänge

CARD_NONE = "none"
CARD_CHAIN = "chain"
CARD_CYCLE = "cycle"
CARDS = {CARD_NONE: "Zufälliger Pool", CARD_CHAIN: "Ketten-Lehrbuchkarte", CARD_CYCLE: "Kreis-Lehrbuchkarte"}
CARD_LABELS = CARDS
DEFAULT_CARD = CARD_NONE

# --- feste Seed-Mengen (unabhängig vom Nutzer-Seed) ------------------------------------------------------------------
DIST_SEEDS = tuple(range(100000, 100100))
ORACLE_SEEDS = DIST_SEEDS[:20]
EFFORT_NS = (10, 20, 25, 30, 35)   # real gemessen: n=35 im schlechtesten Fall 0,56 s, n=40 schon > 1 s - bewusst konservativ
EFFORT_SEEDS = DIST_SEEDS[:5]

BLOOD_COLORS = {"O": "#1f77b4", "A": "#2ca02c", "B": "#ff7f0e", "AB": "#d62728"}
COLORS = {"cycle": "#2ca02c", "chain": "#9467bd", "cap2": "#1f77b4", "unmatched": "#bbbbbb"}

# --- Presets ------------------------------------------------------------------------------------------------------------------
_BASE = dict(card=CARD_NONE, n=DEFAULT_N, n_alt=DEFAULT_N_ALT, sens=DEFAULT_SENS, cap=DEFAULT_CAP, chain_cap=DEFAULT_CHAIN_CAP, seed=DEFAULT_SEED)
PRESETS = {
    "⛓️ Ketten-Lehrbuchkarte": {**_BASE, "card": CARD_CHAIN},
    "🔁 Kreis-Lehrbuchkarte": {**_BASE, "card": CARD_CYCLE},
    "🗺️ Mittlere Karte": {**_BASE},
    "🙋 Viele altruistische Spender": {**_BASE, "n_alt": 6, "seed": 41},
    "👫 Nur Paartausch (Kappung 2)": {**_BASE, "cap": 2, "chain_cap": 1, "seed": 21},
    "🧬 Hohe Sensibilisierung": {**_BASE, "sens": 90, "seed": 13},
    "😴 Kein Kompatibilitätsglück": {**_BASE, "n": 20, "n_alt": 0, "sens": 0, "seed": 8},
    "🔬 Beweis": {**_BASE, "n": 8, "n_alt": 1, "seed": 5},
}
# Jede Zahl in diesen Texten ist in tests/test_claims.py über die 100 festen Karten (DIST_SEEDS) belegt
PRESET_HELP = {
    "⛓️ Ketten-Lehrbuchkarte": "Von Hand nachvollzogen (n=6, 1 altruistischer Spender): bei reinem Paartausch erreicht die Kette nur 1 Patienten (Qualität 77). Mit Kettenlimit 4 verlängert sie sich auf 4 Glieder (Qualität 286) - der GESAMTE Zugewinn kommt allein aus der längeren Kette, kein Kreis beteiligt.",
    "🔁 Kreis-Lehrbuchkarte": "Von Hand nachvollzogen (n=6, 1 altruistischer Spender), als Kontrast: bei Kappung 2 ein 2er-Kreis (2 Patienten, Qualität 93). Bei Kappung 3 ersetzt ihn ein 3er-Kreis (3 Patienten, Qualität 183) - hier kommt der Zugewinn rein aus der Kreislänge, keine Kette beteiligt.",
    "🗺️ Mittlere Karte": "Realistische Einstellungen: reiner Paartausch versorgt im Mittel 57 % des Pools, der allgemeine Modus (Kreise bis 3, Ketten bis 4) 62 %.",
    "🙋 Viele altruistische Spender": "8 altruistische Spender auf 25 Paare: deutlich mehr Ketten als auf der Standardkarte.",
    "👫 Nur Paartausch (Kappung 2)": "Kappung 2 ist EXAKT lösbar (Maximum-Weight-Matching, `nt_blossom.py`) - der Kontrast zum allgemeinen, nur heuristisch lösbaren Modus.",
    "🧬 Hohe Sensibilisierung": "Sensibilisierung bis 90 %: viele sonst ABO-passende Kanten scheitern am simulierten Crossmatch, der Pool wird spärlicher.",
    "😴 Kein Kompatibilitätsglück": "Negativbeispiel, bewusst gezeigt: ohne altruistische Spender UND ohne die Crossmatch-Regel (Sensibilisierung 0) ist der Kompatibilitätsgraph fast bipartit - O-Patienten sind unerreichbar, 3er-Kreise praktisch unmöglich.",
    "🔬 Beweis": "Kleine Karte (n=8): klein genug, dass `nt_oracle.py` die optimale Kreis-/Kettenauswahl erschöpfend nachprüfen kann (in den Tests, nicht live in der App).",
}
