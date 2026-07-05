const $ = (id) => document.getElementById(id);

const app = {
  snapshot: null,
  turns: [],
  ticks: [],
  tickIndex: 0,
  playing: false,
  timer: null,
  uploadedPath: "",
  mediaType: "",
  mediaSource: "",
  teacherFocusBoxes: [],
  recorder: null,
  recordingChunks: [],
  selectedPackageId: "",
  selectedMemoryIds: new Set(),
  visibleMemoryIds: [],
  historyTurns: [],
  replayedTurn: null,
  latestTeachTarget: null,
  ttsVoiceReady: null,
};

const ACTION_LABELS = {
  move_focus: "移动视焦点",
  write_cell: "写入草稿格",
  commit_reply: "正式发出",
  reply_tts_audio: "本地朗读",
  idle_observe: "空 tick 观察",
  stop_generating: "主动停止",
  look_again_draft: "回看草稿",
  system_stop: "系统边界停止",
  type_text: "写入草稿格",
  commit: "正式发出",
};

const SOURCE_KIND_LABELS = {
  slow_cooccurrence_teacher_phrase: "慢记忆共现短句",
  styled_expression_pattern: "风格表达范式",
  legacy_runtime_candidate_evidence: "旧文本运行痕迹候选",
};

const FAMILY_LABELS = {
  phase20_input: "用户输入痕迹",
  context: "当前情境",
  source_candidate: "召回候选源",
  draft_grid: "草稿格",
  visual_candidate: "视觉候选",
  slow_memory_hint: "慢记忆提示",
  affect_evidence: "情绪/语气线索",
  reply_tts_actuator_intent: "朗读执行意图",
  teacher_guided_focus: "教师辅助视焦点",
  canvas_visual_sensor: "画布视觉输入",
  audio_audit_sensor: "音频感受器输入",
  unresolved_carry: "未闭合任务",
};

const EVIDENCE_LABELS = {
  visual_candidate_sa: "视觉候选 SA",
  saliency_only_no_label: "只给显著性，不给标签",
  auto_focus: "自动视焦点",
  teacher_guided_focus: "教师辅助视焦点",
  observe_before_write: "先观察再写",
  observation_optional: "可继续观察",
  recall_candidate: "召回候选",
  draftgrid_write: "写入草稿格",
  draftgrid_visible_text: "草稿已有内容",
  commit_readiness: "提交倾向",
  active_stop: "主动停",
  after_commit: "提交后",
  low_unresolved_pressure: "未闭合压力低",
  reply_tts: "朗读回复",
  local_browser_or_offline_actuator: "本地执行器",
  not_inner_voice: "不是内心音频",
  quiet_tick: "安静观察 tick",
  draft_review: "回看草稿",
};

const CHANNEL_LABELS = {
  text: "文本",
  external_user: "外部用户",
  context: "情境",
  phase20: "Phase20",
  memory: "记忆",
  draft: "草稿",
  vision: "视觉",
  candidate: "候选对象",
  class_agnostic: "不带类别标签",
  affect: "情绪线索",
  text_receptor: "文本感受器",
  actuator: "执行器",
  tts: "朗读",
  local_only: "本地",
  slow: "慢记忆",
  unresolved: "未闭合",
  cross_turn: "跨 turn",
  teacher_saliency: "教师显著性",
  no_label: "无标签",
  canvas: "画布",
  user_sensor_input: "用户感受器输入",
  audio: "听觉",
  recording: "录音",
  audit_only: "仅审计",
};

document.addEventListener("DOMContentLoaded", () => {
  $("turnForm").addEventListener("submit", (event) => {
    event.preventDefault();
    sendTurn();
  });
  $("refreshBtn").addEventListener("click", refreshState);
  $("refreshHistoryBtn").addEventListener("click", refreshHistory);
  $("clearBtn").addEventListener("click", () => {
    $("textInput").value = "";
    $("mediaPathInput").value = "";
    app.uploadedPath = "";
    app.mediaType = "";
    app.mediaSource = "";
    renderMediaPreview();
  });
  $("teachBtn").addEventListener("click", teachLatest);
  $("fileInput").addEventListener("change", uploadMedia);
  $("addFocusBoxBtn").addEventListener("click", addFocusBox);
  $("clearFocusBoxesBtn").addEventListener("click", () => {
    app.teacherFocusBoxes = [];
    renderFocusBoxes();
  });
  $("clearCanvasBtn").addEventListener("click", clearCanvas);
  $("useCanvasBtn").addEventListener("click", useCanvasAsImage);
  $("recordBtn").addEventListener("click", toggleRecording);
  $("refreshMemoryBtn").addEventListener("click", refreshMemoryView);
  $("exportMemoryBtn").addEventListener("click", exportSelectedMemory);
  $("importPackageBtn").addEventListener("click", importMemoryPackage);
  $("uninstallPackageBtn").addEventListener("click", uninstallSelectedPackage);
  $("previewPackageBtn").addEventListener("click", previewSelectedPackage);
  $("deleteMemoriesBtn").addEventListener("click", deleteSelectedMemories);
  $("selectVisibleMemoryBtn").addEventListener("click", selectVisibleMemories);
  $("invertVisibleMemoryBtn").addEventListener("click", invertVisibleMemories);
  $("clearSelectedMemoryBtn").addEventListener("click", clearSelectedMemories);
  $("memorySearchInput").addEventListener("input", debounce(refreshMemoryView, 250));
  document.querySelectorAll(".memoryKindInput").forEach((input) => {
    input.addEventListener("change", refreshMemoryView);
  });
  $("prevTickBtn").addEventListener("click", () => setTick(app.tickIndex - 1));
  $("nextTickBtn").addEventListener("click", () => setTick(app.tickIndex + 1));
  $("playTickBtn").addEventListener("click", togglePlayback);
  $("tickSlider").addEventListener("input", () => setTick(Number($("tickSlider").value || 0)));
  setupCanvas();
  if (window.speechSynthesis) {
    window.speechSynthesis.onvoiceschanged = () => {
      app.ttsVoiceReady = null;
    };
  }
  refreshState();
  refreshHistory();
  refreshMemoryView();
});

async function refreshState() {
  const data = await apiGet("/api/state");
  app.snapshot = data;
  renderAll();
}

