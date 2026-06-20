// SERVUS UI - liga ao backend via window.pywebview.api

const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

const chat = $("#chat");
const orb = $("#orb");
const status = $("#status");
const micBtn = $("#micBtn");
const sendBtn = $("#sendBtn");
const input = $("#textInput");
const player = $("#player");
const resetBtn = $("#resetBtn");
const modelLabel = $("#modelLabel");
const brandName = $("#brandName");
const settingsBtn = $("#settingsBtn");
const modal = $("#modal");
const closeBtn = $("#closeBtn");
const cancelBtn = $("#cancelBtn");
const saveBtn = $("#saveBtn");
const previewBtn = $("#previewBtn");

let assistantEl = null;
let recognition = null;
let recognizing = false;
let currentCfg = null;
let catalogs = null;
let draft = null; // copia mutavel da config no modal

// ----- helpers ------------------------------------------------------------
function setState(s) {
  orb.classList.remove("listening", "thinking", "speaking");
  if (s) orb.classList.add(s);
  const text =
    s === "listening" ? "ESCUTANDO" :
    s === "thinking"  ? "PROCESSANDO"  :
    s === "speaking"  ? "FALANDO"   : "PRONTO";
  status.textContent = text;
}

function addMsg(role, text) {
  const div = document.createElement("div");
  div.className = `msg ${role}`;
  div.textContent = text;
  chat.appendChild(div);
  chat.scrollTop = chat.scrollHeight;
  return div;
}

function addCode(kind, text) {
  const div = document.createElement("div");
  div.className = `codeblk ${kind}`;
  const label = document.createElement("div");
  label.className = "label";
  label.textContent = kind === "console" ? "saida" : "codigo";
  const body = document.createElement("div");
  body.textContent = text;
  div.appendChild(label);
  div.appendChild(body);
  chat.appendChild(div);
  chat.scrollTop = chat.scrollHeight;
  return div;
}

// ----- bridge backend -> UI ----------------------------------------------
let pendingUpdate = null; // {latest, url, notes}

function showUpdateBanner(latest, url, notes) {
  pendingUpdate = { latest, url, notes };
  $("#settingsBtn").classList.add("has-update");
  $("#updateBox").hidden = false;
  $("#updLatest").textContent = latest;
  $("#updNotes").textContent = notes || "";
  $("#sysStatus").textContent = `Nova versao ${latest} disponivel`;
}

window.servusStream = (kind, payload) => {
  if (kind === "token") {
    if (!assistantEl) assistantEl = addMsg("assistant", "");
    assistantEl.textContent += payload;
    chat.scrollTop = chat.scrollHeight;
  } else if (kind === "code") {
    // so mostra se modo dev estiver ligado
    if (currentCfg && currentCfg.show_code) addCode("code", payload);
  } else if (kind === "console") {
    if (currentCfg && currentCfg.show_code) addCode("console", payload);
  } else if (kind === "done") {
    assistantEl = null;
    setState(null);
  } else if (kind === "error") {
    assistantEl = null;
    addMsg("error", "⚠ " + payload);
    setState(null);
  } else if (kind === "audio") {
    playAudio(payload);
  } else if (kind === "update_available") {
    const [latest, url, notes] = payload.split("|");
    showUpdateBanner(latest, url, notes);
  } else if (kind === "update_progress") {
    $("#updProgress").hidden = false;
    $("#updProgressBar").style.width = `${payload}%`;
    $("#sysStatus").textContent = `Baixando atualizacao… ${payload}%`;
  } else if (kind === "update_ready") {
    $("#sysStatus").textContent = "Instalando…";
  } else if (kind === "ptt_start") {
    if (!recognition) recognition = initRecognition();
    if (recognition && !recognizing) try { recognition.start(); } catch {}
  } else if (kind === "ptt_end") {
    if (recognition && recognizing) try { recognition.stop(); } catch {}
  } else if (kind === "screen_captured") {
    addMsg("user", "📷 tela capturada - sua proxima mensagem incluira a imagem");
  } else if (kind === "wake_toggled") {
    currentCfg.wake_enabled = payload === "1";
    syncWakeMode();
  } else if (kind === "vosk_progress") {
    const bar = $("#voskProgressBar");
    if (payload === "done") {
      $("#voskProgress").hidden = true;
      $("#voskStatus").textContent = "Modelo pronto";
      $("#voskDownload").hidden = true;
    } else if (payload === "error") {
      $("#voskStatus").textContent = "Erro no download";
    } else {
      if (bar) bar.style.width = payload + "%";
    }
  } else if (kind === "rag_status") {
    $("#ragStatus").textContent = payload;
    if (payload.startsWith("OK") || payload.startsWith("Erro")) {
      $("#ragIndexBtn").disabled = false;
      $("#ragIndexBtn").textContent = "Indexar";
      refreshIntel();
    }
  } else if (kind === "wake_triggered") {
    // Backend disparou wake - inicia burst de captura via Web Speech
    addMsg("assistant", "👂 Te escutando...");
    orb.classList.add("listening");
    _captureBurstCommand(5000);  // 5s
  } else if (kind === "wake_listening_followup") {
    addMsg("assistant", "Sim?");
    orb.classList.add("listening");
    _captureBurstCommand(5000);
  } else if (kind === "wake_engine") {
    // status do engine de wake (vosk / stopped)
  } else if (kind === "device_found") {
    const [key, type, name, addr] = payload.split("|");
    _addDeviceFoundPrompt(key, type, name, addr);
  } else if (kind === "screen_captured_auto") {
    // notifica visualmente que screenshot foi anexada
    orb.classList.add("thinking");
    setTimeout(() => orb.classList.remove("thinking"), 800);
  }
};

function _addDeviceFoundPrompt(key, type, name, addr) {
  const icon = type === "bluetooth" ? "📱" : (type === "cast" ? "📺" : "🔌");
  const div = document.createElement("div");
  div.className = "msg assistant";
  div.innerHTML = `${icon} Encontrei <b>${name || "(sem nome)"}</b> (${type}: ${addr})<br/>
    <small style="opacity:.7">Quer conectar?</small>
    <div style="margin-top:8px;display:flex;gap:6px;">
      <button class="primary" data-act="connect">Conectar</button>
      <button class="ghost" data-act="dismiss">Ignorar</button>
    </div>`;
  div.querySelector('[data-act=connect]').onclick = async () => {
    if (type === "bluetooth") {
      await window.pywebview.api.ble_remember(addr, name, "");
    }
    addMsg("assistant", `Conectado: ${name}`);
    div.remove();
  };
  div.querySelector('[data-act=dismiss]').onclick = async () => {
    await window.pywebview.api.dismiss_device(key);
    div.remove();
  };
  chat.appendChild(div);
  chat.scrollTop = chat.scrollHeight;
}

// Fila de audios pro streaming TTS (varios chunks de fala chegam)
const audioQueue = [];
let audioPlaying = false;

function playAudio(b64) {
  audioQueue.push(b64);
  if (!audioPlaying) _playNext();
}

function _playNext() {
  if (!audioQueue.length) {
    audioPlaying = false;
    setState(null);
    if (wakeOn) {
      wakePaused = false;
      setTimeout(() => { if (wakeOn && !wakeRecog) startWake(); }, 400);
    }
    return;
  }
  audioPlaying = true;
  const b64 = audioQueue.shift();
  const blob = new Blob([Uint8Array.from(atob(b64), c => c.charCodeAt(0))], { type: "audio/mpeg" });
  player.src = URL.createObjectURL(blob);
  setState("speaking");
  if (wakeOn) {
    wakePaused = true;
    if (wakeRecog) { try { wakeRecog.stop(); } catch {} wakeRecog = null; }
  }
  // Barge-in: inicia monitor de mic enquanto fala
  if (currentCfg && currentCfg.barge_in) _startBargeMonitor();
  player.onended = _playNext;
  player.onerror = _playNext;
  player.play().catch(_playNext);
}

