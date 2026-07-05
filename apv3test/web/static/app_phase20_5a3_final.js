// Phase 20.5a3 final browser layer. This file is loaded after app.js so its
// functions are the browser-visible definitions.
function current205a3Tick() {
  if (!state.workbenchTicks.length) return null;
  const index = Math.max(0, Math.min(state.workbenchTickIndex, state.workbenchTicks.length - 1));
  return state.workbenchTicks[index] || null;
}

function current205a3Draft(tick = current205a3Tick()) {
  return (tick && (tick.draft_snapshot || tick.draft_changes)) || {};
}

function current205a3Metrics(tick = current205a3Tick()) {
  const draft = current205a3Draft(tick);
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

function stepWorkbenchTick(delta) {
  if (!state.workbenchTicks.length) return;
  setWorkbenchTick(state.workbenchTickIndex + delta);
}

function renderReplay() {
  const tick = current205a3Tick();
  if (!tick) {
    $("tickButtons").innerHTML = "";
    $("replayDetail").innerHTML = `<div class="row-card"><b>等待本轮 turn</b><small>发送后显示每个 tick 的 AP loop 快照。</small></div>`;
    return;
  }
  const draft = current205a3Draft(tick);
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
    ${kv("共现召回", draft.teaching_candidate_applied ? `命中 ${draft.teaching_id || ""}` : "未命中教师共现记忆")}
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
        const m = current205a3Metrics(tick);
        return {
          real: Number((tick.energy_RAPF || [])[0] || m.mean_real_energy || 0),
          attention: Number((tick.energy_RAPF || [])[1] || m.mean_attention_energy || 0),
          pressure: Number((tick.energy_RAPF || [])[2] || m.mean_cognitive_pressure || 0),
          draft: Number(m.draft_length || 0),
        };
      })
    : [];
  drawSeries(ctx, rows, "real", "#0f766e", width, height);
  drawSeries(ctx, rows, "attention", "#245a8f", width, height);
  drawSeries(ctx, rows, "pressure", "#a33b35", width, height);
  drawSeries(ctx, rows, "draft", "#8a6d1f", width, height);
  drawLegendRows(ctx, [["real", "#0f766e"], ["attention", "#245a8f"], ["pressure", "#a33b35"], ["draft", "#8a6d1f"]]);
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
  const tick = current205a3Tick();
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
  const tick = current205a3Tick();
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
  $("auditPanel").innerHTML = `<div class="row-card"><b>AP runtime 审计</b><small>所有曲线来自当前 turn 的 RuntimeTickEvent；分过程耗时是后端本轮实际计时，不是前端动画。</small></div><div class="audit-grid">${specs.map(([key, label, path]) => renderMiniChart(label, ticks.map((tick) => metric205a3(tick, key, path)))).join("")}</div>`;
}

function metric205a3(tick, key, path) {
  const metrics = current205a3Metrics(tick);
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