async function refreshHistory() {
  const data = await apiPost("/api/phase20/history/list", { limit: 80 });
  app.historyTurns = data.turns || [];
  renderHistory();
}

async function sendTurn() {
  setBusy(true);
  try {
    const mediaPath = app.uploadedPath || $("mediaPathInput").value.trim();
    const mediaType = app.mediaType || guessMediaType(mediaPath);
    const isAudio = String(mediaType || "").startsWith("audio/");
    const payload = {
      text: $("textInput").value,
      image_path: isAudio ? "" : mediaPath,
      media_path: mediaPath,
      media_type: mediaType,
      media_source: app.mediaSource,
      teacher_focus_boxes: app.teacherFocusBoxes,
      tts_enabled: $("ttsEnabledInput").checked,
      max_ticks: Number($("maxTicksInput").value || 16),
      idle_ticks: Number($("idleTicksInput").value || 2),
    };
    const data = await apiPost("/api/phase20/turn", payload);
    app.snapshot = data.snapshot;
    app.ticks = data.turn.workbench_tick_trace || [];
    app.tickIndex = 0;
    app.replayedTurn = null;
    app.latestTeachTarget = {
      tick: data.turn.tick,
      context_signature: data.turn.context_signature || "",
      reply_text: data.turn.reply_text || "",
    };
    app.turns.push({ type: "turn", payload, turn: data.turn });
    renderAll();
    speakIfRuntimeRequested(data.turn);
    refreshMemoryView();
    refreshHistory();
  } finally {
    setBusy(false);
  }
}

async function teachLatest() {
  const text = $("teachInput").value.trim();
  if (!text) {
    $("teachStatus").textContent = "先输入教学回应";
    return;
  }
  setBusy(true);
  try {
    const data = await apiPost("/api/phase20/teach", {
      teaching_reply_text: text,
      target_tick: app.latestTeachTarget?.tick || "",
      target_context_signature: app.latestTeachTarget?.context_signature || "",
    });
    if (data.error) {
      $("teachStatus").textContent = `教学失败: ${teachErrorLabel(data.error)}`;
      return;
    }
    app.snapshot = data.snapshot;
    app.turns.push({ type: "teaching", teaching: data.teaching, target: app.latestTeachTarget });
    $("teachStatus").textContent = `已学习 ${data.teaching?.candidate_support?.toFixed ? data.teaching.candidate_support.toFixed(2) : ""}`;
    $("teachInput").value = "";
    renderAll();
    refreshMemoryView();
    refreshHistory();
  } catch (error) {
    $("teachStatus").textContent = `教学失败: ${error.message || error}`;
  } finally {
    setBusy(false);
  }
}

async function loadHistoryTurn(turnId) {
  if (!turnId) return;
  const data = await apiPost("/api/phase20/history/replay", { turn_id: turnId });
  if (data.error) {
    $("historyList").innerHTML = `<div class="list-row"><small>${escapeHtml(data.error)}</small></div>`;
    return;
  }
  app.replayedTurn = data.turn || null;
  app.ticks = data.turn?.workbench_tick_trace || [];
  app.tickIndex = 0;
  renderAll();
}

async function uploadMedia() {
  const file = $("fileInput").files && $("fileInput").files[0];
  if (!file) return;
  const dataUrl = await readAsDataUrl(file);
  const result = await uploadDataUrl(file.name, dataUrl, "upload");
  if (result?.url) renderMediaPreview(result.url, result.media_type);
}

async function uploadDataUrl(name, dataUrl, source) {
  const result = await apiPost("/api/phase20/media/upload", { name, data_url: dataUrl });
  if (result.error) {
    $("mediaPreview").textContent = result.error;
    return result;
  }
  app.uploadedPath = result.path;
  app.mediaType = result.media_type || "";
  app.mediaSource = source || "upload";
  $("mediaPathInput").value = result.path;
  return result;
}

function addFocusBox() {
  const box = {
    x: boundedNumber($("focusXInput").value, 0, 100),
    y: boundedNumber($("focusYInput").value, 0, 100),
    w: boundedNumber($("focusWInput").value, 1, 100),
    h: boundedNumber($("focusHInput").value, 1, 100),
  };
  app.teacherFocusBoxes.push(box);
  renderFocusBoxes();
}

function renderFocusBoxes() {
  $("focusBoxList").innerHTML = app.teacherFocusBoxes.length
    ? app.teacherFocusBoxes.map((box, index) => `<span class="tag">#${index + 1} x${box.x} y${box.y} w${box.w} h${box.h}</span>`).join("")
    : "无教师焦点框";
}

function setupCanvas() {
  const canvas = $("sketchCanvas");
  const ctx = canvas.getContext("2d");
  ctx.fillStyle = "#ffffff";
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  ctx.lineWidth = 4;
  ctx.lineCap = "round";
  ctx.strokeStyle = "#172126";
  let drawing = false;
  const point = (event) => {
    const rect = canvas.getBoundingClientRect();
    return {
      x: (event.clientX - rect.left) * (canvas.width / rect.width),
      y: (event.clientY - rect.top) * (canvas.height / rect.height),
    };
  };
  canvas.addEventListener("pointerdown", (event) => {
    drawing = true;
    canvas.setPointerCapture(event.pointerId);
    const p = point(event);
    ctx.beginPath();
    ctx.moveTo(p.x, p.y);
  });
  canvas.addEventListener("pointermove", (event) => {
    if (!drawing) return;
    const p = point(event);
    ctx.lineTo(p.x, p.y);
    ctx.stroke();
  });
  canvas.addEventListener("pointerup", () => { drawing = false; });
  canvas.addEventListener("pointercancel", () => { drawing = false; });
}

function clearCanvas() {
  const canvas = $("sketchCanvas");
  const ctx = canvas.getContext("2d");
  ctx.fillStyle = "#ffffff";
  ctx.fillRect(0, 0, canvas.width, canvas.height);
}

async function useCanvasAsImage() {
  const canvas = $("sketchCanvas");
  const result = await uploadDataUrl("phase20_canvas.png", canvas.toDataURL("image/png"), "canvas");
  if (result?.url) renderMediaPreview(result.url, result.media_type);
}

