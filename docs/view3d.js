/* 3D replay of a BIOBUZZ match. Same frames as the 2D map; this is only a camera. */
import * as THREE from "three";
import { OrbitControls } from "./vendor/OrbitControls.js";

const FIELD = 144;
const HALF = FIELD / 2;
const WALL_H = 12;
const POLLEN_R = 1.4;
const NECTAR_R = 1.8;
const FLOWER_H = 21.5;
const FLOWER_POS = [
  [72, 10],
  [10, 72],
  [72, 134],
  [134, 72],
];
const COL = {
  pollen: 0xf2c14e,
  red: 0xe53935,
  blue: 0x1e88e5,
  tileA: 0xd9cbb3,
  tileB: 0xcbbda3,
  wall: 0x3a3a3a,
  metal: 0x2a2a2a,
  stem: 0x2e7d32,
  leaf: 0x81c784,
};

function wx(x) { return x - HALF; }
function wz(y) { return y - HALF; }
function ballColor(k, c) {
  if (k === 0) return COL.pollen;
  return c === 1 ? COL.red : COL.blue;
}
function ballR(k) { return k === 0 ? POLLEN_R : NECTAR_R; }

function make() {
  const canvas = document.getElementById("c3d");
  if (!canvas) return null;
  let renderer;
  try {
    renderer = new THREE.WebGLRenderer({ canvas: canvas, antialias: true, alpha: false });
  } catch (err) {
    return null;
  }
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.setSize(canvas.width, canvas.height, false);
  renderer.setClearColor(0x1a140c, 1);
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;

  const scene = new THREE.Scene();
  scene.fog = new THREE.Fog(0x1a140c, 180, 420);

  const camera = new THREE.PerspectiveCamera(42, canvas.width / canvas.height, 1, 800);
  camera.position.set(-90, 95, 150);

  const controls = new OrbitControls(camera, canvas);
  controls.target.set(0, 8, 0);
  controls.enableDamping = true;
  controls.dampingFactor = 0.08;
  controls.maxPolarAngle = Math.PI * 0.48;
  controls.minDistance = 40;
  controls.maxDistance = 280;
  controls.update();

  scene.add(new THREE.HemisphereLight(0xfff4dc, 0x3d2a16, 0.85));
  const sun = new THREE.DirectionalLight(0xfff0d0, 1.05);
  sun.position.set(-40, 140, 80);
  sun.castShadow = true;
  sun.shadow.mapSize.set(1024, 1024);
  sun.shadow.camera.left = -100;
  sun.shadow.camera.right = 100;
  sun.shadow.camera.top = 100;
  sun.shadow.camera.bottom = -100;
  scene.add(sun);
  scene.add(new THREE.AmbientLight(0x404040, 0.35));

  const field = new THREE.Group();
  scene.add(field);

  const tileGeo = new THREE.BoxGeometry(23.6, 0.6, 23.6);
  for (let i = 0; i < 6; i++) {
    for (let j = 0; j < 6; j++) {
      const mat = new THREE.MeshLambertMaterial({
        color: (i + j) % 2 === 0 ? COL.tileA : COL.tileB,
      });
      const tile = new THREE.Mesh(tileGeo, mat);
      tile.position.set(wx(i * 24 + 12), 0.3, wz(j * 24 + 12));
      tile.receiveShadow = true;
      field.add(tile);
    }
  }

  function wall(x, y, w, d, color) {
    const mesh = new THREE.Mesh(
      new THREE.BoxGeometry(w, WALL_H, d),
      new THREE.MeshLambertMaterial({ color: color })
    );
    mesh.position.set(wx(x + w / 2), WALL_H / 2, wz(y + d / 2));
    mesh.castShadow = true;
    mesh.receiveShadow = true;
    field.add(mesh);
  }
  wall(-1.2, 0, 1.2, FIELD, 0x8d2f2f);
  wall(FIELD, 0, 1.2, FIELD, 0x1a4e86);
  wall(0, -1.2, FIELD, 1.2, 0x4a4a4a);
  wall(0, FIELD, FIELD, 1.2, 0x4a4a4a);

  function zone(x, y, w, h, color) {
    const mesh = new THREE.Mesh(
      new THREE.BoxGeometry(w, 0.4, h),
      new THREE.MeshLambertMaterial({ color: color, transparent: true, opacity: 0.55 })
    );
    mesh.position.set(wx(x + w / 2), 0.75, wz(y + h / 2));
    field.add(mesh);
  }
  zone(0, 0, 23, 11, 0xe53935);
  zone(121, 0, 23, 11, 0x1e88e5);
  zone(0, 142, 23, 2, 0xe53935);
  zone(121, 142, 23, 2, 0x1e88e5);

  const flowers = FLOWER_POS.map((p) => {
    const g = new THREE.Group();
    const stem = new THREE.Mesh(
      new THREE.CylinderGeometry(2.4, 2.8, FLOWER_H, 12),
      new THREE.MeshLambertMaterial({ color: COL.stem })
    );
    stem.position.y = FLOWER_H / 2;
    stem.castShadow = true;
    g.add(stem);
    const rim = new THREE.Mesh(
      new THREE.TorusGeometry(2.6, 0.45, 8, 16),
      new THREE.MeshLambertMaterial({ color: COL.leaf })
    );
    rim.rotation.x = Math.PI / 2;
    rim.position.y = FLOWER_H;
    g.add(rim);
    g.position.set(wx(p[0]), 0, wz(p[1]));
    field.add(g);
    return g;
  });

  function makeHive(color, xOff) {
    const g = new THREE.Group();
    const stand = new THREE.Mesh(
      new THREE.BoxGeometry(8, 10, 8),
      new THREE.MeshLambertMaterial({ color: COL.metal })
    );
    stand.position.y = 5;
    g.add(stand);
    const beam = new THREE.Group();
    beam.position.y = 11;
    const bar = new THREE.Mesh(
      new THREE.BoxGeometry(36, 3, 10),
      new THREE.MeshLambertMaterial({ color: color })
    );
    bar.castShadow = true;
    beam.add(bar);
    [-12, 12].forEach((ox) => {
      const cell = new THREE.Mesh(
        new THREE.BoxGeometry(12, 8, 12),
        new THREE.MeshLambertMaterial({ color: 0x111111, transparent: true, opacity: 0.55 })
      );
      cell.position.set(ox, 5.5, 0);
      beam.add(cell);
    });
    g.add(beam);
    g.position.set(xOff, 0, 0);
    field.add(g);
    return { group: g, beam: beam };
  }
  const hives = {
    red: makeHive(COL.red, -16),
    blue: makeHive(COL.blue, 16),
  };

  const robotGeo = new THREE.BoxGeometry(16, 12, 16);
  const robots = [0, 1, 2, 3].map(() => {
    const g = new THREE.Group();
    const body = new THREE.Mesh(robotGeo, new THREE.MeshLambertMaterial({ color: COL.red }));
    body.position.y = 6;
    body.castShadow = true;
    g.add(body);
    g.userData.body = body;
    g.visible = false;
    field.add(g);
    return g;
  });

  const sphereGeo = new THREE.SphereGeometry(1, 12, 10);
  const balls = [];
  function getBall() {
    for (let i = 0; i < balls.length; i++) {
      if (!balls[i].userData.used) return balls[i];
    }
    const mesh = new THREE.Mesh(sphereGeo, new THREE.MeshLambertMaterial({ color: COL.pollen }));
    mesh.castShadow = true;
    mesh.userData.used = false;
    field.add(mesh);
    balls.push(mesh);
    return mesh;
  }
  function beginBalls() {
    for (let i = 0; i < balls.length; i++) {
      balls[i].userData.used = false;
      balls[i].visible = false;
    }
  }
  function placeBall(k, c, x, y, z) {
    const m = getBall();
    m.userData.used = true;
    m.visible = true;
    m.material.color.setHex(ballColor(k, c));
    const r = ballR(k);
    m.scale.setScalar(r);
    m.position.set(x, y, z);
    return m;
  }

  const lastRobot = [{ x: 0, y: 0 }, { x: 0, y: 0 }, { x: 0, y: 0 }, { x: 0, y: 0 }];

  function setFrame(frame) {
    if (!frame) return;
    beginBalls();
    (frame.robots || []).forEach((r, i) => {
      const g = robots[i];
      if (!g) return;
      g.visible = true;
      g.position.set(wx(r.x), 0, wz(r.y));
      g.userData.body.material.color.setHex(r.a === "red" ? COL.red : COL.blue);
      const prev = lastRobot[i];
      const dx = r.x - prev.x, dy = r.y - prev.y;
      if (dx * dx + dy * dy > 0.8) g.rotation.y = Math.atan2(dx, dy);
      lastRobot[i].x = r.x;
      lastRobot[i].y = r.y;
      (r.inv || []).forEach((k, n) => {
        placeBall(k === 0 ? 0 : 1, k, wx(r.x) - 4 + n * 3, 14, wz(r.y));
      });
    });
    for (let i = (frame.robots || []).length; i < robots.length; i++) robots[i].visible = false;

    (frame.balls || []).forEach((e) => {
      placeBall(e.k, e.c, wx(e.x), ballR(e.k), wz(e.y));
    });

    (frame.flowers || []).forEach((stack, fi) => {
      const p = FLOWER_POS[fi];
      let h = 4;
      stack.forEach((el) => {
        const r = ballR(el[0]);
        placeBall(el[0], el[1], wx(p[0]), h + r, wz(p[1]));
        h += r * 2;
      });
    });

    ["red", "blue"].forEach((c) => {
      const h = frame.hives && frame.hives[c];
      if (!h) return;
      const hive = hives[c];
      const base = h.up === "a" ? -0.42 : 0.42;
      hive.beam.rotation.z = h.tipping ? (h.up === "a" ? -1.05 : 1.05) : base;
      hive.beam.updateWorldMatrix(true, true);
      const cell = h.cell || [];
      cell.forEach((el, i) => {
        const side = i % 2 === 0 ? -10 : 10;
        const row = Math.floor(i / 2);
        const local = new THREE.Vector3(side, 5.5 + row * 3.1, 0);
        hive.beam.localToWorld(local);
        placeBall(el[0], el[1], local.x, local.y, local.z);
      });
    });
  }

  function resetCamera() {
    camera.position.set(-90, 95, 150);
    controls.target.set(0, 8, 0);
    controls.update();
  }

  let running = true;
  function loop() {
    if (!running) return;
    requestAnimationFrame(loop);
    if (!canvas.hidden) {
      controls.update();
      renderer.render(scene, camera);
    }
  }
  requestAnimationFrame(loop);

  function setVisible(on) {
    canvas.hidden = !on;
    if (on) {
      renderer.setSize(canvas.width, canvas.height, false);
      controls.update();
    }
  }

  return {
    setFrame: setFrame,
    setVisible: setVisible,
    resetCamera: resetCamera,
    ok: true,
  };
}

let api = null;
try {
  api = make();
} catch (err) {
  console.warn("3D view unavailable", err);
}
window.Biobuzz3D = api && api.ok ? api : { ok: false, setFrame: function () {}, setVisible: function () {}, resetCamera: function () {} };
