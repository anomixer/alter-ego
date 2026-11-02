// Alter Ego web player: a thin wrapper around jsnes 2.x.
//
// jsnes' Browser handles the canvas, keyboard/gamepad mapping and frame pacing.
// Its audio path (an AudioWorklet loaded from a blob: URL) never starts when
// the page is opened from file://, so the sound is produced by audio.js
// instead: papu's onAudioSample feeds our own ScriptProcessorNode.

const host = document.getElementById("screen");
const overlay = document.getElementById("overlay");
const statusEl = document.getElementById("status");
const pauseBtn = document.getElementById("pause");
const muteBtn = document.getElementById("mute");
const volumeInput = document.getElementById("volume");

let browser = null;
let audio = null;
let running = false;
let lastBytes = null;

function setStatus(text) {
  statusEl.textContent = text;
}

function base64ToBytes(b64) {
  const bin = atob(b64);
  const bytes = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
  return bytes;
}

function audioLabel() {
  if (!audio) return "Sound: unavailable";
  const out = Math.round(audio.ctx.sampleRate);
  const how = out === AlterEgoAudio.SOURCE_RATE
    ? `${out} Hz`
    : `${AlterEgoAudio.SOURCE_RATE} Hz→${out} Hz`;
  return `Sound: ${audio.muted ? "muted" : volumeLabel()} (${how})`;
}

function volumeLabel() {
  return `${Math.round(audio.volume * 100)}%`;
}

function refreshAudioLabel() {
  setStatus(`ROM ${romName} · ${romSize.toLocaleString()} bytes · ${audioLabel()}`);
}

let romName = "";
let romSize = 0;

// The AudioContext must be created from a user gesture (browser autoplay rule),
// so this only runs from the overlay click.
function ensureAudio() {
  if (audio) {
    audio.resume();
    return audio;
  }
  audio = window.AlterEgoAudio ? AlterEgoAudio.create() : null;
  if (!audio) {
    setStatus("This browser has no WebAudio; the game will be silent.");
  }
  return audio;
}

function boot(bytes, name) {
  if (browser) {
    browser.destroy();
    browser = null;
  }
  ensureAudio();
  browser = new jsnes.Browser({
    container: host,
    onError: (e) => setStatus(`Emulator error: ${e}`),
  });
  // jsnes would start its own AudioWorklet here; ours is audio.js, so keep the
  // frame timer (Browser.start) but skip the speakers it cannot start on file://.
  browser._speakers.start = () => {};
  // Our own input layer handles the pad (see "input" below); clear jsnes' map so
  // the same key press is not applied twice, and so nothing saved in
  // localStorage by another jsnes page remaps the keys.
  browser.keyboard.keys = {};
  releasePads();
  if (audio) browser.nes.opts.onAudioSample = audio.pushSample;
  browser.loadROM(bytes);
  lastBytes = bytes;
  lastExchange = null;
  running = true;
  pauseBtn.textContent = "Pause";
  overlay.hidden = true;
  romName = name;
  romSize = bytes.length;
  refreshAudioLabel();
}

// Preferred source: the base64 copy written by build-rom.mjs, which also makes
// this page work straight from file:// (fetch() is blocked there).
async function bootInline() {
  if (window.AE_ROM_B64) {
    boot(base64ToBytes(window.AE_ROM_B64), "build/alterego.nes (embedded)");
    return true;
  }
  try {
    const response = await fetch("build/alterego.nes");
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    boot(new Uint8Array(await response.arrayBuffer()), "build/alterego.nes");
    return true;
  } catch (e) {
    setStatus(`No ROM available (${e.message}) — run node build-rom.mjs first, or use "Load another .nes"`);
    return false;
  }
}

overlay.addEventListener("click", async () => {
  overlay.hidden = true;
  overlay.blur();
  const ok = await bootInline();
  if (!ok) overlay.hidden = false;
  else if (audio) audio.resume();
});

// A real reset: jsnes' NES.reset() rebuilds the cpu/ppu/papu but not the mapper,
// which left the game wedged.  Booting the ROM again is what "reset" means anyway.
function restart() {
  if (!browser || !lastBytes) return;
  boot(lastBytes, romName);
}

document.getElementById("reset").addEventListener("click", restart);

pauseBtn.addEventListener("click", () => {
  if (!browser) return;
  if (running) {
    browser.stop();
    running = false;
    pauseBtn.textContent = "Resume";
  } else {
    browser.start();
    running = true;
    pauseBtn.textContent = "Pause";
  }
});

muteBtn.addEventListener("click", () => {
  if (!audio) return;
  audio.setMuted(!audio.muted);
  muteBtn.textContent = audio.muted ? "Unmute" : "Mute";
  refreshAudioLabel();
});