async function toggleRecording() {
  if (app.recorder && app.recorder.state === "recording") {
    app.recorder.stop();
    $("recordBtn").textContent = "开始录音";
    $("audioStatus").textContent = "正在保存录音";
    return;
  }
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia || !window.MediaRecorder) {
    $("audioStatus").textContent = "当前浏览器不支持录音";
    return;
  }
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  app.recordingChunks = [];
  app.recorder = new MediaRecorder(stream);
  app.recorder.ondataavailable = (event) => {
    if (event.data && event.data.size) app.recordingChunks.push(event.data);
  };
  app.recorder.onstop = async () => {
    stream.getTracks().forEach((track) => track.stop());
    const blob = new Blob(app.recordingChunks, { type: app.recorder.mimeType || "audio/webm" });
    const dataUrl = await blobToDataUrl(blob);
    const result = await uploadDataUrl("phase20_recording.webm", dataUrl, "recording");
    $("audioStatus").textContent = result?.path ? "录音已作为 audio_audit_only 输入" : "录音保存失败";
    if (result?.url) renderMediaPreview(result.url, result.media_type);
  };
  app.recorder.start();
  $("recordBtn").textContent = "停止录音";
  $("audioStatus").textContent = "正在录音";
}

function renderAll() {
  const snap = app.snapshot || {};
  $("statusLine").textContent = `tick ${snap.tick || 0} · ${snap.db_path || ""}`;
  $("turnBadge").textContent = `${app.turns.filter((item) => item.type === "turn").length} 回合`;
  const memory = snap.phase20_6_memory || {};
  $("memoryBadge").textContent = `${memory.fast_tick_count || 0} 快 / ${memory.slow_tick_count || 0} 慢`;
  renderHistory();
  renderChat();
  renderReplay();
  renderMemory(memory);
}

function renderHistory() {
  const rows = app.historyTurns || [];
  if (!$("historyList")) return;
  $("historyList").innerHTML = rows.length ? rows.map((row) => `
    <button type="button" class="history-item ${app.replayedTurn?.turn_id === row.turn_id ? "active" : ""}" data-history-turn-id="${escapeAttr(row.turn_id || "")}">
      <b>tick ${row.tick || 0} · ${escapeHtml(row.user_text || `输入 ${row.user_text_length || 0} 字`)}</b>
      <small>${escapeHtml(row.reply_text || "")}</small>
      <small>${row.runtime_event_count || 0} 个真实 tick · ${row.teaching_candidate_applied ? "已召回教学共现" : "普通回合"}</small>
    </button>
  `).join("") : `<div class="list-row"><small>暂无历史回合</small></div>`;
  document.querySelectorAll("[data-history-turn-id]").forEach((button) => {
    button.addEventListener("click", () => loadHistoryTurn(button.dataset.historyTurnId || ""));
  });
}

function renderChat() {
  if (!app.turns.length && !app.replayedTurn) {
    $("chatLog").innerHTML = `<div class="bubble system">发送一轮对话后，这里会显示用户原文、AP 回复和本轮 tick 入口。</div>`;
    return;
  }
  const replayBubble = app.replayedTurn ? `
    <div class="bubble system">
      正在回放历史回合 · tick ${app.replayedTurn.tick || 0}
      <small>只读已保存的真实 tick，不重跑 AP。</small>
    </div>
    <div class="bubble user">${escapeHtml(app.replayedTurn.live_user_text || `(输入 ${app.replayedTurn.user_text_length || 0} 字)`)}${renderBubbleMedia(app.replayedTurn.media || {})}</div>
    <div class="bubble ap">${escapeHtml(app.replayedTurn.reply_text || "")}<small>${escapeHtml(boundaryLabel(app.replayedTurn.workbench_runtime?.boundary || ""))}</small></div>
  ` : "";
  $("chatLog").innerHTML = replayBubble + app.turns.map((item) => {
    if (item.type === "teaching") {
      const trace = item.teaching?.trace || {};
      const target = item.target || {};
      return `<div class="bubble system">纠正回答「${escapeHtml(trace.response_text || "")}」 已学习<small>目标 tick ${escapeHtml(target.tick || "")} · ${escapeHtml(trace.teaching_id || "")}</small></div>`;
    }
    const turn = item.turn || {};
    const userText = item.payload?.text || "";
    const media = turn.media || {};
    return `
      <div class="bubble user">${escapeHtml(userText || "(空输入)")}${renderBubbleMedia(media)}</div>
      <div class="bubble ap">${escapeHtml(turn.reply_text || "")}<small>tick ${turn.tick} · ${escapeHtml(boundaryLabel(turn.workbench_runtime?.boundary || ""))}</small></div>
    `;
  }).join("");
  $("chatLog").scrollTop = $("chatLog").scrollHeight;
}

function renderBubbleMedia(media) {
  if (!media || !media.url) return "";
  const type = media.media_type || "";
  if (type.startsWith("audio/")) return `<audio controls src="${escapeAttr(media.url)}"></audio>`;
  return `<img alt="输入媒体" src="${escapeAttr(media.url)}">`;
}

