"""Robot capability bands.

These are not in the manual. They encode what student-built FTC robots
typically accomplish, from kit-bot / first-year through worlds-level.
Cycle times are dominated by driving a 12-ft field, intaking wiffle balls,
and launching into a ~20x14 in CELL vs dunking into a 4 in FLOWER opening.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Skill:
    name: str
    # Drive
    speed_in_s: float
    turn_penalty_s: float
    # Manipulation
    intake_s: float
    launch_s: float
    flower_place_s: float
    flower_extract_s: float
    # Accuracy (0-1)
    hive_accuracy: float
    flower_pollen_accuracy: float
    flower_nectar_accuracy: float
    intake_reliability: float
    # Auto
    auto_leave_p: float
    auto_preload_launch_p: float
    auto_park_p: float
    auto_extra_cycles: float  # expected extra collect+launch cycles in AUTO
    # Endgame
    park_commit_s: float  # how many seconds before 0:00 they head to park


SKILLS: dict[str, Skill] = {
    "starter": Skill(
        name="starter",
        speed_in_s=28.0,
        turn_penalty_s=0.8,
        intake_s=3.5,
        launch_s=2.2,
        flower_place_s=4.0,
        flower_extract_s=3.0,
        hive_accuracy=0.48,
        flower_pollen_accuracy=0.28,
        flower_nectar_accuracy=0.12,
        intake_reliability=0.70,
        auto_leave_p=0.85,
        auto_preload_launch_p=0.35,
        auto_park_p=0.45,
        auto_extra_cycles=0.0,
        park_commit_s=12.0,
    ),
    "developing": Skill(
        name="developing",
        speed_in_s=52.0,
        turn_penalty_s=0.45,
        intake_s=1.8,
        launch_s=1.3,
        flower_place_s=2.4,
        flower_extract_s=1.6,
        hive_accuracy=0.72,
        flower_pollen_accuracy=0.58,
        flower_nectar_accuracy=0.38,
        intake_reliability=0.88,
        auto_leave_p=0.97,
        auto_preload_launch_p=0.80,
        auto_park_p=0.75,
        auto_extra_cycles=0.4,
        park_commit_s=8.0,
    ),
    "competitive": Skill(
        name="competitive",
        speed_in_s=78.0,
        turn_penalty_s=0.25,
        intake_s=1.05,
        launch_s=0.7,
        flower_place_s=1.5,
        flower_extract_s=1.0,
        hive_accuracy=0.90,
        flower_pollen_accuracy=0.82,
        flower_nectar_accuracy=0.68,
        intake_reliability=0.96,
        auto_leave_p=0.995,
        auto_preload_launch_p=0.97,
        auto_park_p=0.93,
        auto_extra_cycles=1.2,
        park_commit_s=5.5,
    ),
    "elite": Skill(
        name="elite",
        speed_in_s=100.0,
        turn_penalty_s=0.12,
        intake_s=0.55,
        launch_s=0.35,
        flower_place_s=0.9,
        flower_extract_s=0.6,
        hive_accuracy=0.97,
        flower_pollen_accuracy=0.93,
        flower_nectar_accuracy=0.86,
        intake_reliability=0.99,
        auto_leave_p=1.0,
        auto_preload_launch_p=1.0,
        auto_park_p=0.99,
        auto_extra_cycles=2.2,
        park_commit_s=4.0,
    ),
}

SKILL_HELP = {
    "starter": "First-year / kit-bot: slow, missed shots, often parks late.",
    "developing": "Typical mid-season local event robot.",
    "competitive": "Solid regional / state-level robot.",
    "elite": "Worlds-level cycle speed and reliability.",
}
