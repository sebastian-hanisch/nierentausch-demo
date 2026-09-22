"""Nierentausch (Kidney Exchange) - interaktive Konzept-Demo
Sebastian Hanisch - Operations Research und Machine Learning

Letztes Stück der Matching-Linie, direkte Erweiterung von top-trading-cycles-demo: TTC löst den Wohnungsmarkt mit
vollständigen Präferenzen und frei langen Tauschkreisen. Nierentausch schränkt das ein, was medizinisch nötig ist:
Kompatibilität statt Präferenz, kurze Kreise/Ketten statt beliebig langer Kreise. Siehe README.

Lauffähig mit: streamlit run app.py
"""

import streamlit as st

import nt_constants as C
import nt_evaluation as ev
from nt_presets import apply_preset, bounds, init_session_state_defaults, load_permalink_settings, randomize_seed, sync_query_params
from nt_visualization import build_cap_comparison, build_graph, build_length_hist, build_scale

st.set_page_config(page_title="Nierentausch – Sebastian Hanisch", layout="wide")


def _f(x, digits=1):
    return "–" if x is None else f"{x:.{digits}f}".replace(".", ",")


def _ms(s, digits=1):
    return "–" if s["mean"] is None else f"{_f(s['mean'], digits)} | {_f(s['median'], digits)}"


def _share(x):
    return "–" if x is None else f"{100 * x:.0f} %"


@st.cache_resource(show_spinner=False, max_entries=16)
def _analysis(params):
    card, n, n_alt, sens, cap, chain_cap, seed = params
    sc = ev.scenario_from_settings(card, n, n_alt, seed, sens)
    return ev.analyse(sc, cap, chain_cap)


@st.cache_data(show_spinner=False)
def _distribution(n, n_alt, sens, cap, chain_cap):
    return ev.distribution(n, n_alt, sens, cap, chain_cap)


@st.cache_data(show_spinner=False)
def _altruistic_contribution(n, sens, n_alt, cap, chain_cap):
    return ev.altruistic_contribution(n, sens, n_alt, cap, chain_cap)


@st.cache_data(show_spinner=False)
def _naive_vs_cap2(n, n_alt, sens, cap, chain_cap):
    return ev.naive_vs_cap2(n, n_alt, sens, cap, chain_cap)


@st.cache_data(show_spinner=False)
def _effort_scaling(sens):
    return ev.effort_scaling(sens)


st.title("🫘 Nierentausch – Tausch unter medizinischen Zwängen")
st.markdown(
    """
**Top Trading Cycles** löst den Wohnungsmarkt: vollständige Präferenzen, beliebig lange Tauschkreise. Bei Nieren geht
das nicht: ein Patient braucht nicht "die beste" Niere, sondern irgendeine **kompatible** - und jede Operation eines
Kreises muss **gleichzeitig** stattfinden (kein Spender darf geben, bevor sein eigener Patient schon versorgt ist).
Eine **Kette**, gestartet von einem altruistischen Spender, braucht das nicht: fällt ein Glied aus, verliert niemand,
der schon gespendet hat. Kreislänge 2 (Paartausch) ist dabei **exakt lösbar**; ab Länge 3 wird die Auswahl NP-schwer.
"""
)
st.caption("Letztes Stück der Matching-Linie, direkte Erweiterung von Top Trading Cycles (Gale, in Shapley & Scarf 1974).")

with st.expander("So funktioniert die Kreis-/Ketten-Auswahl", expanded=True):
    st.markdown(
        """
1. **Kompatibilitätsgraph:** jedes unverträgliche Paar (Patient + eigener, ABO- oder crossmatch-unverträglicher
   Spender) - der Spender kann trotzdem für ANDERE Patienten passen. Dazu altruistische Spender ohne eigenen Patienten.
2. **Kreise** (Länge 2 bis K): jeder im Kreis gibt und empfängt gleichzeitig. **Ketten** (gestartet von einem
   altruistischen Spender): können nacheinander, ohne Simultan-OP, ablaufen.
3. **Kappung 2 (reiner Paartausch) ist exakt lösbar** - Reduktion auf Maximum-Weight-Matching (`nt_blossom.py`,
   dieselbe Aufgabe wie in `weighted-blossom-demo`). **Ab Kappung 3 ist die Auswahl NP-schwer** - eine
   Mehrfachstart-Heuristik sucht, IMMER mit dem exakten Kappung-2-Ergebnis als Sicherheitsnetz.
4. **Ziel:** zuerst so viele Patienten wie möglich versorgen, dann die Qualität maximieren.
        """
    )

