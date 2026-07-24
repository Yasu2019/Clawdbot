import {
  BUILDINGS, DAY_LENGTH, GRID, canAfford, defenseStrength, phaseAt,
  populationCap, productionPerSecond, purchase, resolveRaid, validCell
} from "./rules.js";

const canvas = document.querySelector("#game");
const ctx = canvas.getContext("2d");
const ui = {
  menu: document.querySelector("#menu"),
  hud: document.querySelector("#hud"),
  buildbar: document.querySelector("#buildbar"),
  modal: document.querySelector("#modal"),
  modalTitle: document.querySelector("#modalTitle"),
  modalBody: document.querySelector("#modalBody"),
  modalAction: document.querySelector("#modalAction"),
  toast: document.querySelector("#toast"),
  newGame: document.querySelector("#newGame"),
  continueGame: document.querySelector("#continueGame"),
  howToPlay: document.querySelector("#howToPlay"),
  quitGame: document.querySelector("#quitGame"),
  pause: document.querySelector("#pause")
};
const SAVE_KEY = "bunny-colony-save-v1";
const MAX_DAY = 7;
let state = null;
let selectedBuild = null;
let previousTime = performance.now();
let toastTimer = 0;
let particles = [];
let modalCallback = null;

function freshState() {
  return {
    day: 1, elapsed: 0, carrots: 32, wood: 42, bunnies: 4, happiness: 82,
    buildings: [{ type: "burrow", col: 5, row: 3 }],
    paused: false, ended: false, raidResolved: false, autosaveAt: 0
  };
}

function loadSave() {
  try {
    const parsed = JSON.parse(localStorage.getItem(SAVE_KEY));
    if (!parsed || parsed.version !== 1 || !parsed.state) return null;
    return { ...freshState(), ...parsed.state, paused: false };
  } catch {
    return null;
  }
}

function saveGame() {
  if (!state || state.ended) return;
  localStorage.setItem(SAVE_KEY, JSON.stringify({ version: 1, savedAt: Date.now(), state }));
}

function startGame(saved = null) {
  state = saved || freshState();
  selectedBuild = null;
  particles = [];
  ui.menu.classList.add("hidden");
  ui.modal.classList.add("hidden");
  ui.hud.classList.remove("hidden");
  ui.buildbar.classList.remove("hidden");
  updateHud();
  showToast(saved ? "コロニーへ、おかえりなさい" : "最初の畑を建てて、仲間を育てよう");
}

function returnToMenu() {
  saveGame();
  state = null;
  ui.hud.classList.add("hidden");
  ui.buildbar.classList.add("hidden");
  ui.modal.classList.add("hidden");
  ui.menu.classList.remove("hidden");
  refreshContinue();
}

function refreshContinue() {
  ui.continueGame.disabled = !loadSave();
}

function openModal(title, html, button = "閉じる", callback = null) {
  if (state) state.paused = true;
  ui.modalTitle.textContent = title;
  ui.modalBody.innerHTML = html;
  ui.modalAction.textContent = button;
  modalCallback = callback;
  ui.modal.classList.remove("hidden");
}

function closeModal() {
  ui.modal.classList.add("hidden");
  const callback = modalCallback;
  modalCallback = null;
  if (callback) callback();
  else if (state && !state.ended) state.paused = false;
}

function togglePause() {
  if (!state || state.ended) return;
  if (!ui.modal.classList.contains("hidden")) {
    closeModal();
    return;
  }
  openModal("一時停止", "<p>森の時間もひと休み。</p><p>進行状況は自動保存されています。</p>", "ゲームに戻る");
  const menuButton = document.createElement("button");
  menuButton.textContent = "タイトルへ戻る";
  menuButton.addEventListener("click", returnToMenu, { once: true });
  ui.modalBody.append(menuButton);
}

function showToast(message) {
  ui.toast.textContent = message;
  ui.toast.classList.remove("hidden");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => ui.toast.classList.add("hidden"), 2300);
}

