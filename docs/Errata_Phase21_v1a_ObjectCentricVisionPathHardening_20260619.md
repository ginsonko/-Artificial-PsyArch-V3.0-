# APV3.0 Phase 21 v1a Errata — Object-Centric Vision Path Hardening, Train-Test Symmetry, and Multi-Dimensional Acceptance

Date: 2026-06-19
Author: Claude(架构),银子老师(风格定调与最终签收)
Status: 设计稿微修订(叠加在 Phase 21 v1 之上 — 两份合读)
Source: 吸收 Codex Phase 21 v1 对抗审阅全部 5 项必修 + 我自查 4 项隐患
License intent: AGPL-3.0-or-later
Real name handling: 全文件 grep 真名 = 0

---

## 0. 这一份做什么(一句话)

把 Phase 21 v1 设计稿的 9 处会让"拟人扫视认知"滑成"工程目标检测器 + 标签器"的接口缝隙全部钉死 — 其中**最致命**:**当前 `extract_visual_audit_path_v2` 即使传 focus_xy,V7/V10/V11/V12 仍走整图 mask**,这是 v1 设计稿没看到的工程缺口,直接导致"换 focus 但不会真正避开背景"。

---

## 1. 全部修订清单(5 收 Codex + 4 自查)

| ID | 来源 | 内容 | §X |
|---|---|---|---|
| **R1** | Codex | candidate 不能含 class 信息(opaque + grep 红线) | §2 |
| **R2** | Codex | **致命**:V7/V10/V11/V12 不真随 focus 变,要补 object-centric local mask path | §3 |
| **R3** | Codex | 训练库也要走 object-centric vector 路径 | §4 |
| **R4** | Codex | 9/12 不作硬门;改多维度验收 | §5 |
| **R5** | Codex | 数感不能等候选数;要 IOR 合并 + 重复抑制 | §6 |
| **S1** | 自查 | `recognize_at_focus` 缺底层函数 `_visual_recognize_v1_7_with_trace` 拆分 | §7 |
| **S2** | 自查 | visual_candidate SA 生命周期(图切换时清除) | §8 |
| **S3** | 自查 | candidate 排序策略明确化 | §9 |
| **S4** | 自查 | Python 3.11 与 Zvec 兼容性确认(已实测 — 见 §10) | §10 |

---

## 2. R1 — Class-Agnostic Visual Candidate(收 Codex)

### 2.1 v1 §3.3 修正

candidate SA 严格禁止以下 metadata:

```
RL-21-R1-01: visual_candidate metadata 仅允许:
  - focus_xy: (x, y)
  - region_size_px: int
  - saliency_score: float
  - edge_strength_local: float
  - color_contrast_local: float
  - motion_score: float (运动跟随,可 0)
  - uncertainty: 1 - saliency_score
  - image_trace_hash: str (opaque, source 图的 hash)

RL-21-R1-02: 严禁出现:
  - apple_like / banana_like / orange_like 等类别提示
  - prototype_match_score(已经做识别了)
  - 文件名 / label / 概念名
  - Layer-3 ConceptPrototype uuid 关联

RL-21-R1-03: grep test:
  scripts 不允许 'visual_candidate' metadata 含 'apple|banana|orange|label|concept'
  生成 candidate 函数体不允许 import / 调用 Layer-3 lookup
```

### 2.2 为什么这条服务 G1/G3

- G3 "图里有什么"应来自**扫视**,不是**先识别再造 candidate**
- 若 candidate 自带 label,Phase 21 就变成 hidden classifier,Phase 19 全套架构白做
- 拟人:婴儿看到陌生东西也会先"那是什么?"(用 attention 调焦点),不是"那是 X,我先确认"

---

## 3. R2 — Object-Centric Local Feature Path(收 Codex,最致命)

### 3.1 v1 设计稿没看到的真相

