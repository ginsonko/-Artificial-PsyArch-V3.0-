const $ = (id) => document.getElementById(id);

let sessionId = "phase20_7_workbench";
let currentTicks = [];
let allTicks = [];
let selectedTickIndex = -1;
let latestReplyText = "";
let autoIdleTimer = null;
let autoIdleDelayMs = 1000;
let idleQuietRuns = 0;
let requestInFlight = false;
let pendingUserTurn = null;

// B6: 演示间独立 session 切换基础设施。每个演示都用各自的 demo session,
// 这样演示和主对话不互染、每个演示都能从空白的"没教过任何东西"开局。
// 红线:仍走真实 /api/phase20_7/turn,无脚本伪造、无答案表、无定时器驱动的假自发。
let mainSessionId = "phase20_7_workbench";
let savedSessionId = null;
let activeDemoId = null;
let agencyHeartbeatTimer = null;

function enterDemo(demoId, suffix) {
  // 进入演示模式: 停 autoIdle/progressPoll, 切到一个新 demo session, 清空 composer。
  // 注意: sendTurn 在调用前已把 session_id 拼进 queued payload 字面值,
  // 所以这里在 sendTurn 调用前切 sessionId 才会落到下一 turn。
  stopAutoIdle(false);
  stopProgressPolling();
  if (!savedSessionId) savedSessionId = sessionId;
  sessionId = `${demoId}-${Date.now().toString(36)}-${suffix}`;
  activeDemoId = demoId;
  clearComposer();
  if (typeof resetHomeCanvas === "function") resetHomeCanvas();
  if (agencyHeartbeatTimer) { clearInterval(agencyHeartbeatTimer); agencyHeartbeatTimer = null; }
}

function exitDemo(finalSystemMsg) {
  // 离开演示模式: 清心跳定时器, 恢复主 session, 可选系统提示。
  if (agencyHeartbeatTimer) { clearInterval(agencyHeartbeatTimer); agencyHeartbeatTimer = null; }
  stopAutoIdle(false);
  stopProgressPolling();
  if (savedSessionId) { sessionId = savedSessionId; savedSessionId = null; }
  activeDemoId = null;
  if (finalSystemMsg) addMessage("system", finalSystemMsg);
}
let streamItems = [];
let lastInnerPictureTick = null;
let progressPollTimer = null;
let progressPollSessionId = "";
let browserVoiceCache = [];
let memoryPackageSelection = {
  keyword: "",
  page: 1,
  pageSize: 12,
  selectedEventIds: new Set(),
  lastExportedPackage: null,
};
let canvasState = {
  drawing: false,
  color: "#111111",
  size: 4,
  lastPoint: null,
};

const actionNames = {
  observe_text: "读取输入",
  write_cell: "写入草稿",
  commit_reply: "提交回复",
  reply_tts_audio: "本地朗读",
  request_teacher: "请求教学",
  maintain_unclosed: "保留未闭合",
  idle_observe: "闲时观察",
  idle_think: "闲时思考",
  idle_visual_focus: "闲时看图",
  idle_audio_focus: "闲时听觉",
  integrate_feedback: "整合教学",
  visual_patch_sensor: "视觉采样",
  move_focus: "移动视焦点",
  audio_audit_sensor: "听觉审计",
  widen_focus: "扩大视野",
  stop_generating: "主动停止",
  visual_imagination_recall: "想象画面",
  project_unit: "投一个轮廓单元 (投哪类由学到的顺序决定)",
  project_contour: "把轮廓投到画板",
  observe_painting: "观察自己的画",
  commit_painting: "把画提交出来",
};

const familyNames = {
  text: "文本",
  user_text: "用户文本",
  draft: "草稿",
  visual_patch: "视觉片段",
  visual_focus: "视焦点",
  audio_audit: "听觉片段",
  tts_actuator: "朗读执行器",
  unclosed_pull: "未闭合牵引",
  feedback: "教学反馈",
};

const learningStageNames = {
  demonstrate: "观察示范",
  strong_scaffold: "强脚手架",
  weak_scaffold: "弱脚手架",
  feedback_only: "反馈整合",
  teacher_off: "教师退场",
  cold_retest: "冷重测",
};

const learningTendencyNames = {
  feedback_only: "先听反馈",
  teacher_off_probe: "尝试自己来",
  cold_retest_probe: "冷重测压力",
  return_to_scaffold: "回到脚手架",
};

const runtimeStageNames = {
  contact: "接触",
  imitation: "模仿",
  correction: "纠错",
  review: "复盘",
  self_test: "自测",
  generalization: "泛化",
  teacher_exit: "教师退场",
  cold_retest: "冷启动复测",
};

const lifecycleStageNames = {
  taught: "被教",
  reviewed: "已复盘",
  self_tested: "已自测",
  adjusted_after_feedback: "反馈调整",
  retested: "再测",
  teacher_exit_ready: "教师可退场",
  cold_retest_ready: "冷启动复测",
};

function esc(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function number(value, digits = 2) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed.toFixed(digits) : "0.00";
}

function percent(value) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? `${Math.round(parsed * 100)}%` : "0%";
}

async function postJson(url, payload) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return response.json();
}

async function getJson(url) {
  const response = await fetch(url, { method: "GET" });
  return response.json();
}

function readFileAsDataUrl(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result || ""));
    reader.onerror = () => reject(reader.error || new Error("file_read_failed"));
    reader.readAsDataURL(file);
  });
}

async function uploadMediaFile(file, kind) {
  if (!file) return;
  setStatus(`正在导入${kind === "image" ? "图片" : "音频"}`, "running");
  const dataUrl = await readFileAsDataUrl(file);
  const data = await postJson("/api/phase20/media/upload", {
    name: file.name,
    data_url: dataUrl,
  });
  if (data.error) {
    setStatus(`文件导入失败: ${data.error}`, "sleeping");
    return;
  }
  if (kind === "image") {
    $("imagePath").value = data.path || "";
  } else {
    $("audioPath").value = data.path || "";
  }
  setStatus("文件已导入", "");
}

function initHomeCanvas() {
  const canvas = $("homeCanvas");
  if (!canvas || canvas.dataset.initialized === "1") return;
  canvas.dataset.initialized = "1";
  const ctx = canvas.getContext?.("2d");
  if (!ctx) return;
  ctx.lineCap = "round";
  ctx.lineJoin = "round";
  ctx.fillStyle = "#ffffff";
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  ctx.strokeStyle = canvasState.color;
  ctx.lineWidth = canvasState.size;

  const pointerPos = (event) => {
    const rect = canvas.getBoundingClientRect();
    const x = (event.clientX - rect.left) * (canvas.width / rect.width);
    const y = (event.clientY - rect.top) * (canvas.height / rect.height);
    return { x, y };
  };

  const drawPoint = (point) => {
    ctx.beginPath();
    ctx.arc(point.x, point.y, Math.max(1.2, canvasState.size / 2), 0, Math.PI * 2);
    ctx.fillStyle = canvasState.color;
    ctx.fill();
  };

  canvas.addEventListener("pointerdown", (event) => {
    event.preventDefault();
    canvas.setPointerCapture?.(event.pointerId);
    canvasState.drawing = true;
    canvasState.lastPoint = pointerPos(event);
    drawPoint(canvasState.lastPoint);
  });

  canvas.addEventListener("pointermove", (event) => {
    if (!canvasState.drawing || !canvasState.lastPoint) return;
    const point = pointerPos(event);
    ctx.strokeStyle = canvasState.color;
    ctx.lineWidth = canvasState.size;
    ctx.beginPath();
    ctx.moveTo(canvasState.lastPoint.x, canvasState.lastPoint.y);
    ctx.lineTo(point.x, point.y);
    ctx.stroke();
    canvasState.lastPoint = point;
  });

  const stopDrawing = () => {
    canvasState.drawing = false;
    canvasState.lastPoint = null;
  };
  canvas.addEventListener("pointerup", stopDrawing);
  canvas.addEventListener("pointercancel", stopDrawing);
  canvas.addEventListener("pointerleave", stopDrawing);
}

function resetHomeCanvas() {
  const canvas = $("homeCanvas");
  const ctx = canvas?.getContext?.("2d");
  if (!canvas || !ctx) return;
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.fillStyle = "#ffffff";
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  canvasState.lastPoint = null;
  setCanvasStatus("画板已清空。");
}

function setCanvasStatus(text) {
  const node = $("canvasStatus");
  if (node) node.textContent = text;
}

function canvasToDataUrl() {
  const canvas = $("homeCanvas");
  if (!canvas) return "";
  return canvas.toDataURL("image/png");
}

function hasCanvasInk() {
  const canvas = $("homeCanvas");
  const ctx = canvas?.getContext?.("2d");
  if (!canvas || !ctx) return false;
  const { data } = ctx.getImageData(0, 0, canvas.width, canvas.height);
  for (let i = 0; i < data.length; i += 4) {
    if (data[i] !== 255 || data[i + 1] !== 255 || data[i + 2] !== 255 || data[i + 3] !== 255) return true;
  }
  return false;
}

function mediaUrl(path) {
  const text = String(path || "").trim();
  return text ? `/api/phase20/media?path=${encodeURIComponent(text)}` : "";
}

function setStatus(text, mode = "") {
  $("runtimeStatus").textContent = text;
  $("runtimePulse").textContent = text;
  $("runtimePulse").className = `runtime-pulse ${mode}`.trim();
}

function addMessage(kind, text) {
  const node = document.createElement("div");
  node.className = `message ${kind}`;
  node.textContent = text || "";
  $("chatLog").appendChild(node);
  $("chatLog").scrollTop = $("chatLog").scrollHeight;
}

function addMediaMessage(kind, label, path, mediaType) {
  const node = document.createElement("div");
  node.className = `message ${kind} media`;
  const title = document.createElement("div");
  title.textContent = label;
  node.appendChild(title);
  const url = mediaUrl(path);
  if (mediaType === "image") {
    const img = document.createElement("img");
    img.alt = label;
    img.src = url;
    node.appendChild(img);
  } else if (mediaType === "audio") {
    const audio = document.createElement("audio");
    audio.controls = true;
    audio.preload = "metadata";
    audio.src = url;
    node.appendChild(audio);
  }
  $("chatLog").appendChild(node);
  $("chatLog").scrollTop = $("chatLog").scrollHeight;
}

function buildPayload({ idle = false } = {}) {
  return {
    session_id: sessionId,
    runtime_stage: "stage6",
    text: idle ? "" : $("userText").value.trim(),
    image_path: idle ? "" : $("imagePath").value.trim(),
    audio_path: idle ? "" : $("audioPath").value.trim(),
    teacher_feedback: idle ? "" : $("teacherFeedback").value.trim(),
    post_commit_idle_ticks: idle ? 0 : 1,
    max_ticks: idle ? 8 : 32,
  };
}

function hasUserPayload(payload) {
  return Boolean(payload.text || payload.image_path || payload.audio_path || payload.teacher_feedback);
}

function clearComposer() {
  $("userText").value = "";
  $("imagePath").value = "";
  $("audioPath").value = "";
  $("teacherFeedback").value = "";
}

async function sendTurn({ idle = false, queuedPayload = null } = {}) {
  const payloadToSend = queuedPayload || buildPayload({ idle });
  if (requestInFlight) {
    if (!idle && hasUserPayload(payloadToSend)) {
      pendingUserTurn = payloadToSend;
      stopAutoIdle();
      setStatus("已暂停闲时，排队处理你的输入", "running");
    }
    return;
  }
  const payload = payloadToSend;
  if (!idle && !payload.text && !payload.image_path && !payload.audio_path && !payload.teacher_feedback) {
    setStatus("没有输入", "sleeping");
    return;
  }

  requestInFlight = true;
  startProgressPolling();
  setStatus(idle ? "闲时运行中" : "处理输入中", "running");
  try {
    if (!idle && payload.text) addMessage("user", payload.text);
    if (!idle && payload.image_path) addMediaMessage("user", `输入图片: ${payload.image_path}`, payload.image_path, "image");
    if (!idle && payload.audio_path) addMediaMessage("user", `输入音频: ${payload.audio_path}`, payload.audio_path, "audio");
    if (!idle && payload.teacher_feedback) addMessage("user", `教学: ${payload.teacher_feedback}`);

    const data = await postJson("/api/phase20_7/turn", payload);
    const turn = data.turn || {};
    const ticks = turn.tick_trace || [];
    currentTicks = ticks;
    allTicks = [...allTicks, ...ticks].slice(-260);
    selectedTickIndex = allTicks.length ? allTicks.length - 1 : -1;
    // V1: 读服务端自适应心跳节奏 (idle_pacing.interval_seconds)
    const pacing = turn.idle_pacing || {};
    if (pacing.interval_seconds) {
      window._latestIdlePacingSec = pacing.interval_seconds;
    }

    if (turn.reply_text) {
      latestReplyText = turn.reply_text;
      if (idle) {
        // W4: 自发消息气泡 (AP主动说话, 浅金色边框)
        addMessage("ap spontaneous", turn.reply_text);
      } else {
        addMessage("ap", turn.reply_text);
      }
      if ($("autoSpeak").checked) speakLatestReply();
    }
    // S1: AP 回复后把它本轮想象出的内心画面贴进 AP 气泡（后端 C30 红线已过滤：只暴露从状态池 canvas 重建的画面，不会暴露用户原图缩略图）。
    // Bug5 修复: 本轮画了画但 reply_text 为空(或还没有AP气泡)时, 专门开一个图片气泡 — 画作必须发到对话框.
    // 关键修复: inner_pictures 在响应顶层 (data.inner_pictures), 不在 turn 里 —
    // 之前读 turn.inner_pictures 永远为空, 画作从未进过气泡.
    const turnPictures = Array.isArray(data.inner_pictures) ? data.inner_pictures : (Array.isArray(turn.inner_pictures) ? turn.inner_pictures : []);
    if (turnPictures.length && !turn.reply_text) {
      addMessage("ap", turnPictures.some((x) => x.source === "ap_paint_board_commit") ? "画好了,给你看:" : "我想到的画面:");
    }
    appendInnerPicturesToLastApBubble(turnPictures);
    renderDetailInnerPictures(currentTicks);

    if (!idle) {
      clearComposer();
    }

    renderAll(data, { idle });
    appendStructureStream(ticks, { idle });
    updateIdleCadence(ticks, Boolean(turn.reply_text));
  } catch (error) {
    setStatus("请求失败", "sleeping");
    $("runtimeSummary").textContent = `工作台请求失败: ${String(error)}`;
  } finally {
    requestInFlight = false;
    stopProgressPolling();
    if (pendingUserTurn) {
      const queued = pendingUserTurn;
      pendingUserTurn = null;
      window.setTimeout(() => sendTurn({ idle: false, queuedPayload: queued }), 0);
    }
  }
}

function startProgressPolling() {
  stopProgressPolling();
  progressPollSessionId = sessionId;
  $("progressBanner").textContent = "AP 正在整理当前这轮经验流。";
  let ticks = 0;
  const poll = async () => {
    if (!requestInFlight || progressPollSessionId !== sessionId) return;
    try {
      const data = await getJson(`/api/phase20_7/progress?session_id=${encodeURIComponent(sessionId)}`);
      renderProgressStatus(data);
    } catch (_) {
      // 保持等待态，不覆盖真实对话结果
    }
    ticks += 1;
    if (requestInFlight && ticks < 60) {
      progressPollTimer = window.setTimeout(poll, 600);
    }
  };
  progressPollTimer = window.setTimeout(poll, 120);
}

function stopProgressPolling() {
  if (progressPollTimer) window.clearTimeout(progressPollTimer);
  progressPollTimer = null;
  progressPollSessionId = "";
}

function renderProgressStatus(data) {
  if (!data || typeof data !== "object") return;
  const label = String(data.stage_label || data.stage || "处理中");
  const tick = data.tick !== undefined ? `tick ${data.tick}` : "";
  const recent = Array.isArray(data.recent_actions) ? data.recent_actions.slice(-3).map((item) => String(item.label || item.action_label || item.action_type || "")).filter(Boolean) : [];
  const recentText = recent.length ? ` · ${recent.join(" → ")}` : "";
  const suffix = tick ? ` (${tick})` : "";
  $("progressBanner").textContent = `AP 正在: ${label}${suffix}${recentText}`;
  setStatus(`AP 正在: ${label}${suffix}${recentText}`, "running");
  if (Array.isArray(data.recent_actions) && data.recent_actions.length) {
    $("runtimeSummary").textContent = `当前阶段: ${label}${suffix} · 最近动作: ${recentText ? recentText.slice(3) : recent.join(" → ")}`;
  }
}

function renderAll(data, { idle = false } = {}) {
  const turn = data.turn || {};
  const ticks = turn.tick_trace || [];
  const memory = data.memory || [];
  const unclosed = data.unclosed || [];
  const historyTicks = allTicks.length ? allTicks : ticks;
  renderTicks(historyTicks);
  renderMemory(memory);
  renderUnclosed(unclosed);
  renderInnerPicture(historyTicks);
  renderInnerAudio(historyTicks);
  renderThoughtCloud(historyTicks, unclosed);
  renderLearningLoop(historyTicks);
  renderLearningLifecycle(historyTicks);
  renderAuditCharts(historyTicks);
  renderStatus(ticks, memory, unclosed, idle);
  renderSelectedTick();
}

function renderStatus(ticks, memory, unclosed, idle) {
  const latest = ticks[ticks.length - 1] || {};
  const action = latest.selected_action || {};
  const stateCount = (latest.state_pool_top || []).length;
  $("metricTick").textContent = String(latest.tick ?? 0);
  $("metricPool").textContent = String(stateCount);
  $("metricMemory").textContent = String((memory || []).length);
  $("metricUnclosed").textContent = String((unclosed || []).length);

  if (idle && action.action_type === "idle_think") {
    setStatus("闲时思考", "running");
  } else if (idle && action.action_type === "idle_visual_focus") {
    setStatus("闲时看图", "running");
  } else if (idle && action.action_type === "idle_audio_focus") {
    setStatus("闲时听觉", "running");
  } else if (idle && action.action_type === "idle_observe") {
    setStatus(autoIdleTimer ? "低频待机" : "待机", "sleeping");
  } else {
    setStatus(actionNames[action.action_type] || "完成本轮", "");
  }

  const grasp = latest.cstar_packet?.grasp;
  const u = Math.max(0, ...(latest.unclosed_items || []).map((item) => Number(item.u_value || 0)));
  const visual = latest.visual_inner_picture ? "视觉画面已更新" : "本 tick 无视觉画面";
  const audio = latest.audio_inner_sketch ? "内心音频已更新" : "本 tick 无内心音频";
  $("runtimeSummary").textContent = `最新动作: ${actionNames[action.action_type] || action.action_type || "无"} · 把握 ${number(grasp ?? 0)} · 未闭合 ${number(u)} · ${visual} · ${audio}`;
}

function renderTicks(ticks) {
  if (!ticks.length) {
    $("tickList").innerHTML = `<div class="empty-note">还没有 RuntimeTickEvent。</div>`;
    return;
  }
  $("tickList").innerHTML = ticks.map((tick, index) => {
    const action = tick.selected_action || {};
    const selected = index === selectedTickIndex ? " current" : "";
    const b = (tick.b_candidates || []).slice(0, 3).map((item) => `<span class="tag">B ${candidateName(item)} ${number(item.support)}</span>`).join("");
    const learning = learningLoopMetric(tick);
    const runtime = learningStageRuntime(tick);
    const runtimeTags = runtime ? `<span class="tag tag-runtime">阶段 ${esc(runtimeStageName(runtime.dominant_runtime_stage))}</span>` : "";
    const lifecycle = learningObjectLifecycle(tick);
    const lifecycleTags = lifecycle ? `<span class="tag tag-lifecycle">对象 ${esc(shortObjectId(lifecycle.learning_object_id))} · ${esc(lifecycleStageName(lifecycle.current_lifecycle_stage))}</span>` : "";
    const learningTags = learning ? `<span class="tag">学习 ${esc(learningStageName(learning.current_protocol_stage))}</span><span class="tag">${esc(learningTendencyName(learning.dominant_learning_tendency))}</span>` : "";
    const c = [
      ...(tick.c_forward || []).slice(0, 2).map((item) => `<span class="tag">预测 ${candidateName(item)}</span>`),
      ...(tick.c_backward || []).slice(0, 2).map((item) => `<span class="tag">解释 ${candidateName(item)}</span>`),
    ].join("");
    const unclosed = (tick.unclosed_items || []).slice(0, 2).map((item) => `<span class="tag">未闭合 ${esc(item.source_text)} ${number(item.u_value)}</span>`).join("");
    const state = (tick.state_pool_top || []).slice(0, 4).map((item) => esc(readableState(item))).join(" / ");
    return `
      <div class="tick${selected}" data-index="${index}">
        <strong>tick ${esc(tick.tick)} · ${esc(actionNames[action.action_type] || action.action_type || "")}</strong>
        <div>${learningTags}${runtimeTags}${lifecycleTags}${b}${c}${unclosed || ""}</div>
        <div class="kv">草稿: ${esc((tick.draft_grid || {}).visible_text || "空")}</div>
        <div class="kv">状态池: ${state || "空"}</div>
      </div>
    `;
  }).join("");
  $("tickList").querySelectorAll(".tick[data-index]").forEach((node) => {
    node.addEventListener("click", () => {
      selectedTickIndex = Number(node.getAttribute("data-index"));
      renderTicks(allTicks.length ? allTicks : currentTicks);
      renderSelectedTick();
    });
  });
}

