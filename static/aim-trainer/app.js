const THREE = window.THREE;

const MODE_CONFIGS = {
  tileFrenzy: {
    key: "tileFrenzy",
    name: "Tile Frenzy",
    breadcrumb: "CLICKING · BASIC",
    description: "Shoot any tile, replace it instantly, and keep the wall full.",
    duration: 30,
    targetCount: 3,
    baseSize: 0.129,
    shape: "square",
    color: "#e74c3c",
    accent: "#ffffff",
    scorePerHit: 1,
    moving: false,
    missPenalty: 0,
    variableScore: false
  },
  gridshot: {
    key: "gridshot",
    name: "Gridshot",
    breadcrumb: "CLICKING · BASIC",
    description: "One target at a time with instant respawns and faster scoring for quick reactions.",
    duration: 30,
    targetCount: 1,
    baseSize: 0.129,
    shape: "circle",
    color: "#ff5d4d",
    accent: "#ffcf70",
    scorePerHit: 1,
    moving: false,
    missPenalty: 0,
    variableScore: true
  },
  speedChallenge: {
    key: "speedChallenge",
    name: "Speed Challenge",
    breadcrumb: "CLICKING · ADVANCED",
    description: "Five active targets, no miss penalty, and nonstop pressure for raw speed.",
    duration: 60,
    targetCount: 5,
    baseSize: 0.129,
    shape: "square",
    color: "#e74c3c",
    accent: "#7b8ff5",
    scorePerHit: 2,
    moving: false,
    missPenalty: 0,
    variableScore: false
  },
  precision: {
    key: "precision",
    name: "Precision",
    breadcrumb: "CLICKING · ADVANCED",
    description: "One slow moving target, heavy miss penalty, and a premium on control.",
    duration: 45,
    targetCount: 1,
    baseSize: 0.129,
    shape: "circle",
    color: "#4bc1ff",
    accent: "#4bc1ff",
    scorePerHit: 5,
    moving: true,
    missPenalty: -3,
    variableScore: false
  }
};

const STORAGE_KEY = "aim-trainer-settings-v1";
const HIGH_SCORES_KEY = "aim-trainer-high-scores-v1";

const WALL_DISTANCE = 8;
const WALL_WIDTH = 7.74;
const WALL_HEIGHT = 7.68;

const state = {
  screen: "menu",
  modeKey: "tileFrenzy",
  gameStartTime: 0,
  timeLeft: 0,
  score: 0,
  hits: 0,
  misses: 0,
  combo: 0,
  highestCombo: 0,
  reactionTimes: [],
  hitPositions: [],
  switchSamples: [],
  averageSwitchSpeed: 0,
  activeTargets: [],
  nextTargetId: 1,
  countdownTimer: null,
  rafId: 0,
  needsLayout: false,
  settings: loadSettings(),
  audio: null,
  lastFrameTime: performance.now(),
  pointerLocked: false,
  scene: null,
  camera: null,
  renderer: null,
  raycaster: new THREE.Raycaster(),
  gunMixer: null,
  gunRestPos: new THREE.Vector3(0.42, -0.38, -0.65),
  gunRestRot: new THREE.Euler(0, Math.PI, 0),
  gunRestPitch: 0,
  gunKickBack: 0,
  gunKickUp: 0,
  gunKickPitch: 0,
  muzzleFlash: null,
  shells: [],
  scopeActive: false,
  baseFov: 65,
  yaw: 0,
  pitch: 0,
  targetYaw: 0,
  targetPitch: 0
};

const els = {
  app: document.getElementById("app"),
  canvasContainer: document.getElementById("threeCanvas"),
  fxLayer: document.getElementById("fxLayer"),
  ambientParticles: document.getElementById("ambientParticles"),
  menuOverlay: document.getElementById("menuOverlay"),
  resultsOverlay: document.getElementById("resultsOverlay"),
  settingsPanel: document.getElementById("settingsPanel"),
  settingsToggle: document.getElementById("settingsToggle"),
  closeSettingsButton: document.getElementById("closeSettingsButton"),
  openSettingsFromMenu: document.getElementById("openSettingsFromMenu"),
  playNowButton: document.getElementById("playNowButton"),
  playAgainButton: document.getElementById("playAgainButton"),
  changeModeButton: document.getElementById("changeModeButton"),
  mainMenuButton: document.getElementById("mainMenuButton"),
  fullscreenButton: document.getElementById("fullscreenButton"),
  muteButton: document.getElementById("muteButton"),
  crosshair: document.getElementById("crosshair"),
  scope: document.getElementById("scope"),
  countdown: document.getElementById("countdown"),
  modeGrid: document.getElementById("modeGrid"),
  modeBreadcrumb: document.getElementById("modeBreadcrumb"),
  modeInfoTitle: document.getElementById("modeInfoTitle"),
  modeInfoDescription: document.getElementById("modeInfoDescription"),
  timerValue: document.getElementById("timerValue"),
  scoreValue: document.getElementById("scoreValue"),
  accuracyValue: document.getElementById("accuracyValue"),
  killsPerSecondValue: document.getElementById("killsPerSecondValue"),
  switchSpeedValue: document.getElementById("switchSpeedValue"),
  resultsMode: document.getElementById("resultsMode"),
  resultsGradeBadge: document.getElementById("resultsGradeBadge"),
  resultsScore: document.getElementById("resultsScore"),
  resultsAccuracy: document.getElementById("resultsAccuracy"),
  resultsHits: document.getElementById("resultsHits"),
  resultsMisses: document.getElementById("resultsMisses"),
  resultsBestCombo: document.getElementById("resultsBestCombo"),
  resultsAvgReact: document.getElementById("resultsAvgReact"),
  resultsKps: document.getElementById("resultsKps"),
  resultsBest: document.getElementById("resultsBest"),
  crosshairSize: document.getElementById("crosshairSize"),
  crosshairColor: document.getElementById("crosshairColor"),
  masterVolume: document.getElementById("masterVolume"),
  sfxVolume: document.getElementById("sfxVolume")
};

const popupPool = [];

bootstrap();

function bootstrap() {
  if (!THREE || !THREE.Scene) {
    document.body.innerHTML = '<div style="color:#fff;background:#111;padding:40px;font-family:sans-serif"><h1>Failed to load 3D engine</h1><p>Three.js failed to load. Check your internet connection and try refreshing.</p></div>';
    return;
  }
  try { createThreeScene(); } catch (e) {
    document.body.innerHTML = '<div style="color:#fff;background:#111;padding:40px;font-family:sans-serif"><h1>3D Error</h1><p>' + e.message + '</p></div>';
    return;
  }
  createAmbientParticles();
  buildModeCards();
  applySettings(state.settings);
  bindEvents();
  syncHud();
  renderModeCard();
  showMenu();
  startLoop();
}

/* ── Three.js Scene ── */