volumeInput.addEventListener("input", () => {
  if (!audio) return;
  audio.setVolume(volumeInput.value / 100);
  refreshAudioLabel();
});

document.getElementById("fullscreen").addEventListener("click", () => {
  const stage = document.getElementById("stage");
  if (document.fullscreenElement) document.exitFullscreen();
  else stage.requestFullscreen?.();
});

const picker = document.getElementById("file");
document.getElementById("pick").addEventListener("click", () => picker.click());
picker.addEventListener("change", async () => {
  const file = picker.files?.[0];
  if (!file) return;
  boot(new Uint8Array(await file.arrayBuffer()), file.name);
});

// Drag and drop a .nes anywhere on the page.
for (const type of ["dragenter", "dragover"]) {
  document.addEventListener(type, (e) => {
    e.preventDefault();
    document.body.classList.add("dragging");
  });
}
for (const type of ["dragleave", "drop"]) {
  document.addEventListener(type, (e) => {
    e.preventDefault();
    document.body.classList.remove("dragging");
  });
}
document.addEventListener("drop", async (e) => {
  const file = e.dataTransfer?.files?.[0];
  if (!file) return;
  boot(new Uint8Array(await file.arrayBuffer()), file.name);
});

// --- input ------------------------------------------------------------------
// jsnes' own keyboard map is keyed by `event.keyCode`, which is the wrong tool
// here: with a Chinese IME letters arrive as keyCode 229, and a `keys` table a
// previous jsnes page left in localStorage can remap the pad.  Physical keys are
// reported in `event.code` even during composition, so this layer maps them
// straight onto the pad and jsnes' map is switched off in boot().
//
// The IME also swallows the *keyup* of a letter (it becomes key "Process" /
// keyCode 229 with no code).  A button left down that way is fatal: the ROM only
// accepts an exchange while A/B are released after the previous one, so it then
// refuses every press for ever.  Action buttons are therefore taps -- they are
// released 400 ms after going down unless the keyup arrives sooner -- while the
// direction keys stay hold-to-walk.
const PAD = jsnes.Controller;
const CODE_TO_PAD = {
  ArrowUp: PAD.BUTTON_UP,
  ArrowDown: PAD.BUTTON_DOWN,
  ArrowLeft: PAD.BUTTON_LEFT,
  ArrowRight: PAD.BUTTON_RIGHT,
  KeyX: PAD.BUTTON_A,
  KeyZ: PAD.BUTTON_B,
  Space: PAD.BUTTON_START,
  Enter: PAD.BUTTON_START,
  NumpadEnter: PAD.BUTTON_START,
  ControlLeft: PAD.BUTTON_SELECT,
  ControlRight: PAD.BUTTON_SELECT,
  Numpad7: PAD.BUTTON_A,
  Numpad9: PAD.BUTTON_B,
  Numpad1: PAD.BUTTON_START,
  Numpad3: PAD.BUTTON_SELECT,
};
const NAME_TO_PAD = {
  arrowup: PAD.BUTTON_UP,
  arrowdown: PAD.BUTTON_DOWN,
  arrowleft: PAD.BUTTON_LEFT,
  arrowright: PAD.BUTTON_RIGHT,
  x: PAD.BUTTON_A,
  z: PAD.BUTTON_B,
  enter: PAD.BUTTON_START,
  " ": PAD.BUTTON_START,
  control: PAD.BUTTON_SELECT,
};
const PAD_NAMES = {
  [PAD.BUTTON_A]: "A",
  [PAD.BUTTON_B]: "B",
  [PAD.BUTTON_SELECT]: "SELECT",
  [PAD.BUTTON_START]: "START",
  [PAD.BUTTON_UP]: "UP",
  [PAD.BUTTON_DOWN]: "DOWN",
  [PAD.BUTTON_LEFT]: "LEFT",
  [PAD.BUTTON_RIGHT]: "RIGHT",
};
const PAD_BUTTONS = {
  a: PAD.BUTTON_A,
  b: PAD.BUTTON_B,
  select: PAD.BUTTON_SELECT,
  start: PAD.BUTTON_START,
  up: PAD.BUTTON_UP,
  down: PAD.BUTTON_DOWN,
  left: PAD.BUTTON_LEFT,
  right: PAD.BUTTON_RIGHT,
};
const heldPads = new Set();
const padTimers = new Map();
const PRESS_MS = 400;
const last = { code: "-", key: "-", keyCode: 0 };
let lastPad = "-";

