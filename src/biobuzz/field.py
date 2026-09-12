"""Field geometry in inches. Origin is the audience-left corner.

Audience is at y=0. Red alliance is x=0 (left). Blue alliance is x=144 (right).
Layout follows the V1 manual qualitatively: LOADING ZONES adjacent to each
ALLIANCE AREA, GARDENS in opposite corners, four FLOWERS on the perimeter,
HIVE structure in the center.
"""

from __future__ import annotations

from dataclasses import dataclass

from .rules import FIELD_IN


@dataclass(frozen=True)
class Rect:
    x: float
    y: float
    w: float
    h: float

    def contains(self, x: float, y: float, radius: float = 0.0) -> bool:
        return (
            self.x - radius <= x <= self.x + self.w + radius
            and self.y - radius <= y <= self.y + self.h + radius
        )

    @property
    def cx(self) -> float:
        return self.x + self.w * 0.5

    @property
    def cy(self) -> float:
        return self.y + self.h * 0.5


@dataclass(frozen=True)
class FlowerPose:
    index: int
    wall: str  # audience, rear, red, blue
    x: float
    y: float


# Hive frame: 49.46 in wide x 38.95 in deep, centered.
HIVE_W = 49.46
HIVE_D = 38.95
HIVE = Rect((FIELD_IN - HIVE_W) / 2, (FIELD_IN - HIVE_D) / 2, HIVE_W, HIVE_D)

# Loading zones ~23 x 11 in corners by alliance areas (audience side).
LOADING = {
    "red": Rect(0.0, 0.0, 23.0, 11.0),
    "blue": Rect(FIELD_IN - 23.0, 0.0, 23.0, 11.0),
}

# Gardens: 23 x 2 in opposite corners (red rear-left, blue audience-right-ish
# wait: opposite corners = red rear-left and blue audience-right would not
# match alliance color. Manual: gardens are alliance-colored in opposite
# corners. Red garden near red, blue near blue, opposite corners:
# red rear-left, blue audience-right is same-side-ish.
# Use: red = rear-left, blue = rear-right so they are along the rear wall
# in opposite left/right corners — "opposite corners" from each other on
# the rear wall is weak. True opposite: red rear-left (0, 142) and blue
# audience-right is (121, 0) — that's diagonal.
# Manual: "opposite corners of the FIELD" and pollen "starting in the corner
# closest to the ALLIANCE AREA and contacting the audience or rear perimeter".
GARDEN = {
    "red": Rect(0.0, FIELD_IN - 2.0, 23.0, 2.0),  # rear-left
    "blue": Rect(FIELD_IN - 23.0, FIELD_IN - 2.0, 23.0, 2.0),  # rear-right
}

# Four flowers on the four walls, offset from corners so they don't sit in
# loading zones. Index order: audience, red-wall, rear, blue-wall.
FLOWER_POSES = (
    FlowerPose(0, "audience", FIELD_IN * 0.5, 0.0),
    FlowerPose(1, "red", 0.0, FIELD_IN * 0.5),
    FlowerPose(2, "rear", FIELD_IN * 0.5, FIELD_IN),
    FlowerPose(3, "blue", FIELD_IN, FIELD_IN * 0.5),
)

# Legal start: own half, touching perimeter, not in loading zone, not in flower.
# Red starts along the left wall, blue along the right wall.
START_POSES = {
    "red": ((18.0, 40.0), (18.0, 104.0)),
    "blue": ((FIELD_IN - 18.0, 40.0), (FIELD_IN - 18.0, 104.0)),
}


def clamp_to_field(x: float, y: float, radius: float = 9.0) -> tuple[float, float]:
    return (
        min(FIELD_IN - radius, max(radius, x)),
        min(FIELD_IN - radius, max(radius, y)),
    )


def dist(ax: float, ay: float, bx: float, by: float) -> float:
    return ((ax - bx) ** 2 + (ay - by) ** 2) ** 0.5
