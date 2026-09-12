"""Self-contained HTML report + match replay (no extra Python deps)."""

from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any

from .strategies import STRATEGIES
from .skills import SKILL_HELP


def _esc(s: Any) -> str:
    return html.escape(str(s))


def write_replay(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(REPLAY_HTML.replace("/*__PAYLOAD__*/", json.dumps(payload)), encoding="utf-8")


def write_report(path: Path, summary: dict[str, Any], physics: dict[str, Any], notes: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    body = _report_body(summary, physics, notes)
    path.write_text(REPORT_SHELL.replace("<!--BODY-->", body), encoding="utf-8")


def _bar(value: float, vmax: float, color: str) -> str:
    pct = 0 if vmax <= 0 else max(0, min(100, 100 * value / vmax))
    return (
        f'<div class="barwrap"><div class="bar" style="width:{pct:.1f}%;background:{color}"></div>'
        f'<span>{value:.2f}</span></div>'
    )


def _report_body(summary: dict[str, Any], physics: dict[str, Any], notes: str) -> str:
    rec_html = []
    for rec in summary["recommendations"]:
        skill = rec["skill"]
        ranked = rec["ranked"]
        if not ranked or ranked[0]["n"] == 0:
            continue
        top = ranked[0]
        rec_html.append(
            f"<div class='card'><h3>{_esc(skill)}</h3>"
            f"<p class='muted'>{_esc(SKILL_HELP.get(skill, ''))}</p>"
            f"<p><strong>Best strategy vs the field:</strong> "
            f"{_esc(STRATEGIES[top['strategy']].title)} "
            f"({_esc(top['strategy'])})</p>"
            f"<p>Win rate <strong>{top['win_rate']*100:.1f}%</strong> · "
            f"avg points <strong>{top['avg_points']:.0f}</strong> · "
            f"avg RP <strong>{top['avg_rp']:.2f}</strong> · "
            f"avg tips <strong>{top['avg_tips']:.1f}</strong></p>"
            f"<p class='muted'>{_esc(STRATEGIES[top['strategy']].blurb)}</p></div>"
        )

    tables = []
    for skill, rows in summary["by_skill"].items():
        vmax_pts = max((v["avg_points"] for v in rows.values()), default=1) or 1
        trs = []
        ordered = sorted(rows.items(), key=lambda kv: kv[1]["win_rate"], reverse=True)
        for name, v in ordered:
            if v["n"] == 0:
                continue
            trs.append(
                "<tr>"
                f"<td><strong>{_esc(STRATEGIES[name].title)}</strong><br>"
                f"<span class='muted'>{_esc(name)}</span></td>"
                f"<td>{_bar(v['win_rate']*100, 100, '#2e7d32')}</td>"
                f"<td>{_bar(v['avg_points'], vmax_pts, '#1565c0')}</td>"
                f"<td>{v['avg_tips']:.2f}</td>"
                f"<td>{v['avg_rp']:.2f}</td>"
                f"<td>{v['avg_owned_elements']:.1f}</td>"
                f"<td>{v['avg_bottom_nectar']:.2f}</td>"
                f"<td>{v['avg_auto_tips']:.2f}</td>"
                f"<td>{int(v['n'])}</td>"
                "</tr>"
            )
        tables.append(
            f"<h3>Skill band: {_esc(skill)}</h3>"
            "<table><thead><tr>"
            "<th>Strategy</th><th>Win %</th><th>Avg points</th><th>Tips</th>"
            "<th>RP</th><th>Owned flower el.</th><th>Bottom nectar</th>"
            "<th>AUTO tips</th><th>n</th>"
            "</tr></thead><tbody>"
            + "".join(trs)
            + "</tbody></table>"
        )

    mats = []
    for skill, mat in summary["matchup_winrate"].items():
        names = summary["strategies"]
        head = "<th></th>" + "".join(
            f"<th>{_esc(STRATEGIES[n].title)}</th>" for n in names
        )
        body = []
        for sa in names:
            tds = [f"<th>{_esc(STRATEGIES[sa].title)}</th>"]
            for sb in names:
                wr = mat[sa][sb]
                if wr == 0 and sa != sb:
                    bg = "#eee"
                else:
                    # 0 red -> 0.5 gray -> 1 green
                    g = int(30 + wr * 140)
                    r = int(180 - wr * 140)
                    bg = f"rgb({r},{g},70)"
                tds.append(f"<td style='background:{bg};color:#fff'>{wr*100:.0f}%</td>")
            body.append("<tr>" + "".join(tds) + "</tr>")
        mats.append(
            f"<h3>Win rate (row vs column) — {_esc(skill)}</h3>"
            f"<table class='matrix'><thead><tr>{head}</tr></thead>"
            f"<tbody>{''.join(body)}</tbody></table>"
        )

    strat_cards = "".join(
        f"<div class='card slim'><h4>{_esc(s.title)}</h4><p>{_esc(s.blurb)}</p>"
        f"<p class='muted'>id: <code>{_esc(s.name)}</code></p></div>"
        for s in STRATEGIES.values()
    )

    phys_rows = "".join(
        f"<tr><td>{_esc(k)}</td><td><code>{_esc(v)}</code></td></tr>"
        for k, v in physics.items()
    )

    return f"""
<h1>BIOBUZZ strategy report</h1>
<p class='lede'>Monte Carlo of <strong>{summary['n_matches']}</strong> simulated matches
using Competition Manual V1 scoring. Hive-tip <em>mass</em> is an assumption
(see physics table) because the manual does not publish how many POLLEN/NECTAR
tip a CELL.</p>

<h2>What should we focus on?</h2>
<div class='grid'>{''.join(rec_html)}</div>

<h2>Headline</h2>
<p>{_esc(notes)}</p>

<h2>Strategy catalog</h2>
<div class='grid'>{strat_cards}</div>

<h2>Results by skill band</h2>
{''.join(tables)}

<h2>Matchup matrices</h2>
<p class='muted'>Each cell is how often the <em>row</em> strategy beats the <em>column</em>
strategy at that skill. Ties count as not a win.</p>
{''.join(mats)}

<h2>Physics assumptions (not in the manual)</h2>
<table><tbody>{phys_rows}</tbody></table>
<p class='muted'>Re-run with <code>--tip-mass</code> to test sensitivity. Nectar mass ratio
defaults to volume scaling of the two Gopher balls (3.6 / 2.8)<sup>3</sup> ≈ 2.13.</p>
"""


REPORT_SHELL = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>BIOBUZZ strategy report</title>
<style>
:root { --bg:#f6f1e7; --ink:#1b1b1b; --red:#c62828; --blue:#1565c0; --y:#f2c14e; }
body { font-family: "Trebuchet MS", "Segoe UI", sans-serif; margin:0; background:var(--bg); color:var(--ink); }
main { max-width: 1100px; margin: 0 auto; padding: 28px 20px 80px; }
h1 { font-size: 2rem; margin: 0 0 8px; }
h2 { margin-top: 2.2rem; border-bottom: 3px solid #1b1b1b; padding-bottom: 4px; }
h3 { margin-top: 1.6rem; }
.lede { font-size: 1.05rem; max-width: 70ch; }
.muted { color:#555; font-size: 0.92rem; }
.grid { display:grid; grid-template-columns: repeat(auto-fit, minmax(240px,1fr)); gap:12px; }
.card { background:#fff; border:2px solid #1b1b1b; border-radius:12px; padding:14px 16px; }
.card.slim { padding:12px; }
table { border-collapse: collapse; width:100%; background:#fff; margin: 8px 0 24px; font-size: 0.92rem; }
th, td { border:1px solid #ccc; padding:6px 8px; text-align:left; vertical-align:middle; }
th { background:#1b1b1b; color:#fff; }
.matrix td, .matrix th { text-align:center; font-size:0.8rem; }
.barwrap { display:flex; align-items:center; gap:6px; min-width:110px; }
.bar { height:10px; border-radius:6px; background:#333; }
code { background:#eee; padding:1px 4px; border-radius:4px; }
</style>
</head>
<body><main>
<!--BODY-->
<p class="muted">Generated by biobuzz-sim. Open any file in <code>replays/</code> to watch a match.</p>
</main></body></html>
"""


REPLAY_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>BIOBUZZ match replay</title>
<style>
:root { --red:#d32f2f; --blue:#1976d2; --pollen:#f2c14e; --tile:#e8dcc8; }
html,body { margin:0; height:100%; background:#111; color:#f3f3f3; font-family:"Segoe UI",sans-serif; }
#app { display:grid; grid-template-columns: minmax(360px, 1fr) 340px; height:100%; }
#stage { display:flex; align-items:center; justify-content:center; background:#1a1a1a; }
canvas { background:#0e0e0e; max-width:100%; max-height:100%; }
#side { padding:16px 18px; overflow:auto; background:#181818; border-left:1px solid #333; }
h1 { font-size:1.15rem; margin:0 0 8px; }
.meta { font-size:0.85rem; color:#bbb; }
.score { display:flex; gap:10px; margin:12px 0; }
.score div { flex:1; padding:10px; border-radius:10px; text-align:center; }
.score .r { background:#4a1515; }
.score .b { background:#102a4a; }
.score strong { display:block; font-size:1.8rem; }
button { background:#eee; color:#111; border:0; border-radius:8px; padding:8px 12px; margin-right:6px; cursor:pointer; }
input[type=range] { width:100%; }
.log { font-size:0.8rem; max-height:220px; overflow:auto; background:#111; padding:8px; border-radius:8px; }
.log div { margin:2px 0; color:#ccc; }
.legend span { display:inline-block; width:10px; height:10px; border-radius:50%; margin-right:4px; }
</style>
</head>
<body>
<div id="app">
  <div id="stage"><canvas id="c" width="900" height="900"></canvas></div>
  <aside id="side">
    <h1>BIOBUZZ replay</h1>
    <div class="meta" id="meta"></div>
    <div class="score">
      <div class="r">RED<strong id="rs">0</strong><span id="rsub"></span></div>
      <div class="b">BLUE<strong id="bs">0</strong><span id="bsub"></span></div>
    </div>
    <div>
      <button id="play">Pause</button>
      <button id="slower">− speed</button>
      <button id="faster">+ speed</button>
    </div>
    <p class="meta" id="clock"></p>
    <input type="range" id="scrub" min="0" max="1" step="1" value="0"/>
    <p class="legend meta">
      <span style="background:#f2c14e"></span>Pollen
      <span style="background:#d32f2f"></span>Red nectar
      <span style="background:#1976d2"></span>Blue nectar
    </p>
    <h2 style="font-size:1rem">Events</h2>
    <div class="log" id="log"></div>
    <h2 style="font-size:1rem">Result</h2>
    <pre id="result" class="meta" style="white-space:pre-wrap"></pre>
  </aside>
</div>
<script>
const DATA = /*__PAYLOAD__*/;
const canvas = document.getElementById('c');
const ctx = canvas.getContext('2d');
const FIELD = 144;
const M = 30;
const S = (canvas.width - 2*M) / FIELD;
let idx = 0;
let playing = true;
let speed = 1; // frames skipped-ish via dt of 0.2s recorded

function px(x,y){ return [M + x*S, canvas.height - (M + y*S)]; }

function drawField(){
  ctx.fillStyle = '#24180f';
  ctx.fillRect(0,0,canvas.width,canvas.height);
  // tiles 6x6
  const tile = 24*S;
  for(let i=0;i<6;i++){
    for(let j=0;j<6;j++){
      ctx.fillStyle = ((i+j)%2===0) ? '#d9cbb3' : '#cbbda3';
      const [x,y] = px(i*24, (j+1)*24);
      ctx.fillRect(M + i*tile, M + (5-j)*tile, tile-1, tile-1);
    }
  }
  // walls
  ctx.strokeStyle = '#333';
  ctx.lineWidth = 10;
  const [x0,y0] = px(0,0);
  ctx.strokeRect(M, M, FIELD*S, FIELD*S);
  // loading zones
  ctx.fillStyle = 'rgba(211,47,47,0.25)';
  let p = px(0,0); ctx.fillRect(M, canvas.height-M-11*S, 23*S, 11*S);
  ctx.fillStyle = 'rgba(25,118,210,0.25)';
  ctx.fillRect(M+(144-23)*S, canvas.height-M-11*S, 23*S, 11*S);
  // gardens
  ctx.fillStyle = 'rgba(211,47,47,0.45)';
  ctx.fillRect(M, M, 23*S, 2*S);
  ctx.fillStyle = 'rgba(25,118,210,0.45)';
  ctx.fillRect(M+(144-23)*S, M, 23*S, 2*S);
  // hive frame
  ctx.fillStyle = 'rgba(40,40,40,0.85)';
  const hw=49.46, hd=38.95;
  const [hx,hy] = px((144-hw)/2, (144-hd)/2 + hd);
  ctx.fillRect(hx, hy, hw*S, hd*S);
  // flowers
  const flowers=[[72,0],[0,72],[72,144],[144,72]];
  flowers.forEach(([x,y],i)=>{
    const [fx,fy]=px(x,y);
    ctx.beginPath();
    ctx.fillStyle='#2e7d32';
    ctx.arc(fx, fy, 10, 0, Math.PI*2);
    ctx.fill();
    ctx.strokeStyle='#1b5e20';
    ctx.lineWidth=3;
    ctx.stroke();
  });
}

function draw(frame){
  drawField();
  if(!frame) return;
  // hive cells
  const hx = 72, hy = 72;
  ['red','blue'].forEach((c,i)=>{
    const h = frame.hives[c];
    const col = c==='red' ? '#d32f2f' : '#1976d2';
    ctx.save();
    ctx.translate(...px(hx + (i===0?-10:10), hy));
    const tilt = h.up==='a' ? -0.45 : 0.45;
    ctx.rotate(h.tipping ? tilt*0.4 : tilt);
    ctx.fillStyle = col;
    ctx.fillRect(-28, -10, 56, 20);
    ctx.fillStyle = '#222';
    ctx.fillRect(-18, -18, 36, 16);
    ctx.fillStyle = '#fff';
    ctx.font = '12px sans-serif';
    ctx.fillText('TIPS '+h.tips, -18, 6);
    ctx.restore();
  });
  // elements
  for(const e of frame.elements){
    if(e.loc==='robot' || e.loc==='cell' || e.loc==='flower') continue;
    const [x,y]=px(e.x,e.y);
    ctx.beginPath();
    ctx.fillStyle = e.k===0 ? '#f2c14e' : (e.c===1 ? '#d32f2f' : '#1976d2');
    ctx.arc(x,y, e.k===0 ? 4.2 : 5.4, 0, Math.PI*2);
    ctx.fill();
    ctx.strokeStyle='#222';
    ctx.lineWidth=1;
    ctx.stroke();
  }
  // robots
  for(const r of frame.robots){
    const [x,y]=px(r.x,r.y);
    ctx.save();
    ctx.translate(x,y);
    ctx.fillStyle = r.alliance==='red' ? '#d32f2f' : '#1976d2';
    ctx.fillRect(-11,-11,22,22);
    ctx.strokeStyle='#111';
    ctx.lineWidth=2;
    ctx.strokeRect(-11,-11,22,22);
    ctx.fillStyle='#fff';
    ctx.font='11px sans-serif';
    ctx.fillText(String(r.n), -4, 4);
    ctx.restore();
  }
  // flower stacks
  const fpos=[[72,8],[8,72],[72,136],[136,72]];
  frame.flowers.forEach((stack,i)=>{
    const [fx,fy]=px(fpos[i][0], fpos[i][1]);
    stack.forEach((el,k)=>{
      ctx.beginPath();
      ctx.fillStyle = el[0]===0 ? '#f2c14e' : (el[1]===1 ? '#d32f2f' : '#1976d2');
      ctx.arc(fx, fy - 8 - k*7, 4, 0, Math.PI*2);
      ctx.fill();
    });
  });
}

function setFrame(i){
  idx = Math.max(0, Math.min(DATA.frames.length-1, i));
  const f = DATA.frames[idx];
  draw(f);
  document.getElementById('rs').textContent = f.score.red;
  document.getElementById('bs').textContent = f.score.blue;
  const t = f.t;
  const phase = f.phase.toUpperCase();
  const remain = f.phase==='auto' ? (30-t) : (150-t);
  document.getElementById('clock').textContent =
    phase + '  t=' + t.toFixed(1) + 's  remaining in period ≈ ' + Math.max(0,remain).toFixed(1) + 's  frame ' + idx;
  document.getElementById('scrub').value = idx;
  const log = document.getElementById('log');
  const ev = DATA.events.filter(e => e.t <= f.t + 0.05).slice(-12).reverse();
  log.innerHTML = ev.map(e => `<div>${e.t.toFixed(1)}s — ${e.text}</div>`).join('');
}

document.getElementById('meta').textContent =
  `RED ${DATA.meta.red_skill} / ${DATA.meta.red_strategy}  vs  BLUE ${DATA.meta.blue_skill} / ${DATA.meta.blue_strategy}   seed ${DATA.meta.seed}`;
document.getElementById('rsub').textContent = DATA.meta.red_strategy;
document.getElementById('bsub').textContent = DATA.meta.blue_strategy;
document.getElementById('result').textContent = JSON.stringify(DATA.result, null, 2);
document.getElementById('scrub').max = Math.max(0, DATA.frames.length-1);
document.getElementById('play').onclick = () => {
  playing = !playing;
  document.getElementById('play').textContent = playing ? 'Pause' : 'Play';
};
document.getElementById('faster').onclick = () => { speed = Math.min(8, speed+1); };
document.getElementById('slower').onclick = () => { speed = Math.max(1, speed-1); };
document.getElementById('scrub').oninput = (e) => { setFrame(+e.target.value); playing=false; document.getElementById('play').textContent='Play'; };

let acc = 0;
function loop(ts){
  if(playing){
    acc++;
    if(acc % (3) === 0){
      for(let k=0;k<speed;k++) setFrame(idx+1);
      if(idx >= DATA.frames.length-1){ playing=false; document.getElementById('play').textContent='Play'; }
    }
  }
  requestAnimationFrame(loop);
}
if(DATA.frames && DATA.frames.length){
  setFrame(0);
  requestAnimationFrame(loop);
} else {
  document.getElementById('meta').textContent += ' (no frames recorded)';
}
</script>
</body>
</html>
"""