st.caption("🎯 Schnellstart – eine Beispielkarte laden:")
names = list(C.PRESETS.keys())
for row in range(0, len(names), 4):
    preset_cols = st.columns(4)
    for col, name in zip(preset_cols, names[row:row + 4]):
        with col:
            st.button(name, width="stretch", on_click=apply_preset, args=(name,), help=C.PRESET_HELP[name] or None)

st.caption("🔗 Die Adresszeile oben spiegelt Ihre aktuelle Konfiguration wider – einfach kopieren, um ein Szenario zu teilen.")

load_permalink_settings()
init_session_state_defaults()

with st.sidebar:
    st.header("⚙️ Einstellungen")
    card = st.session_state.get("card_select", C.CARD_NONE)
    if card == C.CARD_NONE:
        n = st.slider("Unverträgliche Paare", *bounds("n_slider"), key="n_slider")
        n_alt = st.slider("Altruistische Spender", *bounds("n_alt_slider"), key="n_alt_slider")
        sens = st.slider("Sensibilisierung (Obergrenze) [%]", *bounds("sens_slider"), key="sens_slider", step=C.SENS_STEP,
                         help="Obergrenze der Ziehung 0..Wert je Patient; höher = mehr scheiternde Crossmatches.")
        cap = st.slider("Kreis-Höchstlänge K", *bounds("cap_slider"), key="cap_slider")
        chain_cap = st.slider("Ketten-Höchstlänge", *bounds("chain_cap_slider"), key="chain_cap_slider")
        seed = st.number_input("Zufalls-Seed", *bounds("seed_input"), key="seed_input", step=1)
        st.button("🎲 Neuen Pool generieren", width="stretch", on_click=randomize_seed)
    else:
        n, n_alt, sens = st.session_state.get("n_slider", C.DEFAULT_N), st.session_state.get("n_alt_slider", C.DEFAULT_N_ALT), st.session_state.get("sens_slider", C.DEFAULT_SENS)
        cap, chain_cap, seed = st.session_state.get("cap_slider", C.DEFAULT_CAP), st.session_state.get("chain_cap_slider", C.DEFAULT_CHAIN_CAP), st.session_state.get("seed_input", C.DEFAULT_SEED)
        st.caption(f"Feste Karte ({C.CARD_LABELS[card]}) - es gibt nichts zu erzeugen.")

params = (card, int(n), int(n_alt), int(sens), int(cap), int(chain_cap), int(seed))
with st.spinner("Rechne..."):
    a = _analysis(params)
sc, res = a.scenario, a.result
d = ev.verdict(a)
sync_query_params({"card_select": card, "n_slider": int(n), "n_alt_slider": int(n_alt), "sens_slider": int(sens), "cap_slider": int(cap), "chain_cap_slider": int(chain_cap), "seed_input": int(seed)})

st.markdown("## 🎯 Ablauf")
n_steps = len(res.chosen)
step_col, play_col = st.columns([6, 2])
if st.session_state.get("nt_step_owner") != params:
    st.session_state["nt_step"] = n_steps
    st.session_state["nt_step_owner"] = params
with step_col:
    if n_steps > 0:
        step = st.slider("Kreis/Kette", 0, n_steps, key="nt_step")
    else:
        step = 0
        st.caption("Kein Kreis/keine Kette gefunden.")
with play_col:
    auto_play = st.button("▶️ Abspielen", width="stretch", disabled=n_steps == 0)
view_slot = st.empty()