function createThreeScene() {
  state.scene = new THREE.Scene();
  state.scene.background = new THREE.Color(0x1a1d23);

  state.renderer = new THREE.WebGLRenderer({ antialias: true });
  state.renderer.setSize(window.innerWidth, window.innerHeight);
  state.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  state.renderer.setClearColor(0x1a1d23, 1);
  state.renderer.domElement.style.display = 'block';
  state.renderer.domElement.style.position = 'absolute';
  state.renderer.domElement.style.top = '0';
  state.renderer.domElement.style.left = '0';
  state.renderer.domElement.style.width = '100%';
  state.renderer.domElement.style.height = '100%';
  els.canvasContainer.appendChild(state.renderer.domElement);

  const ambient = new THREE.AmbientLight(0xffffff, 0.8);
  state.scene.add(ambient);
  const directional = new THREE.DirectionalLight(0xffffff, 1.4);
  directional.position.set(5, 10, 7);
  state.scene.add(directional);
  const fillLight = new THREE.DirectionalLight(0xffffff, 0.4);
  fillLight.position.set(-3, -2, -5);
  state.scene.add(fillLight);

  state.camera = new THREE.PerspectiveCamera(65, window.innerWidth / window.innerHeight, 0.1, 100);
  state.baseFov = state.camera.fov;
  state.camera.position.set(0, 0, 0.5);
  state.camera.rotation.order = 'YXZ';
  state.scene.add(state.camera);

  const wallGeo = new THREE.PlaneGeometry(WALL_WIDTH, WALL_HEIGHT);
  const wallTex = createWallTexture();
  const wallMat = new THREE.MeshStandardMaterial({ map: wallTex, side: THREE.DoubleSide });
  const wallMesh = new THREE.Mesh(wallGeo, wallMat);
  wallMesh.position.set(0, 0, -WALL_DISTANCE);
  state.scene.add(wallMesh);

  /* subtle floor plane */
  const floorGeo = new THREE.PlaneGeometry(30, 20);
  const floorMat = new THREE.MeshStandardMaterial({ color: 0x2a2d33, roughness: 1, metalness: 0 });
  const floor = new THREE.Mesh(floorGeo, floorMat);
  floor.rotation.x = -Math.PI / 2;
  floor.position.set(0, -WALL_HEIGHT / 2 - 0.5, -WALL_DISTANCE / 2);
  state.scene.add(floor);

  buildRoom();
  addSniperReticle();

  loadGunModel();

  window.addEventListener('resize', () => {
    state.camera.aspect = window.innerWidth / window.innerHeight;
    state.camera.updateProjectionMatrix();
    state.renderer.setSize(window.innerWidth, window.innerHeight);
  });
}

function loadGunModel() {
  if (typeof THREE.GLTFLoader === "undefined") {
    console.warn("GLTFLoader not available; gun model will not load.");
    return;
  }
  const loader = new THREE.GLTFLoader();
  loader.load(
    "assets/high_caliber_revolver.glb",
    (gltf) => {
      const gun = gltf.scene;
      const bb = new THREE.Box3().setFromObject(gun);
      const size = bb.getSize(new THREE.Vector3());
      const center = bb.getCenter(new THREE.Vector3());
      console.log("Gun raw bbox min:", bb.min.x.toFixed(3), bb.min.y.toFixed(3), bb.min.z.toFixed(3),
                  "max:", bb.max.x.toFixed(3), bb.max.y.toFixed(3), bb.max.z.toFixed(3),
                  "size:", size.x.toFixed(3), size.y.toFixed(3), size.z.toFixed(3));

      const TARGET_SIZE = 1.1;
      const maxDim = Math.max(size.x, size.y, size.z);
      const autoScale = maxDim > 0 ? TARGET_SIZE / maxDim : 1;
      gun.scale.setScalar(autoScale);
      gun.position.sub(center.multiplyScalar(autoScale));

      gun.position.set(0.42, -0.38, -0.65);
      gun.rotation.set(0, Math.PI, 0);
      gun.userData.isGun = true;
      state.gunRestPitch = 0;
      state.camera.add(gun);

      const bb2 = new THREE.Box3().setFromObject(gun);
      const size2 = bb2.getSize(new THREE.Vector3());
      console.log("Gun final size:", size2.x.toFixed(3), size2.y.toFixed(3), size2.z.toFixed(3), "scale:", autoScale.toFixed(4));

      const flashCanvas = document.createElement('canvas');
      flashCanvas.width = flashCanvas.height = 128;
      const fctx = flashCanvas.getContext('2d');
      const grd = fctx.createRadialGradient(64, 64, 0, 64, 64, 64);
      grd.addColorStop(0, 'rgba(255, 255, 220, 1)');
      grd.addColorStop(0.2, 'rgba(255, 200, 80, 0.9)');
      grd.addColorStop(0.5, 'rgba(255, 140, 40, 0.5)');
      grd.addColorStop(1, 'rgba(255, 80, 0, 0)');
      fctx.fillStyle = grd;
      fctx.fillRect(0, 0, 128, 128);
      const flashTex = new THREE.CanvasTexture(flashCanvas);
      const flashMat = new THREE.MeshBasicMaterial({ map: flashTex, transparent: true, blending: THREE.AdditiveBlending, depthWrite: false });
      state.muzzleFlash = new THREE.Mesh(new THREE.PlaneGeometry(0.35, 0.35), flashMat);
      state.muzzleFlash.position.set(0.45, -0.32, -1.1);
      state.muzzleFlash.visible = false;
      state.camera.add(state.muzzleFlash);

      if (gltf.animations && gltf.animations.length > 0) {
        state.gunMixer = new THREE.AnimationMixer(gun);
        const names = gltf.animations.map(a => a.name);
        console.log("Animations:", names);
        const idle = gltf.animations.find(a => /idle|hold|ready/i.test(a.name)) || gltf.animations[0];
        const action = state.gunMixer.clipAction(idle);
        action.play();
        console.log("Gun animation playing:", idle.name);
      }
    },
    undefined,
    (err) => {
      console.error("Gun model failed to load:", err);
    }
  );
}

function triggerGunFire() {
  state.gunKickBack = 0.025;
  state.gunKickUp = -0.04;
  state.gunKickPitch = 0.40;
  if (state.muzzleFlash) {
    state.muzzleFlash.visible = true;
    state.muzzleFlash.scale.set(0.8 + Math.random() * 0.4, 0.8 + Math.random() * 0.4, 1);
    state.muzzleFlash.material.opacity = 1;
    setTimeout(() => {
      if (state.muzzleFlash) state.muzzleFlash.visible = false;
    }, 50);
  }
  spawnShell();
  playGunshotSound();
}

function spawnShell() {
  const shellGeo = new THREE.CylinderGeometry(0.012, 0.012, 0.04, 8);
  const shellMat = new THREE.MeshStandardMaterial({ color: 0xddae44, metalness: 0.9, roughness: 0.3 });
  const shell = new THREE.Mesh(shellGeo, shellMat);
  shell.position.set(0.5, -0.3, -0.7);
  shell.rotation.set(0, 0, Math.PI / 2);
  const vel = new THREE.Vector3(
    0.3 + Math.random() * 0.2,
    0.4 + Math.random() * 0.3,
    -0.2 - Math.random() * 0.3
  );
  const angVel = new THREE.Vector3(
    (Math.random() - 0.5) * 8,
    (Math.random() - 0.5) * 8,
    (Math.random() - 0.5) * 8
  );
  state.camera.add(shell);
  state.shells.push({ mesh: shell, vel, angVel, life: 0 });
}

function updateShells(delta) {
  for (let i = state.shells.length - 1; i >= 0; i--) {
    const s = state.shells[i];
    s.life += delta;
    s.vel.y -= 2.0 * delta;
    s.mesh.position.x += s.vel.x * delta;
    s.mesh.position.y += s.vel.y * delta;
    s.mesh.position.z += s.vel.z * delta;
    s.mesh.rotation.x += s.angVel.x * delta;
    s.mesh.rotation.y += s.angVel.y * delta;
    s.mesh.rotation.z += s.angVel.z * delta;
    if (s.life > 2.5) {
      state.camera.remove(s.mesh);
      s.mesh.geometry.dispose();
      s.mesh.material.dispose();
      state.shells.splice(i, 1);
    }
  }
}

function createHexFloorTexture() {
  const S = 1024;
  const c = document.createElement('canvas');
  c.width = c.height = S;
  const x = c.getContext('2d');
  x.fillStyle = '#1a1d23';
  x.fillRect(0, 0, S, S);
  const r = 36;
  const dx = r * Math.sqrt(3);
  const dy = r * 1.5;
  for (let row = -1; row * dy < S + r; row++) {
    for (let col = -1; col * dx < S + dx; col++) {
      const cx = col * dx + (row % 2 ? dx / 2 : 0);
      const cy = row * dy;
      x.beginPath();
      for (let i = 0; i < 6; i++) {
        const a = (Math.PI / 3) * i + Math.PI / 6;
        const px = cx + r * Math.cos(a);
        const py = cy + r * Math.sin(a);
        if (i === 0) x.moveTo(px, py); else x.lineTo(px, py);
      }
      x.closePath();
      const g = x.createRadialGradient(cx, cy, 0, cx, cy, r);
      g.addColorStop(0, '#2a2d33');
      g.addColorStop(1, '#1a1d23');
      x.fillStyle = g;
      x.fill();
      x.strokeStyle = 'rgba(255, 255, 255, 0.04)';
      x.lineWidth = 1;
      x.stroke();
    }
  }
  return c;
}