function _stopAll() {
  audioQueue.length = 0;
  try { player.pause(); player.currentTime = 0; } catch {}
  audioPlaying = false;
  setState(null);
}

// ---- Barge-in: monitora nivel do mic durante TTS ------------------------
let bargeStream = null;
let bargeCtx = null;

async function _startBargeMonitor() {
  if (bargeCtx) return;  // ja rodando
  try {
    bargeStream = await navigator.mediaDevices.getUserMedia({ audio: true });
    bargeCtx = new AudioContext();
    const src = bargeCtx.createMediaStreamSource(bargeStream);
    const analyser = bargeCtx.createAnalyser();
    analyser.fftSize = 256;
    src.connect(analyser);
    const buf = new Uint8Array(analyser.frequencyBinCount);
    let consec = 0;
    const check = () => {
      if (!bargeCtx) return;
      analyser.getByteTimeDomainData(buf);
      let max = 0;
      for (let i = 0; i < buf.length; i++) { const v = Math.abs(buf[i] - 128); if (v > max) max = v; }
      if (max > 35) consec++; else consec = 0;
      if (consec >= 3 && audioPlaying) {
        _stopBargeMonitor();
        _stopAll();
        return;
      }
      requestAnimationFrame(check);
    };
    check();
    setTimeout(_stopBargeMonitor, 60000);  // safety cleanup
  } catch (e) {
    bargeCtx = null;
  }
}

function _stopBargeMonitor() {
  try { bargeStream && bargeStream.getTracks().forEach(t => t.stop()); } catch {}
  try { bargeCtx && bargeCtx.close(); } catch {}
  bargeStream = null; bargeCtx = null;
}

// ----- envio --------------------------------------------------------------
async function send(text) {
  const t = text.trim();
  if (!t) return;
  addMsg("user", t);
  input.value = "";
  setState("thinking");
  try { await window.pywebview.api.chat(t); }
  catch (e) { addMsg("error", String(e)); setState(null); }
}

sendBtn.addEventListener("click", () => send(input.value));
input.addEventListener("keydown", (e) => {
  if (e.key === "Enter") { e.preventDefault(); send(input.value); }
});
resetBtn.addEventListener("click", async () => {
  await window.pywebview.api.new_conversation();
  chat.innerHTML = "";
  addMsg("assistant", "Nova conversa iniciada.");
});

// ----- Compact mode + history sidebar -----------------------------------
let compactOn = false;
$("#compactBtn").addEventListener("click", async () => {
  compactOn = !compactOn;
  await window.pywebview.api.toggle_compact(compactOn);
  document.body.classList.toggle("compact", compactOn);
});

$("#historyBtn").addEventListener("click", async () => {
  $("#historySidebar").hidden = false;
  const r = await window.pywebview.api.list_history();
  const list = $("#historyList");
  list.innerHTML = "";
  (r.items || []).forEach(it => {
    const el = document.createElement("div");
    el.className = "hist-item";
    el.innerHTML = `<div class="hist-title"></div><div class="hist-date"></div>`;
    el.querySelector(".hist-title").textContent = it.title || "Conversa";
    el.querySelector(".hist-date").textContent = new Date(it.started_at * 1000).toLocaleString("pt-BR");
    el.onclick = async () => {
      const r2 = await window.pywebview.api.load_history(it.id);
      chat.innerHTML = "";
      (r2.messages || []).forEach(m => addMsg(m.role === "user" ? "user" : "assistant", m.content));
      $("#historySidebar").hidden = true;
    };
    list.appendChild(el);
  });
});
$("#closeHistoryBtn").addEventListener("click", () => { $("#historySidebar").hidden = true; });

// ----- Drag & drop de arquivos -------------------------------------------
const dropzone = $("#dropzone");
let dragCounter = 0;
window.addEventListener("dragenter", (e) => {
  e.preventDefault(); dragCounter++; dropzone.hidden = false;
});
window.addEventListener("dragover", (e) => e.preventDefault());
window.addEventListener("dragleave", () => { if (--dragCounter <= 0) { dropzone.hidden = true; dragCounter = 0; } });
window.addEventListener("drop", async (e) => {
  e.preventDefault(); dropzone.hidden = true; dragCounter = 0;
  const files = e.dataTransfer && e.dataTransfer.files;
  if (!files || !files.length) return;
  // pega o path via file.path (pywebview expoe)
  for (const f of files) {
    const p = f.path || f.name;
    const r = await window.pywebview.api.file_dropped(p);
    if (r.ok && r.kind === "image") addMsg("user", `📷 imagem anexada: ${p}`);
    else addMsg("user", `📎 arquivo: ${p}`);
  }
});

// ----- voz (Web Speech, pt-BR) -------------------------------------------
function initRecognition() {
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SR) return null;
  const r = new SR();
  r.lang = "pt-BR";
  r.continuous = false;
  r.interimResults = true;
  r.onstart = () => { recognizing = true; setState("listening"); micBtn.classList.add("recording"); };
  r.onerror = (e) => { addMsg("error", "mic: " + e.error); };
  r.onend = () => { recognizing = false; micBtn.classList.remove("recording"); if (orb.classList.contains("listening")) setState(null); };
  r.onresult = (ev) => {
    let finalT = "", interimT = "";
    for (let i = ev.resultIndex; i < ev.results.length; i++) {
      const t = ev.results[i][0].transcript;
      if (ev.results[i].isFinal) finalT += t; else interimT += t;
    }
    if (interimT) input.value = interimT;
    if (finalT) { input.value = ""; send(finalT); }
  };
  return r;
}
micBtn.addEventListener("click", async () => {
  // Engine local Whisper - usa MediaRecorder + backend
  if (currentCfg && currentCfg.stt_engine === "whisper_local") {
    if (whisperRecording) {
      await _stopWhisperRecord();
    } else {
      await _startWhisperRecord();
    }
    return;
  }
  // Default: Web Speech
  if (!recognition) recognition = initRecognition();
  if (!recognition) { addMsg("error", "Reconhecimento de voz indisponivel."); return; }
  if (recognizing) recognition.stop(); else recognition.start();
});

// ---- Whisper local (MediaRecorder -> Python) ---------------------------
let mediaRec = null;
let whisperRecording = false;
let whisperChunks = [];

async function _startWhisperRecord() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    mediaRec = new MediaRecorder(stream);
    whisperChunks = [];
    mediaRec.ondataavailable = (e) => { if (e.data.size) whisperChunks.push(e.data); };
    mediaRec.onstop = async () => {
      stream.getTracks().forEach(t => t.stop());
      setState("thinking");
      const blob = new Blob(whisperChunks, { type: "audio/webm" });
      const b64 = await _blobToB64(blob);
      const r = await window.pywebview.api.transcribe(b64);
      if (r.text) send(r.text);
      else { addMsg("error", "Whisper nao transcreveu nada"); setState(null); }
    };
    mediaRec.start();
    whisperRecording = true;
    setState("listening");
    micBtn.classList.add("recording");
  } catch (e) {
    addMsg("error", "mic: " + e);
  }
}

async function _stopWhisperRecord() {
  if (mediaRec) { try { mediaRec.stop(); } catch {} }
  whisperRecording = false;
  micBtn.classList.remove("recording");
}

function _blobToB64(blob) {
  return new Promise(res => {
    const fr = new FileReader();
    fr.onloadend = () => res(fr.result.split(",")[1]);
    fr.readAsDataURL(blob);
  });
}

// ===== modo "sempre escutando" (palavra-gatilho) ========================
let wakeRecog = null;
let wakeOn = false;
let wakePaused = false;   // pausa enquanto TTS toca / processa comando
let wakeWord = "";
let waitingFollowUp = false;
let followUpTimer = null;
const FOLLOW_UP_MS = 8000;
const wakeBadge = $("#wakeBadge");

