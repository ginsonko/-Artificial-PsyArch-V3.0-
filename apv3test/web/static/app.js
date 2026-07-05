const state = {
  snapshot: null,
  mode: "uncertain",
  phase20Turn: null,
  phase20Teaching: null,
  phase20History: [],
  memoryView: null,
  selectedPackageId: "",
  mediaDraft: null,
  workbenchTicks: [],
  workbenchRuntime: null,
  workbenchTickIndex: 0,
  playbackTimer: null,
  playbackPlaying: false,
};

const $ = (id) => document.getElementById(id);

async function api(path, options = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    cache: "no-store",
    ...options,
  });
  const data = await res.json();
  if (!res.ok || data.error) throw new Error(data.error || `HTTP ${res.status}`);
  return data;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

async function boot() {
  bindEvents();
  await refresh();
  await refreshMemoryView();
}

function bindEvents() {
  $("sendForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    await postPhase20Turn({ includeMedia: false });
  });
  $("phase20SendBtn").addEventListener("click", () => postPhase20Turn({ includeMedia: true }));
  $("teachBtn").addEventListener("click", postPhase20Teach);
  $("rewardBtn").addEventListener("click", () => postPhase20Feedback("positive"));
  $("punishBtn").addEventListener("click", () => postPhase20Feedback("negative"));
  $("mediaFileInput").addEventListener("change", handleMediaFile);
  $("imagePathInput").addEventListener("input", () => {
    if (!$("imagePathInput").value.trim()) state.mediaDraft = null;
    renderMediaPreview();
  });
  $("memoryRefreshBtn").addEventListener("click", () => refreshMemoryView(state.selectedPackageId));
  $("memoryExportBtn").addEventListener("click", exportMemoryPackage);
  $("memoryImportBtn").addEventListener("click", importMemoryPackage);
  $("memoryDeleteBtn").addEventListener("click", deleteSelectedMemories);
  $("memorySelectAllBtn").addEventListener("click", () => setMemorySelection(true));
  $("memoryInvertBtn").addEventListener("click", invertMemorySelection);
  $("refreshBtn").addEventListener("click", refresh);
  $("tickPrevBtn").addEventListener("click", () => stepWorkbenchTick(-1));
  $("tickNextBtn").addEventListener("click", () => stepWorkbenchTick(1));
  $("tickPlayBtn").addEventListener("click", toggleTickPlayback);
  $("tickSlider").addEventListener("input", (event) => {
    setWorkbenchTick(Number(event.target.value || 0));
  });
  document.querySelectorAll(".demo-image").forEach((button) => {
    button.addEventListener("click", () => {
      const path = button.dataset.path || "";
      $("imagePathInput").value = path;
      state.mediaDraft = {
        kind: "image",
        mediaType: "image/png",
        path,
        url: localMediaUrl(path),
        name: button.textContent || "示例图片",
      };
      renderMediaPreview();
    });
  });
  document.querySelectorAll(".mode").forEach((button) => {
    button.addEventListener("click", () => setMode(button.dataset.mode));
  });
  document.querySelectorAll(".tab").forEach((button) => {
    button.addEventListener("click", () => switchTab(button.dataset.tab));
  });
}

async function postPhase20Turn({ includeMedia = false } = {}) {
  const text = $("messageInput").value.trim();
  const typedPath = $("imagePathInput").value.trim();
  const media = includeMedia ? mediaFromDraftOrPath(typedPath) : null;
  const isImage = media && String(media.mediaType || "").startsWith("image/");
  if (!text && !media) return;
  $("messageInput").value = "";
  const payload = {
    text,
    image_path: isImage ? media.path : null,
    media_path: media ? media.path : null,
    media_type: media ? media.mediaType : "",
    max_ticks: numberInput("maxTicksInput", 16),
    idle_ticks: numberInput("idleTicksInput", 2),
  };
  const data = await api("/api/phase20/turn", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  state.phase20Turn = data.turn;
  state.workbenchTicks = data.turn.workbench_tick_trace || [];
  state.workbenchRuntime = data.turn.workbench_runtime || null;
  state.workbenchTickIndex = 0;
  state.phase20History.push({
    type: "turn",
    text,
    media,
    turn: data.turn,
  });
  applySnapshot(data.snapshot);
  await refreshMemoryView(state.selectedPackageId);
}

async function postPhase20Feedback(kind) {
  const data = await api("/api/phase20/turn", {
    method: "POST",
    body: JSON.stringify({
      text: "",
      feedback_kind: kind,
      max_ticks: numberInput("maxTicksInput", 16),
      idle_ticks: numberInput("idleTicksInput", 2),
    }),
  });
  state.phase20Turn = data.turn;
  state.workbenchTicks = data.turn.workbench_tick_trace || [];
  state.workbenchRuntime = data.turn.workbench_runtime || null;
  state.workbenchTickIndex = 0;
  state.phase20History.push({
    type: "feedback",
    kind,
    turn: data.turn,
  });
  applySnapshot(data.snapshot);
  await refreshMemoryView(state.selectedPackageId);
}

async function postPhase20Teach() {
  const teaching = $("teachingReplyInput").value.trim();
  if (!teaching) return;
  $("teachingReplyInput").value = "";
  const data = await api("/api/phase20/teach", {
    method: "POST",
    body: JSON.stringify({ teaching_reply_text: teaching }),
  });
  state.phase20Teaching = data.teaching;
  state.phase20History.push({ type: "teaching", teaching: data.teaching });
  applySnapshot(data.snapshot);
  await refreshMemoryView(state.selectedPackageId);
}

async function handleMediaFile(event) {
  const file = event.target.files && event.target.files[0];
  if (!file) return;
  if (!(file.type.startsWith("image/") || file.type.startsWith("audio/"))) {
    state.mediaDraft = { kind: "error", name: file.name, error: "只支持图片或音频" };
    renderMediaPreview();
    return;
  }
  const dataUrl = await fileToDataUrl(file);
  const uploaded = await api("/api/phase20/media/upload", {
    method: "POST",
    body: JSON.stringify({ name: file.name, data_url: dataUrl }),
  });
  state.mediaDraft = {
    kind: file.type.startsWith("image/") ? "image" : "audio",
    mediaType: uploaded.media_type || file.type,
    path: uploaded.path,
    url: uploaded.url,
    name: file.name,
  };
  if (state.mediaDraft.kind === "image") $("imagePathInput").value = uploaded.path;
  renderMediaPreview();
}

function fileToDataUrl(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result || ""));
    reader.onerror = () => reject(reader.error || new Error("file_read_failed"));
    reader.readAsDataURL(file);
  });
}

function mediaFromDraftOrPath(path) {
  if (state.mediaDraft && state.mediaDraft.path) return state.mediaDraft;
  if (!path) return null;
  const mediaType = guessMediaType(path);
  return {
    kind: mediaType.startsWith("audio/") ? "audio" : "image",
    mediaType,
    path,
    url: localMediaUrl(path),
    name: path.split(/[\\/]/).pop() || "本地媒体",
  };
}

function guessMediaType(path) {
  const lower = String(path || "").toLowerCase();
  if (/\.(wav|mp3|ogg|m4a|flac)$/.test(lower)) return "audio/wav";
  if (/\.(jpg|jpeg)$/.test(lower)) return "image/jpeg";
  if (/\.webp$/.test(lower)) return "image/webp";
  return "image/png";
}

function localMediaUrl(path) {
  return `/api/phase20/media?path=${encodeURIComponent(path)}`;
}

async function setMode(mode) {
  const data = await api("/api/mode", {
    method: "POST",
    body: JSON.stringify({ mode }),
  });
  applySnapshot(data.snapshot);
}

async function refresh() {
  applySnapshot(await api("/api/state"));
}

async function refreshMemoryView(packageId = "") {
  const query = $("memoryQueryInput")?.value.trim() || "";
  state.selectedPackageId = packageId || "";
  state.memoryView = await api("/api/phase20/memory/list", {
    method: "POST",
    body: JSON.stringify({ query, package_id: state.selectedPackageId, limit: 220 }),
  });
  renderMemory();
}

async function exportMemoryPackage() {
  const ids = selectedMemoryIds();
  const query = $("memoryQueryInput")?.value.trim() || "";
  const name = $("memoryPackageNameInput")?.value.trim() || "APV3 记忆包";
  const pkg = await api("/api/phase20/memory/export", {
    method: "POST",
    body: JSON.stringify({ name, query, include_memory_ids: ids }),
  });
  $("memoryPackageText").value = JSON.stringify(pkg, null, 2);
  await refreshMemoryView(state.selectedPackageId);
}

async function importMemoryPackage() {
  const raw = $("memoryPackageText").value.trim();
  if (!raw) return;
  const pkg = JSON.parse(raw);
  const data = await api("/api/phase20/memory/import", {
    method: "POST",
    body: JSON.stringify({ package: pkg }),
  });
  state.memoryView = data.memory;
  state.selectedPackageId = "";
  renderMemory();
}

async function uninstallMemoryPackage(packageId) {
  const data = await api("/api/phase20/memory/uninstall", {
    method: "POST",
    body: JSON.stringify({ package_id: packageId }),
  });
  state.memoryView = data.memory;
  state.selectedPackageId = "";
  renderMemory();
}

async function deleteSelectedMemories() {
  const ids = selectedMemoryIds();
  if (!ids.length) return;
  const data = await api("/api/phase20/memory/delete", {
    method: "POST",
    body: JSON.stringify({ memory_ids: ids }),
  });
  state.memoryView = data.memory;
  renderMemory();
}

function applySnapshot(snapshot) {
  state.snapshot = snapshot;
  state.mode = snapshot.mode || "uncertain";
  renderAll();
}

function renderAll() {
  const snapshot = state.snapshot || {};
  $("statusLine").textContent = `tick ${snapshot.tick || 0} · ${snapshot.db_path || ""}`;
  document.querySelectorAll(".mode").forEach((button) => {
    button.classList.toggle("active", button.dataset.mode === state.mode);
  });
  renderChat();
  renderMetrics();
  renderChart();
  renderReplay();
  renderPhrases();
  renderCloud();
  renderAudit();
  renderPhase8();
  renderInner();
  renderPhase20();
  renderMediaPreview();
  renderMemory();
}

function renderChat() {
  if (state.phase20History.length) {
    $("chatTimeline").innerHTML = state.phase20History.map(renderHistoryEvent).join("");
    $("chatTimeline").scrollTop = $("chatTimeline").scrollHeight;
    return;
  }
  const trace = state.snapshot?.chat_trace || [];
  $("chatTimeline").innerHTML = trace.length ? trace.map((row) => {
    const fallback = row.used_honest_fallback ? " fallback" : "";
    return `
      <div class="bubble user muted-history"><span class="meta">历史 tick ${row.tick} · ${escapeHtml(row.mode)}</span><span class="bubble-text">${escapeHtml(inputLabel(row))}</span></div>
      <div class="bubble ap${fallback}"><span class="meta">${escapeHtml(row.feeling_label || "")}</span><span class="bubble-text">${escapeHtml(row.presented_text || "")}</span></div>
    `;
  }).join("") : `<div class="empty-chat">当前会话还没有消息。</div>`;
  $("chatTimeline").scrollTop = $("chatTimeline").scrollHeight;
}

