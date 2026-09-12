# BIOBUZZ strategy lab

A **website** that simulates FTC 2026–2027 BIOBUZZ matches in the browser. Set how often robots miss and how long pickup takes, run hundreds of matches, and watch a few of them.

You do **not** need an IDE, and you do not need Python to *use* it.

## Open it

### On a laptop (Mac, Windows, Linux)

From this repo:

```bash
python3 -m biobuzz serve
```

That serves `docs/` at http://127.0.0.1:8765 — the same files you can host on the internet.

Or, with no install, from the repo folder:

```bash
python3 -m http.server 8765 --directory docs
```

Then open http://127.0.0.1:8765 in Safari, Chrome, Edge, or Firefox.

### Host it for the team

The site is static (`docs/index.html` + `docs/sim.js` + `docs/ui.js` + `docs/app.css`). Put that folder on:

- **GitHub Pages** — repo Settings → Pages → Deploy from branch → `/docs`
- Netlify / Cloudflare Pages / any static host — upload the `docs/` folder
- A shared Google Drive / USB copy of `docs/` plus the one-line server above

There is no backend and no database.

## What to turn the knobs to

Practice with the real robot, then copy the numbers into the sliders:

| Slider | How to measure |
| --- | --- |
| **Hive shot hit rate** | Makes ÷ attempts into the CELL |
| **Flower dunk hit rate** | Makes ÷ attempts into the 4 in FLOWER hole |
| **Time to pick up one ball** | Seconds from lined-up on a ball to controlling it |
| **Intake success rate** | Pickup attempts that actually stick |

Then **Simulate 400 matches** to see which strategy wins *for those numbers*, and **Map: what to focus on** to see how the answer changes if you get more accurate or faster.

A HIVE TIP is 20 points. An owned FLOWER element is 2. Missed shots and slow intakes usually matter more than field-geometry trivia. NECTAR dunks are harder than POLLEN (3.6 in ball, 4 in hole).

**Color rule (G408):** red robots only pick up red NECTAR; blue robots only pick up blue NECTAR. POLLEN is yellow and either alliance may use it. Each side has 8 nectar of their color and cannot steal the other side’s to tip the hive or dunk flowers.

## Optional Python CLI

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
python -m pip install -e ".[dev]"
python -m biobuzz simulate --matches 4000 --out output
python -m pytest
```

The CLI is for batch HTML reports. The website is the thing to share.

## Do I need Cursor?

Only if you want to keep changing the model with me. Kids running matches just need a browser.