function renderReplay() {
  const tick = currentTick();
  $("tickSlider").max = String(Math.max(0, app.ticks.length - 1));
  $("tickSlider").value = String(app.tickIndex);
  $("tickCounter").textContent = app.ticks.length ? `${app.tickIndex + 1} / ${app.ticks.length}` : "0 / 0";
  $("runtimeBadge").textContent = tick ? (tick.is_projection ? "投影数据" : "真实 tick 事件") : "等待运行";
  $("tickStrip").innerHTML = app.ticks.map((item, index) => {
    const draft = item.draft_snapshot || item.draft_changes || {};
    const outcome = item.action_chosen?.outcome_kind || draft.draft_action_kind || item.stage || "";
    const label = draft.draft_action_kind === "type_text"
      ? `${item.tick_index} 写「${draft.typed_token || ""}」`
      : `${item.tick_index} ${actionLabel(outcome)}`;
    return `<button type="button" class="${index === app.tickIndex ? "active" : ""}" data-tick="${index}">${escapeHtml(label)}</button>`;
  }).join("");
  document.querySelectorAll("[data-tick]").forEach((button) => {
    button.addEventListener("click", () => setTick(Number(button.dataset.tick || 0)));
  });
  if (!tick) {
    $("tickSummary").innerHTML = `<dt>状态</dt><dd>等待 turn</dd>`;
    $("draftGrid").textContent = "";
    $("recallList").innerHTML = emptyRow("无召回候选");
    $("actionList").innerHTML = emptyRow("无动作候选");
    $("statePoolList").innerHTML = emptyRow("无状态项");
    $("innerPicture").innerHTML = "";
    $("thoughtCloud").innerHTML = "";
    $("auditCharts").innerHTML = "";
    return;
  }
  const action = tick.action_chosen || {};
  const competition = tick.action_competition || {};
  const draft = tick.draft_snapshot || tick.draft_changes || {};
  const grid = tick.draft_grid_snapshot || {};
  const audio = tick.inner_audio_state || {};
  const tts = tick.reply_tts_request || {};
  $("tickSummary").innerHTML = kvRows({
    "当前 tick": `${tick.tick_index || ""} / 运行序号 ${tick.runtime_tick || ""}`,
    "本 tick 选择": actionLabel(action.outcome_kind || action.action_id || ""),
    "主动停状态": action.outcome_kind === "stop_generating" ? "本 tick 主动停止" : `未闭合压力 ${num(tick.unresolved_pressure)}`,
    "是否投影": tick.is_projection ? "是，不能当真运行验收" : "否，来自 RuntimeTickEvent",
    "认知压力": num(tick.cognitive_pressure),
    "听觉状态": audio.enabled ? `焦段 ${JSON.stringify(audio.focus_band || [])}` : "未启用",
    "朗读执行器": tts.selected_this_tick ? "本 tick 触发本地朗读" : (tts.requested ? "等待/已记录本地朗读请求" : "未请求"),
    "过程摘要": humanSummary(tick.summary || "", action.outcome_kind || ""),
  });
  $("draftGrid").textContent = grid.visible_text || draft.draft_buffer || draft.committed_text || "";
  renderRecall(tick.recall_candidates || []);
  renderActions(tick.actions_proposed || [], action);
  renderStatePool(tick.state_pool_top12 || []);
  renderInner(tick);
  renderThoughtCloud(tick.thought_cloud_items || []);
  renderAuditCharts(app.ticks);
}

function renderRecall(rows) {
  $("recallList").innerHTML = rows.length ? rows.map((row) => `
    <div class="list-row">
      <b>${escapeHtml(sourceKindLabel(row.source_kind || ""))}</b>
      <small>下一格「${escapeHtml(row.next_token || "")}」 · 支持 ${num(row.support)} · 优先级 ${num(row.priority)}</small>
      <small title="${escapeAttr(row.candidate_id || "")}">${shortId(row.candidate_id || "")}</small>
    </div>
  `).join("") : emptyRow("无召回候选");
}

function renderActions(rows, selected) {
  const selectedId = selected?.action_id || "";
  $("actionList").innerHTML = rows.length ? rows.map((row) => `
    <div class="list-row">
      <b>${row.action_id === selectedId ? "选中 · " : ""}${escapeHtml(actionLabel(row.outcome_kind || row.action_id || ""))}</b>
      <small>驱动力 ${num(row.drive)} · ${escapeHtml((row.evidence_tags || []).map(evidenceLabel).join(" / "))}</small>
      <small title="${escapeAttr(row.action_id || "")}">${shortId(row.action_id || "")}</small>
    </div>
  `).join("") : emptyRow("无动作候选");
}

function renderStatePool(rows) {
  $("statePoolList").innerHTML = rows.length ? rows.map((row) => `
    <div class="list-row">
      <b>${escapeHtml(familyLabel(row.family || ""))} · ${escapeHtml(readableSaLabel(row.label || ""))}</b>
      <small>R ${num(row.real_energy)} · V ${num(row.virtual_energy)} · A ${num(row.attention_energy)} · P ${num(row.cognitive_pressure)}</small>
      <small>${escapeHtml((row.channel_signature || []).map(channelLabel).join(" / "))}</small>
    </div>
  `).join("") : emptyRow("无状态项");
}

function renderInner(tick) {
  const inner = tick.inner_picture_state || {};
  const audio = tick.inner_audio_state || {};
  const layers = inner.layers || [];
  const samples = inner.samples || [];
  const focus = inner.focus_xy || tick.focus_xy;
  const sampleCanvas = samples.length ? `<canvas class="inner-canvas" id="innerSketchCanvas" aria-label="内心画面重建采样"></canvas>` : "";
  const fallbackLayers = samples.length ? "" : layers.map((layer, index) => {
      const width = Math.max(18, Number(layer.width_pct || 0) || (14 + Number(layer.scale || 1) * 10));
      const height = Math.max(14, Number(layer.height_pct || 0) || (14 + Number(layer.scale || 1) * 10));
      const radius = shapeRadius(layer.shape_bucket || "");
      const color = layer.color || "#6ea8a0";
      return `<span class="inner-layer" title="${escapeAttr(layer.source || "")}" style="left:${Number(layer.x || 50)}%;top:${Number(layer.y || 50)}%;width:${width}%;height:${height}%;opacity:${Number(layer.opacity || .2)};z-index:${20 - index};background:${escapeAttr(color)};border-radius:${radius}">${escapeHtml(layer.label || "视觉对象")}</span>`;
    }).join("");
  $("innerPicture").innerHTML = `
    ${sampleCanvas}
    ${fallbackLayers}
    ${samples.length ? `<span class="inner-boundary">感受器采样 ${samples.length} 点 · ${escapeHtml(inner.reconstruction_boundary || "")}</span>` : ""}
    ${focus ? `<span class="focus-marker" style="left:${Number(focus[0] || 50)}%;top:${Number(focus[1] || 50)}%"></span>` : ""}
    ${audio.enabled ? `<span class="audio-band">音频焦段 ${escapeHtml(JSON.stringify(audio.focus_band || []))}</span>` : ""}
  `;
  if (samples.length) drawInnerSketch(samples, focus);
}