function renderHistoryEvent(event) {
  if (event.type === "teaching") {
    const trace = event.teaching?.trace || {};
    return `
      <div class="bubble system">
        <span class="meta">teacher_event_cooccurrence · 不覆盖聊天</span>
        纠正回答 "${escapeHtml(trace.response_text || "")}" 已学习
        <small>奖励 +${Number(trace.reward_delta || 0).toFixed(2)} · 旧回复惩罚 -${Number(trace.previous_reply_punish_delta || 0).toFixed(2)}</small>
      </div>
    `;
  }
  if (event.type === "feedback") {
    const trace = event.turn?.feedback_trace || {};
    const label = event.kind === "positive" ? "奖励上一轮" : "惩罚/纠正上一轮";
    return `
      <div class="bubble system">
        <span class="meta">feedback · AP-native correction</span>
        ${escapeHtml(label)} 已记录
        <small>${escapeHtml(trace.target_label || "无视觉对象")} · outcome ${Number(trace.correction_total_outcome || 0).toFixed(3)}</small>
      </div>
    `;
  }
  const turn = event.turn || {};
  const media = event.media || null;
  const objects = (turn.object_files || []).map((item) => (
    `${item.top_visible_label} · ${item.decision_tier} · ${Number(item.raw_confidence || 0).toFixed(3)}`
  ));
  const meta = turn.teaching_applied
    ? `Phase20 · 教师共现候选`
    : `Phase20 · ${turn.styled ? turn.styled.paradigm_id : "styled"}`;
  return `
    <div class="bubble user">
      <span class="meta">tick ${turn.tick || 0}${media ? " · 媒体" : ""}</span>
      <span class="bubble-text">${escapeHtml(event.text || "(空文字)")}</span>
      ${renderMedia(media)}
    </div>
    <div class="bubble ap">
      <span class="meta">${escapeHtml(meta)}</span>
      <span class="bubble-text">${escapeHtml(turn.reply_text || "")}</span>
      ${objects.length ? `<small>${escapeHtml(objects.join(" / "))}</small>` : ""}
    </div>
  `;
}

function renderMedia(media) {
  if (!media || !media.url) return "";
  if (String(media.mediaType || "").startsWith("audio/") || media.kind === "audio") {
    return `<audio class="bubble-media" controls src="${escapeHtml(media.url)}"></audio>`;
  }
  return `<img class="bubble-media" src="${escapeHtml(media.url)}" alt="${escapeHtml(media.name || "图片")}">`;
}

function renderMediaPreview() {
  const node = $("mediaPreview");
  if (!node) return;
  const typedPath = $("imagePathInput")?.value.trim() || "";
  const media = state.mediaDraft || (typedPath ? mediaFromDraftOrPath(typedPath) : null);
  if (!media) {
    node.className = "media-preview empty";
    node.textContent = "未选择媒体";
    return;
  }
  node.className = "media-preview";
  const body = renderMedia(media) || `<span>${escapeHtml(media.error || media.path || "")}</span>`;
  node.innerHTML = `${body}<small>${escapeHtml(media.name || media.path || "")}</small>`;
}

function renderPhase20() {
  const turn = state.phase20Turn;
  const teaching = state.phase20Teaching;
  if (!turn && !teaching) {
    $("phase20Panel").innerHTML = "";
    return;
  }
  const objects = ((turn && turn.object_files) || []).map((item) => (
    `${escapeHtml(item.top_visible_label)} · ${escapeHtml(item.decision_tier)} · ${Number(item.raw_confidence || 0).toFixed(3)}`
  )).join("<br>");
  const teachTrace = teaching?.trace || turn?.teaching_trace || null;
  const feedback = turn?.feedback_trace || null;
  const runtime = turn?.workbench_runtime || {};
  $("phase20Panel").innerHTML = `
    ${kv("本轮回复", turn?.reply_text || "")}
    ${kv("context", turn?.context_signature || "none")}
    ${kv("image", turn?.image_sha16 || "none")}
    ${kv("objects", objects || "none")}
    ${kv("styled", turn?.styled ? `${turn.styled.paradigm_id} / ${turn.styled.entry_id}` : "")}
    ${kv("教学共现", turn?.teaching_applied ? `召回候选 / ${turn.teaching_id}` : "none")}
    ${kv("feedback", feedback ? `${feedback.feedback_kind} / ${Number(feedback.correction_total_outcome || 0).toFixed(3)}` : "none")}
    ${kv("教学记录", teachTrace ? `纠正回答 "${teachTrace.response_text}" 已学习` : "none")}
    ${kv("tick 设置", `max=${runtime.max_ticks_if_no_commit || "-"} idle=${runtime.idle_ticks_after_commit || "-"}`)}
  `;
}

function renderMetrics() {
  const metrics = state.snapshot?.metrics || {};
  $("metricPhrase").textContent = metrics.phrase_records || 0;
  $("metricAssoc").textContent = metrics.association_pairs || 0;
  $("metricFeeling").textContent = metrics.unique_feeling_count || 0;
  $("metricFallback").textContent = metrics.fallback_count || 0;
  const count = state.workbenchTicks.length || Number(state.snapshot?.tick || 0);
  $("tickLabel").textContent = state.workbenchTicks.length
    ? `workbench tick ${state.workbenchTickIndex + 1}`
    : `tick ${state.snapshot?.tick || 0}`;
  $("tickSlider").max = String(Math.max(0, count - (state.workbenchTicks.length ? 1 : 0)));
  $("tickSlider").value = String(state.workbenchTicks.length ? state.workbenchTickIndex : state.snapshot?.tick || 0);
  $("frameCount").textContent = state.workbenchTicks.length
    ? `${state.workbenchTickIndex + 1} / ${state.workbenchTicks.length}`
    : `${state.snapshot?.tick || 0} / ${state.snapshot?.tick || 0}`;
}

// Phase 20.5a3 actual EOF override. Anything below this line is intentionally
// the browser-visible implementation.
const phase205a3 = {
  tick() {
    if (!state.workbenchTicks.length) return null;
    const index = Math.max(0, Math.min(state.workbenchTickIndex, state.workbenchTicks.length - 1));
    return state.workbenchTicks[index] || null;
  },
  draft(tick = phase205a3.tick()) {
    return (tick && (tick.draft_snapshot || tick.draft_changes)) || {};
  },
  metrics(tick = phase205a3.tick()) {
    const draft = phase205a3.draft(tick);
    return (tick && tick.audit_metrics) || draft.audit_metrics || {};
  },
};

function setWorkbenchTick(index) {
  if (!state.workbenchTicks.length) return;
  state.workbenchTickIndex = Math.max(0, Math.min(state.workbenchTicks.length - 1, Number(index || 0)));
  renderReplay();
  renderMetrics();
  renderChart();
  renderCloud();
  renderAudit();
  renderInner();
}

function stepWorkbenchTick(delta) {
  if (!state.workbenchTicks.length) return;
  setWorkbenchTick(state.workbenchTickIndex + delta);
}

function renderReplay() {
  const tick = phase205a3.tick();
  if (!tick) {
    $("tickButtons").innerHTML = "";
    $("replayDetail").innerHTML = `<div class="row-card"><b>等待本轮 turn</b><small>发送后显示每个 tick 的 AP loop 快照。</small></div>`;
    return;
  }
  const draft = phase205a3.draft(tick);
  const action = tick.action_chosen || {};
  const energy = tick.energy_RAPF || [];
  const labels = draft.object_labels || [];
  const recall = tick.recall_candidates || [];
  const competition = tick.action_competition || {};
  const grid = tick.draft_grid_snapshot || {};
  const thoughts = tick.thought_cloud_items || [];
  $("replayDetail").innerHTML = `
    <div class="draft-snapshot">
      <div><span>草稿框二维快照</span><b>${escapeHtml(draft.draft_buffer || draft.committed_text || "空")}</b></div>
      <div><span>本 tick 草稿动作</span><b>${escapeHtml(draft.draft_action_kind || "none")}${draft.typed_token ? ` · ${escapeHtml(draft.typed_token)}` : ""}</b></div>
    </div>
    ${kv("tick", `${tick.tick_index || ""} / runtime ${tick.runtime_tick || ""}`)}
    ${kv("循环帧", tick.stage || "")}
    ${kv("输入观察", `${draft.input_text_length || 0} 字 · ${draft.input_text_hash || "no-hash"}`)}
    ${kv("视觉对象", labels.length ? labels.join(" / ") : "none")}
    ${kv("共现召回", draft.teaching_candidate_applied ? `召回 ${draft.teaching_id || ""}` : "未召回教师共现候选")}
    ${kv("候选动作", action.action_id || "")}
    ${kv("能量 R/A/P/F", energy.map((item) => Number(item || 0).toFixed(3)).join(" / "))}
    ${kv("状态池 top", (tick.state_pool_top12 || []).slice(0, 6).map((item) => `${item.family}:${item.label}:${Number(item.attention_energy || 0).toFixed(2)}`).join("; ") || "none")}
    ${kv("边界", tick.boundary || state.workbenchRuntime?.boundary || "")}
  `;
  $("replayDetail").insertAdjacentHTML("beforeend", `
    <div class="runtime-extra">
      ${kv("RecallCandidate", recall.slice(0, 4).map((item) => `${item.source_kind}:${item.next_token || ""}:${Number(item.support || 0).toFixed(2)}`).join(" / ") || "none")}
      ${kv("ActionCompetition", `${competition.selected_outcome_kind || action.outcome_kind || ""} / rejected ${(competition.rejected_action_ids || []).length}`)}
      ${kv("DraftGrid", `${grid.visible_text || draft.draft_buffer || ""} @ ${grid.visible_text_hash || ""}`)}
      ${kv("ThoughtCloud", thoughts.slice(0, 5).map((item) => `${item.display_label || item.family}:${Number(item.energy || 0).toFixed(2)}`).join(" / ") || "none")}
    </div>
  `);
  $("tickButtons").innerHTML = state.workbenchTicks.map((item, index) => {
    const snap = item.draft_snapshot || item.draft_changes || {};
    const title = snap.draft_action_kind === "type_text"
      ? `${item.tick_index} 写 ${snap.typed_token || ""}`
      : `${item.tick_index} ${snap.draft_action_kind || item.title || ""}`;
    return `<button type="button" class="tick-jump ${index === state.workbenchTickIndex ? "active" : ""}" data-tick-index="${index}">${escapeHtml(title)}</button>`;
  }).join("");
  document.querySelectorAll("[data-tick-index]").forEach((button) => {
    button.addEventListener("click", () => setWorkbenchTick(button.dataset.tickIndex || 0));
  });
}

function renderMetrics() {
  const metrics = state.snapshot?.metrics || {};
  $("metricPhrase").textContent = metrics.phrase_records || 0;
  $("metricAssoc").textContent = metrics.association_pairs || 0;
  $("metricFeeling").textContent = metrics.unique_feeling_count || 0;
  $("metricFallback").textContent = metrics.fallback_count || 0;
  const count = state.workbenchTicks.length || Number(state.snapshot?.tick || 0);
  $("tickLabel").textContent = state.workbenchTicks.length ? `AP loop tick ${state.workbenchTickIndex + 1}` : `tick ${state.snapshot?.tick || 0}`;
  $("tickSlider").max = String(Math.max(0, count - (state.workbenchTicks.length ? 1 : 0)));
  $("tickSlider").value = String(state.workbenchTicks.length ? state.workbenchTickIndex : state.snapshot?.tick || 0);
  $("frameCount").textContent = state.workbenchTicks.length
    ? `${state.workbenchTickIndex + 1} / ${state.workbenchTicks.length}`
    : `${state.snapshot?.tick || 0} / ${state.snapshot?.tick || 0}`;
}

function renderChart() {
  const canvas = $("trendChart");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  const dpr = window.devicePixelRatio || 1;
  const rect = canvas.getBoundingClientRect();
  const width = Math.max(320, Math.floor(rect.width || 680));
  const height = 210;
  canvas.width = Math.floor(width * dpr);
  canvas.height = Math.floor(height * dpr);
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, width, height);
  ctx.fillStyle = "#fbfdff";
  ctx.fillRect(0, 0, width, height);
  drawGrid(ctx, width, height);
  const rows = state.workbenchTicks.length
    ? state.workbenchTicks.map((tick) => {
        const m = phase205a3.metrics(tick);
        return {
          real: Number((tick.energy_RAPF || [])[0] || m.mean_real_energy || 0),
          attention: Number((tick.energy_RAPF || [])[1] || m.mean_attention_energy || 0),
          pressure: Number((tick.energy_RAPF || [])[2] || m.mean_cognitive_pressure || 0),
          draft: Number(m.draft_length || 0),
        };
      })
    : (state.snapshot?.chart || []);
  drawSeries(ctx, rows, "real", "#0f766e", width, height);
  drawSeries(ctx, rows, "attention", "#245a8f", width, height);
  drawSeries(ctx, rows, "pressure", "#a33b35", width, height);
  drawSeries(ctx, rows, "draft", "#8a6d1f", width, height);
  drawLegendRows(ctx, [["real", "#0f766e"], ["attention", "#245a8f"], ["pressure", "#a33b35"], ["draft", "#8a6d1f"]]);
}

