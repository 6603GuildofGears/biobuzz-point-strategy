"""Batch match runner and summary statistics."""

from __future__ import annotations

import time
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from typing import Any, Iterable

from .rules import DEFAULT_PHYSICS, PhysicsAssumptions
from .scoring import MatchScore
from .sim import MatchSim
from .skills import SKILLS
from .strategies import STRATEGIES


@dataclass
class MatchRow:
    red_skill: str
    blue_skill: str
    red_strategy: str
    blue_strategy: str
    seed: int
    winner: str
    red_points: int
    blue_points: int
    red_tips: int
    blue_tips: int
    red_rp: int
    blue_rp: int
    red_leave: int
    blue_leave: int
    red_owned: int
    blue_owned: int
    red_bottom: int
    blue_bottom: int
    red_auto_tips: int
    blue_auto_tips: int


def _play(args: tuple) -> MatchRow:
    red_skill, blue_skill, red_strategy, blue_strategy, seed, physics_d = args
    physics = PhysicsAssumptions(**physics_d)
    sim = MatchSim(red_skill, blue_skill, red_strategy, blue_strategy, seed=seed, physics=physics)
    score: MatchScore = sim.run()
    red_rp, _ = score.red.ranking_points(score.winner == "red", score.winner == "tie")
    blue_rp, _ = score.blue.ranking_points(score.winner == "blue", score.winner == "tie")
    return MatchRow(
        red_skill=red_skill,
        blue_skill=blue_skill,
        red_strategy=red_strategy,
        blue_strategy=blue_strategy,
        seed=seed,
        winner=score.winner,
        red_points=score.red.match_points,
        blue_points=score.blue.match_points,
        red_tips=score.red.tips,
        blue_tips=score.blue.tips,
        red_rp=red_rp,
        blue_rp=blue_rp,
        red_leave=score.red.leave,
        blue_leave=score.blue.leave,
        red_owned=score.red.owned_flower_elements,
        blue_owned=score.blue.owned_flower_elements,
        red_bottom=score.red.bottom_nectar,
        blue_bottom=score.blue.bottom_nectar,
        red_auto_tips=score.red.auto_tips,
        blue_auto_tips=score.blue.auto_tips,
    )


def iter_jobs(
    matches: int,
    skills: Iterable[str],
    strategies: Iterable[str],
    seed0: int,
    physics: PhysicsAssumptions,
    mix: str = "same_skill",
) -> list[tuple]:
    """Build a balanced set of jobs.

    same_skill: both alliances share a skill band; all strategy vs strategy pairs.
    cross_skill: also mixes adjacent skill bands.
    """
    skills = list(skills)
    strategies = list(strategies)
    physics_d = asdict(physics)
    jobs: list[tuple] = []
    seed = seed0
    # Pairwise strategies at each skill, mirrored colors so A vs B is fair.
    combo = 0
    while len(jobs) < matches:
        for skill in skills:
            for sa in strategies:
                for sb in strategies:
                    jobs.append((skill, skill, sa, sb, seed, physics_d))
                    seed += 1
                    combo += 1
                    if len(jobs) >= matches:
                        return jobs
        if mix == "cross_skill" and len(skills) > 1:
            for i, s0 in enumerate(skills[:-1]):
                s1 = skills[i + 1]
                for sa in strategies:
                    for sb in strategies:
                        jobs.append((s0, s1, sa, sb, seed, physics_d))
                        seed += 1
                        if len(jobs) >= matches:
                            return jobs
    return jobs[:matches]


def run_batch(
    matches: int = 4000,
    skills: list[str] | None = None,
    strategies: list[str] | None = None,
    seed: int = 1,
    physics: PhysicsAssumptions | None = None,
    workers: int = 0,
    mix: str = "same_skill",
    progress: bool = True,
) -> list[MatchRow]:
    physics = physics or DEFAULT_PHYSICS
    skills = skills or list(SKILLS)
    strategies = strategies or list(STRATEGIES)
    jobs = iter_jobs(matches, skills, strategies, seed, physics, mix=mix)
    rows: list[MatchRow] = []
    t0 = time.time()
    if workers == 1 or len(jobs) < 8:
        for i, job in enumerate(jobs, 1):
            rows.append(_play(job))
            if progress and i % 50 == 0:
                print(f"  {i}/{len(jobs)} matches", flush=True)
    else:
        with ProcessPoolExecutor(max_workers=workers or None) as ex:
            futs = [ex.submit(_play, job) for job in jobs]
            done = 0
            for fut in as_completed(futs):
                rows.append(fut.result())
                done += 1
                if progress and done % 50 == 0:
                    print(f"  {done}/{len(jobs)} matches", flush=True)
    if progress:
        dt = time.time() - t0
        print(f"Finished {len(rows)} matches in {dt:.1f}s ({len(rows)/max(dt, 0.01):.1f}/s)")
    return rows