读 [apv3test/runtime/visual_receptor.py:262 `extract_visual_audit_path_v2`](apv3test/runtime/visual_receptor.py#L262) 实际代码:

```python
mask, segmentation_confidence = _best_mask(rgb, edge)   # ← 整图 mask, 不随 focus 变
channels.append(("V0", _v0_vector(rgb, edge, focus)))    # ← V0 真随 focus
channels.append(("V6", _shape_geometry(mask)))           # ← 用整图 mask
channels.append(("V7", _part_prototype_coverage(rgb, mask)))   # ← 用整图 mask
channels.append(("V8", _layout_summary(mask, focus_xy=focus))) # ← V8 真随 focus
channels.append(("V9", _foreground_background_kl(rgb, luma, mask)))   # ← 整图 mask
channels.append(("V10", _per_part_color_texture(rgb, mask)))   # ← 整图 mask
channels.append(("V11", _part_relational_graph(rgb, mask)))    # ← 整图 mask
channels.append(("V12", _color_cluster_spatial_map(rgb, mask)))# ← 整图 mask
```

**只有 V0、V8 随 focus 变**。其余**11 个通道全部走整图 mask**,换 focus 等于没换。这就是为什么 Codex 警告"扫视只是换焦点,不会真正避开背景污染"。

### 3.2 v1a 修正:新增 object-centric 抽取入口

```python
def extract_visual_audit_path_v2_object_centric(
    image_like: Path | str | np.ndarray,
    *,
    focus_xy: tuple[int, int],
    candidate_region: tuple[int, int, int, int] | None = None,  # (x_min, y_min, x_max, y_max)
    candidate_mask: np.ndarray | None = None,  # 该候选的 mask, shape 同原图
    tick: int = 0,
) -> VisualAuditTrace:
    """
    object-centric 抽取入口。
    - V0: 用 focus_xy(同既有)
    - V8: 用 focus_xy(同既有)
    - V6/V7/V9/V10/V11/V12: **用 candidate_mask 替代整图 _best_mask**
    - 若 candidate_mask 为 None,用 candidate_region 内的 _best_mask
    - V1/V2/V3/V4/V5: **在 candidate_region crop 内计算**(不是整图)
    """
    rgb = _as_rgb_array(image_like)

    # 1. 解析 candidate_region
    if candidate_region:
        x_min, y_min, x_max, y_max = candidate_region
        # 用候选 bbox 扩 1.2 倍作为局部视野
        local_rgb, local_offset = _crop_with_padding(rgb, x_min, y_min, x_max, y_max, padding_ratio=0.2)
    else:
        # focus_xy 周边 patch_size 半径
        patch_size = _int_constant("phase21.local_patch_size_px")  # 默认 128
        local_rgb, local_offset = _crop_around_focus(rgb, focus_xy, patch_size)

    local_luma = _luma(local_rgb)
    local_edge = _sobel_magnitude(local_luma)

    # 2. 解析 candidate_mask(若给定)
    if candidate_mask is not None:
        local_mask = candidate_mask[
            local_offset[1]:local_offset[1]+local_rgb.shape[0],
            local_offset[0]:local_offset[0]+local_rgb.shape[1]
        ]
        seg_conf = float(_mask_confidence(local_mask, local_edge))
    else:
        local_mask, seg_conf = _best_mask(local_rgb, local_edge)

    # 3. 在 local_rgb + local_mask 上抽 V0..V12,而不是整图
    channels = []
    relative_focus = (focus_xy[0] - local_offset[0], focus_xy[1] - local_offset[1])
    channels.append(("V0", _v0_vector(local_rgb, local_edge, relative_focus)))
    # V1-V12 全部在 local_rgb + local_mask 内算
    # ... (其余实现与既有相同,只是输入换 local)
```

### 3.3 三种调用模式

| 模式 | 输入 | 用途 |
|---|---|---|
| **legacy 全图** | image_like(默认 focus 中心)| 已有兼容路径,保留 |
| **focus_only** | image_like + focus_xy(无 region)| 用 focus 周边 patch_size_px 半径 |
| **object_centric** | image_like + focus_xy + candidate_region + candidate_mask | Phase 21 阶段 C 主用 |

### 3.4 新常量

```yaml
phase21:
  local_patch_size_px: 128         # @structural - 默认局部视野半径
  candidate_region_padding_ratio: 0.2  # @experimental - bbox 扩 1.2 倍
```

### 3.5 红线

```
RL-21-R2-01: Phase 21 阶段 C 调用必为 extract_visual_audit_path_v2_object_centric
             并必带 candidate_region 或 candidate_mask
RL-21-R2-02: grep test: enumerate_objects_in_image 函数体内
             调用 extract_visual_audit_path_v2_object_centric ≥ 2 次(多 candidate)
             禁止只调 extract_visual_audit_path_v2(那是 legacy 整图)
RL-21-R2-03: 单测:对同一张图不同 candidate_region 抽特征,V7/V10/V11/V12 必须显著不同
             (差异 > 0.3),否则说明 mask 还是没 local 化
```

### 3.6 为什么服务 G3

- G3 "图里有什么"必须依赖 **per-candidate 真高清 + 真局部 mask**,否则换 focus = 没换
- 这是 Codex 最关键的一条

---

## 4. R3 — Train-Test Symmetric Object-Centric(收 Codex)

### 4.1 训练库也要 object-centric

```python
def build_object_centric_teaching_library(teaching_examples: Sequence[TeachingImage]) -> dict[str, list[VisualAuditTrace]]:
    """
    教学库也走 candidate 扫描 + per-focus 抽特征。
    每张教学图先做候选检测,然后对每个候选独立抽 object-centric trace。
    然后聚类成 ConceptPrototype.
    """
    concept_to_traces = {}
    for teaching in teaching_examples:
        rgb = _as_rgb_array(teaching.image_path)
        candidates = extract_candidate_targets(rgb, max_targets=6)
        if not candidates:
            continue
        # 教学时,教师 label 指向主要对象 — 默认取最大 saliency 那个 candidate
        primary = max(candidates, key=lambda c: c.saliency_score)
        trace = extract_visual_audit_path_v2_object_centric(
            teaching.image_path,
            focus_xy=primary.focus_xy,
            candidate_region=primary.region,
            candidate_mask=primary.mask,
        )
        concept_to_traces.setdefault(teaching.label, []).append(trace)
    return concept_to_traces
```

### 4.2 关键:教学时一张图只取最大 candidate 作 train,不是全图

- 这就解决了"教学图整图特征 vs query 候选 patch 特征"的 domain mismatch

### 4.3 复杂教学图(多对象在一张)的处理

教学图本身可能含多个对象(比如"这是苹果"但桌上还有香蕉):

- 若 saliency 最高的与 label 真匹配 → 直接走
- 若 saliency 最高的与 label **不**匹配(教学图模糊) → 教师可用 box 手动指定(future Phase 22)
- Phase 21 初版只取 max saliency,接受少量 noise

### 4.4 红线

```
RL-21-R3-01: build_object_centric_teaching_library 在 enumerate_objects_in_image 前调用
             query candidates 与 train candidates 走**同一个** extract_visual_audit_path_v2_object_centric
             函数(grep test:同函数名)
RL-21-R3-02: legacy 整图 trace 在 Phase 21 识别路径不允许使用
             grep test: enumerate_objects_in_image 路径不调 extract_visual_audit_path_v2(无 candidate_region)
```

### 4.5 为什么服务 G3

- 训测对称就是 Codex 强调的"同一 vector path",这是工业 CV transfer learning 公理
- 不对称的话,识别准不准跟 candidate 检测准不准纠缠,无法分离诊断

---

## 5. R4 — Multi-Dimensional Acceptance(替换 v1 §10 期待 9/12)

### 5.1 v1 §10 期待"≥ 9/12 正确"过乐观

实测当前 6-7/12,即使方向对,工程接 v1c-vh + Phase 21 + R1-R3 修订后,**第一版能到 8-9/12 已经是好结果**。

### 5.2 v1a 改多维度验收(每条独立 gate)

| Gate 维度 | 目标 |
|---|---|
| G-21-Acc-01 候选框覆盖主体 | 12 张图每张至少 1 个 candidate 与真实主体 IoU ≥ 0.5 |
| G-21-Acc-02 per-focus margin 提升 | 同张图 per-focus margin > 整图 margin(实测验证扫视真起效) |
| G-21-Acc-03 错 firm 数 | 0 张(继承 v1a 红线) |
| G-21-Acc-04 多物体列举 | 银子老师拼的 5-10 张多物体图,**至少 2/3 对象正确列举** |
| G-21-Acc-05 同对象多 tick 把握上升 | 单张图 5 个 tick 内,top object 的 raw_confidence 单调上升 |
| G-21-Acc-06 单主体识别正确率 | ≥ 8/12(不再硬要求 9/12)|
| G-21-Acc-07 soft/firm 比例 | ≥ 4/12(从当前 0)|

### 5.3 加权评分(给 Final Report 用)

Phase 21 通过 = G-Acc-01..05 全过 + 06/07 都达到。**G06 即便只到 7/12 也允许通过**,但要写诚实 Final Report。

---

## 6. R5 — 数感接通要 IOR + 候选合并 + 重复对象抑制(收 Codex)

### 6.1 v1 §6.2 错误

v1 简单说"阶段 A 候选检测器**直接产 N 个 SA**,数感系统自动数得到 N"。但 candidate 检测会:
- **过分割**:一个苹果被切成 3 个 candidate(果柄 / 果体 / 阴影)
- **漏分割**:几个紧挨的苹果合一个 candidate
- 都会让数感错

### 6.2 v1a 修正:候选合并 + IOR + 同对象抑制

```python
def merge_candidates_into_object_files(candidates: list[CandidateTarget]) -> list[ObjectFile]:
    """
    把 candidate 列表合并成 ObjectFile 列表(拟人 object file 概念)
    步骤:
    1. NMS 合并 IoU > 0.5 的 candidate
    2. 同 candidate 群里 saliency 最高的为 primary
    3. 经过 Phase 21 阶段 C 识别后,同 label 且 IoU 重叠 > 0.3 的 ObjectFile 合并
    """
```

### 6.3 数感是 ObjectFile 数量,不是 candidate 数量

```python
def count_object_files(objects: list[ObjectFile]) -> dict:
    """
    数感输出:
    - total_count: len(objects)
    - per_label_count: {"apple": 2, "banana": 1, ...}
    - confidence_per_count: 由 per ObjectFile 的 raw_confidence 加权
    """
```

### 6.4 接通 countloop0

countloop0 数 SA 数量 — Phase 21 输入 `len(ObjectFile)` 即可,**不是** `len(candidates)`。

### 6.5 红线

```
RL-21-R5-01: ObjectFile 是 candidate + 识别后合并的单位,不是单 candidate
RL-21-R5-02: 数感输入必为 ObjectFile.count,grep test
```

### 6.6 为什么服务 G2

老师场景"看到几个" → ObjectFile.count 才是拟人正确数感,不是 candidate 数

---

## 7. Self-1 — `_visual_recognize_v1_7_with_trace` 拆分

### 7.1 v1 §5.2 假设的函数不存在,需要先拆

```python
# 拆分现有 visual_recognize_v1_7:
def _visual_recognize_v1_7_with_trace(
    query_trace: VisualAuditTrace,
    teaching_examples: Sequence[VisualTeachingExample],
    tick: int,
) -> RecognitionResult:
    """
    Phase 21 共用的内部识别函数 — 输入 trace,不再重新 extract.
    """
    concept_traces = _concept_training_traces(teaching_examples)
    if not concept_traces:
        # 冷启动 tentative concept(v1e §7)
        ...
    channel_validity = _channel_validity_map(concept_traces)
    concept_scores = tuple(
        _score_concept_channelwise(query_trace, label, traces, concept_traces, channel_validity)
        for label, traces in sorted(concept_traces.items())
    )
    ...


def visual_recognize_v1_7(query_image_path, *, teaching_examples, tick=0):
    """
    Legacy 整图入口 — 默认 focus 中心.
    """
    trace = extract_visual_audit_path_v2(query_image_path, tick=tick)
    return _visual_recognize_v1_7_with_trace(trace, teaching_examples, tick)


def recognize_at_focus(image_path, focus_xy, *, teaching_examples, tick, candidate_region=None, candidate_mask=None):
    """
    Phase 21 per-focus 入口 — object-centric.
    """
    trace = extract_visual_audit_path_v2_object_centric(
        image_path,
        focus_xy=focus_xy,
        candidate_region=candidate_region,
        candidate_mask=candidate_mask,
        tick=tick,
    )
    return _visual_recognize_v1_7_with_trace(trace, teaching_examples, tick)
```

### 7.2 红线

```
RL-21-S1-01: visual_recognize_v1_7 和 recognize_at_focus 共享 _visual_recognize_v1_7_with_trace
            不允许各自重写打分逻辑
```

---

## 8. Self-2 — visual_candidate SA 生命周期

### 8.1 问题

v1 §3.3 注入 candidate SA 后**没说什么时候清除**。多张图连续输入会累积污染:第 2 张图的 propose_visual_focus_actions 会看到第 1 张图遗留的 candidate。

### 8.2 修正

```python
def enumerate_objects_in_image(image_path, ...):
    image_trace_hash = hash_of_image(image_path)
    # 注入前先清除其他 image_trace_hash 的 visual_candidate
    state_pool.clear_visual_candidates_except(image_trace_hash)
    # 注入本图候选
    inject_candidates(candidates, image_trace_hash)
    try:
        # ... 三段管线
        return objects
    finally:
        # 完成后清理(或保留作短期记忆,看 Phase 19.5 source-aware 是否要用)
        # 短期保留 10 tick 作为"我刚看过这张图"记忆,然后衰减
        state_pool.mark_candidates_for_decay(image_trace_hash, half_life_ticks=10)
```

### 8.3 红线

```
RL-21-S2-01: enumerate_objects_in_image 开始时清除其他 image_trace_hash 的 visual_candidate
RL-21-S2-02: 完成后 visual_candidate 进入 10 tick 衰减,不是直接删除
            (保留短期"我刚看过"记忆,接 Phase 19.5 reverse_imagination 使用)
```

---

## 9. Self-3 — Candidate 排序策略

### 9.1 v1 §4.2 公式给了 score,但没说怎么排

```python
def sort_candidates_by_attention(candidates_with_scores: list[(CandidateTarget, float)]):
    """
    Phase 21 候选排序:
    1. 按 score 降序排
    2. 若 score 差 < 0.1(几乎平),按 region_size 降序(看大的优先)
    3. 若两个 candidate 重叠 IoU > 0.5,只保留 score 高那个(NMS)
    4. 同 tick 内最多 N 个进入实际扫视(避免一图 30 个 candidate 都扫)
    """
    return sorted_top_n_candidates
```

`phase21.max_candidates_per_tick = 6` @structural

### 9.2 为什么这么做

- 排序策略本身要拟人:人类看图也是先看大的、显眼的,小的细节后看
- IoU 0.5 NMS 防过分割
- max 6 per tick 防 candidate 爆炸

---

## 10. Self-4 — Python 3.11 与 Zvec 兼容性(已实测)

### 10.1 当前

`python --version` = **Python 3.11.9**

Zvec PyPI 要求 Python **3.10-3.14** → ✓ 兼容

### 10.2 落地前验证步骤

```bash
# Phase 19.9 落地前必做
pip install zvec
python -c "import zvec; print(zvec.__version__)"
# 期待: 0.3.1 或更新
python -c "
import zvec
c = zvec.Collection('test.zvec')
c.create_collection(dim=256, metric='cosine')
print('ok')
"
```

若失败 → 退回 brute-force topK + sqlite,Phase 19.9 暂缓。

### 10.3 兼容性 fallback

```python
try:
    import zvec
    HAS_ZVEC = True
except ImportError:
    HAS_ZVEC = False

class Layer1PerceptVectorStore:
    def __init__(self, sqlite_path, zvec_path):
        self.sql = ...
        if HAS_ZVEC:
            self.zvec = zvec.Collection(zvec_path)
        else:
            self.zvec = None

    def c_recall(self, query_signature, *, source_filter, top_k=10):
        if self.zvec:
            return self.zvec.search(...)
        # Fallback: brute-force on SQLite-loaded signatures
        return self._bruteforce_topk(query_signature, top_k, source_filter)
```

### 10.4 红线

```
RL-19.9-Compat-01: Zvec 必须有 brute-force fallback
RL-19.9-Compat-02: import zvec 失败不阻断系统启动
```

---

## 11. 修订后的 Deliverable Gates 总表(替换 v1 §8.1)

### Phase 21 v1a Gates(15 条)

| Gate |
|---|
| G-21-v1a-01 阶段 A 候选检测器实现,产 ≤ 6 个 class-agnostic visual_candidate(RL-21-R1) |
| G-21-v1a-02 阶段 B 真接通 propose_visual_focus_actions(grep test)|
| G-21-v1a-03 阶段 C 调 extract_visual_audit_path_v2_object_centric 而非 legacy 整图(grep test)|
| G-21-v1a-04 同图不同 candidate_region 抽特征,V7/V10/V11/V12 差异 > 0.3(单测验)|
| G-21-v1a-05 build_object_centric_teaching_library 实现,train candidate 与 query candidate 走同函数 |
| G-21-v1a-06 visual_candidate metadata 不含 label/concept/文件名(grep test)|
| G-21-v1a-07 visual_candidate SA 生命周期 — 新图开始时清理(单测)|
| G-21-v1a-08 ObjectFile 合并:NMS IoU > 0.5,同 label 重叠 > 0.3 |
| G-21-v1a-09 数感数 ObjectFile.count,不数 candidate(grep test)|
| G-21-v1a-10 12 张单主体图正确率 ≥ 8/12(允许 7/12 但写诚实 Final Report)|
| G-21-v1a-11 错 firm 数 = 0 |
| G-21-v1a-12 银子老师 5-10 张多物体图,每张至少 2/3 对象列举正确 |
| G-21-v1a-13 单张图 5 tick 内 top object raw_confidence 单调上升 |
| G-21-v1a-14 per-focus margin 显著 > 整图 margin |
| G-21-v1a-15 styled 输出符合小默风格("嗯,苹果。…橙子。")|

### Phase 19.9 v1a Gates(8 条)

| Gate |
|---|
| G-19.9-v1a-01 Zvec 安装通过(pip install zvec on Python 3.11)|
| G-19.9-v1a-02 brute-force fallback 实现 |
| G-19.9-v1a-03 SQLite 真源不变,删除 Zvec 索引可由 SQLite 重建 |
| G-19.9-v1a-04 Zvec 召回 top-10 与 brute-force 一致(差异 ≤ 5%)|
| G-19.9-v1a-05 7 条红线 RL-19.9-Z01..Z07 全过 |
| G-19.9-v1a-06 不允许跨 epistemic_source/substrate/receptor_version 召回(单测)|
| G-19.9-v1a-07 Zvec 删后重建,12 张图泛化结果不变 |
| G-19.9-v1a-08 性能:Layer-1 1 万 instances 时 Zvec 召回 < 5ms(vs brute-force > 100ms)|

---

## 12. 修订后的落地优先级

**Codex 建议(我同意)**:

```
1. Phase 21 实施(7-8 天,含 v1a 修订)
   Day 1: 阶段 A 候选检测器 + R1 红线
   Day 2: extract_visual_audit_path_v2_object_centric 实现 + R2 红线
   Day 3: build_object_centric_teaching_library + R3 红线
   Day 4: 阶段 B 真接通 visual_focus.py (S1 拆分 _with_trace)
   Day 5: 阶段 C enumerate_objects + IOR + ObjectFile + R5 数感接通
   Day 6: Phase 16 styled 渲染输出
   Day 7-8: 测试 + 银子老师拼多物体图测试 + 多维度验收

2. Phase 19.9 Zvec(平行 Phase 21 后期,3 天)
   Day 1: pip install zvec + Layer1.c_recall 接入 + fallback
   Day 2: SQLite 真源 + 重建测试
   Day 3: 7 红线 + 性能测

3. Phase 20 对话底座(Phase 21 + 19.9 完成后)
```

---

## 13. 自查清单(开工前必勾)

- [ ] candidate SA opaque(无 label / 无 concept)
- [ ] extract_visual_audit_path_v2_object_centric 在 Phase 21 路径调 ≥ 2 次
- [ ] train candidates 与 query candidates 走同一函数
- [ ] visual_recognize_v1_7 与 recognize_at_focus 共享 _visual_recognize_v1_7_with_trace
- [ ] visual_candidate SA 新图开始清理 + 10 tick 衰减
- [ ] candidate 排序策略明确(score → region_size → IoU NMS)
- [ ] ObjectFile 合并而非 candidate 直接计数
- [ ] 多物体图测试集(银子老师 5-10 张拼图)
- [ ] Python 3.11 + Zvec 兼容
- [ ] brute-force fallback 实现
- [ ] 真名 0 命中

---

## 14. 三大目标举证更新

| 目标 | 怎么达成(v1a 更新) |
|---|---|
| **G1 自由开放中文对话底座** | Phase 21 v1a 输出对象列表 → Phase 16 styled "嗯,苹果。…橙子。" → 接 Phase 20 对话;扫视调度 R/A/P/F 与对话注意力同套;Zvec 解决召回性能 |
| **G2 四大应用场景** | 桌宠/老师/倾听/家庭:**数 ObjectFile.count 而非 candidate**(R5 修)+ 训测对称的 object-centric(R3 修)+ class-agnostic candidate(R1 修)|
| **G3 短期图片认知** | **R2 是关键** — 仅靠 V0+V8 随 focus 变远不够,V7/V10/V11/V12 也必须 object-centric;多物体合成图测验(G-21-v1a-12)是真测,12 张单主体测不到这能力 |

---

## 15. 这次为什么不会再被打脸

| 风险 | 防护 |
|---|---|
| Codex 实现"diagnostic prose 装饰" 重演? | R2/R3/S1 强制 grep test,新函数名明确 |
| Object-centric 还是混回整图? | RL-21-R2-03 单测:不同 candidate_region 抽出来的 V7/V10/V11/V12 差异 > 0.3 |
| 9/12 又达不到? | R4 多维度验收,7/12 + 多物体 2/3 + soft/firm 比例提升也算通过 |
| 数感数错? | R5 ObjectFile 合并 |
| Zvec 安装失败炸系统? | S4 fallback + import 容错 |
| 我还有别的看不到的工程缺口? | 已直接读 [extract_visual_audit_path_v2:262](apv3test/runtime/visual_receptor.py#L262) 实际实现,而非看设计稿;实现层没看到的还需 Codex 实测 |

---

## 16. 给银子老师拍板项

1. **5 条 Codex 必修 + 4 条自查全部吸收**,是否同意?
2. **优先级 Phase 21 → 19.9 → Phase 20**(Codex 建议同我),是否同意?
3. **多物体合成图**:您拍 5-10 张真水果摆一起的照片(苹果 + 香蕉 + 橙子在桌上),还是用现有 12 张单主体图先打通?

---

## 17. 署名

- 原架构设计:银子老师(笔名)
- v1a 修订:Claude (Anthropic) 吸收 Codex 5 项必修 + 我自查 4 项 + 直接读 visual_receptor.py 找到 mask 未 local 化致命缺口后产出
- 落地:Codex 在 v1a 通过审查后实施

End of Phase 21 v1a Errata.