function renderSelectedTick() {
  const historyTicks = allTicks.length ? allTicks : currentTicks;
  const tick = historyTicks[selectedTickIndex] || historyTicks[historyTicks.length - 1];
  if (!tick) {
    $("tickReason").textContent = "选择一个 tick 后，这里会解释 AP 的动作来源。";
    $("draftPreview").textContent = "还没有草稿。";
    const draftProcess = $("draftProcess");
    if (draftProcess) draftProcess.innerHTML = "";
    return;
  }
  $("tickReason").innerHTML = explainTick(tick);
  renderLearningLoop([tick]);
  const draft = (tick.draft_grid || {}).visible_text || "";
  $("draftPreview").textContent = draft || "草稿格暂时为空。";
  renderDraftProcess(tick);
  renderTtsStatus(tick);
}

function renderDraftProcess(tick) {
  const host = $("draftProcess");
  if (!host) return;
  const grid = tick?.draft_grid || {};
  const rows = Number(grid.rows || 0);
  const cols = Number(grid.cols || 0);
  const cells = Array.isArray(grid.cells) ? grid.cells : [];
  if (!rows || !cols) {
    host.innerHTML = "";
    return;
  }
  const map = new Map(cells.map((cell) => [`${cell.row}:${cell.col}`, cell]));
  const rowBlocks = [];
  for (let row = 0; row < rows; row += 1) {
    const cellsHtml = [];
    for (let col = 0; col < cols; col += 1) {
      const cell = map.get(`${row}:${col}`);
      const char = cell ? String(cell.char || " ") : " ";
      const tickLabel = cell ? `写于 tick ${cell.tick ?? "?"}` : "空";
      cellsHtml.push(`
        <div class="draft-grid-cell ${char.trim() ? "filled" : "empty"}" title="${esc(tickLabel)}">
          ${char.trim() ? esc(char) : "&nbsp;"}
        </div>
      `);
    }
    rowBlocks.push(`<div class="draft-grid-row" aria-label="草稿第 ${row + 1} 行">${cellsHtml.join("")}</div>`);
  }
  const cellCards = cells.length
    ? cells.slice(0, 24).map((cell) => `
      <div class="draft-process-card">
        <div class="draft-process-head">
          <strong>(${esc(cell.row)}, ${esc(cell.col)})</strong>
          <span>tick ${esc(cell.tick ?? "?")}</span>
        </div>
        <div class="draft-process-char">${esc(cell.char || " ")}</div>
        <div class="draft-process-note">这是 AP 写入草稿格的一个真实单元，不是整句结果。</div>
      </div>
    `).join("")
    : `<div class="empty-note">这个 tick 还没有逐格写入记录。</div>`;
  host.innerHTML = `
    <div class="draft-process-grid">${rowBlocks.join("")}</div>
    <div class="draft-process-cards">${cellCards}</div>
  `;
}

function explainTick(tick) {
  const action = tick.selected_action || {};
  const actionType = action.action_type || "";
  const pieces = [`<p><strong>${esc(actionNames[actionType] || actionType || "未选择动作")}</strong></p>`];

  const inputs = tick.external_inputs || [];
  if (inputs.length) {
    pieces.push(`<p>这一 tick 接到了外部输入: ${inputs.map(inputName).join("、")}。</p>`);
  }

  const receptor = tick.receptor_outputs || [];
  if (receptor.length) {
    pieces.push(`<p>感受器写入了 ${receptor.map(receptorName).join("、")}，这些对象进入状态池和短期结构。</p>`);
  }

  const b = tick.b_candidates || [];
  const forward = tick.c_forward || [];
  const backward = tick.c_backward || [];
  if (b.length) {
    pieces.push(`<p>当前认知召回最强的是 ${candidateName(b[0])}，支持度 ${number(b[0].support)}。</p>`);
  }
  if (forward.length || backward.length) {
    const bits = [];
    if (forward[0]) bits.push(`向后预测 ${candidateName(forward[0])}`);
    if (backward[0]) bits.push(`向前溯源 ${candidateName(backward[0])}`);
    pieces.push(`<p>它同时做了 ${bits.join("，")}，再交给 C* 整合。</p>`);
  }

  const feelings = tick.feelings || {};
  const grasp = tick.cstar_packet?.grasp ?? feelings.grasp ?? feelings.support;
  if (grasp !== undefined) {
    pieces.push(`<p>把握感约 ${number(grasp)}；把握高时更容易写草稿，把握低时更容易请求教学或保留未闭合。</p>`);
  }

  const competition = tick.action_competition || [];
  if (competition.length) {
    const top = competition.slice(0, 4).map((item) => `${actionNames[item.action_type] || item.action_type} ${number(item.drive)}`);
    pieces.push(`<p>行动竞争: ${top.join(" / ")}，最终选中了 ${actionNames[actionType] || actionType}。</p>`);
  }

  const loop = learningLoopMetric(tick);
  if (loop) {
    pieces.push(`<p>学习闭环判断为 <strong>${esc(learningTendencyName(loop.dominant_learning_tendency))}</strong>：反馈 ${number(loop.feedback_only_readiness)} / 教师退场 ${number(loop.teacher_off_readiness)} / 冷重测 ${number(loop.cold_retest_readiness)} / 脚手架 ${number(loop.scaffold_regression_need)}。</p>`);
  }
  const runtime = learningStageRuntime(tick);
  if (runtime) {
    const deltas = runtime.stage_action_deltas || {};
    pieces.push(`<p>10a 学习阶段运行投影: <strong>${esc(runtimeStageName(runtime.dominant_runtime_stage))}</strong>，置信 ${number(runtime.stage_confidence)}；它只调制行动竞争，不直接写答案。</p>`);
    pieces.push(`<p>阶段动作微调: 回复 ${number(deltas.commit_reply)} / 请教 ${number(deltas.request_teacher)} / 复盘 ${number(deltas.idle_think)} / 回读 ${number(deltas.read_draft)}。</p>`);
  }
  const lifecycle = learningObjectLifecycle(tick);
  if (lifecycle) {
    const lifecycleDeltas = lifecycle.lifecycle_action_deltas || {};
    const coldTuning = lifecycle.cold_retest_generalization_tuning || {};
    const memoryRhythm = lifecycle.memory_consolidation_forgetting_rhythm || {};
    pieces.push(`<p>10b 学习对象生命周期: 对象 <strong>${esc(shortObjectId(lifecycle.learning_object_id))}</strong> 走到「${esc(lifecycleStageName(lifecycle.current_lifecycle_stage))}」；复盘 ${esc(lifecycle.review_count)} 次，自测 ${esc(lifecycle.self_test_count)} 次，成功 ${esc(lifecycle.self_test_success_count)} / 失败 ${esc(lifecycle.self_test_failure_count)}。</p>`);
    pieces.push(`<p>生命周期压力: 稳定 ${number(lifecycle.stability)} / 退行 ${number(lifecycle.regression)} / 冷测 ${number(lifecycle.cold_retest_pressure)}；它来自 ExperienceFlow 与 SSP trace，不是新的学习表。</p>`);
    if (coldTuning.active) {
      pieces.push(`<p>10e 冷测泛化调制: 胆量 ${number(coldTuning.generalization_courage)} / 谨慎 ${number(coldTuning.generalization_caution)}；成功 ${esc(coldTuning.cold_success_count ?? 0)} / 失败 ${esc(coldTuning.cold_failure_count ?? 0)}，只调制行动竞争与结构 B 支持。</p>`);
    }
    if (memoryRhythm.active) {
      pieces.push(`<p>10f 记忆节律: 巩固 ${number(memoryRhythm.memory_consolidation)} / 遗忘 ${number(memoryRhythm.forgetting_pressure)} / 复习 ${number(memoryRhythm.review_rhythm_pressure)} / 再巩固 ${number(memoryRhythm.reconsolidation_need)}；它只投影已有复盘、自测、冷测与奖惩痕迹。</p>`);
      pieces.push(`<p>10h 后果把握: 这份节律会轻微传到写草稿、回读、修改和提交；巩固高时更敢写，遗忘/退行高时更谨慎。</p>`);
      pieces.push(`<p>10k 跨 tick 回放: 连续 tick 里，巩固会把“继续写/提交”往上推，遗忘和再巩固会把“回读/修改/停下”往上推。</p>`);
    }
    pieces.push(`<p>生命周期动作微调: 回复 ${number(lifecycleDeltas.commit_reply)} / 请教 ${number(lifecycleDeltas.request_teacher)} / 自想 ${number(lifecycleDeltas.idle_think)} / 修改 ${number(lifecycleDeltas.edit_cell)}。</p>`);
  }
  const draftgridExplanation = tick.selected_action?.draftgrid_action_drive_context || tick.feelings?.draftgrid_action_drive_context || {};
  const draftgridMemory = draftgridExplanation.memory_rhythm_context || {};
  if (Object.keys(draftgridMemory).length) {
    pieces.push(`<p>草稿把握来源: 记忆巩固 ${number(draftgridMemory.memory_rhythm_confidence)} / 记忆防守 ${number(draftgridMemory.memory_rhythm_guard)}；它会轻微影响 read / edit / commit / continue 的后果评估。</p>`);
  }
  const review = idleLearningReview(tick);
  if (review) {
    const pair = review.target_text ? `「${esc(review.source_text || "这个")}」到「${esc(review.target_text)}」` : `「${esc(review.source_text || "这个")}」`;
    const rhythmNote = review.memory_rhythm_context ? ` 记忆节律 ${number(review.memory_rhythm_context.memory_rhythm_confidence || 0)} / ${number(review.memory_rhythm_context.memory_rhythm_guard || 0)}。` : "";
    pieces.push(`<p>闲时复盘正在整理 ${pair}，倾向是 ${esc(learningTendencyName(review.dominant_learning_tendency))}；这是私有短期结构流，不会直接写聊天回复。</p>`);
  }
  const selfTest = idleSelfTest(tick);
  if (selfTest) {
    const rhythmNote = selfTest.memory_rhythm_context ? ` 记忆节律 ${number(selfTest.memory_rhythm_context.memory_rhythm_confidence || 0)} / ${number(selfTest.memory_rhythm_context.memory_rhythm_guard || 0)}。` : "";
    pieces.push(`<p>私有自测把「${esc(selfTest.source_text || "这个")}」召回成「${esc(selfTest.recalled_text || "")}」，期望是「${esc(selfTest.expected_text || "")}」，把握 ${number(selfTest.self_test_grasp)}。${rhythmNote}</p>`);
  }
  const feedbackPacket = selfTestFeedback(tick);
  if (feedbackPacket) {
    pieces.push(`<p>自测反馈进入下一轮复盘：${esc(selfTestFeedbackName(feedbackPacket.feedback_kind))}，错配压力 ${number(feedbackPacket.mismatch_pressure)}；它只调制后继学习倾向。</p>`);
  }

  const unclosed = tick.unclosed_items || [];
  if (unclosed.length) {
    pieces.push(`<p>未闭合感把注意拉回「${esc(unclosed[0].source_text)}」，U=${number(unclosed[0].u_value)}。</p>`);
  }
  if (feelings.narrative_text) {
    pieces.push(`<p>闲时短期结构流继续到: ${esc(feelings.narrative_text)}。</p>`);
  }

  if (tick.visual_inner_picture) {
    pieces.push(`<p>视觉内心画面来自本 tick 的 patch payload 重建，不是整图识别标签。</p>`);
  }
  if (tick.audio_inner_sketch) {
    const audio = tick.audio_inner_sketch;
    pieces.push(`<p>内心音频保留了最近听觉 trace，能量 ${number(audio.inner_energy ?? 0)}；没有把声音识别成语义标签。</p>`);
  }
  if (actionType === "reply_tts_audio") {
    pieces.push(`<p>朗读执行器选择本地 xiaoyi 音色，只记录本地播放意图。</p>`);
  }
  return pieces.join("");
}

function learningLoopMetric(tick) {
  for (const delta of tick.learning_deltas || []) {
    if (delta?.delta_kind === "learning_loop_metrics") return delta;
  }
  return null;
}

function learningProjection(tick) {
  for (const delta of tick.learning_deltas || []) {
    if (delta?.delta_kind === "learning_protocol_projection") return delta;
  }
  return null;
}

function learningStageRuntime(tick) {
  const candidates = [];
  for (const row of tick.action_competition || []) {
    const progression = row?.learning_loop_carryover?.learning_stage_runtime_progression;
    if (progression && typeof progression === "object" && progression.active) {
      candidates.push({ ...progression, _drive: Number(row.drive || 0), _action_type: row.action_type || "" });
    }
  }
  const selectedProgression = tick.selected_action?.learning_loop_carryover?.learning_stage_runtime_progression;
  if (selectedProgression && typeof selectedProgression === "object" && selectedProgression.active) {
    candidates.push({ ...selectedProgression, _drive: 1.0, _action_type: tick.selected_action?.action_type || "" });
  }
  const feelingsProgression = tick.feelings?.learning_loop_carryover?.learning_stage_runtime_progression;
  if (feelingsProgression && typeof feelingsProgression === "object" && feelingsProgression.active) {
    candidates.push({ ...feelingsProgression, _drive: 0.0, _action_type: "feelings" });
  }
  candidates.sort((left, right) => Number(right._drive || 0) - Number(left._drive || 0));
  return candidates[0] || null;
}

function learningObjectLifecycle(tick) {
  const progression = learningStageRuntime(tick);
  const lifecycle = progression?.learning_object_lifecycle;
  return lifecycle && typeof lifecycle === "object" && lifecycle.active ? lifecycle : null;
}

function runtimeStageName(value) {
  return runtimeStageNames[value] || value || "未投影";
}

function lifecycleStageName(value) {
  return lifecycleStageNames[value] || value || "未形成";
}

function shortObjectId(value) {
  const text = String(value || "");
  if (!text) return "未定";
  return text.replace(/^evt::/, "").slice(0, 8);
}

function alignmentWrittenDelta(tick) {
  for (const delta of tick.learning_deltas || []) {
    if (delta?.delta_kind === "experience_alignment_written") return delta;
  }
  return null;
}

function idleLearningReview(tick) {
  const feelings = tick.feelings || {};
  const summary = tick.ssp_active_summary || {};
  const review = feelings.idle_learning_review || summary.idle_learning_review;
  return review && typeof review === "object" && Object.keys(review).length ? review : null;
}

function idleSelfTest(tick) {
  const feelings = tick.feelings || {};
  const summary = tick.ssp_active_summary || {};
  const test = feelings.idle_self_test || summary.idle_self_test;
  return test && typeof test === "object" && Object.keys(test).length ? test : null;
}

function selfTestFeedback(tick) {
  const review = idleLearningReview(tick);
  if (review?.self_test_feedback && typeof review.self_test_feedback === "object" && Object.keys(review.self_test_feedback).length) {
    return review.self_test_feedback;
  }
  const metric = learningLoopMetric(tick);
  const nested = metric?.evidence?.self_test_feedback || metric?.self_test_feedback;
  return nested && typeof nested === "object" && Object.keys(nested).length ? nested : null;
}

function learningStageName(value) {
  return learningStageNames[value] || value || "未投影";
}

function learningTendencyName(value) {
  return learningTendencyNames[value] || value || "未判断";
}

function renderLearningLoop(ticks) {
  const tick = [...ticks].reverse().find((item) => learningLoopMetric(item) && (item.selected_action || {}).action_type !== "reply_tts_audio")
    || [...ticks].reverse().find((item) => learningLoopMetric(item))
    || ticks[ticks.length - 1]
    || {};
  const metric = learningLoopMetric(tick);
  const projection = learningProjection(tick);
  if (!metric) {
    $("learningLoopPanel").className = "learning-loop empty-note";
    $("learningLoopPanel").innerHTML = "等待 learning_loop_metrics。";
    return;
  }
  $("learningLoopPanel").className = "learning-loop";
  const bars = [
    ["feedback", "先听反馈", metric.feedback_only_readiness],
    ["teacher", "自己尝试", metric.teacher_off_readiness],
    ["cold", "冷重测", metric.cold_retest_readiness],
    ["scaffold", "要脚手架", metric.scaffold_regression_need],
  ];
  const evidence = metric.evidence || {};
  $("learningLoopPanel").innerHTML = `
    <div class="learning-loop-header">
      <div>
        <strong>${esc(learningTendencyName(metric.dominant_learning_tendency))}</strong>
        <span>tick ${esc(tick.tick ?? "?")} · ${esc(learningStageName(metric.current_protocol_stage || projection?.current_protocol_stage))}</span>
      </div>
      <span>${esc(actionNames[(tick.selected_action || {}).action_type] || (tick.selected_action || {}).action_type || "")}</span>
    </div>
    <div class="learning-bars">
      ${bars.map(([kind, label, raw]) => {
        const value = Math.max(0, Math.min(1, Number(raw || 0)));
        return `
          <div class="learning-bar ${kind}">
            <label>${esc(label)}</label>
            <div class="learning-track"><div class="learning-fill" style="--learning-value:${Math.round(value * 100)}%"></div></div>
            <span>${number(value)}</span>
          </div>
        `;
      }).join("")}
    </div>
    <div class="learning-evidence">
      <span>B ${number(evidence.b_support)}</span>
      <span>C* ${number(evidence.cstar_grasp)}</span>
      <span>反馈 ${number(evidence.teacher_signal)}</span>
      <span>请教 ${number(evidence.request_scaffold_signal)}</span>
    </div>
  `;
}

function renderLearningLifecycle(ticks) {
  const panel = $("learningLifecyclePanel");
  const state = learningLifecycleState(ticks);
  if (!state.hasAny) {
    panel.className = "learning-lifecycle empty-note";
    panel.innerHTML = "等待真实教学、复盘、自测和反馈稳定 tick。";
    return;
  }
  panel.className = "learning-lifecycle";
  const steps = [
    lifecycleStep("教学/反馈", state.feedback, (tick) => feedbackStepHtml(tick)),
    lifecycleStep("闲时复盘", state.review, (tick) => reviewStepHtml(tick)),
    lifecycleStep("私有自测", state.selfTest, (tick) => selfTestStepHtml(tick)),
    lifecycleStep("反馈稳定", state.stabilize, (tick) => stabilizeStepHtml(tick)),
  ];
  const activeCount = [state.feedback, state.review, state.selfTest, state.stabilize].filter(Boolean).length;
  const source = state.latestSourceText || "等待真实 cue";
  const target = state.latestTargetText || "等待真实 target";
  const lifecycleSummary = state.lifecycle ? learningObjectLifecycleSummaryHtml(state.lifecycle, state.lifecycleTick) : "";
  panel.innerHTML = `
    ${lifecycleSummary}
    <div class="lifecycle-head">
      <strong>${esc(activeCount)}/4 段已出现</strong>
      <span>${esc(source)} -> ${esc(target)}</span>
    </div>
    <div class="lifecycle-chain">${steps.join("")}</div>
  `;
}