function updateHud() {
  if (!state) return;
  const phase = phaseAt(state.elapsed);
  document.querySelector("#carrots").textContent = Math.floor(state.carrots);
  document.querySelector("#wood").textContent = Math.floor(state.wood);
  document.querySelector("#bunnies").textContent = `${state.bunnies}/${populationCap(state.buildings)}`;
  document.querySelector("#happiness").textContent = `${Math.floor(state.happiness)}%`;
  document.querySelector("#phase").textContent = `${state.day}日目・${phase.name}`;
  document.querySelector("#timer").textContent = `${Math.floor(state.elapsed)} / ${DAY_LENGTH}秒`;
  document.querySelectorAll("[data-build]").forEach((button) => {
    button.classList.toggle("selected", button.dataset.build === selectedBuild);
    button.disabled = !canAfford(state, button.dataset.build);
  });
}

function selectBuilding(type) {
  if (!state || state.paused || !canAfford(state, type)) return;
  selectedBuild = selectedBuild === type ? null : type;
  updateHud();
}

function placeBuilding(event) {
  if (!state || state.paused || !selectedBuild) return;
  const bounds = canvas.getBoundingClientRect();
  const x = (event.clientX - bounds.left) * canvas.width / bounds.width;
  const y = (event.clientY - bounds.top) * canvas.height / bounds.height;
  const col = Math.floor((x - GRID.left) / GRID.cell);
  const row = Math.floor((y - GRID.top) / GRID.cell);
  if (!validCell(state.buildings, col, row)) {
    showToast("空いている草地を選んでください");
    return;
  }
  const paid = purchase(state, selectedBuild);
  if (!paid) return;
  state.carrots = paid.carrots;
  state.wood = paid.wood;
  state.buildings.push({ type: selectedBuild, col, row });
  burst(GRID.left + col * GRID.cell + 36, GRID.top + row * GRID.cell + 36, "#fff2ce");
  showToast(`${BUILDINGS[selectedBuild].label}を建てました`);
  selectedBuild = null;
  saveGame();
  updateHud();
}

function simulate(dt) {
  if (!state || state.paused || state.ended) return;
  state.elapsed += dt;
  const phase = phaseAt(state.elapsed);
  if (phase.name !== "夜") {
    const rates = productionPerSecond(state.buildings, state.bunnies);
    state.carrots += rates.carrots * dt;
    state.wood += rates.wood * dt;
    const cap = populationCap(state.buildings);
    if (state.bunnies < cap && state.carrots >= 14 && state.happiness >= 45) {
      const chance = dt * 0.055 * state.buildings.filter((b) => b.type === "burrow").length;
      if (Math.random() < chance) {
        state.carrots -= 14;
        state.bunnies += 1;
        state.happiness = Math.min(100, state.happiness + 2);
        showToast("新しいウサギが仲間になりました！");
      }
    }
  }
  if (phase.name === "夜" && !state.raidResolved) {
    state.raidResolved = true;
    const result = resolveRaid(state);
    state.bunnies = result.bunnies;
    state.happiness = result.happiness;
    const message = result.lost
      ? `キツネ襲来！ 防衛 ${result.defense} / 脅威 ${result.attack}・仲間を${result.lost}羽失いました`
      : `防衛成功！ 見張り台がコロニーを守りました`;
    showToast(message);
  }
  if (state.elapsed >= DAY_LENGTH) advanceDay();
  if (state.elapsed - state.autosaveAt >= 10) {
    state.autosaveAt = state.elapsed;
    saveGame();
  }
  updateHud();
}

function advanceDay() {
  if (state.bunnies <= 1 || state.happiness <= 0) {
    finish(false);
    return;
  }
  if (state.day >= MAX_DAY) {
    finish(true);
    return;
  }
  state.day += 1;
  state.elapsed = 0;
  state.autosaveAt = 0;
  state.raidResolved = false;
  state.carrots = Math.max(0, state.carrots - state.bunnies * 1.5);
  state.happiness = Math.min(100, state.happiness + 4);
  saveGame();
  showToast(`${state.day}日目の朝です`);
}

function finish(won) {
  state.ended = true;
  state.paused = true;
  if (won) localStorage.setItem("bunny-colony-best", String(state.bunnies));
  localStorage.removeItem(SAVE_KEY);
  openModal(
    won ? "コロニーは安住の地へ" : "森に静けさが戻りました",
    won
      ? `<p>7つの夜を越え、${state.bunnies}羽の仲間が暮らすコロニーを築きました。</p><p>あなたの森は、これからも成長を続けます。</p>`
      : "<p>仲間か幸福度を守れませんでした。畑を早めに建て、夜までに見張り台を増やしてみましょう。</p>",
    "タイトルへ",
    returnToMenu
  );
}