function _exitFollowUp() {
  waitingFollowUp = false;
  if (followUpTimer) { clearTimeout(followUpTimer); followUpTimer = null; }
  orb.classList.remove("listening");
}

// Captura comando em modo BURST (5s, nao-continuo).
// Acionado quando OpenWakeWord backend dispara wake_triggered.
let burstRecog = null;
function _captureBurstCommand(timeoutMs) {
  // pausa Vosk listener pra liberar mic
  window.pywebview.api.stop_vosk_wake().catch(() => {});

  // se ja tem burst rodando, para
  if (burstRecog) { try { burstRecog.abort(); } catch {} burstRecog = null; }

  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SR) {
    addMsg("error", "Web Speech indisponivel - nao posso capturar comando");
    return;
  }
  const r = new SR();
  r.lang = "pt-BR";
  r.continuous = false;
  r.interimResults = false;
  r.maxAlternatives = 1;

  let captured = "";
  let finished = false;

  r.onresult = (ev) => {
    if (ev.results.length > 0 && ev.results[0].isFinal) {
      captured = ev.results[0][0].transcript.trim();
    }
  };
  r.onerror = (ev) => {
    if (ev.error === "no-speech") {
      addMsg("assistant", "Nao te ouvi. Tente de novo.");
    } else if (ev.error !== "aborted") {
      console.warn("burst err:", ev.error);
    }
  };
  r.onend = () => {
    if (finished) return;
    finished = true;
    orb.classList.remove("listening");
    burstRecog = null;
    if (captured) {
      send(captured);
    }
    // retoma wake listener Vosk
    if (currentCfg && currentCfg.wake_enabled && currentCfg.wake_offline) {
      setTimeout(() => {
        window.pywebview.api.start_vosk_wake().catch(() => {});
      }, 500);
    }
  };

  burstRecog = r;
  try { r.start(); }
  catch (e) {
    addMsg("error", "mic burst fail: " + e);
    finished = true;
    burstRecog = null;
    return;
  }

  // timeout - encerra sem comando
  setTimeout(() => {
    if (burstRecog === r && !finished) {
      try { r.stop(); } catch {}
    }
  }, timeoutMs || 5000);
}

function _normalize(s) {
  // remove acentos via decomposicao Unicode (faixa de combining diacritics)
  return (s || "").toString().toLowerCase()
    .normalize("NFD").replace(/[̀-ͯ]/g, "")
    .trim();
}

function _wakeIndex(text, word) {
  if (!word) return -1;
  const re = new RegExp("(?:^|\\W)" + word.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"), "i");
  const m = text.match(re);
  if (!m) return -1;
  return m.index + (text[m.index] && /\W/.test(text[m.index]) ? 1 : 0);
}

function _lev(a, b) {
  if (a.length < b.length) [a, b] = [b, a];
  if (!b) return a.length;
  let prev = Array.from({length: b.length + 1}, (_, i) => i);
  for (let i = 0; i < a.length; i++) {
    const curr = [i + 1];
    for (let j = 0; j < b.length; j++) {
      curr.push(Math.min(curr[j] + 1, prev[j + 1] + 1, prev[j] + (a[i] !== b[j] ? 1 : 0)));
    }
    prev = curr;
  }
  return prev[b.length];
}

function _wakeMatch(textNorm, words) {
  // 1) exato (case-insensitive, sem acentos)
  for (const w of words) {
    const idx = _wakeIndex(textNorm, w);
    if (idx >= 0) return [idx, w];
  }
  // 2) fuzzy por token (Levenshtein <= 1)
  const tokens = textNorm.split(/\s+/);
  let pos = 0;
  for (const t of tokens) {
    for (const w of words) {
      if (!w || w.length < 3) continue;
      if (Math.abs(t.length - w.length) <= 1 && _lev(t, w) <= 1) {
        return [pos, t];
      }
    }
    pos += t.length + 1;
  }
  return [-1, ""];
}

function _getWakeList() {
  const list = (currentCfg.wake_words || []).map(_normalize).filter(Boolean);
  const single = _normalize(currentCfg.wake_word || "");
  const name = _normalize(currentCfg.identity.name || "servus");
  // dedup
  const all = new Set();
  list.forEach(w => all.add(w));
  if (single) all.add(single);
  if (!all.size) all.add(name);
  return [...all];
}

function startWake() {
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SR) { addMsg("error", "Reconhecimento de voz indisponivel nesta WebView."); return; }
  if (wakeRecog) return;
  const wakeList = _getWakeList();
  if (!wakeList.length) return;
  wakeWord = wakeList[0];  // fallback display

  const r = new SR();
  r.lang = "pt-BR";
  r.continuous = true;
  r.interimResults = true;  // mantem sessao viva mais tempo

  r.onresult = (ev) => {
    if (wakePaused) return;
    for (let i = ev.resultIndex; i < ev.results.length; i++) {
      if (!ev.results[i].isFinal) continue;
      const raw = ev.results[i][0].transcript.trim();
      if (raw.length < 2) continue;

      // modo follow-up: qualquer fala vira comando
      if (waitingFollowUp) {
        _exitFollowUp();
        send(raw);
        return;
      }

      // procura qualquer uma das palavras-gatilho
      const norm = _normalize(raw);
      const [idx, matched] = _wakeMatch(norm, _getWakeList());
      if (idx < 0) continue;
      const after = raw.substring(idx + matched.length)
        .replace(/^[\s,.\-:;!?]+/, "")
        .trim();
      if (after.length >= 2) {
        send(after);
      } else {
        // só falou a palavra-gatilho - entra em modo follow-up
        addMsg("assistant", "Sim?");
        orb.classList.add("listening");
        waitingFollowUp = true;
        if (followUpTimer) clearTimeout(followUpTimer);
        followUpTimer = setTimeout(_exitFollowUp, FOLLOW_UP_MS);
      }
      return;
    }
  };

  const _restart = (delay) => {
    setTimeout(() => {
      if (!wakeOn || wakePaused) return;
      try {
        wakeRecog = null;
        startWake();
      } catch (e) { console.warn("wake restart fail", e); }
    }, delay);
  };

  r.onend = () => {
    if (wakeOn && !wakePaused) _restart(200);
  };

  r.onerror = (e) => {
    if (e.error === "not-allowed" || e.error === "service-not-allowed") {
      wakeOn = false;
      wakeBadge.hidden = true;
      orb.classList.remove("wake");
      addMsg("error", "Microfone bloqueado. Permita o acesso para usar palavra-gatilho.");
      return;
    }
    // no-speech, network, audio-capture, aborted: reinicia
    try { r.stop(); } catch {}
    _restart(e.error === "network" ? 2000 : 500);
  };

  wakeRecog = r;
  wakeOn = true;
  wakeBadge.hidden = false;
  orb.classList.add("wake");
  try { r.start(); }
  catch (e) {
    // ja rodando? aborta e tenta de novo
    try { r.abort(); } catch {}
    _restart(500);
  }
}

function stopWake() {
  wakeOn = false;
  wakeBadge.hidden = true;
  orb.classList.remove("wake");
  _exitFollowUp();
  if (wakeRecog) {
    try { wakeRecog.abort(); } catch {}
    try { wakeRecog.stop(); } catch {}
    wakeRecog = null;
  }
  // libera tracks/streams pendentes
  if (bargeStream) {
    try { bargeStream.getTracks().forEach(t => t.stop()); } catch {}
    bargeStream = null;
  }
  if (bargeCtx) {
    try { bargeCtx.close(); } catch {}
    bargeCtx = null;
  }
}

function pauseWakeWhile(promise) {
  wakePaused = true;
  if (wakeRecog) { try { wakeRecog.stop(); } catch {} }
  Promise.resolve(promise).finally(() => {
    wakePaused = false;
    if (wakeOn && !wakeRecog) {
      // recria — onend ja teria reiniciado mas se foi parado, recria
      setTimeout(() => startWake(), 300);
    }
  });
}

