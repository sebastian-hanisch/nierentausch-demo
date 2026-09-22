# Nierentausch – Tausch unter medizinischen Zwängen – Streamlit-Demo

Dreizehntes und letztes Stück der **Matching-Linie** der "Konzepte"-Reihe für die Website "Sebastian Hanisch – Operations Research und Machine Learning", direkte Erweiterung von [top-trading-cycles-demo](https://github.com/sebastian-hanisch/top-trading-cycles-demo) – inspiriert von Alvin Roths Arbeiten zu Marktdesign ohne Geld.

**Top Trading Cycles** löst den Wohnungsmarkt: vollständige Präferenzen, beliebig lange Tauschkreise. Bei Nieren geht das nicht: ein Patient braucht nicht "die beste" Niere, sondern irgendeine **kompatible** – und jede Operation eines Kreises muss **gleichzeitig** stattfinden (kein Spender darf geben, bevor sein eigener Patient schon versorgt ist, sonst könnte ein früherer Spender leer ausgehen, wenn ein späteres Glied ausfällt). Eine **Kette**, gestartet von einem altruistischen Spender, braucht das nicht: fällt ein Glied aus, verliert nur das nächste Glied, niemand, der schon gespendet hat. Kreislänge 2 (Paartausch) ist dabei **exakt lösbar** (Roth, Sönmez & Ünver 2005); ab Länge 3 wird die Auswahl **NP-schwer** (Abraham, Blum & Sandholm 2007).

```
greedy-matching-demo (Wurzel: eine gewählte Zuordnung bleibt)                     [gebaut]
  ├─ augmenting-path-demo … weighted-blossom-demo (Konvergenz)                    [gebaut]
  ├─ gale-shapley-demo (Vorlieben statt Kosten, stabil)                            [gebaut]
  │    ├─ stabile-mitbewohner-demo (eine Gruppe statt zwei Seiten)                 [gebaut]
  │    ├─ krankenhaus-zulassung-demo (many-to-one, Kapazitäten)                    [gebaut]
  │    └─ top-trading-cycles-demo (Tausch ohne Geld, Wohnungsmarkt)                [gebaut]
  │         └─ nierentausch-demo (Kompatibilität statt Präferenz, kurze Zyklen)    [dieses, letztes Stück]
  └─ online-matching-demo (Aufträge kommen nacheinander)                          [gebaut]
```

## Ergebnis (Zahlen aus den Tests)

Jede hier genannte Zahl ist in `tests/test_claims.py` über die 100 festen Karten (Seeds 100000–100099) belegt: 25 unverträgliche Paare, 3 altruistische Spender, Sensibilisierung ≤ 60 %, Kreis-Höchstlänge 3, Ketten-Höchstlänge 4. Aufwand = **erzeugte Kandidaten + geprüfte Kombinationsschritte**, nie Sekunden.

| Frage | Ergebnis |
|---|---|
| Versorgungsanteil | ✅ Im Mittel **61,6 %** (Median 60 %) im allgemeinen Modus, gegenüber **57,0 %** (Median 56 %) bei reinem Paartausch (Kappung 2). |
| Qualität | ✅ Im Mittel **1173** (Median 1138) im allgemeinen Modus, gegenüber **1099** (Median 1043) bei Kappung 2. |
| Beitrag altruistischer Spender | ✅ 3 altruistische Spender (12 % der Paarzahl) bringen im Mittel **+2,2** (Median +2,0) zusätzliche Patienten und **+182** (Median +165) zusätzliche Qualität. |
| Ehrlichkeit der Heuristik | ⚠️ Eine einfache, unsortierte Greedy-Reihenfolge verliert auf **58 von 100** Karten gegen die exakte Kappung-2-Lösung – obwohl ihr Kandidatenraum strikt größer ist. Die Mehrfachstart-Heuristik MIT dem Kappung-2-Sicherheitsnetz verliert auf **0 von 100** – das Sicherheitsnetz erzwingt das, nicht die Heuristik selbst. |
| Heuristik-Genauigkeit gegen das Orakel | ⚠️ An kleinen Karten (n=6–9, gegen `nt_oracle.py`): **58 von 80** exakt (72,5 %), mittlere Lücke 0,15 Patienten, größte beobachtete Lücke 2 – ehrlich berichtet, nicht auf 0 Abweichungen geschönt. |
| Kappung 2 selbst | ✅ **0 von 60** Abweichungen gegen das Orakel – Kappung 2 ist beweisbar exakt (Maximum-Weight-Matching, `nt_blossom.py`). |

## Was nicht funktioniert hat / widerlegte Vorab-Hypothesen

- **Ein echter Strukturfehler im ersten Szenario-Entwurf.** Die erste Version ließ ein Paar nur dann in den Pool, wenn der eigene Spender ABO-UNVERTRÄGLICH war. Das reicht nicht: die ABO-Tabelle selbst ist fast bipartit (O → jeder, A → A/AB, B → B/AB, AB → nur AB) – bei reiner ABO-Ausschlussregel können O-Spender NIE im Pool auftauchen (ein O-Spender ist mit JEDEM Patienten verträglich, also nie "unverträglich mit dem eigenen"), AB-Patienten ebenso wenig (sie sind mit JEDEM Spender verträglich), und O-Patienten sind dadurch aus JEDEM Kreis ausgeschlossen (nur ein O-Spender könnte sie versorgen, und den gibt es im Pool nicht). Die Folge: 3er-Kreise waren praktisch unmöglich (0 von mehreren hundert getesteten Karten, selbst bei n=40) – die A/B-Struktur erzwingt gerade Kreislängen, ein reines Analogon zu bipartiten Graphen. Gefunden durch eine eigene Brute-Force-Prüfung, NICHT durch Vertrauen auf plausibel aussehende Zahlen. Gelöst: ein Paar tritt auch ein, wenn der eigene Spender ABO-VERTRÄGLICH ist, aber am eigenen Crossmatch scheitert (dieselbe Sensibilisierungs-Ziehung wie bei jeder anderen Kante) – realistisch (ein erheblicher Teil echter Kidney-Paired-Donation-Register besteht aus genau solchen Paaren) und bricht die Bipartitheit auf.
- **O-Spender bleiben auch nach der Korrektur unterrepräsentiert – kein Fehler, sondern real.** In einer 3000-Paare-Stichprobe sind nur rund 23 % der Spender vom Typ O (gegenüber 44 % in der zugrunde gelegten Bevölkerungsverteilung) – ein bekannter Selektionseffekt echter Register: O-Spender werden meist direkt gebraucht und tauchen seltener in "braucht Tausch"-Paaren auf.
- **Das erste Brute-Force-Orakel war zu optimistisch dimensioniert.** Eine erste Erwartung (in Analogie zu `tt_oracle.py`s n ≤ 9 bei einem strukturell anderen, faktoriellen Problem) ging von einer praktikablen Grenze um n ≈ 16–20 aus. Real gemessen, nach der Szenario-Korrektur (dichterer Graph): bei n=12 bereits über 2 Sekunden im schlechtesten Fall, ab n≈13 drohen Läufe über mehrere Sekunden. `PRACTICAL_MAX_N = 9` (wie `hr_oracle.py`/`tt_oracle.py`) nach echter Messung, nicht nach Analogie.
- **Die Regler-Obergrenzen mussten nach unten korrigiert werden.** Ein erster Entwurf erlaubte bis zu 60 Paare, Kreis-Höchstlänge 4, Ketten-Höchstlänge 6 – die Kombination aus großem Pool, hoher Kappung und hoher Sensibilisierung ließ den Kandidatenraum in der Praxis über mehrere zehn Sekunden hinaus wachsen (ein Extremfall lief über 60 Sekunden nicht durch). Nach echter Messung auf `N_MAX = 35`, `Kreis-Höchstlänge ≤ 3` begrenzt – der schlechteste beobachtete Fall bei diesen Grenzen liegt bei 0,7 Sekunden, auch am Rand der Regler (n=35, 10 altruistische Spender, Sensibilisierung 90 %).
- **Eine naive Greedy-Heuristik kann trotz größerem Kandidatenraum schlechter abschneiden als der exakte Spezialfall.** Real gemessen (nicht angenommen): eine einfach sortierte Greedy-Auswahl über Kreise bis Länge 3 und Ketten bis Länge 4 verlor auf 58 von 100 Standardkarten gegen die EXAKTE Kappung-2-Lösung. Behoben durch Mehrfachstart (mehrere Sortierschlüssel plus randomisierte Neustarts) UND ein Sicherheitsnetz, das das exakte Kappung-2-Ergebnis immer als zusätzlichen Kandidaten mitführt – seitdem 0 von 100 Verlusten, per Konstruktion garantiert.

## Was die Demo zeigt

- **Ablauf:** Schritt-Slider und ▶️ über die gewählten Kreise/Ketten (ein Kompatibilitätsgraph mit Paaren auf einem Kreis, altruistischen Spendern als Sterne); am Ende Versorgungsanteil, Qualität, Zugewinn gegenüber Kappung 2.
- **Nicht nur diese eine Karte:** Versorgungsanteil und Qualität über 100 feste Karten, Kreis-/Kettenlängen-Histogramm, Kappung 2 vs. allgemeiner Modus im direkten Vergleich, Beitrag der altruistischen Spender, ehrliche Heuristik-Trefferquote.
- **Wovon hängt der Aufwand ab?** Aufwand gegen die Poolgröße (n = 10 bis 35) – zeigt das sehr steile Wachstum, das echte Programme zur Kappung zwingt.
- **Feste Presets:** Ketten-Lehrbuchkarte · Kreis-Lehrbuchkarte (Kontrast) · Mittlere Karte · Viele altruistische Spender · Nur Paartausch (Kappung 2) · Hohe Sensibilisierung · Kein Kompatibilitätsglück (Negativbeispiel) · Beweis; **Wo die Annahmen enden.**

## Modell und Verfahren

- **Kompatibilitätsgraph, kein geometrisches Kartenbild** (`nt_scenario.py`): n unverträgliche Paare (Patient + eigener Spender), erzeugt entweder über ABO-Unverträglichkeit ODER ABO-Verträglichkeit mit gescheitertem eigenen Crossmatch (siehe "Was nicht funktioniert hat"), plus altruistische Spender ohne eigenen Patienten. Blutgruppen-Häufigkeit nach Stanford Blood Center/AABB Technical Manual (18. Auflage), ausdrücklich als vereinfachte, illustrative US-Annahme gekennzeichnet.
- **Kappung 2 (`nt_blossom.py`, Kopie-mit-Umbenennung von `weighted-blossom-demo/wb_blossom.py`):** reiner Paartausch plus Ketten der Länge 1 reduziert exakt auf Maximum-Weight-Matching im allgemeinen Graphen (Roth, Sönmez & Ünver 2005) – dieselbe kombinatorische Aufgabe wie in `weighted-blossom-demo`, hier auf Qualität statt Kosten angewendet.
- **Allgemeiner Modus (`nt_exchange.py`):** Kreise bis Länge K und Ketten bis zu einem Kettenlimit werden vollständig aufgezählt (kein Pruning nach Güte), eine Mehrfachstart-Greedy-Heuristik (mehrere Sortierschlüssel plus randomisierte Neustarts) sucht die beste disjunkte Auswahl, IMMER mit dem exakten Kappung-2-Ergebnis als Sicherheitsnetz. Ab Kreislänge ≥ 3 ist das Problem NP-schwer (Abraham, Blum & Sandholm 2007); die Heuristik hat keinen Optimalitätsbeweis – ihre gemessene Lücke gegen `nt_oracle.py` (kleine Karten, in den Tests) ist der App eigener, ehrlicher Beweis ihrer Grenzen.
- **Eigenes Brute-Force-Orakel (`nt_oracle.py`):** dieselbe Kandidatenerzeugung wie die Heuristik, aber eine unabhängige Tiefensuche mit oberer Schranke fürs Abschneiden (zulässiges Optimierungs-Pruning, nicht das bei `hr_oracle.py`/`tt_oracle.py` gefundene ungültige Muster "Korrektheit schon während der Konstruktion beurteilen").

## Dateien

| Datei | Inhalt |
|---|---|
| `app.py` | Streamlit-Oberfläche |
| `nt_constants.py` | Regler-Grenzen, Presets und Hilfetexte, feste Seed-Mengen |
| `nt_presets.py` | Permalink-, Preset- und Zufalls-Seed-Logik (`card_select` für die zwei festen Lehrbuchkarten) |
| `nt_scenario.py` | Kompatibilitätsgraph, ABO-Tabelle, Blutgruppen-Ziehung, unverträgliche Paare, altruistische Spender, zwei feste Lehrbuchkarten |
| `nt_blossom.py` | Kappung 2, exakt (Kopie-mit-Umbenennung von `weighted-blossom-demo/wb_blossom.py`) |
| `nt_exchange.py` | Kandidatenerzeugung, Mehrfachstart-Greedy mit Kappung-2-Sicherheitsnetz |
| `nt_oracle.py` | Brute-Force-Orakel (nur Tests, `PRACTICAL_MAX_N=9`) |
| `nt_evaluation.py` | Einordnung, Verteilung, Kappungs-Vergleich, Beitrag altruistischer Spender, Aufwand, ehrliche Heuristik-Trefferquote |
| `nt_visualization.py` | Plotly-Abbildungen (Kompatibilitätsgraph, Achsen gesperrt) |
| `tests/` | Zwei NAMENTLICHE Lehrbuchkarten-Regressionen, Kappung-2-Exaktheit, ehrlich berichtete Heuristik-Genauigkeit, Negativkontrollen, belegte Zahlen, AppTest-Rauchtests |

Alle Daten sind synthetisch (keine echten Patientendaten); die Laufzeit braucht nur numpy, pandas, plotly und streamlit.

## Lokal starten

```bash
python -m venv venv
venv\Scripts\pip install -r requirements.txt
venv\Scripts\streamlit run app.py
```

## Tests ausführen

```bash
venv\Scripts\pip install -r requirements-dev.txt
venv\Scripts\python -m pytest tests -v
```

Die Logik rechnet ausschließlich mit ganzen Zahlen; die im Text genannten Anteile und Mittelwerte sind deshalb auf jeder Plattform identisch.
Die CI (`.github/workflows/tests.yml`) läuft auf Ubuntu mit Python 3.12, bei jedem Push und wöchentlich mit den jeweils neuesten Bibliotheksversionen.