function drawInnerSketch(samples, focus) {
  const canvas = $("innerSketchCanvas");
  const box = $("innerPicture");
  if (!canvas || !box) return;
  const rect = box.getBoundingClientRect();
  const ratio = window.devicePixelRatio || 1;
  const width = Math.max(1, Math.floor(rect.width * ratio));
  const height = Math.max(1, Math.floor(rect.height * ratio));
  canvas.width = width;
  canvas.height = height;
  canvas.style.width = "100%";
  canvas.style.height = "100%";
  const ctx = canvas.getContext("2d");
  if (!ctx) return;
  ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
  ctx.clearRect(0, 0, rect.width, rect.height);
  const gradient = ctx.createRadialGradient(rect.width * .5, rect.height * .5, 12, rect.width * .5, rect.height * .5, Math.max(rect.width, rect.height) * .62);
  gradient.addColorStop(0, "rgba(8, 20, 25, 0.96)");
  gradient.addColorStop(1, "rgba(2, 8, 12, 0.98)");
  ctx.fillStyle = gradient;
  ctx.fillRect(0, 0, rect.width, rect.height);
  const sorted = [...samples].sort((a, b) => Number(a.clarity || 0) - Number(b.clarity || 0));
  for (const sample of sorted) {
    const x = clamp(Number(sample.x || 0), 0, 100) / 100 * rect.width;
    const y = clamp(Number(sample.y || 0), 0, 100) / 100 * rect.height;
    const clarity = clamp(Number(sample.clarity || 0), 0, 1);
    const radius = Math.max(.7, Number(sample.radius || 1.5) + clarity * .35);
    const opacity = clamp(Number(sample.opacity || .25), 0, 1);
    ctx.globalAlpha = opacity;
    ctx.fillStyle = sample.color || "#88aaa2";
    ctx.beginPath();
    ctx.arc(x, y, radius, 0, Math.PI * 2);
    ctx.fill();
    if (Number(sample.edge || 0) > .22) {
      ctx.globalAlpha = Math.min(.7, opacity + .15);
      ctx.strokeStyle = "rgba(255,255,255,.34)";
      ctx.lineWidth = .5;
      ctx.stroke();
    }
  }
  if (focus) {
    const fx = clamp(Number(focus[0] || 50), 0, 100) / 100 * rect.width;
    const fy = clamp(Number(focus[1] || 50), 0, 100) / 100 * rect.height;
    const halo = ctx.createRadialGradient(fx, fy, 1, fx, fy, 70);
    halo.addColorStop(0, "rgba(255,255,255,.18)");
    halo.addColorStop(1, "rgba(255,255,255,0)");
    ctx.globalAlpha = 1;
    ctx.fillStyle = halo;
    ctx.fillRect(0, 0, rect.width, rect.height);
  }
  ctx.globalAlpha = 1;
}

function renderThoughtCloud(rows) {
  const placed = [];
  $("thoughtCloud").innerHTML = rows.length ? rows.slice(0, 18).map((row, index) => {
    const label = readableSaLabel(row.display_label || row.family || "SA");
    const size = Math.max(48, Number(row.radius || 18) * 2 + Math.min(50, label.length * 3));
    const pos = cloudPosition(row, index, size, placed);
    placed.push({ x: pos.x, y: pos.y, r: size / 2 });
    const balance = Number(row.real_virtual_balance || 0);
    const hue = balance >= 0 ? 178 : 258;
    const sat = Math.round(42 + Math.abs(balance) * 38);
    const alpha = 0.5 + Math.min(.35, Number(row.energy || 0) * .35);
    return `<span class="thought-node" title="${escapeAttr(label)}" style="width:${size}px;height:${size}px;left:${pos.x}%;top:${pos.y}%;background:hsla(${hue},${sat}%,42%,${alpha})">${escapeHtml(label)}</span>`;
  }).join("") : `<div class="list-row">无 thought cloud item</div>`;
}

function renderAuditCharts(ticks) {
  const groups = [
    { label: "状态池规模", keys: [["state_pool_count", "总数"], ["visual_state_count", "视觉"], ["text_state_count", "文本"], ["memory_state_count", "记忆"]] },
    { label: "草稿/提交长度", keys: [["draft_length", "草稿"], ["committed_length", "提交"]] },
    { label: "压力/疲劳", keys: [["mean_cognitive_pressure", "压力"], ["mean_fatigue", "疲劳"]] },
    { label: "注意/实能量", keys: [["max_attention_energy", "最高注意"], ["max_real_energy", "最高实能量"]] },
    { label: "对象数量", keys: [["object_file_count", "对象"], ["visual_state_count", "视觉 SA"]] },
    { label: "运行用时", keys: [["runtime_ms", "总 ms"]] },
  ];
  $("auditCharts").innerHTML = groups.map((group) => multiChart(group.label, group.keys.map(([key, label]) => ({
    key,
    label,
    values: ticks.map((tick) => metric(tick, key)),
  })))).join("");
}

function renderMemory(memory) {
  $("fastMemory").innerHTML = emptyRow(`已合并到“本地记忆 / 记忆包” · ${memory.fast_tick_count || 0} 条 tick 快记忆`);
  $("slowMemory").innerHTML = emptyRow(`已合并到“本地记忆 / 记忆包” · ${memory.slow_tick_count || 0} 条 tick 慢记忆`);
  $("carryMemory").innerHTML = (memory.unresolved_top || []).length ? memory.unresolved_top.map((row) => `
    <div class="list-row"><b>${escapeHtml(readableSaLabel(row.context_signature || ""))}</b><small>压力 ${num(row.pressure)} · 是否闭合 ${Boolean(row.closed) ? "是" : "否"}</small></div>
  `).join("") : emptyRow("暂无未闭合 carry");
}

async function refreshMemoryView() {
  const query = $("memorySearchInput")?.value || "";
  const data = await apiPost("/api/phase20/memory/list", {
    query,
    kinds: selectedMemoryKinds(),
    limit: 160,
  });
  renderMemoryView(data);
}