async function syncWakeMode() {
  if (!currentCfg) return;
  // sempre para tudo primeiro
  if (wakeOn) stopWake();
  try { await window.pywebview.api.stop_vosk_wake(); } catch {}

  if (!currentCfg.wake_enabled) return;

  // Vosk (backend) vs Web Speech (frontend)
  if (currentCfg.wake_offline) {
    // Auto-download do modelo se nao baixou ainda
    const vk = await window.pywebview.api.vosk_status();
    if (!vk.ready) {
      addMsg("assistant", "Baixando modelo Vosk (~40MB), aguarde...");
      await window.pywebview.api.vosk_download();
      // espera notificacao via stream "vosk_progress: done"
      let attempts = 0;
      while (attempts < 90) {  // 90s max
        await new Promise(r => setTimeout(r, 1000));
        const s = await window.pywebview.api.vosk_status();
        if (s.ready) break;
        attempts++;
      }
      const final = await window.pywebview.api.vosk_status();
      if (!final.ready) {
        addMsg("error", "Falha no download do Vosk - tentando Web Speech");
        startWake();
        return;
      }
      addMsg("assistant", "Modelo baixado! Iniciando escuta offline.");
    }
    const r = await window.pywebview.api.start_vosk_wake();
    if (r.ok) {
      wakeOn = true;
      wakeBadge.hidden = false;
      orb.classList.add("wake");
    } else {
      addMsg("error", "Vosk: " + (r.error || "falhou") + " - tentando Web Speech");
      startWake();
    }
  } else {
    startWake();
  }
}

// ===== painel de configuracao ============================================

function openModal() {
  draft = JSON.parse(JSON.stringify(currentCfg));
  renderConfig();
  modal.hidden = false;
}
function closeModal() { modal.hidden = true; }

settingsBtn.addEventListener("click", openModal);
closeBtn.addEventListener("click", closeModal);
cancelBtn.addEventListener("click", closeModal);
modal.addEventListener("click", (e) => { if (e.target === modal) closeModal(); });

// tabs
$$(".tab").forEach((t) => {
  t.addEventListener("click", () => {
    $$(".tab").forEach((x) => x.classList.remove("active"));
    t.classList.add("active");
    const id = t.dataset.tab;
    $$(".panel").forEach((p) => { p.hidden = (p.id !== `panel-${id}`); });
    if (id === "devices") refreshKnownBLE();
    if (id === "memory") refreshFacts();
    if (id === "intel") refreshIntel();
    if (id === "model") { refreshOllama(); refreshBrowsers(); }
    if (id === "msgs") refreshMsgs();
    if (id === "hw") startHwPolling(); else stopHwPolling();
  });
});

function renderConfig() {
  // identidade
  $("#cfgName").value = draft.identity.name;
  $("#cfgPersona").value = draft.identity.persona;
  $("#cfgName").oninput = (e) => { draft.identity.name = e.target.value; };
  $("#cfgPersona").oninput = (e) => { draft.identity.persona = e.target.value; };

  // voice presets
  renderVoicePresets();

  // voz
  const voiceSel = $("#cfgVoice");
  voiceSel.innerHTML = catalogs.voices
    .map(v => `<option value="${v.id}">${v.label}</option>`).join("");
  voiceSel.value = draft.voice;
  voiceSel.onchange = (e) => { draft.voice = e.target.value; markActivePreset(); };

  $("#cfgRate").value = draft.rate;
  $("#cfgRate").onchange = (e) => { draft.rate = e.target.value; };

  $("#cfgPitch").value = draft.pitch || "+0Hz";
  $("#cfgPitch").onchange = (e) => { draft.pitch = e.target.value; markActivePreset(); };
  $("#cfgRate").onchange = (e) => { draft.rate = e.target.value; markActivePreset(); };

  // Modo desenvolvedor (show_code)
  if ($("#cfgShowCode")) {
    $("#cfgShowCode").checked = !!draft.show_code;
    $("#cfgShowCode").onchange = (e) => { draft.show_code = e.target.checked; };
  }

  $("#cfgWake").checked = !!draft.wake_enabled;
  $("#cfgWake").onchange = (e) => { draft.wake_enabled = e.target.checked; };

  // Wake words (multi)
  draft.wake_words = draft.wake_words || [];
  // migra wake_word legado -> wake_words
  if (draft.wake_word && !draft.wake_words.includes(draft.wake_word)) {
    draft.wake_words.push(draft.wake_word);
  }
  _renderWakeChips();

  // Screen mode
  if ($("#cfgScreenMode")) {
    $("#cfgScreenMode").checked = !!draft.screen_mode;
    $("#cfgScreenMode").onchange = (e) => { draft.screen_mode = e.target.checked; };
  }

  // Auto-scan
  if ($("#cfgAutoScan")) {
    $("#cfgAutoScan").checked = (draft.auto_scan_enabled !== false);
    $("#cfgAutoScan").onchange = (e) => { draft.auto_scan_enabled = e.target.checked; };
  }
  if ($("#cfgAutoScanInterval")) {
    $("#cfgAutoScanInterval").value = draft.auto_scan_interval_min || 10;
    $("#cfgAutoScanInterval").oninput = (e) => {
      draft.auto_scan_interval_min = parseInt(e.target.value || "10", 10);
    };
  }

  // humor
  renderChips("#cfgMood", catalogs.moods, draft.mood, (id) => { draft.mood = id; });

  // sotaque
  renderChips("#cfgAccent", catalogs.accents, draft.accent, (id) => { draft.accent = id; });

  // speed modes (Haiku/Sonnet/Opus)
  renderSpeedModes();

  // modelo
  const modelSel = $("#cfgModel");
  modelSel.innerHTML = catalogs.models
    .map(m => `<option value="${m.id}">${m.label}</option>`).join("");
  modelSel.value = draft.model;
  modelSel.onchange = (e) => { draft.model = e.target.value; };

  // Inteligencia
  $("#cfgStreamTTS").checked = !!(draft.streaming_tts ?? true);
  $("#cfgStreamTTS").onchange = e => { draft.streaming_tts = e.target.checked; };
  $("#cfgBargeIn").checked = !!(draft.barge_in ?? true);
  $("#cfgBargeIn").onchange = e => { draft.barge_in = e.target.checked; };
  $("#cfgSTTEngine").value = draft.stt_engine || "browser";
  $("#cfgSTTEngine").onchange = e => { draft.stt_engine = e.target.value; };
  $("#cfgWakeOffline").checked = !!draft.wake_offline;
  $("#cfgWakeOffline").onchange = e => { draft.wake_offline = e.target.checked; };
  if ($("#cfgWakeModelOffline")) {
    $("#cfgWakeModelOffline").value = draft.wake_model_offline || "hey_jarvis";
    $("#cfgWakeModelOffline").onchange = e => { draft.wake_model_offline = e.target.value; };
  }
  $("#cfgMultiStep").checked = !!draft.multi_step_mode;
  $("#cfgMultiStep").onchange = e => { draft.multi_step_mode = e.target.checked; };
  $("#cfgAutoRetry").checked = !!(draft.auto_retry ?? true);
  $("#cfgAutoRetry").onchange = e => { draft.auto_retry = e.target.checked; };
  $("#cfgRagFolder").value = draft.rag_folder || "";
  $("#cfgRagFolder").oninput = e => { draft.rag_folder = e.target.value.trim(); };
  $("#cfgOllamaModel").value = draft.ollama_model || "";
  $("#cfgOllamaModel").onchange = e => { draft.ollama_model = e.target.value; };

  // dispositivos
  draft.devices = draft.devices || { provider: "none", ha_url: "", ha_token: "" };
  $("#cfgDevProvider").value = draft.devices.provider || "none";
  $("#cfgDevProvider").onchange = (e) => {
    draft.devices.provider = e.target.value;
    $("#haFields").hidden = (e.target.value !== "home_assistant");
  };
  $("#haFields").hidden = (draft.devices.provider !== "home_assistant");
  $("#cfgHaUrl").value = draft.devices.ha_url || "";
  $("#cfgHaUrl").oninput = (e) => { draft.devices.ha_url = e.target.value.trim(); };
  $("#cfgHaToken").value = draft.devices.ha_token || "";
  $("#cfgHaToken").oninput = (e) => { draft.devices.ha_token = e.target.value.trim(); };
  $("#devStatus").textContent = "—";
  $("#devStatus").className = "dev-status";
  $("#devSample").hidden = true;
}

