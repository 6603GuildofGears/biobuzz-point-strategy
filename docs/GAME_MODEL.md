# How this simulator models BIOBUZZ

Scoring, timing, possession, and field sizes come from the BIOBUZZ Competition
Manual V1 (12 Sep 2026), Tables 10-2 and 10-3 and sections 9–11.

## Encoded as rules

- AUTO 30s, TELEOP 120s, 8s transition ignored as dead time (robots motionless).
- 40 POLLEN, 8 NECTAR per alliance.
- Staging: 4 pollen / flower, 4 pollen / garden, 4 pollen preloaded / robot,
  3 nectar in each upward CELL, 5 nectar off-field.
- HIVE TIP = 20 (AUTO or TELEOP). CELL leftovers = 2. Bottom nectar = 5.
  Owned flower element = 2. Garden element = 1. LEAVE = 3. PARK = 5 / period.
- SWARM RP at 16 combined LEAVE+PARK. POLLINATOR 1 at 4 tips, 2 at 7.
- Possession 4. Cannot CONTROL opponent NECTAR.
- Flower *scoring* (placing into the top) only in the last 60s of TELEOP.
  Extracting POLLEN from the bottom of a FLOWER is allowed earlier.
- One off-field NECTAR may enter per TIP; all remaining NECTAR at 60s left.
- When a HIVE tips, CELL contents dump to the floor and must settle before intake (G409).

## Assumptions (not in the manual)

These are CLI flags. Defaults:

| Symbol | Default | Why |
| --- | --- | --- |
| Empty CELL tip mass | 8 pollen-equivalents | Two robots at the possession limit can tip together. 4 nectar (~8.5 PE) can solo-tip. 3 starting nectar (~6.4 PE) do **not** self-tip. |
| Nectar / pollen mass | (3.6/2.8)³ ≈ 2.13 | Same polyethylene ball family; volume scaling. Video: nectar tips the hive faster. |
| Flower scoring height | 17 in (AndyMark 17" pipes) | Stack height of pollen (2.8") + nectar (3.6") cannot exceed this. |
| Robot skill bands | starter → elite | Typical FTC cycle times, not championship-only fantasy. |

If FIRST later publishes a tip-mass or a field-tour measurement, change `--tip-mass`
and re-run. Strategy *ranking* is more trustworthy than absolute point totals.

## What “reasonable robots” means

FTC robots start in an 18-inch cube and expand to 18×24×29. The CELL opening is
large (~20×14 in) so launching is easier than dunking into a 4 in FLOWER hole,
especially with 3.6 in NECTAR. Intakes that work on foam tiles and corners are
harder than they look — that is why `starter` accuracy is poor and cycle times
are long.

Defense, fouls, and broken robots are **not** fully modeled. Friendly defense
will make hive cycling slightly worse and parking slightly harder; it should not
flip “flowers-only is better than hive cycling” unless tip mass is far off.