function renderMemoryView(data) {
  const memories = data.memories || [];
  const packages = data.packages || [];
  app.visibleMemoryIds = memories.map((item) => item.memory_id).filter(Boolean);
  $("memoryList").innerHTML = memories.length ? memories.map((item) => `
    <label class="list-row select-row">
      <input type="checkbox" data-memory-id="${escapeAttr(item.memory_id || "")}" ${app.selectedMemoryIds.has(item.memory_id) ? "checked" : ""}>
      <span>
        <b>${escapeHtml(item.display_title || item.text || item.memory_id || "")}</b>
        <small>${escapeHtml(item.display_detail || item.kind_label || "")}</small>
        <small>${escapeHtml(item.memory_id || "")}</small>
      </span>
    </label>
  `).join("") : emptyRow("暂无可显示记忆");
  document.querySelectorAll("[data-memory-id]").forEach((checkbox) => {
    checkbox.addEventListener("change", () => {
      if (checkbox.checked) app.selectedMemoryIds.add(checkbox.dataset.memoryId);
      else app.selectedMemoryIds.delete(checkbox.dataset.memoryId);
      renderSelectedMemoryCount();
    });
  });
  renderSelectedMemoryCount();
  $("packageList").innerHTML = packages.length ? packages.map((item) => `
    <label class="list-row select-row">
      <input type="radio" name="packageSelect" data-package-id="${escapeAttr(item.package_id || "")}" ${app.selectedPackageId === item.package_id ? "checked" : ""}>
      <span>
        <b>${escapeHtml(item.name || item.package_id || "")}</b>
        <small>${escapeHtml(item.status || "")} · added ${item.added_count || 0} · dedup ${item.dedup_count || 0}</small>
        <small>${escapeHtml(item.package_id || "")}</small>
      </span>
    </label>
  `).join("") : emptyRow("暂无导入记忆包");
  document.querySelectorAll("[data-package-id]").forEach((radio) => {
    radio.addEventListener("change", () => {
      if (radio.checked) app.selectedPackageId = radio.dataset.packageId || "";
      $("packagePreview").innerHTML = emptyRow("点击查看选中包后显示包内记忆");
    });
  });
  if (!$("packagePreview").innerHTML) {
    $("packagePreview").innerHTML = emptyRow("点击查看选中包后显示包内记忆");
  }
}

async function exportSelectedMemory() {
  const ids = [...app.selectedMemoryIds];
  const excludeMode = $("excludeSelectedInput").checked;
  const payload = {
    name: $("packageNameInput").value || "APV3 教学记忆包",
    query: $("memorySearchInput").value || "",
    kinds: selectedMemoryKinds(),
    include_memory_ids: excludeMode ? [] : ids,
    exclude_memory_ids: excludeMode ? ids : [],
  };
  const data = await apiPost("/api/phase20/memory/export", payload);
  $("packageOutput").textContent = JSON.stringify(data, null, 2);
}

async function previewSelectedPackage() {
  if (!app.selectedPackageId) {
    $("packagePreview").innerHTML = emptyRow("请先选择一个记忆包");
    return;
  }
  const data = await apiPost("/api/phase20/memory/list", {
    package_id: app.selectedPackageId,
    query: $("memorySearchInput").value || "",
    kinds: selectedMemoryKinds(),
    limit: 160,
  });
  const memories = data.memories || [];
  $("packagePreview").innerHTML = memories.length ? memories.map((item) => `
    <div class="list-row">
      <b>${escapeHtml(item.display_title || item.text || item.memory_id || "")}</b>
      <small>${escapeHtml(item.display_detail || item.kind_label || "")}</small>
      <small>${escapeHtml(item.memory_id || "")}</small>
    </div>
  `).join("") : emptyRow("选中包内没有匹配当前筛选的记忆");
}

async function importMemoryPackage() {
  const raw = $("packageImportText").value.trim();
  if (!raw) {
    $("packageOutput").textContent = "请先粘贴记忆包 JSON";
    return;
  }
  const packagePayload = JSON.parse(raw);
  const data = await apiPost("/api/phase20/memory/import", { package: packagePayload });
  $("packageOutput").textContent = JSON.stringify(data.import || data, null, 2);
  renderMemoryView(data.memory || {});
  refreshState();
}

async function uninstallSelectedPackage() {
  if (!app.selectedPackageId) {
    $("packageOutput").textContent = "请先选择一个记忆包";
    return;
  }
  const data = await apiPost("/api/phase20/memory/uninstall", { package_id: app.selectedPackageId });
  $("packageOutput").textContent = JSON.stringify(data.uninstall || data, null, 2);
  renderMemoryView(data.memory || {});
  $("packagePreview").innerHTML = emptyRow("已卸载，包内新增记忆已回退");
  refreshState();
}

async function deleteSelectedMemories() {
  const ids = [...app.selectedMemoryIds];
  if (!ids.length) {
    $("packageOutput").textContent = "请先勾选要删除的记忆";
    return;
  }
  const data = await apiPost("/api/phase20/memory/delete", { memory_ids: ids });
  app.selectedMemoryIds.clear();
  $("packageOutput").textContent = JSON.stringify(data.delete || data, null, 2);
  renderMemoryView(data.memory || {});
  refreshState();
}

function selectedMemoryKinds() {
  return [...document.querySelectorAll(".memoryKindInput")]
    .filter((input) => input.checked)
    .map((input) => input.value);
}

function selectVisibleMemories() {
  app.visibleMemoryIds.forEach((id) => app.selectedMemoryIds.add(id));
  refreshMemoryCheckboxes();
}

function invertVisibleMemories() {
  app.visibleMemoryIds.forEach((id) => {
    if (app.selectedMemoryIds.has(id)) app.selectedMemoryIds.delete(id);
    else app.selectedMemoryIds.add(id);
  });
  refreshMemoryCheckboxes();
}

function clearSelectedMemories() {
  app.selectedMemoryIds.clear();
  refreshMemoryCheckboxes();
}

function refreshMemoryCheckboxes() {
  document.querySelectorAll("[data-memory-id]").forEach((checkbox) => {
    checkbox.checked = app.selectedMemoryIds.has(checkbox.dataset.memoryId);
  });
  renderSelectedMemoryCount();
}

function renderSelectedMemoryCount() {
  if ($("selectedMemoryCount")) {
    $("selectedMemoryCount").textContent = `已选 ${app.selectedMemoryIds.size}`;
  }
}

function setTick(index) {
  if (!app.ticks.length) return;
  app.tickIndex = Math.max(0, Math.min(app.ticks.length - 1, Number(index || 0)));
  renderReplay();
}