$("#testDevBtn").addEventListener("click", async () => {
  const url = $("#cfgHaUrl").value.trim();
  const token = $("#cfgHaToken").value.trim();
  if (!url || !token) { $("#devStatus").textContent = "Preencha URL e token"; return; }
  $("#testDevBtn").disabled = true;
  $("#devStatus").textContent = "Testando…";
  $("#devStatus").className = "dev-status";
  const r = await window.pywebview.api.test_devices(url, token);
  $("#testDevBtn").disabled = false;
  if (r.ok) {
    $("#devStatus").className = "dev-status ok";
    $("#devStatus").textContent = `OK · HA ${r.version} · ${r.entity_count} dispositivos`;
    $("#devSample").hidden = false;
    const list = $("#devSampleList");
    list.innerHTML = "";
    (r.sample || []).forEach(s => {
      const d = document.createElement("div");
      d.className = "dev-sample-item";
      d.textContent = s;
      list.appendChild(d);
    });
  } else {
    $("#devStatus").className = "dev-status err";
    $("#devStatus").textContent = "Falha: " + r.error;
    $("#devSample").hidden = true;
  }
});

function renderChips(containerSel, items, selectedId, onPick) {
  const c = $(containerSel);
  c.innerHTML = "";
  items.forEach(it => {
    const b = document.createElement("button");
    b.className = "chip" + (it.id === selectedId ? " active" : "");
    b.textContent = it.label;
    b.onclick = () => {
      c.querySelectorAll(".chip").forEach(x => x.classList.remove("active"));
      b.classList.add("active");
      onPick(it.id);
    };
    c.appendChild(b);
  });
}

saveBtn.addEventListener("click", async () => {
  const res = await window.pywebview.api.save_config(draft);
  if (res.ok) {
    currentCfg = res.config;
    brandName.textContent = currentCfg.identity.name;
    document.title = currentCfg.identity.name;
    const _hud = $("#hudLabel"); if (_hud) _hud.textContent = _spaceLetters(currentCfg.identity.name);
    chat.innerHTML = "";
    addMsg("assistant", `Identidade atualizada. Eu sou ${currentCfg.identity.name}.`);
    syncWakeMode();
    closeModal();
  }
});

previewBtn.addEventListener("click", async () => {
  await window.pywebview.api.preview_voice(draft.voice);
});

function _renderWakeChips() {
  const cont = $("#cfgWakeChips");
  if (!cont) return;
  cont.innerHTML = "";
  (draft.wake_words || []).forEach((w, i) => {
    const c = document.createElement("span");
    c.className = "wake-chip";
    c.innerHTML = `${w} <button class="wake-chip-rm">×</button>`;
    c.querySelector(".wake-chip-rm").onclick = () => {
      draft.wake_words.splice(i, 1);
      _renderWakeChips();
    };
    cont.appendChild(c);
  });
}

// Teste do mic: grava 5s, mostra o que foi ouvido (Web Speech)
document.addEventListener("click", async (e) => {
  if (e.target.id !== "wakeTestBtn") return;
  const btn = e.target;
  const status = $("#wakeTestStatus");
  const out = $("#wakeTestTranscript");
  out.hidden = false;
  out.textContent = "";
  status.textContent = "Ouvindo… fala alguma coisa";
  status.className = "dev-status";
  btn.disabled = true;
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SR) {
    status.textContent = "Web Speech indisponivel - tente Vosk";
    status.className = "dev-status err";
    btn.disabled = false;
    return;
  }
  const r = new SR();
  r.lang = "pt-BR";
  r.continuous = true;
  r.interimResults = true;
  let last = "";
  r.onresult = (ev) => {
    let txt = "";
    for (let i = 0; i < ev.results.length; i++) txt += ev.results[i][0].transcript;
    last = txt;
    out.textContent = txt;
  };
  r.onerror = (ev) => {
    status.textContent = "Erro: " + ev.error;
    status.className = "dev-status err";
  };
  try { r.start(); } catch (ex) {
    status.textContent = "Falha ao iniciar: " + ex;
    status.className = "dev-status err";
    btn.disabled = false;
    return;
  }
  setTimeout(() => {
    try { r.stop(); } catch {}
    if (last.trim()) {
      status.textContent = `OK - ${last.trim().split(/\s+/).length} palavras detectadas`;
      status.className = "dev-status ok";
    } else {
      status.textContent = "Nada detectado - cheque o microfone";
      status.className = "dev-status err";
    }
    btn.disabled = false;
  }, 5000);
});

document.addEventListener("click", (e) => {
  if (e.target.id !== "cfgWakeAddBtn") return;
  const inp = $("#cfgWakeWordInput");
  if (!inp) return;
  const raw = inp.value.trim();
  if (!raw) return;
  raw.split(/[,;]/).map(s => s.trim()).filter(Boolean).forEach(w => {
    draft.wake_words = draft.wake_words || [];
    if (!draft.wake_words.includes(w)) draft.wake_words.push(w);
  });
  inp.value = "";
  _renderWakeChips();
});

// ===== Hardware monitor =================================================
let hwTimer = null;
async function startHwPolling() {
  if (hwTimer) return;
  await pollHw();
  hwTimer = setInterval(pollHw, 2000);
}
function stopHwPolling() {
  if (hwTimer) { clearInterval(hwTimer); hwTimer = null; }
}

async function pollHw() {
  let s;
  try { s = await window.pywebview.api.hw_stats(); }
  catch { return; }

  // CPU
  const cpuP = s.cpu.percent || 0;
  $("#hwCpuVal").textContent = `${cpuP.toFixed(0)}%`;
  _setBar("#hwCpuBar", cpuP);
  $("#hwCpuSub").textContent = `${s.cpu.count_physical}c/${s.cpu.count_logical}t · ${s.cpu.freq_mhz}MHz`;

  // RAM
  const ramP = s.ram.percent || 0;
  $("#hwRamVal").textContent = `${ramP.toFixed(0)}%`;
  _setBar("#hwRamBar", ramP);
  $("#hwRamSub").textContent = `${s.ram.used_gb}/${s.ram.total_gb} GB · free ${s.ram.available_gb}`;

  // GPU
  if (s.gpu && s.gpu.length) {
    const g = s.gpu[0];
    $("#hwGpuVal").textContent = `${g.util_percent}%`;
    _setBar("#hwGpuBar", g.util_percent);
    $("#hwGpuSub").textContent =
      `${g.name} · ${g.mem_used_gb}/${g.mem_total_gb}GB${g.power_w ? ' · '+g.power_w+'W' : ''}`;
  } else {
    $("#hwGpuVal").textContent = "—";
    _setBar("#hwGpuBar", 0);
    $("#hwGpuSub").textContent = "GPU NVIDIA nao detectada";
  }

  // Temp
  const cpuT = s.cpu_temp_c;
  const gpuT = (s.gpu && s.gpu[0]) ? s.gpu[0].temp_c : null;
  const t = cpuT || gpuT;
  if (t != null) {
    $("#hwTempVal").textContent = `${t.toFixed(0)}°C`;
    _setBar("#hwTempBar", Math.min(100, (t / 100) * 100));
    $("#hwTempSub").textContent =
      (cpuT != null ? `CPU ${cpuT.toFixed(0)}°C` : "") +
      (gpuT != null ? `${cpuT != null ? ' · ' : ''}GPU ${gpuT.toFixed(0)}°C` : "");
  } else {
    $("#hwTempVal").textContent = "—";
    _setBar("#hwTempBar", 0);
    $("#hwTempSub").textContent = "Temperatura indisponivel";
  }

  // Discos
  const disksEl = $("#hwDisks");
  disksEl.innerHTML = "";
  (s.disk || []).forEach(d => {
    const el = document.createElement("div");
    el.className = "hw-disk-item";
    el.innerHTML = `<span class="hw-disk-name"></span><span class="hw-disk-val"></span>`;
    el.querySelector(".hw-disk-name").textContent = `${d.mount} (${d.fstype})`;
    el.querySelector(".hw-disk-val").textContent = `${d.percent}% · ${d.free_gb}GB livres`;
    disksEl.appendChild(el);
  });

  // Processos
  const procsEl = $("#hwProcs");
  procsEl.innerHTML = "";
  (s.top_processes || []).forEach(p => {
    const el = document.createElement("div");
    el.className = "hw-proc-item";
    el.innerHTML = `<span class="hw-proc-name"></span><span class="hw-proc-val"></span>`;
    el.querySelector(".hw-proc-name").textContent = p.name;
    el.querySelector(".hw-proc-val").textContent = `CPU ${p.cpu.toFixed(0)}% · ${p.ram_mb}MB`;
    procsEl.appendChild(el);
  });
}