function renderCloud() {
  const tick = phase205a3.tick();
  const items = (tick?.state_pool_top12 || []).filter((item) => {
    const sig = item.channel_signature || [];
    return !(sig.includes("vision") || sig.includes("audio") || String(item.family || "").startsWith("visual"));
  });
  $("thoughtCloud").innerHTML = items.length
    ? `<div class="orb-field">${items.map((item, index) => {
        const real = Number(item.real_energy || 0);
        const virt = Number(item.virtual_energy || 0);
        const attention = Number(item.attention_energy || 0);
        const energy = Math.max(real, virt, attention);
        const bias = real - virt;
        const size = Math.round(42 + energy * 70);
        const radius = Math.max(4, 36 - energy * 32);
        const angle = index * 1.97 + (tick?.tick_index || 0) * 0.37;
        const x = 50 + Math.cos(angle) * radius;
        const y = 50 + Math.sin(angle) * radius;
        const hue = bias >= 0 ? 178 : 266;
        const sat = Math.round(38 + Math.abs(bias) * 48 + energy * 10);
        const alpha = (0.48 + energy * 0.42).toFixed(3);
        return `<div class="thought-orb" style="width:${size}px;height:${size}px;left:${x}%;top:${y}%;background:hsla(${hue},${sat}%,48%,${alpha});animation-delay:${(index * -0.23).toFixed(2)}s"><b>${escapeHtml(item.label || item.family || "SA")}</b><small>R ${real.toFixed(2)} / V ${virt.toFixed(2)}</small></div>`;
      }).join("")}</div>`
    : `<span class="chip">等待状态池</span>`;
}

function renderInner() {
  const tick = phase205a3.tick();
  const inner = tick?.inner_picture_state || {};
  const focus = inner.focus_xy || tick?.focus_xy || null;
  const layers = inner.layers || [];
  $("innerVision").innerHTML = `
    <div class="inner-composite" aria-label="state pool inner picture">
      <div class="inner-grid-bg"></div>
      ${layers.map((layer, index) => {
        const opacity = Number(layer.opacity || 0.2);
        const size = Math.round(48 + Number(layer.scale || 1) * 62);
        const hue = 170 + ((index * 37) % 90);
        return `<span class="inner-layer" style="left:${Number(layer.x || 50)}%;top:${Number(layer.y || 50)}%;width:${size}px;height:${size}px;opacity:${opacity};z-index:${20 - index};background:hsla(${hue},55%,48%,${Math.min(0.82, opacity)})">${escapeHtml(layer.label || "visual")}</span>`;
      }).join("")}
      ${focus ? `<span class="focus-marker" style="left:${Number(focus[0] || 50)}%;top:${Number(focus[1] || 50)}%"></span>` : ""}
      <div class="inner-caption">状态池重建 · tick ${escapeHtml(tick?.tick_index || "-")} · ${escapeHtml(inner.source || "state_pool_energy_reconstruction_not_original_asset")}</div>
    </div>
    <div class="object-bars">${layers.map((layer) => confidenceBar(layer.label, layer.energy, "state-energy")).join("") || `<small>本 tick 没有视觉 SA 能量可重建。</small>`}</div>
  `;
  const audioItems = (tick?.state_pool_top12 || []).filter((item) => (item.channel_signature || []).includes("audio"));
  $("innerAudio").innerHTML = `<div class="audio-sketch"><b>内心音频</b>${audioItems.length ? `<div class="audio-bars">${audioItems.slice(0, 12).map((item, index) => `<span style="height:${Math.round(18 + Number(item.attention_energy || item.real_energy || 0) * 74)}px" title="${escapeHtml(item.label || index)}"></span>`).join("")}</div>` : `<small>听觉感受器尚未启用；这里不把 TTS 冒充 inner voice。</small>`}</div>`;
}

function renderAudit() {
  const ticks = state.workbenchTicks || [];
  if (!ticks.length) {
    $("auditPanel").innerHTML = `<div class="row-card"><b>等待 tick trace</b><small>发送后显示运行时间、分过程耗时、状态池规模和能量变化。</small></div>`;
    return;
  }
  const specs = [
    ["runtime_ms", "本轮运行 ms"],
    ["feedback_ms", "反馈处理 ms", "process_timing_ms.feedback_ms"],
    ["visual_ms", "视觉处理 ms", "process_timing_ms.visual_ms"],
    ["text_runtime_ms", "文本运行 ms", "process_timing_ms.text_runtime_ms"],
    ["recall_ms", "共现召回 ms", "process_timing_ms.recall_ms"],
    ["style_ms", "风格选择 ms", "process_timing_ms.style_ms"],
    ["draft_assembly_ms", "草稿组装 ms", "process_timing_ms.draft_assembly_ms"],
    ["state_pool_count", "状态池对象数"],
    ["visual_state_count", "视觉 SA 数"],
    ["text_state_count", "文本 SA 数"],
    ["memory_state_count", "记忆 SA 数"],
    ["object_file_count", "ObjectFile 数"],
    ["draft_length", "草稿长度"],
    ["mean_real_energy", "平均实能量"],
    ["mean_attention_energy", "平均注意能量"],
    ["mean_cognitive_pressure", "认知压力"],
    ["mean_fatigue", "疲劳"],
  ];
  $("auditPanel").innerHTML = `<div class="row-card"><b>AP runtime 审计</b><small>所有曲线来自当前 turn 的 RuntimeTickEvent；分过程耗时是后端本轮实际计时，不是前端动画。</small></div><div class="audit-grid">${specs.map(([key, label, path]) => renderMiniChart(label, ticks.map((tick) => metricValue(tick, key, path)))).join("")}</div>`;
}

function metricValue(tick, key, path) {
  const metrics = phase205a3.metrics(tick);
  if (path) return Number(path.split(".").reduce((obj, part) => (obj && obj[part] !== undefined ? obj[part] : undefined), metrics) || 0);
  if (key === "runtime_ms") return Number(metrics.runtime_ms || 0);
  return Number(metrics[key] || 0);
}

function renderMiniChart(label, values) {
  const max = Math.max(1, ...values.map((v) => Number(v || 0)));
  const points = values.map((value, index) => {
    const x = values.length <= 1 ? 4 : 4 + (index / (values.length - 1)) * 92;
    const y = 30 - (Number(value || 0) / max) * 24;
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  }).join(" ");
  const latest = values.length ? values[values.length - 1] : 0;
  return `<div class="mini-chart"><span>${escapeHtml(label)}</span><svg viewBox="0 0 100 34" preserveAspectRatio="none"><polyline points="${points}" /></svg><b>${Number(latest || 0).toFixed(latest > 10 ? 1 : 3)}</b></div>`;
}

// Phase 20.5a3 EOF override: keep this final block after all legacy repair
// functions so the browser renders RuntimeTickEvent/state-pool data, not the
// older projection panels.
function currentWorkbenchTick() {
  if (!state.workbenchTicks.length) return null;
  const index = Math.max(0, Math.min(state.workbenchTickIndex, state.workbenchTicks.length - 1));
  return state.workbenchTicks[index] || null;
}

function currentDraft(tick = currentWorkbenchTick()) {
  return (tick && (tick.draft_snapshot || tick.draft_changes)) || {};
}

function currentAuditMetrics(tick = currentWorkbenchTick()) {
  const draft = currentDraft(tick);
  return (tick && tick.audit_metrics) || draft.audit_metrics || {};
}

function setWorkbenchTick(index) {
  if (!state.workbenchTicks.length) return;
  state.workbenchTickIndex = Math.max(0, Math.min(state.workbenchTicks.length - 1, Number(index || 0)));
  renderReplay();
  renderMetrics();
  renderChart();
  renderCloud();
  renderAudit();
  renderInner();
}

function renderReplay() {
  const tick = currentWorkbenchTick();
  if (!tick) {
    $("tickButtons").innerHTML = "";
    $("replayDetail").innerHTML = `<div class="row-card"><b>等待本轮 turn</b><small>发送后显示每个 tick 的 AP loop 快照。</small></div>`;
    return;
  }
  const draft = currentDraft(tick);
  const action = tick.action_chosen || {};
  const energy = tick.energy_RAPF || [];
  const labels = draft.object_labels || [];
  $("replayDetail").innerHTML = `
    <div class="draft-snapshot">
      <div>
        <span>草稿框二维快照</span>
        <b>${escapeHtml(draft.draft_buffer || draft.committed_text || "空")}</b>
      </div>
      <div>
        <span>本 tick 草稿动作</span>
        <b>${escapeHtml(draft.draft_action_kind || "none")}${draft.typed_token ? ` · ${escapeHtml(draft.typed_token)}` : ""}</b>
      </div>
    </div>
    ${kv("tick", `${tick.tick_index || ""} / runtime ${tick.runtime_tick || ""}`)}
    ${kv("循环帧", tick.stage || "")}
    ${kv("输入观察", `${draft.input_text_length || 0} 字 · ${draft.input_text_hash || "no-hash"}`)}
    ${kv("视觉对象", labels.length ? labels.join(" / ") : "none")}
    ${kv("共现召回", draft.teaching_candidate_applied ? `召回 ${draft.teaching_id || ""}` : "未召回教师共现候选")}
    ${kv("候选动作", action.action_id || "")}
    ${kv("能量 R/A/P/F", energy.map((item) => Number(item || 0).toFixed(3)).join(" / "))}
    ${kv("状态池 top", (tick.state_pool_top12 || []).slice(0, 6).map((item) => `${item.family}:${item.label}:${Number(item.attention_energy || 0).toFixed(2)}`).join("; ") || "none")}
    ${kv("边界", tick.boundary || state.workbenchRuntime?.boundary || "")}
  `;
  $("tickButtons").innerHTML = state.workbenchTicks.map((item, index) => {
    const snap = item.draft_snapshot || item.draft_changes || {};
    const title = snap.draft_action_kind === "type_text"
      ? `${item.tick_index} 写 ${snap.typed_token || ""}`
      : `${item.tick_index} ${snap.draft_action_kind || item.title || ""}`;
    return `<button type="button" class="tick-jump ${index === state.workbenchTickIndex ? "active" : ""}" data-tick-index="${index}">${escapeHtml(title)}</button>`;
  }).join("");
  document.querySelectorAll("[data-tick-index]").forEach((button) => {
    button.addEventListener("click", () => setWorkbenchTick(button.dataset.tickIndex || 0));
  });
}

function stepWorkbenchTick(delta) {
  if (!state.workbenchTicks.length) return;
  setWorkbenchTick(state.workbenchTickIndex + delta);
}

function renderChart() {
  const canvas = $("trendChart");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  const dpr = window.devicePixelRatio || 1;
  const rect = canvas.getBoundingClientRect();
  const width = Math.max(320, Math.floor(rect.width || 680));
  const height = 210;
  canvas.width = Math.floor(width * dpr);
  canvas.height = Math.floor(height * dpr);
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, width, height);
  ctx.fillStyle = "#fbfdff";
  ctx.fillRect(0, 0, width, height);
  drawGrid(ctx, width, height);
  const rows = state.workbenchTicks.length
    ? state.workbenchTicks.map((tick) => {
        const m = currentAuditMetrics(tick);
        return {
          tick: tick.tick_index,
          real: Number((tick.energy_RAPF || [])[0] || m.mean_real_energy || 0),
          attention: Number((tick.energy_RAPF || [])[1] || m.mean_attention_energy || 0),
          pressure: Number((tick.energy_RAPF || [])[2] || m.mean_cognitive_pressure || 0),
          draft: Number(m.draft_length || 0),
        };
      })
    : (state.snapshot?.chart || []).map((row) => ({
        tick: row.tick,
        real: Number(row.learned_total || 0),
        attention: Number(row.candidate_count || 0),
        pressure: Number(row.fallback_total || 0),
        draft: Number(row.learned_total || 0),
      }));
  drawSeries(ctx, rows, "real", "#0f766e", width, height);
  drawSeries(ctx, rows, "attention", "#245a8f", width, height);
  drawSeries(ctx, rows, "pressure", "#a33b35", width, height);
  drawSeries(ctx, rows, "draft", "#8a6d1f", width, height);
  drawLegendRows(ctx, [
    ["real", "#0f766e"],
    ["attention", "#245a8f"],
    ["pressure", "#a33b35"],
    ["draft", "#8a6d1f"],
  ]);
}

