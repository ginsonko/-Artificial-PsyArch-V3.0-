# APV3 Phase20.7 发布 demo 用户说明

日期: 2026-06-26

## 1. 这是什么

这是 APV3 Phase20.7 的本地开放中文对话底座 demo。

它的目标不是像 LLM 一样一开始什么都知道, 而是像一个会成长的 3-5 岁小孩级 AP:

1. 不懂会承认。
2. 可以被用户教学。
3. 学过的内容会进入统一经验流。
4. 之后能从经验流召回。
5. 低把握时会形成未闭合感。
6. 闲时 tick 能想起还没弄懂的问题。
7. 图片和音频可以作为感受器证据进入同一套 RuntimeTickEvent。

## 2. 如何运行

在 `APV3.0test` 目录运行:

```powershell
python -m apv3test.web_chat --host 127.0.0.1 --port 8774
```

浏览器打开:

```text
http://127.0.0.1:8774/phase20_7
```

## 3. 推荐演示流程

### 3.1 文本教学

输入:

```text
你好啊
```

教学纠正:

```text
你也好
```

AP 会回复:

```text
嗯,记下了。
```

再次输入:

```text
你好啊
```

AP 会通过经验流召回:

```text
你也好
```

### 3.2 结构类比

在学过“你好啊 -> 你也好”后, 输入:

```text
你好呀
```

AP 会走 structural B/C/C* 路径, 形成近似结构召回。tick 回放中可以看到:

```text
B structural_b
C_forward
C_backward
C*
```

### 3.3 未闭合感

输入:

```text
猫是什么
```

AP 会回复:

```text
我还不太知道怎么说。
```

再次输入同一句, AP 会回复:

```text
我还在想这个。
```

点击“闲时 tick”, tick 回放中会出现 `idle_think`, 表明未闭合项把注意拉回。

教学:

```text
猫是一种动物
```

之后再次问:

```text
猫是什么
```

AP 会回复:

```text
猫是一种动物
```

### 3.4 视觉 patch 与内心画面

输入图片路径后发送。工作台会显示:

1. `move_focus`
2. `visual_patch_sample`
3. `visual_inner_picture`
4. `clarity_coverage`

这证明当前阶段的视觉能力是“焦点采样 + patch 重建 + 状态池证据”, 不代表已经完成水果识别。

### 3.5 音频与 TTS

输入音频路径后发送。工作台会显示:

```text
audio_audit_sensor
audio_audit_only
```

有文本回复时, 会出现:

```text
reply_tts_audio
voice_preference = xiaoyi
local_only = true
```

TTS 是朗读执行器, 不是回答来源。

## 4. 当前边界

当前 demo 可以证明:

1. Phase20.7 已有独立 AP-native runtime。
2. 统一经验流、StatePool、SSP、DraftGrid、B/C/C*、未闭合感、多模态感受器和 TTS 执行器已经接到同一条 RuntimeTickEvent 链上。
3. 教学不会通过独立答案表全局命中。
4. 图片不会通过文件名、整图标签或 OCR 得出答案。

当前 demo 还不证明:

1. AP 已具备成人级通用闲聊能力。
2. AP 已能稳定识别苹果/香蕉/橙子。
3. AP 已完成长程因果解释、复杂视觉泛化和真实麦克风识别。

## 5. 审计原则

工作台只显示 RuntimeTickEvent。  
如果某能力没有写进 RuntimeTickEvent, 页面不应该补编或假装已经发生。

