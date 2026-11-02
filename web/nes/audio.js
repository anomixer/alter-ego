// Audio output for the Alter Ego web player.
//
// jsnes' Browser normally plays through an AudioWorklet module that it loads
// from a blob: URL.  Chrome never loads that module when the page is opened
// from file:// (the promise does not even settle), so the game runs with no
// sound and no error.  This module replaces that path with a ScriptProcessor
// node, which works from file:// and http:// alike, and resamples jsnes'
// 44.1 kHz stream to whatever rate the browser's AudioContext runs at.

(function (global) {
  "use strict";

  const SOURCE_RATE = 44100; // jsnes' papu rate in this player (see app.js)
  const RING_SECONDS = 0.4;  // capacity of the sample ring
  const START_SECONDS = 0.1; // pre-buffer before playback starts

  function create() {
    const Ctor = global.AudioContext || global.webkitAudioContext;
    if (!Ctor) return null;

    const ctx = new Ctor();
    const gain = ctx.createGain();
    gain.gain.value = 0.9;
    gain.connect(ctx.destination);

    const node = ctx.createScriptProcessor(2048, 1, 2);
    node.connect(gain);

    const cap = Math.ceil(RING_SECONDS * SOURCE_RATE);
    const ringL = new Float32Array(cap);
    const ringR = new Float32Array(cap);
    const step = SOURCE_RATE / ctx.sampleRate;
    const startSamples = Math.ceil(START_SECONDS * SOURCE_RATE);

    let written = 0; // source samples received from jsnes
    let readPos = 0; // float read cursor, in source samples
    let primed = false;
    let muted = false;
    let volume = 0.9;

    // Called from jsnes for every emulated audio sample.
    function pushSample(l, r) {
      if (muted) return;
      const w = written % cap;
      ringL[w] = l;
      ringR[w] = r;
      written += 1;
      // Never let the writer lap the reader; drop the oldest audio instead.
      if (written - readPos > cap - 2) readPos = written - (cap - 2);
    }

    // Fill two float buffers (linear resample SOURCE_RATE -> ctx.sampleRate).
    function processInto(outL, outR) {
      const n = outL.length;
      for (let i = 0; i < n; i++) {
        const avail = written - readPos;
        if (!primed) {
          if (avail >= startSamples) primed = true;
          else { outL[i] = 0; outR[i] = 0; continue; }
        }
        if (avail < 2) {
          outL[i] = 0;
          outR[i] = 0;
          readPos = written;
          primed = false;
          continue;
        }
        const base = Math.floor(readPos);
        const frac = readPos - base;
        const i0 = base % cap;
        const i1 = (base + 1) % cap;
        outL[i] = ringL[i0] + (ringL[i1] - ringL[i0]) * frac;
        outR[i] = ringR[i0] + (ringR[i1] - ringR[i0]) * frac;
        readPos += step;
      }
    }

    node.onaudioprocess = (event) => {
      const outL = event.outputBuffer.getChannelData(0);
      const outR = event.outputBuffer.getChannelData(1);
      if (muted) {
        outL.fill(0);
        outR.fill(0);
        readPos = written;
        primed = false;
        return;
      }
      processInto(outL, outR);
    };

    return {
      ctx,
      node,
      gain,
      pushSample,
      processInto,
      get written() { return written; },
      get buffered() { return Math.max(0, written - Math.floor(readPos)); },
      resume() {
        if (ctx.state === "suspended") return ctx.resume();
        return Promise.resolve();
      },
      setMuted(m) {
        muted = !!m;
        gain.gain.value = muted ? 0 : volume;
      },
      get muted() { return muted; },
      setVolume(v) {
        volume = Math.min(1, Math.max(0, v));
        gain.gain.value = muted ? 0 : volume;
        return volume;
      },
      get volume() { return volume; },
      close() {
        try { node.disconnect(); gain.disconnect(); ctx.close(); } catch (e) { /* already gone */ }
      },
    };
  }

  global.AlterEgoAudio = { create, SOURCE_RATE };
})(window);