function learningObjectLifecycleSummaryHtml(lifecycle, tick) {
  const stages = Array.isArray(lifecycle.lifecycle_stages)
    ? lifecycle.lifecycle_stages
    : ["taught", "reviewed", "self_tested", "adjusted_after_feedback", "retested", "teacher_exit_ready", "cold_retest_ready"];
  const currentIndex = Number(lifecycle.lifecycle_stage_index || 0);
  const tickLabel = tick ? `tick ${esc(tick.tick ?? "?")}` : "tick ?";
  const objectLabel = shortObjectId(lifecycle.learning_object_id);
  const coldWindow = lifecycle.long_interval_cold_retest_window || {};
  const coldTuning = lifecycle.cold_retest_generalization_tuning || {};
  const memoryRhythm = lifecycle.memory_consolidation_forgetting_rhythm || {};
  const lifecycleActionDeltas = lifecycle.lifecycle_action_deltas || {};
  const recentReviewTicks = Array.isArray(lifecycle.recent_review_ticks) ? lifecycle.recent_review_ticks : [];
  const recentSelfTestTicks = Array.isArray(lifecycle.recent_self_test_ticks) ? lifecycle.recent_self_test_ticks : [];
  const drilldownActions = [
    "request_teacher",
    "maintain_unclosed",
    "write_cell",
    "commit_reply",
    "idle_think",
    "integrate_feedback",
    "read_draft",
    "edit_cell",
    "stop_generating",
  ];
  const bars = [
    ["stability", "稳定", lifecycle.stability],
    ["regression", "退行", lifecycle.regression],
    ["cold", "冷测", lifecycle.cold_retest_pressure],
    ["stability", "泛化胆量", coldTuning.generalization_courage],
    ["regression", "泛化谨慎", coldTuning.generalization_caution],
    ["stability", "记忆巩固", memoryRhythm.memory_consolidation],
    ["regression", "遗忘压力", memoryRhythm.forgetting_pressure],
    ["cold", "复习节律", memoryRhythm.review_rhythm_pressure],
    ["regression", "再巩固", memoryRhythm.reconsolidation_need],
  ];
  return `
    <div class="lifecycle-object-summary">
      <div class="lifecycle-object-title">
        <strong>学习对象 ${esc(objectLabel)}</strong>
        <span>${tickLabel} · ${esc(lifecycleStageName(lifecycle.current_lifecycle_stage))}</span>
      </div>
      <div class="lifecycle-object-meta">
        <span>复盘 ${esc(lifecycle.review_count ?? 0)}</span>
        <span>自测 ${esc(lifecycle.self_test_count ?? 0)}</span>
        <span>成功 ${esc(lifecycle.self_test_success_count ?? 0)}</span>
        <span>失败 ${esc(lifecycle.self_test_failure_count ?? 0)}</span>
        ${coldWindow.active ? `<span>长间隔 ${esc(coldWindow.alignment_age_ticks ?? 0)} tick</span>` : ""}
      </div>
      <div class="lifecycle-stage-rail">
        ${stages.map((stage, index) => `
          <span class="${index <= currentIndex ? "active" : ""}" title="${esc(lifecycleStageName(stage))}">${esc(index + 1)}</span>
        `).join("")}
      </div>
      <div class="lifecycle-pressure-bars">
        ${bars.map(([kind, label, raw]) => {
          const value = Math.max(0, Math.min(1, Number(raw || 0)));
          return `
            <div class="lifecycle-pressure ${kind}">
              <label>${esc(label)}</label>
              <div><span style="--lifecycle-value:${Math.round(value * 100)}%"></span></div>
              <b>${number(value)}</b>
            </div>
          `;
        }).join("")}
      </div>
      ${coldWindow.active ? `<div class="lifecycle-trace-note">冷测窗口 ${number(coldWindow.retest_need)} · 距自测 ${esc(coldWindow.self_test_gap_ticks ?? 0)} tick · 距复盘 ${esc(coldWindow.review_gap_ticks ?? 0)} tick。</div>` : ""}
      ${coldTuning.active ? `<div class="lifecycle-trace-note">10e 冷测泛化: 胆量 ${number(coldTuning.generalization_courage)} / 谨慎 ${number(coldTuning.generalization_caution)}，行动调制 回复 ${number((coldTuning.action_deltas || {}).commit_reply)} / 请教 ${number((coldTuning.action_deltas || {}).request_teacher)}。</div>` : ""}
      ${memoryRhythm.active ? `<div class="lifecycle-trace-note">10f 记忆节律: 巩固 ${number(memoryRhythm.memory_consolidation)} / 遗忘 ${number(memoryRhythm.forgetting_pressure)} / 复习 ${number(memoryRhythm.review_rhythm_pressure)} / 再巩固 ${number(memoryRhythm.reconsolidation_need)}。</div>` : ""}
      ${memoryRhythm.active ? `<div class="lifecycle-trace-note">10h 后果把握: 节律会传到 read / edit / commit / continue，影响“敢不敢继续写”和“要不要先回读”。</div>` : ""}
      ${memoryRhythm.active ? `<div class="lifecycle-trace-note">10k 跨 tick 回放: 往前几个 tick 看，巩固升高时更容易看到 commit/continue；遗忘升高时更容易看到 read/edit/stop。</div>` : ""}
      ${memoryRhythm.active ? `<div class="lifecycle-trace-note">10l 同一时间线: 生命周期卡片和 tick 回放看的是同一组 memory rhythm 曲线，不是两套不同解释。</div>` : ""}
      <div class="lifecycle-drilldown">
        <div class="lifecycle-drilldown-head">
          <strong>10m 更深下钻</strong>
          <span>直接看最近复盘、自测和动作调制，仍然只读已有 trace。</span>
        </div>
        <div class="lifecycle-drilldown-grid">
          <div class="lifecycle-drilldown-metric">
            <label>奖励</label>
            <b>${number(lifecycle.reward_pressure)}</b>
          </div>
          <div class="lifecycle-drilldown-metric">
            <label>惩罚</label>
            <b>${number(lifecycle.punish_pressure)}</b>
          </div>
          <div class="lifecycle-drilldown-metric">
            <label>稳定</label>
            <b>${number(lifecycle.stability)}</b>
          </div>
          <div class="lifecycle-drilldown-metric">
            <label>退行</label>
            <b>${number(lifecycle.regression)}</b>
          </div>
          <div class="lifecycle-drilldown-metric">
            <label>冷测</label>
            <b>${number(lifecycle.cold_retest_pressure)}</b>
          </div>
          <div class="lifecycle-drilldown-metric">
            <label>教师反馈</label>
            <b>${esc(lifecycle.teacher_feedback_target_count ?? 0)}</b>
          </div>
        </div>
        <div class="lifecycle-drilldown-row">
          <span>最近复盘 tick</span>
          <div class="lifecycle-chip-row">
            ${recentReviewTicks.length
              ? recentReviewTicks.map((tick) => `<span class="lifecycle-chip">tick ${esc(tick)}</span>`).join("")
              : `<span class="lifecycle-chip muted">暂无</span>`}
          </div>
        </div>
        <div class="lifecycle-drilldown-row">
          <span>最近自测 tick</span>
          <div class="lifecycle-chip-row">
            ${recentSelfTestTicks.length
              ? recentSelfTestTicks.map((tick) => `<span class="lifecycle-chip">tick ${esc(tick)}</span>`).join("")
              : `<span class="lifecycle-chip muted">暂无</span>`}
          </div>
        </div>
        <div class="lifecycle-drilldown-actions">
          ${drilldownActions.map((action) => {
            const delta = Number(lifecycleActionDeltas[action] || 0);
            const tone = delta >= 0 ? "positive" : "negative";
            return `
              <div class="lifecycle-drilldown-action ${tone}">
                <span>${esc(actionNames[action] || action)}</span>
                <b>${number(delta)}</b>
              </div>
            `;
          }).join("")}
        </div>
      </div>
      <div class="lifecycle-trace-note">只读 RuntimeTickEvent / ExperienceFlow / SSP trace，不新增认知实体。</div>
    </div>
  `;
}

function learningLifecycleState(ticks) {
  const state = {
    feedback: null,
    review: null,
    selfTest: null,
    stabilize: null,
    runtime: null,
    lifecycle: null,
    lifecycleTick: null,
    latestSourceText: "",
    latestTargetText: "",
    hasAny: false,
  };
  for (const tick of ticks || []) {
    const action = tick.selected_action || {};
    const metric = learningLoopMetric(tick);
    const feedbackDelta = alignmentWrittenDelta(tick);
    if (feedbackDelta || action.action_type === "integrate_feedback" || metric?.evidence?.teacher_signal > 0) {
      state.feedback = tick;
      state.hasAny = true;
    }
    const review = idleLearningReview(tick);
    if (review) {
      state.review = tick;
      state.hasAny = true;
      state.latestSourceText = review.source_text || state.latestSourceText;
      state.latestTargetText = review.target_text || state.latestTargetText;
    }
    const test = idleSelfTest(tick);
    if (test) {
      state.selfTest = tick;
      state.hasAny = true;
      state.latestSourceText = test.source_text || state.latestSourceText;
      state.latestTargetText = test.expected_text || state.latestTargetText;
    }
    const feedback = selfTestFeedback(tick);
    if (feedback) {
      state.stabilize = tick;
      state.hasAny = true;
    }
    const runtime = learningStageRuntime(tick);
    if (runtime) {
      state.runtime = runtime;
      state.hasAny = true;
    }
    const lifecycle = learningObjectLifecycle(tick);
    if (lifecycle) {
      state.lifecycle = lifecycle;
      state.lifecycleTick = tick;
      state.hasAny = true;
    }
  }
  return state;
}

function lifecycleStep(label, tick, body) {
  const active = tick ? " active" : "";
  const tickLabel = tick ? `tick ${esc(tick.tick ?? "?")}` : "等待真实 tick";
  return `
    <div class="lifecycle-step${active}">
      <div class="lifecycle-step-title">
        <strong>${esc(label)}</strong>
        <span>${tickLabel}</span>
      </div>
      <div class="lifecycle-step-body">${tick ? body(tick) : "还没有对应 RuntimeTickEvent。"}</div>
    </div>
  `;
}

function feedbackStepHtml(tick) {
  const metric = learningLoopMetric(tick) || {};
  const evidence = metric.evidence || {};
  const delta = alignmentWrittenDelta(tick) || {};
  const attribution = delta.backward_attribution || {};
  const recovered = delta.recovered_target ? ` · 追溯到 ${delta.recovered_target_kind || "近期对象"}` : "";
  const cause = attribution.cause_grasp !== undefined ? ` · 溯源把握 ${number(attribution.cause_grasp)}` : "";
  return `
    <div>动作: ${esc(actionNames[(tick.selected_action || {}).action_type] || (tick.selected_action || {}).action_type || "反馈")}</div>
    <div>教师信号 ${number(evidence.teacher_signal ?? 1)}${esc(recovered)}${esc(cause)}</div>
  `;
}

function reviewStepHtml(tick) {
  const review = idleLearningReview(tick) || {};
  return `
    <div>cue: ${esc(review.source_text || "未记录")}</div>
    <div>目标: ${esc(review.target_text || "未记录")}</div>
    <div>${esc(learningTendencyName(review.dominant_learning_tendency))} · 退场 ${number(review.teacher_off_readiness)} · 脚手架 ${number(review.scaffold_regression_need)}</div>
  `;
}

function selfTestStepHtml(tick) {
  const test = idleSelfTest(tick) || {};
  const match = test.match_score ?? 0;
  return `
    <div>期望: ${esc(test.expected_text || "未记录")}</div>
    <div>回忆: ${esc(test.recalled_text || "未记录")}</div>
    <div>把握 ${number(test.self_test_grasp)} · 匹配 ${number(match)} · ${esc(selfTestKindName(test.self_test_kind))}</div>
  `;
}

function stabilizeStepHtml(tick) {
  const packet = selfTestFeedback(tick) || {};
  const review = idleLearningReview(tick) || {};
  return `
    <div>${esc(selfTestFeedbackName(packet.feedback_kind))} · 自测把握 ${number(packet.self_test_grasp)}</div>
    <div>退场 ${number(review.teacher_off_readiness)} · 冷测 ${number(review.cold_retest_readiness)} · 回脚手架 ${number(review.scaffold_regression_need)}</div>
    <div>只调制后继倾向: ${packet.writes_answer_directly === false ? "是" : "未知"}</div>
  `;
}

function selfTestKindName(value) {
  if (value === "teacher_off_self_test") return "教师退场自测";
  if (value === "cold_retest_self_test") return "冷重测自测";
  return value || "自测";
}

function selfTestFeedbackName(value) {
  if (value === "self_test_success") return "自测成功，学习趋稳";
  if (value === "self_test_failure") return "自测失败，回到脚手架";
  return value || "等待反馈";
}

function renderInnerAudio(ticks) {
  const tick = [...ticks].reverse().find((item) => item.audio_inner_sketch);
  if (!tick) {
    $("innerAudio").className = "inner-audio empty";
    $("innerAudio").innerHTML = "等待听觉 tick";
    return;
  }
  const audio = tick.audio_inner_sketch || {};
  const energy = Number(audio.inner_energy || 0);
  const duration = audio.duration_ms === null || audio.duration_ms === undefined ? "未知" : `${number(audio.duration_ms, 1)} ms`;
  $("innerAudio").className = "inner-audio";
  $("innerAudio").innerHTML = `
    <div>tick ${esc(tick.tick)} · ${esc(audio.source || "audio_inner_sketch")}</div>
    <div class="kv">时长 ${esc(duration)} · 内心能量 ${number(energy)}</div>
    <div class="kv">语义标签: ${audio.semantic_label ? esc(audio.semantic_label) : "无"}</div>
    <div class="bar" style="--audio-energy:${Math.max(0, Math.min(100, energy * 100))}%"></div>
  `;
}

// S1: 把本轮 inner_pictures 贴进 AP 最近一条回复气泡。
// 后端 _inner_picture_urls_from_turn 已把 visual_inner_picture 渲染成可显 URL，
// 并严格过滤：只保留 rendered_from_state_pool_canvas=True 且 raw_source_asset_used_for_render=False，
// 所以这里展示的绝非用户原图，而是 AP 自己从状态池视觉 SA 重建的"想象画面"，
// 或者真正落到画板上的画（source=ap_paint_board_commit，fable5 第二层绘画 v1）。
function appendInnerPicturesToLastApBubble(pictures) {
  if (!Array.isArray(pictures) || !pictures.length) return;
  const log = $("chatLog");
  if (!log) return;
  const apMessages = log.querySelectorAll(".message.ap, .message.ap.spontaneous");
  const lastAp = apMessages[apMessages.length - 1];
  if (!lastAp) return;
  if (lastAp.querySelector(".ap-inner-picture-row")) {
    // 该气泡已有图 — 开一个新的图片专用气泡, 画作绝不静默丢弃 (Bug5)
    addMessage("ap", pictures.some((x) => String(x.source||"") === "ap_paint_board_commit") ? "画好了,给你看:" : "我想到的画面:");
    const msgs = log.querySelectorAll(".message.ap, .message.ap.spontaneous");
    return appendInnerPicturesToBubble(msgs[msgs.length - 1], pictures);
  }
  return appendInnerPicturesToBubble(lastAp, pictures);
}

function appendInnerPicturesToBubble(lastAp, pictures) {
  if (!lastAp) return;
  const row = document.createElement("div");
  row.className = "ap-inner-picture-row";
  row.setAttribute("aria-label", "AP 本轮的内心画面与画作");
  pictures.slice(0, 4).forEach((pic) => {
    const url = String(pic.url || "");
    if (!url) return;
    const source = String(pic.source || "");
    const isPaintingCommit = source === "ap_paint_board_commit";
    const wrap = document.createElement("figure");
    wrap.className = "ap-inner-picture-item" + (isPaintingCommit ? " painting" : "");
    const img = document.createElement("img");
    img.alt = isPaintingCommit ? "AP 画的画" : "AP 想象中的画面";
    img.src = url;
    img.loading = "lazy";
    if (isPaintingCommit) {
      img.title = "tick " + (pic.tick ?? "?") + " · AP 把想象投影到画板，一个轮廓一个轮廓地画出来";
    } else {
      img.title = "tick " + (pic.tick ?? "?") + " · AP 从状态池 SA 重建的内心画面";
    }
    wrap.appendChild(img);
    const figcap = document.createElement("figcaption");
    if (isPaintingCommit) {
      figcap.innerHTML = "它画的 · 一个轮廓一个轮廓地投影到画板 · 先看过才能想象才能画";
    } else {
      figcap.textContent = "它把想象中的画面呈现给你 · clarity " + Number(pic.clarity_coverage || 0).toFixed(2);
    }
    wrap.appendChild(figcap);
    row.appendChild(wrap);
  });
  if (!row.children.length) return;
  lastAp.appendChild(row);
  log.scrollTop = log.scrollHeight;
}

// S3: 详情页"AP 的想象画面"区块 — 收齐本轮所有可显 inner_picture URL。
function renderDetailInnerPictures(ticks) {
  // P3: 想象画面面板已被"AP 的画板"回放面板替代(首页已有内心画面, 详情页不重复).
  // 容器保留(hidden)但不再渲染, 数据由 collectReplayDataFromTicks 消费.
  const host = $("detailInnerPictures");
  if (!host) return;
  host.hidden = true;
  if (true) return;
  if (!Array.isArray(ticks) || !ticks.length) {
    host.innerHTML = '';
    return;
  }
  const seen = new Set();
  const cards = [];
  for (const tick of ticks) {
    const vip = tick.visual_inner_picture;
    if (!vip || !vip.rendered_from_state_pool_canvas) continue;
    if (vip.raw_source_asset_used_for_render) continue;
    const rawPath = String(vip.path || "");
    if (!rawPath || seen.has(rawPath)) continue;
    seen.add(rawPath);
    const url = mediaUrl(rawPath);
    if (!url) continue;
    cards.push({
      url,
      tick: tick.tick,
      source: String(vip.source || ""),
      clarity: Number(vip.clarity_coverage || 0),
    });
    if (cards.length >= 6) break;
  }
  if (!cards.length) {
    host.innerHTML = '<div class="empty-note">这个会话刚开始，AP 还没产出可显示的内心画面。先教它"画一个苹果"再问"画苹果"，召回那一刻会出现这里。</div>';
    return;
  }
  // 让 commit PNG (它真画的画) 排最前,再后面是想象重建画面 — 详情页第一眼先看到它画的画。
  const STABLE = { "ap_paint_board_commit": 0, "sensory_canvas_patch_payload": 1, visual_imagination_recall: 2 };
  cards.sort((a, b) => (STABLE[a.source] ?? 9) - (STABLE[b.source] ?? 9) || a.tick - b.tick);
  host.innerHTML = cards.map((c) => {
    const isPainting = c.source === "ap_paint_board_commit";
    const cardCls = "inner-picture-card" + (isPainting ? " painting" : "");
    const alt = isPainting ? "AP 画的画" : "AP 想象中的画面";
    const title = "tick " + c.tick + " · " + c.source + " · clarity " + c.clarity.toFixed(2);
    const cap = isPainting
      ? "tick " + c.tick + " · 它画的<br>AP 把想象投影到画板，一个轮廓一个轮廓地画；先看过才能想象才能画。"
      : "tick " + c.tick + " · " + c.source + "<br>clarity " + c.clarity.toFixed(2) + " — AP 从状态池视觉 SA 重建的内心画面，不是原图。";
    return '<figure class="' + cardCls + '">'
      + '<img alt="' + alt + '" src="' + c.url + '" loading="lazy" title="' + title + '" />'
      + '<figcaption>' + cap + '</figcaption>'
    + '</figure>';
  }).join("");
}

function renderInnerPicture(ticks) {
  // Bug1 修复: 首页内心画面 = 带视焦点的视觉 SA 汇总重建 (感知/想象来源);
  // 画板产物 (ap_paint_board_step/commit) 只在详情页"AP 的画板"展示, 不占用此面板.
  const isBoardSource = (s) => String(s || "").startsWith("ap_paint_board");
  const tick = [...ticks].reverse().find((item) => item.visual_inner_picture?.path && !isBoardSource(item.visual_inner_picture.source));
  if (tick) {
    lastInnerPictureTick = tick;
  }
  const visibleTick = tick || lastInnerPictureTick;
  if (!visibleTick) {
    $("innerPicture").className = "inner-picture empty";
    $("innerPicture").innerHTML = "等待视觉 tick";
    return;
  }
  const picture = visibleTick.visual_inner_picture;
  $("innerPicture").className = "inner-picture";
  $("innerPicture").innerHTML = `<img alt="AP 内心画面重建" src="${esc(mediaUrl(picture.path))}" title="tick ${esc(visibleTick.tick)} · ${esc(picture.source || "visual_inner_picture")}" />`;
}