function padFromEvent(event) {
  const byCode = CODE_TO_PAD[event.code];
  if (byCode !== undefined) return byCode;
  return NAME_TO_PAD[String(event.key).toLowerCase()];
}

function pressPad(pad) {
  if (heldPads.has(pad)) return;
  heldPads.add(pad);
  if (browser) browser.nes.buttonDown(1, pad);
  lastPad = PAD_NAMES[pad] ?? String(pad);
  if (pad < PAD.BUTTON_UP) {
    clearTimeout(padTimers.get(pad));
    padTimers.set(pad, setTimeout(() => releasePad(pad), PRESS_MS));
  }
}

function releasePad(pad) {
  clearTimeout(padTimers.get(pad));
  padTimers.delete(pad);
  heldPads.delete(pad);
  if (browser) browser.nes.buttonUp(1, pad);
}

function releasePads() {
  for (const pad of [...heldPads]) releasePad(pad);
}

// Direction keys stay held while walking; the action buttons are taps.
function releaseActionPads() {
  for (const pad of [...heldPads]) if (pad < PAD.BUTTON_UP) releasePad(pad);
}

function toggleFullscreen() {
  const stage = document.getElementById("stage");
  if (document.fullscreenElement) document.exitFullscreen();
  else stage.requestFullscreen?.();
}

document.addEventListener("keydown", (event) => {
  if (audio) audio.resume();
  last.code = event.code || "-";
  last.key = event.key || "-";
  last.keyCode = event.keyCode;
  const pad = padFromEvent(event);
  if (pad !== undefined) {
    // Let the volume slider keep its arrow keys while it has focus.
    const sliderFocused = event.target instanceof HTMLInputElement;
    const isArrow = pad >= PAD.BUTTON_UP;
    if (sliderFocused && isArrow) return;
    event.preventDefault();
    if (event.repeat) return; // auto-repeat is not a new press
    pressPad(pad);
    return;
  }
  if (event.repeat) return;
  if (event.code === "KeyR") { lastPad = "RESET"; restart(); return; }
  if (event.code === "KeyF") { lastPad = "FULLSCREEN"; toggleFullscreen(); }
});

document.addEventListener("keyup", (event) => {
  const pad = padFromEvent(event);
  if (pad !== undefined) {
    event.preventDefault();
    releasePad(pad);
    return;
  }
  // The keyup of an IME-composed key has no usable code ("Process", keyCode
  // 229); do not leave a button down because of it.
  if (event.keyCode === 229 || event.key === "Process" || !event.code) releaseActionPads();
});
document.addEventListener("compositionend", releaseActionPads);

// On-screen pad: pointer events cover mouse, pen and touch.  Releasing first
// makes the button work even if the pad ever thinks it is already down.
for (const button of document.querySelectorAll("#pad button")) {
  const pad = PAD_BUTTONS[button.dataset.pad];
  if (pad === undefined) continue;
  button.addEventListener("pointerdown", (event) => {
    event.preventDefault();
    try { button.setPointerCapture?.(event.pointerId); } catch (e) { /* synthetic events */ }
    lastPad = PAD_NAMES[pad] ?? String(pad);
    releasePad(pad);
    pressPad(pad);
  });
  for (const type of ["pointerup", "pointercancel", "pointerleave"]) {
    button.addEventListener(type, () => releasePad(pad));
  }
  button.addEventListener("contextmenu", (event) => event.preventDefault());
}

window.addEventListener("blur", releasePads);

setStatus("Click the screen to play");

// Small read-only hook for the console: handy when a key seems dead, harmless
// for players.  `hud` reads the two counters the ROM keeps in sprite memory
// (sprite 58 restarts, 59 exchanges; game.c stores 0xe5+n at OAM_STATS+6/+7).
function hudCounters() {
  if (!browser) return null;
  const mem = browser.nes.ppu.spriteMem;
  const restart = mem[58 * 4 + 1] - 0xe5;
  const exchange = mem[59 * 4 + 1] - 0xe5;
  if (restart < 0 || restart > 9 || exchange < 0 || exchange > 9) return null;
  return { restart, exchange };
}

window.__ae = {
  get running() { return running; },
  get fps() { return browser ? browser.nes.getFPS() : 0; },
  get samples() { return audio ? audio.written : 0; },
  get buffered() { return audio ? audio.buffered : 0; },
  get audioState() { return audio ? audio.ctx.state : "none"; },
  get sampleRate() { return audio ? audio.ctx.sampleRate : 0; },
  get lastKey() { return `${last.code} / ${last.key} / ${last.keyCode}`; },
  get lastPad() { return lastPad; },
  get held() { return [...heldPads]; },
  get hud() { return hudCounters(); },
};