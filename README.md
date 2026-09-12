# BIOBUZZ match simulator (FTC 2026-2027)

Simulate thousands of BIOBUZZ matches, compare strategies, and watch a few of them in a browser.

You do **not** need an IDE. Python 3.10+ and a web browser are enough on Mac (including M2), Windows, and Linux. Cursor in the browser is a fine place to edit this repo with me; when the kids run it at a meeting, they just use Terminal / Command Prompt.

## Quick start

```bash
# Mac / Linux
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
python -m pip install -e ".[dev]"

python -m biobuzz simulate --matches 4000 --out output
```

Then open `output/report.html` and any file in `output/replays/`.

Windows (Command Prompt):

```bat
py -3 -m venv .venv
.venv\Scripts\activate
python -m pip install -e ".[dev]"
python -m biobuzz simulate --matches 4000 --out output
start output\report.html
```

There are no extra runtime libraries. The simulator is pure Python. Replays are a single HTML file each.

## Do I need Cursor / VS Code / this web browser?

| What you want | What to use |
| --- | --- |
| Keep working on the model with me | This Cursor cloud session, or Cursor / VS Code on the laptop |
| Run 4,000 matches on a kid's laptop | Terminal + Python. No IDE. |
| Watch a match | Any browser (Safari, Chrome, Edge, Firefox) |
| Change numbers (tip mass, skill) | A text editor is enough; an IDE is optional |

An IDE helps with tests and editing, but it is not required to *run* the sim.

## What the game is (short)

BIOBUZZ is 2v2 on a 12-ft field. AUTO is 30s, then 2 minutes of TELEOP.

- **HIVE / CELL:** launch POLLEN or NECTAR into your upward CELL. When there is enough mass, the HIVE **TIPS** (20 pts). Balls dump back onto the floor and you can cycle them again. Leftovers in the CELL at the end are 2 pts each.
- **FLOWERS:** last 60 seconds only. NECTAR cannot be removed once scored. Bottom-most NECTAR is +5. Top-most NECTAR **owns** the flower and scores **2 pts per element** in it (any color). Pollen-only flowers score **nothing**.
- **GARDEN:** 1 pt per element sitting there at the end (cheap leftover).
- **LEAVE / PARK:** 3 + 5 (AUTO) + 5 (TELEOP). Combined ≥ 16 pts earns the **SWARM** ranking point.
- **POLLINATOR 1 / 2:** 4 tips and 7 tips.

Possession limit is 4. You may not control opponent NECTAR. NECTAR is larger/heavier (~2.1× POLLEN) so it tips the HIVE faster. One NECTAR may enter from the alliance area after each tip; all remaining NECTAR may enter in the last 60s.

The Competition Manual does **not** publish the exact mass that tips a CELL. We assume **8 pollen-equivalents** for an empty CELL (two robots at the possession limit can tip together; 4 nectar ≈ one robot solo-tip). Override with `--tip-mass`.

## Strategies compared

| id | Idea |
| --- | --- |
| `hive_cycle` | Launch into the CELL all match. Ignore flowers. |
| `hive_then_flower` | Cycle the HIVE until the last 60s, then contest flowers. |
| `nectar_tips` | Hunt NECTAR because it tips faster. |
| `flower_focus` | Extract flower pollen, then stuff flowers in the last minute. |
| `rp_hunter` | LEAVE+PARK for SWARM, 4 tips for POLLINATOR 1, then flowers. |
| `park_and_dump` | Realistic first-meet: leave, dump what is easy, park. |

Skill bands (`starter`, `developing`, `competitive`, `elite`) cap how fast and how accurately a student-built robot can intake, launch, and dunk. That is the point: “optimal” on paper is not what a first-year kit-bot can do.

## Useful commands

```bash
python -m biobuzz simulate --matches 8000 --skills starter,developing,competitive
python -m biobuzz simulate --matches 2000 --tip-mass 10
python -m biobuzz watch --red-strategy hive_cycle --blue-strategy flower_focus --out output/replays/one.html
python -m pytest
```

## Layout

```
src/biobuzz/     simulator
tests/           scoring + smoke tests
docs/GAME_MODEL.md
output/          created when you run (gitignored)
```
