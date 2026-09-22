"""Szenario: unverträgliche Patient-Spender-Paare + altruistische Spender für einen Nierentausch-Pool.

Anders als jedes bisherige Stück der Matching-Linie ist hier KEIN geometrisches Kartenbild sinnvoll (Entfernung ist
fachlich falsch) - stattdessen ein Kompatibilitätsgraph über Blutgruppen. Alles ganzzahlig, eigener `SplitMix64`-
Zufallsgenerator (wie in jeder Vorgängerdemo), damit Voreinstellungen/Seeds auf jeder Plattform gleich bleiben.

**ABO-Kompatibilität** (UNOS/National Kidney Foundation/Cedars-Sinai, deckungsgleich): Spender O -> jeder Empfänger;
Spender A -> A, AB; Spender B -> B, AB; Spender AB -> nur AB. Rhesusfaktor ist für Organtransplantation irrelevant
(anders als bei Blutprodukten) und wird bewusst NICHT modelliert.

**Blutgruppen-Häufigkeit**: Stanford Blood Center (Quelle: AABB Technical Manual, 18. Auflage), von Stanford selbst
als "allgemeine Schätzwerte zu Bildungszwecken" bezeichnet - Rhesus-zusammengefasst: O 44 %, A 42 %, B 10 %, AB 4 %.
Eine vereinfachte, illustrative US-Annahme, keine belastbare globale Epidemiologie - im README so benannt.

**Ein Paar entsteht auf zwei Wegen** (beim Bauen selbst gefunden, siehe README "Was nicht funktioniert hat"): entweder
ist der eigene Spender ABO-UNVERTRÄGLICH mit dem eigenen Patienten, ODER er ist ABO-verträglich, scheitert aber am
eigenen Crossmatch (Sensibilisierung). **Nur die erste Regel reicht NICHT**: sie schließt reine ABO-Verträglichkeit
strukturell aus, und die ABO-Tabelle selbst ist fast bipartit (O -> jeder, A -> A/AB, B -> B/AB, AB -> nur AB) - ohne
die zweite Regel können O-Spender und AB-Patienten nie im Pool auftauchen, O-Patienten sind dann aus JEDEM Kreis
ausgeschlossen (nur ein O-Spender kann sie versorgen, und reine ABO-Ausschluss-Paare haben nie einen O-Spender, weil
O IMMER kompatibel ist), und 3er-Kreise werden praktisch unmöglich (die A/B-Struktur erzwingt gerade Kreislängen).
Mit der Crossmatch-Regel können auch ABO-kompatible, aber hochsensibilisierte Paare eintreten - realistisch (echte
Kidney-Paired-Donation-Register bestehen zu einem erheblichen Teil aus genau solchen Paaren) und bricht die
Bipartitheit auf. Eine Obergrenze an Versuchen verhindert trotzdem ein Hängen bei entarteten Parametern.

**Sensibilisierung** (0-99, ein vereinfachter Ersatz für echtes Crossmatch/HLA-Screening, NICHT als klinisches Modell
zu verstehen) senkt zusätzlich zur ABO-Regel die Erfolgschance eines sonst ABO-passenden Spenders: mit Wahrschein-
lichkeit `sensibilisierung / 100` schlägt das (simulierte) Crossmatch fehl. **Qualität** ist eine unabhängige
ganzzahlige Kennziffer je verträglicher Kante (40-99), Ersatz für "wie gut passt dieses Match" (kein Anspruch, echte
klinische Erfolgsfaktoren abzubilden)."""

from dataclasses import dataclass

_MASK = (1 << 64) - 1
MAX_ATTEMPTS = 500

BLOOD_LABELS = ("O", "A", "B", "AB")
O, A, B, AB = 0, 1, 2, 3
BLOOD_WEIGHTS = (44, 42, 10, 4)                      # Stanford Blood Center / AABB Technical Manual, 18. Aufl.
# ABO_COMPAT[spender][empfänger] = kompatibel?
ABO_COMPAT = (
    (True, True, True, True),      # Spender O -> jeder
    (False, True, False, True),    # Spender A -> A, AB
    (False, False, True, True),    # Spender B -> B, AB
    (False, False, False, True),   # Spender AB -> nur AB
)
SENS_MIN, SENS_MAX, DEFAULT_SENS_MAX = 0, 90, 60      # Regler-Obergrenze fuer die Sensibilisierungs-Ziehung
QUALITY_MIN, QUALITY_MAX = 40, 99

SENS_STREAM_XOR = 0x53454E534954495645     # eigener, vom Haupt-Strom unabhaengiger Strom fuer Sensibilisierung
QUALITY_STREAM_XOR = 0x5155414C495459      # eigener Strom fuer die Kantenqualitaet


class SplitMix64:
    """Kleiner, gut gemischter 64-Bit-Zufallsgenerator (Vigna); reine Ganzzahl-Arithmetik."""

    def __init__(self, seed):
        self.state = seed & _MASK

    def next(self):
        self.state = (self.state + 0x9E3779B97F4A7C15) & _MASK
        z = self.state
        z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & _MASK
        z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & _MASK
        return z ^ (z >> 31)

    def below(self, n):
        """Ganzzahl in 0..n-1 (die Modulo-Verzerrung bei kleinen n ist vernachlaessigbar)."""
        return self.next() % n


def _draw(seed, a, b, bits):
    """Reproduzierbare Ziehung 0 .. 2^bits - 1 fuer (Seed, a, b): unabhaengig von der Aufrufreihenfolge."""
    state = seed & _MASK
    for part in (a, b):
        state = (state * 1000003 + part + 1) & _MASK
    return SplitMix64(state).below(1 << bits)