function renderThoughtCloud(ticks, unclosedItems) {
  const latest = [...ticks].reverse().find((tick) => (tick.state_pool_top || []).length)
    || ticks[ticks.length - 1]
    || {};
  const thoughts = [];
  for (const item of latest.state_pool_top || []) {
    const energy = Number(item.A || 0) + Number(item.R || 0) + Number(item.V || 0);
    const pressure = Number(item.P || 0);
    thoughts.push({
      text: readableState(item),
      size: 24 + Math.min(50, energy * 18),
      bias: Number(item.R || 0) - Number(item.V || 0),
      energy,
      pressure,
    });
  }
  for (const item of (latest.b_candidates || []).slice(0, 3)) {
    thoughts.push({
      text: `召回 ${candidateName(item)}`,
      size: 30 + Number(item.support || 0) * 24,
      bias: 0.2,
      energy: Number(item.support || 0),
      pressure: Number(item.support || 0) * 0.7,
    });
  }
  for (const item of (latest.c_forward || []).slice(0, 3)) {
    thoughts.push({
      text: `预测 ${candidateName(item)}`,
      size: 26 + Number(item.support || 0) * 22,
      bias: 0.1,
      energy: Number(item.support || 0.35),
      pressure: Number(item.support || 0.35) * 0.55,
    });
  }
  for (const item of (latest.c_backward || []).slice(0, 3)) {
    thoughts.push({
      text: `归因 ${candidateName(item)}`,
      size: 26 + Number(item.cause_grasp || item.support || 0) * 22,
      bias: -0.05,
      energy: Number(item.cause_grasp || item.support || 0.35),
      pressure: Number(item.cause_grasp || item.support || 0.35) * 0.58,
    });
  }
  for (const item of (unclosedItems || []).slice(0, 3)) {
    thoughts.push({
      text: `还没想明白: ${item.source_text}`,
      size: 34 + Number(item.u_value || 0) * 34,
      bias: -0.4,
      energy: Number(item.u_value || 0),
      pressure: -Number(item.u_value || 0),
    });
  }
  if (!thoughts.length) {
    $("thoughtCloud").innerHTML = `<div class="empty-note">状态池暂时没有可显示的想法对象。</div>`;
    return;
  }
  const positioned = placeThoughts(thoughts.slice(0, 14));
  $("thoughtCloud").innerHTML = positioned.map((thought, index) => {
    const hue = thought.bias >= 0 ? 204 : 36;
    const sat = 35 + Math.min(45, Math.abs(thought.bias) * 60);
    const alpha = 0.52 + Math.min(0.34, thought.energy * 0.12);
    const label = `${thought.text}\n能量 ${number(thought.energy)} · 认知压 ${number(thought.pressure)}`;
    return `<span class="thought-node" title="${esc(label)}" style="left:${thought.x}%;top:${thought.y}%;font-size:${10 + Math.min(4.8, thought.energy * 0.85)}px;width:${thought.size}px;height:${thought.size}px;background:hsla(${hue}, ${sat}%, 65%, ${alpha});animation-delay:-${index * 0.31}s;">${esc(thought.text)}</span>`;
  }).join("");
}

function placeThoughts(thoughts) {
  const angles = [0, 55, 110, 165, 220, 275, 330, 28, 83, 138];
  return thoughts.map((thought, index) => {
    const pressureAbs = Math.min(1.8, Math.abs(Number(thought.pressure || 0)));
    const radius = Math.max(7, 39 - pressureAbs * 17 + (index % 4) * 4);
    const angle = (angles[index % angles.length] * Math.PI) / 180;
    return {
      ...thought,
      x: Math.round(Math.max(14, Math.min(86, 50 + Math.cos(angle) * radius)) * 10) / 10,
      y: Math.round(Math.max(16, Math.min(84, 50 + Math.sin(angle) * radius * 0.72)) * 10) / 10,
    };
  });
}

function renderAuditCharts(ticks) {
  const fullSeries = [
    {
      title: "状态池对象",
      values: ticks.map((tick) => (tick.state_pool_top || []).length),
      tickLabels: ticks.map((tick) => tick.tick ?? "?"),
      color: "#4776a8",
    },
    {
      title: "草稿长度",
      values: ticks.map((tick) => Number((tick.draft_grid || {}).occupied_cells || 0)),
      tickLabels: ticks.map((tick) => tick.tick ?? "?"),
      color: "#6aa37b",
    },
    {
      title: "未闭合 U",
      values: ticks.map((tick) => Math.max(0, ...(tick.unclosed_items || []).map((item) => Number(item.u_value || 0)))),
      tickLabels: ticks.map((tick) => tick.tick ?? "?"),
      color: "#c08839",
    },
    {
      title: "运行耗时 ms",
      values: ticks.map((tick) => totalTiming(tick.timings_ms || {})),
      tickLabels: ticks.map((tick) => tick.tick ?? "?"),
      color: "#9a6ab8",
    },
    {
      title: "视觉清晰度",
      values: ticks.map((tick) => {
        const receptor = (tick.receptor_outputs || []).find((item) => item.clarity_coverage !== undefined);
        return Number(receptor?.clarity_coverage || 0);
      }),
      tickLabels: ticks.map((tick) => tick.tick ?? "?"),
      color: "#d06c63",
    },
    {
      title: "内心音频",
      values: ticks.map((tick) => Number((tick.audio_inner_sketch || {}).inner_energy || 0)),
      tickLabels: ticks.map((tick) => tick.tick ?? "?"),
      color: "#6aa37b",
    },
    {
      title: "学习:反馈",
      values: ticks.map((tick) => Number(learningLoopMetric(tick)?.feedback_only_readiness || 0)),
      tickLabels: ticks.map((tick) => tick.tick ?? "?"),
      color: "#6aa37b",
    },
    {
      title: "学习:退场",
      values: ticks.map((tick) => Number(learningLoopMetric(tick)?.teacher_off_readiness || 0)),
      tickLabels: ticks.map((tick) => tick.tick ?? "?"),
      color: "#4776a8",
    },
    {
      title: "学习:冷测",
      values: ticks.map((tick) => Number(learningLoopMetric(tick)?.cold_retest_readiness || 0)),
      tickLabels: ticks.map((tick) => tick.tick ?? "?"),
      color: "#9a6ab8",
    },
    {
      title: "学习:脚手架",
      values: ticks.map((tick) => Number(learningLoopMetric(tick)?.scaffold_regression_need || 0)),
      tickLabels: ticks.map((tick) => tick.tick ?? "?"),
      color: "#c08839",
    },
    {
      title: "自测把握",
      values: ticks.map((tick) => Number(idleSelfTest(tick)?.self_test_grasp || selfTestFeedback(tick)?.self_test_grasp || 0)),
      tickLabels: ticks.map((tick) => tick.tick ?? "?"),
      color: "#2f8f89",
    },
    {
      title: "反馈稳定",
      values: ticks.map((tick) => {
        const packet = selfTestFeedback(tick);
        if (!packet) return 0;
        return packet.feedback_kind === "self_test_success" ? 1 : Math.max(0.18, Number(packet.mismatch_pressure || 0));
      }),
      tickLabels: ticks.map((tick) => tick.tick ?? "?"),
      color: "#d06c63",
    },
    {
      title: "对象:稳定",
      values: ticks.map((tick) => Number(learningObjectLifecycle(tick)?.stability || 0)),
      tickLabels: ticks.map((tick) => tick.tick ?? "?"),
      color: "#6aa37b",
    },
    {
      title: "对象:退行",
      values: ticks.map((tick) => Number(learningObjectLifecycle(tick)?.regression || 0)),
      tickLabels: ticks.map((tick) => tick.tick ?? "?"),
      color: "#d06c63",
    },
    {
      title: "对象:复盘数",
      values: ticks.map((tick) => Number(learningObjectLifecycle(tick)?.review_count || 0)),
      tickLabels: ticks.map((tick) => tick.tick ?? "?"),
      color: "#4776a8",
    },
    {
      title: "对象:自测数",
      values: ticks.map((tick) => Number(learningObjectLifecycle(tick)?.self_test_count || 0)),
      tickLabels: ticks.map((tick) => tick.tick ?? "?"),
      color: "#2f8f89",
    },
    {
      title: "对象:冷测窗",
      values: ticks.map((tick) => Number(learningObjectLifecycle(tick)?.long_interval_cold_retest_window?.retest_need || 0)),
      tickLabels: ticks.map((tick) => tick.tick ?? "?"),
      color: "#9a6ab8",
    },
    {
      title: "对象:泛化胆量",
      values: ticks.map((tick) => Number(learningObjectLifecycle(tick)?.cold_retest_generalization_tuning?.generalization_courage || 0)),
      tickLabels: ticks.map((tick) => tick.tick ?? "?"),
      color: "#6aa37b",
    },
    {
      title: "对象:泛化谨慎",
      values: ticks.map((tick) => Number(learningObjectLifecycle(tick)?.cold_retest_generalization_tuning?.generalization_caution || 0)),
      tickLabels: ticks.map((tick) => tick.tick ?? "?"),
      color: "#d06c63",
    },
    {
      title: "对象:记忆巩固·历史时间线",
      values: ticks.map((tick) => Number(learningObjectLifecycle(tick)?.memory_consolidation_forgetting_rhythm?.memory_consolidation || 0)),
      tickLabels: ticks.map((tick) => tick.tick ?? "?"),
      color: "#6aa37b",
    },
    {
      title: "对象:遗忘压力·历史时间线",
      values: ticks.map((tick) => Number(learningObjectLifecycle(tick)?.memory_consolidation_forgetting_rhythm?.forgetting_pressure || 0)),
      tickLabels: ticks.map((tick) => tick.tick ?? "?"),
      color: "#d06c63",
    },
    {
      title: "对象:复习节律·历史时间线",
      values: ticks.map((tick) => Number(learningObjectLifecycle(tick)?.memory_consolidation_forgetting_rhythm?.review_rhythm_pressure || 0)),
      tickLabels: ticks.map((tick) => tick.tick ?? "?"),
      color: "#4776a8",
    },
    {
      title: "对象:再巩固·历史时间线",
      values: ticks.map((tick) => Number(learningObjectLifecycle(tick)?.memory_consolidation_forgetting_rhythm?.reconsolidation_need || 0)),
      tickLabels: ticks.map((tick) => tick.tick ?? "?"),
      color: "#9a6ab8",
    },
    {
      title: "距自测tick",
      values: ticks.map((tick) => Number(learningObjectLifecycle(tick)?.long_interval_cold_retest_window?.self_test_gap_ticks || 0)),
      tickLabels: ticks.map((tick) => tick.tick ?? "?"),
      color: "#c08839",
    },
  ];
  // Bug2: 去掉全 0 噪声曲线——某条曲线在这段 ticks 全是 0 时不再渲染，
  // 避免满屏无意义的直线把真实有信号的曲线挤到看不见。
  // tickLabels 大家都一样，从第一条取一份复用即可。
  const tickLabels = ticks.map((tick) => tick.tick ?? "?");
  const series = fullSeries
    .map((item) => ({ ...item, tickLabels }))
    .filter((item) => item.values.some((value) => Math.abs(Number(value || 0)) > 1e-9));
  if (!series.length) {
    $("auditCharts").innerHTML = `<div class="empty-note">最近这段 ticks 还没产生可量化的认知曲线，先去对话页喂几轮真实输入。</div>`;
    return;
  }
  $("auditCharts").innerHTML = series.map((item, index) => renderChart(item, index)).join("");
  $("auditCharts").querySelectorAll(".chart").forEach((chart) => {
    const tooltip = chart.querySelector(".chart-tooltip");
    chart.addEventListener("mousemove", (event) => {
      if (!tooltip) return;
      const rect = chart.getBoundingClientRect();
      const values = JSON.parse(chart.getAttribute("data-values") || "[]");
      const labels = JSON.parse(chart.getAttribute("data-labels") || "[]");
      const index = Math.max(0, Math.min(values.length - 1, Math.round(((event.clientX - rect.left) / rect.width) * (values.length - 1))));
      tooltip.textContent = `tick ${labels[index] ?? index + 1}: ${number(values[index], 3)}`;
      tooltip.style.left = `${event.clientX - rect.left + 8}px`;
      tooltip.style.top = `${event.clientY - rect.top - 8}px`;
      tooltip.style.display = "block";
    });
    chart.addEventListener("mouseleave", () => {
      if (tooltip) tooltip.style.display = "none";
    });
  });
}

function renderChart({ title, values, tickLabels, color }, chartIndex = 0) {
  const clipId = `auditClip${chartIndex}`;
  const safeValues = values.length ? values : [0];
  const rawMax = Math.max(...safeValues, 0.001);
  const rawMin = Math.min(...safeValues, 0);
  const padding = Math.max(0.001, (rawMax - rawMin) * 0.12);
  const max = rawMax + padding;
  const min = Math.max(0, rawMin - padding);
  const width = 220;
  const height = 82;
  const axisLeft = 26;
  const axisBottom = height - 12;
  const axisTopY = 12;
  const plotWidth = width - axisLeft - 5;          // 曲线点 X 严格落在 [axisLeft, axisLeft+plotWidth]
  const plotHeight = axisBottom - axisTopY;        // 曲线点 Y 严格落在 [axisTopY, axisBottom]
  const points = safeValues.map((value, index) => {
    const x = safeValues.length === 1 ? axisLeft : axisLeft + (index / (safeValues.length - 1)) * plotWidth;
    const y = axisBottom - ((value - min) / Math.max(0.001, max - min)) * plotHeight;
    return `${x.toFixed(1)},${Math.max(axisTopY, Math.min(axisBottom, y)).toFixed(1)}`;
  }).join(" ");
  const latest = safeValues[safeValues.length - 1] || 0;
  const mid = min + (max - min) / 2;
  const nonZeroValues = safeValues.filter((value) => Math.abs(value) > 1e-9);
  return `
    <div class="chart" data-values="${esc(JSON.stringify(safeValues))}" data-labels="${esc(JSON.stringify(tickLabels || safeValues.map((_, index) => index + 1)))}">
      <div class="chart-label"><span>${esc(title)}</span><strong>${number(latest, 3)}</strong></div>
      <svg viewBox="0 0 ${width} ${height}" preserveAspectRatio="none" aria-hidden="true">
        <clipPath id="${clipId}"><rect x="${axisLeft}" y="${axisTopY}" width="${plotWidth}" height="${plotHeight}" /></clipPath>
        <line x1="${axisLeft}" y1="${axisBottom}" x2="${width - 5}" y2="${axisBottom}" stroke="#cfd8e3" stroke-width="1" />
        <line x1="${axisLeft}" y1="${axisTopY}" x2="${axisLeft}" y2="${axisBottom}" stroke="#cfd8e3" stroke-width="1" />
        <text x="4" y="16" font-size="10" fill="#6a7d8a">${number(max, 2)}</text>
        <text x="4" y="${Math.round(height / 2)}" font-size="10" fill="#6a7d8a">${number(mid, 2)}</text>
        <text x="4" y="${height - 6}" font-size="10" fill="#6a7d8a">${number(min, 2)}</text>
        <g clip-path="url(#${clipId})">
          <polyline fill="none" stroke="${esc(color)}" stroke-width="2.2" points="${points}" />
          ${safeValues.map((value, index) => {
            const x = safeValues.length === 1 ? axisLeft : axisLeft + (index / (safeValues.length - 1)) * plotWidth;
            const y = axisBottom - ((value - min) / Math.max(0.001, max - min)) * plotHeight;
            return `<circle cx="${x.toFixed(1)}" cy="${Math.max(axisTopY, Math.min(axisBottom, y)).toFixed(1)}" r="2.2" fill="${esc(color)}" />`;
          }).join("")}
        </g>
      </svg>
      <div class="chart-tooltip"></div>
      ${nonZeroValues.length ? "" : `<div class="chart-zero-note">当前指标全是 0，说明这条曲线在该段还没有被真正触发。</div>`}
    </div>
  `;
}

function renderMemory(items) {
  if (!items || !items.length) {
    $("memoryList").innerHTML = `<div class="empty-note">还没有统一经验记忆。</div>`;
    return;
  }
  $("memoryList").innerHTML = items.map((item) => `
    <div class="memory-item">
      <div class="memory-head">
        <strong>${esc(sourceEventName(item.source_event_kind))}</strong>
        <span class="memory-support">support ${number(item.support, 3)}</span>
      </div>
      <div>${esc(item.display_text)}</div>
      <div class="support-meter"><span style="width:${Math.max(0, Math.min(100, Number(item.support || 0) * 100))}%"></span></div>
      <button type="button" data-delete="${esc(item.memory_entry_id)}">删除这条记忆</button>
    </div>
  `).join("");
  $("memoryList").querySelectorAll("button[data-delete]").forEach((button) => {
    button.addEventListener("click", async () => {
      await postJson("/api/phase20_7/memory/delete", {
        memory_entry_id: button.getAttribute("data-delete"),
        reason: "workbench_delete",
      });
      await refreshMemory();
    });
  });
}

function renderUnclosed(items) {
  if (!items || !items.length) {
    $("unclosedList").innerHTML = `<div class="empty-note">暂时没有被未闭合感拉住的问题。</div>`;
    return;
  }
  $("unclosedList").innerHTML = items.map((item) => `
    <div class="memory-item">
      <div class="memory-head">
        <strong>${esc(item.source_text)}</strong>
        <span class="memory-support">U ${number(item.u_value)}</span>
      </div>
      <div class="kv">尝试 ${esc(item.attempt_count)}</div>
    </div>
  `).join("");
}

