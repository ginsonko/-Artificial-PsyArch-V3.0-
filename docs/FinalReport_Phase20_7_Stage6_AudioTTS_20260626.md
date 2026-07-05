# Phase20.7 Stage 6 Audio TTS 验收报告

日期: 2026-06-26  
范围: audio audit sensor、xiaoyi 本地 TTS actuator intent、TTS 与 inner voice 分离。

---

## 1. 本阶段目标

Stage 6 的目标是把听觉输入和朗读执行器接入同一套 RuntimeTickEvent:

1. 音频输入只做 audit sensor, 不冒充语音识别。
2. 音频 trace 不输出语义标签。
3. 回复提交后产生 `reply_tts_audio` actuator tick。
4. TTS 默认本地-only, voice preference 为 xiaoyi。
5. TTS 是回复朗读执行器, 不是 inner voice。

---

## 2. 已落地内容

新增 `apv3test/runtime/phase20_7/audio.py`:

1. `run_audio_audit_ticks(...)`
2. `record_tts_actuator_tick(...)`
3. `select_xiaoyi_voice(...)`

### 2.1 audio audit

音频输入写入:

```text
phase20_7_payload_blobs: audio_audit_payload
phase20_7_experience_events: audio_audit_sample
RuntimeTickEvent.audio_inner_sketch.source = audio_audit_only
```

只记录:

1. source hash
2. byte length
3. wav duration
4. audit_only

不记录识别词、标签或转写文本。

### 2.2 xiaoyi TTS actuator

回复提交后写入:

```text
RuntimeTickEvent.selected_action.action_type = reply_tts_audio
voice_preference = xiaoyi
local_only = true
event_kind = reply_tts_audio
```

`select_xiaoyi_voice(...)` 会优先在本地 pyttsx3/SAPI voices 中查找 xiaoyi / xiao yi / 晓伊 / 晓艺。未枚举到时仍保留 xiaoyi preference, 由后续 UI/执行器层继续绑定真实本地声音。

---

## 3. 当前可展示效果

```text
音频输入:
tick: audio_audit_sensor
audio_inner_sketch: audio_audit_only
semantic_label: None

文本回复:
tick: commit_reply
tick: reply_tts_audio
voice_preference: xiaoyi
local_only: True
```

---

## 4. 本阶段能证明什么

Stage 6 可以证明:

1. 音频已经进入 Phase20.7 RuntimeTickEvent。
2. 音频输入不冒充识别。
3. TTS 与 inner voice 已分离。
4. xiaoyi 本地 voice preference 已进入 actuator trace。
5. 回复朗读是行动记录, 不是回答来源。

---

## 5. 本阶段尚未证明什么

Stage 6 还不证明:

1. 实时麦克风录音 UI。
2. 实际播放音频文件。
3. Phase19.1/19.4 听觉识别。
4. 音频与文本/视觉经验的跨模态结构召回。

这些进入后续 Stage 和工作台发布版。

---

## 6. 验收命令

### 6.1 Stage 0-6 单测

```powershell
python -m pytest .\tests\test_phase20_7_stage0_runtime_boundary.py .\tests\test_phase20_7_stage1_text_closed_loop.py .\tests\test_phase20_7_stage2_experience_memory_indexes.py .\tests\test_phase20_7_stage3_structural_bccstar.py .\tests\test_phase20_7_stage4_unclosed_idle.py .\tests\test_phase20_7_stage5_visual_patch_reconstruction.py .\tests\test_phase20_7_stage6_audio_tts.py -q
```

结果: `27 passed`。

### 6.2 Stage 6 红线扫描

```powershell
python .\scripts\red_line_check_v14.py --phase 20.7-stage6
```

结果: 见最终运行记录。

---

## 7. 下一阶段入口

Stage 7 应实现工作台/API:

1. 对外 `/api/phase20_7/turn` 或等价本地调用入口。
2. 工作台只读取 RuntimeTickEvent。
3. 统一记忆视图可浏览、删除、卸载包。
4. 视觉、音频、TTS、未闭合、B/C/C* 都在同一 trace 中展示。