function burst(x, y, color) {
  for (let i = 0; i < 18; i += 1) {
    particles.push({ x, y, vx: (Math.random() - .5) * 90, vy: -30 - Math.random() * 80, life: 1, color });
  }
}

function roundedRect(x, y, width, height, radius) {
  ctx.beginPath();
  ctx.roundRect(x, y, width, height, radius);
}

function drawRabbit(x, y, scale = 1, color = "#f5ead8") {
  ctx.save();
  ctx.translate(x, y);
  ctx.scale(scale, scale);
  ctx.fillStyle = color;
  ctx.beginPath(); ctx.ellipse(-6, -16, 5, 15, -.2, 0, Math.PI * 2); ctx.fill();
  ctx.beginPath(); ctx.ellipse(6, -16, 5, 15, .2, 0, Math.PI * 2); ctx.fill();
  ctx.beginPath(); ctx.arc(0, 0, 14, 0, Math.PI * 2); ctx.fill();
  ctx.fillStyle = "#28332c";
  ctx.beginPath(); ctx.arc(-5, -2, 1.8, 0, Math.PI * 2); ctx.arc(5, -2, 1.8, 0, Math.PI * 2); ctx.fill();
  ctx.restore();
}

function drawBuilding(building) {
  const x = GRID.left + building.col * GRID.cell + 36;
  const y = GRID.top + building.row * GRID.cell + 38;
  ctx.save();
  if (building.type === "farm") {
    ctx.fillStyle = "#8a6039"; ctx.fillRect(x - 26, y - 20, 52, 42);
    ctx.strokeStyle = "#deb05b"; ctx.lineWidth = 4;
    for (let row = -12; row <= 12; row += 12) { ctx.beginPath(); ctx.moveTo(x - 22, y + row); ctx.lineTo(x + 22, y + row); ctx.stroke(); }
    ctx.fillStyle = "#e8793d";
    for (let col = -18; col <= 18; col += 12) { ctx.beginPath(); ctx.arc(x + col, y, 3, 0, Math.PI * 2); ctx.fill(); }
  } else if (building.type === "burrow") {
    ctx.fillStyle = "#6b4c35"; ctx.beginPath(); ctx.arc(x, y + 9, 28, Math.PI, 0); ctx.fill();
    ctx.fillStyle = "#263329"; ctx.beginPath(); ctx.arc(x, y + 10, 13, Math.PI, 0); ctx.fill();
    drawRabbit(x + 23, y + 13, .55);
  } else if (building.type === "lumber") {
    ctx.strokeStyle = "#634934"; ctx.lineWidth = 7; ctx.beginPath(); ctx.moveTo(x, y + 23); ctx.lineTo(x, y - 12); ctx.stroke();
    ctx.fillStyle = "#668353"; ctx.beginPath(); ctx.arc(x, y - 14, 23, 0, Math.PI * 2); ctx.fill();
    ctx.fillStyle = "#886344"; ctx.fillRect(x + 12, y + 12, 22, 10);
  } else {
    ctx.fillStyle = "#725743"; ctx.fillRect(x - 18, y - 12, 36, 35);
    ctx.strokeStyle = "#d0a86a"; ctx.lineWidth = 5;
    ctx.beginPath(); ctx.moveTo(x - 20, y + 25); ctx.lineTo(x - 13, y - 30); ctx.moveTo(x + 20, y + 25); ctx.lineTo(x + 13, y - 30); ctx.stroke();
    ctx.fillStyle = "#8b735c"; ctx.fillRect(x - 25, y - 32, 50, 13);
  }
  ctx.restore();
}

