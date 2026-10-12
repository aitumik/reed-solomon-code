"use strict";

const state = {
  message: "",
  messageLen: 0,
  nsym: 4,
  t: 0,
  original: [],
  corrupted: new Set(),
};

const els = {
  message: document.getElementById("message"),
  nsym: document.getElementById("nsym"),
  encode: document.getElementById("encode"),
  encodeError: document.getElementById("encode-error"),
  generatorLine: document.getElementById("generator-line"),
  corruptCard: document.getElementById("corrupt-card"),
  decodeCard: document.getElementById("decode-card"),
  tLabel: document.getElementById("t-label"),
  errorValue: document.getElementById("error-value"),
  randomize: document.getElementById("randomize"),
  clear: document.getElementById("clear"),
  errorCount: document.getElementById("error-count"),
  codeword: document.getElementById("codeword"),
  decode: document.getElementById("decode"),
  results: document.getElementById("results"),
};

const hex = (n) => n.toString(16).toUpperCase().padStart(2, "0");

function errorValue() {
  let raw = els.errorValue.value.trim().replace(/^0x/i, "");
  if (!/^[0-9a-fA-F]{1,2}$/.test(raw)) return 0xa5;
  const v = parseInt(raw, 16);
  return v === 0 ? 0xa5 : v;
}

function corruptedCodeword() {
  const xor = errorValue();
  return state.original.map((b, i) => (state.corrupted.has(i) ? b ^ xor : b));
}

/* ---------- Step 1: encode ---------- */

