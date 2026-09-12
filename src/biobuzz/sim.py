"""Discrete-time BIOBUZZ match simulation."""

from __future__ import annotations

import math
import random
from dataclasses import asdict, dataclass, field as datafield
from typing import Any

from . import field, rules
from .field import clamp_to_field, dist
from .scoring import AllianceBreakdown, MatchScore, score_flower_stack
from .skills import Skill, SKILLS
from .strategies import Strategy, STRATEGIES
from .rules import PhysicsAssumptions, DEFAULT_PHYSICS, pollen_equiv


ALLIANCES = ("red", "blue")


@dataclass
class Element:
    eid: int
    kind: str  # pollen | nectar
    color: str | None
    x: float
    y: float
    loc: str  # floor, robot, cell, flower, garden, loading, off_field
    loc_index: int = 0
    settle_t: float = 0.0

    @property
    def pe(self) -> float:
        return pollen_equiv(self.kind)


@dataclass
class Hive:
    alliance: str
    up_is_a: bool = True
    cell_a: list[int] = datafield(default_factory=list)
    cell_b: list[int] = datafield(default_factory=list)
    tipping: bool = False
    tip_ends: float = 0.0
    tips_auto: int = 0
    tips_tele: int = 0
    nectar_unlocked: int = 0  # G426: one nectar per tip

    @property
    def tips(self) -> int:
        return self.tips_auto + self.tips_tele

    def up_cell(self) -> list[int]:
        return self.cell_a if self.up_is_a else self.cell_b

    def set_up_cell(self, ids: list[int]) -> None:
        if self.up_is_a:
            self.cell_a = ids
        else:
            self.cell_b = ids


@dataclass
class Robot:
    idx: int
    alliance: str
    slot: int
    x: float
    y: float
    skill: Skill
    strategy: Strategy
    inventory: list[int] = datafield(default_factory=list)
    left: bool = False
    auto_parked: bool = False
    teleop_parked: bool = False
    busy_until: float = 0.0
    intent: str = "idle"
    target_x: float = 0.0
    target_y: float = 0.0
    target_eid: int | None = None
    target_flower: int | None = None
    launch_queue: int = 0
    will_leave: bool = True
    will_auto_dump: bool = True
    will_auto_park: bool = True
    auto_extra_done: float = 0.0


@dataclass
class World:
    rng: random.Random
    physics: PhysicsAssumptions
    play_t: float = 0.0
    phase: str = "auto"
    elements: list[Element] = datafield(default_factory=list)
    robots: list[Robot] = datafield(default_factory=list)
    hives: dict[str, Hive] = datafield(default_factory=dict)
    flowers: list[list[int]] = datafield(default_factory=list)
    pending_nectar: list[tuple[float, str]] = datafield(default_factory=list)
    events: list[dict[str, Any]] = datafield(default_factory=list)
    nectar_flood_done: bool = False

    def el(self, eid: int) -> Element:
        return self.elements[eid]