function buildRoom() {
  const W = WALL_WIDTH, H = WALL_HEIGHT, D = WALL_DISTANCE;
  const floorTex = new THREE.CanvasTexture(createHexFloorTexture());
  floorTex.wrapS = floorTex.wrapT = THREE.RepeatWrapping;
  floorTex.repeat.set(2, 2);
  const floor = new THREE.Mesh(
    new THREE.PlaneGeometry(30, 20),
    new THREE.MeshStandardMaterial({ map: floorTex, roughness: 0.7, metalness: 0.3 })
  );
  floor.rotation.x = -Math.PI / 2;
  floor.position.set(0, -H / 2 - 0.01, -D / 2);
  state.scene.add(floor);

  const panelMat = new THREE.MeshStandardMaterial({
    color: 0x4a4f58, roughness: 0.85, metalness: 0.05
  });
  const seamMat = new THREE.MeshStandardMaterial({
    color: 0x1a1d23, roughness: 0.9, metalness: 0.1
  });
  const wallY = 0;
  const makePanelWall = (w, h, x, y, z, rotY) => {
    const g = new THREE.PlaneGeometry(w, h);
    const m = new THREE.Mesh(g, panelMat);
    m.position.set(x, y, z);
    m.rotation.y = rotY;
    state.scene.add(m);
    const seamH = 0.04, seamGap = 2.0;
    for (let yy = -h / 2 + seamGap; yy < h / 2; yy += seamGap) {
      const s = new THREE.Mesh(new THREE.PlaneGeometry(w, seamH), seamMat);
      s.position.set(x, wallY + yy, z);
      s.rotation.y = rotY;
      s.position.x += Math.cos(rotY) * 0.01;
      s.position.z += Math.sin(rotY) * 0.01;
      state.scene.add(s);
    }
    for (let xx = -w / 2 + seamGap; xx < w / 2; xx += seamGap) {
      const s = new THREE.Mesh(new THREE.PlaneGeometry(seamH, h), seamMat);
      const lx = x + Math.cos(rotY) * xx;
      const lz = z + Math.sin(rotY) * xx;
      s.position.set(lx, y, lz);
      s.rotation.y = rotY;
      s.position.x += Math.cos(rotY) * 0.01;
      s.position.z += Math.sin(rotY) * 0.01;
      state.scene.add(s);
    }
  };
  makePanelWall(20, H, -W / 2 - 0.01, wallY, -D / 2, Math.PI / 2);
  makePanelWall(20, H, W / 2 + 0.01, wallY, -D / 2, -Math.PI / 2);
  const ceil = new THREE.Mesh(new THREE.PlaneGeometry(20, 20), panelMat);
  ceil.rotation.x = Math.PI / 2;
  ceil.position.set(0, H / 2, -D / 2);
  state.scene.add(ceil);

  const accentMat = new THREE.MeshBasicMaterial({ color: 0xffffff, side: THREE.DoubleSide, transparent: true, opacity: 0.15 });
  const strip = (x1, y1, z1, x2, y2, z2) => {
    const len = Math.hypot(x2 - x1, y2 - y1, z2 - z1);
    const m = new THREE.Mesh(new THREE.PlaneGeometry(len, 0.04), accentMat);
    m.position.set((x1 + x2) / 2, (y1 + y2) / 2, (z1 + z2) / 2);
    m.lookAt(x2, y2, z2);
    state.scene.add(m);
  };
  strip(-W / 2 + 0.05, H / 2 - 0.3, -D + 0.02, W / 2 - 0.05, H / 2 - 0.3, -D + 0.02);
  strip(-W / 2 + 0.05, -H / 2 + 0.3, -D + 0.02, W / 2 - 0.05, -H / 2 + 0.3, -D + 0.02);
  strip(-W / 2 + 0.05, -H / 2 + 0.3, -D + 0.02, -W / 2 + 0.05, H / 2 - 0.3, -D + 0.02);
  strip(W / 2 - 0.05, -H / 2 + 0.3, -D + 0.02, W / 2 - 0.05, H / 2 - 0.3, -D + 0.02);
}

function createSniperReticleTexture() {
  const S = 512;
  const c = document.createElement('canvas');
  c.width = c.height = S;
  const x = c.getContext('2d');
  x.clearRect(0, 0, S, S);
  const cx = S / 2, cy = S / 2;
  x.strokeStyle = 'rgba(255, 255, 255, 0.18)';
  x.lineWidth = 2;
  x.beginPath(); x.arc(cx, cy, S * 0.35, 0, Math.PI * 2); x.stroke();
  x.beginPath(); x.arc(cx, cy, S * 0.18, 0, Math.PI * 2); x.stroke();
  x.beginPath(); x.arc(cx, cy, S * 0.08, 0, Math.PI * 2); x.stroke();
  x.beginPath();
  x.moveTo(cx - S * 0.42, cy); x.lineTo(cx - S * 0.36, cy);
  x.moveTo(cx + S * 0.36, cy); x.lineTo(cx + S * 0.42, cy);
  x.moveTo(cx, cy - S * 0.42); x.lineTo(cx, cy - S * 0.36);
  x.moveTo(cx, cy + S * 0.36); x.lineTo(cx, cy + S * 0.42);
  x.stroke();
  x.strokeStyle = 'rgba(255, 255, 255, 0.12)';
  x.lineWidth = 1;
  for (let i = 0; i < 8; i++) {
    const a = (Math.PI * 2 * i) / 8;
    x.beginPath();
    x.moveTo(cx + Math.cos(a) * S * 0.35, cy + Math.sin(a) * S * 0.35);
    x.lineTo(cx + Math.cos(a) * S * 0.42, cy + Math.sin(a) * S * 0.42);
    x.stroke();
  }
  return c;
}

function addSniperReticle() {
  const tex = new THREE.CanvasTexture(createSniperReticleTexture());
  const reticle = new THREE.Mesh(
    new THREE.PlaneGeometry(3.2, 3.2),
    new THREE.MeshBasicMaterial({ map: tex, transparent: true, depthWrite: false })
  );
  reticle.position.set(0, 0, -WALL_DISTANCE + 0.04);
  state.scene.add(reticle);
  state.sniperReticle = reticle;
}

function createWallTexture() {
  const W = 774, H = 768;
  const canvas = document.createElement('canvas');
  canvas.width = W;
  canvas.height = H;
  const ctx = canvas.getContext('2d');
  const grad = ctx.createLinearGradient(0, 0, 0, H);
  grad.addColorStop(0, '#4a4f58');
  grad.addColorStop(1, '#3a3f48');
  ctx.fillStyle = grad;
  ctx.fillRect(0, 0, W, H);
  ctx.strokeStyle = 'rgba(0,0,0,0.15)';
  ctx.lineWidth = 1;
  for (let x = 0; x < W; x += 120) {
    ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, H); ctx.stroke();
  }
  for (let y = 0; y < H; y += 120) {
    ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(W, y); ctx.stroke();
  }
  ctx.strokeStyle = 'rgba(0,0,0,0.25)';
  ctx.lineWidth = 3;
  ctx.strokeRect(2, 2, W - 4, H - 4);
  return new THREE.CanvasTexture(canvas);
}

/* ── Coordinate helpers ── */

function wallToWorld(nx, ny) {
  return { x: (nx - 0.5) * WALL_WIDTH, y: (ny - 0.5) * WALL_HEIGHT, z: -WALL_DISTANCE };
}

function targetWorldPos(target) {
  return wallToWorld(target.x, target.y);
}

