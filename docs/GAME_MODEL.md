# How this simulator models BIOBUZZ

Scoring, timing, possession, and field sizes come from the BIOBUZZ Competition
Manual V1 (12 Sep 2026), Tables 10-2 and 10-3 and sections 9–11.

The **website** (`docs/index.html`) is the product. Python (`python -m biobuzz`)
is optional. The browser engine in `docs/sim.js` is a port of `src/biobuzz/sim.py`.

## Encoded as rules

- AUTO 30s, TELEOP 120s.
- 40 POLLEN (yellow, either alliance may use), 8 NECTAR per alliance color.
- **G408:** a robot may not CONTROL opponent-color NECTAR. Red robots pick
  up red NECTAR only; blue robots pick up blue NECTAR only. This matters:
  you cannot steal their 8 balls to tip your HIVE or dunk FLOWERS. After a
  hive dump the floor can be mixed-color — robots still ignore the other
  color. FLOWERS can mix colors (whoever dunks last NECTAR owns the stack),
  but you can only *add* your own. NECTAR already in a FLOWER cannot be
  removed.
- HIVE TIP = 20. CELL leftovers = 2. Bottom nectar = 5. Owned flower element = 2.
  Garden = 1. LEAVE = 3. PARK = 5 / period.
- SWARM RP at 16 LEAVE+PARK. POLLINATOR 1 at 4 tips, 2 at 7.
- Possession 4. Flower *scoring* only in the last 60s. Extract pollen from flowers earlier.
- One off-field NECTAR per TIP; remaining NECTAR at 60s left.

## What actually decides strategy

Kid-built robots miss, fumble intakes, and take seconds to pick up a ball.
Those knobs are first-class on the website:

| Knob | What to measure at practice |
| --- | --- |
| Hive shot hit rate | Makes / attempts into the CELL |
| Flower dunk hit rate | Makes / attempts into the 4 in FLOWER hole |
| Pickup time | Seconds from lined-up to possessed |
| Intake success | Fraction of pickup attempts that stick |

Slow pickup also stretches launch and dunk time (a clumsy cycle). NECTAR dunks
are modeled as harder than POLLEN (~0.62× the pollen dunk rate) because a 3.6 in
ball into a 4 in hole is tight.

## Physics assumption

Empty CELL tip mass defaults to **8 pollen-equivalents**. The manual does not
publish this. 4 NECTAR can solo-tip; 3 starting NECTAR do not self-tip.
