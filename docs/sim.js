/* BIOBUZZ match engine (browser). Scoring follows Competition Manual V1. */
(function (global) {
  "use strict";

  const R = {
    AUTO_S: 30,
    TELEOP_S: 120,
    PLAY_S: 150,
    FLOWER_UNLOCK: 60,
    FIELD: 144,
    POSSESSION: 4,
    POLLEN_D: 2.8,
    NECTAR_D: 3.6,
    NECTAR_PE: Math.pow(3.6 / 2.8, 3),
    FLOWER_H: 17,
    LEAVE: 3,
    PARK: 5,
    TIP: 20,
    CELL: 2,
    BOTTOM: 5,
    OWNED: 2,
    GARDEN: 1,
    SWARM: 16,
    P1: 4,
    P2: 7,
    TIP_MASS: 8,
    TIP_DUR: 1.2,
    SETTLE: 0.6,
    INTAKE_RANGE: 12,
  };

  const HIVE = { x: (144 - 49.46) / 2, y: (144 - 38.95) / 2, w: 49.46, d: 38.95 };
  HIVE.cx = HIVE.x + HIVE.w / 2;
  HIVE.cy = HIVE.y + HIVE.d / 2;

  const LOADING = {
    red: { x: 0, y: 0, w: 23, h: 11 },
    blue: { x: 144 - 23, y: 0, w: 23, h: 11 },
  };
  const GARDEN = {
    red: { x: 0, y: 142, w: 23, h: 2 },
    blue: { x: 121, y: 142, w: 23, h: 2 },
  };
  const FLOWERS = [
    { i: 0, wall: "audience", x: 72, y: 0 },
    { i: 1, wall: "red", x: 0, y: 72 },
    { i: 2, wall: "rear", x: 72, y: 144 },
    { i: 3, wall: "blue", x: 144, y: 72 },
  ];
  const START = {
    red: [ [18, 40], [18, 104] ],
    blue: [ [126, 40], [126, 104] ],
  };

  const STRATEGIES = {
    hive_cycle: { name: "hive_cycle", title: "Hive cycling", blurb: "Launch into the CELL all match. Ignore flowers.", pre: "hive", post: "hive", auto: "dump_cycle", tipGoal: 0, park: 0, preferNectar: false },
    hive_then_flower: { name: "hive_then_flower", title: "Hive, then flowers", blurb: "Cycle the HIVE until the last 60s, then contest FLOWERS.", pre: "hive", post: "flower", auto: "dump_cycle", tipGoal: 0, park: 0, preferNectar: false },
    nectar_tips: { name: "nectar_tips", title: "Nectar-powered tips", blurb: "Hunt NECTAR because it tips the HIVE with fewer cycles.", pre: "nectar_hive", post: "nectar_hive", auto: "dump_cycle", tipGoal: 0, park: 0, preferNectar: true },
    flower_focus: { name: "flower_focus", title: "Flower focus", blurb: "Dump AUTO preload, then stuff FLOWERS in the last minute.", pre: "extract", post: "flower", auto: "dump_park", tipGoal: 1, park: 0, preferNectar: false },
    rp_hunter: { name: "rp_hunter", title: "Ranking-point hunter", blurb: "LEAVE + PARK for SWARM, 4 TIPS for POLLINATOR 1, then flowers.", pre: "hive", post: "split", auto: "dump_park", tipGoal: 4, park: 0, preferNectar: false },
    park_and_dump: { name: "park_and_dump", title: "Park and dump", blurb: "LEAVE, dump what is easy, PARK. A first-meet plan.", pre: "hive", post: "hive", auto: "leave_only", tipGoal: 2, park: 18, preferNectar: false },
  };

  const BASE = {
    name: "developing",
    speed: 52,
    turn: 0.45,
    intake: 1.8,
    launch: 1.3,
    flowerPlace: 2.4,
    flowerExtract: 1.6,
    hiveAcc: 0.72,
    flowerPollen: 0.58,
    flowerNectar: 0.38,
    intakeRel: 0.88,
    autoLeave: 0.97,
    autoDump: 0.80,
    autoPark: 0.75,
    autoExtra: 0.4,
    parkCommit: 8,
  };

  function applyCaps(opts) {
    opts = opts || {};
    const intake = opts.intake_s != null ? opts.intake_s : BASE.intake;
    const scale = intake / BASE.intake;
    const fp = opts.flower_accuracy != null ? opts.flower_accuracy : BASE.flowerPollen;
    return {
      name: "custom",
      speed: BASE.speed,
      turn: BASE.turn,
      intake: intake,
      launch: opts.launch_s != null ? opts.launch_s : BASE.launch * scale,
      flowerPlace: BASE.flowerPlace * scale,
      flowerExtract: BASE.flowerExtract * scale,
      hiveAcc: opts.hive_accuracy != null ? opts.hive_accuracy : BASE.hiveAcc,
      flowerPollen: fp,
      flowerNectar: Math.max(0.05, Math.min(0.95, fp * 0.62 + 0.04)),
      intakeRel: opts.intake_reliability != null ? opts.intake_reliability : BASE.intakeRel,
      autoLeave: 0.97,
      autoDump: 0.85,
      autoPark: 0.8,
      autoExtra: 0.4,
      parkCommit: 8,
    };
  }

  function mulberry(seed) {
    let s = seed >>> 0;
    return function () {
      s |= 0;
      s = (s + 0x6d2b79f5) | 0;
      let t = Math.imul(s ^ (s >>> 15), 1 | s);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  function dist(ax, ay, bx, by) {
    const dx = ax - bx, dy = ay - by;
    return Math.sqrt(dx * dx + dy * dy);
  }
  function clamp(x, y, r) {
    r = r == null ? 9 : r;
    return [Math.min(144 - r, Math.max(r, x)), Math.min(144 - r, Math.max(r, y))];
  }
  function contains(rect, x, y, rad) {
    rad = rad || 0;
    return x >= rect.x - rad && x <= rect.x + rect.w + rad && y >= rect.y - rad && y <= rect.y + rect.h + rad;
  }
  function pe(kind) { return kind === "nectar" ? R.NECTAR_PE : 1; }
  function cx(rect) { return rect.x + rect.w / 2; }
  function cy(rect) { return rect.y + rect.h / 2; }

  function scoreFlower(stack) {
    const nectars = [];
    for (let i = 0; i < stack.length; i++) if (stack[i].kind === "nectar" && stack[i].color) nectars.push(stack[i].color);
    const pts = { red: 0, blue: 0 };
    if (!nectars.length) return pts;
    pts[nectars[0]] += R.BOTTOM;
    pts[nectars[nectars.length - 1]] += R.OWNED * stack.length;
    return pts;
  }

  function breakdownPoints(b) {
    return b.leave * R.LEAVE + b.autoPark * R.PARK + b.teleopPark * R.PARK
      + b.autoTips * R.TIP + b.teleopTips * R.TIP + b.cell * R.CELL
      + b.bottom * R.BOTTOM + b.owned * R.OWNED + b.garden * R.GARDEN;
  }
  function emptyBd() {
    return { leave: 0, autoPark: 0, teleopPark: 0, autoTips: 0, teleopTips: 0, cell: 0, bottom: 0, owned: 0, garden: 0 };
  }
  function rpBits(b, won, tied) {
    const parkLeave = b.leave * R.LEAVE + b.autoPark * R.PARK + b.teleopPark * R.PARK;
    const tips = b.autoTips + b.teleopTips;
    return {
      win: won ? 3 : (tied ? 1 : 0),
      swarm: parkLeave >= R.SWARM ? 1 : 0,
      p1: tips >= R.P1 ? 1 : 0,
      p2: tips >= R.P2 ? 1 : 0,
    };
  }

  function MatchSim(redSkill, blueSkill, redStrat, blueStrat, seed, record) {
    this.dt = 0.1;
    this.record = !!record;
    this.frames = [];
    this.events = [];
    this.rng = mulberry(seed || 1);
    this.skills = { red: redSkill, blue: blueSkill };
    this.strats = { red: STRATEGIES[redStrat], blue: STRATEGIES[blueStrat] };
    this.meta = { redStrategy: redStrat, blueStrategy: blueStrat, seed: seed || 1, redCaps: redSkill, blueCaps: blueSkill };
    this._setup();
  }

  MatchSim.prototype._note = function (text) {
    this.events.push({ t: Math.round(this.playT * 100) / 100, text: text });
  };

  MatchSim.prototype._setup = function () {
    const rng = this.rng;
    this.playT = 0;
    this.phase = "auto";
    this.elements = [];
    this.robots = [];
    this.hives = {
      red: { alliance: "red", upA: true, a: [], b: [], tipping: false, tipEnds: 0, autoTips: 0, teleTips: 0, unlocked: 0 },
      blue: { alliance: "blue", upA: true, a: [], b: [], tipping: false, tipEnds: 0, autoTips: 0, teleTips: 0, unlocked: 0 },
    };
    this.flowers = [[], [], [], []];
    this.pending = [];
    this.nectarFlood = false;
    let eid = 0;
    const add = (kind, color, x, y, loc, locI) => {
      const e = { eid: eid++, kind: kind, color: color, x: x, y: y, loc: loc, locI: locI || 0, settle: 0 };
      this.elements.push(e);
      return e.eid;
    };
    for (let fi = 0; fi < 4; fi++) {
      for (let k = 0; k < 4; k++) {
        const id = add("pollen", null, FLOWERS[fi].x, FLOWERS[fi].y, "flower", fi);
        this.flowers[fi].push(id);
      }
    }
    ["red", "blue"].forEach((c) => {
      for (let k = 0; k < 4; k++) add("pollen", null, GARDEN[c].x + 3 + k * 5, GARDEN[c].y + 1, "garden", 0);
    });
    ["red", "blue"].forEach((c) => {
      for (let k = 0; k < 3; k++) {
        const id = add("nectar", c, HIVE.cx, HIVE.cy, "cell", 0);
        this.hives[c].a.push(id);
      }
      for (let k = 0; k < 5; k++) add("nectar", c, -10, -10, "off_field", 0);
    });
    let idx = 0;
    ["red", "blue"].forEach((c) => {
      for (let slot = 0; slot < 2; slot++) {
        const p = START[c][slot];
        const inv = [];
        for (let k = 0; k < 4; k++) inv.push(add("pollen", null, p[0], p[1], "robot", idx));
        const sk = this.skills[c];
        this.robots.push({
          idx: idx, alliance: c, slot: slot, x: p[0], y: p[1], skill: sk, strat: this.strats[c],
          inv: inv, left: false, autoPark: false, telePark: false, busy: 0, intent: "idle",
          tx: 0, ty: 0, teid: null, tfl: null, extra: 0,
          willLeave: rng() <= sk.autoLeave, willDump: rng() <= sk.autoDump, willPark: rng() <= sk.autoPark,
        });
        idx++;
      }
    });
    this._note("MATCH start. 4 POLLEN preloaded per ROBOT. 3 NECTAR in each upward CELL.");
  };

  MatchSim.prototype.el = function (id) { return this.elements[id]; };
  MatchSim.prototype.up = function (h) { return h.upA ? h.a : h.b; };
  MatchSim.prototype.setUp = function (h, arr) { if (h.upA) h.a = arr; else h.b = arr; };
  MatchSim.prototype.tips = function (h) { return h.autoTips + h.teleTips; };
  MatchSim.prototype.teleRemain = function () {
    return this.phase === "auto" ? R.TELEOP_S : Math.max(0, R.PLAY_S - this.playT);
  };
  MatchSim.prototype.flowersOn = function () {
    return this.phase === "teleop" && this.teleRemain() <= R.FLOWER_UNLOCK;
  };

  MatchSim.prototype.run = function () {
    const steps = Math.round(R.PLAY_S / this.dt);
    let released = false;
    for (let i = 0; i < steps; i++) {
      if (this.playT + 1e-9 >= R.AUTO_S) {
        if (this.phase === "auto" && !released) {
          this.robots.forEach((b) => { if (b.intent === "park") b.intent = "idle"; });
          released = true;
        }
        this.phase = "teleop";
      }
      this._tick();
      if (this.record && Math.abs(this.playT / 0.25 - Math.round(this.playT / 0.25)) < this.dt * 0.6) {
        this.frames.push(this.snapshot());
      }
      this.playT = Math.round((this.playT + this.dt) * 10000) / 10000;
    }
    const score = this.finalScore();
    this._note("Final: RED " + score.red.points + "  BLUE " + score.blue.points + "  (" + score.winner + ")");
    return score;
  };

  MatchSim.prototype._tick = function () {
    this._hives();
    this._nectar();
    this.elements.forEach((e) => { if (e.settle > 0) e.settle = Math.max(0, e.settle - this.dt); });
    for (let i = 0; i < this.robots.length; i++) {
      const bot = this.robots[i];
      if (this.playT < bot.busy) continue;
      this._choose(bot);
      this._act(bot);
    }
    this._separate();
    this._parkLeave();
    this._assertAllianceNectar();
  };

  MatchSim.prototype._assertAllianceNectar = function () {
    for (let i = 0; i < this.robots.length; i++) {
      const bot = this.robots[i];
      for (let j = 0; j < bot.inv.length; j++) {
        const el = this.el(bot.inv[j]);
        if (el.kind === "nectar" && el.color !== bot.alliance) {
          throw new Error("G408: " + bot.alliance + " robot holds " + el.color + " nectar");
        }
      }
    }
  };

  MatchSim.prototype._hives = function () {
    const self = this;
    ["red", "blue"].forEach((c) => {
      const h = self.hives[c];
      if (h.tipping && self.playT >= h.tipEnds) self._finishTip(h);
      else if (!h.tipping) {
        let mass = 0;
        self.up(h).forEach((id) => { mass += pe(self.el(id).kind); });
        if (mass + 1e-9 >= R.TIP_MASS) {
          h.tipping = true;
          h.tipEnds = self.playT + R.TIP_DUR;
        }
      }
    });
  };

  MatchSim.prototype._finishTip = function (h) {
    const contents = this.up(h).slice();
    this.setUp(h, []);
    h.upA = !h.upA;
    h.tipping = false;
    if (this.phase === "auto") h.autoTips++; else h.teleTips++;
    for (let i = 0; i < contents.length; i++) {
      const el = this.el(contents[i]);
      const ang = this.rng() * Math.PI * 2;
      const rad = 22 + this.rng() * 20;
      const p = clamp(HIVE.cx + Math.cos(ang) * rad, HIVE.cy + Math.sin(ang) * rad, 3);
      el.x = p[0]; el.y = p[1]; el.loc = "floor"; el.settle = R.SETTLE + 0.05 * i;
    }
    this._note(h.alliance.toUpperCase() + " HIVE TIP #" + this.tips(h));
    if (h.unlocked < 5) {
      h.unlocked++;
      this.pending.push({ t: this.playT + 1.5, color: h.alliance });
    }
  };

  MatchSim.prototype._nectar = function () {
    if (!this.nectarFlood && this.phase === "teleop" && this.teleRemain() <= 60) {
      this.nectarFlood = true;
      const self = this;
      ["red", "blue"].forEach((c) => {
        self.elements.forEach((e) => {
          if (e.kind === "nectar" && e.color === c && e.loc === "off_field") {
            self.pending.push({ t: self.playT + 0.4 * self.rng(), color: c });
          }
        });
      });
      this._note("Last 60s: remaining NECTAR may enter via LOADING ZONES.");
    }
    const still = [];
    for (let i = 0; i < this.pending.length; i++) {
      const p = this.pending[i];
      if (this.playT + 1e-9 < p.t) { still.push(p); continue; }
      const el = this.elements.find((e) => e.kind === "nectar" && e.color === p.color && e.loc === "off_field");
      if (!el) continue;
      const lz = LOADING[p.color];
      el.loc = "loading";
      el.x = cx(lz) + (this.rng() - 0.5) * 10;
      el.y = cy(lz) + (this.rng() - 0.5) * 4;
      el.settle = 0.2;
    }
    this.pending = still;
  };

  MatchSim.prototype._parkLeave = function () {
    for (let i = 0; i < this.robots.length; i++) {
      const bot = this.robots[i];
      if (this.phase === "auto" && !bot.left) {
        const wall = bot.alliance === "red" ? 0 : 144;
        if (Math.abs(bot.x - wall) > 12) bot.left = true;
      }
      const inLz = contains(LOADING[bot.alliance], bot.x, bot.y, 8);
      if (this.phase === "auto") bot.autoPark = inLz;
      else bot.telePark = inLz;
    }
  };

  MatchSim.prototype._separate = function () {
    const bots = this.robots;
    for (let i = 0; i < bots.length; i++) {
      for (let j = i + 1; j < bots.length; j++) {
        const a = bots[i], b = bots[j];
        const d = dist(a.x, a.y, b.x, b.y);
        if (d < 1e-3) { a.x += 0.5; continue; }
        if (d < 16) {
          const push = (16 - d) * 0.5;
          const ux = (a.x - b.x) / d, uy = (a.y - b.y) / d;
          let p = clamp(a.x + ux * push, a.y + uy * push); a.x = p[0]; a.y = p[1];
          p = clamp(b.x - ux * push, b.y - uy * push); b.x = p[0]; b.y = p[1];
        }
      }
    }
  };

  MatchSim.prototype._choose = function (bot) {
    if (bot.intent !== "idle") return;
    if (this.phase === "auto") this._chooseAuto(bot);
    else this._chooseTele(bot);
  };

  MatchSim.prototype._chooseAuto = function (bot) {
    const st = bot.strat, sk = bot.skill;
    const remain = R.AUTO_S - this.playT;
    if (!bot.left) {
      if (!bot.willLeave) { bot.intent = "idle"; return; }
      bot.tx = bot.alliance === "red" ? 36 : 108;
      bot.ty = bot.y;
      bot.intent = "leave";
      return;
    }
    const wantDump = st.auto !== "leave_only" && bot.willDump;
    const can = remain > 6.5;
    if (wantDump && bot.inv.length && can) { this._beginLaunch(bot); return; }
    if (st.auto === "dump_cycle" && remain > 10 && bot.extra < sk.autoExtra) {
      const tgt = this._nearest(bot);
      if (tgt && bot.inv.length < R.POSSESSION) {
        bot.extra++;
        this._beginIntake(bot, tgt);
        return;
      }
    }
    if (remain <= 7.5 || st.auto === "leave_only" || (st.auto === "dump_park" && !bot.inv.length)) {
      if (remain <= 4 || bot.willPark) { this._beginPark(bot); return; }
    }
    if (bot.inv.length && can) { this._beginLaunch(bot); return; }
    bot.intent = "idle";
  };

  MatchSim.prototype._chooseTele = function (bot) {
    const st = bot.strat, sk = bot.skill;
    const remain = this.teleRemain();
    const parkS = st.park || sk.parkCommit;
    const hive = this.hives[bot.alliance];
    if (remain <= parkS) { this._beginPark(bot); return; }
    let mode = this.flowersOn() ? st.post : st.pre;
    if (st.tipGoal && this.tips(hive) >= st.tipGoal && this.flowersOn()) mode = "flower";
    else if (st.tipGoal && this.tips(hive) >= st.tipGoal && !this.flowersOn()) mode = st.name === "flower_focus" ? "extract" : "hive";
    if (mode === "hive" || mode === "nectar_hive") this._chooseHive(bot, mode === "nectar_hive" || st.preferNectar);
    else if (mode === "flower") this._chooseFlower(bot);
    else if (mode === "split") {
      if (bot.slot === 0 && this.tips(hive) < R.P2) this._chooseHive(bot, true);
      else this._chooseFlower(bot);
    } else if (mode === "extract") {
      if (!this._tryExtract(bot)) this._chooseHive(bot, false);
    } else this._chooseHive(bot, false);
  };

  MatchSim.prototype._invHas = function (bot, kind) {
    for (let i = 0; i < bot.inv.length; i++) {
      const e = this.el(bot.inv[i]);
      if (e.kind === kind && (kind === "pollen" || e.color === bot.alliance)) return true;
    }
    return false;
  };

  MatchSim.prototype._chooseHive = function (bot, preferNectar) {
    if (bot.inv.length) {
      if (bot.inv.length >= R.POSSESSION || (preferNectar && this._invHas(bot, "nectar")) || !this._nearest(bot, preferNectar)) {
        this._beginLaunch(bot); return;
      }
    }
    let tgt = this._nearest(bot, preferNectar);
    if (!tgt && preferNectar) tgt = this._nearest(bot, false);
    if (tgt && bot.inv.length < R.POSSESSION) { this._beginIntake(bot, tgt); return; }
    if (bot.inv.length) this._beginLaunch(bot);
    else bot.intent = "idle";
  };

  MatchSim.prototype._flowerH = function (fi) {
    let h = 0;
    for (let i = 0; i < this.flowers[fi].length; i++) {
      h += this.el(this.flowers[fi][i]).kind === "nectar" ? R.NECTAR_D : R.POLLEN_D;
    }
    return h;
  };

  MatchSim.prototype._flowerPlan = function (bot) {
    const color = bot.alliance;
    let best = null;
    for (let fi = 0; fi < 4; fi++) {
      const stack = this.flowers[fi];
      const nectars = [];
      const kinds = [];
      for (let i = 0; i < stack.length; i++) {
        const e = this.el(stack[i]);
        kinds.push(e.kind);
        if (e.kind === "nectar") nectars.push(e.color);
      }
      const room = R.FLOWER_H - this._flowerH(fi);
      const ourTop = nectars.length && nectars[nectars.length - 1] === color;
      const ourBot = nectars.length && nectars[0] === color;
      let cand = null;
      if (!nectars.length && room >= R.NECTAR_D) cand = [0, "bottom_nectar", fi];
      else if (nectars.length && !ourBot && kinds[0] === "pollen") cand = [1, "extract", fi];
      else if (ourTop && room >= R.POLLEN_D) cand = [2, "fill_pollen", fi];
      else if (ourBot && !ourTop && room >= R.NECTAR_D) cand = [3, "top_nectar", fi];
      else if (!ourTop && room >= R.NECTAR_D) cand = [4, "top_nectar", fi];
      else if (kinds[0] === "pollen" && bot.inv.length < R.POSSESSION) cand = [5, "extract", fi];
      if (cand && (!best || cand[0] < best[0])) best = cand;
    }
    return best ? [best[1], best[2]] : null;
  };

  MatchSim.prototype._tryExtract = function (bot) {
    if (bot.inv.length >= R.POSSESSION) return false;
    for (let fi = 0; fi < 4; fi++) {
      if (this.flowers[fi].length && this.el(this.flowers[fi][0]).kind === "pollen") {
        this._beginExtract(bot, fi); return true;
      }
    }
    return false;
  };

  MatchSim.prototype._chooseFlower = function (bot) {
    if (!this.flowersOn()) {
      if (!this._tryExtract(bot)) this._chooseHive(bot, false);
      return;
    }
    const plan = this._flowerPlan(bot);
    if (!plan) { this._chooseHive(bot, true); return; }
    const action = plan[0], fi = plan[1];
    if (action === "extract") { this._beginExtract(bot, fi); return; }
    const need = (action === "bottom_nectar" || action === "top_nectar") ? "nectar" : "pollen";
    if (!this._invHas(bot, need)) {
      const tgt = this._nearest(bot, need === "nectar", need);
      if (tgt && bot.inv.length < R.POSSESSION) { this._beginIntake(bot, tgt); return; }
      if (this._invHas(bot, "nectar") && this.flowersOn()) { this._beginPlace(bot, fi, "nectar"); return; }
      if (bot.inv.length && need === "nectar") { this._beginLaunch(bot); return; }
      bot.intent = "idle"; return;
    }
    this._beginPlace(bot, fi, need);
  };

  MatchSim.prototype._parkPt = function (bot) {
    const lz = LOADING[bot.alliance];
    return [cx(lz) + (bot.slot === 0 ? -8 : 8), lz.h + 3];
  };
  MatchSim.prototype._launchPt = function (bot) {
    const sign = bot.alliance === "red" ? -1 : 1;
    return [HIVE.cx + sign * (HIVE.w * 0.5 + 22), HIVE.cy + (bot.slot === 0 ? -14 : 14)];
  };
  MatchSim.prototype._approachFl = function (bot, pose) {
    if (pose.wall === "audience") return [pose.x + (bot.slot - 0.5) * 10, 16];
    if (pose.wall === "rear") return [pose.x + (bot.slot - 0.5) * 10, 128];
    if (pose.wall === "red") return [16, pose.y + (bot.slot - 0.5) * 10];
    return [128, pose.y + (bot.slot - 0.5) * 10];
  };
  MatchSim.prototype._beginPark = function (bot) {
    const p = this._parkPt(bot); bot.intent = "park"; bot.tx = p[0]; bot.ty = p[1];
  };
  MatchSim.prototype._beginIntake = function (bot, el) {
    bot.intent = "intake"; bot.teid = el.eid; bot.tx = el.x; bot.ty = el.y;
  };
  MatchSim.prototype._beginLaunch = function (bot) {
    const p = this._launchPt(bot); bot.intent = "launch"; bot.tx = p[0]; bot.ty = p[1];
  };
  MatchSim.prototype._beginPlace = function (bot, fi, kind) {
    bot.intent = "place"; bot.tfl = fi;
    bot.teid = null;
    for (let i = 0; i < bot.inv.length; i++) {
      const e = this.el(bot.inv[i]);
      if (e.kind === kind && (kind === "pollen" || e.color === bot.alliance)) { bot.teid = e.eid; break; }
    }
    const p = this._approachFl(bot, FLOWERS[fi]); bot.tx = p[0]; bot.ty = p[1];
  };
  MatchSim.prototype._beginExtract = function (bot, fi) {
    bot.intent = "extract"; bot.tfl = fi;
    const p = this._approachFl(bot, FLOWERS[fi]); bot.tx = p[0]; bot.ty = p[1];
  };

  MatchSim.prototype._act = function (bot) {
    if (bot.intent === "idle") return;
    if (bot.intent === "intake" && bot.teid != null) {
      const el = this.el(bot.teid);
      if (["floor", "garden", "loading"].indexOf(el.loc) < 0 || el.settle > 0) { bot.intent = "idle"; bot.teid = null; return; }
      bot.tx = el.x; bot.ty = el.y;
    }
    if (dist(bot.x, bot.y, bot.tx, bot.ty) > 8) { this._drive(bot, bot.tx, bot.ty); return; }
    if (bot.intent === "leave") { bot.intent = "idle"; return; }
    if (bot.intent === "park") return;
    if (bot.intent === "intake") this._doIntake(bot);
    else if (bot.intent === "launch") this._doLaunch(bot);
    else if (bot.intent === "place") this._doPlace(bot);
    else if (bot.intent === "extract") this._doExtract(bot);
  };

  MatchSim.prototype._drive = function (bot, tx, ty) {
    const step = bot.skill.speed * this.dt;
    const d = dist(bot.x, bot.y, tx, ty);
    if (d <= step || d < 1e-6) { bot.x = tx; bot.y = ty; return; }
    let nx = bot.x + ((tx - bot.x) / d) * step;
    let ny = bot.y + ((ty - bot.y) / d) * step;
    if (contains(HIVE, nx, ny, -6)) {
      const ux = (tx - bot.x) / d, uy = (ty - bot.y) / d;
      nx += -uy * step; ny += ux * step;
    }
    const p = clamp(nx, ny); bot.x = p[0]; bot.y = p[1];
  };

  MatchSim.prototype._doIntake = function (bot) {
    if (bot.teid == null || bot.inv.length >= R.POSSESSION) { bot.intent = "idle"; return; }
    const el = this.el(bot.teid);
    // G408: cannot CONTROL opponent-color NECTAR. POLLEN is shared.
    if (el.kind === "nectar" && el.color !== bot.alliance) { bot.intent = "idle"; return; }
    if (["floor", "garden", "loading"].indexOf(el.loc) < 0 || el.settle > 0) { bot.intent = "idle"; return; }
    if (dist(bot.x, bot.y, el.x, el.y) > R.INTAKE_RANGE + 4) return;
    bot.busy = this.playT + bot.skill.intake;
    if (this.rng() > bot.skill.intakeRel) { bot.intent = "idle"; bot.teid = null; return; }
    el.loc = "robot"; el.locI = bot.idx;
    bot.inv.push(el.eid); bot.intent = "idle"; bot.teid = null;
  };

  MatchSim.prototype._doLaunch = function (bot) {
    if (!bot.inv.length) { bot.intent = "idle"; return; }
    const eid = bot.inv.shift();
    const el = this.el(eid);
    bot.busy = this.playT + bot.skill.launch;
    const hive = this.hives[bot.alliance];
    if (hive.tipping) { bot.inv.unshift(eid); bot.busy = hive.tipEnds; return; }
    if (this.rng() <= bot.skill.hiveAcc) {
      el.loc = "cell"; el.x = HIVE.cx; el.y = HIVE.cy;
      this.up(hive).push(eid);
    } else {
      const ang = this.rng() * Math.PI * 2;
      const p = clamp(HIVE.cx + Math.cos(ang) * 20, HIVE.cy + Math.sin(ang) * 16, 3);
      el.loc = "floor"; el.x = p[0]; el.y = p[1];
    }
    if (!bot.inv.length) bot.intent = "idle";
  };

  MatchSim.prototype._doPlace = function (bot) {
    const fi = bot.tfl, eid = bot.teid;
    if (fi == null || eid == null || bot.inv.indexOf(eid) < 0) { bot.intent = "idle"; return; }
    if (!this.flowersOn()) { bot.intent = "idle"; return; }
    const el = this.el(eid);
    const acc = el.kind === "nectar" ? bot.skill.flowerNectar : bot.skill.flowerPollen;
    bot.busy = this.playT + bot.skill.flowerPlace;
    bot.inv = bot.inv.filter((id) => id !== eid);
    bot.intent = "idle";
    const pose = FLOWERS[fi];
    if (this.rng() > acc) {
      const p = clamp(pose.x + (this.rng() - 0.5) * 16, pose.y + (this.rng() - 0.5) * 16, 3);
      el.loc = "floor"; el.x = p[0]; el.y = p[1]; return;
    }
    const need = el.kind === "nectar" ? R.NECTAR_D : R.POLLEN_D;
    if (this._flowerH(fi) + need > R.FLOWER_H + 0.2) {
      const p = clamp(pose.x + 8, pose.y + 8, 3);
      el.loc = "floor"; el.x = p[0]; el.y = p[1]; return;
    }
    el.loc = "flower"; el.locI = fi; el.x = pose.x; el.y = pose.y;
    this.flowers[fi].push(eid);
  };

  MatchSim.prototype._doExtract = function (bot) {
    const fi = bot.tfl;
    bot.intent = "idle";
    if (fi == null || bot.inv.length >= R.POSSESSION) return;
    const stack = this.flowers[fi];
    if (!stack.length) return;
    const bottom = this.el(stack[0]);
    if (bottom.kind !== "pollen") return;
    bot.busy = this.playT + bot.skill.flowerExtract;
    stack.shift();
    bottom.loc = "robot"; bottom.locI = bot.idx;
    bot.inv.push(bottom.eid);
  };

  MatchSim.prototype._nearest = function (bot, nectarOnly, forceKind) {
    let best = null, bestD = 1e9;
    const kind = forceKind || (nectarOnly ? "nectar" : null);
    for (let i = 0; i < this.elements.length; i++) {
      const el = this.elements[i];
      if (["floor", "garden", "loading"].indexOf(el.loc) < 0) continue;
      if (el.settle > 0) continue;
      if (el.kind === "nectar" && el.color !== bot.alliance) continue;
      if (kind && el.kind !== kind) continue;
      if (nectarOnly && el.kind !== "nectar") continue;
      let d = dist(bot.x, bot.y, el.x, el.y);
      if (el.loc === "loading") d *= 0.85;
      if (d < bestD) { best = el; bestD = d; }
    }
    return best;
  };

  MatchSim.prototype.live = function (color) {
    const hive = this.hives[color];
    const bd = emptyBd();
    this.robots.forEach((b) => {
      if (b.alliance !== color) return;
      if (b.left) bd.leave++;
      if (b.autoPark) bd.autoPark++;
      if (b.telePark) bd.telePark++;
    });
    bd.autoTips = hive.autoTips;
    bd.teleopTips = hive.teleTips;
    bd.cell = hive.tipping ? 0 : this.up(hive).length;
    for (let fi = 0; fi < 4; fi++) {
      const stack = this.flowers[fi].map((id) => this.el(id));
      const nectars = stack.filter((e) => e.kind === "nectar" && e.color).map((e) => e.color);
      if (nectars.length) {
        if (nectars[0] === color) bd.bottom++;
        if (nectars[nectars.length - 1] === color) bd.owned += stack.length;
      }
    }
    this.elements.forEach((el) => {
      if (["floor", "garden", "loading"].indexOf(el.loc) < 0) return;
      if (contains(GARDEN[color], el.x, el.y, 2.5)) bd.garden++;
    });
    return bd;
  };

  MatchSim.prototype.finalScore = function () {
    const red = this.live("red"), blue = this.live("blue");
    red.points = breakdownPoints(red);
    blue.points = breakdownPoints(blue);
    const winner = red.points > blue.points ? "red" : blue.points > red.points ? "blue" : "tie";
    red.rp = rpBits(red, winner === "red", winner === "tie");
    blue.rp = rpBits(blue, winner === "blue", winner === "tie");
    red.rpTotal = red.rp.win + red.rp.swarm + red.rp.p1 + red.rp.p2;
    blue.rpTotal = blue.rp.win + blue.rp.swarm + blue.rp.p1 + blue.rp.p2;
    return { red: red, blue: blue, winner: winner };
  };

  MatchSim.prototype.snapshot = function () {
    const self = this;
    const nectar = {
      red: { grab: 0, held: 0, cell: 0, flower: 0, off: 0 },
      blue: { grab: 0, held: 0, cell: 0, flower: 0, off: 0 },
    };
    this.elements.forEach((e) => {
      if (e.kind !== "nectar" || !nectar[e.color]) return;
      const b = nectar[e.color];
      if (e.loc === "robot") b.held++;
      else if (e.loc === "cell") b.cell++;
      else if (e.loc === "flower") b.flower++;
      else if (e.loc === "off_field") b.off++;
      else b.grab++;
    });
    return {
      t: Math.round(this.playT * 10) / 10,
      phase: this.phase,
      robots: this.robots.map((b) => ({
        i: b.idx, a: b.alliance, x: Math.round(b.x), y: Math.round(b.y), n: b.inv.length, intent: b.intent,
        inv: b.inv.map((id) => {
          const e = self.el(id);
          return e.kind === "pollen" ? 0 : (e.color === "red" ? 1 : 2);
        }),
      })),
      balls: this.elements.filter((e) => e.loc !== "off_field" && e.loc !== "robot" && e.loc !== "cell" && e.loc !== "flower").map((e) => ({
        k: e.kind === "pollen" ? 0 : 1, c: e.color === "red" ? 1 : e.color === "blue" ? 2 : 0, x: Math.round(e.x), y: Math.round(e.y),
      })),
      hives: {
        red: {
          tips: this.tips(this.hives.red), up: this.hives.red.upA ? "a" : "b", tipping: this.hives.red.tipping,
          n: this.up(this.hives.red).length,
          cell: this.up(this.hives.red).map((id) => {
            const e = self.el(id);
            return [e.kind === "pollen" ? 0 : 1, e.color === "red" ? 1 : e.color === "blue" ? 2 : 0];
          }),
        },
        blue: {
          tips: this.tips(this.hives.blue), up: this.hives.blue.upA ? "a" : "b", tipping: this.hives.blue.tipping,
          n: this.up(this.hives.blue).length,
          cell: this.up(this.hives.blue).map((id) => {
            const e = self.el(id);
            return [e.kind === "pollen" ? 0 : 1, e.color === "red" ? 1 : e.color === "blue" ? 2 : 0];
          }),
        },
      },
      flowers: this.flowers.map((st) => st.map((id) => {
        const e = self.el(id);
        return [e.kind === "pollen" ? 0 : 1, e.color === "red" ? 1 : e.color === "blue" ? 2 : 0];
      })),
      nectar: nectar,
      score: { red: breakdownPoints(this.live("red")), blue: breakdownPoints(this.live("blue")) },
    };
  };

  function playMatch(opts) {
    opts = opts || {};
    const red = applyCaps(opts.redCaps || opts.caps || {});
    const blue = applyCaps(opts.blueCaps || opts.caps || {});
    const sim = new MatchSim(red, blue, opts.redStrategy || "hive_cycle", opts.blueStrategy || "flower_focus", opts.seed || 1, !!opts.record);
    const score = sim.run();
    return { score: score, frames: sim.frames, events: sim.events, meta: sim.meta };
  }

  function runMany(opts, onProgress) {
    opts = opts || {};
    const n = opts.matches || 200;
    const strats = opts.strategies || Object.keys(STRATEGIES);
    const caps = applyCaps(opts.caps || {});
    const seed0 = opts.seed || 1;
    const rows = [];
    let k = 0;
    const jobs = [];
    while (jobs.length < n) {
      for (let i = 0; i < strats.length; i++) {
        for (let j = 0; j < strats.length; j++) {
          jobs.push([strats[i], strats[j]]);
          if (jobs.length >= n) break;
        }
        if (jobs.length >= n) break;
      }
    }
    for (let i = 0; i < jobs.length; i++) {
      const sim = new MatchSim(caps, caps, jobs[i][0], jobs[i][1], seed0 + i, false);
      const s = sim.run();
      rows.push({
        redS: jobs[i][0], blueS: jobs[i][1], winner: s.winner,
        redP: s.red.points, blueP: s.blue.points,
        redT: s.red.autoTips + s.red.teleopTips, blueT: s.blue.autoTips + s.blue.teleopTips,
        redRP: s.red.rpTotal, blueRP: s.blue.rpTotal,
        redOwn: s.red.owned, blueOwn: s.blue.owned,
      });
      k++;
      if (onProgress && (k % 20 === 0 || k === jobs.length)) onProgress(k, jobs.length);
    }
    return summarize(rows, strats);
  }

  function summarize(rows, strats) {
    const by = {};
    strats.forEach((s) => { by[s] = []; });
    function eat(strat, pts, opp, tips, rp, owned, win, tie) {
      by[strat].push({ pts: pts, opp: opp, tips: tips, rp: rp, owned: owned, win: win, tie: tie });
    }
    rows.forEach((r) => {
      eat(r.redS, r.redP, r.blueP, r.redT, r.redRP, r.redOwn, r.winner === "red" ? 1 : 0, r.winner === "tie" ? 1 : 0);
      eat(r.blueS, r.blueP, r.redP, r.blueT, r.blueRP, r.blueOwn, r.winner === "blue" ? 1 : 0, r.winner === "tie" ? 1 : 0);
    });
    function avg(arr, k) { if (!arr.length) return 0; return arr.reduce((s, x) => s + x[k], 0) / arr.length; }
    const table = {};
    strats.forEach((s) => {
      const a = by[s];
      table[s] = {
        n: a.length,
        winRate: avg(a, "win"),
        tieRate: avg(a, "tie"),
        pts: avg(a, "pts"),
        tips: avg(a, "tips"),
        rp: avg(a, "rp"),
        owned: avg(a, "owned"),
      };
    });
    const ranked = strats.slice().sort((a, b) => table[b].winRate - table[a].winRate || table[b].pts - table[a].pts);
    return { n: rows.length, table: table, ranked: ranked, rows: rows };
  }

  function sweep(opts, onProgress) {
    opts = opts || {};
    const hiveGrid = opts.hiveGrid || [0.30, 0.45, 0.60, 0.75, 0.90];
    const intakeGrid = opts.intakeGrid || [3.5, 2.2, 1.4, 0.8];
    const flowerGrid = opts.flowerGrid || [0.20, 0.40, 0.60, 0.80];
    const strats = opts.strategies || ["hive_cycle", "nectar_tips", "hive_then_flower", "flower_focus"];
    const reps = opts.reps || 2;
    const cells = [];
    let done = 0;
    const total = hiveGrid.length * intakeGrid.length * strats.length * strats.length * reps
      + hiveGrid.length * flowerGrid.length * strats.length * strats.length * reps;
    function cellRun(caps) {
      const jobs = [];
      for (let r = 0; r < reps; r++) {
        strats.forEach((a) => strats.forEach((b) => jobs.push([a, b, r])));
      }
      const rows = [];
      jobs.forEach((j, i) => {
        const sim = new MatchSim(caps, caps, j[0], j[1], 1000 + done + i, false);
        const s = sim.run();
        rows.push({
          redS: j[0], blueS: j[1], winner: s.winner,
          redP: s.red.points, blueP: s.blue.points,
          redT: s.red.autoTips + s.red.teleopTips, blueT: s.blue.autoTips + s.blue.teleopTips,
          redRP: s.red.rpTotal, blueRP: s.blue.rpTotal, redOwn: s.red.owned, blueOwn: s.blue.owned,
        });
        done++;
        if (onProgress && done % 15 === 0) onProgress(done, total);
      });
      const sum = summarize(rows, strats);
      return { best: sum.ranked[0], table: sum.table };
    }
    const hiveIntake = [];
    hiveGrid.forEach((h) => {
      intakeGrid.forEach((inn) => {
        const caps = applyCaps({ hive_accuracy: h, intake_s: inn, flower_accuracy: 0.40, intake_reliability: 0.80 });
        const r = cellRun(caps);
        hiveIntake.push({ hive: h, intake: inn, best: r.best, table: r.table });
      });
    });
    const hiveFlower = [];
    hiveGrid.forEach((h) => {
      flowerGrid.forEach((f) => {
        const caps = applyCaps({ hive_accuracy: h, flower_accuracy: f, intake_s: 2.2, intake_reliability: 0.80 });
        const r = cellRun(caps);
        hiveFlower.push({ hive: h, flower: f, best: r.best, table: r.table });
      });
    });
    if (onProgress) onProgress(total, total);
    return { hiveIntake: hiveIntake, hiveFlower: hiveFlower, hiveGrid: hiveGrid, intakeGrid: intakeGrid, flowerGrid: flowerGrid, strats: strats };
  }

  global.Biobuzz = {
    R: R,
    STRATEGIES: STRATEGIES,
    applyCaps: applyCaps,
    playMatch: playMatch,
    runMany: runMany,
    sweep: sweep,
    MatchSim: MatchSim,
    HIVE: HIVE,
    FLOWERS: FLOWERS,
  };
})(typeof window !== "undefined" ? window : globalThis);