function targetScreenPos(target) {
  const vec = new THREE.Vector3();
  const wp = targetWorldPos(target);
  vec.set(wp.x, wp.y, wp.z);
  vec.project(state.camera);
  return {
    x: (vec.x * 0.5 + 0.5) * window.innerWidth,
    y: (-vec.y * 0.5 + 0.5) * window.innerHeight
  };
}

/* ── Target textures ── */

function roundRectPath(ctx, x, y, w, h, r) {
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.lineTo(x + w - r, y);
  ctx.arcTo(x + w, y, x + w, y + r, r);
  ctx.lineTo(x + w, y + h - r);
  ctx.arcTo(x + w, y + h, x + w - r, y + h, r);
  ctx.lineTo(x + r, y + h);
  ctx.arcTo(x, y + h, x, y + h - r, r);
  ctx.lineTo(x, y + r);
  ctx.arcTo(x, y, x + r, y, r);
  ctx.closePath();
}

function createTargetTexture(shape) {
  const S = 100, H = S / 2;
  const canvas = document.createElement('canvas');
  canvas.width = S; canvas.height = S;
  const ctx = canvas.getContext('2d');

  if (shape === 'circle') {
    ctx.beginPath();
    ctx.arc(H, H, H - 2, 0, Math.PI * 2);
    ctx.clip();
  }

  ctx.shadowColor = 'rgba(0,0,0,0)';
  ctx.shadowBlur = 0;
  ctx.fillStyle = 'rgba(0,0,0,0.4)';
  roundRectPath(ctx, 3, 4, 94, 94, 6);
  ctx.fill();

  ctx.fillStyle = '#1a1d23';
  ctx.fillRect(2, 96, 96, 2);
  ctx.fillRect(96, 2, 2, 96);

  const bg = ctx.createLinearGradient(0, 0, S, S);
  bg.addColorStop(0, '#f5f5f5');
  bg.addColorStop(1, '#e0e0e0');
  ctx.fillStyle = bg;
  roundRectPath(ctx, 2, 2, 96, 96, 6);
  ctx.fill();

  const sheen = ctx.createLinearGradient(0, 0, 0, S);
  sheen.addColorStop(0, 'rgba(255,255,255,0.3)');
  sheen.addColorStop(0.5, 'rgba(255,255,255,0)');
  sheen.addColorStop(1, 'rgba(0,0,0,0.08)');
  ctx.fillStyle = sheen;
  roundRectPath(ctx, 2, 2, 96, 96, 6);
  ctx.fill();

  ctx.strokeStyle = 'rgba(0,0,0,0.2)';
  ctx.lineWidth = 1;
  roundRectPath(ctx, 4, 4, 92, 92, 5);
  ctx.stroke();

  const cx = H, cy = H;
  ctx.fillStyle = '#e63946';
  ctx.beginPath(); ctx.arc(cx, cy, 28, 0, Math.PI * 2); ctx.fill();
  ctx.fillStyle = '#f5f5f5';
  ctx.beginPath(); ctx.arc(cx, cy, 21, 0, Math.PI * 2); ctx.fill();
  ctx.fillStyle = '#e63946';
  ctx.beginPath(); ctx.arc(cx, cy, 14, 0, Math.PI * 2); ctx.fill();
  ctx.fillStyle = '#f5f5f5';
  ctx.beginPath(); ctx.arc(cx, cy, 7, 0, Math.PI * 2); ctx.fill();
  ctx.fillStyle = '#1a1d23';
  ctx.beginPath(); ctx.arc(cx, cy, 2.5, 0, Math.PI * 2); ctx.fill();

  ctx.strokeStyle = 'rgba(0,0,0,0.15)';
  ctx.lineWidth = 0.5;
  ctx.beginPath();
  ctx.moveTo(cx, 6); ctx.lineTo(cx, 18);
  ctx.moveTo(cx, 82); ctx.lineTo(cx, 94);
  ctx.moveTo(6, cy); ctx.lineTo(18, cy);
  ctx.moveTo(82, cy); ctx.lineTo(94, cy);
  ctx.stroke();

  return new THREE.CanvasTexture(canvas);
}

function darkenColor(hex, amount) {
  const num = parseInt(hex.replace('#', ''), 16);
  const r = Math.max(0, (num >> 16) * (1 - amount));
  const g = Math.max(0, ((num >> 8) & 0xFF) * (1 - amount));
  const b = Math.max(0, (num & 0xFF) * (1 - amount));
  return `rgb(${r|0},${g|0},${b|0})`;
}

/* ── Target management ── */

function createTargetMesh(config) {
  const size = config.baseSize * WALL_WIDTH;
  const texture = createTargetTexture(config.shape);
  const mat = new THREE.MeshStandardMaterial({ map: texture, transparent: true, opacity: 0, side: THREE.DoubleSide, depthTest: true });
  const geo = new THREE.PlaneGeometry(size, size);
  const mesh = new THREE.Mesh(geo, mat);
  return { mesh, mat };
}

function overlapsAny3D(candidate, size) {
  return state.activeTargets.some((t) => {
    const dx = candidate.x - t.x;
    const dy = candidate.y - t.y;
    const minDist = (size + t.size) * 0.7;
    return Math.sqrt(dx * dx + dy * dy) < minDist;
  });
}

function spawnTarget3D(preferredX, preferredY) {
  const config = MODE_CONFIGS[state.modeKey];
  const size = config.baseSize;
  const target = {
    id: state.nextTargetId++,
    x: preferredX ?? 0,
    y: preferredY ?? 0,
    size,
    vx: config.moving ? randomRange(-0.07, 0.07) : 0,
    vy: config.moving ? randomRange(-0.05, 0.05) : 0,
    spawnedAt: performance.now(),
    mesh: null,
    material: null
  };
  if (preferredX == null || preferredY == null) {
    const margins = size * 0.65;
    let placed = false;
    for (let attempt = 0; attempt < 70 && !placed; attempt += 1) {
      const candidate = { x: randomRange(margins, 1 - margins), y: randomRange(margins, 1 - margins) };
      if (!overlapsAny3D(candidate, size)) {
        target.x = candidate.x; target.y = candidate.y; placed = true;
      }
    }
    if (!placed) { target.x = randomRange(margins, 1 - margins); target.y = randomRange(margins, 1 - margins); }
  }
  const { mesh, mat } = createTargetMesh(config);
  const wp = targetWorldPos(target);
  mesh.position.set(wp.x, wp.y, wp.z + 0.01);
  mesh.userData.targetId = target.id;
  state.scene.add(mesh);
  target.mesh = mesh;
  target.material = mat;
  state.activeTargets.push(target);
  const startT = performance.now();
  function fadeIn() {
    const t = Math.min(1, (performance.now() - startT) / 130);
    mat.opacity = t;
    if (t < 1) requestAnimationFrame(fadeIn);
  }
  fadeIn();
  return target;
}

function removeTarget3D(target, animate = false) {
  const idx = state.activeTargets.findIndex((t) => t.id === target.id);
  if (idx !== -1) state.activeTargets.splice(idx, 1);
  const dispose = () => {
    if (target.mesh) { target.mesh.geometry.dispose(); target.material.dispose(); state.scene.remove(target.mesh); }
  };
  if (animate) {
    const startT = performance.now();
    function fadeOut() {
      const t = Math.min(1, (performance.now() - startT) / 140);
      target.material.opacity = 1 - t;
      if (t < 1) requestAnimationFrame(fadeOut); else dispose();
    }
    fadeOut();
  } else { dispose(); }
}

function spawnInitialTargets() {
  const config = MODE_CONFIGS[state.modeKey];
  for (let i = 0; i < config.targetCount; i += 1) spawnTarget3D();
}

function spawnReplacementIfNeeded() {
  const config = MODE_CONFIGS[state.modeKey];
  while (state.activeTargets.length < config.targetCount && state.screen === "playing") spawnTarget3D();
}

function clearAllTargets() {
  const copy = [...state.activeTargets];
  copy.forEach((t) => removeTarget3D(t, false));
  state.activeTargets = [];
}