class MatchSim:
    def __init__(
        self,
        red_skill: str,
        blue_skill: str,
        red_strategy: str,
        blue_strategy: str,
        seed: int = 0,
        physics: PhysicsAssumptions | None = None,
        record: bool = False,
        dt: float = 0.1,
    ) -> None:
        self.physics = physics or DEFAULT_PHYSICS
        self.dt = dt
        self.record = record
        self.frames: list[dict[str, Any]] = []
        self.rng = random.Random(seed)
        self.world = self._setup(red_skill, blue_skill, red_strategy, blue_strategy)
        self.meta = {
            "red_skill": red_skill,
            "blue_skill": blue_skill,
            "red_strategy": red_strategy,
            "blue_strategy": blue_strategy,
            "seed": seed,
            "physics": asdict(self.physics),
        }

    def _note(self, text: str) -> None:
        self.world.events.append({"t": round(self.world.play_t, 2), "text": text})

    def _setup(self, red_skill: str, blue_skill: str, red_strategy: str, blue_strategy: str) -> World:
        w = World(rng=self.rng, physics=self.physics)
        w.hives = {"red": Hive("red"), "blue": Hive("blue")}
        w.flowers = [[] for _ in range(rules.FLOWERS)]
        eid = 0

        def add(kind: str, color: str | None, x: float, y: float, loc: str, loc_index: int = 0) -> int:
            nonlocal eid
            w.elements.append(Element(eid, kind, color, x, y, loc, loc_index))
            i = eid
            eid += 1
            return i

        # 4 pollen in each flower
        for fi, pose in enumerate(field.FLOWER_POSES):
            for _ in range(4):
                i = add("pollen", None, pose.x, pose.y, "flower", fi)
                w.flowers[fi].append(i)

        # 4 pollen in each garden, in a line
        for color, rect in field.GARDEN.items():
            for k in range(4):
                add("pollen", None, rect.x + 3 + k * 5.0, rect.cy, "garden", 0)

        # 3 nectar in each upward cell
        for color in ALLIANCES:
            for k in range(3):
                i = add("nectar", color, field.HIVE.cx, field.HIVE.cy, "cell", 0)
                w.hives[color].cell_a.append(i)

        # 5 nectar off-field per alliance
        for color in ALLIANCES:
            for _ in range(5):
                add("nectar", color, -10.0, -10.0, "off_field", 0)

        skills = {"red": SKILLS[red_skill], "blue": SKILLS[blue_skill]}
        strats = {"red": STRATEGIES[red_strategy], "blue": STRATEGIES[blue_strategy]}
        idx = 0
        for color in ALLIANCES:
            for slot, (sx, sy) in enumerate(field.START_POSES[color]):
                inv = []
                for k in range(4):
                    i = add("pollen", None, sx, sy, "robot", idx)
                    inv.append(i)
                sk = skills[color]
                w.robots.append(
                    Robot(
                        idx=idx,
                        alliance=color,
                        slot=slot,
                        x=sx,
                        y=sy,
                        skill=sk,
                        strategy=strats[color],
                        inventory=inv,
                        will_leave=w.rng.random() <= sk.auto_leave_p,
                        will_auto_dump=w.rng.random() <= sk.auto_preload_launch_p,
                        will_auto_park=w.rng.random() <= sk.auto_park_p,
                    )
                )
                idx += 1

        assert len(w.elements) == rules.POLLEN_COUNT + 2 * rules.NECTAR_PER_ALLIANCE
        w.events.append({"t": 0.0, "text": "MATCH start. Each ROBOT preloads 4 POLLEN. 3 NECTAR in each upward CELL."})
        return w

    # --- clock -------------------------------------------------------------
    def run(self) -> MatchScore:
        w = self.world
        steps = int(round(rules.PLAY_S / self.dt))
        teleop_released = False
        for _ in range(steps):
            if w.play_t + 1e-9 >= rules.AUTO_S:
                if w.phase == "auto" and not teleop_released:
                    # AUTO PARK is already recorded; robots must leave the zone to play TELEOP.
                    for bot in w.robots:
                        if bot.intent == "park":
                            bot.intent = "idle"
                    teleop_released = True
                w.phase = "teleop"
            self._tick()
            if self.record and (round(w.play_t / 0.2) * 0.2 - w.play_t) < self.dt * 0.51:
                self.frames.append(self.snapshot())
            w.play_t = round(w.play_t + self.dt, 4)
        # End-of-match park check (already updated live)
        score = self.final_score()
        self._note(
            f"Final: RED {score.red.match_points}  BLUE {score.blue.match_points}  ({score.winner})"
        )
        return score

    def teleop_remaining(self) -> float:
        if self.world.phase == "auto":
            return rules.TELEOP_S
        return max(0.0, rules.PLAY_S - self.world.play_t)

    def flowers_unlocked(self) -> bool:
        return self.world.phase == "teleop" and self.teleop_remaining() <= rules.FLOWER_UNLOCK_TELEOP_S

    # --- tick --------------------------------------------------------------
    def _tick(self) -> None:
        w = self.world
        self._advance_hives()
        self._introduce_nectar()
        self._settle_elements()
        for bot in w.robots:
            if w.play_t < bot.busy_until:
                continue
            self._choose(bot)
            self._act(bot)
        self._separate_robots()
        self._update_park_leave()

    def _settle_elements(self) -> None:
        for el in self.world.elements:
            if el.settle_t > 0:
                el.settle_t = max(0.0, el.settle_t - self.dt)

    def _advance_hives(self) -> None:
        w = self.world
        for hive in w.hives.values():
            if hive.tipping and w.play_t >= hive.tip_ends:
                self._finish_tip(hive)
            elif not hive.tipping:
                mass = sum(
                    pollen_equiv(w.el(i).kind, self.physics.nectar_mass_ratio)
                    for i in hive.up_cell()
                )
                if mass + 1e-9 >= self.physics.empty_cell_tip_pe:
                    hive.tipping = True
                    hive.tip_ends = w.play_t + self.physics.hive_tip_duration_s

    def _finish_tip(self, hive: Hive) -> None:
        w = self.world
        contents = list(hive.up_cell())
        hive.set_up_cell([])
        hive.up_is_a = not hive.up_is_a
        hive.tipping = False
        if w.phase == "auto":
            hive.tips_auto += 1
        else:
            hive.tips_tele += 1
        # Dump onto the floor around the hive (G409 settle).
        for i, eid in enumerate(contents):
            el = w.el(eid)
            ang = w.rng.random() * math.tau
            rad = 22 + w.rng.random() * 20
            el.x, el.y = clamp_to_field(
                field.HIVE.cx + math.cos(ang) * rad,
                field.HIVE.cy + math.sin(ang) * rad,
                3,
            )
            el.loc = "floor"
            el.settle_t = self.physics.dump_settle_s + 0.05 * i
        self._note(f"{hive.alliance.upper()} HIVE TIP #{hive.tips} ({len(contents)} elements dump).")
        # G426: one nectar may be entered per tip, from the 5 staged off-field.
        if hive.nectar_unlocked < 5:
            hive.nectar_unlocked += 1
            w.pending_nectar.append((w.play_t + self.physics.nectar_intro_delay_s, hive.alliance))

    def _introduce_nectar(self) -> None:
        w = self.world
        # Last 60s: remaining off-field nectar may all enter.
        if (
            not w.nectar_flood_done
            and w.phase == "teleop"
            and self.teleop_remaining() <= rules.NECTAR_ALL_REMAINING_TELEOP_S
        ):
            w.nectar_flood_done = True
            for color in ALLIANCES:
                waiting = [e for e in w.elements if e.kind == "nectar" and e.color == color and e.loc == "off_field"]
                for e in waiting:
                    w.pending_nectar.append((w.play_t + 0.4 * w.rng.random(), color))
            if any(e.loc == "off_field" for e in w.elements):
                self._note("Last 60s: remaining NECTAR may enter via LOADING ZONES.")

        still: list[tuple[float, str]] = []
        for t, color in w.pending_nectar:
            if w.play_t + 1e-9 < t:
                still.append((t, color))
                continue
            el = next((e for e in w.elements if e.kind == "nectar" and e.color == color and e.loc == "off_field"), None)
            if el is None:
                continue
            lz = field.LOADING[color]
            el.loc = "loading"
            el.x = lz.cx + (w.rng.random() - 0.5) * 10
            el.y = lz.cy + (w.rng.random() - 0.5) * 4
            el.settle_t = 0.2
        w.pending_nectar = still

    def _update_park_leave(self) -> None:
        w = self.world
        for bot in w.robots:
            if w.phase == "auto" and not bot.left:
                wall_x = 0.0 if bot.alliance == "red" else rules.FIELD_IN
                if abs(bot.x - wall_x) > 12.0:
                    bot.left = True
            lz = field.LOADING[bot.alliance]
            in_lz = lz.contains(bot.x, bot.y, radius=8)
            if w.phase == "auto":
                bot.auto_parked = in_lz
            else:
                bot.teleop_parked = in_lz

    def _separate_robots(self) -> None:
        bots = self.world.robots
        for i in range(len(bots)):
            for j in range(i + 1, len(bots)):
                a, b = bots[i], bots[j]
                d = dist(a.x, a.y, b.x, b.y)
                min_d = 16.0
                if d < 1e-3:
                    a.x += 0.5
                    continue
                if d < min_d:
                    push = (min_d - d) * 0.5
                    ux, uy = (a.x - b.x) / d, (a.y - b.y) / d
                    a.x, a.y = clamp_to_field(a.x + ux * push, a.y + uy * push)
                    b.x, b.y = clamp_to_field(b.x - ux * push, b.y - uy * push)

    # --- AI ----------------------------------------------------------------
    def _choose(self, bot: Robot) -> None:
        w = self.world
        # Do not interrupt travel or a multi-cycle action (launch magazine, etc.).
        if bot.intent != "idle":
            return

        if w.phase == "auto":
            self._choose_auto(bot)
        else:
            self._choose_teleop(bot)

    def _choose_auto(self, bot: Robot) -> None:
        sk, st = bot.skill, bot.strategy
        remaining = rules.AUTO_S - self.world.play_t
        if not bot.left:
            if not bot.will_leave:
                bot.intent = "idle"
                return
            self._set_goto(bot, *self._leave_waypoint(bot))
            bot.intent = "leave"
            return

        want_dump = st.auto != "leave_only" and bot.will_auto_dump
        can_work = remaining > 6.5

        if want_dump and bot.inventory and can_work:
            self._begin_launch(bot)
            return

        extra = st.auto == "dump_cycle" and remaining > 10.0
        if extra and bot.auto_extra_done < sk.auto_extra_cycles:
            tgt = self._nearest_collect(bot)
            if tgt is not None and len(bot.inventory) < rules.POSSESSION_LIMIT:
                bot.auto_extra_done += 1
                self._begin_intake(bot, tgt)
                return

        if remaining <= 7.5 or st.auto == "leave_only" or (st.auto == "dump_park" and not bot.inventory):
            if remaining <= 4.0 or bot.will_auto_park:
                self._begin_park(bot, auto=True)
                return

        if bot.inventory and can_work:
            self._begin_launch(bot)
            return
        bot.intent = "idle"

    def _choose_teleop(self, bot: Robot) -> None:
        sk, st = bot.skill, bot.strategy
        remain = self.teleop_remaining()
        park_s = st.park_override_s or sk.park_commit_s
        hive = self.world.hives[bot.alliance]

        if remain <= park_s:
            self._begin_park(bot, auto=False)
            return

        mode = st.post_flower if self.flowers_unlocked() else st.pre_flower
        if st.tip_goal and hive.tips >= st.tip_goal and self.flowers_unlocked():
            mode = "flower"
        elif st.tip_goal and hive.tips >= st.tip_goal and not self.flowers_unlocked():
            mode = "extract" if st.name == "flower_focus" else "hive"

        if mode in ("hive", "nectar_hive"):
            self._choose_hive(bot, prefer_nectar=(mode == "nectar_hive" or st.prefer_nectar))
        elif mode == "flower":
            self._choose_flower(bot)
        elif mode == "split":
            # Slot 0 keeps tipping if under P2; slot 1 goes flowers.
            if bot.slot == 0 and hive.tips < rules.POLLINATOR_2_TIPS:
                self._choose_hive(bot, prefer_nectar=True)
            else:
                self._choose_flower(bot)
        elif mode == "extract":
            if self._try_extract(bot):
                return
            self._choose_hive(bot, prefer_nectar=False)
        else:
            self._choose_hive(bot, prefer_nectar=False)

    def _choose_hive(self, bot: Robot, prefer_nectar: bool) -> None:
        if bot.inventory:
            # Launch if full, or if we have nectar and prefer it, or nothing left nearby.
            if (
                len(bot.inventory) >= rules.POSSESSION_LIMIT
                or (prefer_nectar and self._inv_has(bot, "nectar"))
                or self._nearest_collect(bot, nectar_only=prefer_nectar) is None
            ):
                self._begin_launch(bot)
                return
        tgt = self._nearest_collect(bot, nectar_only=prefer_nectar)
        if tgt is None and prefer_nectar:
            tgt = self._nearest_collect(bot, nectar_only=False)
        if tgt is not None and len(bot.inventory) < rules.POSSESSION_LIMIT:
            self._begin_intake(bot, tgt)
            return
        if bot.inventory:
            self._begin_launch(bot)
        else:
            bot.intent = "idle"

    def _choose_flower(self, bot: Robot) -> None:
        if not self.flowers_unlocked():
            if self._try_extract(bot):
                return
            self._choose_hive(bot, prefer_nectar=False)
            return
        # Plan: claim a flower without our nectar (bottom), then fill, then top nectar.
        plan = self._flower_plan(bot)
        if plan is None:
            self._choose_hive(bot, prefer_nectar=True)
            return
        action, fi = plan
        if action == "extract":
            self._begin_extract(bot, fi)
            return
        need_kind = "nectar" if action in ("bottom_nectar", "top_nectar") else "pollen"
        if not self._inv_has(bot, need_kind):
            tgt = self._nearest_collect(bot, nectar_only=(need_kind == "nectar"), force_kind=need_kind)
            if tgt is not None and len(bot.inventory) < rules.POSSESSION_LIMIT:
                self._begin_intake(bot, tgt)
                return
            if self._inv_has(bot, "nectar") and self.flowers_unlocked():
                self._begin_place(bot, fi, "nectar")
                return
            if bot.inventory and need_kind == "nectar":
                # Make room: pollen can go into the hive.
                self._begin_launch(bot)
                return
            bot.intent = "idle"
            return
        self._begin_place(bot, fi, need_kind)

    def _flower_plan(self, bot: Robot) -> tuple[str, int] | None:
        """Return (action, flower_index) or None."""
        color = bot.alliance
        best: tuple[int, str, int] | None = None  # priority, action, fi
        for fi, stack in enumerate(self.world.flowers):
            kinds = [self.world.el(i).kind for i in stack]
            colors = [self.world.el(i).color for i in stack]
            nectars = [c for k, c in zip(kinds, colors) if k == "nectar"]
            height = self._flower_height(fi)
            room = self.physics.flower_scoring_height_in - height
            our_top = bool(nectars) and nectars[-1] == color
            our_bottom = bool(nectars) and nectars[0] == color
            opp_top = bool(nectars) and nectars[-1] != color
            if not nectars and room >= rules.NECTAR_DIAMETER_IN:
                cand = (0, "bottom_nectar", fi)
            elif nectars and not our_bottom and kinds and kinds[0] == "pollen":
                cand = (1, "extract", fi)  # make room / clear for our nectar later
            elif our_top and room >= rules.POLLEN_DIAMETER_IN:
                cand = (2, "fill_pollen", fi)
            elif our_bottom and not our_top and room >= rules.NECTAR_DIAMETER_IN:
                cand = (3, "top_nectar", fi)
            elif not our_top and room >= rules.NECTAR_DIAMETER_IN:
                cand = (4, "top_nectar", fi)  # steal ownership
            elif kinds and kinds[0] == "pollen" and len(bot.inventory) < rules.POSSESSION_LIMIT:
                cand = (5, "extract", fi)
            else:
                continue
            if best is None or cand[0] < best[0]:
                best = cand
        if best is None:
            return None
        return best[1], best[2]

    def _try_extract(self, bot: Robot) -> bool:
        if len(bot.inventory) >= rules.POSSESSION_LIMIT:
            return False
        for fi, stack in enumerate(self.world.flowers):
            if stack and self.world.el(stack[0]).kind == "pollen":
                self._begin_extract(bot, fi)
                return True
        return False

    # --- begin actions -----------------------------------------------------
    def _leave_waypoint(self, bot: Robot) -> tuple[float, float]:
        if bot.alliance == "red":
            return 36.0, bot.y
        return rules.FIELD_IN - 36.0, bot.y

    def _park_point(self, bot: Robot) -> tuple[float, float]:
        lz = field.LOADING[bot.alliance]
        # Zone is only 11 in deep; PARK only needs partial overlap. Stagger so two
        # 18 in robots are not fighting over the same point.
        x = lz.cx + (-8 if bot.slot == 0 else 8)
        y = lz.h + 3.0  # center just outside, still overlaps with park radius
        return x, y

    def _launch_point(self, bot: Robot) -> tuple[float, float]:
        # Stand off the hive frame toward own wall, slightly staggered.
        sign = -1 if bot.alliance == "red" else 1
        return (
            field.HIVE.cx + sign * (field.HIVE_W * 0.5 + 22),
            field.HIVE.cy + (-14 if bot.slot == 0 else 14),
        )

    def _set_goto(self, bot: Robot, x: float, y: float) -> None:
        bot.target_x, bot.target_y = x, y
        bot.intent = "goto"

    def _travel_time(self, bot: Robot, x: float, y: float) -> float:
        d = dist(bot.x, bot.y, x, y)
        return d / max(8.0, bot.skill.speed_in_s) + bot.skill.turn_penalty_s

    def _begin_park(self, bot: Robot, auto: bool) -> None:
        x, y = self._park_point(bot)
        bot.intent = "park"
        bot.target_x, bot.target_y = x, y
        bot.busy_until = self.world.play_t  # movement handled in _act

    def _begin_intake(self, bot: Robot, el: Element) -> None:
        bot.intent = "intake"
        bot.target_eid = el.eid
        bot.target_x, bot.target_y = el.x, el.y

    def _begin_launch(self, bot: Robot) -> None:
        x, y = self._launch_point(bot)
        bot.intent = "launch"
        bot.target_x, bot.target_y = x, y
        bot.launch_queue = len(bot.inventory)

    def _begin_place(self, bot: Robot, fi: int, kind: str) -> None:
        pose = field.FLOWER_POSES[fi]
        bot.intent = "place"
        bot.target_flower = fi
        bot.target_eid = next(
            (eid for eid in bot.inventory if self.world.el(eid).kind == kind
             and (kind == "pollen" or self.world.el(eid).color == bot.alliance)),
            None,
        )
        bot.target_x, bot.target_y = self._approach_flower(bot, pose)

    def _begin_extract(self, bot: Robot, fi: int) -> None:
        pose = field.FLOWER_POSES[fi]
        bot.intent = "extract"
        bot.target_flower = fi
        bot.target_x, bot.target_y = self._approach_flower(bot, pose)

    def _approach_flower(self, bot: Robot, pose: field.FlowerPose) -> tuple[float, float]:
        if pose.wall == "audience":
            return pose.x + (bot.slot - 0.5) * 10, 16.0
        if pose.wall == "rear":
            return pose.x + (bot.slot - 0.5) * 10, rules.FIELD_IN - 16.0
        if pose.wall == "red":
            return 16.0, pose.y + (bot.slot - 0.5) * 10
        return rules.FIELD_IN - 16.0, pose.y + (bot.slot - 0.5) * 10

    # --- act ---------------------------------------------------------------
    def _act(self, bot: Robot) -> None:
        w = self.world
        if bot.intent in ("idle",):
            return
        # Update moving target for intakes
        if bot.intent == "intake" and bot.target_eid is not None:
            el = w.el(bot.target_eid)
            if el.loc not in ("floor", "garden", "loading") or el.settle_t > 0:
                bot.intent = "idle"
                bot.target_eid = None
                return
            bot.target_x, bot.target_y = el.x, el.y

        arrived = dist(bot.x, bot.y, bot.target_x, bot.target_y) <= 8.0
        if not arrived:
            self._drive(bot, bot.target_x, bot.target_y)
            return

        if bot.intent == "leave":
            bot.intent = "idle"
            return
        if bot.intent == "park":
            # Stay put
            return
        if bot.intent == "intake":
            self._do_intake(bot)
            return
        if bot.intent == "launch":
            self._do_launch(bot)
            return
        if bot.intent == "place":
            self._do_place(bot)
            return
        if bot.intent == "extract":
            self._do_extract(bot)
            return

    def _drive(self, bot: Robot, tx: float, ty: float) -> None:
        step = bot.skill.speed_in_s * self.dt
        d = dist(bot.x, bot.y, tx, ty)
        if d <= step or d < 1e-6:
            bot.x, bot.y = tx, ty
            return
        ux, uy = (tx - bot.x) / d, (ty - bot.y) / d
        # Slight avoidance of hive interior
        nx, ny = bot.x + ux * step, bot.y + uy * step
        if field.HIVE.contains(nx, ny, radius=-6):
            nx += -uy * step
            ny += ux * step
        bot.x, bot.y = clamp_to_field(nx, ny)

    def _do_intake(self, bot: Robot) -> None:
        w = self.world
        if bot.target_eid is None or len(bot.inventory) >= rules.POSSESSION_LIMIT:
            bot.intent = "idle"
            return
        el = w.el(bot.target_eid)
        if el.kind == "nectar" and el.color != bot.alliance:
            bot.intent = "idle"
            return
        if el.loc not in ("floor", "garden", "loading") or el.settle_t > 0:
            bot.intent = "idle"
            return
        if dist(bot.x, bot.y, el.x, el.y) > self.physics.intake_range_in + 4:
            return
        bot.busy_until = w.play_t + bot.skill.intake_s
        if w.rng.random() > bot.skill.intake_reliability:
            bot.intent = "idle"
            bot.target_eid = None
            return
        el.loc = "robot"
        el.loc_index = bot.idx
        bot.inventory.append(el.eid)
        bot.intent = "idle"
        bot.target_eid = None

    def _do_launch(self, bot: Robot) -> None:
        w = self.world
        if not bot.inventory:
            bot.intent = "idle"
            return
        eid = bot.inventory.pop(0)
        el = w.el(eid)
        bot.busy_until = w.play_t + bot.skill.launch_s
        hive = w.hives[bot.alliance]
        if hive.tipping:
            # Don't shoot the downward cell; wait.
            bot.inventory.insert(0, eid)
            bot.busy_until = hive.tip_ends
            return
        hit = w.rng.random() <= bot.skill.hive_accuracy
        if hit:
            el.loc = "cell"
            el.x, el.y = field.HIVE.cx, field.HIVE.cy
            hive.up_cell().append(eid)
        else:
            ang = w.rng.random() * math.tau
            el.loc = "floor"
            el.x, el.y = clamp_to_field(
                field.HIVE.cx + math.cos(ang) * 20,
                field.HIVE.cy + math.sin(ang) * 16,
                3,
            )
        if not bot.inventory:
            bot.intent = "idle"

    def _do_place(self, bot: Robot) -> None:
        w = self.world
        fi = bot.target_flower
        eid = bot.target_eid
        if fi is None or eid is None or eid not in bot.inventory:
            bot.intent = "idle"
            return
        el = w.el(eid)
        if el.kind == "nectar" and not self.flowers_unlocked():
            bot.intent = "idle"
            return
        if not self.flowers_unlocked():
            bot.intent = "idle"
            return
        acc = (
            bot.skill.flower_nectar_accuracy
            if el.kind == "nectar"
            else bot.skill.flower_pollen_accuracy
        )
        bot.busy_until = w.play_t + bot.skill.flower_place_s
        bot.inventory.remove(eid)
        bot.intent = "idle"
        pose = field.FLOWER_POSES[fi]
        if w.rng.random() > acc:
            el.loc = "floor"
            el.x = pose.x + (w.rng.random() - 0.5) * 16
            el.y = pose.y + (w.rng.random() - 0.5) * 16
            el.x, el.y = clamp_to_field(el.x, el.y, 3)
            return
        need = rules.NECTAR_DIAMETER_IN if el.kind == "nectar" else rules.POLLEN_DIAMETER_IN
        if self._flower_height(fi) + need > self.physics.flower_scoring_height_in + 0.2:
            el.loc = "floor"
            el.x, el.y = clamp_to_field(pose.x + 8, pose.y + 8, 3)
            return
        el.loc = "flower"
        el.loc_index = fi
        el.x, el.y = pose.x, pose.y
        w.flowers[fi].append(eid)

    def _do_extract(self, bot: Robot) -> None:
        w = self.world
        fi = bot.target_flower
        bot.intent = "idle"
        if fi is None or len(bot.inventory) >= rules.POSSESSION_LIMIT:
            return
        stack = w.flowers[fi]
        if not stack:
            return
        bottom = w.el(stack[0])
        if bottom.kind != "pollen":
            return
        bot.busy_until = w.play_t + bot.skill.flower_extract_s
        stack.pop(0)
        bottom.loc = "robot"
        bottom.loc_index = bot.idx
        bot.inventory.append(bottom.eid)

    # --- queries -----------------------------------------------------------
    def _inv_has(self, bot: Robot, kind: str) -> bool:
        return any(
            self.world.el(i).kind == kind
            and (kind == "pollen" or self.world.el(i).color == bot.alliance)
            for i in bot.inventory
        )

    def _flower_height(self, fi: int) -> float:
        h = 0.0
        for eid in self.world.flowers[fi]:
            el = self.world.el(eid)
            h += rules.NECTAR_DIAMETER_IN if el.kind == "nectar" else rules.POLLEN_DIAMETER_IN
        return h

    def _nearest_collect(
        self,
        bot: Robot,
        nectar_only: bool = False,
        force_kind: str | None = None,
    ) -> Element | None:
        best: Element | None = None
        best_d = 1e9
        kind = force_kind or ("nectar" if nectar_only else None)
        for el in self.world.elements:
            if el.loc not in ("floor", "garden", "loading"):
                continue
            if el.settle_t > 0:
                continue
            if el.kind == "nectar" and el.color != bot.alliance:
                continue
            if kind and el.kind != kind:
                continue
            if nectar_only and el.kind != "nectar":
                continue
            d = dist(bot.x, bot.y, el.x, el.y)
            # Slight preference for loading-zone nectar (human intro).
            if el.loc == "loading":
                d *= 0.85
            if d < best_d:
                best, best_d = el, d
        return best

    # --- scoring / snapshot ------------------------------------------------
    def live_breakdown(self, color: str) -> AllianceBreakdown:
        w = self.world
        hive = w.hives[color]
        bd = AllianceBreakdown(
            leave=sum(1 for b in w.robots if b.alliance == color and b.left),
            auto_park=sum(1 for b in w.robots if b.alliance == color and b.auto_parked),
            teleop_park=sum(1 for b in w.robots if b.alliance == color and b.teleop_parked),
            auto_tips=hive.tips_auto,
            teleop_tips=hive.tips_tele,
            cell_remaining=len(hive.up_cell()) if not hive.tipping else 0,
        )
        for stack_ids in w.flowers:
            stack = [(w.el(i).kind, w.el(i).color) for i in stack_ids]
            pts = score_flower_stack(stack)
            # Reconstruct bottom vs owned from the helper by re-walking
            nectars = [c for k, c in stack if k == "nectar" and c]
            if nectars:
                if nectars[0] == color:
                    bd.bottom_nectar += 1
                if nectars[-1] == color:
                    bd.owned_flower_elements += len(stack)
        for el in w.elements:
            if el.loc in ("floor", "garden", "loading"):
                for gcolor, rect in field.GARDEN.items():
                    if gcolor == color and rect.contains(el.x, el.y, radius=2.5):
                        bd.garden += 1
        return bd

    def final_score(self) -> MatchScore:
        # Freeze park at end: already set. Cell remaining as-is.
        return MatchScore(red=self.live_breakdown("red"), blue=self.live_breakdown("blue"))

    def snapshot(self) -> dict[str, Any]:
        w = self.world
        return {
            "t": round(w.play_t, 2),
            "phase": w.phase,
            "robots": [
                {
                    "idx": b.idx,
                    "alliance": b.alliance,
                    "x": round(b.x, 1),
                    "y": round(b.y, 1),
                    "n": len(b.inventory),
                    "intent": b.intent,
                }
                for b in w.robots
            ],
            "elements": [
                {
                    "id": e.eid,
                    "k": 0 if e.kind == "pollen" else 1,
                    "c": 0 if e.color is None else (1 if e.color == "red" else 2),
                    "x": round(e.x, 1),
                    "y": round(e.y, 1),
                    "loc": e.loc,
                }
                for e in w.elements
                if e.loc not in ("off_field",)
            ],
            "hives": {
                color: {
                    "tips": h.tips,
                    "up": "a" if h.up_is_a else "b",
                    "tipping": h.tipping,
                    "mass": round(
                        sum(pollen_equiv(w.el(i).kind, self.physics.nectar_mass_ratio) for i in h.up_cell()),
                        2,
                    ),
                    "n": len(h.up_cell()),
                }
                for color, h in w.hives.items()
            },
            "flowers": [
                [
                    (0 if w.el(i).kind == "pollen" else 1, 1 if w.el(i).color == "red" else (2 if w.el(i).color == "blue" else 0))
                    for i in stack
                ]
                for stack in w.flowers
            ],
            "score": {
                "red": self.live_breakdown("red").match_points,
                "blue": self.live_breakdown("blue").match_points,
            },
        }

    def replay_payload(self, score: MatchScore) -> dict[str, Any]:
        return {
            "meta": self.meta,
            "events": self.world.events,
            "frames": self.frames,
            "result": {
                "winner": score.winner,
                "red": {
                    "points": score.red.match_points,
                    "tips": score.red.tips,
                    "rp": score.red.ranking_points(score.winner == "red", score.winner == "tie")[0],
                    "breakdown": asdict(score.red),
                },
                "blue": {
                    "points": score.blue.match_points,
                    "tips": score.blue.tips,
                    "rp": score.blue.ranking_points(score.winner == "blue", score.winner == "tie")[0],
                    "breakdown": asdict(score.blue),
                },
            },
        }
