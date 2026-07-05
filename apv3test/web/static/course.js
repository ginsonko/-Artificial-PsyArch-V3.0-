const courseState = {
  demos: [],
  trace: null,
  selectedTick: 1,
  playing: false,
  timer: null,
};

const c$ = (id) => document.getElementById(id);

async function courseApi(path, options = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    cache: "no-store",
    ...options,
  });
  const data = await res.json();
  if (!res.ok || data.error) throw new Error(data.error || `HTTP ${res.status}`);
  return data;
}

function escapeCourseHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

async function bootCourse() {
  bindCourseEvents();
  const payload = await courseApi("/api/course/demos");
  courseState.demos = payload.demos || [];
  c$("demoSelect").innerHTML = courseState.demos.map((demo) => (
    `<option value="${escapeCourseHtml(demo.demo_id)}">${escapeCourseHtml(demo.title)}</option>`
  )).join("");
  if (courseState.demos.length) await runCourse();
}

function bindCourseEvents() {
  c$("runCourseBtn").addEventListener("click", runCourse);
  c$("prevTickBtn").addEventListener("click", () => selectCourseTick(courseState.selectedTick - 1));
  c$("nextTickBtn").addEventListener("click", () => selectCourseTick(courseState.selectedTick + 1));
  c$("playTickBtn").addEventListener("click", toggleCoursePlay);
  c$("courseTickSlider").addEventListener("input", (event) => selectCourseTick(Number(event.target.value || 1)));
  document.querySelectorAll("[data-course-tab]").forEach((button) => {
    button.addEventListener("click", () => switchCourseTab(button.dataset.courseTab));
  });
}

async function runCourse() {
  stopCoursePlay();
  const demoId = c$("demoSelect").value;
  const payload = await courseApi("/api/course/run", {
    method: "POST",
    body: JSON.stringify({ demo_id: demoId }),
  });
  courseState.trace = payload;
  courseState.selectedTick = 1;
  renderCourseAll();
}

function renderCourseAll() {
  const trace = courseState.trace || {};
  const ticks = trace.ticks || [];
  const demo = trace.demo || {};
  c$("courseStatus").textContent = `${escapeCourseHtml(demo.title || "课程")} · ${ticks.length} ticks`;
  c$("demoTitle").textContent = demo.title || "未运行";
  c$("questionBox").textContent = demo.question || "";
  c$("courseTickSlider").max = String(Math.max(1, ticks.length));
  c$("courseTickSlider").value = String(courseState.selectedTick);
  renderTickTimeline();
  renderCurrentTick();
}

function renderTickTimeline() {
  const ticks = courseState.trace?.ticks || [];
  c$("tickTimeline").innerHTML = ticks.map((tick) => (
    `<button class="tick-pill ${Number(tick.tick) === Number(courseState.selectedTick) ? "active" : ""}" data-tick="${tick.tick}">
      <b>tick ${escapeCourseHtml(tick.tick)}</b><span>${escapeCourseHtml(tick.title)}</span>
    </button>`
  )).join("");
  document.querySelectorAll(".tick-pill").forEach((button) => {
    button.addEventListener("click", () => selectCourseTick(Number(button.dataset.tick || 1)));
  });
}