/* ── Raycaster hit detection ── */

function getTargetFromRaycaster() {
  const center = new THREE.Vector2(0, 0);
  state.raycaster.setFromCamera(center, state.camera);
  const meshes = state.activeTargets.map((t) => t.mesh).filter(Boolean);
  const hits = state.raycaster.intersectObjects(meshes);
  if (hits.length > 0) {
    const id = hits[0].object.userData.targetId;
    return state.activeTargets.find((t) => t.id === id) || null;
  }
  return null;
}

/* ── Game logic ── */

function handleHit(target, event) {
  const now = performance.now();
  const config = MODE_CONFIGS[state.modeKey];
  const reaction = Math.max(0, now - target.spawnedAt);
  state.hits += 1;
  state.combo += 1;
  state.highestCombo = Math.max(state.highestCombo, state.combo);
  state.reactionTimes.push(reaction);
  if (state.hitPositions.length > 0) {
    const prev = state.hitPositions[state.hitPositions.length - 1];
    const deltaSec = Math.max(0.001, (now - prev.time) / 1000);
    const dx = target.x - prev.x;
    const dy = target.y - prev.y;
    state.switchSamples.push(Math.sqrt(dx * dx + dy * dy) / deltaSec);
  }
  state.hitPositions.push({ x: target.x, y: target.y, time: now });
  const baseScore = config.variableScore ? scoreByReaction(reaction) : config.scorePerHit;
  const multiplier = comboMultiplier(state.combo);
  const points = Math.max(1, Math.round(baseScore * multiplier));
  state.score += points;
  removeTarget3D(target, true);
  spawnReplacementIfNeeded();
  spawnParticlesFromTarget(target);
  spawnScorePopup(points > 1 ? `+${points}` : "+1", target, event, points > 1 ? "popup popup--combo" : "popup");
  playHitSound();
  pulseScore();
  maybeComboFlash();
  syncHud();
}

function handleMiss(event) {
  const config = MODE_CONFIGS[state.modeKey];
  state.misses += 1;
  state.combo = 0;
  if (config.missPenalty) state.score = Math.max(0, state.score + config.missPenalty);
  flashMiss(event);
  playMissSound();
  syncHud();
}

function finishGame() {
  state.screen = "results";
  clearTimeout(state.countdownTimer);
  clearAllTargets();
  if (state.scopeActive) { state.scopeActive = false; if (els.scope) els.scope.classList.remove("is-active"); animateFov(state.baseFov, 180); }
  releasePointerLock();
  showOverlay(els.resultsOverlay);
  hideOverlay(els.menuOverlay);
  if (els.countdown) { els.countdown.classList.remove("is-visible"); els.countdown.innerHTML = ""; }
  syncHud();

  const data = { score: state.score, accuracy: getAccuracy(), hits: state.hits, grade: getGrade() };
  const isNew = saveHighScoreIfBetter(state.modeKey, data);
  if (els.resultsBest) {
    const best = getBestScore(state.modeKey);
    if (isNew) {
      els.resultsBest.textContent = "NEW PERSONAL BEST!";
      els.resultsBest.className = "results-card__best is-new";
    } else if (best) {
      els.resultsBest.textContent = `Personal Best: ${best.score} (${best.grade})`;
      els.resultsBest.className = "results-card__best";
    }
  }
}

/* ── Moving targets ── */

function updateMovingTargets3D() {
  if (!MODE_CONFIGS[state.modeKey].moving) return;
  const delta = Math.min(0.03, (performance.now() - state.lastFrameTime) / 1000);
  state.activeTargets.forEach((t) => {
    t.x += t.vx * delta;
    t.y += t.vy * delta;
    const margin = t.size * 0.55;
    if (t.x < margin || t.x > 1 - margin) { t.vx *= -1; t.x = clamp(t.x, margin, 1 - margin); }
    if (t.y < margin || t.y > 1 - margin) { t.vy *= -1; t.y = clamp(t.y, margin, 1 - margin); }
    const wp = targetWorldPos(t);
    if (t.mesh) t.mesh.position.set(wp.x, wp.y, wp.z + 0.01);
  });
}

/* ── Events ── */

function bindEvents() {
  els.settingsToggle.addEventListener("click", () => toggleSettings(true));
  els.openSettingsFromMenu.addEventListener("click", () => toggleSettings(true));
  els.closeSettingsButton.addEventListener("click", () => toggleSettings(false));
  els.playNowButton.addEventListener("click", () => startMode("tileFrenzy"));
  els.playAgainButton.addEventListener("click", () => restartCurrentMode());
  els.changeModeButton.addEventListener("click", () => showMenu());
  els.mainMenuButton.addEventListener("click", () => showMenu());
  els.fullscreenButton.addEventListener("click", toggleFullscreen);
  els.muteButton.addEventListener("click", toggleMute);
  document.addEventListener("keydown", onKeyDown);
  document.addEventListener("keyup", onKeyUp);
  document.addEventListener("mousemove", onMouseMove);
  document.addEventListener("mousedown", onPrimaryMouseDown);
  document.addEventListener("mouseup", onPrimaryMouseUp);
  document.addEventListener("contextmenu", onContextMenu);
  document.addEventListener("pointerlockchange", onPointerLockChange);
  els.crosshairSize.addEventListener("input", () => {
    state.settings.crosshairSize = Number(els.crosshairSize.value);
    applySettings(state.settings);
    persistSettings();
  });
  els.crosshairColor.addEventListener("input", () => {
    state.settings.crosshairColor = els.crosshairColor.value;
    applySettings(state.settings);
    persistSettings();
  });
  els.masterVolume.addEventListener("input", () => {
    state.settings.masterVolume = Number(els.masterVolume.value);
    persistSettings();
  });
  els.sfxVolume.addEventListener("input", () => {
    state.settings.sfxVolume = Number(els.sfxVolume.value);
    persistSettings();
  });
  document.querySelectorAll("[data-mode]").forEach((button) => {
    button.addEventListener("click", () => startMode(button.dataset.mode));
  });
}

function onPointerLockChange() {
  state.pointerLocked = document.pointerLockElement === els.app;
  if (!state.pointerLocked && state.screen === "playing") showMenu();
}

function onMouseMove(event) {
  if (!state.pointerLocked || state.screen !== "playing") return;
  const sens = state.settings.sensitivity ?? 1;
  state.targetYaw -= event.movementX * sens * 0.002;
  state.targetPitch -= event.movementY * sens * 0.002;
  state.targetPitch = clamp(state.targetPitch, -1.2, 1.2);
}


function onPrimaryMouseDown(event) {
  if (state.screen !== "playing") return;
  if (event.target?.closest?.("button, select, input")) return;
  if (event.button === 2) {
    event.preventDefault();
    if (!state.scopeActive) toggleScope(true);
    return;
  }
  if (event.button !== 0) return;
  triggerGunFire();
  const target = getTargetFromRaycaster();
  if (target) { handleHit(target, event); return; }
  handleMiss(event);
}

function onPrimaryMouseUp(event) {
  if (state.screen !== "playing") return;
  if (event.button === 2 && state.scopeActive) {
    event.preventDefault();
    toggleScope(false);
  }
}

function onContextMenu(event) {
  if (state.screen !== "playing") return;
  event.preventDefault();
}

function toggleScope(force) {
  state.scopeActive = force ?? !state.scopeActive;
  console.log("toggleScope -> active:", state.scopeActive);
  if (els.scope) els.scope.classList.toggle("is-active", state.scopeActive);
  const targetFov = state.scopeActive ? 18 : state.baseFov;
  animateFov(targetFov, 180);
}

let fovAnim = null;
function animateFov(target, durationMs) {
  if (!state.camera) return;
  const start = state.camera.fov;
  const startTime = performance.now();
  fovAnim = { start, target, startTime, durationMs };
}

function updateFovAnim() {
  if (!fovAnim || !state.camera) return;
  const t = Math.min(1, (performance.now() - fovAnim.startTime) / fovAnim.durationMs);
  const eased = t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2;
  state.camera.fov = fovAnim.start + (fovAnim.target - fovAnim.start) * eased;
  state.camera.updateProjectionMatrix();
  if (t >= 1) fovAnim = null;
}

