(function () {
  const B = window.Biobuzz;
  const canvas = document.getElementById("c");
  const ctx = canvas.getContext("2d");
  const FIELD = 144;
  const M = 24;
  const S = (canvas.width - 2 * M) / FIELD;

  function px(x, y) {
    return [M + x * S, canvas.height - (M + y * S)];
  }

  function fillRectIn(x, y, w, h, color) {
    const a = px(x, y + h);
    ctx.fillStyle = color;
    ctx.fillRect(a[0], a[1], w * S, h * S);
  }

  function drawField() {
    ctx.fillStyle = "#1a140c";
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    for (let i = 0; i < 6; i++) {
      for (let j = 0; j < 6; j++) {
        ctx.fillStyle = (i + j) % 2 === 0 ? "#d9cbb3" : "#cbbda3";
        const a = px(i * 24, (j + 1) * 24);
        ctx.fillRect(M + i * 24 * S, M + (5 - j) * 24 * S, 24 * S - 1, 24 * S - 1);
      }
    }
    ctx.strokeStyle = "#333";
    ctx.lineWidth = 8;
    ctx.strokeRect(M, M, FIELD * S, FIELD * S);
    fillRectIn(0, 0, 23, 11, "rgba(229,57,53,0.28)");
    fillRectIn(121, 0, 23, 11, "rgba(30,136,229,0.28)");
    fillRectIn(0, 142, 23, 2, "rgba(229,57,53,0.5)");
    fillRectIn(121, 142, 23, 2, "rgba(30,136,229,0.5)");
    fillRectIn(B.HIVE.x, B.HIVE.y, B.HIVE.w, B.HIVE.d, "rgba(40,40,40,0.88)");
    const legend = [
      ["#f2c14e", "POLLEN (anyone)"],
      ["#e53935", "red NECTAR (red only)"],
      ["#1e88e5", "blue NECTAR (blue only)"],
    ];
    legend.forEach((row, i) => {
      ctx.beginPath();
      ctx.fillStyle = row[0];
      ctx.arc(M + 10, canvas.height - 14, 5, 0, Math.PI * 2);
      ctx.fill();
      ctx.fillStyle = "#d9cbb3";
      ctx.font = "11px sans-serif";
      ctx.fillText(row[1], M + 20, canvas.height - 10);
      ctx.translate(150, 0);
    });
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    B.FLOWERS.forEach((f) => {
      const p = px(f.x, f.y);
      ctx.beginPath();
      ctx.fillStyle = "#2e7d32";
      ctx.arc(p[0], p[1], 9, 0, Math.PI * 2);
      ctx.fill();
    });
  }

  function draw(frame) {
    drawField();
    if (!frame) return;
    ["red", "blue"].forEach((c, i) => {
      const h = frame.hives[c];
      ctx.save();
      const p = px(72 + (i === 0 ? -10 : 10), 72);
      ctx.translate(p[0], p[1]);
      const tilt = h.up === "a" ? -0.45 : 0.45;
      ctx.rotate(h.tipping ? tilt * 0.35 : tilt);
      ctx.fillStyle = c === "red" ? "#e53935" : "#1e88e5";
      ctx.fillRect(-30, -11, 60, 22);
      ctx.fillStyle = "#222";
      ctx.fillRect(-16, -20, 32, 14);
      ctx.fillStyle = "#fff";
      ctx.font = "11px sans-serif";
      ctx.fillText("TIPS " + h.tips, -16, 5);
      ctx.restore();
    });
    (frame.balls || []).forEach((e) => {
      const p = px(e.x, e.y);
      ctx.beginPath();
      ctx.fillStyle = e.k === 0 ? "#f2c14e" : e.c === 1 ? "#e53935" : "#1e88e5";
      ctx.arc(p[0], p[1], e.k === 0 ? 4 : 5.2, 0, Math.PI * 2);
      ctx.fill();
    });
    frame.robots.forEach((r) => {
      const p = px(r.x, r.y);
      ctx.fillStyle = r.a === "red" ? "#e53935" : "#1e88e5";
      ctx.fillRect(p[0] - 10, p[1] - 10, 20, 20);
      ctx.strokeStyle = "#111";
      ctx.strokeRect(p[0] - 10, p[1] - 10, 20, 20);
      (r.inv || []).forEach((k, i) => {
        ctx.beginPath();
        ctx.fillStyle = k === 0 ? "#f2c14e" : k === 1 ? "#e53935" : "#1e88e5";
        ctx.arc(p[0] - 7 + i * 5, p[1] + 14, 3, 0, Math.PI * 2);
        ctx.fill();
      });
      ctx.fillStyle = "#fff";
      ctx.font = "11px sans-serif";
      ctx.fillText(String(r.n), p[0] - 4, p[1] + 4);
    });
    const fpos = [[72, 10], [10, 72], [72, 134], [134, 72]];
    frame.flowers.forEach((stack, i) => {
      const p = px(fpos[i][0], fpos[i][1]);
      stack.forEach((el, k) => {
        ctx.beginPath();
        ctx.fillStyle = el[0] === 0 ? "#f2c14e" : el[1] === 1 ? "#e53935" : "#1e88e5";
        ctx.arc(p[0], p[1] - 8 - k * 6, 4, 0, Math.PI * 2);
        ctx.fill();
      });
    });
  }

  drawField();

  const selR = document.getElementById("redStrat");
  const selB = document.getElementById("blueStrat");
  Object.keys(B.STRATEGIES).forEach((k) => {
    const s = B.STRATEGIES[k];
    [selR, selB].forEach((sel, i) => {
      const o = document.createElement("option");
      o.value = k; o.textContent = s.title;
      if ((i === 0 && k === "hive_cycle") || (i === 1 && k === "flower_focus")) o.selected = true;
      sel.appendChild(o);
    });
  });
  document.getElementById("legend").innerHTML = Object.keys(B.STRATEGIES).map((k) =>
    '<span><i class="swatch ' + k + '"></i>' + B.STRATEGIES[k].title + "</span>"
  ).join("");

  function pct(id) { return (+document.getElementById(id).value) / 100; }
  function intake(id) { return (+document.getElementById(id).value) / 10; }

  function bind(id, vid, fmt) {
    const el = document.getElementById(id);
    const lab = document.getElementById(vid);
    function sync() { lab.textContent = fmt(el.value); }
    el.addEventListener("input", sync); sync();
  }
  bind("hiveAcc", "vHive", (v) => v + "%");
  bind("flowerAcc", "vFlower", (v) => v + "%");
  bind("intakeS", "vIntake", (v) => (v / 10).toFixed(1) + "s");
  bind("intakeRel", "vRel", (v) => v + "%");
  bind("hiveAccB", "vHiveB", (v) => v + "%");
  bind("flowerAccB", "vFlowerB", (v) => v + "%");
  bind("intakeSB", "vIntakeB", (v) => (v / 10).toFixed(1) + "s");

  document.getElementById("sameCaps").addEventListener("change", (e) => {
    document.getElementById("blueCaps").hidden = e.target.checked;
  });

  function redCaps() {
    return {
      hive_accuracy: pct("hiveAcc"),
      flower_accuracy: pct("flowerAcc"),
      intake_s: intake("intakeS"),
      intake_reliability: pct("intakeRel"),
    };
  }
  function blueCaps() {
    if (document.getElementById("sameCaps").checked) return redCaps();
    return {
      hive_accuracy: pct("hiveAccB"),
      flower_accuracy: pct("flowerAccB"),
      intake_s: intake("intakeSB"),
      intake_reliability: pct("intakeRel"),
    };
  }

  let replay = null, idx = 0, playing = false, acc = 0;

  function showFrame(i) {
    if (!replay || !replay.frames.length) return;
    idx = Math.max(0, Math.min(replay.frames.length - 1, i));
    const f = replay.frames[idx];
    draw(f);
    document.getElementById("rs").textContent = f.score.red;
    document.getElementById("bs").textContent = f.score.blue;
    const n = f.nectar || { red: { grab: 0, held: 0, cell: 3, flower: 0, off: 5 }, blue: { grab: 0, held: 0, cell: 3, flower: 0, off: 5 } };
    document.getElementById("clock").textContent =
      f.phase.toUpperCase() + "  t=" + f.t.toFixed(1) + "s   frame " + idx + "/" + (replay.frames.length - 1);
    document.getElementById("nectarHud").innerHTML =
      '<span class="pollen-n">POLLEN — anyone</span>' +
      '<span class="red-n">Red nectar: ' + n.red.grab + " on floor · " + n.red.held + " held · " +
        n.red.cell + " in hive · " + n.red.flower + " in flowers · " + n.red.off + " still off-field</span>" +
      '<span class="blue-n">Blue nectar: ' + n.blue.grab + " on floor · " + n.blue.held + " held · " +
        n.blue.cell + " in hive · " + n.blue.flower + " in flowers · " + n.blue.off + " still off-field</span>";
    const ev = replay.events.filter((e) => e.t <= f.t + 0.05).slice(-8).reverse();
    document.getElementById("log").innerHTML = ev.map((e) => "<div>" + e.t.toFixed(1) + "s — " + e.text + "</div>").join("");
  }

  function loop() {
    if (playing && replay) {
      acc++;
      if (acc % 2 === 0) {
        showFrame(idx + 1);
        if (idx >= replay.frames.length - 1) playing = false;
      }
    }
    requestAnimationFrame(loop);
  }
  requestAnimationFrame(loop);

  function setBusy(on, msg) {
    ["btnWatch", "btnMany", "btnSweep"].forEach((id) => { document.getElementById(id).disabled = on; });
    document.getElementById("prog").hidden = !on;
    document.getElementById("status").textContent = msg || "";
  }
  function prog(n, d) {
    document.getElementById("progBar").style.width = (100 * n / Math.max(1, d)) + "%";
    document.getElementById("status").textContent = "Running " + n + " / " + d;
  }

  document.getElementById("btnWatch").onclick = function () {
    document.getElementById("rsub").textContent = B.STRATEGIES[selR.value].title;
    document.getElementById("bsub").textContent = B.STRATEGIES[selB.value].title;
    replay = B.playMatch({
      redCaps: redCaps(),
      blueCaps: blueCaps(),
      redStrategy: selR.value,
      blueStrategy: selB.value,
      seed: (Math.random() * 1e9) | 0,
      record: true,
    });
    playing = true;
    showFrame(0);
    const s = replay.score;
    document.getElementById("status").textContent =
      "Winner: " + s.winner.toUpperCase() + "  RP red " + s.red.rpTotal + " / blue " + s.blue.rpTotal;
  };

  function yieldThen(fn) {
    setTimeout(fn, 20);
  }

  document.getElementById("btnMany").onclick = function () {
    setBusy(true, "Simulating…");
    yieldThen(function () {
      const summary = B.runMany({
        matches: 400,
        caps: redCaps(),
        strategies: Object.keys(B.STRATEGIES),
        seed: 7,
      }, prog);
      setBusy(false, "Finished " + summary.n + " matches.");
      const best = summary.ranked[0];
      const cards = summary.ranked.map((k, i) => {
        const t = summary.table[k];
        const s = B.STRATEGIES[k];
        return '<div class="card' + (i === 0 ? " best" : "") + '"><h3>' + s.title + "</h3><p>" +
          (t.winRate * 100).toFixed(0) + "% wins · " + t.pts.toFixed(0) + " pts · " +
          t.tips.toFixed(1) + " tips · " + t.rp.toFixed(2) + " RP</p><p>" + s.blurb + "</p></div>";
      }).join("");
      document.getElementById("recCards").innerHTML = cards;
      let html = "<table><thead><tr><th>Strategy</th><th>Win %</th><th>Avg points</th><th>Tips</th><th>RP</th><th>Owned flower el.</th></tr></thead><tbody>";
      summary.ranked.forEach((k) => {
        const t = summary.table[k];
        html += "<tr><td>" + B.STRATEGIES[k].title + "</td><td>" + (t.winRate * 100).toFixed(1) +
          "</td><td>" + t.pts.toFixed(1) + "</td><td>" + t.tips.toFixed(2) + "</td><td>" +
          t.rp.toFixed(2) + "</td><td>" + t.owned.toFixed(1) + "</td></tr>";
      });
      html += "</tbody></table>";
      document.getElementById("manyTable").innerHTML = html;
      document.getElementById("status").textContent =
        "Best with these miss/pickup numbers: " + B.STRATEGIES[best].title +
        " (" + (summary.table[best].winRate * 100).toFixed(0) + "% wins).";
    });
  };

  function paintHeat(el, cells, xKey, yKey, xGrid, yGrid, xFmt, yFmt) {
    el.style.gridTemplateColumns = "90px repeat(" + xGrid.length + ", 1fr)";
    let html = "<div></div>" + xGrid.map((x) => "<div class='lab'>" + xFmt(x) + "</div>").join("");
    yGrid.forEach((y) => {
      html += "<div class='lab'>" + yFmt(y) + "</div>";
      xGrid.forEach((x) => {
        const cell = cells.find((c) => c[xKey] === x && c[yKey] === y);
        if (!cell) { html += "<div class='cell'></div>"; return; }
        const t = B.STRATEGIES[cell.best].title;
        const wr = (cell.table[cell.best].winRate * 100).toFixed(0);
        html += "<div class='cell " + cell.best + "'>" + t + "<br>" + wr + "% · " +
          cell.table[cell.best].pts.toFixed(0) + " pts</div>";
      });
    });
    el.innerHTML = html;
  }

  document.getElementById("btnSweep").onclick = function () {
    setBusy(true, "Mapping strategies… this may take 20–40s");
    yieldThen(function () {
      const data = B.sweep({ reps: 1 }, prog);
      paintHeat(document.getElementById("heatIntake"), data.hiveIntake, "hive", "intake",
        data.hiveGrid, data.intakeGrid, (x) => Math.round(x * 100) + "% hive", (y) => y.toFixed(1) + "s pickup");
      paintHeat(document.getElementById("heatFlower"), data.hiveFlower, "hive", "flower",
        data.hiveGrid, data.flowerGrid, (x) => Math.round(x * 100) + "% hive", (y) => Math.round(y * 100) + "% flower");
      setBusy(false, "Map complete. Read the highlighted strategy in each cell.");
    });
  };
})();