function togglePlayback() {
  if (!app.ticks.length) return;
  app.playing = !app.playing;
  $("playTickBtn").textContent = app.playing ? "暂停" : "播放";
  if (app.timer) clearInterval(app.timer);
  if (app.playing) {
    app.timer = setInterval(() => {
      if (app.tickIndex >= app.ticks.length - 1) {
        app.playing = false;
        $("playTickBtn").textContent = "播放";
        clearInterval(app.timer);
        return;
      }
      setTick(app.tickIndex + 1);
    }, 650);
  }
}

function currentTick() {
  return app.ticks[Math.max(0, Math.min(app.tickIndex, app.ticks.length - 1))] || null;
}

function renderMediaPreview(url, mediaType) {
  const path = $("mediaPathInput").value.trim();
  if (!path && !url) {
    $("mediaPreview").textContent = "未选择媒体";
    return;
  }
  if (url && String(mediaType || "").startsWith("image/")) {
    $("mediaPreview").innerHTML = `<img alt="上传预览" src="${escapeAttr(url)}"><small>${escapeHtml(path || app.uploadedPath)}</small>`;
  } else if (url && String(mediaType || "").startsWith("audio/")) {
    $("mediaPreview").innerHTML = `<audio controls src="${escapeAttr(url)}"></audio><small>${escapeHtml(path || app.uploadedPath)}</small>`;
  } else {
    $("mediaPreview").textContent = path || app.uploadedPath || "媒体已选择";
  }
}

function speakIfRuntimeRequested(turn) {
  const shouldSpeak = (turn?.workbench_tick_trace || []).some((tick) => tick?.reply_tts_request?.selected_this_tick);
  if (!shouldSpeak || !window.speechSynthesis || !turn?.reply_text) return;
  ensureTtsVoices().then((voice) => {
    const utterance = new SpeechSynthesisUtterance(turn.reply_text);
    utterance.lang = "zh-CN";
    if (voice) utterance.voice = voice;
    const selected = voice ? `${voice.name || ""} ${voice.lang || ""}`.trim() : "未找到 xiaoyi, 浏览器使用默认声线";
    $("statusLine").textContent = `${$("statusLine").textContent} · TTS ${selected}`;
    window.speechSynthesis.cancel();
    window.speechSynthesis.speak(utterance);
  });
}

function metric(tick, key) {
  const audit = (tick.draft_snapshot || tick.draft_changes || {}).audit_metrics || {};
  return Number(audit[key] || 0);
}

function multiChart(label, series) {
  const allValues = series.flatMap((row) => row.values.map((value) => Number(value || 0)));
  const max = Math.max(1, ...allValues);
  const palette = ["#245a8f", "#0f766e", "#9a6a18", "#a33b35"];
  const lines = series.map((row, seriesIndex) => {
    const points = row.values.map((value, index) => {
      const x = row.values.length <= 1 ? 3 : 3 + (index / (row.values.length - 1)) * 94;
      const y = 38 - (Number(value || 0) / max) * 32;
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    }).join(" ");
    return `<polyline points="${points}" style="stroke:${palette[seriesIndex % palette.length]}"></polyline>`;
  }).join("");
  const currentTick = Math.max(0, Math.min(app.tickIndex, Math.max(0, (series[0]?.values?.length || 1) - 1)));
  const current = series.map((row) => `${row.label} ${num(row.values[currentTick] ?? row.values[row.values.length - 1] ?? 0)}`).join(" · ");
  const legend = series.map((row, index) => `<span style="--legend:${palette[index % palette.length]}">${escapeHtml(row.label)}</span>`).join("");
  const tooltip = series.map((row) => `${row.label}: ${num(row.values[currentTick] ?? 0)}`).join(" | ");
  const x = series[0]?.values?.length <= 1 ? 3 : 3 + (currentTick / (series[0].values.length - 1)) * 94;
  return `
    <div class="mini-chart" title="tick ${currentTick + 1} · ${escapeAttr(tooltip)}">
      <small>${escapeHtml(label)}<b>${escapeHtml(current)}</b></small>
      <svg viewBox="0 0 100 42" preserveAspectRatio="none">
        ${lines}
        <line class="chart-cursor" x1="${x.toFixed(1)}" y1="4" x2="${x.toFixed(1)}" y2="40"></line>
      </svg>
      <div class="chart-tooltip">tick ${currentTick + 1} · ${escapeHtml(tooltip)}</div>
      <div class="chart-legend">${legend}</div>
    </div>
  `;
}

function ensureTtsVoices() {
  if (app.ttsVoiceReady) return app.ttsVoiceReady;
  app.ttsVoiceReady = new Promise((resolve) => {
    const pick = () => resolve(preferredTtsVoice());
    const voices = window.speechSynthesis?.getVoices?.() || [];
    if (voices.length) {
      pick();
      return;
    }
    const previous = window.speechSynthesis.onvoiceschanged;
    window.speechSynthesis.onvoiceschanged = () => {
      if (typeof previous === "function") previous();
      pick();
    };
    setTimeout(pick, 900);
  });
  return app.ttsVoiceReady;
}

function preferredTtsVoice() {
  const voices = window.speechSynthesis?.getVoices?.() || [];
  return voices.find((voice) => /xiaoyi|xiao yi|晓伊|小艺|小依/i.test(`${voice.name || ""} ${voice.voiceURI || ""}`))
    || voices.find((voice) => /zh|chinese|中文|普通话|huihui/i.test(`${voice.name || ""} ${voice.lang || ""}`))
    || null;
}

function teachErrorLabel(value) {
  const text = String(value || "");
  if (text.includes("needs_previous_turn")) return "还没有可纠正的上一轮";
  if (text.includes("target_context_changed") || text.includes("target_tick_changed")) return "目标回合已经变化, 请先确认要教的是最新一轮";
  if (text.includes("empty_teaching_reply")) return "教学内容为空";
  if (text.includes("teaching_reply_too_long")) return "教学内容太长, 请先用短回应/短标注";
  if (text.includes("style_rejected")) return "教学内容被风格边界拒绝";
  return text || "未知错误";
}

function actionLabel(value) {
  const key = String(value || "").replace(/^phase20_6::/, "");
  return ACTION_LABELS[key] || key || "未选择";
}