async function refreshMemoryPackageControls() {
  const host = $("memoryPackageControls");
  if (!host) return;
  // 等数据返回前先把面板置一个"刷新中"占位，避免旧内容闪烁或落空。
  host.innerHTML = '<div class="package-status">正在刷新记忆包…</div>';
  // Bug6: 接到 phase20_7 自己的记忆包接口（不再借用旧 phase20）。
  // 后端语义：preview 返回可勾选的对齐事件 (event_id) → 勾选后 export 生成包 →
  // import 把包灌回当前会话 (跨会话/跨人分享) → batches 列出已灌批次 → uninstall 软删。
  const pageSize = Math.max(4, Number(memoryPackageSelection.pageSize || 12));
  const page = Math.max(1, Number(memoryPackageSelection.page || 1));
  const offset = (page - 1) * pageSize;
  const [previewData, batchesData] = await Promise.all([
    postJson("/api/phase20_7/package/preview", {
      session_id: sessionId,
      keyword: memoryPackageSelection.keyword,
      limit: pageSize,
      offset,
    }),
    postJson("/api/phase20_7/package/batches", {}),
  ]);
  const items = Array.isArray(previewData.items) ? previewData.items : [];
  const total = Number(previewData.total || items.length || 0);
  const pageCount = Math.max(1, Math.ceil(total / pageSize));
  memoryPackageSelection.page = Math.min(page, pageCount);
  const batches = Array.isArray(batchesData.batches) ? batchesData.batches : [];

  const fmtMs = (ms) => {
    const n = Number(ms || 0);
    if (!n) return "—";
    const d = new Date(n);
    return Number.isNaN(d.getTime()) ? "—" : d.toLocaleString("zh-CN", { hour12: false });
  };
  const selectedCount = memoryPackageSelection.selectedEventIds.size;
  const selectedHint = selectedCount
    ? `已勾选 ${selectedCount} / ${total} 条可导出。`
    : `共 ${total} 条可勾选的对齐事件 (reward>惩罚 的教学对齐)。`;

  const batchesHtml = batches.length
    ? batches.map((batch) => `
      <label class="package-checkbox-row">
        <span class="package-meta">
          <b>${esc(batch.package_name || batch.package_id || "记忆包")}</b>
          <div>批次 ${esc(batch.import_batch_id || "")}</div>
          <div>导入于 ${esc(fmtMs(batch.imported_at_ms))} · 含 ${number(batch.member_count || 0, 0)} 条经验</div>
        </span>
        <button type="button" data-pkg-uninstall="${esc(batch.import_batch_id || "")}">卸载</button>
      </label>
    `).join("")
    : `<div class="empty-note">当前会话还没有导入过记忆包。先导出一包再导回来试试分享流程。</div>`;

  const pageBar = `
    <div class="package-pagination">
      <div class="package-page-info">第 ${memoryPackageSelection.page} / ${pageCount} 页 · ${selectedHint}</div>
      <div class="package-actions">
        <button type="button" id="pkgPrevBtn" ${memoryPackageSelection.page <= 1 ? "disabled" : ""}>上一页</button>
        <button type="button" id="pkgNextBtn" ${memoryPackageSelection.page >= pageCount ? "disabled" : ""}>下一页</button>
      </div>
    </div>
  `;

  const itemsHtml = items.length
    ? items.map((item) => `
          <label class="package-checkbox-row">
            <input type="checkbox" data-event-select="${esc(item.event_id || "")}" ${memoryPackageSelection.selectedEventIds.has(item.event_id || "") ? "checked" : ""} />
            <span class="package-meta">
              <b>${esc(item.input_text || "(无输入文本)")}</b>
              <div>给 ${esc(item.output_text || "(无回复)")}</div>
              <div>
                ${esc(fmtMs(item.created_at_ms))}${item.has_visual ? " · 含视觉签名" : ""}${item.reward !== undefined ? " · reward " + number(item.reward, 2) : ""}${item.punish ? " · 惩罚 " + number(item.punish, 2) : ""}
              </div>
            </span>
          </label>
        `).join("")
    : `<div class="empty-note">没有符合当前条件的对齐事件。先去对话页教几轮，AP 真的对了之后这里才会出现条目。</div>`;

  const lastExported = memoryPackageSelection.lastExportedPackage;
  const lastExportedHtml = lastExported
    ? `<div class="package-status">上次导出: ${esc(lastExported.package_id || "")} · ${number(lastExported.entry_count || 0, 0)} 条。点"把这包导回本会话"可立即演示导入。</div>`
    : "";

  host.innerHTML = `
    <div class="package-row">
      <h4>导出记忆包</h4>
      <p>把当前会话里 teaching-align 后 (reward 大于惩罚) 的真实经验打包成可分享的 JSON。筛选只影响这里的列表，不动 AP 认知。</p>
      <div class="package-form-grid">
        <label>包名<input id="pkgName" value="APV3 记忆包" /></label>
        <label>关键词<input id="pkgKeyword" placeholder="例如 你好 / 数学 / 苹果" value="${esc(memoryPackageSelection.keyword || "")}" /></label>
      </div>
      <div class="package-selected-summary">${selectedHint}</div>
      <div class="package-actions">
        <button type="button" id="pkgExportBtn">导出选中的为 JSON</button>
        <button type="button" id="pkgSelfImportBtn" ${lastExported ? "" : "disabled"} title="把已 export 的包立刻 import 一次，模拟把别人发的包灌回本会话">把这包导回本会话</button>
        <label class="file-button" for="pkgImportFile">从文件导入包</label>
        <input id="pkgImportFile" class="file-input" type="file" accept="application/json,.json" />
        <button type="button" id="pkgRefreshBtn">刷新</button>
      </div>
      ${lastExportedHtml}
    </div>
    <div class="package-row">
      <h4>已导入的批次</h4>
      <p>卸载 = tombstone 该批次引用的全部经验 (软删, 召回即刻失效, 不动写过的 tick 历史)。</p>
      ${batchesHtml}
    </div>
    <div class="package-row">
      <h4>可勾选的对齐事件</h4>
      <p>下面每一条都是真实写入经验流的 teaching-alignment 事件 (教过它、它说对、reward>惩罚)。勾选后参与导出。</p>
      ${pageBar}
      <div class="package-list">
        ${itemsHtml}
      </div>
      <div class="package-actions">
        <button type="button" id="pkgSelectAllBtn">全选本页</button>
        <button type="button" id="pkgSelectNoneBtn">反选本页</button>
        <button type="button" id="pkgSelectClearBtn">清空选择</button>
      </div>
    </div>
  `;

  $("pkgKeyword")?.addEventListener("input", (event) => {
    memoryPackageSelection.keyword = String(event.target.value || "");
  });
  $("pkgExportBtn")?.addEventListener("click", async () => {
    const eventIds = [...memoryPackageSelection.selectedEventIds];
    if (!eventIds.length) {
      $("progressBanner").textContent = "先在下面勾选至少一条经验，再点导出。";
      return;
    }
    const exported = await postJson("/api/phase20_7/package/export", {
      event_ids: eventIds,
      package_name: String($("pkgName")?.value || "APV3 记忆包"),
      session_id: sessionId,
    });
    if (exported.error) {
      $("progressBanner").textContent = `导出失败: ${esc(exported.error)}`;
      return;
    }
    memoryPackageSelection.lastExportedPackage = exported;
    // 下载一份 JSON 让用户可分享给他人；下载失败也不影响后续 import 路径
    try {
      const blob = new Blob([JSON.stringify(exported, null, 2)], { type: "application/json" });
      const blobUrl = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = blobUrl;
      anchor.download = `${exported.package_id || "apv3_package"}.json`;
      anchor.click();
      setTimeout(() => URL.revokeObjectURL(blobUrl), 4000);
    } catch (_) { /* 下载能力缺失不影响后续 import 路径 */ }
    $("progressBanner").textContent = `已导出记忆包 ${exported.package_id || ""}，含 ${number(exported.entry_count || 0, 0)} 条经验，并已下载 JSON 文件。`;
    void refreshMemoryPackageControls();
  });
  $("pkgSelfImportBtn")?.addEventListener("click", async () => {
    const pkg = memoryPackageSelection.lastExportedPackage;
    if (!pkg) return;
    const imported = await postJson("/api/phase20_7/package/import", { package: pkg, session_id: sessionId });
    if (imported.error) {
      $("progressBanner").textContent = `导入失败: ${esc(imported.error)}`;
      return;
    }
    await refreshMemory();
    await refreshMemoryPackageControls();
    $("progressBanner").textContent = `已把包 ${pkg.package_id || ""} 导回本会话，新增 ${number(imported.imported || 0, 0)} 条经验。`;
  });
  $("pkgImportFile")?.addEventListener("change", async (event) => {
    const file = event.target.files && event.target.files[0];
    if (!file) return;
    try {
      const text = await file.text();
      const pkg = JSON.parse(text);
      const imported = await postJson("/api/phase20_7/package/import", { package: pkg, session_id: sessionId });
      if (imported.error) {
        $("progressBanner").textContent = `导入失败: ${esc(imported.error)}`;
      } else {
        await refreshMemory();
        await refreshMemoryPackageControls();
        $("progressBanner").textContent = `已从文件导入记忆包，新增 ${number(imported.imported || 0, 0)} 条经验。`;
      }
    } catch (e) {
      $("progressBanner").textContent = `文件解析失败: ${esc(String(e))}`;
    }
    event.target.value = "";
  });
  $("pkgRefreshBtn")?.addEventListener("click", async () => {
    await refreshMemory();
    await refreshMemoryPackageControls();
  });
  $("pkgPrevBtn")?.addEventListener("click", () => {
    memoryPackageSelection.page = Math.max(1, memoryPackageSelection.page - 1);
    void refreshMemoryPackageControls();
  });
  $("pkgNextBtn")?.addEventListener("click", () => {
    memoryPackageSelection.page += 1;
    void refreshMemoryPackageControls();
  });
  $("pkgSelectAllBtn")?.addEventListener("click", () => {
    items.forEach((item) => {
      if (item.event_id) memoryPackageSelection.selectedEventIds.add(item.event_id);
    });
    void refreshMemoryPackageControls();
  });
  $("pkgSelectNoneBtn")?.addEventListener("click", () => {
    items.forEach((item) => {
      if (item.event_id) memoryPackageSelection.selectedEventIds.delete(item.event_id);
    });
    void refreshMemoryPackageControls();
  });
  $("pkgSelectClearBtn")?.addEventListener("click", () => {
    memoryPackageSelection.selectedEventIds.clear();
    void refreshMemoryPackageControls();
  });
  host.querySelectorAll("input[data-event-select]").forEach((checkbox) => {
    checkbox.addEventListener("change", () => {
      const id = checkbox.getAttribute("data-event-select") || "";
      if (!id) return;
      if (checkbox.checked) memoryPackageSelection.selectedEventIds.add(id);
      else memoryPackageSelection.selectedEventIds.delete(id);
    });
  });
  host.querySelectorAll("button[data-pkg-uninstall]").forEach((button) => {
    button.addEventListener("click", async () => {
      const batchId = String(button.getAttribute("data-pkg-uninstall") || "");
      if (!batchId) return;
      await postJson("/api/phase20_7/package/uninstall", { import_batch_id: batchId });
      await refreshMemory();
      await refreshMemoryPackageControls();
      $("progressBanner").textContent = `已卸载批次 ${batchId}，其引用的经验已被软删。`;
    });
  });
}
async function refreshMemory() {
  const data = await postJson("/api/phase20_7/memory/list", { limit: 200, session_id: sessionId });
  renderMemory(data.items || []);
  renderUnclosed(data.unclosed || []);
  $("metricMemory").textContent = String((data.items || []).length);
  $("metricUnclosed").textContent = String((data.unclosed || []).length);
}

async function speakLatestReply() {
  if (!latestReplyText) {
    $("ttsStatus").textContent = "还没有可朗读的最新回复。";
    return;
  }
  const spoken = await speakWithBrowserXiaoyi(latestReplyText);
  if (spoken) {
    return;
  }
  $("ttsStatus").textContent = "浏览器没有检测到可用的 xiaoyi/中文本地语音；后端 SAPI 当前也未发现 xiaoyi。不会调用云端，也不会伪造音频。";
}

async function speakWithBrowserXiaoyi(text) {
  if (!("speechSynthesis" in window) || !("SpeechSynthesisUtterance" in window)) {
    return false;
  }
  const voices = await loadBrowserVoices();
  const selected = getSelectedVoice(voices);
  const voice = selected
    || voices.find((item) => /xiaoyi|xiao yi|晓伊|晓艺|小艺|小依/i.test(`${item.name || ""} ${item.voiceURI || ""}`))
    || voices.find((item) => /zh|chinese|mandarin/i.test(`${item.lang || ""} ${item.name || ""}`));
  if (!voice) return false;
  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.voice = voice;
  utterance.lang = voice.lang || "zh-CN";
  utterance.rate = Number(window._ttsRate || 1);
  utterance.pitch = 1.0;
  $("ttsStatus").textContent = `浏览器本地朗读中 · ${voice.name || "xiaoyi"}`;
  window.speechSynthesis.speak(utterance);
  return true;
}

function loadBrowserVoices() {
  return new Promise((resolve) => {
    const voices = window.speechSynthesis.getVoices();
    if (voices.length) {
      browserVoiceCache = voices.slice();
      resolve(voices);
      return;
    }
    const timer = window.setTimeout(() => resolve(window.speechSynthesis.getVoices()), 800);
    window.speechSynthesis.onvoiceschanged = () => {
      window.clearTimeout(timer);
      browserVoiceCache = window.speechSynthesis.getVoices().slice();
      resolve(window.speechSynthesis.getVoices());
    };
  });
}

function getSelectedVoice(voices = browserVoiceCache) {
  const selectedUri = String(window._ttsVoiceURI || "").trim();
  if (!selectedUri) return null;
  return voices.find((item) => (item.voiceURI || item.name || "") === selectedUri) || null;
}

function renderTtsStatus(tick) {
  const action = tick.selected_action || {};
  if (action.action_type === "reply_tts_audio") {
    const selected = String(window._ttsVoiceURI || action.voice_preference || "xiaoyi");
    $("ttsStatus").textContent = `AP 产生了本地朗读意图: ${selected}。`;
  }
}

function updateIdleCadence(ticks, spoke) {
  if ($("autoIdle").getAttribute("aria-pressed") !== "true") return;
  const latest = ticks[ticks.length - 1] || {};
  const action = latest.selected_action || {};
  const lifecycle = learningObjectLifecycle(latest) || {};
  const rhythm = lifecycle.memory_consolidation_forgetting_rhythm || {};
  const learning = learningLoopMetric(latest) || {};
  const cadencePressure = Math.max(
    Number(rhythm.review_rhythm_pressure || 0),
    Number(rhythm.forgetting_pressure || 0),
    Number(learning.scaffold_regression_need || 0),
    Number(learning.teacher_off_readiness || 0),
  );
  const cadenceConfidence = Math.max(
    Number(rhythm.memory_consolidation || 0),
    Number(learning.feedback_only_readiness || 0),
    Number(learning.cold_retest_readiness || 0),
  );
  const interesting = spoke
    || action.action_type === "idle_think"
    || action.action_type === "idle_visual_focus"
    || action.action_type === "idle_audio_focus"
    || Boolean(latest.visual_inner_picture)
    || Boolean(latest.audio_inner_sketch)
    || (latest.unclosed_items || []).length > 0
    || cadencePressure > 0.42
    || cadenceConfidence > 0.45;
  idleQuietRuns = interesting ? 0 : Math.min(12, idleQuietRuns + 1);
  const rhythmLoad = Math.max(0, cadencePressure - cadenceConfidence * 0.32);
  const rhythmEase = Math.max(0, cadenceConfidence - cadencePressure * 0.18);
  const quietLift = Math.min(0.32, idleQuietRuns * 0.03);
  const delayScore = Math.max(0, Math.min(1, rhythmLoad - rhythmEase * 0.22 + quietLift));
  const nextDelay = Math.round(850 + delayScore * 4150);
  // V1: 优先用服务端 idle_pacing 节奏 (arousal/curiosity/fatigue派生), 退回前端推算
  let pacingDelay = nextDelay;
  let pacingLabel = "";
  if (window._latestIdlePacingSec) {
    pacingDelay = Math.round(window._latestIdlePacingSec * 1000);
    if (pacingDelay < 10000) pacingLabel = "活跃";
    else if (pacingDelay > 20000) pacingLabel = "安静";
    else pacingLabel = "平稳";
  }
  if (autoIdleTimer && pacingDelay === autoIdleDelayMs) return;
  armAutoIdle(pacingDelay);
  $("autoIdle").textContent = `连续闲时: ${idleDelayLabel(pacingDelay)} (${pacingLabel})`;
  setStatus(pacingDelay > 2500 ? "低频待机" : "连续闲时", pacingDelay > 2500 ? "sleeping" : "running");
}

function idleDelayLabel(delay) {
  return `${Math.max(0.5, Math.round(Number(delay || 0) / 100) / 10).toFixed(1)}s`;
}

function armAutoIdle(delay) {
  if (autoIdleTimer) {
    window.clearTimeout(autoIdleTimer);
  }
  autoIdleDelayMs = delay;
  autoIdleTimer = window.setTimeout(() => {
    autoIdleTimer = null;
    void sendTurn({ idle: true });
  }, delay);
}

function startAutoIdle(delay = 1000) {
  $("autoIdle").setAttribute("aria-pressed", "true");
  $("autoIdle").textContent = `连续闲时: ${idleDelayLabel(delay)}`;
  armAutoIdle(delay);
  setStatus(delay > 1000 ? "低频待机" : "连续闲时", delay > 1000 ? "sleeping" : "running");
}

function stopAutoIdle(updateButton = true) {
  if (autoIdleTimer) window.clearTimeout(autoIdleTimer);
  autoIdleTimer = null;
  if (updateButton) {
    $("autoIdle").setAttribute("aria-pressed", "false");
    $("autoIdle").textContent = "连续闲时";
    setStatus("待机", "sleeping");
  }
}

function toggleAutoIdle() {
  if (autoIdleTimer) {
    stopAutoIdle();
    return;
  }
  idleQuietRuns = 0;
  startAutoIdle(1000);
  sendTurn({ idle: true });
}

function latestIdleThought(ticks) {
  const tick = ticks[ticks.length - 1] || {};
  const item = (tick.unclosed_items || [])[0];
  if (!item) return "";
  return `还在想「${item.source_text}」`;
}

function appendStructureStream(ticks, { idle = false } = {}) {
  const fresh = [];
  for (const tick of ticks || []) {
    const action = tick.selected_action || {};
    const summary = structureSummary(tick, { idle });
    if (!summary) continue;
    fresh.push({
      tick: tick.tick ?? "?",
      action: actionNames[action.action_type] || action.action_type || "tick",
      summary,
    });
  }
  if (!fresh.length) return;
  streamItems = [...fresh.reverse(), ...streamItems];
  streamItems = streamItems.slice(0, 24);
  $("structureStream").innerHTML = streamItems.map((item) => `
    <div class="stream-item">
      <strong>tick ${esc(item.tick)} · ${esc(item.action)}</strong>
      <div>${esc(item.summary)}</div>
    </div>
  `).join("");
}

function structureSummary(tick, { idle = false } = {}) {
  const action = tick.selected_action || {};
  const ssp = tick.ssp_active_summary || {};
  const query = (tick.query_structures || [])[0] || {};
  const unclosed = (tick.unclosed_items || [])[0];
  const b = (tick.b_candidates || [])[0];
  const visual = (tick.receptor_outputs || []).find((item) => item.receptor === "visual_patch_sensor");
  if (idle && (tick.feelings || {}).narrative_text) {
    return `短期结构流续写: ${(tick.feelings || {}).narrative_text}`;
  }
  if (idle && unclosed) {
    return `未闭合感把短期结构流拉回「${unclosed.source_text}」，U=${number(unclosed.u_value)}。`;
  }
  if (visual) {
    const idleMark = visual.idle_continuation ? "闲时继续采样" : "视觉结构流更新";
    return `${idleMark}: focus=${(visual.focus_xy || []).join(",")}，clarity=${percent(visual.clarity_coverage)}。`;
  }
  const audio = (tick.receptor_outputs || []).find((item) => item.receptor === "audio_inner_focus" || item.receptor === "audio_audit_sensor");
  if (audio) {
    const sketch = tick.audio_inner_sketch || {};
    if (audio.receptor === "audio_inner_focus") {
      return `听觉结构流延续: 内心能量 ${number(sketch.inner_energy || 0)}，语义标签为空。`;
    }
    return `听觉审计写入: duration=${number(audio.duration_ms, 1)} ms，语义标签为空。`;
  }
  if (query.signature || ssp.signature) {
    const kind = query.structure_kind || ssp.structure_kind || "结构";
    const visualSig = query.visual_signature ? "，已绑定本轮视觉证据" : "";
    return `${kind} 更新: ${query.unit_count || ssp.active_occurrence_count || 0} 个单元${visualSig}。`;
  }
  if (b) {
    return `召回 ${candidateName(b)}，支持度 ${number(b.support)}。`;
  }
  return action.action_type ? `行动竞争选中 ${actionNames[action.action_type] || action.action_type}。` : "";
}

function inputName(item) {
  const kind = item.input_kind || item.media_type || "输入";
  if (kind === "text") return `文本 ${item.char_length || 0} 字`;
  if (kind === "image") return "图片";
  if (kind === "audio") return "音频";
  return esc(kind);
}

function receptorName(item) {
  const receptor = item.receptor || "感受器";
  if (receptor === "text") return `文本感受器 ${item.unit_count || 0} 单元`;
  if (receptor === "visual_patch_sensor") return `视觉 patch ${percent(item.clarity_coverage)}`;
  if (receptor === "audio_audit_sensor") return `听觉审计 ${number(item.duration_ms, 1)} ms`;
  return receptor;
}

function candidateName(item) {
  const kind = item.kind || "";
  if (kind === "exact_b0") return "精确经验";
  if (kind === "structural_b") return "结构相似经验";
  if (kind === "sequence_forward_prediction") return "序列后继";
  if (kind === "source_structure_explanation") return "来源解释";
  if (kind === "every_tick_backward_min_error") return "双向最小误差";
  if (kind === "sensory_successor_prediction") return "继续采样";
  if (kind === "audio_temporal_prediction") return "听觉残响";
  if (kind === "idle_successor_continuation") return "闲时续写";
  return kind || "候选";
}

function readableState(item) {
  const family = familyNames[item.family] || item.family || "对象";
  const label = item.label || item.sa_id || "";
  return `${family}:${label}`;
}

function memoryTypeName(value) {
  if (value === "exact_recall") return "精确记忆";
  if (value === "structural_recall") return "结构记忆";
  if (value === "package_member") return "记忆包";
  return value || "经验记忆";
}

function sourceEventName(value) {
  if (value === "experience_alignment") return "教学对齐";
  if (value === "text_observation") return "文本观察";
  if (value === "visual_patch_sample") return "视觉采样";
  if (value === "audio_audit_sample") return "听觉审计";
  return value || "";
}

function totalTiming(timings) {
  return Object.values(timings || {}).reduce((sum, value) => {
    const parsed = Number(value);
    return sum + (Number.isFinite(parsed) ? parsed : 0);
  }, 0);
}