function _setBar(sel, percent) {
  const el = $(sel); if (!el) return;
  el.style.width = `${Math.max(0, Math.min(100, percent))}%`;
  el.classList.toggle("warn", percent >= 70 && percent < 90);
  el.classList.toggle("crit", percent >= 90);
}

$("#hwRefreshBtn")?.addEventListener("click", pollHw);

function renderSpeedModes() {
  const container = $("#cfgSpeedModes");
  if (!container || !catalogs.speed_modes) return;
  container.innerHTML = "";
  catalogs.speed_modes.forEach(s => {
    const btn = document.createElement("button");
    btn.className = "preset" + (draft.speed === s.id ? " active" : "");
    btn.type = "button";
    btn.dataset.id = s.id;
    btn.innerHTML = `<div class="preset-label"></div><div class="preset-desc"></div>`;
    btn.querySelector(".preset-label").textContent = s.label;
    btn.querySelector(".preset-desc").textContent = s.model;
    btn.onclick = () => {
      draft.speed = s.id;
      document.querySelectorAll("#cfgSpeedModes .preset").forEach(b =>
        b.classList.toggle("active", b.dataset.id === s.id));
    };
    container.appendChild(btn);
  });
}

function renderVoicePresets() {
  const container = $("#cfgVoicePresets");
  if (!container || !catalogs.voice_presets) return;
  container.innerHTML = "";
  catalogs.voice_presets.forEach(p => {
    const btn = document.createElement("button");
    btn.className = "preset";
    btn.type = "button";
    btn.dataset.id = p.id;
    btn.innerHTML = `<div class="preset-label"></div><div class="preset-desc"></div>`;
    btn.querySelector(".preset-label").textContent = p.label;
    btn.querySelector(".preset-desc").textContent = p.description;
    btn.onclick = () => applyPreset(p);
    container.appendChild(btn);
  });
  markActivePreset();
}

async function applyPreset(p) {
  draft.voice = p.voice;
  draft.rate = p.rate;
  draft.pitch = p.pitch;
  draft.mood = p.mood;
  $("#cfgVoice").value = p.voice;
  $("#cfgRate").value = p.rate;
  $("#cfgPitch").value = p.pitch;
  markActivePreset();
  // AUTO-SAVE: preset so funciona se persistir
  try {
    const res = await window.pywebview.api.save_config(draft);
    if (res && res.config) currentCfg = res.config;
  } catch (e) { /* segue mesmo se falhar */ }
  // toca preview pra confirmar
  window.pywebview.api.preview_voice(p.voice).catch(() => {});
}

function markActivePreset() {
  if (!catalogs.voice_presets) return;
  document.querySelectorAll(".preset").forEach(b => {
    const p = catalogs.voice_presets.find(x => x.id === b.dataset.id);
    if (!p) return;
    const active = p.voice === draft.voice
      && p.rate === draft.rate
      && p.pitch === draft.pitch;
    b.classList.toggle("active", active);
  });
}

// ----- aba sistema / updates --------------------------------------------
$("#checkUpdateBtn").addEventListener("click", async () => {
  $("#sysStatus").textContent = "Verificando…";
  const info = await window.pywebview.api.check_update();
  if (info.error) {
    $("#sysStatus").textContent = "Erro: " + info.error;
    return;
  }
  if (info.available) {
    showUpdateBanner(info.latest, info.url, info.notes);
  } else {
    $("#sysStatus").textContent = `Voce esta na ultima versao (${info.current})`;
    $("#updateBox").hidden = true;
    $("#settingsBtn").classList.remove("has-update");
  }
});

// ----- aba bluetooth (BLE) ----------------------------------------------
function _bleItem(d, known) {
  const it = document.createElement("div");
  it.className = "ble-item" + (known ? " known" : "");
  it.innerHTML = `
    <div class="ble-meta">
      <div class="ble-name"></div>
      <div class="ble-addr"></div>
    </div>
    <span class="ble-rssi"></span>
    <div class="ble-actions"></div>
  `;
  it.querySelector(".ble-name").textContent = d.name || "(sem nome)";
  it.querySelector(".ble-addr").textContent = d.address || "";
  it.querySelector(".ble-rssi").textContent = (d.rssi != null ? d.rssi + " dBm" : "");
  const actions = it.querySelector(".ble-actions");
  const btn = document.createElement("button");
  if (known) {
    btn.textContent = "Remover";
    btn.className = "danger";
    btn.onclick = async () => {
      await window.pywebview.api.ble_forget(d.address);
      refreshKnownBLE();
    };
  } else {
    btn.textContent = "Conhecer";
    btn.onclick = async () => {
      await window.pywebview.api.ble_remember(d.address, d.name, "");
      refreshKnownBLE();
    };
  }
  actions.appendChild(btn);
  return it;
}

async function refreshKnownBLE() {
  const list = $("#bleKnownList");
  if (!list) return;
  const known = (currentCfg.bluetooth && currentCfg.bluetooth.known) || [];
  list.innerHTML = "";
  if (!known.length) {
    list.innerHTML = `<p class="hint" style="margin:4px 0">Nenhum dispositivo conhecido. Escaneie e adicione.</p>`;
    return;
  }
  known.forEach(d => list.appendChild(_bleItem(d, true)));
}

// ===== Messaging Hub ====================================================
function _sub(id) {
  document.querySelectorAll(".subtab").forEach(b => b.classList.toggle("active", b.dataset.sub === id));
  document.querySelectorAll(".subpanel").forEach(p => p.hidden = (p.id !== `sub-${id}`));
}
document.querySelectorAll(".subtab").forEach(b => {
  b.addEventListener("click", () => _sub(b.dataset.sub));
});

function refreshMsgs() {
  const m = (currentCfg.messaging || {});
  const e = m.email || {}, tg = m.telegram || {}, wa = m.whatsapp || {};
  // Email
  $("#cfgEmailUser").value = e.user || "";
  $("#cfgEmailPass").value = e.password || "";
  $("#cfgEmailSmtpHost").value = e.smtp_host || "smtp.gmail.com";
  $("#cfgEmailSmtpPort").value = e.smtp_port || 587;
  $("#cfgEmailImapHost").value = e.imap_host || "imap.gmail.com";
  $("#cfgEmailImapPort").value = e.imap_port || 993;
  // Telegram
  $("#cfgTgToken").value = tg.token || "";
  $("#cfgTgChatId").value = tg.chat_id || "";
  // WhatsApp
  $("#cfgWaUrl").value = wa.webhook_url || "";
  $("#cfgWaSecret").value = wa.webhook_secret || "";
  refreshContacts();
  refreshTemplates();
}

