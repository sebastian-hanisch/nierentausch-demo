"""Jede Zahl in den Hilfetexten, Presets und der README ist hier über die 100 festen Karten (DIST_SEEDS) belegt.
Alles rechnet mit ganzen Zahlen und einem eigenen Zufallsgenerator - die Werte sind auf jeder Plattform dieselben;
die Toleranzen decken nur die Rundung auf die im Text genannten Stellen."""

import pytest

import nt_evaluation as ev


def near(value, expected, tol):
    assert abs(value - expected) <= tol, f"{value:.4f} statt {expected}"


@pytest.fixture(scope="module")
def dist():
    return ev.distribution(25, 3, 60, 3, 4)


def test_default_map_matched_share(dist):
    near(dist["matched_share"]["mean"], 0.6156, 0.001)
    assert dist["matched_share"]["median"] == 0.6
    near(dist["cap2_share"]["mean"], 0.5696, 0.001)
    assert dist["cap2_share"]["median"] == 0.56


def test_default_map_quality(dist):
    near(dist["quality"]["mean"], 1173.02, 0.5)
    assert dist["quality"]["median"] == 1138.0
    near(dist["cap2_quality"]["mean"], 1098.53, 0.5)
    assert dist["cap2_quality"]["median"] == 1043.0


def test_default_map_effort(dist):
    near(dist["steps"]["mean"], 122751.02, 5)
    assert dist["steps"]["median"] == 98201.0


def test_length_distribution(dist):
    assert dist["n_candidates_total"] == 653
    assert dist["length_hist"] == {1: 107, 2: 326, 3: 100, 4: 120}


def test_altruistic_contribution():
    r = ev.altruistic_contribution(25, 60, 3)
    near(r["matched_gain"]["mean"], 2.18, 0.02)
    assert r["matched_gain"]["median"] == 2.0
    near(r["quality_gain"]["mean"], 182.46, 1.0)
    assert r["quality_gain"]["median"] == 165.0


def test_naive_vs_cap2_and_safety_net():
    r = ev.naive_vs_cap2(25, 3, 60)
    assert r == {"total": 100, "naive_losses": 58, "multi_losses": 0}


def test_effort_scaling():
    rows = {r["n"]: r["steps"] for r in ev.effort_scaling(60)}
    expect = {10: 530.8, 20: 18003.6, 25: 91058.4, 30: 253298.2, 35: 644797.4}
    for n, steps in expect.items():
        near(rows[n], steps, max(1.0, steps * 0.02))
    ns = sorted(expect)
    values = [rows[n] for n in ns]
    assert values == sorted(values)


def test_heuristic_accuracy_pinned():
    r = ev.heuristic_accuracy(60)
    assert r == {"exact": 58, "total": 80, "mean_gap": 0.15, "max_gap": 2}


def test_chain_and_cycle_example_cards():
    import nt_scenario as S
    from nt_exchange import solve

    res_chain = solve(S.chain_example(), 3, 4)
    assert sum(c.size for c in res_chain.chosen) == 4
    assert sum(c.quality for c in res_chain.chosen) == 286

    res_cycle = solve(S.cycle_example(), 3, 1)
    assert sum(c.size for c in res_cycle.chosen) == 3
    assert sum(c.quality for c in res_cycle.chosen) == 183