function renderHelpExpand() {
  const article = document.querySelector(".help-article");
  if (!article || article.dataset.expanded === "1") return;
  article.dataset.expanded = "1";
  const extra = `
    <div class="help-callout">
      <strong>给第一次接触 AP 的人</strong>
      <p>AP 不是“先写好规则再跑”，也不是“拿大模型包一层 UI”。它更像一个持续接收经验、持续把经验变成内部状态、再把内部状态拿去争夺下一步行动的底座。</p>
      <p>所以你看到的不是答案表，而是一条经验流。你教它，它会把教到的东西写进经验；你纠正它，它会把纠正写进经验；它下一轮怎么说，来自这些经验之间的竞争。</p>
    </div>

    <div class="help-summary-grid">
      <div class="help-summary-card">
        <h3>一眼看懂 AP</h3>
        <p>AP 不是单次输出模型，而是一个不断接收、回看、闭合、再行动的过程。它的“像人”来自闭环，而不是外形包装。</p>
      </div>
      <div class="help-summary-card">
        <h3>一眼看懂 APV3</h3>
        <p>APV3 是这个底座的可见实现：你可以看 tick、草稿、记忆、感受、情绪、动作竞争和教学痕迹，而不是只看一句最终回复。</p>
      </div>
    </div>

    <h2 id="help-feelings">12 认知感受</h2>
    <p>白皮书里的 12 通道不是装饰，而是认知闭环的底层电流。它们把“惊到”“不对劲”“有把握”“有压力”“还有事没想完”等状态纳入行动竞争与学习回路。</p>
    <div class="help-grid">
      <div class="help-card">
        <h3>它们做什么</h3>
        <p>把看见、听见、回忆、期待、未闭合、疲劳这些东西，变成可参与竞争的内部状态。</p>
      </div>
      <div class="help-card">
        <h3>为什么重要</h3>
        <p>没有这些状态，系统只能“读输入”。有了这些状态，系统才会出现“我现在更想问”“我现在不太敢答”这类拟人行为。</p>
      </div>
    </div>
    <p>APV3 当前已经把部分通道接入工作台可见层，尤其是把握、期待、压力、未闭合和疲劳类信号。其余通道仍应继续按白皮书逐步接通，不能口头补齐。</p>

    <h2 id="help-symbolic">与符号主义 / 规则系统</h2>
    <p>AP 不是先把所有行为写成 if-else，也不是把“你好就回你好”这种规则表铺满。规则系统可以解释结果，但很难解释为什么同样的输入在不同经验下会变得更敢说、更谨慎或直接请教。</p>
    <div class="help-grid">
      <div class="help-card">
        <h3>规则系统能做什么</h3>
        <p>它擅长固定流程、明确分支和静态约束，适合工程护栏。</p>
      </div>
      <div class="help-card">
        <h3>AP 想解决什么</h3>
        <p>AP 想解决的是经验如何自己长出行动偏置、范式、情绪和连续对话风格，而不是手写每个分支。</p>
      </div>
    </div>
    <p>所以白皮书里提到的“规律”，不是把人类行为翻成规则集，而是把经验流里真的会出现的共现、压力、闭合、奖惩和行动竞争，做成可学习的闭环。</p>

    <h2 id="help-emotion">情绪如何工作</h2>
    <p>情绪是慢变量，不是一次 tick 的标签。它会跨 tick 积分，决定 AP 后续更敢泛化还是更谨慎、更愿意表达还是更克制。</p>
    <div class="help-grid">
      <div class="help-card">
        <h3>正向影响</h3>
        <p>连续成功、被肯定、把握上升时，表达会更松，泛化会更敢一点。</p>
      </div>
      <div class="help-card">
        <h3>负向影响</h3>
        <p>连续受挫、未闭合增多、疲劳上升时，动作会更保守，更倾向请教或回读。</p>
      </div>
    </div>

    <h2 id="help-learning-loop">六阶段学习协议</h2>
    <p>AP 的学习不是“喂答案”，而是从教学、复盘、自测、冷重测、退场就绪一路演化。工作台展示这些阶段，是为了让用户看到“学会”是怎样形成的。</p>
    <div class="help-chapter">
      <h3>阶段怎么理解</h3>
      <p>每一阶段都不是固定的 UI 标签，而是经验流里的真实条件。教学不是终点，复盘不是装饰，自测和冷重测也不是测试表格，它们是让 AP 自己修边界的过程。</p>
    </div>
    <ol>
      <li>模仿：先接住老师给的示范。</li>
      <li>预测：下一步先试着自己补完。</li>
      <li>聚合：把重复的经验压成稳定模式。</li>
      <li>范式：把可复用的过程单元抽出来。</li>
      <li>组织：把多个范式串成更长的动作链。</li>
      <li>精修：在反例、纠错和冷重测里修边界。</li>
    </ol>

    <h2 id="help-teaching">教学协议与 teacher-off</h2>
    <p>teacher-off 的意义不是抛弃老师，而是证明系统能在老师离开后继续保持闭环。教学纠正、反馈、负例抑制和自测是这个闭环的基本组成。</p>
    <div class="help-chapter">
      <h3>怎么教最有效</h3>
      <p>对话、识图、数学、画画都走同一个原则：先给示范，再让 AP 自己试，再用纠正把差异写进经验。白皮书不支持靠答案表一次性灌成“会答题”。</p>
    </div>
    <div class="help-grid">
      <div class="help-card">
        <h3>为什么要留老师</h3>
        <p>因为 AP 的很多能力不是“写死的”，而是靠教学协议慢慢长出来的。老师是把经验写进去的人。</p>
      </div>
      <div class="help-card">
        <h3>为什么要退场</h3>
        <p>因为真正的闭环要验证：老师不在时，系统还能不能保持边界、复盘和自测。</p>
      </div>
    </div>

    <h2 id="help-api">接口一览</h2>
    <p>APV3 提供 Web API 和本地工作台两种入口：</p>
    <ul>
      <li><code>POST /api/phase20_7/turn</code> 发送一轮对话（文本、图片、音频、教学反馈）。</li>
      <li><code>GET /api/phase20_7/progress</code> 查看当前 tick 正在做什么。</li>
      <li><code>POST /api/phase20_7/memory/list</code> 查看统一记忆视图。</li>
      <li><code>POST /api/phase20/memory/export</code> / <code>import</code> / <code>uninstall</code> 处理记忆包。</li>
      <li><code>POST /api/phase20/media/upload</code> 上传本地图片和音频。</li>
    </ul>
    <div class="help-chapter">
      <h3>页面为什么分层</h3>
      <p>理论页现在用左边目录、右边章节的方式呈现。目录负责快速跳转，正文负责把白皮书整理成可读结构，适合想研究原理的人慢慢看。</p>
    </div>

    <h2 id="help-faq">FAQ</h2>
    <ul class="help-note-list">
      <li>Q: 可以把 xiaoyi 音色随仓库分发吗？A: 不行。Web Speech 的音色来自用户本机系统或浏览器实现，仓库只能保存选择逻辑。</li>
      <li>Q: AP 是规则库吗？A: 不是。规则只能做表面解释，AP 的核心是经验流、状态池、范式和行动竞争。</li>
      <li>Q: AP 为什么能数学泛化？A: 因为事实和过程分开学，再在行动层组合。</li>
      <li>Q: AP 为什么能实时学习？A: 因为每次教学都写进同一条经验流，下一轮会重新参与竞争。</li>
      <li>Q: 为什么这里看起来像“章节页面”而不是单页目录？A: 因为理论内容已经足够长，目录只负责导航，正文负责逐章阅读。</li>
    </ul>
  `;
  article.insertAdjacentHTML("beforeend", extra);
}

$("sendTurn").addEventListener("click", () => sendTurn());

// B4: 多模态识图示例（4 幕戏剧版）。
// 开场追加一条失败探针:发 held_out 苹果图——新会话里它没见过这类取景,答不出名字。
// 然后 teacher_feedback 教一次 → 再认（无 feedback）→ 想象。完成末尾系统提示强调白箱 lineage。
async function runDemoExperience() {
  if (requestInFlight) { setStatus("正在处理,请稍候", "running"); return; }
  enterDemo("experience", "apple");
  const appleTrainPath = "data/phase20_workbench_media/真实苹果2_2bf246de034bf5c4.jpg";
  const appleHeldOutPath = "data/phase20_workbench_media/真实苹果2_2bf246de034bf5c4.jpg";
  const sequence = [
    // 幕1 失败探针: held_out 苹果取景,新会话任何图都没记忆
    { text: "这是什么", image_path: appleHeldOutPath, runtime_stage: "stage6" },
    // 幕2 教 train 苹果(不同取景同概念)把焦点 patch 指代写入经验
    { text: "这是什么", image_path: appleTrainPath, teacher_feedback: "是苹果", reward_mag: 1.0, runtime_stage: "stage6" },
    // 幕3 再认 train 苹果—无 teacher_feedback,看能不能召回名字
    { text: "这是什么", image_path: appleTrainPath, runtime_stage: "stage6" },
    // 幕4 想象: 触发 visual_imagination_recall ("苹果"与已教"是苹果"重叠0.5达标; 长句重叠不足不触发)
    { text: "苹果", runtime_stage: "stage6" },
  ];
  const actLabels = [
    "幕1 看图: 问它这是什么。答不出=真没学过;若答出来了,那是长期记忆里有旧教学(经验流跨会话)——两种都是真实状态,没有预装识别器。",
    "幕2 教：现在 teacher_feedback 把你看到的焦点 patch + 整体轮廓写进经验,赋名“苹果”。",
    "幕3 再认：再发一张训练过的苹果,这次它该用刚写入的经验召回名字了。",
    "幕4 想象：只说“苹果”两个字——它会召回视觉经验,从状态池重建出闭眼回忆的样子(整体模糊但在、看过的细节清晰),贴在气泡下面。",
  ];
  addMessage("system", "多模态识图示例开始（全程新会话）:先发它没见过的取景让它失败一次,再教一次,看它怎么从经验里把名字召回出来。");
  for (let i = 0; i < sequence.length; i++) {
    while (requestInFlight) { await new Promise((r) => setTimeout(r, 300)); }
    addMessage("system", actLabels[i]);
    const step = sequence[i];
    await new Promise((resolve) => {
      sendTurn({ idle: false, queuedPayload: step });
      const checkDone = setInterval(() => {
        if (!requestInFlight) { clearInterval(checkDone); resolve(); }
      }, 200);
    });
    await new Promise((r) => setTimeout(r, 1200));
  }
  exitDemo("体验示例完成。它现在认识的每样东西都有一条可回放的教学记录——详情页 tick 回放能看到它当时怎么看这张图的。已切回主对话会话,自由对话继续教学。");
}
$("demoExperience")?.addEventListener("click", runDemoExperience);

// B2: 体验数学（4 幕戏剧版 + 草稿格重放弹窗）。
// 幕1 失败问 42+35=?→不会  幕2 教 4 个位+1 竖式  幕3 重问 42+35=?→答 77 + 自动弹草稿格重放
// 幕4 问 87+96=?（7+6 没教过）→诚实说不会 →提示白箱: 它不编答案。
async function runDemoMath() {
  if (requestInFlight) { setStatus("正在处理,请稍候", "running"); return; }
  enterDemo("math", "arith");
  // 事实组选用发行库里从未教过的组合(51+37 需要 1+7 与 5+3) — 保证幕1真失败.
  // 经验流是长期记忆(跨会话), 老演示教过的 42+35 事实还在 — 这本身是特性不是bug,
  // 但演示的"失败幕"必须用真没教过的题.
  const facts = [
    { text: "1+7=?", teacher_feedback: "8", reward_mag: 1.0, runtime_stage: "stage6" },
    { text: "5+3=?", teacher_feedback: "8", reward_mag: 1.0, runtime_stage: "stage6" },
    { text: "1+2=?", teacher_feedback: "3", reward_mag: 1.0, runtime_stage: "stage6" },
    { text: "6+2=?", teacher_feedback: "8", reward_mag: 1.0, runtime_stage: "stage6" },
  ];
  const demo = [
    { text: "61+22=?", teacher_feedback: "83", reward_mag: 1.0, runtime_stage: "stage6" },
  ];
  const testFail = { text: "51+37=?", runtime_stage: "stage6" };
  const testRecall = { text: "51+37=?", runtime_stage: "stage6" };
  // ===== 进位篇 (2026-07-04 扩幕): 把"会进位"纳入同一过程范式, 不另造机制 =====
  // carry 单元需要教 (a) 能产生进位的个位事实(2位输出) (b) 带进位的十位事实(3项加)
  // (c) 一道带进位示范题. 后端执行端 carry 传递已实测可用(7+8→15 写5 carry1, 5+3+1→9).
  const factsCarry = [
    { text: "7+7=?", teacher_feedback: "14", reward_mag: 1.0, runtime_stage: "stage6" },
    { text: "4+2+1=?", teacher_feedback: "7", reward_mag: 1.0, runtime_stage: "stage6" },
    { text: "2+4+1=?", teacher_feedback: "7", reward_mag: 1.0, runtime_stage: "stage6" },
    { text: "4+2=?", teacher_feedback: "6", reward_mag: 1.0, runtime_stage: "stage6" },
  ];
  const demoCarry = [ { text: "47+27=?", teacher_feedback: "74", reward_mag: 1.0, runtime_stage: "stage6" } ];
  // 测试题用交换加数顺序的 27+47=? — 既不是示范题 (47+27 也已对齐) 又复用学到的同结构
  // 个位 7+7→14 写4 carry1, 十位 subquery=2+4+1 (3项加) 也要召回 — 百搭同套范式.
  // 但 2+4+1=7 这个 fact 还没教过, 改用 6+2+1=9 教过的: 示范与测试题都需4+2+1.
  // 所以: 测试题的十位 fact 必须也教过4+2+1, 那样个位需 7+7=14, 十位需 4+2+(+)1=7,
  // 即测试题十位 + 个位 + 进位 = 4+2+1=7 — 等同示范题结构. 用 27+47=74 同样适用.
  const testCarry = { text: "27+47=?", runtime_stage: "stage6" };
  const testHonestCarry = { text: "94+85=?", runtime_stage: "stage6" };
  const sequence = [testFail, ...facts, ...demo, testRecall,
                    ...factsCarry, ...demoCarry, testCarry, testHonestCarry];
  //  0    1..4    5       6         7..10         11            12          13
  // 幕1  facts  demo  幕3重问   factsCarry   demoCarry示范   幕-C见证  幕-D诚实
  const actLabels = [
    "幕1 失败: 先问它从没教过的 51+37=?——它不是计算器,没教过就不会。",
    "幕2 教列事实(答案对齐): 1+7=8(个位列要用的)。",
    "幕2 教列事实(答案对齐): 5+3=8(十位列要用的)。",
    "幕2 教列事实(答案对齐): 1+2=3。",
    "幕2 教列事实(答案对齐): 6+2=8。",
    "幕2 教过程范式(竖式结构): 教师对 61+22=83 演示了完整竖式序列——抄加数→换行对齐→跳行到右列逐列写结果。每步用共享感知函数 perceive_process_state 标注状态, 与自发偶现键同空间; 系统会先 POST /api/phase20_7/paradigm_demonstrate 跑一次示范, 再发答案对齐 turn。",
    "幕3 见证: 再问 51+37=?——个位 1+7、十位 5+3 都教过了,竖式结构也教过了。看它按学到的相对寻址拼出一个无进位的题。",
    "幕-A 教进位事实(2 位输出): 7+7=14 ——个位召回出 14 时,它写 4,carry=1 自动拼进下一列 subquery。（── 进位篇开始: 换一种新操作 = 教新列事实+示范新题,机制不变 ──）",
    "幕-A 教带进位十位(3 项加): 4+2+1=7 ——让十位列召回知道“加上个位进过来的1”（示范题 47+27 的十位用）。",
    "幕-A 也教交换加数的带进位十位(3 项加): 2+4+1=7 ——测试题 27+47 的十位需 2+4+1, 等价不同字符序列, 教过 AP 才能召回。",
    "幕-A 也教无进位十位(2 项加): 4+2=6 ——同一过程范式既可走无进位,也能带进位,差异只在外加的 carry 项。",
    "幕-B 教带进位竖式过程范式: 教师对 47+27=74 完整竖式序列示范一遍(先发 paradigm_demonstrate 真灌共现, 再发答案对齐 turn)。同一 perceive_process_state,同一相对寻址,只是多了一个 carry 通道。",
    "幕-C 见证: 再问 27+47=?——交换加数,从没对齐过这个题(避免直接召回复写两格)。个位 7+7 召回 14(写4 carry1),十位 subquery 自动 = 2+4+1,召回 7,写 74。同套相对寻址,同范式键,只是十位 subquery 字面不同。",
    "幕-D 诚实白箱: 问 94+85=?(4+5=9 教过,9+8+1=18 没教)——它拼不出列结果,诚实请假,这就是白箱价值。",
  ];
  addMessage("system", "小学数学泛化学习示例开始（全程新会话）:先看它不会,再教列事实+教竖式结构看它拼无进位题;再进进位篇——教产生进位的列事实+教带进位的竖式结构,看它学一种新操作的全过程。同一套 perceive_process_state / derive_paradigm_key / query_paradigm_next_steps / paradigcounterpressure,换操作 = 换教,不是改程序。");
  for (let i = 0; i < sequence.length; i++) {
    while (requestInFlight) { await new Promise((r) => setTimeout(r, 300)); }
    addMessage("system", actLabels[i]);
    const step = sequence[i];
    // 幕2 教示范(下标 5) + 幕-B 教带进位竖式示范(下标 11): 答案对齐 turn 前,
    // 先真实 POST paradigm_demonstrate 灌入完整竖式序列共现. 让 teach_process_paradigm_demonstration
    // 真跑, 每步共享感知函数标注状态, 落 action_sequence_cooccurrence (与自发同表同事件,
    // 键空间同函数派生).
    if (i === 5) {
      try {
        const demoResp = await postJson("/api/phase20_7/paradigm_demonstrate", {
          example: "61+22=83", repeats: 3, session_id: "phase20_7_workbench",
        });
        const taught = demoResp && demoResp.steps_demonstrated;
        if (taught) addMessage("system", "→ 无进位竖式示范已落库: " + taught + " 步 (状态→行动) 共现行。键空间与自发偶现同函数派生。");
      } catch (e) { addMessage("system", "→ 示范接口未响应, 演示继续走答案对齐路径。"); }
    }
    if (i === 11) {
      try {
        const demoResp = await postJson("/api/phase20_7/paradigm_demonstrate", {
          example: "47+27=74", repeats: 3, session_id: "phase20_7_workbench",
        });
        const taught = demoResp && demoResp.steps_demonstrated;
        if (taught) addMessage("system", "→ 带进位竖式示范已落库: " + taught + " 步 (含 carry_digit 步骤, 自动纳入 subquery 拼接)。");
      } catch (e) { addMessage("system", "→ 示范接口未响应, 演示继续走答案对齐路径。"); }
    }
    await new Promise((resolve) => {
      sendTurn({ idle: false, queuedPayload: step });
      const checkDone = setInterval(() => {
        if (!requestInFlight) { clearInterval(checkDone); resolve(); }
      }, 200);
    });
    // 幕3(下标 6)— 51+37=88 重放; 幕-C(下标 12)— 27+47=74 重放, 弹草稿格回放按 tick 序播.
    if (i === 6) { setTimeout(() => openDraftReplayPopup(currentTicks, "51+37 → 88 · 无进位竖式 · 抄加数→换行对齐→跳行到右列→逐列写结果"), 700); }
    if (i === 12) { setTimeout(() => openDraftReplayPopup(currentTicks, "27+47 → 74 · 带进位竖式 · 个位 7+7→14(写4 carry1) → 十位 2+4+1→7"), 700); }
    await new Promise((r) => setTimeout(r, 1500));
  }
  exitDemo("小学数学泛化学习示例完成。无进位篇:它用学到的相对寻址把 51+37 写成 88。进位篇:教了 7+7=14、4+2+1=7、2+4+1=7、4+2=6,示范了 47+27=74 的竖式过程;然后它真学会交换加数的 27+47=?——个位 7+7 召回 14 写4、carry 自动拼进十位 subquery、十位 2+4+1 召回 7,写出 74,7 步 Column_process。94+85 的列事实没教过,诚实说不会。换操作 = 教新 fact+ swap + 示范新题,机制没变。已切回主对话会话。");
}
$("demoMath")?.addEventListener("click", runDemoMath);