def _step_text(k):
    if k == 0:
        return f"Anfang: {d['n']} Paare, {d['n_alt']} altruistische Spender, noch niemand versorgt."
    c = res.chosen[k - 1]
    if c.kind == "cycle":
        return f"Kreis {' → '.join(str(p) for p in c.pairs)} → {c.pairs[0]}: {len(c.pairs)} Patienten versorgt, Qualität {c.quality}."
    return f"Kette Spender {c.alt} → {' → '.join(str(p) for p in c.pairs)}: {len(c.pairs)} Patienten versorgt, Qualität {c.quality}."


def _render(k):
    with view_slot.container():
        c1, c2 = st.columns([3, 2])
        c1.markdown(f"**Nach {k} von {n_steps} Kreisen/Ketten** – " + _step_text(k))
        c1.plotly_chart(build_graph(sc, res, revealed=k), width="stretch", key=f"nt_graph_{k}")
        with c2:
            st.markdown(f"**{d['matched']} von {d['n']} Patienten versorgt** ({_share(d['matched']/d['n'])}), Qualität {d['quality']} - "
                       f"{d['n_cycles']} Kreis(e), {d['n_chains']} Kette(n) (Längen {', '.join(str(x) for x in d['lengths'])}).")
            st.caption(f"Gefunden über: {d['source']} (Sicherheitsnetz: Kappung-2-Ergebnis war {d['cap2_matched']} Patienten/{d['cap2_quality']} Qualität - "
                      f"{'übertroffen' if d['gain_over_cap2'] > 0 else 'nicht übertroffen, also übernommen'}).")
            m1, m2 = st.columns(2)
            m1.metric("Versorgt", f"{d['matched']} / {d['n']}")
            m2.metric("Qualität", d['quality'])
            m3, m4 = st.columns(2)
            m3.metric("Zugewinn ggü. Kappung 2", f"+{d['gain_over_cap2']} Patienten")
            m4.metric("Aufwand (Schritte)", f"{d['steps']:,}".replace(",", " "))


if auto_play:
    import time
    for k in range(n_steps + 1):
        _render(k)
        time.sleep(min(0.6, 6.0 / max(n_steps, 1)))
    step = n_steps
else:
    _render(step)

st.caption("Kreise: Paare (Blutgruppe beschriftet, grün = versorgt, grau = unversorgt). Sterne: altruistische Spender. "
           "Grüne Linie: gewählter Kreis. Lila Linie: gewählte Kette. Graue Linien: alle möglichen, nicht gewählten Kanten.")

st.markdown("---")

# --- Verteilung über viele Karten -----------------------------------------------------------------------------------

