# BIOBUZZ strategy lab

A website that simulates FTC 2026–2027 BIOBUZZ matches in your browser. Set how often the robots miss and how long pickup takes, run hundreds of matches, and watch a few of them.

You do **not** need an IDE, Cursor, or a Python install to *use* it. Open the site, move the sliders, press a button.

## How to use it

### Fastest: open the page

1. Get this repo (GitHub **Code → Download ZIP**, or `git clone https://github.com/6603GuildofGears/biobuzz-point-strategy.git`).
2. Open `docs/index.html` in Chrome, Safari, Edge, or Firefox (double-click, or File → Open).

If the page is blank or the buttons do nothing, your browser is blocking local files. Use the one-line server below.

### Reliable: one-line server (Mac, Windows, Linux)

You only need Python 3, which is already on most school Macs and many Windows machines.

```bash
cd biobuzz-point-strategy
python3 -m http.server 8765 --directory docs
```

On Windows, if `python3` is not found:

```bat
python -m http.server 8765 --directory docs
```

Leave that terminal open. In a browser go to **http://127.0.0.1:8765**. Stop the server with Ctrl+C.

### On the internet (share with the whole team)

The site is four static files in `docs/` (`index.html`, `sim.js`, `ui.js`, `app.css`). There is no login and no database.

A repo admin still has to flip Pages on once (GitHub will not do it from a workflow by itself):

1. GitHub repo **Settings → Pages**
2. Deploy from branch **`main`**, folder **`/docs`**
3. After a minute, the public URL is typically https://6603guildofgears.github.io/biobuzz-point-strategy/

Until Pages is on, use the local steps above. You can also drop the `docs/` folder onto Netlify, Cloudflare Pages, or a USB stick plus the one-line server.

## What to do on the site

1. **Set the sliders from practice** with the real robot (see the table below).
2. Pick a **Red strategy** and a **Blue strategy**.
3. **Watch one match** — a replay of one simulated match. Yellow balls are POLLEN (anyone). Red/blue balls are NECTAR (that alliance only).
4. **Simulate 400 matches** — which plan wins *for your miss/pickup numbers*.
5. **Map: what to focus on** — heatmaps of hive accuracy vs pickup time, and hive accuracy vs flower accuracy.

| Slider | How to measure at practice |
| --- | --- |
| **Hive shot hit rate** | Makes ÷ attempts into the CELL |
| **Flower dunk hit rate** | Makes ÷ attempts into the 4 in FLOWER hole |
| **Time to pick up one ball** | Seconds from lined-up on a ball to controlling it |
| **Intake success rate** | Pickup attempts that actually stick |

A HIVE TIP is 20 points. An owned FLOWER element is 2. Missed shots and slow intakes usually matter more than field-geometry trivia. NECTAR dunks are harder than POLLEN (3.6 in ball, 4 in hole).

**Color rule (G408):** red robots only pick up red NECTAR; blue robots only pick up blue NECTAR. POLLEN is yellow and either alliance may use it. Each side has 8 nectar of their color and cannot steal the other side’s to tip the hive or dunk flowers.

## Optional: Python CLI (batch reports)

Only if you want thousands of matches written to HTML on disk. First install the package:

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
python -m pip install -e ".[dev]"
python -m biobuzz serve            # same website, opens a browser
python -m biobuzz simulate --matches 4000 --out output
python -m pytest
```

Then open `output/report.html`. The website in `docs/` is still the thing to share with the team.

How scoring is modeled: [`docs/GAME_MODEL.md`](docs/GAME_MODEL.md).