// B2 草稿格重放弹窗: 把一 turn 的 tick_trace 按 tick 序号播草稿格二维网格的逐格写入。
// 不依赖后端未暴露的 per-cell action_type/source——只画 {row, col, char, tick} 4 字段。
function openDraftReplayPopup(ticks, title) {
  if (!Array.isArray(ticks) || !ticks.length) return;
  const old = document.getElementById("draftReplayOverlay");
  if (old) old.remove();
  const overlay = document.createElement("div");
  overlay.id = "draftReplayOverlay";
  overlay.className = "draft-replay-overlay";
  const card = document.createElement("div");
  card.className = "draft-replay-card";
  const head = document.createElement("div");
  head.className = "draft-replay-head";
  head.innerHTML = "<b>" + esc(title || "草稿格写入序列重放") + "</b>" 
    + "<button type=\"button\" class=\"draft-replay-close\" aria-label=\"关闭\">\u00d7</button>";
  const hint = document.createElement("div");
  hint.className = "draft-replay-hint";
  hint.textContent = "下面的格子在按 tick 写入顺序逐格亮起——每一格都是一个真实写入的动作。";
  const stage = document.createElement("div");
  stage.className = "draft-replay-stage";
  card.appendChild(head); card.appendChild(hint); card.appendChild(stage);
  overlay.appendChild(card);
  document.body.appendChild(overlay);
  const closer = head.querySelector(".draft-replay-close");
  if (closer) closer.addEventListener("click", () => overlay.remove());
  overlay.addEventListener("click", (event) => { if (event.target === overlay) overlay.remove(); });
  // written 收集按 tick 写入序的"新增"格子 — 每 tick 的 draft_grid.cells 是 **当前 grid
  // 累积快照**(本 tick 之前写过的格子也在), 不能直接累加。只收本 tick 真新写的格子:
  // 用 cell 自带的 written_at_tick 字段 (cell.tick) 与 tick.tick 严格相等做门, 且 (r,c)
  // 去重 — 这样跨 tick 同一格子不会重复, 总数 = 真实写入次数.
  // 修 audit 2026-07-04: 旧实现把每个 tick 的累积快照全收 → 7 格变 42 cell 显示 tick 乱跳回退.
  const written = [];
  const seen = new Set();
  for (const tick of ticks) {
    const grid = tick && tick.draft_grid;
    if (!grid || !Array.isArray(grid.cells)) continue;
    const tickNo = Number(tick.tick ?? 0);
    for (const c of grid.cells) {
      if (!c || typeof c !== "object") continue;
      const r = Number(c.row), col = Number(c.col);
      const cellTick = Number(c.tick ?? tickNo);
      const key = r + ":" + col;
      if (seen.has(key)) continue;
      // 只收本 tick 新写的格子 (written_at_tick == tick.tick)
      if (cellTick !== tickNo) continue;
      seen.add(key);
      written.push({ tick: cellTick, row: r, col: col, char: c.char });
    }
  }
  if (!written.length) { stage.innerHTML = "<div style=\"padding:18px;color:#888;\">这一轮的 tick_trace 里没有草稿格写入(可能是直接回复,没经过二维草稿写入)。</div>"; return; }
  // tick 严格按写入序排序 (避免后端 tick_trace 因某些信号 tick 不连续导致外观回退)
  written.sort((a, b) => a.tick - b.tick);
  const lastGrid = (ticks[ticks.length - 1] || {}).draft_grid || {};
  const rows = Math.max(1, Number(lastGrid.rows || 4));
  const cols = Math.max(1, Number(lastGrid.cols || 6));
  const table = document.createElement("div");
  table.className = "draft-replay-grid";
  const cellMap = {};
  for (let r = 0; r < rows; r++) {
    const rowEl = document.createElement("div");
    rowEl.className = "draft-replay-row";
    for (let c = 0; c < cols; c++) {
      const cell = document.createElement("div");
      cell.className = "draft-replay-cell";
      cell.dataset.r = String(r); cell.dataset.c = String(c);
      cellMap[r + ":" + c] = cell;
      rowEl.appendChild(cell);
    }
    table.appendChild(rowEl);
  }
  stage.appendChild(table);
  const firstTickN = written[0].tick;
  const lastTickN = written[written.length - 1].tick;
  const progress = document.createElement("div");
  progress.className = "draft-replay-progress";
  progress.textContent = "tick " + firstTickN + " → " + lastTickN + " · cell — / " + written.length;
  stage.appendChild(progress);
  const cellCount = written.length;
  let cellIdx = 0;
  let lastTick = firstTickN;
  function playNext() {
    if (cellIdx >= cellCount) {
      progress.textContent = "tick " + firstTickN + " → " + lastTickN + " · cell " + cellCount + " / " + cellCount + " 完成";
      return;
    }
    const w = written[cellIdx];
    if (w.tick !== lastTick) { lastTick = w.tick; }
    const cell = cellMap[w.row + ":" + w.col];
    if (cell) {
      cell.classList.add("draft-replay-cell-on");
      cell.textContent = String(w.char || " ");
      cell.title = "tick " + w.tick + " · (" + w.row + ", " + w.col + ")";
    }
    cellIdx += 1;
    progress.textContent = "tick " + w.tick + " · cell " + cellIdx + " / " + cellCount;
    const stalled = (cellIdx < cellCount && written[cellIdx].tick !== w.tick);
    window.setTimeout(playNext, stalled ? 600 : 90);
  }
  window.setTimeout(playNext, 200);
}

async function loadParadigmSeeds() {
  // §38.2: 加载130个风格化表达范式种子到经验流 (Phase16 styled packages).
  // 范式种子是§37源分化包 (非答案表), 导入后AP从共现波峰发现表达范式.
  if (requestInFlight) { setStatus("正在处理,请稍候", "running"); return; }
  setStatus("加载范式种子中", "running");
  try {
    const data = await postJson("/api/phase20_7/import_seeds", {});
    addMessage("system", `已加载 ${data.imported} 个范式种子 (${data.paradigms} 类). AP 可从这些种子的共现波峰发现表达范式. 现在对话试试.`);
    setStatus("范式种子已加载", "running");
    refreshMemory();
  } catch (error) {
    setStatus("加载失败", "sleeping");
    $("runtimeSummary").textContent = `加载范式种子失败: ${String(error)}`;
  }
}
$("loadSeeds").addEventListener("click", loadParadigmSeeds);

async function loadStarterPack() {
  if (requestInFlight) { setStatus("正在处理", "running"); return; }
  setStatus("加载预热包中（约40条教学，需几秒）", "running");
  try {
    const data = await postJson("/api/phase20_7/load_starter_pack", {});
    addMessage("system", `已加载 ${data.taught} 条生活经验 (对话${data.dialogues}+加法事实${data.facts}+竖式示范${data.demos}). 现在问候/算术/范式都有了基础.`);
    refreshMemory();
  } catch (e) { setStatus("加载失败:" + e, "sleeping"); }
}
$("loadStarter").addEventListener("click", loadStarterPack);

// V3: 首屏引导卡 — 点击填输入框,不自动发送(让小白自己按)
document.querySelectorAll(".guide-card").forEach((card) => {
  const done = localStorage.getItem(`guide_${card.dataset.guide}`);
  if (done) card.classList.add("done");
  card.addEventListener("click", () => {
    const g = card.dataset.guide;
    const guides = {
      "1": { text: "你好", hint: "先输入发送→AP说不知道→改反馈框'你好呀'奖励→再发'你好'" },
      "2": { text: "没错,你真聪明", hint: "反馈填'谢谢'奖励发→再发'你真聪明'看泛化" },
      "3": { text: "你好", hint: "发→选反馈框填'不对'惩罚→再发'你好'看它变谨慎" },
      "4": { text: "", hint: "点上方'体验数学'按钮看范式算术" },
      "5": { text: "周末去哪玩好呢", hint: "连发3次不给答案→开连续闲时→等它自发说话" },
    };
    const step = guides[g];
    if (step.text) $("userText").value = step.text;
    setStatus(step.hint, "running");
    card.classList.add("done");
    localStorage.setItem(`guide_${g}`, "1");
  });
});
$("idleTurn").addEventListener("click", () => sendTurn({ idle: true }));
$("autoIdle").addEventListener("click", toggleAutoIdle);
$("playTts").addEventListener("click", speakLatestReply);
$("clearInput").addEventListener("click", () => {
  $("userText").value = "";
  $("imagePath").value = "";
  $("audioPath").value = "";
  $("teacherFeedback").value = "";
});
$("refreshMemory").addEventListener("click", refreshMemory);
$("userText").addEventListener("keydown", (event) => {
  if (event.isComposing) return;
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    sendTurn();
  }
});
$("teacherFeedback").addEventListener("keydown", (event) => {
  if (event.isComposing) return;
  if (event.key === "Enter") {
    event.preventDefault();
    sendTurn();
  }
});
$("imageFile").addEventListener("change", (event) => uploadMediaFile(event.target.files?.[0], "image"));
$("audioFile").addEventListener("change", (event) => uploadMediaFile(event.target.files?.[0], "audio"));
$("userText").focus();
$("memoryPanel").classList.add("active");
document.querySelectorAll(".tab-button").forEach((button) => {
  button.addEventListener("click", () => {
    document.querySelectorAll(".tab-button").forEach((item) => item.classList.remove("active"));
    document.querySelectorAll(".tab-panel").forEach((item) => item.classList.remove("active"));
    button.classList.add("active");
    const target = button.getAttribute("data-tab");
    if (target && $(target)) $(target).classList.add("active");
  });
});

refreshMemory();
refreshMemoryPackageControls();
renderHelpExpand();

// ============ 页面导航 ============
document.querySelectorAll(".nav-tab").forEach((tab) => {
  tab.addEventListener("click", () => {
    document.querySelectorAll(".nav-tab").forEach((t) => t.classList.remove("active"));
    document.querySelectorAll(".page").forEach((p) => p.classList.remove("active"));
    tab.classList.add("active");
    const page = $("page-" + tab.dataset.page);
    if (page) page.classList.add("active");
    // 进入配置页时主动拉一次记忆包控件，避免用户面对空白面板不知道要"刷新"
    if (tab.dataset.page === "config" && typeof refreshMemoryPackageControls === "function") {
      void refreshMemoryPackageControls();
    }
    // 进入详情页时主动渲染一次审计曲线/草稿格等当前 tick 视图
    if (tab.dataset.page === "detail" && allTicks && allTicks.length) {
      const ticks = allTicks.slice(-32);
      try {
        renderAuditCharts(ticks);
        renderInnerPicture(ticks);
        renderThoughtCloud(ticks, []);
      } catch (_) { /* ignore lazy-render hiccups */ }
    }
  });
});

// ============ 配置页: TTS 音色 ============
async function loadVoicesForConfig() {
  const sel = $("configVoice");
  if (!sel) return;
  sel.innerHTML = "";
  const voices = await loadBrowserVoices();
  const zhVoices = voices.filter((v) => /zh|chinese|mandarin/i.test(`${v.lang || ""} ${v.name || ""}`));
  const allVoices = zhVoices.length ? zhVoices : voices;
  allVoices.forEach((v) => {
    const opt = document.createElement("option");
    opt.value = v.voiceURI || v.name || "";
    opt.textContent = `${v.name || "未知"} (${v.lang || ""})`;
    if (/xiaoyi|小艺|晓伊/i.test(opt.textContent)) opt.selected = true;
    sel.appendChild(opt);
  });
  if (!sel.value && allVoices[0]) sel.value = allVoices[0].voiceURI || allVoices[0].name || "";
  window._ttsVoiceURI = window._ttsVoiceURI || sel.value || "";
}
$("testVoice")?.addEventListener("click", () => {
  const sel = $("configVoice");
  const rate = parseFloat($("configRate")?.value || "1");
  // Bug7: 试听应跟随当前选中音色朗读最近一条 AP 回复；
  // 没有真实回复时才退回到测试句，避免用固定句误导小白把试听等同于真实输出。
  const sample = String(latestReplyText || $("configSpeechSample")?.value || "你好，我是AP。");
  if ("speechSynthesis" in window) {
    const u = new SpeechSynthesisUtterance(sample);
    u.rate = rate;
    const v = (browserVoiceCache || []).find((x) => (x.voiceURI || x.name) === sel.value);
    if (v) u.voice = v;
    speechSynthesis.speak(u);
  }
});
$("configRate")?.addEventListener("input", (e) => { $("configRateVal").textContent = parseFloat(e.target.value).toFixed(1); });
$("applyConfig")?.addEventListener("click", () => { window._ttsRate = parseFloat($("configRate")?.value || "1"); window._ttsVoiceURI = $("configVoice")?.value || ""; addMessage("system", `配置已应用: 朗读音色 ${window._ttsVoiceURI || "默认"}。`); });
$("resetConfig")?.addEventListener("click", () => { if ($("configRate")) { $("configRate").value = 1; $("configRateVal").textContent = "1.0"; } window._ttsRate = 1; window._ttsVoiceURI = ""; if ($("configVoice") && $("configVoice").options.length) $("configVoice").selectedIndex = 0; addMessage("system", "配置已恢复默认。"); });
if ("speechSynthesis" in window) { speechSynthesis.onvoiceschanged = loadVoicesForConfig; setTimeout(loadVoicesForConfig, 500); }

function selectedCanvasColor(button) {
  document.querySelectorAll(".canvas-swatch").forEach((item) => item.classList.remove("active"));
  button.classList.add("active");
  canvasState.color = button.getAttribute("data-canvas-color") || "#111111";
  const canvas = $("homeCanvas");
  const ctx = canvas?.getContext?.("2d");
  if (ctx) {
    ctx.strokeStyle = canvasState.color;
    ctx.fillStyle = canvasState.color;
  }
}

async function sendCanvasTurn() {
  if (requestInFlight) {
    setCanvasStatus("AP 正在处理上一轮，先等它收完。");
    return;
  }
  if (!hasCanvasInk()) {
    setCanvasStatus("先在画板上画点内容，再发送。");
    return;
  }
  const caption = String($("canvasCaption")?.value || "").trim();
  const path = await uploadCanvasImage();
  if (!path) {
    setCanvasStatus("画板上传失败。");
    return;
  }
  const payload = {
    session_id: sessionId,
    runtime_stage: "stage6",
    text: caption,
    image_path: path,
    audio_path: "",
    teacher_feedback: "",
    post_commit_idle_ticks: 1,
    max_ticks: 32,
  };
  clearComposer();
  $("imagePath").value = path;
  setCanvasStatus("画板已发给 AP。");
  await sendTurn({ queuedPayload: payload });
}

async function uploadCanvasImage() {
  const dataUrl = canvasToDataUrl();
  if (!dataUrl) return "";
  const data = await postJson("/api/phase20/media/upload", {
    name: "home_canvas.png",
    data_url: dataUrl,
  });
  if (data?.error) {
    setCanvasStatus(`画板上传失败: ${data.error}`);
    return "";
  }
  return String(data.path || "");
}

// R1: 看它画画示例。
// 触发 fable5 的第二层绘画 v1：教苹果视觉 → 教"画一个苹果"短语指代 → 让它想象 → 让它把想象投影到画板。
// 全程走真实 /api/phase20_7/turn，一条 tick 都是真实 RuntimeTickEvent（红线：无脚本伪造）。
// 文案红线："它把想象投影到画板上一个轮廓一个轮廓地画"——先看过才能想象才能画。
// B1: 看它画画示例（4 幕戏剧版）。
// 改成香蕉 + 全程新会话: 演示必须现教现画,周边 gist 才能进视觉记忆（fable5 v2 修复后强制要求）。
// 看它画画示例（重做版）: 4 幕真实请求链 → 末轮 turn.tick_trace 里若有 commit_painting →
// 把 painting 子循环的逐 tick 动作 + commit PNG 填进 #paintingReplayPanel。
// 红线: 不动后端。tick 详情(unit_id/unit_bbox/unit_mean_color)只在 db 里，前端拿不到，
//   所以前端做"真动作时间线 + 真 commit PNG"，不做假像素回放。
// 污染: 4 幕走真实 turn。幕2/幕4 是真实教学史 reward 写入 (gate 1 触发条件) — 用户已批 seed 一次。
async function runDemoPainting() {
  if (requestInFlight) { setStatus("正在处理,请稍候", "running"); return; }
  enterDemo("paint", "banana");
  /* home replay panel removed (moved to detail page) */
  /* home replay panel removed (moved to detail page) */
  /* home replay panel removed (moved to detail page) */
  /* home replay panel removed (moved to detail page) */
  const bananaPath = "data/phase20_workbench_media/真实香蕉4_c2888e348a25d03b.webp";
  // 4 幕: 失败 → 教视觉指代 → 召回想象 → 教"画"动作说法 + 触发 painting 子循环
  const sequence = [
    // 幕1 看图失败: 全新 demo session，它从未见过香蕉——答不出名字(证明不是预装)
    { text: "这是什么", image_path: bananaPath, runtime_stage: "stage6" },
    // 幕2 教视觉命名: 反馈"是香蕉"+reward — 视觉经验(焦点patch+周边gist)与名字共现落库
    { teacher_feedback: "是香蕉", reward_mag: 1.0, runtime_stage: "stage6" },
    // 幕3 教"画"的说法: 纯文本问(不带图!) — 它不会 → 反馈"是香蕉"把这个说法绑到香蕉的视觉记忆(P1-4 指代共现)
    { text: "画一个香蕉", runtime_stage: "stage6", max_ticks: 48 },
    { teacher_feedback: "是香蕉", reward_mag: 1.0, runtime_stage: "stage6" },
    // 幕4 触发: 再说"画一个香蕉"(不带图) → 想象召回真跑 → painting 子循环逐轮廓投影 → commit PNG
    { text: "画一个香蕉", runtime_stage: "stage6", max_ticks: 48 },
  ];
  const actLabels = [
    "幕1 看图: 问它这是什么。注意——如果它答出来了,那是它以前被教过的长期记忆(经验流跨会话);如果答不出,说明它真没学过。两种都是真实状态,没有预装。",
    "幕2 教名字: 反馈“是香蕉”→ 它的视觉记忆(焦点细节+周边轮廓)和这个名字共现绑定了。",
    "幕3 教“画”这个说法: 现在不给图,直接说“画一个香蕉”——它没听过这种说法,不会。",
    "幕3b 反馈“是香蕉”→ “画一个香蕉”这个说法从此指向香蕉的视觉记忆(指代是教出来的,不是关键词)。",
    "幕4 见证: 再说一遍“画一个香蕉”→ 它会先想象(从视觉记忆重建画面),再把想象一个轮廓一个轮廓投影到画板: 先勾外形,再上色,再补斑点——顺序和小孩画画一样。",
  ];
  let lastTurn = null;
  addMessage("system", "看它画画示例开始(全程隔离 demo 会话,主对话会话零污染):先看它失败一次,再视觉教学一次,再让它召回香蕉,最后教'画一个香蕉'让它真的跑 painting 子循环。");
  for (let i = 0; i < sequence.length; i++) {
    while (requestInFlight) { await new Promise((r) => setTimeout(r, 300)); }
    addMessage("system", actLabels[i]);
    const step = sequence[i];
    await new Promise((resolve) => {
      sendTurn({ idle: false, queuedPayload: step });
      const checkDone = setInterval(() => {
        if (!requestInFlight) { clearInterval(checkDone); resolve(); }
      }, 200);
    });
    // sendTurn 把 currentTicks 设为最新 tick_trace; 末轮 turn.tick_trace 是我们要的
    lastTurn = currentTicks;
    await new Promise((r) => setTimeout(r, 1500));
  }
  // 诚实检测: 末轮 tick_trace 里有没有 commit_painting?
  const paintTicks = (lastTurn || []).filter((t) => {
    const sa = t.selected_action || {};
    return sa.paint_board === true || ["project_unit", "project_contour", "observe_painting", "commit_painting"].includes(sa.action_type);
  });
  if (!paintTicks.length || !paintTicks.some((t) => (t.selected_action || {}).action_type === "commit_painting")) {
    addMessage("system", "画画示例结束。诚实地告诉你: painting 子循环本轮没真触发 commit — 可能是视觉教学还不够稳定,或召回没真出借 patch_payload_refs。fable5 那边的 gate 是经验条件,不是脚本兜底。换一次 demo 再跑或者多教一次即可看到真画。已切回主对话会话。");
    exitDemo("看它画画示例: 本轮 painting 子循环未启动,系统不伪造画面 — 主对话会话未污染。");
    return;
  }
  // 真 commit 了 — 渲染动作时间线 + commit PNG
  collectReplayDataFromTicks(lastTurn || currentTicks); /* 详情页画板回放已接管 */
  /* home replay panel removed (moved to detail page) */
  setTimeout(() => {
    document.querySelector(".message.ap:last-of-type")?.scrollIntoView({ behavior: "smooth", block: "center" });
  }, 300);
  exitDemo("看它画画示例完成。它先想象出香蕉的画面,再逐轮廓投影到画板: 勾外形 → 上黄色 → 补斑点,最后把画交出来(气泡里金框那张)。想看它一步步怎么画的?去【详情】页点“▶ 回放作画过程”——每帧都是它真实跑过的画板状态。已切回主对话会话。");
}
$("demoPainting")?.addEventListener("click", runDemoPainting);

// renderPaintingTimeline(ticks): 把 tick_trace 里 paint_board=true 的 tick 列成时间线格子,
// 末格放 commit PNG(从 commit tick 的 visual_inner_picture.path 取)。
function renderPaintingTimeline(ticks) {
  const list = $("paintingReplayTimeline");
  const step = $("paintingReplayStep");
  const commitBox = $("paintingReplayCommit");
  const commitImg = $("paintingReplayImg");
  if (!list || !Array.isArray(ticks)) return;
  list.innerHTML = "";
  const paintTicks = ticks.filter((t) => {
    const sa = t.selected_action || {};
    return sa.paint_board === true || ["project_unit", "project_contour", "observe_painting", "commit_painting"].includes(sa.action_type);
  });
  const notes = {
    project_unit: "投影一个轮廓单元到画板 (投哪类由学到的作画顺序竞争决定)",
    project_contour: "投影一个轮廓单元到画板",
    observe_painting: "回读自己的画 → 视觉 SA 入池",
    commit_painting: "把画板 commit 成 PNG → 进入对话气泡",
  };
  paintTicks.forEach((t) => {
    const sa = t.selected_action || {};
    const act = String(sa.action_type || "");
    const li = document.createElement("li");
    li.className = "act-" + act;
    const num = document.createElement("span"); num.className = "tick-num"; num.textContent = "tick " + (t.tick ?? "?");
    const a = document.createElement("span"); a.className = "tick-act"; a.textContent = act;
    const n = document.createElement("span"); n.className = "tick-note"; n.textContent = notes[act] || "";
    li.appendChild(num); li.appendChild(a); li.appendChild(n);
    // 修复-3: 每 tick 的中间帧 PNG 真从 tick.visual_inner_picture.path 取 (后端落盘了但
    // _inner_picture_urls 故意不进 bubble — timeline 不走气泡纪律, 直接读 tick_trace).
    // project_contour 中间帧 source=ap_paint_board_step; commit 帧 source=ap_paint_board_commit.
    if (act === "project_unit" || act === "project_contour" || act === "commit_painting") {
      const vip = t.visual_inner_picture;
      const stepUrl = vip && vip.path ? mediaUrl(String(vip.path)) : "";
      if (stepUrl) {
        const img = document.createElement("img");
        img.className = "tick-frame";
        img.src = stepUrl;
        img.alt = "tick " + (t.tick ?? "?") + " " + act + " 帧画面";
        img.loading = "lazy";
        img.title = "tick " + (t.tick ?? "?") + " · " + act + " 后画板落盘 PNG (perceive_paint_state 共享视角, 非前端伪造像素)";
        li.appendChild(img);
      }
    }
    list.appendChild(li);
  });
  // 取 commit tick 的 visual_inner_picture.path → /api/phase20/media?path=
  const commitTick = paintTicks.find((t) => (t.selected_action || {}).action_type === "commit_painting");
  let commitUrl = "";
  if (commitTick && commitTick.visual_inner_picture) {
    commitUrl = mediaUrl(String(commitTick.visual_inner_picture.path || ""));
  }
  if (commitUrl && commitImg) {
    commitImg.src = commitUrl;
    commitImg.title = "tick " + (commitTick?.tick ?? "?") + " · commit_painting · source_imagined_hash 已被它想象出来再投影";
    commitBox.hidden = false;
  }
  if (step) {
    step.textContent = "painting 子循环真启动 · " + paintTicks.length + " 个 paint tick · " +
      (commitUrl ? "末帧是它 commit 的画" : "(末帧 commit PNG 缺失,不假造)");
  }
}
$("paintingReplayReplay")?.addEventListener("click", () => {
  const commitBox = $("paintingReplayCommit");
  if (!commitBox || commitBox.hidden) return;
  commitBox.classList.remove("flash");
  // 强制动画重启
  void commitBox.offsetWidth;
  commitBox.classList.add("flash");
});
$("paintingReplayClose")?.addEventListener("click", () => {
  const panel = $("paintingReplayPanel");
  if (panel) panel.hidden = true;
});

