"""Self-contained offline HTML viewer: three.js r147 (vendored) + the GLB inlined (gzip+base64).

Works from a file:// URL or as a published page, no network. Touch: one finger orbits, two
fingers zoom/pan. ``?shot=1`` hides the controls (used for the PNG renders) and exposes
``window.viewer`` for automation.
"""
from __future__ import annotations

import base64
import gzip
import json
from pathlib import Path

VENDOR = Path(__file__).parent / "vendor"
SCRIPTS = ["three.min.js", "GLTFLoader.js", "OrbitControls.js", "RoomEnvironment.js"]


def build_html(glb_path, manifest: dict, metrics: dict, info: dict, out_path, title="Pack 5200") -> Path:
    glb = Path(glb_path).read_bytes()
    b64 = base64.b64encode(gzip.compress(glb, 9)).decode()
    vendor = "\n".join(f"<script>/* {s} */\n{(VENDOR / s).read_text()}\n</script>" for s in SCRIPTS)
    data = {"parts": manifest, "metrics": metrics, "info": info, "title": title}
    html = (TEMPLATE.replace("/*__VENDOR__*/", vendor)
            .replace("__GLB_B64__", b64)
            .replace("/*__DATA__*/null", json.dumps(data, default=_js))
            .replace("__TITLE__", title))
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html)
    return out_path


def _js(o):
    if hasattr(o, "tolist"):
        return o.tolist()
    return str(o)


TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no, viewport-fit=cover">
<title>__TITLE__ - 3D viewer</title>
<style>
  :root { --ink:#23241f; --mute:#6c6b62; --card:rgba(250,249,246,.86); --line:rgba(35,36,31,.12);
          --acc:#5b6247; --accInk:#f4f2ea; }
  * { box-sizing:border-box; -webkit-tap-highlight-color:transparent; }
  html,body { margin:0; height:100%; overflow:hidden; font:14px/1.35 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif; color:var(--ink);
    background: radial-gradient(120% 90% at 50% 38%, #fbfaf7 0%, #ecebe5 48%, #cfcdc4 100%); }
  #c { position:fixed; inset:0; width:100%; height:100%; display:block; touch-action:none; }
  .card { background:var(--card); backdrop-filter: blur(10px); -webkit-backdrop-filter: blur(10px);
          border:1px solid var(--line); border-radius:14px; box-shadow:0 6px 24px rgba(30,30,20,.10); }
  #hdr { position:fixed; left:12px; top:calc(10px + env(safe-area-inset-top)); right:12px; padding:10px 14px; display:flex; flex-wrap:wrap; gap:6px 14px; align-items:baseline; }
  #hdr h1 { font-size:17px; margin:0; letter-spacing:.2px; font-weight:700; }
  #hdr .sub { color:var(--mute); font-size:12.5px; }
  #stats { display:flex; flex-wrap:wrap; gap:6px; width:100%; }
  .chip { background:#fff; border:1px solid var(--line); border-radius:999px; padding:3px 10px; font-size:12.5px; white-space:nowrap; }
  .chip b { font-weight:700; }
  .chip.warn { background:#fff7e0; border-color:#e6c86e; }
  #bar { position:fixed; left:0; right:0; bottom:0; padding:10px 10px calc(10px + env(safe-area-inset-bottom)); display:flex; gap:8px; overflow-x:auto; scrollbar-width:none; }
  #bar::-webkit-scrollbar { display:none; }
  .grp { display:flex; gap:4px; padding:4px; flex:0 0 auto; }
  button { font:inherit; font-size:13.5px; border:0; border-radius:10px; padding:9px 12px; background:transparent; color:var(--ink); white-space:nowrap; cursor:pointer; min-height:40px; }
  button.on { background:var(--acc); color:var(--accInk); }
  button:active { transform:scale(.97); }
  #legend { position:fixed; right:12px; top:120px; padding:10px 12px; width:230px; display:none; font-size:12px; }
  #legend .ramp { height:10px; border-radius:5px; margin:6px 0 2px; background:linear-gradient(90deg,#1a9850 0%,#91cf60 33%,#fee08b 50%,#f46d43 67%,#a50026 100%); }
  #legend .ticks { display:flex; justify-content:space-between; color:var(--mute); }
  #caption { position:fixed; left:14px; bottom:14px; padding:8px 12px; display:none; max-width:70%; font-size:12px; }
  #caption .t { font-weight:700; font-size:15px; margin-bottom:1px; }
  .lbl { position:fixed; transform:translate(-50%,-100%); white-space:nowrap; padding:4px 10px; font-weight:700; font-size:14px; pointer-events:none; display:none; text-align:center; }
  .lbl small { display:block; font-weight:500; color:var(--mute); font-size:11.5px; }
  #loading { position:fixed; inset:0; display:flex; align-items:center; justify-content:center; color:var(--mute); font-size:15px; }
  body.shot #bar, body.shot #hdr { display:none; }
  body.shot #caption { display:block; }
  @media (max-width: 600px) { #hdr { padding:8px 10px; } #hdr .sub { display:none; } #stats { flex-wrap:nowrap; overflow-x:auto; scrollbar-width:none; } #stats::-webkit-scrollbar { display:none; } .chip { font-size:12px; } #hdr h1 { font-size:15.5px; } #legend { top:auto; bottom:84px; right:10px; width:200px; } #caption { max-width:90%; } }
</style>
</head>
<body>
<canvas id="c"></canvas>
<div id="loading">Loading 3D model...</div>
<div id="hdr" class="card">
  <h1>__TITLE__</h1><span class="sub" id="subtitle"></span>
  <div id="stats"></div>
</div>
<div id="legend" class="card">
  <b>Frame utilization</b> (required SF / SF, worst load case)
  <div class="ramp"></div><div class="ticks"><span>0</span><span>0.5</span><span>0.75</span><span>1.0</span><span>1.5+</span></div>
  <div id="feainfo" style="margin-top:6px;color:#4a4a42"></div>
</div>
<div id="caption" class="card"><div class="t" id="capT"></div><div id="capS"></div></div>
<div id="bar" class="card">
  <div class="grp"><button data-mode="pack" class="on">Full pack</button><button data-mode="frame">Frame only</button></div>
  <div class="grp"><button data-tog="haul" title="Full pack: bag swung open on the hinge pins, meat between bag and frame. Frame only: bag off, meat in the cradle">Meat haul</button><button data-tog="xray" title="See through the bag and the back-panel mesh">X-ray</button><button data-tog="explode">Exploded</button><button data-tog="fea">FEA colors</button><button data-tog="mannequin">Mannequin</button><button data-tog="harness" class="on">Harness</button><button data-tog="bp" class="on">Back panel</button><button data-tog="full">Full 85 L</button><button data-tog="lid">Lid</button></div>
  <div class="grp"><button data-torso="15">15 in</button><button data-torso="19" class="on">19 in</button><button data-torso="23">23 in</button><button data-tog="fit">Fit 3 sizes</button></div>
  <div class="grp"><button id="reset">Reset view</button></div>
</div>
<div class="lbl card" id="lbl0"></div><div class="lbl card" id="lbl1"></div><div class="lbl card" id="lbl2"></div>
/*__VENDOR__*/
<script>
const DATA = /*__DATA__*/null;
const GLB_GZ_B64 = "__GLB_B64__";
const SHOT = /[?&]shot=1/.test(location.search);
if (SHOT) document.body.classList.add('shot');

const canvas = document.getElementById('c');
const renderer = new THREE.WebGLRenderer({canvas, antialias:true, alpha:true, preserveDrawingBuffer:true});
renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
renderer.outputEncoding = THREE.sRGBEncoding;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 0.9;
renderer.physicallyCorrectLights = true;
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
const scene = new THREE.Scene();
const pmrem = new THREE.PMREMGenerator(renderer);
scene.environment = pmrem.fromScene(new THREE.RoomEnvironment(), 0.04).texture;
const camera = new THREE.PerspectiveCamera(30, 1, 0.02, 80);
const controls = new THREE.OrbitControls(camera, canvas);
controls.enableDamping = true; controls.dampingFactor = 0.08; controls.minDistance = 0.25; controls.maxDistance = 30;
controls.screenSpacePanning = true;

// lights: sky/ground hemisphere + warm key with soft shadows + cool fill + rim
scene.add(new THREE.HemisphereLight(0xf6f3ea, 0x5f5a4c, 0.9));
const key = new THREE.DirectionalLight(0xfff1de, 3.2);
key.position.set(1.6, 2.6, 2.0); key.castShadow = true;
key.shadow.mapSize.set(2048, 2048); key.shadow.bias = -0.0004; key.shadow.normalBias = 0.02; key.shadow.radius = 4;
Object.assign(key.shadow.camera, {left:-1.4, right:1.4, top:1.6, bottom:-1.2, near:0.1, far:8});
scene.add(key); scene.add(key.target);
const fill = new THREE.DirectionalLight(0xdfe8ff, 1.0); fill.position.set(-2.2, 1.2, -1.0); scene.add(fill);
const rim = new THREE.DirectionalLight(0xffffff, 1.4); rim.position.set(-0.6, 2.0, -2.6); scene.add(rim);
const ground = new THREE.Mesh(new THREE.CircleGeometry(4, 64), new THREE.ShadowMaterial({opacity:0.22}));
ground.rotation.x = -Math.PI/2; ground.receiveShadow = true; scene.add(ground);

const state = {mode:'pack', haul:false, explode:false, fea:false, mannequin:false, torso:19, fit:false, harness:true, full:false, lid:false, xray:false, bp:true};
let root = null, fitRoots = [], explodeT = 0, needsFrame = 3, fitFloor = 0;
const P = DATA.parts;
const M = DATA.metrics;

function b64ToBytes(b64) { const s = atob(b64); const u = new Uint8Array(s.length); for (let i=0;i<s.length;i++) u[i]=s.charCodeAt(i); return u; }
async function gunzip(u8) {
  const ds = new DecompressionStream('gzip');
  const buf = await new Response(new Blob([u8]).stream().pipeThrough(ds)).arrayBuffer();
  return buf;
}

function upgradeMaterial(m) {
  const n = m.name || '';
  const aniso = renderer.capabilities.getMaxAnisotropy();
  [m.map, m.normalMap].forEach(t => { if (t) { t.anisotropy = Math.min(8, aniso); t.wrapS = t.wrapT = THREE.RepeatWrapping; t.needsUpdate = true; }});
  if (n === 'carbon_twill') {
    return new THREE.MeshPhysicalMaterial({name:n, map:m.map, color:0xffffff, metalness:0.25, roughness:0.42,
      clearcoat:1.0, clearcoatRoughness:0.10, envMapIntensity:1.1});
  }
  if (n === 'fea_utilization') return new THREE.MeshStandardMaterial({name:n, vertexColors:true, roughness:0.45, metalness:0.0, envMapIntensity:0.6});
  if (n === 'clay') return new THREE.MeshStandardMaterial({name:n, color:m.color, roughness:0.8, metalness:0, envMapIntensity:0.5});
  const fabric = ['cordura_body','ultragrid_pocket','tpu_840d','binding_trim','webbing','harness_shell','spacer_mesh','camo_owner_base','game_bag_cotton','blaze_orange'];
  if (fabric.includes(n)) {
    const pm = new THREE.MeshPhysicalMaterial({name:n, color:m.color, map:m.map, normalMap:m.normalMap,
      roughness: n==='tpu_840d' ? 0.78 : 0.92, metalness:0, sheen:0.12, sheenRoughness:0.9,
      sheenColor:new THREE.Color(0x8a8676), envMapIntensity:0.45});
    pm.normalScale = new THREE.Vector2(0.35, 0.35);
    return pm;
  }
  m.envMapIntensity = 0.8;
  return m;
}

function partOf(obj) { let o = obj; while (o && !P[o.name]) o = o.parent; return o ? o.name : null; }

function load() {
  const loader = new THREE.GLTFLoader();
  gunzip(b64ToBytes(GLB_GZ_B64)).then(buf => {
    loader.parse(buf, '', gltf => {
      root = gltf.scene;
      const cache = new Map();
      root.traverse(o => {
        if (o.isMesh) {
          o.castShadow = true; o.receiveShadow = true;
          if (!cache.has(o.material)) cache.set(o.material, upgradeMaterial(o.material));
          o.material = cache.get(o.material);
        }
      });
      root.traverse(o => { if (P[o.name]) o.userData.part = o.name; });

      scene.add(root);
      document.getElementById('loading').style.display = 'none';
      buildStats(); resize();
      apply(); view('hero');
      window.viewer.ready = true;
    }, err => { document.getElementById('loading').textContent = 'Could not load model: ' + err; });
  });
}

function fmt(x, d=1) { return (x==null) ? '-' : Number(x).toFixed(d); }
function buildStats() {
  const s = document.getElementById('stats');
  if (M.chips) {   // generic models (e.g. huntkit.clothsim) bring their own header chips + subtitle
    s.innerHTML = M.chips.map(c => `<span class="chip">${c}</span>`).join('');
    document.getElementById('subtitle').textContent = M.subtitle || '';
    return;
  }
  const t = M.torsos[String(state.torso.toFixed(1))] || M.torsos[state.torso] || {};
  const chips = [
    `Main bag <b>${fmt(M.bag_volume_l)} L</b> · ${Math.round(M.bag_volume_cu_in).toLocaleString()} cu in`,
    `Frame <b>${Math.round(M.frame_mass_g)} g</b> · ${fmt(M.frame_mass_g/453.6,2)} lb`,
    `Total <b>${fmt(M.total_mass_g/1000,2)} kg</b> · ${fmt(M.total_mass_g/453.6,1)} lb`,
    `Lid <b>${fmt(M.lid_design_l)} L</b>`,
    `Torso <b>${state.torso} in</b>: crown top ${Math.round(t.crown_top_z||0)} mm · lifters ${fmt(t.lifter_angle_design_deg,1)}°`,
    `Volume from the 3D mesh; target ${fmt(M.target_volume_l)} L (${fmt(M.volume_error_pct,2)} %)`,
  ];
  if (M.attach) chips.push(`Bag hooks <b>${Math.round(M.attach.hook_rated_n)} N</b> rated · crown hood ${Math.round(M.attach.hood_width_mm)} mm`);
  if (M.hinge) chips.push(`Between mode: bag swings <b>${fmt(M.hinge.angle_deg,1)}°</b> on the z ${Math.round(M.hinge.z)} pins`);
  s.innerHTML = chips.map(c => `<span class="chip">${c}</span>`).join('') +
    (M.frame_type === 'generative' ? `<span class="chip">Frame: printed PAHT-CF branch frame + carbon crown</span>`
                                   : `<span class="chip warn">Tube sizes: ${M.tube_size_source}</span>`);
  document.getElementById('subtitle').textContent = `v3.1 SPINE · 85.2 L teardrop roll-top · printed branch frame, carbon crown · ${DATA.info.colorway ? DATA.info.colorway.name : ''} colorway`;
  if (M.fea) document.getElementById('feainfo').innerHTML =
    `Worst: <b>${fmt(M.fea.max_utilization,2)}</b> (${M.fea.critical_case.replace(/_/g,' ')})<br>FEA model: ${M.fea.source}`;
}

function modeKey() { return state.mode + (state.haul ? '_haul' : ''); }
function visibleFor(name, torso) {
  const p = P[name]; if (!p) return true;
  if (!p.modes.includes(modeKey())) return false;
  if (p.torso != null && Math.abs(p.torso - torso) > 0.01) return false;
  if (p.variant === 'full' && !state.full) return false;
  if (p.variant === 'rolled' && state.full) return false;
  if (p.variant === 'lid' && !state.lid) return false;
  if (p.group === 'mannequin') return state.mannequin && explodeT < 0.02;
  if (p.group === 'fea') return state.fea;
  if (p.group === 'suspension' && !state.harness) return false;
  if (p.group === 'backpanel' && !state.bp) return false;
  if (state.fea && (name === 'frame_stays' || name === 'frame_bars' || name.startsWith('crown@'))) return false;
  return true;
}
// between mode: bag parts rotate about the hinge-pin axis (FCS x through y_h, z_h -> glTF X through Y=z, Z=y)
const HINGE = M.hinge || null;
const XMAT = new Map(), XORIG = new Map();   // X-ray twin per original material (clones share materials, not userData)
const _q = new THREE.Quaternion(), _ax = new THREE.Vector3(1, 0, 0), _pv = new THREE.Vector3(), _tmp = new THREE.Vector3();
function placeAll(r, torso) {
  r.traverse(o => {
    const n = o.userData.part; if (!n) return;
    o.visible = visibleFor(n, torso);
    const p = P[n];
    const between = state.haul && state.mode === 'pack';
    const h = between ? p.haul : [0,0,0];
    let px = h[0] + p.explode[0]*explodeT, py = h[1] + p.explode[1]*explodeT, pz = h[2] + p.explode[2]*explodeT;
    if (between && p.swing && HINGE) {
      _q.setFromAxisAngle(_ax, THREE.MathUtils.degToRad(HINGE.angle_deg));
      _pv.set(0, HINGE.z / 1000, HINGE.y / 1000);
      _tmp.copy(_pv).applyQuaternion(_q);
      o.quaternion.copy(_q);
      px += _pv.x - _tmp.x; py += _pv.y - _tmp.y; pz += _pv.z - _tmp.z;
    } else {
      o.quaternion.identity();
    }
    o.position.set(px, py, pz);
    if (p.xray) o.traverse(c => { if (!c.isMesh) return;
      const orig = XORIG.get(c.material) || c.material;
      if (!XMAT.has(orig)) { const x = orig.clone(); x.transparent = true; x.opacity = 0.26; x.depthWrite = false;
                             XMAT.set(orig, x); XORIG.set(x, orig); }
      c.material = state.xray ? XMAT.get(orig) : orig; c.castShadow = !state.xray; });
  });
}
const FIT_DZ = 1.05;
function apply() {
  if (!root) return;
  if (state.fit) {
    root.visible = false;
    if (!fitRoots.length) {
      [15,19,23].forEach((t,i) => { const c = root.clone(true); c.userData.torso = t; scene.add(c); fitRoots.push(c); });
    }
    fitRoots.forEach((c,i) => { c.visible = true; c.position.set(0, 0, (i-1)*FIT_DZ); placeAll(c, c.userData.torso); });
  } else {
    root.visible = true; fitRoots.forEach(c => c.visible = false);
    placeAll(root, state.torso);
  }
  // ground under the lowest visible point
  const box = visibleBox();
  if (!box.isEmpty()) { ground.position.y = box.min.y - 0.001; fitFloor = box.max.y; }
  document.getElementById('legend').style.display = state.fea ? 'block' : 'none';
  syncButtons(); buildStats(); needsFrame = 3;
}
function isShown(o) { let p = o; while (p) { if (!p.visible) return false; p = p.parent; } return true; }

function syncButtons() {
  document.querySelectorAll('[data-mode]').forEach(b => b.classList.toggle('on', b.dataset.mode === state.mode));
  document.querySelectorAll('[data-tog]').forEach(b => b.classList.toggle('on', !!state[b.dataset.tog]));
  document.querySelectorAll('[data-torso]').forEach(b => b.classList.toggle('on', +b.dataset.torso === state.torso && !state.fit));
}
document.querySelectorAll('[data-mode]').forEach(b => b.onclick = () => { state.mode = b.dataset.mode; if (state.mode==='pack') state.fea=false; apply(); });
document.querySelectorAll('[data-tog]').forEach(b => b.onclick = () => {
  const k = b.dataset.tog; state[k] = !state[k];
  if (k === 'fea' && state.fea) { state.mode = 'frame'; state.haul = false; }
  apply();
  if (k === 'fit') view(state.fit ? 'fit' : 'hero');
});
document.querySelectorAll('[data-torso]').forEach(b => b.onclick = () => { state.torso = +b.dataset.torso; state.fit = false; apply(); });
document.getElementById('reset').onclick = () => view(state.fit ? 'fit' : 'hero');

// camera presets: azimuth (deg, 0 = looking at the bag outer face from +Z, +90 = from the wearer's right),
// elevation (deg), zoom (1 = fit the visible bounding sphere), optional target override (glTF metres)
const VIEWS = {
  hero:    {az:-38, el:14, zoom:1},
  side:    {az:90,  el:4,  zoom:1},
  front:   {az:0,   el:6,  zoom:1},
  back:    {az:-150, el:14, zoom:1},
  haul:    {az:58,  el:18, zoom:1},
  exploded:{az:42,  el:16, zoom:1},
  frame:   {az:142, el:12, zoom:1.0},
  fea:     {az:-160, el:12, zoom:1},
  fit:     {az:90,  el:4,  zoom:0.95, fov:14},
  // close-ups framed on a box (FCS mm: [x0, y0, z0, x1, y1, z1]) instead of the whole visible model
  attach:  {az:128, el:20, zoom:1, box:[-80, -30, 380, 215, 90, 810]},
  attach_low:{az:70, el:4, zoom:1, box:[-40, -10, 15, 215, 160, 380]},
  hood:    {az:-138, el:28, zoom:1, box:[-215, -40, 640, 215, 120, 780]},
  bow:     {az:62, el:8, zoom:1, box:[60, 40, 300, 240, 300, 680]},
  between: {az:72,  el:12, zoom:1},
  bagoff:  {az:48,  el:14, zoom:1},
  spreader:{az:22,  el:10, zoom:1, box:[-150, -30, 30, 150, 60, 560]},
  backpanel:{az:-160, el:8, zoom:1, box:[-200, -60, 20, 200, 30, 520]},
};
let currentView = 'hero';
function visibleBox() {
  scene.updateMatrixWorld(true);
  const box = new THREE.Box3();
  (state.fit ? fitRoots : [root]).forEach(r => r && r.traverse(o => { if (o.isMesh && isShown(o)) box.expandByObject(o); }));
  return box;
}
function view(name) {
  currentView = name;
  const v = VIEWS[name] || VIEWS.hero;
  if (!root) return;
  camera.fov = v.fov || (window.innerWidth < window.innerHeight ? 42 : 30); camera.updateProjectionMatrix();
  const box = v.box ? new THREE.Box3(new THREE.Vector3(v.box[0]/1000, v.box[2]/1000, v.box[1]/1000),
                                     new THREE.Vector3(v.box[3]/1000, v.box[5]/1000, v.box[4]/1000)) : visibleBox();
  const tgt = v.tgt ? new THREE.Vector3(...v.tgt) : box.getCenter(new THREE.Vector3());
  const az = THREE.MathUtils.degToRad(v.az), el = THREE.MathUtils.degToRad(v.el);
  const dir = new THREE.Vector3(Math.sin(az)*Math.cos(el), Math.sin(el), Math.cos(az)*Math.cos(el));
  const corners = [];
  for (let i = 0; i < 8; i++) corners.push(new THREE.Vector3(i&1 ? box.max.x : box.min.x, i&2 ? box.max.y : box.min.y, i&4 ? box.max.z : box.min.z));
  let dist = box.getSize(new THREE.Vector3()).length() * 1.5;
  const [ti, bi] = uiInsets();
  const fill = (SHOT ? 0.86 : 0.86 * Math.max(0.45, (window.innerHeight - ti - bi) / window.innerHeight)) * v.zoom;          // fraction of the frame the object may fill
  for (let it = 0; it < 6; it++) {
    camera.position.copy(tgt).addScaledVector(dir, dist); camera.lookAt(tgt); camera.updateMatrixWorld(); camera.updateProjectionMatrix();
    let m = 0;
    corners.forEach(c => { const p = c.clone().project(camera); m = Math.max(m, Math.abs(p.x), Math.abs(p.y + (SHOT ? 0.0 : 0))); });
    dist *= m / fill;
  }
  camera.position.copy(tgt).addScaledVector(dir, dist);
  controls.target.copy(tgt); controls.update(); needsFrame = 3;
}
function uiInsets() {
  if (SHOT) return [0, 0];
  const hdr = document.getElementById('hdr').getBoundingClientRect().bottom;
  const bar = window.innerHeight - document.getElementById('bar').getBoundingClientRect().top;
  return [hdr, bar];
}
function resize() {
  const w = window.innerWidth, h = window.innerHeight;
  renderer.setSize(w, h, false); camera.aspect = w / h;
  camera.fov = w < h ? 42 : 30;
  if (SHOT) camera.setViewOffset(w, h, 0, Math.round(h * 0.07), w, h);
  else { const [top, bot] = uiInsets(); camera.setViewOffset(w, h, 0, -Math.round((top - bot) / 2), w, h); }
  camera.updateProjectionMatrix(); needsFrame = 3;
}
window.addEventListener('resize', resize); resize();
controls.addEventListener('change', () => needsFrame = 2);

const lbls = [0,1,2].map(i => document.getElementById('lbl'+i));
function updateLabels() {
  lbls.forEach((l,i) => {
    if (!state.fit || !root) { l.style.display = 'none'; return; }
    const t = [15,19,23][i]; const tm = M.torsos[t.toFixed(1)] || M.torsos[t] || {};
    const p = new THREE.Vector3(0, fitFloor + 0.02, (i-1)*FIT_DZ).project(camera);
    l.style.display = 'block';
    l.style.left = ((p.x+1)/2*window.innerWidth) + 'px'; l.style.top = ((1-p.y)/2*window.innerHeight) + 'px';
    l.innerHTML = `${t} in torso<small>crown top ${Math.round(tm.crown_top_z)} mm · lifters ${fmt(tm.lifter_angle_design_deg,1)}°</small>`;
  });
}
function tick() {
  requestAnimationFrame(tick);
  const target = state.explode ? 1 : 0;
  if (Math.abs(explodeT - target) > 1e-3) { explodeT += (target - explodeT) * 0.12; if (Math.abs(explodeT-target) < 2e-3) explodeT = target; apply(); }
  if (controls.update()) needsFrame = 2;
  if (needsFrame > 0) { renderer.render(scene, camera); updateLabels(); needsFrame--; }
}
tick();

window.viewer = {
  ready:false, state, view,
  set(s) { Object.assign(state, s); explodeT = state.explode ? 1 : 0; apply(); },
  caption(t, s) { document.getElementById('capT').textContent = t; document.getElementById('capS').innerHTML = s || ''; },
  camera(pos, tgt, fov) { camera.position.set(...pos); controls.target.set(...tgt); if (fov) { camera.fov = fov; camera.updateProjectionMatrix(); } controls.update(); needsFrame = 3; },
  renderNow() { renderer.render(scene, camera); updateLabels(); },
  metrics: M,
};
load();
</script>
</body>
</html>
"""