// --- Email ---
$("#emailSaveBtn")?.addEventListener("click", async () => {
  const data = {
    user: $("#cfgEmailUser").value.trim(),
    password: $("#cfgEmailPass").value,
    smtp_host: $("#cfgEmailSmtpHost").value.trim(),
    smtp_port: parseInt($("#cfgEmailSmtpPort").value || "587", 10),
    imap_host: $("#cfgEmailImapHost").value.trim(),
    imap_port: parseInt($("#cfgEmailImapPort").value || "993", 10),
  };
  await window.pywebview.api.msg_save_config("email", data);
  currentCfg = await window.pywebview.api.get_config();
  $("#emailStatus").textContent = "Salvo";
  $("#emailStatus").className = "dev-status ok";
});

$("#emailInboxBtn")?.addEventListener("click", async () => {
  $("#emailStatus").textContent = "Lendo…";
  const r = await window.pywebview.api.msg_email_inbox(10, false);
  const box = $("#emailInbox");
  box.innerHTML = "";
  (r.items || []).forEach(it => {
    if (it.error) { box.innerHTML = `<p class="hint" style="color:var(--danger)">${it.error}</p>`; return; }
    const el = document.createElement("div");
    el.className = "inbox-item";
    el.innerHTML = `<div class="inbox-from"></div><div class="inbox-subject"></div><div class="inbox-snippet"></div><div class="inbox-date"></div>`;
    el.querySelector(".inbox-from").textContent = it.from;
    el.querySelector(".inbox-subject").textContent = it.subject;
    el.querySelector(".inbox-snippet").textContent = it.snippet;
    el.querySelector(".inbox-date").textContent = it.date;
    box.appendChild(el);
  });
  $("#emailStatus").textContent = `${(r.items || []).length} mensagens`;
  $("#emailStatus").className = "dev-status ok";
});

// --- Telegram ---
$("#tgSaveBtn")?.addEventListener("click", async () => {
  await window.pywebview.api.msg_save_config("telegram", {
    token: $("#cfgTgToken").value.trim(),
    chat_id: $("#cfgTgChatId").value.trim(),
  });
  currentCfg = await window.pywebview.api.get_config();
  $("#tgStatus").textContent = "Salvo";
  $("#tgStatus").className = "dev-status ok";
});
$("#tgTestBtn")?.addEventListener("click", async () => {
  $("#tgStatus").textContent = "Enviando…";
  const r = await window.pywebview.api.msg_telegram_send("Teste do SERVUS 🤖");
  $("#tgStatus").textContent = r.ok ? "OK" : ("Erro: " + (r.error || r.status));
  $("#tgStatus").className = "dev-status " + (r.ok ? "ok" : "err");
});
$("#tgInboxBtn")?.addEventListener("click", async () => {
  const r = await window.pywebview.api.msg_telegram_inbox(10);
  const box = $("#tgInbox");
  box.innerHTML = "";
  (r.items || []).forEach(it => {
    const el = document.createElement("div");
    el.className = "inbox-item";
    el.innerHTML = `<div class="inbox-from"></div><div class="inbox-snippet"></div><div class="inbox-date">chat_id: <code></code></div>`;
    el.querySelector(".inbox-from").textContent = it.from;
    el.querySelector(".inbox-snippet").textContent = it.text;
    el.querySelector("code").textContent = it.chat_id;
    box.appendChild(el);
  });
});

// --- WhatsApp ---
$("#waSaveBtn")?.addEventListener("click", async () => {
  await window.pywebview.api.msg_save_config("whatsapp", {
    webhook_url: $("#cfgWaUrl").value.trim(),
    webhook_secret: $("#cfgWaSecret").value,
  });
  currentCfg = await window.pywebview.api.get_config();
  $("#waStatus").textContent = "Salvo";
  $("#waStatus").className = "dev-status ok";
});
$("#waTestBtn")?.addEventListener("click", async () => {
  const to = prompt("Numero destino (com DDI, ex: 5511999999999):");
  if (!to) return;
  $("#waStatus").textContent = "Enviando…";
  const r = await window.pywebview.api.msg_whatsapp_send(to, "Teste do SERVUS 🤖");
  $("#waStatus").textContent = r.ok ? `OK (${r.status})` : ("Erro: " + (r.error || r.status));
  $("#waStatus").className = "dev-status " + (r.ok ? "ok" : "err");
});

// --- Contatos ---
async function refreshContacts() {
  const r = await window.pywebview.api.contacts_list();
  const list = $("#contactsList");
  if (!list) return;
  list.innerHTML = "";
  (r.items || []).forEach(c => {
    const el = document.createElement("div");
    el.className = "fact-item";
    el.innerHTML = `<span class="fact-cat">contato</span><span class="fact-text"></span><button class="fact-rm">×</button>`;
    const parts = [c.name];
    if (c.phone) parts.push(`📱 ${c.phone}`);
    if (c.email) parts.push(`📧 ${c.email}`);
    if (c.telegram) parts.push(`💬 ${c.telegram}`);
    el.querySelector(".fact-text").textContent = parts.join(" · ");
    el.querySelector(".fact-rm").onclick = async () => {
      await window.pywebview.api.contacts_remove(c.id);
      refreshContacts();
    };
    list.appendChild(el);
  });
}
$("#addContactBtn")?.addEventListener("click", async () => {
  const name = $("#newContactName").value.trim();
  if (!name) return;
  await window.pywebview.api.contacts_add(
    name,
    $("#newContactPhone").value.trim(),
    $("#newContactEmail").value.trim(),
    $("#newContactTg").value.trim(),
  );
  ["#newContactName", "#newContactPhone", "#newContactEmail", "#newContactTg"].forEach(s => $(s).value = "");
  refreshContacts();
});

// --- Templates ---
async function refreshTemplates() {
  const r = await window.pywebview.api.templates_list();
  const list = $("#templatesList");
  if (!list) return;
  list.innerHTML = "";
  (r.items || []).forEach(t => {
    const el = document.createElement("div");
    el.className = "fact-item";
    el.innerHTML = `<span class="fact-cat"></span><span class="fact-text"></span><button class="fact-rm">×</button>`;
    el.querySelector(".fact-cat").textContent = t.name;
    el.querySelector(".fact-text").textContent = t.text.slice(0, 80) + (t.text.length > 80 ? "…" : "");
    el.querySelector(".fact-rm").onclick = async () => {
      await window.pywebview.api.templates_remove(t.id);
      refreshTemplates();
    };
    list.appendChild(el);
  });
}
$("#addTplBtn")?.addEventListener("click", async () => {
  const name = $("#newTplName").value.trim();
  const text = $("#newTplText").value.trim();
  if (!name || !text) return;
  await window.pywebview.api.templates_add(name, text);
  $("#newTplName").value = ""; $("#newTplText").value = "";
  refreshTemplates();
});