function sourceKindLabel(value) {
  return SOURCE_KIND_LABELS[String(value || "")] || String(value || "未知来源");
}

function boundaryLabel(value) {
  const text = String(value || "");
  if (text === "per_tick_ap_loop_snapshot_not_stage_pipeline") return "逐 tick 真实循环，不是阶段流水线";
  if (text === "stored_runtime_tick_events_replay") return "历史真实 tick 回放";
  if (text === "recall_candidate_to_action_competition_to_draftgrid_commit") return "召回候选 → 动作竞争 → 草稿格 → 发出";
  return text;
}

function familyLabel(value) {
  return FAMILY_LABELS[String(value || "")] || String(value || "状态项");
}

function evidenceLabel(value) {
  return EVIDENCE_LABELS[String(value || "")] || String(value || "");
}

function channelLabel(value) {
  return CHANNEL_LABELS[String(value || "")] || String(value || "");
}

function readableSaLabel(value) {
  const text = String(value || "");
  if (!text) return "";
  if (text === "empty") return "空草稿";
  if (text.startsWith("visual_candidate::")) return `视觉候选 ${shortId(text)}`;
  if (text.startsWith("teacher_phrase::")) return `教师短句 ${shortId(text)}`;
  if (text.startsWith("style::")) return `风格范式 ${shortId(text)}`;
  if (text.startsWith("phase20ctx::")) return `情境 ${shortId(text)}`;
  if (text.startsWith("slow_source::")) return `慢记忆来源 ${shortId(text)}`;
  if (text.startsWith("visual_signature::compound::")) return `复合视觉签名 ${shortId(text)}`;
  if (text.length > 42 && /^[a-z0-9_:|.-]+$/i.test(text)) return shortId(text);
  return text;
}

function humanSummary(summary, outcome) {
  const action = actionLabel(outcome);
  if (outcome === "write_cell") return `动作竞争选择“写入草稿格”：${summary}`;
  if (outcome === "move_focus") return "动作竞争选择“移动视焦点”，本 tick 主要观察图像。";
  if (outcome === "commit_reply") return "动作竞争选择“正式发出”，草稿格内容变成正式回复。";
  if (outcome === "stop_generating") return "动作竞争选择“主动停止”，表示本轮未闭合压力已经足够低。";
  return summary ? `${action}：${summary}` : action;
}

function shapeRadius(shape) {
  if (shape === "wide") return "999px / 60%";
  if (shape === "tall") return "60% / 999px";
  if (shape === "balanced") return "50%";
  return "8px";
}

function cloudPosition(row, index, size, placed) {
  const centerPull = Math.max(0, Math.min(1, Number(row.energy || 0)));
  let x = (Number(row.x_hint || ((index * 31) % 100) / 100) * 46) + 27;
  let y = (Number(row.y_hint || ((index * 47) % 100) / 100) * 46) + 27;
  x = x * (1 - centerPull * 0.48) + 50 * centerPull * 0.48;
  y = y * (1 - centerPull * 0.48) + 50 * centerPull * 0.48;
  for (let attempt = 0; attempt < 24; attempt += 1) {
    const overlapping = placed.some((item) => {
      const dx = (x - item.x) * 3.6;
      const dy = (y - item.y) * 2.8;
      return Math.sqrt(dx * dx + dy * dy) < (size / 2 + item.r) * 0.42;
    });
    if (!overlapping) break;
    const angle = (index + attempt * 1.7) * 1.618;
    const radius = 4 + attempt * 1.05;
    x = Math.max(8, Math.min(92, 50 + Math.cos(angle) * radius));
    y = Math.max(10, Math.min(90, 50 + Math.sin(angle) * radius * .72));
  }
  return { x: Math.max(8, Math.min(92, x)), y: Math.max(8, Math.min(92, y)) };
}

function shortId(value) {
  const text = String(value || "");
  if (text.length <= 20) return text;
  return `${text.slice(0, 10)}…${text.slice(-6)}`;
}

function kvRows(rows) {
  return Object.entries(rows).map(([key, value]) => `<dt>${escapeHtml(key)}</dt><dd>${escapeHtml(value)}</dd>`).join("");
}

function emptyRow(text) {
  return `<div class="list-row"><small>${escapeHtml(text)}</small></div>`;
}

async function apiGet(path) {
  const response = await fetch(path, { cache: "no-store" });
  if (!response.ok) throw new Error(`${path} ${response.status}`);
  return response.json();
}

async function apiPost(path, payload) {
  const response = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload || {}),
  });
  if (!response.ok) throw new Error(`${path} ${response.status}`);
  return response.json();
}

function readAsDataUrl(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result || ""));
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

function blobToDataUrl(blob) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result || ""));
    reader.onerror = reject;
    reader.readAsDataURL(blob);
  });
}

function setBusy(value) {
  document.querySelectorAll("button").forEach((button) => { button.disabled = Boolean(value); });
}

function num(value) {
  return Number(value || 0).toFixed(3);
}

function clamp(value, min, max) {
  const number = Number(value);
  if (!Number.isFinite(number)) return min;
  return Math.max(min, Math.min(max, number));
}

function boundedNumber(value, min, max) {
  const number = Number(value || 0);
  return clamp(Number.isFinite(number) ? number : min, min, max);
}

function guessMediaType(path) {
  const lower = String(path || "").toLowerCase();
  if (/\.(png|jpg|jpeg|webp|gif|bmp)$/.test(lower)) return "image/" + (lower.endsWith(".png") ? "png" : lower.endsWith(".webp") ? "webp" : "jpeg");
  if (/\.(wav|mp3|ogg|webm|m4a)$/.test(lower)) return lower.endsWith(".wav") ? "audio/wav" : lower.endsWith(".mp3") ? "audio/mpeg" : lower.endsWith(".ogg") ? "audio/ogg" : "audio/webm";
  return "";
}

function debounce(fn, delay) {
  let handle = null;
  return (...args) => {
    if (handle) clearTimeout(handle);
    handle = setTimeout(() => fn(...args), delay);
  };
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (ch) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  }[ch]));
}

function escapeAttr(value) {
  return escapeHtml(value).replace(/`/g, "&#96;");
}