function drawSeries(ctx, rows, key, color, w, h) {
  if (!rows.length) return;
  const values = rows.map((row) => Number(row[key] || 0));
  const max = Math.max(1, ...values);
  const left = 32;
  const right = w - 14;
  const top = 24;
  const bottom = h - 24;
  ctx.strokeStyle = color;
  ctx.lineWidth = 2;
  ctx.beginPath();
  rows.forEach((row, index) => {
    const x = left + (index / Math.max(1, rows.length - 1)) * (right - left);
    const y = bottom - (Number(row[key] || 0) / max) * (bottom - top);
    if (index === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.stroke();
}

function drawLegendRows(ctx, rows) {
  rows.forEach((row, index) => {
    const x = 38 + index * 104;
    ctx.fillStyle = row[1];
    ctx.fillRect(x, 10, 10, 10);
    ctx.fillStyle = "#63727a";
    ctx.font = "12px Microsoft YaHei, Arial";
    ctx.fillText(row[0], x + 16, 19);
  });
}

function renderCloud() {
  const tick = currentWorkbenchTick();
  const items = (tick?.state_pool_top12 || []).filter((item) => {
    const sig = item.channel_signature || [];
    return !(sig.includes("vision") || sig.includes("audio") || String(item.family || "").startsWith("visual"));
  });
  if (!items.length) {
    $("thoughtCloud").innerHTML = `<span class="chip">等待状态池</span>`;
    return;
  }
  $("thoughtCloud").innerHTML = `<div class="orb-field">${items.map(renderThoughtOrb).join("")}</div>`;
}

function renderThoughtOrb(item, index) {
  const real = Number(item.real_energy || 0);
  const virt = Number(item.virtual_energy || 0);
  const attention = Number(item.attention_energy || 0);
  const energy = Math.max(real, virt, attention);
  const bias = real - virt;
  const size = Math.round(42 + energy * 70);
  const radius = Math.max(4, 36 - energy * 32);
  const angle = index * 1.97 + (currentWorkbenchTick()?.tick_index || 0) * 0.37;
  const x = 50 + Math.cos(angle) * radius;
  const y = 50 + Math.sin(angle) * radius;
  const hue = bias >= 0 ? 178 : 266;
  const sat = Math.round(38 + Math.abs(bias) * 48 + energy * 10);
  const alpha = (0.48 + energy * 0.42).toFixed(3);
  return `
    <div class="thought-orb" style="width:${size}px;height:${size}px;left:${x}%;top:${y}%;background:hsla(${hue},${sat}%,48%,${alpha});animation-delay:${(index * -0.23).toFixed(2)}s">
      <b>${escapeHtml(item.label || item.family || "SA")}</b>
      <small>R ${real.toFixed(2)} / V ${virt.toFixed(2)}</small>
    </div>
  `;
}

function renderInner() {
  const tick = currentWorkbenchTick();
  const inner = tick?.inner_picture_state || {};
  const focus = inner.focus_xy || tick?.focus_xy || null;
  const layers = inner.layers || [];
  $("innerVision").innerHTML = `
    <div class="inner-composite" aria-label="state pool inner picture">
      <div class="inner-grid-bg"></div>
      ${layers.map(renderInnerLayer).join("")}
      ${focus ? `<span class="focus-marker" style="left:${Number(focus[0] || 50)}%;top:${Number(focus[1] || 50)}%"></span>` : ""}
      <div class="inner-caption">状态池重建 · tick ${escapeHtml(tick?.tick_index || "-")} · ${escapeHtml(inner.source || "state_pool_energy_reconstruction_not_original_asset")}</div>
    </div>
    <div class="object-bars">
      ${layers.map((layer) => confidenceBar(layer.label, layer.energy, "state-energy")).join("") || `<small>本 tick 没有视觉 SA 能量可重建。</small>`}
    </div>
  `;
  const audioItems = (tick?.state_pool_top12 || []).filter((item) => (item.channel_signature || []).includes("audio"));
  $("innerAudio").innerHTML = `
    <div class="audio-sketch">
      <b>内心音频</b>
      ${audioItems.length ? renderAudioBars(audioItems) : `<small>听觉感受器尚未启用；这里不把 TTS 冒充 inner voice。</small>`}
    </div>
  `;
}

function renderInnerLayer(layer, index) {
  const opacity = Number(layer.opacity || 0.2);
  const size = Math.round(48 + Number(layer.scale || 1) * 62);
  const hue = 170 + ((index * 37) % 90);
  return `
    <span class="inner-layer" style="left:${Number(layer.x || 50)}%;top:${Number(layer.y || 50)}%;width:${size}px;height:${size}px;opacity:${opacity};z-index:${20 - index};background:hsla(${hue},55%,48%,${Math.min(0.82, opacity)})">
      ${escapeHtml(layer.label || "visual")}
    </span>
  `;
}

function renderAudioBars(items) {
  return `<div class="audio-bars">${items.slice(0, 12).map((item, index) => {
    const h = Math.round(18 + Number(item.attention_energy || item.real_energy || 0) * 74);
    return `<span style="height:${h}px" title="${escapeHtml(item.label || index)}"></span>`;
  }).join("")}</div>`;
}

function renderAudit() {
  const ticks = state.workbenchTicks || [];
  if (!ticks.length) {
    $("auditPanel").innerHTML = `<div class="row-card"><b>等待 tick trace</b><small>发送后显示运行时间、分过程耗时、状态池规模和能量变化。</small></div>`;
    return;
  }
  const specs = [
    ["runtime_ms", "本轮运行 ms"],
    ["feedback_ms", "反馈处理 ms", "process_timing_ms.feedback_ms"],
    ["visual_ms", "视觉处理 ms", "process_timing_ms.visual_ms"],
    ["text_runtime_ms", "文本运行 ms", "process_timing_ms.text_runtime_ms"],
    ["recall_ms", "共现召回 ms", "process_timing_ms.recall_ms"],
    ["style_ms", "风格选择 ms", "process_timing_ms.style_ms"],
    ["draft_assembly_ms", "草稿组装 ms", "process_timing_ms.draft_assembly_ms"],
    ["state_pool_count", "状态池对象数"],
    ["visual_state_count", "视觉 SA 数"],
    ["text_state_count", "文本 SA 数"],
    ["memory_state_count", "记忆 SA 数"],
    ["object_file_count", "ObjectFile 数"],
    ["draft_length", "草稿长度"],
    ["mean_real_energy", "平均实能量"],
    ["mean_attention_energy", "平均注意能量"],
    ["mean_cognitive_pressure", "认知压力"],
    ["mean_fatigue", "疲劳"],
  ];
  $("auditPanel").innerHTML = `
    <div class="row-card"><b>AP runtime 审计</b><small>所有曲线来自当前 turn 的 RuntimeTickEvent；分过程耗时是后端本轮实际计时，不是前端动画。</small></div>
    <div class="audit-grid">${specs.map(([key, label, path]) => renderMiniChart(label, ticks.map((tick) => metricValue(tick, key, path)))).join("")}</div>
  `;
}

function metricValue(tick, key, path) {
  const metrics = currentAuditMetrics(tick);
  if (path) {
    return Number(path.split(".").reduce((obj, part) => (obj && obj[part] !== undefined ? obj[part] : undefined), metrics) || 0);
  }
  if (key === "runtime_ms") return Number(metrics.runtime_ms || 0);
  return Number(metrics[key] || 0);
}

function renderMiniChart(label, values) {
  const max = Math.max(1, ...values.map((v) => Number(v || 0)));
  const points = values.map((value, index) => {
    const x = values.length <= 1 ? 4 : 4 + (index / (values.length - 1)) * 92;
    const y = 30 - (Number(value || 0) / max) * 24;
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  }).join(" ");
  const latest = values.length ? values[values.length - 1] : 0;
  return `
    <div class="mini-chart">
      <span>${escapeHtml(label)}</span>
      <svg viewBox="0 0 100 34" preserveAspectRatio="none">
        <polyline points="${points}" />
      </svg>
      <b>${Number(latest || 0).toFixed(latest > 10 ? 1 : 3)}</b>
    </div>
  `;
}

function renderMemory() {
  if (!$("memoryPackages")) return;
  const view = state.memoryView || {};
  const packages = view.packages || [];
  const memories = view.memories || [];
  $("memoryScopeLine").textContent = state.selectedPackageId
    ? `正在查看记忆包 ${state.selectedPackageId}`
    : `显示本地完整记忆 ${view.total_memories ?? memories.length} 条`;
  $("memoryPackages").innerHTML = packages.length ? packages.map((pkg) => `
    <div class="row-card memory-package ${pkg.status === "uninstalled" ? "muted-package" : ""}">
      <b>${escapeHtml(pkg.name || pkg.package_id)}</b>
      <small>${escapeHtml(pkg.package_id)} · ${escapeHtml(pkg.status || "active")} · 新增 ${escapeHtml(pkg.added_count || 0)} · 去重 ${escapeHtml(pkg.dedup_count || 0)}</small>
      <div class="memory-actions">
        <button type="button" data-memory-view-package="${escapeHtml(pkg.package_id)}">查看内容</button>
        <button type="button" data-memory-uninstall-package="${escapeHtml(pkg.package_id)}">卸载</button>
      </div>
    </div>
  `).join("") : `<div class="row-card"><b>暂无导入包</b><small>导入后会实时显示名称、内容和卸载入口。</small></div>`;
  $("memoryList").innerHTML = memories.length ? memories.map((item) => `
    <label class="row-card memory-row">
      <input type="checkbox" class="memory-check" value="${escapeHtml(item.memory_id)}">
      <span>
        <b>${escapeHtml(item.display_title || item.text || "未命名记忆")}</b>
        <small>${escapeHtml(item.kind_label || item.kind)} · ${escapeHtml(stripRawIds(item.display_detail || ""))}</small>
      </span>
    </label>
  `).join("") : `<div class="row-card"><b>暂无匹配记忆</b><small>换个关键词或刷新。</small></div>`;
  document.querySelectorAll("[data-memory-view-package]").forEach((button) => {
    button.addEventListener("click", () => refreshMemoryView(button.dataset.memoryViewPackage || ""));
  });
  document.querySelectorAll("[data-memory-uninstall-package]").forEach((button) => {
    button.addEventListener("click", () => uninstallMemoryPackage(button.dataset.memoryUninstallPackage || ""));
  });
  renderPackageMirror();
}

function inputLabel(row) {
  if (!row) return "";
  if (row.user_text) return row.user_text;
  const count = Number(row.incoming_query_count || 0);
  const length = Number(row.user_text_length || row.incoming_query_total_length || 0);
  if (count <= 0 && length <= 0) return "(feedback)";
  const hash = String(row.user_text_hash || row.incoming_query_hash || "");
  const shortHash = hash ? hash.slice(0, 16) : "no-hash";
  return `历史输入摘要 · ${length} 字 · ${shortHash}`;
}

// Phase 20.5a3 final workbench repair. These definitions intentionally come
// last so the UI reads the real RuntimeTickEvent fields instead of older
// projection-era panels.
function currentWorkbenchTick() {
  if (!state.workbenchTicks.length) return null;
  const index = Math.max(0, Math.min(state.workbenchTickIndex, state.workbenchTicks.length - 1));
  return state.workbenchTicks[index] || null;
}

function currentDraft(tick = currentWorkbenchTick()) {
  return (tick && (tick.draft_snapshot || tick.draft_changes)) || {};
}

function currentAuditMetrics(tick = currentWorkbenchTick()) {
  const draft = currentDraft(tick);
  return (tick && tick.audit_metrics) || draft.audit_metrics || {};
}

function setWorkbenchTick(index) {
  state.workbenchTickIndex = Math.max(0, Math.min(state.workbenchTicks.length - 1, Number(index || 0)));
  renderReplay();
  renderMetrics();
  renderChart();
  renderCloud();
  renderAudit();
  renderInner();
}

function renderReplay() {
  const tick = currentWorkbenchTick();
  if (!tick) {
    $("tickButtons").innerHTML = "";
    $("replayDetail").innerHTML = `<div class="row-card"><b>等待本轮 turn</b><small>发送后显示每个 tick 的 AP loop 快照。</small></div>`;
    return;
  }
  const draft = currentDraft(tick);
  const action = tick.action_chosen || {};
  const energy = tick.energy_RAPF || [];
  const labels = draft.object_labels || [];
  $("replayDetail").innerHTML = `
    <div class="draft-snapshot">
      <div>
        <span>草稿框二维快照</span>
        <b>${escapeHtml(draft.draft_buffer || draft.committed_text || "空")}</b>
      </div>
      <div>
        <span>本 tick 草稿动作</span>
        <b>${escapeHtml(draft.draft_action_kind || "none")}${draft.typed_token ? ` · ${escapeHtml(draft.typed_token)}` : ""}</b>
      </div>
    </div>
    ${kv("tick", `${tick.tick_index || ""} / runtime ${tick.runtime_tick || ""}`)}
    ${kv("循环帧", tick.stage || "")}
    ${kv("输入观察", `${draft.input_text_length || 0} 字 · ${draft.input_text_hash || "no-hash"}`)}
    ${kv("视觉对象", labels.length ? labels.join(" / ") : "none")}
    ${kv("共现召回", draft.teaching_candidate_applied ? `召回 ${draft.teaching_id || ""}` : "未召回教师共现候选")}
    ${kv("候选动作", action.action_id || "")}
    ${kv("能量 R/A/P/F", energy.map((item) => Number(item || 0).toFixed(3)).join(" / "))}
    ${kv("状态池 top", (tick.state_pool_top12 || []).slice(0, 6).map((item) => `${item.family}:${item.label}:${Number(item.attention_energy || 0).toFixed(2)}`).join("; ") || "none")}
    ${kv("边界", tick.boundary || state.workbenchRuntime?.boundary || "")}
  `;
  $("tickButtons").innerHTML = state.workbenchTicks.map((item, index) => {
    const snap = item.draft_snapshot || item.draft_changes || {};
    const title = snap.draft_action_kind === "type_text"
      ? `${item.tick_index} 写 ${snap.typed_token || ""}`
      : `${item.tick_index} ${snap.draft_action_kind || item.title || ""}`;
    return `<button type="button" class="tick-jump ${index === state.workbenchTickIndex ? "active" : ""}" data-tick-index="${index}">${escapeHtml(title)}</button>`;
  }).join("");
  document.querySelectorAll("[data-tick-index]").forEach((button) => {
    button.addEventListener("click", () => setWorkbenchTick(button.dataset.tickIndex || 0));
  });
}

function stepWorkbenchTick(delta) {
  if (!state.workbenchTicks.length) return;
  setWorkbenchTick(state.workbenchTickIndex + delta);
}

function renderChart() {
  const canvas = $("trendChart");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  const dpr = window.devicePixelRatio || 1;
  const rect = canvas.getBoundingClientRect();
  const width = Math.max(320, Math.floor(rect.width || 680));
  const height = 210;
  canvas.width = Math.floor(width * dpr);
  canvas.height = Math.floor(height * dpr);
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, width, height);
  ctx.fillStyle = "#fbfdff";
  ctx.fillRect(0, 0, width, height);
  drawGrid(ctx, width, height);
  const rows = state.workbenchTicks.length
    ? state.workbenchTicks.map((tick) => {
        const m = currentAuditMetrics(tick);
        return {
          tick: tick.tick_index,
          real: Number((tick.energy_RAPF || [])[0] || m.mean_real_energy || 0),
          attention: Number((tick.energy_RAPF || [])[1] || m.mean_attention_energy || 0),
          pressure: Number((tick.energy_RAPF || [])[2] || m.mean_cognitive_pressure || 0),
          draft: Number(m.draft_length || 0),
        };
      })
    : (state.snapshot?.chart || []).map((row) => ({
        tick: row.tick,
        real: Number(row.learned_total || 0),
        attention: Number(row.candidate_count || 0),
        pressure: Number(row.fallback_total || 0),
        draft: Number(row.learned_total || 0),
      }));
  drawSeries(ctx, rows, "real", "#0f766e", width, height);
  drawSeries(ctx, rows, "attention", "#245a8f", width, height);
  drawSeries(ctx, rows, "pressure", "#a33b35", width, height);
  drawSeries(ctx, rows, "draft", "#8a6d1f", width, height);
  drawLegendRows(ctx, [
    ["real", "#0f766e"],
    ["attention", "#245a8f"],
    ["pressure", "#a33b35"],
    ["draft", "#8a6d1f"],
  ]);
}

function drawSeries(ctx, rows, key, color, w, h) {
  if (!rows.length) return;
  const values = rows.map((row) => Number(row[key] || 0));
  const max = Math.max(1, ...values);
  const left = 32;
  const right = w - 14;
  const top = 24;
  const bottom = h - 24;
  ctx.strokeStyle = color;
  ctx.lineWidth = 2;
  ctx.beginPath();
  rows.forEach((row, index) => {
    const x = left + (index / Math.max(1, rows.length - 1)) * (right - left);
    const y = bottom - (Number(row[key] || 0) / max) * (bottom - top);
    if (index === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.stroke();
}

function drawLegendRows(ctx, rows) {
  rows.forEach((row, index) => {
    const x = 38 + index * 104;
    ctx.fillStyle = row[1];
    ctx.fillRect(x, 10, 10, 10);
    ctx.fillStyle = "#63727a";
    ctx.font = "12px Microsoft YaHei, Arial";
    ctx.fillText(row[0], x + 16, 19);
  });
}

function renderCloud() {
  const tick = currentWorkbenchTick();
  const items = (tick?.state_pool_top12 || []).filter((item) => {
    const sig = item.channel_signature || [];
    return !(sig.includes("vision") || sig.includes("audio") || String(item.family || "").startsWith("visual"));
  });
  if (!items.length) {
    $("thoughtCloud").innerHTML = `<span class="chip">等待状态池</span>`;
    return;
  }
  $("thoughtCloud").innerHTML = `<div class="orb-field">${items.map(renderThoughtOrb).join("")}</div>`;
}

function renderThoughtOrb(item, index) {
  const real = Number(item.real_energy || 0);
  const virt = Number(item.virtual_energy || 0);
  const attention = Number(item.attention_energy || 0);
  const energy = Math.max(real, virt, attention);
  const bias = real - virt;
  const size = Math.round(42 + energy * 70);
  const radius = Math.max(4, 36 - energy * 32);
  const angle = index * 1.97 + (currentWorkbenchTick()?.tick_index || 0) * 0.37;
  const x = 50 + Math.cos(angle) * radius;
  const y = 50 + Math.sin(angle) * radius;
  const hue = bias >= 0 ? 178 : 266;
  const sat = Math.round(38 + Math.abs(bias) * 48 + energy * 10);
  const alpha = (0.48 + energy * 0.42).toFixed(3);
  return `
    <div class="thought-orb" style="width:${size}px;height:${size}px;left:${x}%;top:${y}%;background:hsla(${hue},${sat}%,48%,${alpha});animation-delay:${(index * -0.23).toFixed(2)}s">
      <b>${escapeHtml(item.label || item.family || "SA")}</b>
      <small>R ${real.toFixed(2)} / V ${virt.toFixed(2)}</small>
    </div>
  `;
}

function renderInner() {
  const tick = currentWorkbenchTick();
  const inner = tick?.inner_picture_state || {};
  const focus = inner.focus_xy || tick?.focus_xy || null;
  const layers = inner.layers || [];
  $("innerVision").innerHTML = `
    <div class="inner-composite" aria-label="state pool inner picture">
      <div class="inner-grid-bg"></div>
      ${layers.map(renderInnerLayer).join("")}
      ${focus ? `<span class="focus-marker" style="left:${Number(focus[0] || 50)}%;top:${Number(focus[1] || 50)}%"></span>` : ""}
      <div class="inner-caption">状态池重建 · tick ${escapeHtml(tick?.tick_index || "-")} · ${escapeHtml(inner.source || "no visual state")}</div>
    </div>
    <div class="object-bars">
      ${layers.map((layer) => confidenceBar(layer.label, layer.energy, "state-energy")).join("") || `<small>本 tick 没有视觉 SA 能量可重建。</small>`}
    </div>
  `;
  const audioItems = (tick?.state_pool_top12 || []).filter((item) => (item.channel_signature || []).includes("audio"));
  $("innerAudio").innerHTML = `
    <div class="audio-sketch">
      <b>内心音频</b>
      ${audioItems.length ? renderAudioBars(audioItems) : `<small>听觉感受器尚未启用；这里不把 TTS 冒充 inner voice。</small>`}
    </div>
  `;
}

function renderInnerLayer(layer, index) {
  const opacity = Number(layer.opacity || 0.2);
  const size = Math.round(48 + Number(layer.scale || 1) * 62);
  const hue = 170 + ((index * 37) % 90);
  return `
    <span class="inner-layer" style="left:${Number(layer.x || 50)}%;top:${Number(layer.y || 50)}%;width:${size}px;height:${size}px;opacity:${opacity};z-index:${20 - index};background:hsla(${hue},55%,48%,${Math.min(0.82, opacity)})">
      ${escapeHtml(layer.label || "visual")}
    </span>
  `;
}

function renderAudioBars(items) {
  return `<div class="audio-bars">${items.slice(0, 12).map((item, index) => {
    const h = Math.round(18 + Number(item.attention_energy || item.real_energy || 0) * 74);
    return `<span style="height:${h}px" title="${escapeHtml(item.label || index)}"></span>`;
  }).join("")}</div>`;
}

function renderAudit() {
  const ticks = state.workbenchTicks || [];
  if (!ticks.length) {
    $("auditPanel").innerHTML = `<div class="row-card"><b>等待 tick trace</b><small>发送后显示运行时间、分过程耗时、状态池规模和能量变化。</small></div>`;
    return;
  }
  const specs = [
    ["runtime_ms", "本轮运行 ms"],
    ["feedback_ms", "反馈处理 ms", "process_timing_ms.feedback_ms"],
    ["visual_ms", "视觉处理 ms", "process_timing_ms.visual_ms"],
    ["text_runtime_ms", "文本运行 ms", "process_timing_ms.text_runtime_ms"],
    ["recall_ms", "共现召回 ms", "process_timing_ms.recall_ms"],
    ["style_ms", "风格选择 ms", "process_timing_ms.style_ms"],
    ["draft_assembly_ms", "草稿组装 ms", "process_timing_ms.draft_assembly_ms"],
    ["state_pool_count", "状态池对象数"],
    ["visual_state_count", "视觉 SA 数"],
    ["text_state_count", "文本 SA 数"],
    ["memory_state_count", "记忆 SA 数"],
    ["object_file_count", "ObjectFile 数"],
    ["draft_length", "草稿长度"],
    ["mean_real_energy", "平均实能量"],
    ["mean_attention_energy", "平均注意能量"],
    ["mean_cognitive_pressure", "认知压力"],
    ["mean_fatigue", "疲劳"],
  ];
  $("auditPanel").innerHTML = `
    <div class="row-card"><b>AP runtime 审计</b><small>所有曲线来自当前 turn 的 RuntimeTickEvent；分过程耗时是后端本轮实际计时，不是前端动画。</small></div>
    <div class="audit-grid">${specs.map(([key, label, path]) => renderMiniChart(label, ticks.map((tick) => metricValue(tick, key, path)))).join("")}</div>
  `;
}

function metricValue(tick, key, path) {
  const metrics = currentAuditMetrics(tick);
  if (path) {
    return Number(path.split(".").reduce((obj, part) => (obj && obj[part] !== undefined ? obj[part] : undefined), metrics) || 0);
  }
  if (key === "runtime_ms") return Number(metrics.runtime_ms || 0);
  return Number(metrics[key] || 0);
}

function renderMiniChart(label, values) {
  const max = Math.max(1, ...values.map((v) => Number(v || 0)));
  const points = values.map((value, index) => {
    const x = values.length <= 1 ? 4 : 4 + (index / (values.length - 1)) * 92;
    const y = 30 - (Number(value || 0) / max) * 24;
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  }).join(" ");
  const latest = values.length ? values[values.length - 1] : 0;
  return `
    <div class="mini-chart">
      <span>${escapeHtml(label)}</span>
      <svg viewBox="0 0 100 34" preserveAspectRatio="none">
        <polyline points="${points}" />
      </svg>
      <b>${Number(latest || 0).toFixed(latest > 10 ? 1 : 3)}</b>
    </div>
  `;
}

function renderMemory() {
  if (!$("memoryPackages")) return;
  const view = state.memoryView || {};
  const packages = view.packages || [];
  const memories = view.memories || [];
  $("memoryScopeLine").textContent = state.selectedPackageId
    ? `正在查看记忆包 ${state.selectedPackageId}`
    : `显示本地完整记忆 ${view.total_memories ?? memories.length} 条`;
  $("memoryPackages").innerHTML = packages.length ? packages.map((pkg) => `
    <div class="row-card memory-package ${pkg.status === "uninstalled" ? "muted-package" : ""}">
      <b>${escapeHtml(pkg.name || pkg.package_id)}</b>
      <small>${escapeHtml(pkg.package_id)} · ${escapeHtml(pkg.status || "active")} · 新增 ${escapeHtml(pkg.added_count || 0)} · 去重 ${escapeHtml(pkg.dedup_count || 0)}</small>
      <div class="memory-actions">
        <button type="button" data-memory-view-package="${escapeHtml(pkg.package_id)}">查看内容</button>
        <button type="button" data-memory-uninstall-package="${escapeHtml(pkg.package_id)}">卸载</button>
      </div>
    </div>
  `).join("") : `<div class="row-card"><b>暂无导入包</b><small>导入后会实时显示名称、内容和卸载入口。</small></div>`;
  $("memoryList").innerHTML = memories.length ? memories.map((item) => `
    <label class="row-card memory-row">
      <input type="checkbox" class="memory-check" value="${escapeHtml(item.memory_id)}">
      <span>
        <b>${escapeHtml(item.display_title || item.text || "未命名记忆")}</b>
        <small>${escapeHtml(item.kind_label || item.kind)} · ${escapeHtml(stripRawIds(item.display_detail || ""))}</small>
      </span>
    </label>
  `).join("") : `<div class="row-card"><b>暂无匹配记忆</b><small>换个关键词或刷新。</small></div>`;
  document.querySelectorAll("[data-memory-view-package]").forEach((button) => {
    button.addEventListener("click", () => refreshMemoryView(button.dataset.memoryViewPackage || ""));
  });
  document.querySelectorAll("[data-memory-uninstall-package]").forEach((button) => {
    button.addEventListener("click", () => uninstallMemoryPackage(button.dataset.memoryUninstallPackage || ""));
  });
  renderPackageMirror();
}

function inputLabel(row) {
  if (!row) return "";
  if (row.user_text) return row.user_text;
  const count = Number(row.incoming_query_count || 0);
  const length = Number(row.user_text_length || row.incoming_query_total_length || 0);
  if (count <= 0 && length <= 0) return "(feedback)";
  const hash = String(row.user_text_hash || row.incoming_query_hash || "");
  const shortHash = hash ? hash.slice(0, 16) : "no-hash";
  return `历史输入摘要 · ${length} 字 · ${shortHash}`;
}

function renderChart() {
  const canvas = $("trendChart");
  const ctx = canvas.getContext("2d");
  const dpr = window.devicePixelRatio || 1;
  const rect = canvas.getBoundingClientRect();
  canvas.width = Math.max(320, Math.floor(rect.width * dpr));
  canvas.height = Math.floor(210 * dpr);
  ctx.scale(dpr, dpr);
  const w = rect.width;
  const h = 210;
  ctx.clearRect(0, 0, w, h);
  ctx.fillStyle = "#fbfdff";
  ctx.fillRect(0, 0, w, h);
  const rows = state.snapshot?.chart || [];
  drawGrid(ctx, w, h);
  drawLine(ctx, rows, "learned_total", "#0f766e", w, h);
  drawLine(ctx, rows, "fallback_total", "#a33b35", w, h);
  drawLine(ctx, rows, "candidate_count", "#245a8f", w, h);
  drawLegend(ctx);
}

function drawGrid(ctx, w, h) {
  ctx.strokeStyle = "#e1e8ec";
  ctx.lineWidth = 1;
  for (let i = 1; i < 4; i += 1) {
    const y = 22 + i * ((h - 42) / 4);
    ctx.beginPath();
    ctx.moveTo(32, y);
    ctx.lineTo(w - 14, y);
    ctx.stroke();
  }
}

function drawLine(ctx, rows, key, color, w, h) {
  if (!rows.length) return;
  const values = rows.map((row) => Number(row[key] || 0));
  const max = Math.max(1, ...values);
  const left = 32;
  const right = w - 14;
  const top = 20;
  const bottom = h - 22;
  ctx.strokeStyle = color;
  ctx.lineWidth = 2;
  ctx.beginPath();
  rows.forEach((row, index) => {
    const x = left + (index / Math.max(1, rows.length - 1)) * (right - left);
    const y = bottom - (Number(row[key] || 0) / max) * (bottom - top);
    if (index === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.stroke();
}

function drawLegend(ctx) {
  const rows = [
    ["learned", "#0f766e"],
    ["fallback", "#a33b35"],
    ["candidate", "#245a8f"],
  ];
  rows.forEach((row, index) => {
    const x = 38 + index * 92;
    ctx.fillStyle = row[1];
    ctx.fillRect(x, 10, 10, 10);
    ctx.fillStyle = "#63727a";
    ctx.font = "12px Microsoft YaHei, Arial";
    ctx.fillText(row[0], x + 16, 19);
  });
}

function renderReplay() {
  if (state.workbenchTicks.length) {
    const tick = state.workbenchTicks[Math.max(0, Math.min(state.workbenchTickIndex, state.workbenchTicks.length - 1))] || {};
    $("replayDetail").innerHTML = `
      ${kv("阶段", `${tick.tick_index || ""}. ${tick.title || ""}`)}
      ${kv("做了什么", tick.summary || "")}
      ${kv("细节", tick.detail || "")}
      ${kv("边界", state.workbenchRuntime?.boundary || "")}
    `;
    $("tickButtons").innerHTML = state.workbenchTicks.map((item, index) => `
      <button type="button" class="tick-jump ${index === state.workbenchTickIndex ? "active" : ""}" data-tick-index="${index}">
        ${escapeHtml(item.tick_index)} ${escapeHtml(item.title)}
      </button>
    `).join("");
    document.querySelectorAll("[data-tick-index]").forEach((button) => {
      button.addEventListener("click", () => {
        state.workbenchTickIndex = Number(button.dataset.tickIndex || 0);
        renderReplay();
        renderMetrics();
      });
    });
    renderMetrics();
    return;
  }
  const tick = state.snapshot?.tick || 0;
  const runtime = (state.snapshot?.runtime_trace || []).find((row) => Number(row.tick) === Number(tick)) || {};
  const chat = (state.snapshot?.chat_trace || []).find((row) => Number(row.tick) === Number(tick)) || {};
  const feeling = (state.snapshot?.feelings || []).find((row) => Number(row.tick) === Number(tick)) || {};
  $("tickButtons").innerHTML = "";
  $("replayDetail").innerHTML = `
    ${kv("输入", inputLabel(chat))}
    ${kv("呈现", chat.presented_text || "")}
    ${kv("底层提交", runtime.committed_text || "")}
    ${kv("候选", (runtime.candidate_phrase_ids || []).join(" · "))}
    ${kv("学习", chat.learned_phrase_id || "")}
    ${kv("fallback", chat.used_honest_fallback ? "true" : "false")}
    ${kv("facts", JSON.stringify(feeling.facts || {}))}
  `;
}

function stepWorkbenchTick(delta) {
  if (!state.workbenchTicks.length) return;
  state.workbenchTickIndex = Math.max(0, Math.min(state.workbenchTicks.length - 1, state.workbenchTickIndex + delta));
  renderReplay();
  renderMetrics();
}

function toggleTickPlayback() {
  if (state.playbackPlaying) {
    stopTickPlayback();
    return;
  }
  if (!state.workbenchTicks.length) return;
  state.playbackPlaying = true;
  $("tickPlayBtn").textContent = "暂停";
  state.playbackTimer = window.setInterval(() => {
    if (state.workbenchTickIndex >= state.workbenchTicks.length - 1) {
      stopTickPlayback();
      return;
    }
    stepWorkbenchTick(1);
  }, 900);
}

function stopTickPlayback() {
  state.playbackPlaying = false;
  $("tickPlayBtn").textContent = "播放";
  if (state.playbackTimer) window.clearInterval(state.playbackTimer);
  state.playbackTimer = null;
}

function inputLabel(row) {
  if (!row) return "";
  if (row.user_text) return row.user_text;
  const count = Number(row.incoming_query_count || 0);
  const length = Number(row.user_text_length || row.incoming_query_total_length || 0);
  if (count <= 0 && length <= 0) return "(feedback)";
  const hash = String(row.user_text_hash || row.incoming_query_hash || "");
  const shortHash = hash ? hash.slice(0, 16) : "no-hash";
  return `历史输入已脱敏 · ${length} 字 · ${shortHash}`;
}

function kv(label, value) {
  return `<div class="kv"><span>${escapeHtml(label)}</span><span class="mono">${escapeHtml(value)}</span></div>`;
}

function renderPhrases() {
  const rows = state.snapshot?.top_phrases || [];
  $("topPhrases").innerHTML = rows.length ? rows.map((row) => `
    <div class="row-card"><b>${escapeHtml(row.text)}</b><small>${escapeHtml(row.phrase_id)} · support ${escapeHtml(row.support)}</small></div>
  `).join("") : `<div class="row-card"><b>不知道</b><small>暂无已召回短语</small></div>`;
}

function renderCloud() {
  const latest = latestTurnEvent();
  const labels = state.snapshot?.audit?.unique_feelings || [];
  const top = state.snapshot?.top_phrases || [];
  const objectLabels = latest?.turn?.object_files?.map((item) => item.top_visible_label) || [];
  const teaching = state.phase20Teaching?.trace?.response_text ? [state.phase20Teaching.trace.response_text] : [];
  $("thoughtCloud").innerHTML = [
    ...objectLabels.map((label) => `<span class="chip object-chip">${escapeHtml(label)}</span>`),
    ...teaching.map((label) => `<span class="chip teach-chip">${escapeHtml(label)}</span>`),
    ...labels.map((label) => `<span class="chip">${escapeHtml(label)}</span>`),
    ...top.map((row) => `<span class="chip">${escapeHtml(row.text)}</span>`),
  ].join("") || `<span class="chip">等待输入</span>`;
}

function renderAudit() {
  const audit = state.snapshot?.audit || {};
  const latest = latestTurnEvent();
  const turn = latest?.turn || {};
  $("auditPanel").innerHTML = `
    <div class="row-card"><b>当前工作台路径</b><small>主发送路径: /api/phase20/turn · 教学: teacher_event_cooccurrence · 原文: 当前页面显示, SQLite 不持久化</small></div>
    <div class="row-card"><b>最新 Phase20</b><small>${escapeHtml(JSON.stringify({
      reply: turn.reply_text || "",
      teaching_applied: Boolean(turn.teaching_applied),
      object_count: (turn.object_files || []).length,
      image_sha16: turn.image_sha16 || "",
    }))}</small></div>
    <div class="row-card"><b>latest runtime</b><small>${escapeHtml(JSON.stringify(audit.latest_runtime || {}))}</small></div>
    <div class="row-card"><b>latest feeling</b><small>${escapeHtml(JSON.stringify(audit.latest_feeling || {}))}</small></div>
  `;
}

function renderPhase8() {
  const audit = state.snapshot?.phase8_audit || {};
  const ledger = audit.ledger_pie || [];
  const feelings = audit.feelings_display || {};
  const chain = audit.endogenous_chain || {};
  const overlay = audit.visual_focus_overlay || [];
  $("ledgerPie").innerHTML = ledger.map((row) => `
    <div class="row-card"><b>${escapeHtml(row.source)}</b><small>${escapeHtml(Number(row.value || 0).toFixed(4))}</small></div>
  `).join("") || `<div class="row-card"><b>等待</b><small>暂无 ledger source</small></div>`;
  $("feelingsDisplay").innerHTML = Object.entries(feelings).map(([key, value]) => `
    <div class="meter-row"><span>${escapeHtml(key)}</span><meter min="0" max="1" value="${Number(value || 0)}"></meter><small>${escapeHtml(Number(value || 0).toFixed(3))}</small></div>
  `).join("");
  $("endogenousChain").innerHTML = Object.entries(chain).map(([sa, values]) => `
    <div class="row-card"><b>${escapeHtml(sa)}</b><small>${escapeHtml(JSON.stringify(values))}</small></div>
  `).join("");
  $("visualOverlay").innerHTML = overlay.map((row) => `
    <div class="row-card"><b>${escapeHtml(row.action_kind)}</b><small>${escapeHtml(row.target_sa_id)} · ${escapeHtml(Number(row.score || 0).toFixed(3))}</small></div>
  `).join("");
}

function renderInner() {
  const latest = latestTurnEvent();
  const media = latest?.media || null;
  const objects = latest?.turn?.object_files || [];
  $("innerVision").innerHTML = `
    <div class="inner-card">
      <b>内心画面</b>
      ${renderMedia(media && media.kind !== "audio" ? media : null) || `<small>暂无图片输入。</small>`}
      <div class="object-bars">
        ${objects.map((item) => confidenceBar(item.top_visible_label, item.raw_confidence, item.decision_tier)).join("") || `<small>暂无 ObjectFile。</small>`}
      </div>
    </div>
  `;
  $("innerAudio").innerHTML = `
    <div class="inner-card">
      <b>内心音频</b>
      ${renderMedia(media && media.kind === "audio" ? media : null) || `<small>暂无音频输入；Phase 20.4 只做播放展示, 不宣称听觉识别。</small>`}
    </div>
  `;
}

function confidenceBar(label, value, tier) {
  const pct = Math.max(0, Math.min(100, Number(value || 0) * 100));
  return `
    <div class="confidence-row">
      <span>${escapeHtml(label)} · ${escapeHtml(tier)}</span>
      <i><b style="width:${pct}%"></b></i>
      <small>${Number(value || 0).toFixed(3)}</small>
    </div>
  `;
}

function renderMemory() {
  if (!$("memoryPackages")) return;
  const view = state.memoryView || {};
  const packages = view.packages || [];
  const memories = view.memories || [];
  $("memoryScopeLine").textContent = state.selectedPackageId
    ? `正在查看记忆包: ${state.selectedPackageId}`
    : `显示本地记忆 ${view.total_memories ?? memories.length} 条`;
  $("memoryPackages").innerHTML = packages.length ? packages.map((pkg) => `
    <div class="row-card memory-package ${pkg.status === "uninstalled" ? "muted-package" : ""}">
      <b>${escapeHtml(pkg.name || pkg.package_id)}</b>
      <small>${escapeHtml(pkg.package_id)} · ${escapeHtml(pkg.status || "active")} · 新增 ${escapeHtml(pkg.added_count || 0)} · 去重 ${escapeHtml(pkg.dedup_count || 0)}</small>
      <div class="memory-actions">
        <button type="button" data-memory-view-package="${escapeHtml(pkg.package_id)}">查看内容</button>
        <button type="button" data-memory-uninstall-package="${escapeHtml(pkg.package_id)}">卸载</button>
      </div>
    </div>
  `).join("") : `<div class="row-card"><b>暂无导入包</b><small>导入后会显示名称、内容和卸载入口。</small></div>`;
  $("memoryList").innerHTML = memories.length ? memories.map((item) => `
    <label class="row-card memory-row">
      <input type="checkbox" class="memory-check" value="${escapeHtml(item.memory_id)}">
      <span>
        <b>${escapeHtml(item.display_title || item.text || item.memory_id)}</b>
        <small>${escapeHtml(item.kind_label || item.kind)} · ${escapeHtml(item.display_detail || item.memory_id)} · id ${escapeHtml(item.memory_id)}</small>
      </span>
    </label>
  `).join("") : `<div class="row-card"><b>暂无匹配记忆</b><small>换个关键词或刷新。</small></div>`;
  document.querySelectorAll("[data-memory-view-package]").forEach((button) => {
    button.addEventListener("click", () => refreshMemoryView(button.dataset.memoryViewPackage || ""));
  });
  document.querySelectorAll("[data-memory-uninstall-package]").forEach((button) => {
    button.addEventListener("click", () => uninstallMemoryPackage(button.dataset.memoryUninstallPackage || ""));
  });
}

function selectedMemoryIds() {
  return Array.from(document.querySelectorAll(".memory-check:checked")).map((item) => item.value);
}

function setMemorySelection(checked) {
  document.querySelectorAll(".memory-check").forEach((item) => { item.checked = checked; });
}

function invertMemorySelection() {
  document.querySelectorAll(".memory-check").forEach((item) => { item.checked = !item.checked; });
}

function switchTab(name) {
  document.querySelectorAll(".tab").forEach((button) => button.classList.toggle("active", button.dataset.tab === name));
  document.querySelectorAll(".tab-panel").forEach((panel) => panel.classList.toggle("active", panel.id === `tab-${name}`));
  if (name === "memory" && !state.memoryView) refreshMemoryView();
}

function latestTurnEvent() {
  for (let index = state.phase20History.length - 1; index >= 0; index -= 1) {
    if (state.phase20History[index].type === "turn") return state.phase20History[index];
  }
  return null;
}

function numberInput(id, fallback) {
  const value = Number($(id)?.value || fallback);
  return Number.isFinite(value) ? value : fallback;
}

function renderAll() {
  const snapshot = state.snapshot || {};
  $("statusLine").textContent = `tick ${snapshot.tick || 0} · ${snapshot.db_path || ""}`;
  document.querySelectorAll(".mode").forEach((button) => {
    button.classList.toggle("active", button.dataset.mode === state.mode);
  });
  renderChat();
  renderSessionHistory();
  renderMetrics();
  renderChart();
  renderReplay();
  renderPhrases();
  renderCloud();
  renderAudit();
  renderPhase8();
  renderInner();
  renderPhase20();
  renderMediaPreview();
  renderMemory();
  renderPackageMirror();
}

function renderReplay() {
  if (state.workbenchTicks.length) {
    const tick = state.workbenchTicks[Math.max(0, Math.min(state.workbenchTickIndex, state.workbenchTicks.length - 1))] || {};
    const action = tick.action_chosen || {};
    const energy = tick.energy_RAPF || [];
    const topItems = tick.state_pool_top12 || [];
    const projection = tick.is_projection ? "projection warning" : "RuntimeTickEvent";
    $("replayDetail").innerHTML = `
      ${kv("event", `${tick.tick_index || ""}. ${tick.title || ""}`)}
      ${kv("source", projection)}
      ${kv("runtime tick", tick.runtime_tick || "")}
      ${kv("action", action.action_id || "")}
      ${kv("energy R/A/P/F", energy.map((item) => Number(item || 0).toFixed(3)).join(" / "))}
      ${kv("state top", topItems.slice(0, 4).map((item) => `${item.label}:${Number(item.attention_energy || 0).toFixed(2)}`).join("; ") || "none")}
      ${kv("summary", tick.summary || "")}
      ${kv("detail", tick.detail || "")}
      ${kv("boundary", tick.boundary || state.workbenchRuntime?.boundary || "")}
    `;
    $("tickButtons").innerHTML = state.workbenchTicks.map((item, index) => `
      <button type="button" class="tick-jump ${index === state.workbenchTickIndex ? "active" : ""}" data-tick-index="${index}">
        ${escapeHtml(item.tick_index)} ${escapeHtml(item.title)}
      </button>
    `).join("");
    document.querySelectorAll("[data-tick-index]").forEach((button) => {
      button.addEventListener("click", () => {
        state.workbenchTickIndex = Number(button.dataset.tickIndex || 0);
        renderReplay();
        renderMetrics();
      });
    });
    renderMetrics();
    return;
  }
  const tick = state.snapshot?.tick || 0;
  const runtime = (state.snapshot?.runtime_trace || []).find((row) => Number(row.tick) === Number(tick)) || {};
  const chat = (state.snapshot?.chat_trace || []).find((row) => Number(row.tick) === Number(tick)) || {};
  const feeling = (state.snapshot?.feelings || []).find((row) => Number(row.tick) === Number(tick)) || {};
  $("tickButtons").innerHTML = "";
  $("replayDetail").innerHTML = `
    ${kv("input", inputLabel(chat))}
    ${kv("presented", chat.presented_text || "")}
    ${kv("runtime commit", runtime.committed_text || "")}
    ${kv("candidates", (runtime.candidate_phrase_ids || []).join(" · "))}
    ${kv("learning", chat.learned_phrase_id || "")}
    ${kv("fallback", chat.used_honest_fallback ? "true" : "false")}
    ${kv("facts", JSON.stringify(feeling.facts || {}))}
  `;
}

function renderSessionHistory() {
  const node = $("sessionHistoryList");
  if (!node) return;
  const turnCount = state.phase20History.filter((item) => item.type === "turn").length;
  const teachingCount = state.phase20History.filter((item) => item.type === "teaching").length;
  const latest = latestTurnEvent();
  node.innerHTML = `
    <div class="row-card">
      <b>当前会话</b>
      <small>${turnCount} turn · ${teachingCount} 次教学 · ${latest?.turn?.user_text_hash_display || "no-hash"}</small>
    </div>
    <div class="row-card">
      <b>历史隐私</b>
      <small>默认不保存跨 session 原文。需要分享时请从记忆包面板显式导出。</small>
    </div>
  `;
}

function renderPackageMirror() {
  const node = $("packagePanelMirror");
  if (!node) return;
  const view = state.memoryView || {};
  const packages = view.packages || [];
  const memories = view.memories || [];
  const selected = selectedMemoryIds();
  node.innerHTML = `
    <div class="row-card">
      <b>本地记忆包</b>
      <small>${packages.length} 个包 · 当前筛选 ${memories.length} 条记忆 · 已勾选 ${selected.length} 条</small>
    </div>
    ${packages.slice(0, 4).map((pkg) => `
      <div class="row-card">
        <b>${escapeHtml(pkg.name || pkg.package_id)}</b>
        <small>${escapeHtml(pkg.status || "active")} · 新增 ${escapeHtml(pkg.added_count || 0)} · 去重 ${escapeHtml(pkg.dedup_count || 0)}</small>
      </div>
    `).join("") || `<div class="row-card"><b>暂无导入包</b><small>可在记忆面板粘贴 JSON 导入。</small></div>`}
  `;
}

function renderPhrases() {
  const rows = state.snapshot?.top_phrases || [];
  $("topPhrases").innerHTML = rows.length ? rows.map((row) => `
    <div class="row-card"><b>${escapeHtml(row.text)}</b><small>表达短句 · support ${escapeHtml(row.support)}</small></div>
  `).join("") : `<div class="row-card"><b>不知道</b><small>暂无已召回短语</small></div>`;
}

function renderMemory() {
  if (!$("memoryPackages")) return;
  const view = state.memoryView || {};
  const packages = view.packages || [];
  const memories = view.memories || [];
  $("memoryScopeLine").textContent = state.selectedPackageId
    ? `正在查看记忆包内容`
    : `显示本地记忆 ${view.total_memories ?? memories.length} 条`;
  $("memoryPackages").innerHTML = packages.length ? packages.map((pkg) => `
    <div class="row-card memory-package ${pkg.status === "uninstalled" ? "muted-package" : ""}">
      <b>${escapeHtml(pkg.name || "未命名记忆包")}</b>
      <small>${escapeHtml(pkg.status || "active")} · 新增 ${escapeHtml(pkg.added_count || 0)} · 去重 ${escapeHtml(pkg.dedup_count || 0)}</small>
      <div class="memory-actions">
        <button type="button" data-memory-view-package="${escapeHtml(pkg.package_id)}">查看内容</button>
        <button type="button" data-memory-uninstall-package="${escapeHtml(pkg.package_id)}">卸载</button>
      </div>
    </div>
  `).join("") : `<div class="row-card"><b>暂无导入包</b><small>导入后会显示名称、内容和卸载入口。</small></div>`;
  $("memoryList").innerHTML = memories.length ? memories.map((item) => `
    <label class="row-card memory-row">
      <input type="checkbox" class="memory-check" value="${escapeHtml(item.memory_id)}">
      <span>
        <b>${escapeHtml(item.display_title || item.text || "未命名记忆")}</b>
        <small>${escapeHtml(item.kind_label || item.kind)} · ${escapeHtml(stripRawIds(item.display_detail || ""))}</small>
      </span>
    </label>
  `).join("") : `<div class="row-card"><b>暂无匹配记忆</b><small>换个关键词或刷新。</small></div>`;
  document.querySelectorAll("[data-memory-view-package]").forEach((button) => {
    button.addEventListener("click", () => refreshMemoryView(button.dataset.memoryViewPackage || ""));
  });
  document.querySelectorAll("[data-memory-uninstall-package]").forEach((button) => {
    button.addEventListener("click", () => uninstallMemoryPackage(button.dataset.memoryUninstallPackage || ""));
  });
  renderPackageMirror();
}

function stripRawIds(value) {
  return String(value || "")
    .replace(/style_paradigm::[\\w.:-]+/g, "风格范式")
    .replace(/style::[\\w.:-]+/g, "风格短句")
    .replace(/teacher_phrase::[\\w.:-]+/g, "教师短句")
    .replace(/phase20ctx::[\\w.:-]+/g, "上下文记忆")
    .replace(/assocp?::[\\w.:-]+/g, "共现边");
}

window.addEventListener("resize", renderChart);
boot().catch((error) => {
  $("statusLine").textContent = error.message;
});

// Phase 20.5a2 UI repair: replay ticks are complete AP loop snapshots.
function renderReplay() {
  if (state.workbenchTicks.length) {
    const tick = state.workbenchTicks[Math.max(0, Math.min(state.workbenchTickIndex, state.workbenchTicks.length - 1))] || {};
    const action = tick.action_chosen || {};
    const energy = tick.energy_RAPF || [];
    const topItems = tick.state_pool_top12 || [];
    const draft = tick.draft_snapshot || tick.draft_changes || {};
    const labels = draft.object_labels || [];
    $("replayDetail").innerHTML = `
      <div class="draft-snapshot">
        <div>
          <span>草稿框</span>
          <b>${escapeHtml(draft.draft_buffer || draft.committed_text || "空")}</b>
        </div>
        <div>
          <span>本 tick 草稿动作</span>
          <b>${escapeHtml(draft.draft_action_kind || "none")}${draft.typed_token ? ` · ${escapeHtml(draft.typed_token)}` : ""}</b>
        </div>
      </div>
      ${kv("tick", `${tick.tick_index || ""} / runtime ${tick.runtime_tick || ""}`)}
      ${kv("循环帧", tick.stage || "")}
      ${kv("输入", `${draft.input_text_length || 0} 字 · ${draft.input_text_hash || "no-hash"}`)}
      ${kv("视觉对象", labels.length ? labels.join(" / ") : "none")}
      ${kv("共现召回", draft.teaching_candidate_applied ? `召回 ${draft.teaching_id || ""}` : "未召回教师共现候选")}
      ${kv("候选动作", action.action_id || "")}
      ${kv("能量 R/A/P/F", energy.map((item) => Number(item || 0).toFixed(3)).join(" / "))}
      ${kv("状态池 top", topItems.slice(0, 6).map((item) => `${item.family}:${item.label}:${Number(item.attention_energy || 0).toFixed(2)}`).join("; ") || "none")}
      ${kv("说明", tick.summary || "")}
      ${kv("边界", tick.boundary || state.workbenchRuntime?.boundary || "")}
    `;
    $("tickButtons").innerHTML = state.workbenchTicks.map((item, index) => {
      const snap = item.draft_snapshot || item.draft_changes || {};
      const title = snap.draft_action_kind === "type_text"
        ? `${item.tick_index} 写 ${snap.typed_token || ""}`
        : `${item.tick_index} ${snap.draft_action_kind || item.title || ""}`;
      return `
        <button type="button" class="tick-jump ${index === state.workbenchTickIndex ? "active" : ""}" data-tick-index="${index}">
          ${escapeHtml(title)}
        </button>
      `;
    }).join("");
    document.querySelectorAll("[data-tick-index]").forEach((button) => {
      button.addEventListener("click", () => {
        state.workbenchTickIndex = Number(button.dataset.tickIndex || 0);
        renderReplay();
        renderMetrics();
      });
    });
    renderMetrics();
    return;
  }
  $("tickButtons").innerHTML = "";
  $("replayDetail").innerHTML = `<div class="row-card"><b>等待本轮 turn</b><small>发送后会显示每 tick 的完整 AP loop 快照。</small></div>`;
}

function renderPhase20() {
  const turn = state.phase20Turn;
  const teaching = state.phase20Teaching;
  if (!turn && !teaching) {
    $("phase20Panel").innerHTML = `<div class="row-card"><b>本轮恢复</b><small>发送后显示回复、对象、教学与 tick 设置。</small></div>`;
    return;
  }
  const objects = ((turn && turn.object_files) || []).map((item) => (
    `${escapeHtml(item.top_visible_label)} · ${escapeHtml(item.decision_tier)} · ${Number(item.raw_confidence || 0).toFixed(3)}`
  )).join("<br>");
  const teachTrace = teaching?.trace || turn?.teaching_trace || null;
  const feedback = turn?.feedback_trace || null;
  const runtime = turn?.workbench_runtime || {};
  $("phase20Panel").innerHTML = `
    <div class="turn-summary-title">本轮恢复</div>
    ${kv("回复", turn?.reply_text || "")}
    ${kv("图片", turn?.image_sha16 || "none")}
    ${kv("对象", objects || "none")}
    ${kv("风格", turn?.styled ? `${turn.styled.paradigm_id} / ${turn.styled.entry_id}` : "")}
    ${kv("教学", teachTrace ? `纠正回答 "${teachTrace.response_text}" 已学习` : (turn?.teaching_applied ? `召回候选 ${turn.teaching_id}` : "none"))}
    ${kv("反馈", feedback ? `${feedback.feedback_kind} / ${Number(feedback.correction_total_outcome || 0).toFixed(3)}` : "none")}
    ${kv("tick", `提交点=${runtime.commit_tick_index || "-"} · max=${runtime.max_ticks_if_no_commit || "-"} · idle=${runtime.idle_ticks_after_commit || "-"}`)}
  `;
}

function renderMetrics() {
  const metrics = state.snapshot?.metrics || {};
  $("metricPhrase").textContent = metrics.phrase_records || 0;
  $("metricAssoc").textContent = metrics.association_pairs || 0;
  $("metricFeeling").textContent = metrics.unique_feeling_count || 0;
  $("metricFallback").textContent = metrics.fallback_count || 0;
  const count = state.workbenchTicks.length || Number(state.snapshot?.tick || 0);
  $("tickLabel").textContent = state.workbenchTicks.length
    ? `AP loop tick ${state.workbenchTickIndex + 1}`
    : `tick ${state.snapshot?.tick || 0}`;
  $("tickSlider").max = String(Math.max(0, count - (state.workbenchTicks.length ? 1 : 0)));
  $("tickSlider").value = String(state.workbenchTicks.length ? state.workbenchTickIndex : state.snapshot?.tick || 0);
  $("frameCount").textContent = state.workbenchTicks.length
    ? `${state.workbenchTickIndex + 1} / ${state.workbenchTicks.length}`
    : `${state.snapshot?.tick || 0} / ${state.snapshot?.tick || 0}`;
}

// Phase 20.5a3 visible-final marker.

function _phase205a3Tick() {
  if (!state.workbenchTicks.length) return null;
  const index = Math.max(0, Math.min(state.workbenchTickIndex, state.workbenchTicks.length - 1));
  return state.workbenchTicks[index] || null;
}

function _phase205a3Draft(tick = _phase205a3Tick()) {
  return (tick && (tick.draft_snapshot || tick.draft_changes)) || {};
}

function setWorkbenchTick(index) {
  if (!state.workbenchTicks.length) return;
  state.workbenchTickIndex = Math.max(0, Math.min(state.workbenchTicks.length - 1, Number(index || 0)));
  renderReplay();
  renderMetrics();
  renderChart();
  renderCloud();
  renderAudit();
  renderInner();
}

function stepWorkbenchTick(delta) {
  if (!state.workbenchTicks.length) return;
  setWorkbenchTick(state.workbenchTickIndex + delta);
}

function renderReplay() {
  const tick = _phase205a3Tick();
  if (!tick) {
    $("tickButtons").innerHTML = "";
    $("replayDetail").innerHTML = `<div class="row-card"><b>等待本轮 turn</b><small>发送后显示每个 tick 的 AP loop 快照。</small></div>`;
    return;
  }
  const draft = _phase205a3Draft(tick);
  const action = tick.action_chosen || {};
  const energy = tick.energy_RAPF || [];
  const labels = draft.object_labels || [];
  $("replayDetail").innerHTML = `
    <div class="draft-snapshot">
      <div><span>草稿框二维快照</span><b>${escapeHtml(draft.draft_buffer || draft.committed_text || "空")}</b></div>
      <div><span>本 tick 草稿动作</span><b>${escapeHtml(draft.draft_action_kind || "none")}${draft.typed_token ? ` · ${escapeHtml(draft.typed_token)}` : ""}</b></div>
    </div>
    ${kv("tick", `${tick.tick_index || ""} / runtime ${tick.runtime_tick || ""}`)}
    ${kv("循环帧", tick.stage || "")}
    ${kv("输入观察", `${draft.input_text_length || 0} 字 · ${draft.input_text_hash || "no-hash"}`)}
    ${kv("视觉对象", labels.length ? labels.join(" / ") : "none")}
    ${kv("共现召回", draft.teaching_candidate_applied ? `召回 ${draft.teaching_id || ""}` : "未召回教师共现候选")}
    ${kv("候选动作", action.action_id || "")}
    ${kv("能量 R/A/P/F", energy.map((item) => Number(item || 0).toFixed(3)).join(" / "))}
    ${kv("状态池 top", (tick.state_pool_top12 || []).slice(0, 6).map((item) => `${item.family}:${item.label}:${Number(item.attention_energy || 0).toFixed(2)}`).join("; ") || "none")}
    ${kv("边界", tick.boundary || state.workbenchRuntime?.boundary || "")}
  `;
  $("tickButtons").innerHTML = state.workbenchTicks.map((item, index) => {
    const snap = item.draft_snapshot || item.draft_changes || {};
    const title = snap.draft_action_kind === "type_text"
      ? `${item.tick_index} 写 ${snap.typed_token || ""}`
      : `${item.tick_index} ${snap.draft_action_kind || item.title || ""}`;
    return `<button type="button" class="tick-jump ${index === state.workbenchTickIndex ? "active" : ""}" data-tick-index="${index}">${escapeHtml(title)}</button>`;
  }).join("");
  document.querySelectorAll("[data-tick-index]").forEach((button) => {
    button.addEventListener("click", () => setWorkbenchTick(button.dataset.tickIndex || 0));
  });
}

function renderMetrics() {
  const metrics = state.snapshot?.metrics || {};
  $("metricPhrase").textContent = metrics.phrase_records || 0;
  $("metricAssoc").textContent = metrics.association_pairs || 0;
  $("metricFeeling").textContent = metrics.unique_feeling_count || 0;
  $("metricFallback").textContent = metrics.fallback_count || 0;
  const count = state.workbenchTicks.length || Number(state.snapshot?.tick || 0);
  $("tickLabel").textContent = state.workbenchTicks.length ? `AP loop tick ${state.workbenchTickIndex + 1}` : `tick ${state.snapshot?.tick || 0}`;
  $("tickSlider").max = String(Math.max(0, count - (state.workbenchTicks.length ? 1 : 0)));
  $("tickSlider").value = String(state.workbenchTicks.length ? state.workbenchTickIndex : state.snapshot?.tick || 0);
  $("frameCount").textContent = state.workbenchTicks.length
    ? `${state.workbenchTickIndex + 1} / ${state.workbenchTicks.length}`
    : `${state.snapshot?.tick || 0} / ${state.snapshot?.tick || 0}`;
}