function onKeyDown(event) {
  if (event.key === "Escape") {
    if (state.screen === "playing") { showMenu(); return; }
    if (els.settingsPanel.classList.contains("is-open")) { closeSettings(); return; }
    showMenu(); return;
  }
  if (event.key.toLowerCase() === "y") { restartCurrentMode(); return; }
  if (event.key.toLowerCase() === "m") { toggleMute(); return; }
  if (event.key.toLowerCase() === "f") { toggleFullscreen(); return; }
  if (!els.menuOverlay.classList.contains("hidden")) {
    const mapping = { "1": "tileFrenzy", "2": "gridshot", "3": "speedChallenge", "4": "precision" };
    if (mapping[event.key]) startMode(mapping[event.key]);
  }
}

function onKeyUp() {}

/* ── Mode management ── */

function startMode(modeKey) {
  clearAllTargets();
  state.modeKey = modeKey;
  state.screen = "countdown";
  state.score = 0;
  state.hits = 0;
  state.misses = 0;
  state.combo = 0;
  state.yaw = 0;
  state.pitch = 0;
  state.targetYaw = 0;
  state.targetPitch = 0;
  if (state.camera) {
    state.camera.rotation.y = 0;
    state.camera.rotation.x = 0;
  }
  state.highestCombo = 0;
  state.reactionTimes = [];
  state.hitPositions = [];
  state.switchSamples = [];
  state.averageSwitchSpeed = 0;
  state.activeTargets = [];
  state.nextTargetId = 1;
  state.timeLeft = MODE_CONFIGS[modeKey].duration;
  state.gameStartTime = 0;
  state.yaw = 0; state.pitch = 0; state.targetYaw = 0; state.targetPitch = 0;
  if (state.camera) { state.camera.rotation.y = 0; state.camera.rotation.x = 0; }
  requestPointerLock();
  hideOverlay(els.menuOverlay);
  hideOverlay(els.resultsOverlay);
  closeSettings();
  setModeTheme(modeKey);
  renderModeCard();
  syncHud();
  runCountdown(() => {
    state.screen = "playing";
    state.gameStartTime = performance.now();
    state.timeLeft = MODE_CONFIGS[state.modeKey].duration;
    spawnInitialTargets();
    syncHud();
  });
}

function restartCurrentMode() { startMode(state.modeKey); }

function runCountdown(done) {
  const steps = ["3", "2", "1", "GO!"];
  let index = 0;
  const advance = () => {
    if (state.screen !== "countdown") return;
    if (index >= steps.length) {
      if (els.countdown) { els.countdown.innerHTML = ""; els.countdown.classList.remove("is-visible"); }
      done(); return;
    }
    const label = steps[index];
    if (els.countdown) { els.countdown.classList.add("is-visible"); els.countdown.innerHTML = `<div class="countdown__text ${label === "GO!" ? "countdown__text--go" : ""}">${label}</div>`; }
    playCountdownSound(index);
    index += 1;
    state.countdownTimer = window.setTimeout(advance, 850);
  };
  clearTimeout(state.countdownTimer);
  advance();
}

function showMenu() {
  state.screen = "menu";
  clearTimeout(state.countdownTimer);
  clearAllTargets();
  state.timeLeft = MODE_CONFIGS[state.modeKey].duration;
  state.yaw = 0; state.pitch = 0; state.targetYaw = 0; state.targetPitch = 0;
  if (state.camera) { state.camera.rotation.y = 0; state.camera.rotation.x = 0; }
  if (state.scopeActive) { state.scopeActive = false; if (els.scope) els.scope.classList.remove("is-active"); animateFov(state.baseFov, 180); }
  releasePointerLock();
  showOverlay(els.menuOverlay);
  hideOverlay(els.resultsOverlay);
  if (els.countdown) { els.countdown.classList.remove("is-visible"); els.countdown.innerHTML = ""; }
  syncHud();
}

/* ── UI ── */

function showOverlay(el) { el.classList.remove("hidden"); }
function hideOverlay(el) { el.classList.add("hidden"); }

function buildModeCards() {
  els.modeGrid.innerHTML = "";
  const scores = loadHighScores();
  const order = ["tileFrenzy", "gridshot", "speedChallenge", "precision"];
  for (const key of order) {
    const config = MODE_CONFIGS[key];
    const best = scores[key];
    const bestHtml = best ? `<div class="mode-card__best">Best: ${best.score} <span class="mode-card__best-grade">${best.grade}</span></div>` : "";
    const card = document.createElement("button");
    card.type = "button";
    card.className = "mode-card mode-card--menu";
    card.dataset.mode = key;
    card.innerHTML = `<div class="mode-card__breadcrumb">${config.breadcrumb}</div><div class="mode-card__title">${config.name}</div><div class="mode-card__description">${config.description}</div><div class="mode-card__duration">${config.duration}s</div>${bestHtml}<div class="mode-card__dots">${renderDots(config.targetCount)}</div>`;
    els.modeGrid.appendChild(card);
  }
}

function renderDots(count) {
  return Array.from({ length: 5 }, (_, i) => `<span class="${i < Math.min(count, 5) ? "is-filled" : ""}"></span>`).join("");
}

function setModeTheme(modeKey) {
  document.documentElement.dataset.mode = modeKey;
  const config = MODE_CONFIGS[modeKey];
  document.documentElement.style.setProperty("--accent", config.accent);
  document.documentElement.style.setProperty("--target", config.color);
  document.documentElement.style.setProperty("--crosshair-color", state.settings.crosshairColor);
}

function renderModeCard() {
  const config = MODE_CONFIGS[state.modeKey];
  els.modeBreadcrumb.textContent = config.breadcrumb;
  els.modeInfoTitle.textContent = config.name;
  els.modeInfoDescription.textContent = config.description;
  els.resultsMode.textContent = `${config.name} Complete`;
  document.querySelectorAll(".mode-card--menu").forEach((card) => {
    card.classList.toggle("is-active", card.dataset.mode === state.modeKey);
  });
}

/* ── HUD ── */

function syncHud() {
  const config = MODE_CONFIGS[state.modeKey];
  els.timerValue.textContent = formatClock(Math.max(0, state.timeLeft || config.duration));
  els.scoreValue.textContent = String(state.score);
  const acc = getAccuracy();
  els.accuracyValue.textContent = `${acc.toFixed(1)}%`;
  els.killsPerSecondValue.textContent = `${getKillsPerSecond().toFixed(2)}`;
  els.switchSpeedValue.textContent = `${state.averageSwitchSpeed.toFixed(2)} /s`;
  els.resultsScore.textContent = String(state.score);
  els.resultsAccuracy.textContent = `${acc.toFixed(1)}%`;
  els.resultsHits.textContent = String(state.hits);
  els.resultsMisses.textContent = String(state.misses);
  els.resultsBestCombo.textContent = String(state.highestCombo);
  els.resultsAvgReact.textContent = `${Math.round(getAverageReaction())} ms`;
  els.resultsKps.textContent = getKillsPerSecond().toFixed(2);
  els.resultsGradeBadge.textContent = getGrade();
}

function updateHud() {
  const now = performance.now();
  const config = MODE_CONFIGS[state.modeKey];
  if (state.screen === "playing") {
    const elapsed = (now - state.gameStartTime) / 1000;
    state.timeLeft = Math.max(0, config.duration - elapsed);
    if (state.timeLeft <= 0) { state.timeLeft = 0; finishGame(); return; }
    if (config.moving) updateMovingTargets3D();
  }
  state.averageSwitchSpeed = state.switchSamples.length > 0
    ? state.switchSamples.reduce((s, v) => s + v, 0) / state.switchSamples.length
    : 0;
  syncHud();
}

function pulseScore() {
  els.scoreValue.classList.add("is-pulse");
  window.setTimeout(() => els.scoreValue.classList.remove("is-pulse"), 120);
}

