"""Alliance strategy policies.

A strategy is a preference over actions. Robots still obey physics, possession
limits, and the clock; they just choose different targets.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Strategy:
    name: str
    title: str
    blurb: str
    # During TELEOP before flowers unlock, prefer hive vs collect nectar vs extract.
    pre_flower: str  # hive, nectar_hive, extract, garden, idle
    # After flowers unlock.
    post_flower: str  # hive, flower, split, nectar_hive
    # AUTO intent.
    auto: str  # dump_park, dump_cycle, leave_only
    # Stop hive cycling once this many tips (0 = never stop for this reason).
    tip_goal: int
    # Head to park this many seconds before match end (0 = use skill default).
    park_override_s: float = 0.0
    # Prefer nectar over pollen when collecting for hive.
    prefer_nectar: bool = False
    # Try to claim bottom nectar first, then top nectar.
    flower_nectar_first: bool = True


STRATEGIES: dict[str, Strategy] = {
    "hive_cycle": Strategy(
        name="hive_cycle",
        title="Hive cycling",
        blurb="Launch pollen/nectar into the CELL all match. Park at the end. Ignore flowers.",
        pre_flower="hive",
        post_flower="hive",
        auto="dump_cycle",
        tip_goal=0,
    ),
    "hive_then_flower": Strategy(
        name="hive_then_flower",
        title="Hive, then flowers",
        blurb="Cycle the HIVE until the last 60s, then contest FLOWERS with nectar + pollen.",
        pre_flower="hive",
        post_flower="flower",
        auto="dump_cycle",
        tip_goal=0,
        flower_nectar_first=True,
    ),
    "nectar_tips": Strategy(
        name="nectar_tips",
        title="Nectar-powered tips",
        blurb="Hunt NECTAR because it is ~2x as heavy, so the HIVE tips with fewer cycles.",
        pre_flower="nectar_hive",
        post_flower="nectar_hive",
        auto="dump_cycle",
        tip_goal=0,
        prefer_nectar=True,
    ),
    "flower_focus": Strategy(
        name="flower_focus",
        title="Flower focus",
        blurb="Dump AUTO preload, extract FLOWER pollen, then spend the last 60s stuffing FLOWERS.",
        pre_flower="extract",
        post_flower="flower",
        auto="dump_park",
        tip_goal=1,
        flower_nectar_first=True,
    ),
    "rp_hunter": Strategy(
        name="rp_hunter",
        title="Ranking-point hunter",
        blurb="LEAVE + PARK for SWARM, get 4 TIPS for POLLINATOR 1, then flowers if time.",
        pre_flower="hive",
        post_flower="split",
        auto="dump_park",
        tip_goal=4,
    ),
    "park_and_dump": Strategy(
        name="park_and_dump",
        title="Park and dump",
        blurb="LEAVE, launch whatever is easy, PARK. A realistic first-meet plan.",
        pre_flower="hive",
        post_flower="hive",
        auto="leave_only",
        tip_goal=2,
        park_override_s=18.0,
    ),
}


def strategy_names() -> list[str]:
    return list(STRATEGIES)