function drawScene(time) {
  const phase = state ? phaseAt(state.elapsed) : phaseAt(8);
  const background = ctx.createLinearGradient(0, 0, 0, canvas.height);
  background.addColorStop(0, state && phase.name === "夜" ? "#172746" : "#799e79");
  background.addColorStop(1, state && phase.name === "夜" ? "#24382e" : "#c8b978");
  ctx.fillStyle = background;
  ctx.fillRect(0, 0, canvas.width, canvas.height);

  ctx.fillStyle = state && phase.name === "夜" ? "#e7e0ba" : "#f4d78c";
  ctx.beginPath(); ctx.arc(1100, 104, 45, 0, Math.PI * 2); ctx.fill();
  for (let i = 0; i < 9; i += 1) {
    const x = 30 + i * 155;
    const height = 90 + (i % 3) * 24;
    ctx.fillStyle = i % 2 ? "#2e513a" : "#345c40";
    ctx.beginPath(); ctx.moveTo(x, 185); ctx.lineTo(x + 55, 185 - height); ctx.lineTo(x + 110, 185); ctx.fill();
  }

  if (!state) {
    for (let i = 0; i < 11; i += 1) {
      drawRabbit(660 + (i % 5) * 90 + Math.sin(time / 700 + i) * 10, 450 + Math.floor(i / 5) * 72, .8);
    }
    return;
  }

  ctx.fillStyle = "rgba(57, 82, 48, .82)";
  roundedRect(GRID.left - 12, GRID.top - 12, GRID.columns * GRID.cell + 24, GRID.rows * GRID.cell + 24, 22); ctx.fill();
  ctx.strokeStyle = "rgba(255,255,255,.08)"; ctx.lineWidth = 1;
  for (let col = 0; col <= GRID.columns; col += 1) {
    ctx.beginPath(); ctx.moveTo(GRID.left + col * GRID.cell, GRID.top); ctx.lineTo(GRID.left + col * GRID.cell, GRID.top + GRID.rows * GRID.cell); ctx.stroke();
  }
  for (let row = 0; row <= GRID.rows; row += 1) {
    ctx.beginPath(); ctx.moveTo(GRID.left, GRID.top + row * GRID.cell); ctx.lineTo(GRID.left + GRID.columns * GRID.cell, GRID.top + row * GRID.cell); ctx.stroke();
  }
  state.buildings.forEach(drawBuilding);
  for (let i = 0; i < state.bunnies; i += 1) {
    const angle = time / 2100 + i * 2.4;
    const x = 640 + Math.cos(angle) * (95 + (i % 5) * 35);
    const y = 380 + Math.sin(angle * 1.35) * (65 + (i % 3) * 28);
    drawRabbit(x, y, .52);
  }
  if (phase.name === "夜") {
    ctx.fillStyle = "rgba(15, 25, 45, .25)"; ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.fillStyle = "#e7ad66"; ctx.font = "700 15px sans-serif";
    ctx.fillText(`防衛力 ${defenseStrength(state.buildings, state.bunnies)}`, 1070, 104);
  }
}

function drawParticles(dt) {
  particles.forEach((particle) => {
    particle.x += particle.vx * dt;
    particle.y += particle.vy * dt;
    particle.vy += 150 * dt;
    particle.life -= dt * 1.3;
    ctx.globalAlpha = Math.max(0, particle.life);
    ctx.fillStyle = particle.color;
    ctx.beginPath(); ctx.arc(particle.x, particle.y, 3, 0, Math.PI * 2); ctx.fill();
  });
  ctx.globalAlpha = 1;
  particles = particles.filter((particle) => particle.life > 0);
}

function frame(time) {
  const dt = Math.min(.05, (time - previousTime) / 1000);
  previousTime = time;
  simulate(dt);
  drawScene(time);
  drawParticles(dt);
  requestAnimationFrame(frame);
}

ui.newGame.addEventListener("click", () => startGame());
ui.continueGame.addEventListener("click", () => startGame(loadSave()));
ui.howToPlay.addEventListener("click", () => openModal("遊び方", `
  <ul>
    <li>昼に畑と木こり場を建て、資源を集めます。</li>
    <li>巣穴は人口上限を増やし、見張り台は夜のキツネを防ぎます。</li>
    <li>建物を選び、草地のマスをクリックして建設します。</li>
    <li>1～4キーで建物、Escで一時停止。7日目の夜を越えると勝利です。</li>
  </ul>`, "はじめよう"));
ui.quitGame.addEventListener("click", () => window.close());
ui.modalAction.addEventListener("click", closeModal);
ui.pause.addEventListener("click", togglePause);
document.querySelectorAll("[data-build]").forEach((button) => button.addEventListener("click", () => selectBuilding(button.dataset.build)));
canvas.addEventListener("pointerdown", placeBuilding);
window.addEventListener("keydown", (event) => {
  if (event.key === "Escape") togglePause();
  const type = { "1": "burrow", "2": "farm", "3": "lumber", "4": "watch" }[event.key];
  if (type) selectBuilding(type);
});
window.addEventListener("beforeunload", saveGame);
refreshContinue();
requestAnimationFrame(frame);