// ----- Inteligencia (Path 1 + 3) ----------------------------------------
async function refreshIntel() {
  // Vosk status
  const vk = await window.pywebview.api.vosk_status();
  const vs = $("#voskStatus");
  if (vk.ready) {
    vs.textContent = "Modelo pronto - ative o toggle";
    $("#voskDownload").hidden = true;
  } else {
    vs.textContent = "Modelo nao baixado";
    $("#voskDownload").hidden = false;
  }
  // RAG status
  const rg = await window.pywebview.api.rag_status();
  const emb = rg.embedder || {};
  $("#ragEmbedder").textContent = emb.ok
    ? `Embedder: ${emb.provider}`
    : "Embedder: NENHUM (precisa Ollama nomic-embed-text ou OPENAI_API_KEY)";
  const list = $("#ragSources");
  list.innerHTML = "";
  (rg.sources || []).forEach(s => {
    const el = document.createElement("div");
    el.className = "fact-item";
    el.innerHTML = `<span class="fact-cat">RAG</span><span class="fact-text"></span><button class="fact-rm">×</button>`;
    el.querySelector(".fact-text").textContent = `${s.source} - ${s.chunks} chunks`;
    el.querySelector(".fact-rm").onclick = async () => {
      await window.pywebview.api.rag_remove(s.source);
      refreshIntel();
    };
    list.appendChild(el);
  });
}

$("#voskDownloadBtn")?.addEventListener("click", async () => {
  $("#voskProgress").hidden = false;
  await window.pywebview.api.vosk_download();
});

$("#ragIndexBtn")?.addEventListener("click", async () => {
  const folder = $("#cfgRagFolder").value.trim();
  if (!folder) return;
  $("#ragIndexBtn").disabled = true;
  $("#ragIndexBtn").textContent = "Indexando…";
  await window.pywebview.api.rag_index(folder);
});

async function refreshBrowsers() {
  const sel = $("#cfgBrowser");
  if (!sel) return;
  try {
    const r = await window.pywebview.api.browsers();
    const items = r.items || [];
    const cur = draft.browser || currentCfg.browser || "default";
    sel.innerHTML = items.map(b => {
      const tag = b.installed ? "" : " (nao instalado)";
      return `<option value="${b.id}" ${b.installed ? "" : "disabled"}>${b.label}${tag}</option>`;
    }).join("");
    sel.value = items.some(b => b.id === cur && b.installed) ? cur : "default";
    sel.onchange = (e) => { draft.browser = e.target.value; };
  } catch (e) { console.warn("browsers fail", e); }
}

async function refreshOllama() {
  const r = await window.pywebview.api.ollama_status();
  const st = $("#ollamaStatus");
  if (r.running) {
    st.textContent = `${r.models.length} modelos disponiveis`;
    const sel = $("#cfgOllamaModel");
    const cur = sel.value;
    sel.innerHTML = `<option value="">(padrao: llama3.1)</option>` +
      r.models.map(m => `<option value="${m.name}">${m.name} (${m.size_gb}GB)</option>`).join("");
    sel.value = cur || currentCfg.ollama_model || "";
  } else {
    st.textContent = "Ollama nao detectado (rode 'ollama serve')";
  }
}
$("#ollamaRefreshBtn")?.addEventListener("click", refreshOllama);

// ----- Memoria (facts) ---------------------------------------------------
async function refreshFacts() {
  const r = await window.pywebview.api.list_facts();
  const list = $("#factsList");
  list.innerHTML = "";
  (r.facts || []).forEach(f => {
    const el = document.createElement("div");
    el.className = "fact-item";
    el.innerHTML = `<span class="fact-cat"></span><span class="fact-text"></span><button class="fact-rm">×</button>`;
    el.querySelector(".fact-cat").textContent = f.category || "geral";
    el.querySelector(".fact-text").textContent = f.text;
    el.querySelector(".fact-rm").onclick = async () => {
      await window.pywebview.api.remove_fact(f.id);
      refreshFacts();
    };
    list.appendChild(el);
  });
  if (!r.facts || !r.facts.length) {
    list.innerHTML = `<p class="hint" style="padding:8px">Nenhum fato salvo ainda.</p>`;
  }
}

$("#addFactBtn")?.addEventListener("click", async () => {
  const text = $("#newFactText").value.trim();
  const cat = $("#newFactCat").value.trim() || "geral";
  if (!text) return;
  await window.pywebview.api.add_fact(text, cat);
  $("#newFactText").value = "";
  refreshFacts();
});

// ----- MQTT --------------------------------------------------------------
$("#mqttConnectBtn")?.addEventListener("click", async () => {
  const host = $("#cfgMqttHost").value.trim();
  const port = parseInt($("#cfgMqttPort").value || "1883", 10);
  const user = $("#cfgMqttUser").value.trim();
  const pass = $("#cfgMqttPass").value;
  if (!host) { $("#mqttStatus").textContent = "Informe o host"; return; }
  $("#mqttStatus").textContent = "Conectando…";
  const r = await window.pywebview.api.configure_mqtt(host, port, user, pass);
  $("#mqttStatus").textContent = r.ok ? "Conectado" : ("Erro: " + r.error);
  $("#mqttStatus").className = "dev-status " + (r.ok ? "ok" : "err");
});

// ----- Chromecast --------------------------------------------------------
$("#castScanBtn")?.addEventListener("click", async () => {
  const btn = $("#castScanBtn");
  btn.disabled = true; btn.textContent = "Escaneando…";
  const r = await window.pywebview.api.cast_list();
  const list = $("#castList");
  list.innerHTML = "";
  (r.devices || []).forEach(d => {
    const el = document.createElement("div");
    el.className = "cast-item";
    el.innerHTML = `<div><b>${d.name}</b></div><div class="cast-meta">${d.model} · ${d.host}</div>`;
    list.appendChild(el);
  });
  if (!r.devices || !r.devices.length) {
    list.innerHTML = `<p class="hint" style="margin:8px 0">Nenhum cast encontrado.</p>`;
  }
  btn.disabled = false; btn.textContent = "Escanear";
});

$("#bleScanBtn")?.addEventListener("click", async () => {
  const btn = $("#bleScanBtn");
  const results = $("#bleResults");
  btn.disabled = true;
  btn.textContent = "Escaneando…";
  results.innerHTML = "";
  try {
    const r = await window.pywebview.api.ble_scan();
    const devs = (r.devices || []);
    if (!devs.length) {
      results.innerHTML = `<p class="hint" style="margin:8px 0">Nenhum dispositivo BLE encontrado.</p>`;
    } else {
      const knownAddrs = new Set(((currentCfg.bluetooth && currentCfg.bluetooth.known) || []).map(d => d.address));
      devs.forEach(d => results.appendChild(_bleItem(d, knownAddrs.has(d.address))));
    }
  } catch (e) {
    results.innerHTML = `<p class="hint" style="color:var(--danger);margin:8px 0">Erro no scan: ${e}</p>`;
  } finally {
    btn.disabled = false;
    btn.textContent = "Escanear";
  }
  // recarrega config pra refletir mudancas
  currentCfg = await window.pywebview.api.get_config();
  refreshKnownBLE();
});

$("#installUpdateBtn").addEventListener("click", async () => {
  if (!pendingUpdate) return;
  $("#installUpdateBtn").disabled = true;
  $("#sysStatus").textContent = "Iniciando download…";
  await window.pywebview.api.install_update(pendingUpdate.url);
});

// ----- boot --------------------------------------------------------------
function _spaceLetters(s) {
  return (s || "").toUpperCase().split("").join(".") + ".";
}

window.addEventListener("pywebviewready", async () => {
  currentCfg = await window.pywebview.api.get_config();
  catalogs   = await window.pywebview.api.get_catalogs();
  const appInfo = await window.pywebview.api.app_info();
  const name = currentCfg.identity.name;
  brandName.textContent = name;
  document.title = name;
  const hudLabel = $("#hudLabel");
  if (hudLabel) hudLabel.textContent = _spaceLetters(name);
  modelLabel.textContent = `v${appInfo.version} · ${currentCfg.mood} · ${currentCfg.accent}`;
  $("#sysAppName").textContent = appInfo.name;
  $("#sysVersion").textContent = appInfo.version;
  $("#sysStatus").textContent = "Pronto";
  addMsg("assistant", `Ola, Nicholas. ${name} pronto. Pode falar ou digitar.`);
  syncWakeMode();
});