st.markdown("## 🎯 Nicht nur diese eine Karte")
st.markdown(f"{len(C.DIST_SEEDS)} feste Karten mit denselben Einstellungen (Paare {n}, altruistische Spender {n_alt}, Sensibilisierung ≤{sens} %), getrennt vom Seed oben.")
if card == C.CARD_NONE:
    with st.spinner("Rechne über 100 feste Karten..."):
        dist = _distribution(int(n), int(n_alt), int(sens), int(cap), int(chain_cap))
    p1, p2, p3, p4 = st.columns(4)
    p1.metric("Versorgungsanteil (Mittel | Median)", f"{_share(dist['matched_share']['mean'])} | {_share(dist['matched_share']['median'])}")
    p2.metric("Kappung 2 (Mittel | Median)", f"{_share(dist['cap2_share']['mean'])} | {_share(dist['cap2_share']['median'])}")
    p3.metric("Qualität (Mittel | Median)", _ms(dist["quality"], 0))
    p4.metric("Aufwand (Mittel | Median)", _ms(dist["steps"], 0))
    c1, c2 = st.columns([3, 2])
    c1.plotly_chart(build_length_hist(dist["length_hist_share"]), width="stretch", key="nt_hist_chart")
    c2.table({"Größe": list(dist["length_hist"]), "Anzahl": list(dist["length_hist"].values()), "Anteil": [_share(dist["length_hist_share"][L]) for L in dist["length_hist"]]})

    st.markdown("### Kappung 2 (exakt) vs. allgemeiner Modus")
    st.plotly_chart(build_cap_comparison(dist["cap2_share"]["mean"], dist["matched_share"]["mean"], dist["cap2_quality"]["mean"], dist["quality"]["mean"]), width="stretch", key="nt_cap_chart")

    with st.spinner("Rechne den Beitrag der altruistischen Spender..."):
        alt = _altruistic_contribution(int(n), int(sens), int(n_alt), int(cap), int(chain_cap))
    st.caption(f"Beitrag der {n_alt} altruistischen Spender (mit vs. ohne, gleiche Karten): {_ms(alt['matched_gain'], 1)} zusätzliche Patienten, {_ms(alt['quality_gain'], 0)} zusätzliche Qualität.")

    with st.spinner("Prüfe die Heuristik gegen die exakte Kappung-2-Lösung..."):
        nv = _naive_vs_cap2(int(n), int(n_alt), int(sens), int(cap), int(chain_cap))
    st.caption(f"Ehrlichkeit der Heuristik: eine einfache, unsortierte Greedy-Reihenfolge verliert auf {nv['naive_losses']} von {nv['total']} Karten gegen die exakte Kappung-2-Lösung; "
              f"die Mehrfachstart-Heuristik MIT Sicherheitsnetz verliert auf {nv['multi_losses']} von {nv['total']} - genau 0, weil das Sicherheitsnetz das erzwingt (siehe README).")
else:
    st.info("Feste Karte: es gibt nur diese eine Ziehung. Für die Verteilung über viele Karten einen zufälligen Pool wählen.")

st.markdown("---")

st.subheader("🔬 Wovon hängt der Aufwand ab?")
if st.button("Aufwand gegen die Größe (n = 10 bis 35)", key="scale_start"):
    st.session_state["scale_on"] = True
if st.session_state.get("scale_on"):
    with st.spinner("Rechne..."):
        srows = _effort_scaling(int(sens))
    st.plotly_chart(build_scale(srows), width="stretch", key="nt_scale_chart")
    st.caption("Der Kandidatenraum wächst sehr steil mit der Poolgröße (Kreise/Ketten bis zur Kappung, kombinatorisch) - "
              "einer der Gründe, warum echte Kidney-Exchange-Programme Kreise auf 2-3 und Ketten auf eine praktikable Länge begrenzen.")

st.markdown("---")

# --- Grenzen -------------------------------------------------------------------------------------------------------

st.subheader("🚧 Wo die Annahmen enden")
st.markdown(
    """
| Annahme | Was tatsächlich fehlt |
|---|---|
| **Sensibilisierung als einzelner Prozentwert** | Echtes Crossmatch/HLA-Screening ist weit komplexer (spezifische Antikörper, Panel-reaktive Antikörper je Allel) - hier bewusst ein grober, integer-wertiger Ersatz. |
| **Vereinfachte, illustrative Blutgruppenverteilung** | Stanford Blood Center/AABB-Werte für die US-Bevölkerung, ausdrücklich "zu Bildungszwecken" - keine belastbare globale Epidemiologie. |
| **Keine Desensibilisierungs-Protokolle** | Manche Programme transplantieren auch über ein positives Crossmatch hinweg, medizinisch aufwendiger - hier nicht modelliert. |
| **Ein einzelner, undifferenzierter Pool** | Reale Programme unterscheiden regionale/nationale Pools mit unterschiedlichen Regeln. |
| **Keine Wartezeit-/Prioritätsregeln** | Qualität ist eine abstrakte, integer-wertige Kennziffer, keine Zusammensetzung aus realen klinischen und fairnessbezogenen Faktoren. |
| **Die Heuristik ab Kappung 3 ist nicht bewiesen optimal** | Die gemessene Lücke gegen `nt_oracle.py` (kleine Karten, in den Tests) ist der App eigener, ehrlicher Beweis ihrer Grenzen. |
"""
)