function renderCurrentTick() {
  const ticks = courseState.trace?.ticks || [];
  const tick = ticks.find((row) => Number(row.tick) === Number(courseState.selectedTick)) || ticks[0] || {};
  c$("courseTickLabel").textContent = `tick ${tick.tick || 0}`;
  c$("courseFrameCount").textContent = `${courseState.selectedTick || 0} / ${ticks.length || 0}`;
  c$("courseTickSlider").value = String(courseState.selectedTick || 1);
  c$("assetStrip").innerHTML = (tick.asset_urls || []).map((url, index) => renderAsset(url, index)).join("");
  c$("tickDetail").innerHTML = `
    ${courseKv("阶段", tick.title || "")}
    ${courseKv("题目", tick.question || "")}
    ${courseKv("当前材料", (tick.asset_refs || []).join(" · "))}
    ${courseKv("Q 倾向", tick.q_score ?? "")}
    ${courseKv("AP 输出", tick.ap_output || "")}
  `;
  c$("packetPanel").innerHTML = `
    <div class="row-card"><b>content_key</b><small>${escapeCourseHtml(tick.packet?.content_key || "")}</small></div>
    <div class="row-card"><b>source_key</b><small>${escapeCourseHtml(tick.packet?.source_key || "")}</small></div>
    <div class="row-card"><b>feeling_key</b><small>${escapeCourseHtml(tick.packet?.feeling_key || "")}</small></div>
  `;
  c$("mindPanel").innerHTML = `
    <div class="row-card"><b>focus</b><small>${escapeCourseHtml(tick.mind?.focus || "")}</small></div>
    <div class="row-card"><b>marker</b><small>${escapeCourseHtml(tick.mind?.marker || "")}</small></div>
    <div class="row-card"><b>source</b><small>${escapeCourseHtml(tick.mind?.source || "")}</small></div>
    <div class="row-card"><b>feeling</b><small>${escapeCourseHtml(tick.mind?.feeling || "")}</small></div>
  `;
  const summary = courseState.trace?.summary || {};
  c$("summaryPanel").innerHTML = `
    <div class="row-card"><b>final_output</b><small>${escapeCourseHtml(summary.final_output || "")}</small></div>
    <div class="row-card"><b>runtime_generated</b><small>${summary.runtime_generated ? "true" : "false"}</small></div>
    <div class="row-card"><b>asset_ref_count</b><small>${escapeCourseHtml(summary.asset_ref_count || 0)}</small></div>
  `;
  renderTickTimeline();
}

function renderAsset(url, index) {
  const safeUrl = escapeCourseHtml(url);
  if (safeUrl.endsWith(".wav") || safeUrl.includes("audio_")) {
    return `<div class="course-asset"><audio controls src="${safeUrl}"></audio><small>asset ${index + 1}</small></div>`;
  }
  return `<div class="course-asset"><img src="${safeUrl}" alt="course asset ${index + 1}"><small>asset ${index + 1}</small></div>`;
}

function courseKv(label, value) {
  return `<div class="kv"><span>${escapeCourseHtml(label)}</span><span class="mono">${escapeCourseHtml(value)}</span></div>`;
}

function selectCourseTick(tick) {
  const ticks = courseState.trace?.ticks || [];
  if (!ticks.length) return;
  courseState.selectedTick = Math.max(1, Math.min(ticks.length, Number(tick || 1)));
  renderCurrentTick();
}

function toggleCoursePlay() {
  if (courseState.playing) {
    stopCoursePlay();
    return;
  }
  courseState.playing = true;
  c$("playTickBtn").textContent = "暂停";
  courseState.timer = window.setInterval(() => {
    const ticks = courseState.trace?.ticks || [];
    if (!ticks.length || courseState.selectedTick >= ticks.length) {
      stopCoursePlay();
      return;
    }
    selectCourseTick(courseState.selectedTick + 1);
  }, 800);
}

function stopCoursePlay() {
  courseState.playing = false;
  c$("playTickBtn").textContent = "播放";
  if (courseState.timer) window.clearInterval(courseState.timer);
  courseState.timer = null;
}

function switchCourseTab(tab) {
  document.querySelectorAll("[data-course-tab]").forEach((button) => {
    button.classList.toggle("active", button.dataset.courseTab === tab);
  });
  document.querySelectorAll("[id^='course-tab-']").forEach((panel) => {
    panel.classList.toggle("active", panel.id === `course-tab-${tab}`);
  });
}

bootCourse().catch((error) => {
  c$("courseStatus").textContent = `课程回放启动失败: ${error.message}`;
});