def _mean(xs: list[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def summarize(rows: list[MatchRow]) -> dict[str, Any]:
    """Perspective-normalized stats: each alliance counted as 'us'."""

    by_skill_strat: dict[tuple[str, str], list[dict[str, float]]] = defaultdict(list)
    matchups: dict[tuple[str, str, str], list[int]] = defaultdict(list)  # skill, us, them -> win
    overall_by_strat: dict[str, list[dict[str, float]]] = defaultdict(list)

    def eat(skill: str, strat: str, opp: str, pts: int, opp_pts: int, tips: int, rp: int,
            owned: int, bottom: int, auto_tips: int, winner: str, us_color: str) -> None:
        won = 1 if winner == us_color else 0
        tied = 1 if winner == "tie" else 0
        rec = {
            "pts": pts,
            "opp": opp_pts,
            "tips": tips,
            "rp": rp,
            "owned": owned,
            "bottom": bottom,
            "auto_tips": auto_tips,
            "win": won,
            "tie": tied,
        }
        by_skill_strat[(skill, strat)].append(rec)
        overall_by_strat[strat].append(rec)
        matchups[(skill, strat, opp)].append(won if not tied else 0)

    for r in rows:
        eat(r.red_skill, r.red_strategy, r.blue_strategy, r.red_points, r.blue_points,
            r.red_tips, r.red_rp, r.red_owned, r.red_bottom, r.red_auto_tips, r.winner, "red")
        eat(r.blue_skill, r.blue_strategy, r.red_strategy, r.blue_points, r.red_points,
            r.blue_tips, r.blue_rp, r.blue_owned, r.blue_bottom, r.blue_auto_tips, r.winner, "blue")

    def pack(recs: list[dict[str, float]]) -> dict[str, float]:
        n = len(recs)
        return {
            "n": n,
            "win_rate": _mean([x["win"] for x in recs]),
            "tie_rate": _mean([x["tie"] for x in recs]),
            "avg_points": _mean([x["pts"] for x in recs]),
            "avg_opp": _mean([x["opp"] for x in recs]),
            "avg_tips": _mean([x["tips"] for x in recs]),
            "avg_rp": _mean([x["rp"] for x in recs]),
            "avg_owned_elements": _mean([x["owned"] for x in recs]),
            "avg_bottom_nectar": _mean([x["bottom"] for x in recs]),
            "avg_auto_tips": _mean([x["auto_tips"] for x in recs]),
        }

    skills = sorted({r.red_skill for r in rows} | {r.blue_skill for r in rows})
    strats = list(STRATEGIES)
    tables = {}
    for skill in skills:
        tables[skill] = {
            strat: pack(by_skill_strat.get((skill, strat), []))
            for strat in strats
        }
    matrices = {}
    for skill in skills:
        mat = {}
        for sa in strats:
            mat[sa] = {
                sb: _mean(matchups.get((skill, sa, sb), []))
                for sb in strats
            }
        matrices[skill] = mat

    # Recommendation: highest win rate, then points, then RP
    recs = []
    for skill in skills:
        ranked = sorted(
            tables[skill].items(),
            key=lambda kv: (kv[1]["win_rate"], kv[1]["avg_rp"], kv[1]["avg_points"]),
            reverse=True,
        )
        recs.append({"skill": skill, "ranked": [{"strategy": k, **v} for k, v in ranked]})

    return {
        "n_matches": len(rows),
        "skills": skills,
        "strategies": strats,
        "by_skill": tables,
        "matchup_winrate": matrices,
        "overall": {s: pack(overall_by_strat[s]) for s in strats},
        "recommendations": recs,
    }