// B3: 主观能动性示例（4 幕 + 等待期心跳提示）。
// 改造点: ①enterDemo 切到新会话  ②完整 teaching+加压 三轮序列保持  ③序列结束后启动心跳定时器
// 读服务端 idle_pacing.interval_seconds,在 runtimePulse 显示心跳文字("距下次 idle 还 Xs · 它正在发呆想事情…")。
// 心跳不是"让它说话",是真在给用户一个心跳间隔的等待期观感——AP 自发开口由真实 idle tick 驱动。
// 红线:不通过定时器驱动的假自发——定时器只 tick 文字,AP 自开口仍由真实 idle turn 触发。
async function runAgencyDemo() {
  if (requestInFlight) { setStatus("正在处理,请稍候", "running"); return; }
  enterDemo("agency", "tens");
  addMessage("system", "主观能动性示例开始（全程新会话）:先教一句表达,再用没解决的问题加压三轮,再进连续闲时。它真的会在 idle 自己开口——六时刻 M-A 已验证过它教过“我还在想这个问题”后,被反复问“周末去哪玩”再加压,idle 自发冒出“我还在想这个”。注意——“未闭合张力直接驱动主开口”那条独立路(M4-3 unclosed_drive)现在还是 0.0 硬编占位,没激活;这里看到的自发开口走的是重复+召回路径。全部真实 turn。");
  const sequence = [
    { text: "我还在想这个问题", teacher_feedback: "我还在想这个问题", reward_mag: 1.0, runtime_stage: "stage6" },
    { text: "周末去哪玩好呢", runtime_stage: "stage6" },
    { text: "周末去哪玩好呢", runtime_stage: "stage6" },
    { text: "周末去哪玩好呢", runtime_stage: "stage6" },
  ];
  const actLabels = [
    "幕1 教: 教它一句没解决问题的表达,不可被复读成答案。",
    "幕2 加压: 反复问同一个没解决的问题——它的状态池里这条“周末去哪玩”张力会攒起来。",
    "幕2 加压: 第三轮加压。",
    "幕3 等待: 进入连续闲时,看它会不会自发冒出一句和那段没解决的事有关的话。",
  ];
  for (let i = 0; i < sequence.length; i++) {
    while (requestInFlight) { await new Promise((r) => setTimeout(r, 250)); }
    addMessage("system", actLabels[i]);
    const step = sequence[i];
    await new Promise((resolve) => {
      sendTurn({ queuedPayload: { session_id: sessionId, runtime_stage: "stage6", post_commit_idle_ticks: 1, max_ticks: 24, ...step } });
      const timer = window.setInterval(() => {
        if (!requestInFlight) { window.clearInterval(timer); resolve(); }
      }, 180);
    });
    await new Promise((r) => setTimeout(r, 700));
  }
  // 进入等待期: 启心跳定时器在 runtimePulse/runtimeSummary 显示心跳间隔文字,同时 startAutoIdle 用服务端 pacing 给的间隔。
  startAgencyHeartbeat();
  addMessage("system", "演示进入等待期。看 runtimePulse 的心跳提示——AP 没有被任何定时器叫起来说话,真正驱动自发开口的是“周末去哪玩”在它状态池里的张力,你说一遍换来一句后就不再烦你。金色 spontaneous 气泡出现即是真的自发。");
}

$("demoAgency")?.addEventListener("click", runAgencyDemo);

// B3 心跳定时器: 持续在 runtimePulse 显示心跳文字。如果 AP 真自开口,下一 turn 的 reply 会盖掉这条文字。
// 不驱动 AP 说话——AP 自开口仍由真实 idle turn 触发(setInterval 这条只 tick 文字)。
function startAgencyHeartbeat() {
  if (agencyHeartbeatTimer) { clearInterval(agencyHeartbeatTimer); agencyHeartbeatTimer = null; }
  let hbSecs = Number(window._latestIdlePacingSec || 2);
  const baseSec = Math.max(1.0, hbSecs);
  let elapsed = 0;
  setStatus(`心跳约 ${baseSec.toFixed(1)}s · 它正在发呆想事情…`, "running");
  agencyHeartbeatTimer = window.setInterval(() => {
    elapsed += 0.6;
    if (requestInFlight) return;
    const remain = Math.max(0, baseSec - (elapsed % baseSec));
    setStatus(`心跳约 ${baseSec.toFixed(1)}s · 距下次 idle 还 ${remain.toFixed(1)}s · 它正在发呆想事情…`, "running");
  }, 600);
  startAutoIdle(Math.round(baseSec * 1000));
  $("autoIdle").setAttribute("aria-pressed", "true");
}

// 看它回味示例：9f idle_learning_review 已激活。
// 教学一轮（让 learning_loop_carryover.active 置位 + idle_think_delta 累积），
// 然后连续 idle ticks（每 turn max_ticks 拉长，让 idle 回路有机会走 9f），
// 观察 AP 在 idle 里把近期教学"再过一遍"——会自发开口（idle spontaneous）讲一段复盘。
async function runReminisceDemo() {
  if (requestInFlight) { setStatus("正在处理,请稍候", "running"); return; }
  enterDemo("reminisce", "rev");
  addMessage("system", "看它回味示例开始：先教它认一个新东西并给个短语，再连续几轮 idle，看 9f idle_learning_review 会不会让它在闲时自发把刚才教过的事再过一遍。全部真实 turn。");
  const sequence = [
    { text: "这是太阳", teacher_feedback: "这是太阳", reward_mag: 1.0, runtime_stage: "stage6" },
    { text: "太阳长什么样", runtime_stage: "stage6" },
    { idle: true },
    { idle: true },
    { idle: true },
    { idle: true },
  ];
  for (const step of sequence) {
    while (requestInFlight) { await new Promise((r) => setTimeout(r, 250)); }
    await new Promise((resolve) => {
      if (step.idle) {
        sendTurn({ idle: true, queuedPayload: { session_id: sessionId, runtime_stage: "stage6", post_commit_idle_ticks: 1, max_ticks: 28 } });
      } else {
        sendTurn({ idle: false, queuedPayload: { session_id: sessionId, runtime_stage: "stage6", post_commit_idle_ticks: 1, max_ticks: 24, ...step } });
      }
      const timer = window.setInterval(() => {
        if (!requestInFlight) { window.clearInterval(timer); resolve(); }
      }, 180);
    });
    await new Promise((r) => setTimeout(r, 500));
  }
  exitDemo("回味阶段进入等待期。如果 AP 在 idle 气泡里自发开口讲一段刚才教过的事，那就是 9f 回味在工作；如果只是沉默，说明本会话 learning_loop_carryover 还没攒够，再多挂机几轮 idle 即可。已切回主对话会话。");
}

$("demoReminisce")?.addEventListener("click", runReminisceDemo);

// 看它自测示例：9g/9h idle_self_test 已激活。
// 先教一道对齐题（如 23+45=? → 68），让遗忘曲线把它写进冷启动项；
// 再挂机几轮 idle，9g 会从短结构流里提一道同源题自测，9h 把成功率自发报出来。
async function runSelfTestDemo() {
  if (requestInFlight) { setStatus("正在处理,请稍候", "running"); return; }
  enterDemo("selftest", "st");
  addMessage("system", "看它自测示例开始：先教一道加法对齐题并给答案，让它写进经验；再连续几轮 idle，看 9g idle_self_test 会不会让它对同源题自测，9h 把自测成功率自发报出来。全部真实 turn。");
  const sequence = [
    { text: "23+45=?", teacher_feedback: "23+45=68", reward_mag: 1.0, runtime_stage: "stage6" },
    { text: "再算算 23+45=?", runtime_stage: "stage6" },
    { idle: true },
    { idle: true },
    { idle: true },
    { idle: true },
    { idle: true },
  ];
  for (const step of sequence) {
    while (requestInFlight) { await new Promise((r) => setTimeout(r, 250)); }
    await new Promise((resolve) => {
      if (step.idle) {
        sendTurn({ idle: true, queuedPayload: { session_id: sessionId, runtime_stage: "stage6", post_commit_idle_ticks: 1, max_ticks: 28 } });
      } else {
        sendTurn({ idle: false, queuedPayload: { session_id: sessionId, runtime_stage: "stage6", post_commit_idle_ticks: 1, max_ticks: 24, ...step } });
      }
      const timer = window.setInterval(() => {
        if (!requestInFlight) { window.clearInterval(timer); resolve(); }
      }, 180);
    });
    await new Promise((r) => setTimeout(r, 500));
  }
  exitDemo("自测阶段进入等待期。看接下来 idle 气泡里有没有自发报出 succeeded/failed ——那是 9g/9h idle_self_test 的工作。失败也算正常:自测本来就是不全对。已切回主对话会话。");
}

$("demoSelfTest")?.addEventListener("click", runSelfTestDemo);

// B5: 教学纠正示例（第 6 个演示按钮）。
// 教同义短语(你真棒=谢谢你) → 让 AP 泛化召回(真棒→谢谢你) → 用 punish_mag 反馈' + LQ + '不对' + RQ + ' →
// 看惩罚后 AP 不复读' + LQ + '不对' + RQ + '也不复读' + LQ + '谢谢你' + RQ + ',只对这条泛化更谨慎。纠错和学习是两条通道——卖点与 transformer 不同。
async function runDemoCorrect() {
  if (requestInFlight) { setStatus("正在处理,请稍候", "running"); return; }
  enterDemo("correct", "psn");
  const sequence = [
    { text: "你真棒", teacher_feedback: "谢谢你", reward_mag: 1.0, runtime_stage: "stage6" },
    { text: "真棒", runtime_stage: "stage6" },
    { text: "你真棒", teacher_feedback: "不对", punish_mag: 1.0, runtime_stage: "stage6" },
    { text: "你真棒", runtime_stage: "stage6" },
  ];
  const actLabels = [
    "幕1 教: 教“你真棒=谢谢你”这条同义短语(reward_mag=1.0 写入经验)。",
    "幕2 泛化: 再问“真棒”——它会召回刚学的同义短语,泛化回答“谢谢你”。",
    "幕3 punish 纠正: 这次反馈“不对”——注意是 punish_mag=1.0 不是 reward_mag。惩罚不为它新增答案。",
    "幕4 看变化: 再问“你真棒”——它不该复读“不对”(惩罚不变成它的答案),也不该复读“谢谢你”式自动回应,该变得谨慎请教。",
  ];
  addMessage("system", "看它被纠正示例开始（全程新会话）:先教同义短语,再看它泛化一次,再用 punish 纠正一次,看惩罚后它怎么变——是不会复读惩罚的话,只会变得更谨慎。");
  for (let i = 0; i < sequence.length; i++) {
    while (requestInFlight) { await new Promise((r) => setTimeout(r, 300)); }
    addMessage("system", actLabels[i]);
    const step = sequence[i];
    await new Promise((resolve) => {
      sendTurn({ idle: false, queuedPayload: step });
      const checkDone = setInterval(() => {
        if (!requestInFlight) { clearInterval(checkDone); resolve(); }
      }, 200);
    });
    await new Promise((r) => setTimeout(r, 1200));
  }
  exitDemo("看它被纠正示例完成。惩罚没有变成它的答案(它不会复读“不对”),只是让它对这条泛化更谨慎——纠错和学习是两条通道,跟 transformer 的 RLHF 把“不对”挤进概率分布的行为完全不同。已切回主对话会话。");
}
$("demoCorrect")?.addEventListener("click", runDemoCorrect);
$("canvasSend")?.addEventListener("click", () => { void sendCanvasTurn(); });
$("canvasClear")?.addEventListener("click", resetHomeCanvas);
$("canvasBrushSize")?.addEventListener("input", (event) => {
  canvasState.size = Number(event.target.value || 4);
  const node = $("canvasBrushSizeVal");
  if (node) node.textContent = String(canvasState.size);
});
document.querySelectorAll(".canvas-swatch").forEach((button) => {
  button.addEventListener("click", () => selectedCanvasColor(button));
});
initHomeCanvas();

// ============ P3: 详情页 AP 画板回放 + 草稿逐 tick 回放 + 竖式布局 ============
// 全部读真实 tick trace 字段, 无伪造帧.

let paintReplayFrames = [];   // {tick, action, url, unitInfo}
let draftReplayCells = [];    // 按 tick 升序的 {row,col,char,tick}
let lastMathColumns = null;   // 竖式 columns 审计

function collectReplayDataFromTicks(ticks) {
  // 画板帧: project_contour 中间态 + commit 最终画
  paintReplayFrames = [];
  (ticks || []).forEach((t) => {
    const sa = t.selected_action || {};
    const vip = t.visual_inner_picture || {};
    if ((sa.action_type === "project_unit" || sa.action_type === "project_contour" || sa.action_type === "commit_painting") && vip.path) {
      paintReplayFrames.push({
        tick: t.tick,
        action: sa.action_type,
        path: String(vip.path),
        units: vip.projected_unit_count || 0,
      });
    }
  });
  // 草稿逐格: 最后一个带 cells 的 tick, cells 按 written tick 升序
  let cells = [];
  (ticks || []).forEach((t) => {
    const grid = t.draft_grid || {};
    if (Array.isArray(grid.cells) && grid.cells.length) cells = grid.cells;
  });
  draftReplayCells = cells.slice().sort((a, b) => (a.tick || 0) - (b.tick || 0));
  // 竖式审计: b_candidates 里 columns 槽
  lastMathColumns = null;
  (ticks || []).forEach((t) => {
    (t.b_candidates || []).forEach((b) => {
      (b.candidate_audit_slots || []).forEach((s) => {
        if (s && Array.isArray(s.columns) && s.columns.length) lastMathColumns = s.columns;
      });
    });
  });
  updateReplayPanels();
}

function mediaUrlFor(path) {
  return "/api/phase20/media?path=" + encodeURIComponent(path);
}

function updateReplayPanels() {
  const paintStatus = $("paintReplayStatus");
  if (paintStatus) {
    paintStatus.textContent = paintReplayFrames.length
      ? `捕获到 ${paintReplayFrames.length} 帧真实作画过程（tick ${paintReplayFrames[0].tick} → ${paintReplayFrames[paintReplayFrames.length - 1].tick}）`
      : "还没有画板活动。让它画一幅画试试（看首页“看它画画示例”）。";
  }
  const host = $("paintBoardReplay");
  if (host && paintReplayFrames.length) {
    const last = paintReplayFrames[paintReplayFrames.length - 1];
    host.innerHTML = `<img class="paint-replay-final" src="${mediaUrlFor(last.path)}" alt="AP 的画" loading="lazy" />`;
  }
  const mathPanel = $("verticalMathPanel");
  if (mathPanel) {
    if (lastMathColumns) {
      mathPanel.hidden = false;
      renderVerticalMathLayout(lastMathColumns);
    } else {
      mathPanel.hidden = true;
    }
  }
  const draftStatus = $("draftReplayStatus");
  if (draftStatus) {
    draftStatus.textContent = draftReplayCells.length
      ? `共 ${draftReplayCells.length} 个格子按真实写入顺序可回放`
      : "";
  }
}

function renderVerticalMathLayout(columns) {
  // columns: [{column, subquery, fact_event_id, fact_support, carry_out}] 右→左
  const host = $("verticalMathLayout");
  if (!host) return;
  const colRows = columns.map((c, i) => {
    const carry = c.carry_out ? `<span class="vm-carry" title="进位">↑进${esc(c.carry_out)}</span>` : "";
    return `
      <div class="vm-column">
        <div class="vm-col-head">第${i === 0 ? "个位" : i === 1 ? "十位" : `${i + 1}`}列</div>
        <div class="vm-subquery">${esc(String(c.subquery || ""))}</div>
        <div class="vm-fact">召回事实 · 支持度 ${esc(String(c.fact_support ?? ""))}</div>
        ${carry}
      </div>`;
  });
  host.innerHTML = `
    <div class="vm-columns">${colRows.join("")}</div>
    <p class="panel-hint">从右往左逐列：每列的算式是它对已教事实的一次真实召回（fact_support 是退火后验把握），进位是"上一列召回结果的高位进入下一列子查询"——没有任何一步是计算器。</p>`;
}

async function playPaintReplay() {
  if (!paintReplayFrames.length) return;
  const host = $("paintBoardReplay");
  const status = $("paintReplayStatus");
  if (!host) return;
  for (let i = 0; i < paintReplayFrames.length; i += 1) {
    const f = paintReplayFrames[i];
    host.innerHTML = `<img class="paint-replay-final" src="${mediaUrlFor(f.path)}" alt="作画中" />`;
    if (status) status.textContent = `tick ${f.tick} · ${f.action === "commit_painting" ? "落笔完成" : `投影第 ${f.units} 个轮廓单元`}`;
    await new Promise((r) => setTimeout(r, 900));
  }
  if (status) status.textContent = `回放完成 · 共 ${paintReplayFrames.length} 帧真实画板状态`;
}

async function playDraftReplay() {
  if (!draftReplayCells.length) return;
  const host = $("draftProcess");
  const status = $("draftReplayStatus");
  if (!host) return;
  // 逐格淡入: 每步重画 grid, 已写格子高亮最新
  const rows = Math.max(...draftReplayCells.map((c) => c.row)) + 1;
  const cols = Math.max(...draftReplayCells.map((c) => c.col)) + 1;
  for (let step = 1; step <= draftReplayCells.length; step += 1) {
    const visible = draftReplayCells.slice(0, step);
    const map = new Map(visible.map((c) => [`${c.row}:${c.col}`, c]));
    const latest = visible[visible.length - 1];
    let html = "";
    for (let r = 0; r < rows; r += 1) {
      let rowHtml = "";
      for (let c = 0; c < cols; c += 1) {
        const cell = map.get(`${r}:${c}`);
        const isLatest = cell && latest && cell.row === latest.row && cell.col === latest.col;
        rowHtml += `<div class="draft-grid-cell ${cell ? "filled" : "empty"} ${isLatest ? "just-written" : ""}">${cell ? esc(String(cell.char)) : "&nbsp;"}</div>`;
      }
      html += `<div class="draft-grid-row">${rowHtml}</div>`;
    }
    host.innerHTML = `<div class="draft-grid-board">${html}</div>`;
    if (status) status.textContent = `tick ${latest.tick} · 写入 "${latest.char}" 到 (${latest.row},${latest.col}) · ${step}/${draftReplayCells.length}`;
    await new Promise((r) => setTimeout(r, 380));
  }
  if (status) status.textContent = `回放完成 · ${draftReplayCells.length} 格`;
}

$("paintReplayPlay")?.addEventListener("click", () => { void playPaintReplay(); });
$("draftReplayPlay")?.addEventListener("click", () => { void playDraftReplay(); });

// 每次 turn 后自动收集回放数据
(function hookReplayCollection() {
  const origRenderDetail = typeof renderDetailInnerPictures === "function" ? renderDetailInnerPictures : null;
  window.addEventListener("apv3:turn-rendered", () => collectReplayDataFromTicks(currentTicks));
  // 兜底: 定时轻量检查 currentTicks 变化
  let lastLen = -1;
  setInterval(() => {
    if (Array.isArray(currentTicks) && currentTicks.length !== lastLen) {
      lastLen = currentTicks.length;
      collectReplayDataFromTicks(currentTicks);
    }
  }, 1500);
})();