/* ── Particles & popups ── */

function spawnScorePopup(text, target, event, className) {
  const sp = targetScreenPos(target);
  const popup = getPopupElement();
  popup.className = className;
  popup.textContent = text;
  popup.style.left = `${sp.x}px`;
  popup.style.top = `${sp.y}px`;
  popup.style.display = "block";
  popup.addEventListener("animationend", () => { popup.style.display = "none"; }, { once: true });
}

function getPopupElement() {
  let popup = popupPool.find((n) => n.style.display === "none");
  if (!popup) {
    popup = document.createElement("div");
    popup.className = "popup";
    popup.style.display = "none";
    document.body.appendChild(popup);
    popupPool.push(popup);
  }
  return popup;
}

function spawnParticlesFromTarget(target) {
  const sp = targetScreenPos(target);
  for (let i = 0; i < 10; i += 1) {
    const p = document.createElement("div");
    p.className = "particle";
    p.style.left = `${sp.x}px`;
    p.style.top = `${sp.y}px`;
    p.style.setProperty("--particle-color", i % 2 === 0 ? "#ff4444" : "#f39c12");
    p.style.setProperty("--dx", `${randomRange(-60, 60)}px`);
    p.style.setProperty("--dy", `${randomRange(-70, 50)}px`);
    p.style.setProperty("--rot", `${randomRange(-220, 220)}deg`);
    document.body.appendChild(p);
    p.addEventListener("animationend", () => p.remove(), { once: true });
  }
}

function flashMiss(event) {
  const flash = ensureEffect("miss-vignette");
  flash.classList.remove("is-visible");
  void flash.offsetWidth;
  flash.classList.add("is-visible");
  const dot = document.createElement("div");
  dot.className = "particle";
  dot.style.width = "8px";
  dot.style.height = "8px";
  dot.style.borderRadius = "999px";
  dot.style.background = "rgba(255,255,255,0.92)";
  dot.style.left = `${event.clientX}px`;
  dot.style.top = `${event.clientY}px`;
  dot.style.setProperty("--dx", "0px");
  dot.style.setProperty("--dy", "0px");
  dot.style.setProperty("--rot", "0deg");
  document.body.appendChild(dot);
  dot.addEventListener("animationend", () => dot.remove(), { once: true });
  playMissSound();
}

function maybeComboFlash() {
  if (state.combo > 0 && state.combo % 5 === 0) {
    const flash = ensureEffect("screen-flash");
    flash.classList.remove("is-visible");
    void flash.offsetWidth;
    flash.classList.add("is-visible");
    spawnComboPopup(`x${state.combo} COMBO`);
    playComboSound();
  }
}

function spawnComboPopup(text) {
  const popup = getPopupElement();
  popup.className = "popup popup--combo";
  popup.textContent = text;
  popup.style.left = `${window.innerWidth / 2}px`;
  popup.style.top = `${window.innerHeight * 0.36}px`;
  popup.style.display = "block";
  popup.addEventListener("animationend", () => { popup.style.display = "none"; }, { once: true });
}

function ensureEffect(className) {
  let node = document.querySelector(`.${className}`);
  if (!node) { node = document.createElement("div"); node.className = className; document.body.appendChild(node); }
  return node;
}

function createAmbientParticles() {
  for (let i = 0; i < 26; i += 1) {
    const p = document.createElement("span");
    p.className = "ambient-particle";
    p.style.left = `${randomRange(0, 100)}%`;
    p.style.top = `${randomRange(0, 100)}%`;
    p.style.setProperty("--size", `${randomRange(2, 5)}px`);
    p.style.setProperty("--opacity", String(randomRange(0.12, 0.34)));
    p.style.setProperty("--duration", `${randomRange(18, 34)}s`);
    p.style.setProperty("--delay", `${randomRange(-24, 0)}s`);
    p.style.setProperty("--dx", `${randomRange(-48, 48)}px`);
    p.style.setProperty("--dy", `${randomRange(-96, -24)}px`);
    els.ambientParticles.appendChild(p);
  }
}

/* ── Scoring helpers ── */

function getAccuracy() {
  const total = state.hits + state.misses;
  return total === 0 ? 100 : (state.hits / total) * 100;
}

function getKillsPerSecond() {
  if (!state.gameStartTime || state.screen === "menu") return 0;
  return state.hits / Math.max(0.001, (performance.now() - state.gameStartTime) / 1000);
}

function getAverageReaction() {
  return state.reactionTimes.length === 0 ? 0 : state.reactionTimes.reduce((s, v) => s + v, 0) / state.reactionTimes.length;
}

function getGrade() {
  const accuracy = getAccuracy();
  const score = state.score;
  if (accuracy >= 97 && score >= 50) return "S";
  if (accuracy >= 92 && score >= 40) return "A";
  if (accuracy >= 85 && score >= 30) return "B";
  if (accuracy >= 70) return "C";
  return "D";
}

function comboMultiplier(combo) {
  if (combo >= 20) return 3;
  if (combo >= 10) return 2;
  if (combo >= 5) return 1.5;
  return 1;
}

function scoreByReaction(reaction) {
  if (reaction < 160) return 4;
  if (reaction < 260) return 3;
  if (reaction < 420) return 2;
  return 1;
}

function formatClock(seconds) {
  const total = Math.max(0, Math.ceil(seconds));
  return `${String(Math.floor(total / 60)).padStart(2, "0")}:${String(total % 60).padStart(2, "0")}`;
}

/* ── Settings ── */

function toggleSettings(forceOpen) {
  const shouldOpen = typeof forceOpen === "boolean" ? forceOpen : !els.settingsPanel.classList.contains("is-open");
  els.settingsPanel.classList.toggle("is-open", shouldOpen);
  els.settingsPanel.setAttribute("aria-hidden", String(!shouldOpen));
}

function closeSettings() { toggleSettings(false); }

function applySettings(settings) {
  document.documentElement.style.setProperty("--crosshair-size", `${settings.crosshairSize}px`);
  document.documentElement.style.setProperty("--crosshair-color", settings.crosshairColor);
  els.crosshairSize.value = String(settings.crosshairSize);
  els.crosshairColor.value = settings.crosshairColor;
  els.masterVolume.value = String(settings.masterVolume);
  els.sfxVolume.value = String(settings.sfxVolume);
  updateMuteButton();
}

function persistSettings() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(state.settings));
  updateMuteButton();
}

function updateMuteButton() { els.muteButton.textContent = state.settings.muted ? "Unmute" : "Mute"; }

function toggleMute() { state.settings.muted = !state.settings.muted; persistSettings(); }

function toggleFullscreen() {
  if (document.fullscreenElement) { document.exitFullscreen().catch(() => {}); } else { document.documentElement.requestFullscreen?.().catch(() => {}); }
}

function requestPointerLock() {
  if (document.pointerLockElement) return;
  els.app.requestPointerLock?.();
}

function releasePointerLock() {
  if (document.pointerLockElement) document.exitPointerLock?.();
}

function loadSettings() {
  const defaults = { crosshairSize: 16, crosshairColor: "#00ff88", masterVolume: 70, sfxVolume: 80, muted: false, sensitivity: 1 };
  try { return { ...defaults, ...JSON.parse(localStorage.getItem(STORAGE_KEY) || "null") }; } catch { return defaults; }
}

/* ── High Scores ── */

function loadHighScores() {
  try { return JSON.parse(localStorage.getItem(HIGH_SCORES_KEY) || "{}"); } catch { return {}; }
}

function saveHighScoreIfBetter(modeKey, data) {
  const scores = loadHighScores();
  const prev = scores[modeKey];
  if (!prev || data.score > prev.score) {
    scores[modeKey] = { score: data.score, accuracy: data.accuracy, hits: data.hits, grade: data.grade, date: new Date().toISOString().slice(0, 10) };
    localStorage.setItem(HIGH_SCORES_KEY, JSON.stringify(scores));
    return true;
  }
  return false;
}

