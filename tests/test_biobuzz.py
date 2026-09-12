from __future__ import annotations

from biobuzz.scoring import score_flower_stack, AllianceBreakdown
from biobuzz import rules
from biobuzz.sim import MatchSim
from biobuzz.monte_carlo import summarize, run_batch
from biobuzz.rules import PhysicsAssumptions


def test_empty_flower_scores_nothing():
    assert score_flower_stack([("pollen", None), ("pollen", None)]) == {"red": 0, "blue": 0}


def test_bottom_and_owner():
    stack = [("nectar", "red"), ("pollen", None), ("nectar", "blue")]
    pts = score_flower_stack(stack)
    # red bottom 5; blue owns 3 elements * 2 = 6
    assert pts["red"] == 5
    assert pts["blue"] == 6


def test_owner_gets_all_elements_regardless_of_color():
    stack = [("nectar", "blue"), ("nectar", "red"), ("pollen", None)]
    pts = score_flower_stack(stack)
    assert pts["blue"] == 5  # bottom
    assert pts["red"] == 6  # owner of 3


def test_ranking_points_swarm_and_pollinator():
    bd = AllianceBreakdown(leave=2, auto_park=2, teleop_park=0, auto_tips=1, teleop_tips=3)
    assert bd.park_leave_pts == 16
    rp, bits = bd.ranking_points(won=True, tied=False)
    assert bits["win"] == 3
    assert bits["swarm"] == 1
    assert bits["pollinator1"] == 1
    assert bits["pollinator2"] == 0
    assert rp == 5


def test_pollinator2_requires_seven_tips():
    bd = AllianceBreakdown(teleop_tips=7)
    rp, bits = bd.ranking_points(won=False, tied=False)
    assert bits["pollinator1"] == 1
    assert bits["pollinator2"] == 1
    assert rp == 2


def test_deterministic_match_seed():
    a = MatchSim("developing", "developing", "hive_cycle", "flower_focus", seed=42)
    b = MatchSim("developing", "developing", "hive_cycle", "flower_focus", seed=42)
    sa, sb = a.run(), b.run()
    assert sa.red.match_points == sb.red.match_points
    assert sa.blue.match_points == sb.blue.match_points
    assert sa.winner == sb.winner


def test_preload_and_element_counts():
    sim = MatchSim("starter", "starter", "park_and_dump", "park_and_dump", seed=1)
    w = sim.world
    assert len(w.elements) == 40 + 16
    pollen = [e for e in w.elements if e.kind == "pollen"]
    assert len(pollen) == 40
    assert sum(len(b.inventory) for b in w.robots) == 16
    assert len(w.hives["red"].up_cell()) == 3
    assert len(w.flowers[0]) == 4


def test_first_tip_is_possible_from_preload():
    """3 starting nectar (~6.4 PE) + 2 pollen should tip at default mass 8."""
    sim = MatchSim("elite", "starter", "hive_cycle", "park_and_dump", seed=2)
    score = sim.run()
    assert score.red.tips >= 1


def test_flower_scoring_locked_before_last_minute():
    sim = MatchSim("elite", "elite", "flower_focus", "flower_focus", seed=5)
    # Mid AUTO / early teleop: flower stacks should still be starting pollen only
    # until unlock. After a full match, flower_focus may add nectar.
    score = sim.run()
    # If they scored flower points, it must be via nectar ownership, not pollen-only.
    total_owned = score.red.owned_flower_elements + score.blue.owned_flower_elements
    if total_owned:
        assert score.red.bottom_nectar + score.blue.bottom_nectar >= 1


def test_small_batch_runs():
    rows = run_batch(
        matches=12,
        skills=["developing"],
        strategies=["hive_cycle", "flower_focus"],
        seed=99,
        workers=1,
        progress=False,
        physics=PhysicsAssumptions(),
    )
    assert len(rows) == 12
    summary = summarize(rows)
    assert summary["n_matches"] == 12
    assert "developing" in summary["by_skill"]


def test_match_points_nonnegative_and_clock_completes():
    sim = MatchSim("competitive", "developing", "hive_then_flower", "nectar_tips", seed=8)
    score = sim.run()
    assert sim.world.play_t >= rules.PLAY_S - 0.2
    assert score.red.match_points >= 0
    assert score.blue.match_points >= 0