def _blood_type(rng):
    r = rng.below(100)
    cum = 0
    for t, w in enumerate(BLOOD_WEIGHTS):
        cum += w
        if r < cum:
            return t
    return AB


@dataclass(frozen=True)
class Scenario:
    patient_type: tuple      # Blutgruppe je Paar-Patient, Laenge n
    donor_type: tuple         # Blutgruppe je Paar-Spender, Laenge n
    sensitization: tuple       # 0..99 je Paar-Patient, Laenge n
    alt_type: tuple             # Blutgruppe je altruistischem Spender, Laenge n_alt
    seed: int
    sens_max: int

    @property
    def n(self):
        return len(self.patient_type)

    @property
    def n_alt(self):
        return len(self.alt_type)

    def edge_quality(self, donor_idx, patient_idx, is_alt_donor):
        """Kante Spender -> Patient (falls kompatibel), sonst None. `donor_idx` indiziert Paare oder (bei
        `is_alt_donor`) altruistische Spender; `patient_idx` immer ein Paar-Patient."""
        d_type = self.alt_type[donor_idx] if is_alt_donor else self.donor_type[donor_idx]
        p_type = self.patient_type[patient_idx]
        if not ABO_COMPAT[d_type][p_type]:
            return None
        tag = (1 if is_alt_donor else 0) * 1_000_003 + donor_idx
        sens_roll = _draw(self.seed ^ SENS_STREAM_XOR, tag, patient_idx, 7)   # 0..127
        if sens_roll < self.sensitization[patient_idx] * 128 // 100:
            return None
        q = QUALITY_MIN + _draw(self.seed ^ QUALITY_STREAM_XOR, tag, patient_idx, 8) % (QUALITY_MAX - QUALITY_MIN + 1)
        return q

    def compatible_edges(self):
        """Alle Kanten (Spender-Bezeichner, Patient-Index, Qualitaet). Spender-Bezeichner: ('pair', i) oder ('alt', a)."""
        out = []
        for i in range(self.n):
            for p in range(self.n):
                if i == p:
                    continue
                q = self.edge_quality(i, p, False)
                if q is not None:
                    out.append((("pair", i), p, q))
        for a in range(self.n_alt):
            for p in range(self.n):
                q = self.edge_quality(a, p, True)
                if q is not None:
                    out.append((("alt", a), p, q))
        return out


def _incompatible_pair(rng, sens_max):
    """Ein Paar tritt ein, wenn der eigene Spender ABO-unverträglich ist ODER (ABO-verträglich, aber am eigenen
    Crossmatch scheitert - mit Wahrscheinlichkeit Sensibilisierung/100, derselbe Wurf-Typ wie bei jeder anderen
    Kante in `edge_quality`). Ohne den zweiten Fall wäre der Pool strukturell fast bipartit, siehe Moduldoku."""
    for _ in range(MAX_ATTEMPTS):
        p_type = _blood_type(rng)
        d_type = _blood_type(rng)
        sens = rng.below(sens_max + 1)
        if not ABO_COMPAT[d_type][p_type]:
            return p_type, d_type, sens
        if rng.below(100) < sens:
            return p_type, d_type, sens
    raise RuntimeError(f"_incompatible_pair: kein unvertraegliches Paar in {MAX_ATTEMPTS} Versuchen gefunden")


def generate(n, n_alt, seed, sens_max=DEFAULT_SENS_MAX):
    rng = SplitMix64(seed)
    patient_type, donor_type, sensitization = [], [], []
    for _ in range(n):
        p, d, s = _incompatible_pair(rng, sens_max)
        patient_type.append(p)
        donor_type.append(d)
        sensitization.append(s)
    alt_rng = SplitMix64(seed ^ 0x414C545255495354)
    alt_type = [_blood_type(alt_rng) for _ in range(n_alt)]
    return Scenario(tuple(patient_type), tuple(donor_type), tuple(sensitization), tuple(alt_type), seed, sens_max)


# --- feste Lehrbuchkarten (von Hand nachvollzogen, siehe README/Tests) ------------------------------------------------

def chain_example():
    """Zeigt AUSSCHLIESSLICH den Ketteneffekt (keine Kreise beteiligt): bei Kappung 2 erreicht die Kette des
    altruistischen Spenders nur Paar 3 (1 Patient, Qualität 77). Bei Kettenlimit 4 verlängert sich die Kette auf
    4 Glieder - alt→5→1→4→0 (4 Patienten, Qualität 286) - und nimmt dabei sogar einen ANDEREN ersten Schritt als die
    kurze Kette. Erzeugt mit `generate(6, 1, seed=100005, sens_max=60)`, hier als feste Ziehung eingefroren."""
    return generate(6, 1, 100005, DEFAULT_SENS_MAX)


def cycle_example():
    """Zeigt AUSSCHLIESSLICH den Kreislängeneffekt (keine Kette beteiligt): bei Kappung 2 der 2er-Kreis {1,4}
    (2 Patienten, Qualität 93). Bei Kappung 3 ersetzt ihn ein 3er-Kreis {1,3,4} (3 Patienten, Qualität 183) - der
    3er-Kreis existiert nur, weil Paar 1 auch Paar 3 erreichen kann (43) und Paar 3 Paar 4 (92). Erzeugt mit
    `generate(6, 1, seed=100031, sens_max=60)`, hier als feste Ziehung eingefroren."""
    return generate(6, 1, 100031, DEFAULT_SENS_MAX)


NETS = {"chain": chain_example, "cycle": cycle_example}


def build(net, n, n_alt, seed, sens_max=DEFAULT_SENS_MAX):
    if net in NETS:
        return NETS[net]()
    return generate(n, n_alt, seed, sens_max)
