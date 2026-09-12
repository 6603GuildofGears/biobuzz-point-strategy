"""Command-line entry: simulate thousands of BIOBUZZ matches and write reports."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import rules
from .html_report import write_replay, write_report
from .monte_carlo import run_batch, summarize
from .rules import PhysicsAssumptions
from .sim import MatchSim
from .skills import SKILLS, SKILL_HELP
from .strategies import STRATEGIES


DEMO_MATCHUPS = (
    ("developing", "hive_then_flower", "developing", "flower_focus", 7),
    ("developing", "hive_cycle", "developing", "hive_then_flower", 11),
    ("starter", "park_and_dump", "starter", "hive_then_flower", 3),
    ("competitive", "nectar_tips", "competitive", "hive_then_flower", 19),
    ("elite", "rp_hunter", "elite", "hive_cycle", 23),
    ("developing", "hive_cycle", "starter", "flower_focus", 29),
)


def _physics(args: argparse.Namespace) -> PhysicsAssumptions:
    return PhysicsAssumptions(
        empty_cell_tip_pe=args.tip_mass,
        nectar_mass_ratio=args.nectar_mass,
    )


def _headline(summary: dict) -> str:
    lines = []
    for rec in summary["recommendations"]:
        skill = rec["skill"]
        ranked = [r for r in rec["ranked"] if r["n"]]
        if not ranked:
            continue
        best = ranked[0]
        hive = next((r for r in ranked if r["strategy"] == "hive_cycle"), None)
        flower = next((r for r in ranked if r["strategy"] == "flower_focus"), None)
        mix = next((r for r in ranked if r["strategy"] == "hive_then_flower"), None)
        bit = (
            f"At {skill} skill, {STRATEGIES[best['strategy']].title} wins most often "
            f"({best['win_rate']*100:.0f}% wr, {best['avg_points']:.0f} pts, {best['avg_tips']:.1f} tips)."
        )
        if hive and flower:
            bit += (
                f" Pure hive cycling averages {hive['avg_points']:.0f} pts vs "
                f"flower-focus {flower['avg_points']:.0f} pts."
            )
        if mix:
            bit += f" Hive-then-flowers averages {mix['avg_points']:.0f} pts."
        lines.append(bit)
    return " ".join(lines) if lines else "Not enough data."


def cmd_simulate(args: argparse.Namespace) -> int:
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    physics = _physics(args)
    skills = args.skills.split(",") if args.skills else list(SKILLS)
    strats = args.strategies.split(",") if args.strategies else list(STRATEGIES)
    for s in skills:
        if s not in SKILLS:
            raise SystemExit(f"Unknown skill {s}. Choose from: {', '.join(SKILLS)}")
    for s in strats:
        if s not in STRATEGIES:
            raise SystemExit(f"Unknown strategy {s}. Choose from: {', '.join(STRATEGIES)}")

    print(f"Simulating {args.matches} matches…")
    print("Skills:", ", ".join(f"{s} ({SKILL_HELP[s]})" for s in skills))
    print("Strategies:", ", ".join(strats))
    print(f"Tip threshold: {physics.empty_cell_tip_pe:.2f} pollen-equivalents "
          f"(nectar ≈ {physics.nectar_mass_ratio:.2f} PE)")

    rows = run_batch(
        matches=args.matches,
        skills=skills,
        strategies=strats,
        seed=args.seed,
        physics=physics,
        workers=args.workers,
        mix=args.mix,
        progress=not args.quiet,
    )
    summary = summarize(rows)
    notes = _headline(summary)
    print("\n" + notes + "\n")

    (out / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    write_report(out / "report.html", summary, physics.__dict__, notes)

    # Watchable subset
    replay_dir = out / "replays"
    print("Recording watchable replays…")
    for rs, rstr, bs, bstr, seed in DEMO_MATCHUPS:
        if rs not in skills or bs not in skills:
            continue
        if rstr not in strats or bstr not in strats:
            continue
        sim = MatchSim(rs, bs, rstr, bstr, seed=seed, physics=physics, record=True)
        score = sim.run()
        name = f"{rs}_{rstr}_vs_{bs}_{bstr}_{seed}.html"
        write_replay(replay_dir / name, sim.replay_payload(score))
        print(f"  {name}: RED {score.red.match_points}  BLUE {score.blue.match_points}  ({score.winner})")

    print(f"\nOpen {out / 'report.html'} in any browser.")
    print(f"Watch matches in {replay_dir}/")
    return 0


def cmd_watch(args: argparse.Namespace) -> int:
    physics = _physics(args)
    sim = MatchSim(
        args.red_skill,
        args.blue_skill,
        args.red_strategy,
        args.blue_strategy,
        seed=args.seed,
        physics=physics,
        record=True,
    )
    score = sim.run()
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    write_replay(out, sim.replay_payload(score))
    print(f"RED {score.red.match_points}  BLUE {score.blue.match_points}  winner={score.winner}")
    print(f"Wrote {out}")
    return 0


def _docs_dir() -> Path:
    here = Path(__file__).resolve()
    for candidate in (here.parents[2] / "docs", here.parents[1] / "docs", Path.cwd() / "docs"):
        if (candidate / "index.html").exists():
            return candidate
    raise SystemExit("Could not find docs/index.html. Run from the repo checkout.")


def cmd_serve(args: argparse.Namespace) -> int:
    import http.server
    import os
    import webbrowser

    docs = _docs_dir()
    os.chdir(docs)
    server = http.server.ThreadingHTTPServer(("127.0.0.1", args.port), http.server.SimpleHTTPRequestHandler)
    url = f"http://127.0.0.1:{args.port}/"
    print(f"BIOBUZZ lab at {url}")
    print("This is a static site. Copy the docs/ folder to GitHub Pages, Netlify, or any host.")
    if not args.no_open:
        try:
            webbrowser.open(url)
        except Exception:
            pass
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="biobuzz",
        description="Simulate FTC 2026-2027 BIOBUZZ matches and compare strategies.",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("simulate", help="Run a Monte Carlo batch and write HTML report + replays")
    s.add_argument("--matches", type=int, default=4000)
    s.add_argument("--skills", default="", help="Comma list: starter,developing,competitive,elite")
    s.add_argument("--strategies", default="", help="Comma list of strategy ids")
    s.add_argument("--seed", type=int, default=1)
    s.add_argument("--workers", type=int, default=0, help="Process workers (0 = auto)")
    s.add_argument("--mix", choices=("same_skill", "cross_skill"), default="same_skill")
    s.add_argument("--tip-mass", type=float, default=rules.DEFAULT_PHYSICS.empty_cell_tip_pe)
    s.add_argument("--nectar-mass", type=float, default=rules.DEFAULT_PHYSICS.nectar_mass_ratio)
    s.add_argument("--out", default="output")
    s.add_argument("--quiet", action="store_true")
    s.set_defaults(func=cmd_simulate)

    w = sub.add_parser("watch", help="Simulate one match and write an HTML replay")
    w.add_argument("--red-skill", default="developing")
    w.add_argument("--blue-skill", default="developing")
    w.add_argument("--red-strategy", default="hive_then_flower")
    w.add_argument("--blue-strategy", default="flower_focus")
    w.add_argument("--seed", type=int, default=7)
    w.add_argument("--tip-mass", type=float, default=rules.DEFAULT_PHYSICS.empty_cell_tip_pe)
    w.add_argument("--nectar-mass", type=float, default=rules.DEFAULT_PHYSICS.nectar_mass_ratio)
    w.add_argument("--out", default="output/replays/one.html")
    w.set_defaults(func=cmd_watch)

    sv = sub.add_parser("serve", help="Open the browser app locally (static docs/ site)")
    sv.add_argument("--port", type=int, default=8765)
    sv.add_argument("--no-open", action="store_true")
    sv.set_defaults(func=cmd_serve)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
