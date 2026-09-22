"""Presets: jedes hat einen Hilfetext, Regler-/Schrittgitter sind gültig, die genannten Zahlen stimmen."""

import nt_constants as C
import nt_evaluation as ev
from nt_presets import PRESET_KEYS, SETTING_SPECS, STEPS


def test_every_preset_has_help_text():
    for name in C.PRESETS:
        assert name in C.PRESET_HELP and C.PRESET_HELP[name]


def test_preset_keys_cover_every_setting_spec():
    assert set(PRESET_KEYS.values()) == set(SETTING_SPECS)
    for name, p in C.PRESETS.items():
        assert set(p) == set(PRESET_KEYS), name


def test_bounds_and_step_grid_are_valid():
    for state_key, spec in SETTING_SPECS.items():
        if spec.lo is not None and spec.hi is not None and isinstance(spec.default, (int, float)):
            assert spec.lo <= spec.default <= spec.hi, state_key
    for key, step in STEPS.items():
        lo, hi = SETTING_SPECS[key].lo, SETTING_SPECS[key].hi
        assert (hi - lo) % step == 0, key


def test_presets_do_not_collide_with_dist_seeds():
    for name, p in C.PRESETS.items():
        assert p["seed"] not in C.DIST_SEEDS, name


def _verdict_for(name):
    p = C.PRESETS[name]
    sc = ev.scenario_from_settings(p["card"], p["n"], p["n_alt"], p["seed"], p["sens"])
    a = ev.analyse(sc, p["cap"], p["chain_cap"])
    return ev.verdict(a)


def test_presets_show_what_the_help_text_says():
    d = _verdict_for("⛓️ Ketten-Lehrbuchkarte")
    assert d["matched"] == 4 and d["quality"] == 286 and d["n_cycles"] == 0 and d["n_chains"] == 1

    d = _verdict_for("🔁 Kreis-Lehrbuchkarte")
    assert d["matched"] == 3 and d["quality"] == 183 and d["n_chains"] == 0

    d = _verdict_for("👫 Nur Paartausch (Kappung 2)")
    assert d["source"] == "cap2"

    d = _verdict_for("😴 Kein Kompatibilitätsglück")
    assert d["n_chains"] == 0        # keine altruistischen Spender -> keine Ketten möglich

    d = _verdict_for("🔬 Beweis")
    assert d["n"] == 8


def test_default_preset_matches_test_claims():
    sc = ev.scenario_from_settings(C.CARD_NONE, C.DEFAULT_N, C.DEFAULT_N_ALT, C.DEFAULT_SEED, C.DEFAULT_SENS)
    a = ev.analyse(sc, C.DEFAULT_CAP, C.DEFAULT_CHAIN_CAP)
    d = ev.verdict(a)
    assert d["n"] == 25


def test_proof_preset_is_small_enough_for_the_oracle():
    import nt_oracle as O
    assert C.PRESETS["🔬 Beweis"]["n"] <= O.PRACTICAL_MAX_N