st.markdown("---")

st.subheader("📚 Die Matching-Linie im Rückblick")
st.markdown(
    """
Von **Greedy** (eine gewählte Zuordnung bleibt) über **allgemeine Graphen** (Hopcroft-Karp, Ungarische Methode,
Blossom) bis zur **Konvergenz** (Ungarisch + Blossom = min-Cost-Perfect-Matching) - dann der zweite Ast:
**präferenzbasiertes, stabiles Matching** (Gale-Shapley), erweitert um **einseitige Wohnungsmärkte** (Stabile
Mitbewohner, Top Trading Cycles) und **many-to-one-Kapazitäten** (Krankenhaus-Zulassung) - und hier, am Ende der
Linie, der Schritt von freier Präferenz zu **medizinisch beschränkter Kompatibilität**. Ein dritter, unabhängiger
Ast: **Online-Matching** (Entscheidungen ohne Blick in die Zukunft).
"""
)

st.markdown("---")

with st.expander("📐 Mathematische Formulierung"):
    st.markdown(
        r"""
**Modell.** Unverträgliche Paare $(patient_i, spender_i)$, $i = 1, ..., n$, plus altruistische Spender ohne eigenen
Patienten. Eine Kante $spender_i \to patient_j$ existiert, wenn ABO-verträglich UND das (simulierte) Crossmatch
besteht. Gesucht: eine Menge disjunkter Kreise (Länge $2 \le k \le K$) und Ketten (gestartet von einem altruistischen
Spender, Länge $\le L$), die zuerst die Patientenzahl, dann die Qualität maximiert.

**Kappung 2 (Roth, Sönmez & Ünver 2005, *JET*, "Pairwise Kidney Exchange").** Reiner Paartausch ist logistisch
einfacher, weil nur 2 gleichzeitige Operationsteams nötig sind (statt $2k$ bei einem $k$-Kreis). Er reduziert exakt
auf Maximum-Weight-Matching im allgemeinen Graphen - lösbar mit Edmonds' Blossom-Algorithmus (`nt_blossom.py`).

**Warum Kreise Simultan-OPs brauchen, Ketten nicht.** In einem $k$-Kreis darf kein Spender geben, bevor sein eigener
Patient schon versorgt ist - sonst könnte ein früherer Spender am Ende leer ausgehen, wenn ein späteres Glied
ausfällt. Eine Kette, gestartet von einem altruistischen Spender, kann Glied für Glied ablaufen: fällt ein Glied aus,
verliert nur das NÄCHSTE Glied, niemand, der schon gespendet hat (Rees et al. 2009, *NEJM*, "A Nonsimultaneous,
Extended, Altruistic-Donor Chain").

**Ab Kappung 3: NP-schwer** (Abraham, Blum & Sandholm 2007, "Clearing Algorithms for Barter Exchange Markets" -
Grundlage echter Kidney-Exchange-Clearinghouses). Roth, Sönmez & Ünver (2007, *AER*, "Efficient Kidney Exchange")
zeigen: der Schritt von 2er- auf 3er-Tausch bringt einen substanziellen Zugewinn, längere Kreise kaum noch mehr.

Implementiert in `nt_scenario.py` (Kompatibilitätsgraph, ABO-Regel, ISBN-artige ABO-Tabelle), `nt_blossom.py`
(Kappung 2, Kopie von `weighted-blossom-demo/wb_blossom.py`), `nt_exchange.py` (Kandidatenerzeugung,
Mehrfachstart-Heuristik mit Sicherheitsnetz), `nt_oracle.py` (Brute-Force-Orakel, nur in den Tests).
        """
    )

st.markdown("---")

st.caption(
    "Diese Demo ist Teil des Portfolios von [Sebastian Hanisch](https://sebastianhanisch.net) – "
    "Operations Research und Machine Learning. Interesse an einer maßgeschneiderten Lösung für "
    "Ihr Unternehmen? [Kontakt aufnehmen](https://sebastianhanisch.net/kontakt.html)"
)