function getBestScore(modeKey) {
  const scores = loadHighScores();
  return scores[modeKey] || null;
}

/* ── Audio ── */

function playHitSound() { playTone(780, 0.05, "triangle", 0.06); }
function playMissSound() { playTone(140, 0.08, "sine", 0.04); }
function playComboSound() { playChord([660, 880, 990], 0.12, 0.05); }

function playGunshotSound() {
  if (state.settings.muted || state.settings.sfxVolume === 0) return;
  const audio = ensureAudio();
  if (!audio) return;
  if (audio.state === "suspended") audio.resume().catch(() => {});
  const vol = (state.settings.sfxVolume / 100) * (state.settings.masterVolume / 100);
  const now = audio.currentTime;

  const bufSize = Math.floor(audio.sampleRate * 0.18);
  const buf = audio.createBuffer(1, bufSize, audio.sampleRate);
  const data = buf.getChannelData(0);
  for (let i = 0; i < bufSize; i++) data[i] = (Math.random() * 2 - 1);
  const noiseSrc = audio.createBufferSource();
  noiseSrc.buffer = buf;
  const hp = audio.createBiquadFilter();
  hp.type = "highpass";
  hp.frequency.value = 1200;
  const noiseGain = audio.createGain();
  noiseGain.gain.setValueAtTime(0.0001, now);
  noiseGain.gain.exponentialRampToValueAtTime(0.45 * vol, now + 0.002);
  noiseGain.gain.exponentialRampToValueAtTime(0.12 * vol, now + 0.05);
  noiseGain.gain.exponentialRampToValueAtTime(0.0001, now + 0.18);
  noiseSrc.connect(hp).connect(noiseGain).connect(audio.destination);
  noiseSrc.start(now);
  noiseSrc.stop(now + 0.2);

  const thumpOsc = audio.createOscillator();
  const thumpGain = audio.createGain();
  thumpOsc.type = "sine";
  thumpOsc.frequency.setValueAtTime(110, now);
  thumpOsc.frequency.exponentialRampToValueAtTime(40, now + 0.12);
  thumpGain.gain.setValueAtTime(0.0001, now);
  thumpGain.gain.exponentialRampToValueAtTime(0.6 * vol, now + 0.005);
  thumpGain.gain.exponentialRampToValueAtTime(0.0001, now + 0.15);
  thumpOsc.connect(thumpGain).connect(audio.destination);
  thumpOsc.start(now);
  thumpOsc.stop(now + 0.18);
}

function playCountdownSound(index) {
  if (index < 3) { playTone(440, 0.07, "sine", 0.05); } else { playChord([523, 659, 784], 0.2, 0.04); }
}

function ensureAudio() {
  if (state.audio) return state.audio;
  const AC = window.AudioContext || window.webkitAudioContext;
  if (!AC) return null;
  state.audio = new AC();
  return state.audio;
}

function playTone(frequency, duration, type = "sine", gainValue = 0.05) {
  if (state.settings.muted || state.settings.sfxVolume === 0) return;
  const audio = ensureAudio();
  if (!audio) return;
  if (audio.state === "suspended") audio.resume().catch(() => {});
  const osc = audio.createOscillator();
  const gain = audio.createGain();
  osc.type = type;
  osc.frequency.value = frequency;
  gain.gain.value = gainValue * (state.settings.sfxVolume / 100) * (state.settings.masterVolume / 100);
  osc.connect(gain);
  gain.connect(audio.destination);
  const now = audio.currentTime;
  gain.gain.setValueAtTime(0.0001, now);
  gain.gain.exponentialRampToValueAtTime(Math.max(0.0002, gain.gain.value), now + 0.005);
  gain.gain.exponentialRampToValueAtTime(0.0001, now + duration);
  osc.start(now);
  osc.stop(now + duration + 0.03);
}

function playChord(frequencies, duration, gainValue = 0.05) {
  frequencies.forEach((f, i) => playTone(f, duration, i % 2 === 0 ? "triangle" : "sine", gainValue));
}

/* ── Loop ── */

function startLoop() {
  const loop = (now) => {
    requestAnimationFrame(loop);
    const delta = Math.min(0.05, (now - state.lastFrameTime) / 1000);
    state.lastFrameTime = now;
    if (state.screen === "playing" || state.screen === "countdown") updateHud();

    const smoothFactor = 1 - Math.exp(-60 * delta);
    state.yaw += (state.targetYaw - state.yaw) * smoothFactor;
    state.pitch += (state.targetPitch - state.pitch) * smoothFactor;
    if (Math.abs(state.targetYaw - state.yaw) < 0.0001) state.yaw = state.targetYaw;
    if (Math.abs(state.targetPitch - state.pitch) < 0.0001) state.pitch = state.targetPitch;
    if (state.camera) {
      state.camera.rotation.y = state.yaw;
      state.camera.rotation.x = state.pitch;
    }

    if (state.screen !== "playing" && state.screen !== "countdown") {
      state.targetYaw *= 0.88;
      state.targetPitch *= 0.88;
    }

    if (state.gunMixer) state.gunMixer.update(delta);

    if (state.gunKickBack > 0.001 || state.gunKickUp < -0.001 || state.gunKickPitch > 0.001) {
      state.gunKickBack *= Math.max(0, 1 - 14 * delta);
      state.gunKickUp *= Math.max(0, 1 - 14 * delta);
      state.gunKickPitch *= Math.max(0, 1 - 12 * delta);
      const gun = state.camera.children.find(c => c.userData && c.userData.isGun);
      if (gun) {
        gun.position.z = state.gunRestPos.z + state.gunKickBack;
        gun.position.y = state.gunRestPos.y + state.gunKickUp;
        gun.rotation.x = state.gunRestPitch + state.gunKickPitch;
      }
    }

    updateShells(delta);
    updateFovAnim();

    if (state.renderer && state.scene && state.camera) {
      state.renderer.render(state.scene, state.camera);
    }
  };
  requestAnimationFrame(loop);
}

/* ── Utilities ── */

function randomRange(min, max) { return Math.random() * (max - min) + min; }
function clamp(value, min, max) { return Math.min(max, Math.max(min, value)); }

/* ── Multiplayer postMessage API ── */
function sendToParent(type, data) {
  try { window.parent.postMessage(Object.assign({type: type}, data || {}), '*'); } catch(e) {}
}
function sendProgress(data) { sendToParent('progress', {data: data}); }
function sendComplete(data) { sendToParent('complete', {data: data}); }

window.addEventListener('message', function(e) {
  var msg = e.data || {};
  if (msg.type === 'start') {
    var mode = msg.challenge && msg.challenge.mode ? msg.challenge.mode : 'gridshot';
    if (!MODE_CONFIGS[mode]) mode = 'gridshot';
    startMode(mode);
  } else if (msg.type === 'opponent_progress') {
    var d = msg.data || {};
    var oppBar = document.getElementById('oppBar');
    var oppVal = document.getElementById('oppVal');
    var oppTracker = document.getElementById('oppTracker');
    if (oppBar) oppBar.style.width = (d.percent_complete || 0) + '%';
    if (oppVal) oppVal.textContent = 'Score ' + (d.score || 0);
    if (oppTracker) oppTracker.classList.add('show');
  }
});

/* Hook handleHit and finishGame to send multiplayer messages */
(function() {
  var origHandleHit = handleHit;
  handleHit = function(target, event) {
    origHandleHit(target, event);
    var config = MODE_CONFIGS[state.modeKey];
    var duration = config ? config.duration : 30;
    var elapsed = Math.max(0.001, (performance.now() - state.gameStartTime) / 1000);
    sendProgress({score: state.score, hits: state.hits, time_remaining: Math.max(0, duration - elapsed), percent_complete: Math.min(100, Math.round(elapsed / duration * 100))});
  };

  var origFinishGame = finishGame;
  finishGame = function() {
    origFinishGame();
    sendComplete({score: state.score, hits: state.hits, accuracy: getAccuracy(), grade: getGrade()});
  };
})();

sendToParent('ready');
