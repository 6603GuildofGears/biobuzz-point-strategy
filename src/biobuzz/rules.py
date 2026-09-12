"""Scoring and timing constants from the BIOBUZZ Competition Manual V1.

Point values follow Table 10-2. Ranking-point thresholds follow Table 10-3
("All Other Events"). Hive-tip *physics* (how much mass tips a CELL) is not
published in the manual; those values live in ASSUMPTIONS and are configurable.
"""

from __future__ import annotations

from dataclasses import dataclass

# --- Match clock -----------------------------------------------------------
AUTO_S = 30.0
TRANSITION_S = 8.0
TELEOP_S = 120.0
PLAY_S = AUTO_S + TELEOP_S  # 150s of robot play, excluding the 8s transition
FLOWER_UNLOCK_TELEOP_S = 60.0  # last 60s of TELEOP
NECTAR_ALL_REMAINING_TELEOP_S = 60.0

# --- Field / robot limits (manual) -----------------------------------------
FIELD_IN = 144.0
POSSESSION_LIMIT = 4
POLLEN_COUNT = 40
NECTAR_PER_ALLIANCE = 8
# G408: a ROBOT may not CONTROL NECTAR of the opponent alliance color.
# POLLEN is yellow/neutral — either alliance may use it. Each alliance has
# a private pool of 8 NECTAR (3 start in their upward CELL, 5 enter via
# the LOADING ZONE). You cannot steal theirs to tip your HIVE or dunk flowers.
FLOWERS = 4
ROBOTS_PER_ALLIANCE = 2

POLLEN_DIAMETER_IN = 2.8
NECTAR_DIAMETER_IN = 3.6
POLLEN_MASS_LB = 0.055
# Same polyethylene family; scale by volume unless overridden.
NECTAR_MASS_RATIO = (NECTAR_DIAMETER_IN / POLLEN_DIAMETER_IN) ** 3  # ~2.125

# Flower scoring volume is the 17 in pipes between the top and middle rings
# (top opening is 21.5 in above the tiles; pipes are 17 in).
FLOWER_SCORING_HEIGHT_IN = 17.0
FLOWER_OPENING_IN = 4.0

# --- Match points (Table 10-2) ---------------------------------------------
LEAVE_PTS = 3
PARK_PTS = 5  # AUTO park and TELEOP park are each 5
HIVE_TIP_PTS = 20
CELL_REMAINING_PTS = 2
BOTTOM_NECTAR_BONUS_PTS = 5
OWNED_FLOWER_ELEMENT_PTS = 2
GARDEN_ELEMENT_PTS = 1

# --- Ranking points (Tables 10-2 and 10-3, "All Other Events") -------------
SWARM_RP_THRESHOLD_PTS = 16  # combined LEAVE + PARK points
POLLINATOR_1_TIPS = 4
POLLINATOR_2_TIPS = 7
WIN_RP = 3
TIE_RP = 1
SWARM_RP = 1
POLLINATOR_RP = 1  # each of P1 and P2

FOUL_MINOR = 5
FOUL_MAJOR = 20


@dataclass(frozen=True)
class PhysicsAssumptions:
    """Values the manual does not specify. All are CLI-overridable.

    Empty-cell tip mass of 8 pollen-equivalents is the main design guess:
    two robots at the 4-element possession limit can tip together, and one
    robot carrying 4 nectar (~8.5 PE) can solo-tip. First tip is easier
    because 3 nectar already start in the upward CELL.
    """

    empty_cell_tip_pe: float = 8.0
    nectar_mass_ratio: float = NECTAR_MASS_RATIO
    flower_scoring_height_in: float = FLOWER_SCORING_HEIGHT_IN
    dump_settle_s: float = 0.6  # G409: elements must hit the floor first
    hive_tip_duration_s: float = 1.2
    nectar_intro_delay_s: float = 1.5
    launch_range_in: float = 28.0
    intake_range_in: float = 12.0
    flower_range_in: float = 14.0
    park_margin_in: float = 2.0


DEFAULT_PHYSICS = PhysicsAssumptions()


def pollen_equiv(kind: str, nectar_mass_ratio: float = NECTAR_MASS_RATIO) -> float:
    return nectar_mass_ratio if kind == "nectar" else 1.0