async function encode() {
  els.encodeError.hidden = true;
  const body = { message: els.message.value, nsym: parseInt(els.nsym.value, 10) };

  let data;
  try {
    const res = await fetch("/api/encode", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    data = await res.json();
    if (!res.ok) throw new Error(data.error || "Encoding failed.");
  } catch (err) {
    els.encodeError.textContent = err.message;
    els.encodeError.hidden = false;
    return;
  }

  state.message = data.message;
  state.messageLen = data.message_bytes.length;
  state.nsym = data.nsym;
  state.t = data.t;
  state.original = data.codeword;
  state.corrupted.clear();

  els.tLabel.textContent = String(data.t);
  els.generatorLine.textContent = `G(x) = ${data.generator}`;
  els.generatorLine.hidden = false;

  els.corruptCard.hidden = false;
  els.decodeCard.hidden = false;
  els.results.innerHTML = "";

  renderCodeword();
  updateErrorCount();
}

/* ---------- Step 2: corruption ---------- */

function renderCodeword() {
  els.codeword.innerHTML = "";
  const xor = errorValue();
  const values = corruptedCodeword();

  values.forEach((value, i) => {
    const isParity = i >= state.messageLen;
    const isCorrupt = state.corrupted.has(i);

    const chip = document.createElement("div");
    chip.className = "byte " + (isCorrupt ? "corrupt" : isParity ? "parity" : "message");
    chip.title = isCorrupt
      ? `Byte ${i}: ${hex(state.original[i])} XOR ${hex(xor)} = ${hex(value)}`
      : `Byte ${i} (${isParity ? "parity" : "message"})`;

    const idx = document.createElement("span");
    idx.className = "idx";
    idx.textContent = i;

    const val = document.createElement("span");
    val.className = "val";
    val.textContent = hex(value);

    chip.append(idx, val);

    if (isCorrupt) {
      const was = document.createElement("span");
      was.className = "was";
      was.textContent = `was ${hex(state.original[i])}`;
      chip.append(was);
    }

    chip.addEventListener("click", () => toggleCorrupt(i));
    els.codeword.append(chip);
  });
}

function toggleCorrupt(i) {
  if (state.corrupted.has(i)) {
    state.corrupted.delete(i);
  } else {
    state.corrupted.add(i);
  }
  renderCodeword();
  updateErrorCount();
}

function randomErrors() {
  state.corrupted.clear();
  const count = 1 + Math.floor(Math.random() * state.t);
  const indices = [...state.original.keys()];
  for (let i = indices.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [indices[i], indices[j]] = [indices[j], indices[i]];
  }
  indices.slice(0, count).forEach((i) => state.corrupted.add(i));
  renderCodeword();
  updateErrorCount();
}

function clearErrors() {
  state.corrupted.clear();
  renderCodeword();
  updateErrorCount();
}

function updateErrorCount() {
  const n = state.corrupted.size;
  els.errorCount.textContent = `${n} error${n === 1 ? "" : "s"}`;
  els.errorCount.className = "pill " + (n <= state.t ? "ok" : "bad");
}

/* ---------- Step 3: decode ---------- */

async function decode() {
  els.decode.disabled = true;
  const body = { codeword: corruptedCodeword(), nsym: state.nsym };

  let data;
  try {
    const res = await fetch("/api/decode", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    data = await res.json();
    if (!res.ok) throw new Error(data.error || "Decoding failed.");
  } catch (err) {
    els.results.innerHTML = `<div class="banner bad">${err.message}</div>`;
    els.decode.disabled = false;
    return;
  }

  renderResults(data);
  els.decode.disabled = false;
}

/* ---------- rendering results ---------- */

function chip(label, value, cls) {
  const el = document.createElement("span");
  el.className = "chip" + (cls ? " " + cls : "");
  if (label !== null) {
    const small = document.createElement("small");
    small.textContent = label;
    el.append(small);
  }
  el.append(document.createTextNode(hex(value)));
  return el;
}

function stage(title, desc) {
  const el = document.createElement("div");
  el.className = "stage";
  el.innerHTML = `<h3>${title}</h3>`;
  if (desc) el.insertAdjacentHTML("beforeend", `<p class="desc">${desc}</p>`);
  return el;
}

function renderResults(data) {
  const { steps, corrected, verified } = data;
  els.results.innerHTML = "";

  // Syndromes
  const sStage = stage(
    "Syndromes",
    "Evaluate the received polynomial at the generator roots &alpha;<sup>i</sup>. All zero means a valid codeword."
  );
  const sRow = document.createElement("div");
  sRow.className = "chip-row";
  steps.syndromes.forEach((s) =>
    sRow.append(chip(`S${s.index}`, s.value, s.value === 0 ? "zero" : "nonzero"))
  );
  sStage.append(sRow);
  els.results.append(sStage);

  if (steps.clean) {
    const banner = document.createElement("div");
    banner.className = "banner ok";
    banner.innerHTML = "No errors detected &mdash; the codeword is already valid.";
    els.results.append(banner);
  } else {
    // Error locator
    const lStage = stage(
      "Error locator (Berlekamp&ndash;Massey)",
      "The LFSR that reproduces the syndrome sequence. Its roots point at the error positions."
    );
    const poly = document.createElement("div");
    poly.className = "poly";
    poly.textContent = `\u039B(x) = ${steps.error_locator.pretty}`;
    lStage.append(poly);
    els.results.append(lStage);

    // Chien search
    const roots = steps.chien.filter((c) => c.is_root);
    const cStage = stage(
      "Chien search",
      `Tested every position for a root of &Lambda;(x). Found ${roots.length} root${roots.length === 1 ? "" : "s"}.`
    );
    const cRow = document.createElement("div");
    cRow.className = "chip-row";
    roots.forEach((r) =>
      cRow.append(chip(`byte ${r.index}`, r.x_inv, "root"))
    );
    cStage.append(cRow);
    els.results.append(cStage);

    // Forney
    const fStage = stage(
      "Forney algorithm",
      "Solve for the error magnitude at each located position."
    );
    const fRow = document.createElement("div");
    fRow.className = "chip-row";
    steps.magnitudes.forEach((m) =>
      fRow.append(chip(`byte ${m.index}`, m.value, "nonzero"))
    );
    fStage.append(fRow);
    els.results.append(fStage);
  }

  // Corrected codeword
  const rStage = stage(
    "Corrected codeword",
    "Applying the magnitudes flips the corrupted bytes back to the original codeword."
  );
  const rRow = document.createElement("div");
  rRow.className = "bytes";
  const input = corruptedCodeword();
  corrected.forEach((value, i) => {
    const isParity = i >= state.messageLen;
    const changed = value !== input[i];
    const el = document.createElement("div");
    el.className =
      "byte static " + (changed ? "fixed" : isParity ? "parity" : "message");
    el.innerHTML = `<span class="idx">${i}</span><span class="val">${hex(value)}</span>`;
    rRow.append(el);
  });
  rStage.append(rRow);
  els.results.append(rStage);

  // Recovered message
  const recoveredBytes = corrected.slice(0, state.messageLen);
  const recovered = recoveredBytes.map((b) => String.fromCharCode(b)).join("");
  const isMatch = recovered === state.message;

  const mStage = stage("Recovered message");
  const out = document.createElement("div");
  out.className = "recovered " + (isMatch ? "ok" : "bad");
  out.textContent = recovered || "(empty)";
  mStage.append(out);
  els.results.append(mStage);

  const banner = document.createElement("div");
  banner.className = "banner " + (verified && isMatch ? "ok" : "bad");
  if (verified && isMatch) {
    banner.innerHTML = "\u2713 Decoding succeeded &mdash; the original message was recovered.";
  } else if (state.corrupted.size > state.t) {
    banner.innerHTML =
      "\u2717 Too many errors. Reed-Solomon can only correct up to t = " +
      state.t +
      " with this redundancy.";
  } else {
    banner.innerHTML = "\u2717 Decoding failed to recover the original message.";
  }
  els.results.append(banner);
}

/* ---------- wiring ---------- */

els.encode.addEventListener("click", encode);
els.message.addEventListener("keydown", (e) => {
  if (e.key === "Enter") encode();
});
els.randomize.addEventListener("click", randomErrors);
els.clear.addEventListener("click", clearErrors);
els.decode.addEventListener("click", decode);
els.errorValue.addEventListener("change", renderCodeword);
