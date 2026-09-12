"""Pure scoring functions for BIOBUZZ match outcomes."""

from __future__ import annotations

from dataclasses import dataclass, field

from . import rules


@dataclass
class AllianceBreakdown:
    leave: int = 0
    auto_park: int = 0
    teleop_park: int = 0
    auto_tips: int = 0
    teleop_tips: int = 0
    cell_remaining: int = 0
    bottom_nectar: int = 0
    owned_flower_elements: int = 0
    garden: int = 0
    fouls_against_opponent: int = 0  # points this alliance received from opponent fouls

    @property
    def tips(self) -> int:
        return self.auto_tips + self.teleop_tips

    @property
    def park_leave_pts(self) -> int:
        return (
            self.leave * rules.LEAVE_PTS
            + self.auto_park * rules.PARK_PTS
            + self.teleop_park * rules.PARK_PTS
        )

    @property
    def match_points(self) -> int:
        return (
            self.leave * rules.LEAVE_PTS
            + self.auto_park * rules.PARK_PTS
            + self.teleop_park * rules.PARK_PTS
            + self.auto_tips * rules.HIVE_TIP_PTS
            + self.teleop_tips * rules.HIVE_TIP_PTS
            + self.cell_remaining * rules.CELL_REMAINING_PTS
            + self.bottom_nectar * rules.BOTTOM_NECTAR_BONUS_PTS
            + self.owned_flower_elements * rules.OWNED_FLOWER_ELEMENT_PTS
            + self.garden * rules.GARDEN_ELEMENT_PTS
            + self.fouls_against_opponent
        )

    def ranking_points(self, won: bool, tied: bool) -> tuple[int, dict[str, int]]:
        bits = {
            "win": rules.WIN_RP if won else (rules.TIE_RP if tied else 0),
            "swarm": rules.SWARM_RP if self.park_leave_pts >= rules.SWARM_RP_THRESHOLD_PTS else 0,
            "pollinator1": rules.POLLINATOR_RP if self.tips >= rules.POLLINATOR_1_TIPS else 0,
            "pollinator2": rules.POLLINATOR_RP if self.tips >= rules.POLLINATOR_2_TIPS else 0,
        }
        return sum(bits.values()), bits


@dataclass
class MatchScore:
    red: AllianceBreakdown = field(default_factory=AllianceBreakdown)
    blue: AllianceBreakdown = field(default_factory=AllianceBreakdown)

    @property
    def winner(self) -> str:
        r, b = self.red.match_points, self.blue.match_points
        if r > b:
            return "red"
        if b > r:
            return "blue"
        return "tie"


def score_flower_stack(stack_colors: list[tuple[str, str | None]]) -> dict[str, int]:
    """stack_colors: list of (kind, color) from bottom to top.

    kind is 'pollen' or 'nectar'. pollen color is None.
    Returns points per alliance from this one flower.
    """
    pts = {"red": 0, "blue": 0}
    nectars = [(i, color) for i, (kind, color) in enumerate(stack_colors) if kind == "nectar" and color]
    if not nectars:
        return pts
    bottom_color = nectars[0][1]
    pts[bottom_color] += rules.BOTTOM_NECTAR_BONUS_PTS
    owner = nectars[-1][1]
    pts[owner] += rules.OWNED_FLOWER_ELEMENT_PTS * len(stack_colors)
    return pts
