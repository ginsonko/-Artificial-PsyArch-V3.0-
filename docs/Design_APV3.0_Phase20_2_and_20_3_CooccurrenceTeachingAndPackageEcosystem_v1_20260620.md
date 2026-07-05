# APV3.0 Phase 20.2 + Phase 20.3 Unified Design — Multimodal Cooccurrence Teaching Bridge + Cooccurrence-Native Memory Package Ecosystem (One Mechanism)

Date: 2026-06-20
Author: Claude(架构),银子老师(风格定调与最终签收)
Status: 完整设计稿(Phase 20.2 + 20.3 写在一份,统一 AP 哲学,等审查)
Final Goal:
- **G1** 自由开放中文对话底座
- **G2** 四大应用场景:网页 demo / agent / 桌宠 / 具身(暂)
- **G3** 短期图片认知
- **G4(新)** 用户教学的可分享生态(导入/导出/卸载/检索)
License intent: AGPL-3.0-or-later
Real name handling: 全文件 grep 真名 = 0

---

## 0. 这一份的核心原则(银子老师明文)

> "所谓的图片标注,根据 AP 的理论,本质上它还是因为这个词和这个图片共现过,所以可以下次看见这个图片时,就能联想到曾经共现输入的这个词汇/文本。而且根据我们的学习理论,多次输入时,共同出现的那个词会天然成为'波峰'被抽象出来,这就实现了标注,而不是脱离 AP 的独立标注。**我们理论上不需要一个单独的体系或者模块来做图片标注这件事**。"

**本设计稿严格遵守**:**不**新增"图片标签表"、"文本-视觉标签字典"、"用户教学条目表"等任何独立映射结构。所有"教学"语义都通过**已存在**的 AP 机制实现:

| AP 既有机制 | 在 Phase 20.2/20.3 中的角色 |
|---|---|
| `CooccurrenceAssociationStore` ([cooccurrence_store.py](apv3test/runtime/cooccurrence_store.py)) | 视觉对象 SA 与文本 SA 在同一 tick 共激活时,关联强度自然累积 |
| `SparsePairwiseGraph` ([sparse_pairwise.py](runtime/cognitive/composed_vocab/sparse_pairwise.py)) | SDPL packet 下的稀疏共现图,反复共现的 token 自然形成波峰 |
| `delta_p_cold_fork` ([delta_p_cold_fork.py](runtime/cognitive/composed_vocab/delta_p_cold_fork.py)) | ΔP 评估让"诊断性强"的共现 token 被 promote |
| `apply_natural_correction_credit` ([natural_correction.py](runtime/cognitive/correction/natural_correction.py)) | 用户纠错走 source-aware credit,不直接覆盖 weights |
| `observe_feeling_expression_cooccurrence` ([cooccurrence_learning.py](apv3test/runtime/cooccurrence_learning.py)) | 情感+表达共现观察的入口,Phase 20.2 在此**加视觉证据维度** |
| `temporal_event_bind` (Phase 19.5/v1e §10) | 跨模态 6 tick 绑定 |

**Phase 20.2 / 20.3 = 这套机制的接通 + 用户界面 + 记忆包导入导出**,不是"标注模块"。

---

## 1. 与 Codex 旧理解的清算(防止再被误会)

| Codex 旧理解 | 银子老师原则 | 本设计纠正 |
|---|---|---|
| "图 + 文本 → 教 AP 这是苹果" 当作图片标签学习 | **不**做标签表 | §4 走 cooccurrence graph,视觉 ObjectFile SA + 文本 token SA 同 packet |
| 独立 teaching paradigm 表保存"什么情境该说什么" | **不**做映射表 | Phase 20.1 现存 teaching paradigm 表 **在 Phase 20.2 重写为** 共现事件的特殊 source marker |
| 一次教学就立刻生效 | **不**做立即覆盖 | §5 通过 `delta_p_cold_fork` + 多次共现自然抽象,n_situations_per_eval=8 既有约束 |
| 记忆包 = 图片标签 list | **不**做标签包 | §7 记忆包 = `(visual_signature_sa, text_token_sa, cooccurrence_count, ΔP_score, source, tick_range)` 共现边集合 |
| 导出 = 把标签 dict 序列化 | **不** | §7 导出 = 选定子图的 `AssociationPair` + 来源元数据,opaque uuid |
| 卸载 = 删 label dict 行 | **不** | §7 卸载 = 按 `import_batch_id` 反向回退共现计数 + 删除 batch 内创建的 packet,不影响 batch 外/共享的边 |

---

## 2. Phase 20.2 设计 — 多模态共现教学桥

### 2.1 核心数据流(完全 AP-native,无新映射表)

```
用户带图说:"这是苹果"
        ↓
Step 1: 文字 tokenize → ["这是","苹果"](走既有 minimalist_dialogue_flow)
Step 2: 图走 Phase 21 → ObjectLookingResult,产 ObjectFile(s)
        每 ObjectFile 包含 candidate.opaque_uuid + recognition.top_concept_uuid
Step 3: 视觉对象 SA 注入 state_pool:
        sa_id = f"vision_object::{obj.candidate.opaque_uuid}::{tick}"
        family = "vision_object"
        channel_signature = ("vision", "object")
Step 4: 文本 token SA 注入 state_pool(既有 minimalist 已做):
        sa_id = f"text_token::{token_hash}::{tick}"
Step 5: temporal_event_bind(tick, vision_uuids=[...], text_token_uuids=[...])
        若 6 tick 窗口内同时存在 → 共享 temporal_event_uuid
Step 6: SDPL packet 形成,通过 sparse_pairwise.observe_packet:
        - 视觉对象 SA 与文本 token SA 之间的共现边 +1
        - packet_key 记 source = "teacher_event"(若用户用了教学按钮)
                       或 source = "natural_dialogue"(自然对话中)
Step 7: 这一切就完了 — 不写"标签",不查"表"
```

**Why**: 完全用 SDPL packet + sparse pairwise graph 完成"学习",这是 AP-Core 既有机制,Phase 20.2 只是**调度**。

### 2.2 召回侧(下次看图怎么"想起苹果"这个词)

```
用户再次上传相似苹果图,无文字
        ↓
Phase 21 → ObjectFile(s),其中 candidate.visual_signature 与之前教学的相似
        ↓
state_pool 注入 vision_object SA(同上)
        ↓
sparse_pairwise.top_partners(vision_object_sa_id) → 返回该视觉对象 SA 关联最强的若干 text token SA
        ↓
若 top partner 满足 delta_p_cold_fork 的诊断性 + 一致性门:
    召回"苹果" token,经 Phase 16 styled corpus → "嗯,苹果。"
否则:
    "嗯。" 或 "...还不能确认。"(诚实)
```

**Why**:
- **不**做"先识别成苹果再说苹果",是**直接由 vision_object SA 的共现伙伴 召回 文本 token**
- 这正是您原话:"下次看见这个图片时,就能联想到曾经共现输入的这个词汇"
- 召回门走既有 `delta_p_cold_fork`,无新阈值

### 2.3 视焦点对齐(关键 — 多对象图不能整图绑标)

银子老师明文:"如果图里有苹果和香蕉,AP 不能把整张图和'苹果'绑定。应该绑定当前选中的 ObjectFile / 当前视焦点区域。"

实现:

```python
def bind_visual_text_cooccurrence(
    object_files: Sequence[ObjectFile],
    text_token_sa_ids: Sequence[str],
    *,
    selected_object_index: int | None,    # 用户在 UI 上点了哪个 ObjectFile
    tick: int,
    state_pool: StatePool,
    sparse_graph: SparsePairwiseGraph,
) -> None:
    """
    若 selected_object_index 指定:
        只把那个 ObjectFile 的 vision_object SA 与文本 token SA 关联.
    若未指定(用户没点):
        - 若只有 1 个 ObjectFile,默认绑它.
        - 若多个 ObjectFile,attention top-1 那个,但同时在 state_pool 中
          为用户注入一个 "请指明哪个" 的不确定标记(让 AP 在下轮可以反问).
    """
```

**Why**:
- 严格遵守"视焦点 = 拟人识别的本质"原则(Phase 21 已实证)
- 多对象时不强行绑,让 AP 有"哪个?"的拟人反应能力(Phase 20.4 可加 styled 反问)

### 2.4 纠错(完全走 source-aware credit,不改答案表)

银子老师明文:"用户说'不是苹果,是橙子'时:旧的视觉-苹果共现权重下降;新的视觉-橙子共现权重上升;并保留 correction trace。"

实现:

```python
def correct_visual_text_cooccurrence(
    last_turn: ChatTurn,
    correction_text: str,
    *,
    state_pool: StatePool,
    sparse_graph: SparsePairwiseGraph,
) -> CorrectionTrace:
    """
    1. 从 last_turn 取被纠错的 (vision_object_sa_id, wrong_text_token_sa_id) 对
    2. 走 apply_natural_correction_credit:
       - R_ext = -1 给 wrong 关联
       - 通过 eligibility trace + credit 分摊到该共现边
    3. 同时把新 correction_text 分词,作为 right_text_token_sa_id
    4. 让 right_text_token_sa 与 vision_object_sa 共现(新教学事件)
    5. 写 correction_trace:
       (vision_object_uuid, wrong_token, right_token, tick, source="natural_correction")
       source marker 走 既有 v14 CORRECTION marker(不新增 marker_kind)
    """
```

**Why**:
- 不存"错误答案 list"和"正确答案 list",只有共现边的强度变化
- 复用既有 `apply_natural_correction_credit` 路径,v1d/v1e 已经审查过
- correction_trace 走既有 CORRECTION marker,保持 v14 cap=20

### 2.5 纯文字教学(承接 Phase 20.1 的"教学范式"但走共现)

银子老师 Phase 20.1 时提的:"用户觉得它的最新回复不满意时,可以直接输入一个'教学范式',来教它这种情况下可以怎么回复用户"。

Phase 20.1 当时**实现成独立 teaching paradigm 表**(错的),Phase 20.2 重写为:

```python
def teach_text_response_paradigm(
    previous_situation_sa_ids: Sequence[str],    # 上轮上下文的 SA(用户上轮文字 + 当时 feeling + 视觉)
    teacher_response_text: str,                  # 用户教的回应
    *,
    state_pool: StatePool,
    sparse_graph: SparsePairwiseGraph,
) -> None:
    """
    1. 把 teacher_response_text 分词成 text_token_sa_ids
    2. 在同一 SDPL packet 内,让 previous_situation_sa_ids 与 teacher_response_text 的 token 共现
    3. packet source = "teacher_taught_paradigm"(opaque 标记 source,不新增 marker_kind)
    4. 多次同情境教学后,通过 sparse_pairwise + delta_p_cold_fork
       自然形成"那种情境下高诊断 token = 教师教的词" 的波峰
    """
```

**为什么这跟 Phase 20.1 现有实现的差别 = 治本**:
- Phase 20.1 现状:`teaching_id` 维护一个独立表,"situation → reply" 查表
- Phase 20.2 修正:所有教学走 SDPL packet + cooccurrence graph,**没有独立表**,跟 AP-Core 共用同一套学习管线
- 多次教学后,稳定的 token 通过 `delta_p_cold_fork.promote_dP_min = 0.05` 既有门自然抽象出来 = 波峰
- 银子老师演示的 bug("说你好它又说这是什么")的根因:Phase 20.1 用了独立表,把 *最后一次* 教学硬覆盖到 *该情境*。改走 cooccurrence graph 后,需要多次稳定共现才会形成 token 召回,**避免一次教学导致的混乱**

### 2.6 Phase 20.2 红线

```
RL-20.2-COC-01: Phase 20.2 不允许新增任何"text → image" 或 "image → label" 映射表
                grep test: 不允许出现 teaching_label_table / image_label_map / visual_label_dict
                等独立映射数据结构

RL-20.2-COC-02: 所有教学事件必走 SDPL packet + sparse_pairwise.observe_packet
                grep test: 不允许 setattr(layer3.concept, "taught_label", ...) 这种直接赋值

RL-20.2-COC-03: 纠错必走 apply_natural_correction_credit 既有路径,
                不允许直接 reset cooccurrence_edge.weight = X

RL-20.2-COC-04: 教学事件的 source marker 走 既有 markers(TEACHER_EVENT / CORRECTION / NATURAL_DIALOGUE)
                不新增 marker_kind(继承 v14 cap=20)

RL-20.2-COC-05: 视觉 ObjectFile SA 注入时,必须保留 candidate.opaque_uuid 作为视觉签名,
                不允许写 candidate.label 进 SA id

RL-20.2-COC-06: 移除/重写 Phase 20.1 的 teaching paradigm 表
                grep test: PHASE20_1_TEACHING_SCHEMA_ID 应不再被引用
                (历史 schema 保留为 deprecated,但 runtime 路径不走)
```

### 2.7 Phase 20.2 Gates(12 条)

| Gate |
|---|
| G-20.2-01 不存在任何独立 label table 数据结构(grep test) |
| G-20.2-02 视觉对象 SA + 文本 token SA 在同一 SDPL packet 内 |
| G-20.2-03 共现走 sparse_pairwise.observe_packet,不绕过 |
| G-20.2-04 召回走 sparse_pairwise.top_partners + delta_p_cold_fork 双门 |
| G-20.2-05 单测:同图教 3 次"苹果",第 4 次再传相似图,无文字,top_partners 含"苹果" token |
| G-20.2-06 单测:同图教 3 次"苹果",第 4 次教 1 次"橙子",sparse_pairwise 两边都有但"苹果"诊断性更高 |
| G-20.2-07 单测:多对象图,只 bind 用户选定的 ObjectFile,其他 ObjectFile 不被绑 |
| G-20.2-08 纠错走 apply_natural_correction_credit + CORRECTION marker |
| G-20.2-09 教学范式("说你好它又说这是什么"演示 bug)在多次稳定教学下不重演:演示用例单测 |
| G-20.2-10 Phase 20.1 teaching paradigm 表路径在 runtime 不再触发(grep test) |
| G-20.2-11 不新增 marker_kind(maintains v14 cap=20) |
| G-20.2-12 全 Phase 20.2 文件真名 0 命中 |

---

## 3. Phase 20.3 设计 — Cooccurrence-Native 记忆包生态

### 3.1 记忆包的真正含义(继承 §2 哲学)

银子老师明文:"导出的不是'图片标签包',而是'多模态共现教学包':视觉对象特征摘要 + 共现文本 token/短句 + 来源 teacher_event + 形成时间、支持度、覆盖样本 + 可卸载的 package_id / memory_id。"

**Phase 20.3 记忆包内容**:

```python
@dataclass(frozen=True)
class CooccurrenceMemoryPackage:
    package_id: str                          # opaque uuid
    package_label_external: str              # 用户取的名字 (audit only, 不进 SA id)
    creator_pseudonymous_id: str             # 既有 pseudonymous identifier
    created_at_iso: str                      # ISO date
    license_id: str                          # AGPL-3.0-or-later / CC-BY-4.0 / 自定
    description_external: str                # 用户写的说明(audit)

    # 真内容:共现边的子图(就是 SparsePairwiseGraph 的导出子集)
    cooccurrence_edges: tuple[CooccurrenceEdge, ...]

    # 视觉签名(若包含视觉教学)
    visual_signatures: tuple[VisualSignatureRecord, ...]

    # 来源元数据(每条共现边的诊断性 + 支持度)
    edge_metadata: dict[str, EdgeMetadata]

    # 不包含
    #   - 原图 bytes(默认不导出,银子老师 Phase 20.3 明文)
    #   - user_text 原文(只 token sa_id + token_hash)
    #   - 文件名(opaque uuid)
    # 单独许可时可附图,但需要单独 license/授权字段


@dataclass(frozen=True)
class CooccurrenceEdge:
    edge_id: str                             # opaque, batch import 时用于回退
    left_sa_id: str                          # 比如 vision_object SA 的 opaque uuid
    right_sa_id: str                         # 比如 text_token SA 的 opaque uuid
    count: float                             # 共现次数
    packet_keys: tuple[str, ...]             # 多 packet 来源 (audit)


@dataclass(frozen=True)
class VisualSignatureRecord:
    signature_id: str                        # opaque
    feature_sha16: str                       # 视觉特征 sha 短 hash
    receptor_version: str                    # 继承 v1e RL
    epistemic_source: str                    # PERCEIVED / TEACHER_EVENT 等
    # 不包含原图 bytes(默认)


@dataclass(frozen=True)
class EdgeMetadata:
    edge_id: str
    coverage_count: int                      # 该边覆盖的样本数
    delta_p_score: float                     # delta_p_cold_fork 评估
    support: float                           # sparse_pairwise stats
    teacher_event_uuid: str                  # 来自哪个 teacher event(若是 teacher source)
    package_source_id: str                   # 该边来自哪个 package(若已 import)
    keyword_tags: tuple[str, ...]            # 用户加的关键词(用于检索)
```

**Why**:
- "记忆包"本质就是 sparse_pairwise graph 的一个**子图导出 + 元数据**
- 没有"图片 → 标签 dict",只有"边 + 边的元数据"
- 不存原图,符合"用户隐私默认不外泄"
- `package_source_id` 让每条边知道自己从哪个 package 来,**为 §3.4 卸载提供根据**

### 3.2 导出 — 选择性导出

银子老师明文:"导出记忆包也可以设置的好一些,如果可以选择记忆范围/选择记忆关键词等就更好了"。

实现 — 提供 6 个过滤维度,可组合:

```python
@dataclass(frozen=True)
class ExportFilter:
    skill_tag: str | None = None             # 如 "fruit_recognition" "greeting_paradigm"
    time_range: tuple[str, str] | None = None # (start_iso, end_iso)
    keyword: str | None = None               # 全文检索(在 audit 文本里 grep,但导出值仍 opaque)
    edge_support_min: float = 0.0            # 最小支持度
    delta_p_min: float = 0.0                 # 最小诊断性
    manual_include_edge_ids: tuple[str, ...] = ()
    manual_exclude_edge_ids: tuple[str, ...] = ()


def export_memory_package(
    filter: ExportFilter,
    *,
    include_visual_signatures: bool = True,
    include_original_images: bool = False,    # 默认 False,符合 §3.1
    license_id: str = "CC-BY-4.0",
    package_label_external: str = "",
    description_external: str = "",
) -> CooccurrenceMemoryPackage:
    """
    1. 在 sparse_pairwise + edge_metadata 上按 filter 选边
    2. 包装成 CooccurrenceMemoryPackage
    3. opaque_uuid 化所有 sa_id(用户每次导出使用新映射,防止跟踪)
    4. 写到磁盘 (json + ed25519 签名,可选)
    """
```

### 3.3 检索 + UI(给银子老师"如果记忆太多")

```python
def search_memory_for_export(
    query: str,
    *,
    top_k: int = 100,
) -> list[EdgeMetadata]:
    """
    检索接口,用户在 UI 上:
    - 输入关键词
    - 选时间段
    - 看技能 tag
    返回边列表
    """


def batch_select_edges(
    metadata_list: list[EdgeMetadata],
    *,
    select_all: bool = False,
    invert: bool = False,
) -> list[str]:
    """支持全选 / 反选 / 单选"""
```

银子老师明文:"如果记忆太多,也应该支持检索和批量勾选/反选" — 上述 API 全覆盖。

### 3.4 导入 — 自动去重

银子老师明文:"导入时自动去重"。

```python
def import_memory_package(
    package: CooccurrenceMemoryPackage,
    *,
    sparse_graph: SparsePairwiseGraph,
    edge_metadata_store: EdgeMetadataStore,
) -> ImportTrace:
    """
    1. 计算 import_batch_id = uuid()
    2. 对每条 edge:
       a. 用 (left_sa_id, right_sa_id, packet_signature) 算 dedup_key
       b. 若 sparse_graph 已存该边 → 标记为 deduplicated,不累加,记下 dedup_match
       c. 否则 → 创建新边,记 package_source_id = package.package_id
                              + import_batch_id = batch_id
    3. 视觉签名同样去重
    4. 返回 ImportTrace:
       (import_batch_id, new_edge_ids, deduplicated_edge_ids,
        new_signature_ids, deduplicated_signature_ids)
    """
```

### 3.5 卸载 — 精准回退

银子老师明文:"卸载时只删除该包新增的记忆,不删原本已有或由别的包共享的记忆"。

```python
def uninstall_memory_package(
    import_batch_id: str,
    *,
    sparse_graph: SparsePairwiseGraph,
    edge_metadata_store: EdgeMetadataStore,
) -> UninstallTrace:
    """
    1. 找该 import_batch_id 创建的 new_edge_ids
       (注意:dedup 过的不在内 — 那些已经在用户既有图谱里)
    2. 对每条 new_edge:
       a. 从 sparse_graph 删除该边
       b. 从 edge_metadata_store 删除
    3. 对该 batch 创建的 visual_signatures 同样回退
    4. 不动 dedup_matches(那是用户自己已有的)
    5. 返回 UninstallTrace
    """
```

**关键性质**:**卸载后状态等同于从未导入该包**(去重的部分本来就在用户图谱里,不卸)。

### 3.6 隐私默认值(银子老师明文)

```yaml
phase20_3:
  export:
    include_original_images_default: false       # @structural
    include_user_text_raw_default: false         # @structural
    include_pseudonymous_id_default: false       # @structural (是否暴露创建者)
    include_audit_chat_history_default: false    # @structural
```

用户可显式打开,但默认全关。

### 3.7 Phase 20.3 红线

```
RL-20.3-Pkg-01: 导入包不允许跳过 dedup
                grep test: import 路径必经 dedup_key 计算

RL-20.3-Pkg-02: 卸载必按 import_batch_id 精准
                grep test: 不允许 sparse_graph.clear() 整体清

RL-20.3-Pkg-03: 默认导出不包含原图 / user_text raw
                grep test: include_original_images_default 必须 False

RL-20.3-Pkg-04: 包内 sa_id opaque uuid 化,不暴露内部 sa_id 模式

RL-20.3-Pkg-05: 包的 license_id 必填(白名单内)
                白名单:AGPL-3.0-or-later / CC-BY-4.0 / CC0-1.0 / 自定义需用户输入完整文本

RL-20.3-Pkg-06: 共享包不存真名 + 真名 grep test 0 命中
```

### 3.8 Phase 20.3 Gates(10 条)

| Gate |
|---|
| G-20.3-01 export 6 维过滤都单测覆盖 |
| G-20.3-02 search 接口返回结果与 sparse_pairwise 一致 |
| G-20.3-03 batch select all/invert 单测 |
| G-20.3-04 import dedup 单测:导入同包两次,第二次全 deduplicated |
| G-20.3-05 import → uninstall 完全可逆性:状态 hash 与导入前一致 |
| G-20.3-06 dedup 的边不被卸载(共享边保留) |
| G-20.3-07 默认导出不含原图 / user_text raw(单测) |
| G-20.3-08 包内 sa_id 全 opaque uuid(grep test) |
| G-20.3-09 包 license_id 白名单单测 |
| G-20.3-10 真名 0 命中 |

---

## 4. UI 改进(银子老师当前演示提的)

银子老师明文:"我不喜欢这个'输入已隐藏',为什么要隐藏,看不懂。"

→ Codex 这次已修(http://127.0.0.1:8771/ 现在显示用户原文)。**Phase 20.2 实现需保持**:

- 当前轮 user_text 在 UI 显示**真原文**(便于用户审阅自己输入了什么)
- SQLite 持久化仍**只存 hash + length**(隐私不破),只是 UI session 内存中显示原文
- 单测:刷新页面后历史轮 user_text 仍隐藏(因为 SQLite 没存,符合隐私)

```
RL-20.2-UI-01: 当前 session 内,UI 显示当前轮用户原文
RL-20.2-UI-02: SQLite 持久化仍只 hash + length(不变 v14 RL)
RL-20.2-UI-03: 跨 session 历史轮显示"输入已隐藏"或长度提示(隐私必要)
```

---

## 5. 落地分解(给 Codex,6 天)

| 天 | 工作 |
|---|---|
| **Day 1** | **§2.6 RL 红线先实施**:删 Phase 20.1 独立 teaching paradigm 表的 runtime 调用 + grep test 红线 + 旧 schema 标 deprecated |
| **Day 2** | **§2.1-2.3 多模态共现教学桥**:vision_object SA 注入 + temporal_event_bind + sparse_pairwise.observe_packet 接通 + 单测 G-20.2-02..05 |
| **Day 3** | **§2.4-2.5 纠错 + 文字教学**:apply_natural_correction_credit 接 + teach_text_response_paradigm 重写 + 单测 G-20.2-06, 08, 09 |
| **Day 4** | **§3.1-3.3 记忆包数据结构 + 导出 + 检索 + UI 选择** + 单测 G-20.3-01..03 |
| **Day 5** | **§3.4-3.5 导入(dedup)+ 卸载(精准回退)**+ 单测 G-20.3-04..06 |
| **Day 6** | UI(§4)+ Final Report + 展示页(银子老师可直接试导出/卸载演示) |

---

## 6. 与最终目标的对应

| 目标 | Phase 20.2 / 20.3 怎么交付 |
|---|---|
| **G1 自由开放中文对话** | §2 共现教学 = 用户能用拟人方式教 AP 说话,不需要任何 label dict |
| **G2 四大场景** | 网页 demo 直接受益(用户教 → AP 学);agent tool 输出"我现在记得这是 X"(因为共现强);桌宠未来通过共现自然形成性格 |
| **G3 短期图片认知** | §2.2 视觉对象 SA 召回文本 token 波峰 = 真正"拟人识别 = 移动视焦点后联想曾共现的词" |
| **G4 教学生态** | §3 记忆包导入/导出/卸载 + 检索 + 选择性 = 用户社区可分享教学经验 |

---

## 7. 边界

- **不**做"如果记忆包来自不可信源该怎么办"(Phase 20.3 不做验证签名 / 反审查机制,Phase 21+)
- **不**做"自动从社区下载记忆包",必须用户手动导入
- **不**做"分布式同步",必须用户主动上传/下载文件
- **不**做"共现图谱可视化界面"(选 top 100 edges 文本表即可,Phase 24+)
- 视觉对象签名(visual_signature)使用既有 Phase 19/19.9 候选框签名,不新发明

---

## 8. 为什么这次方案 Codex 真听得懂(防误会)

| 防误会措施 | 做法 |
|---|---|
| 不再用"标注"两个字 | 全文用"多模态共现"代替"图片标注" |
| 不允许独立映射表 | §2.6 RL 红线 + grep test |
| 不允许立即覆盖 | 走既有 delta_p_cold_fork |
| 重写 Phase 20.1 旧实现 | Day 1 第一件事,grep test 防回归 |
| 引用既有文件路径 | §0 表格里直接给路径 |
| 数学模型继承既有 | sparse_pairwise / delta_p_cold_fork / source-aware credit 都已有 |
| 演示 bug 作为单测 | G-20.2-09 直接复现"说你好它又说这是什么"演示 case |

---

## 9. 银子老师拍板项

1. **Phase 20.2 = 多模态共现教学桥(无独立模块)** + **Phase 20.3 = 共现记忆包生态**(导入/导出/卸载/检索/选择性),**统一在一份设计稿**:同意吗?
2. **核心红线 §2.6 + §3.7**:任何想加/删?
3. **演示 bug 单测**(G-20.2-09 复现"说你好它又说这是什么"):需要您手动给 5 个 turn 的 transcript,我让 Codex 加进 unit test
4. **记忆包许可证白名单** §3.7 RL-20.3-Pkg-05:AGPL / CC-BY / CC0 三个够吗?

---

## 10. 署名

- 原架构设计:银子老师(笔名)
- Phase 20.2 + 20.3 统一设计:Claude (Anthropic) 在银子老师"AP 哲学 = 共现,不要独立模块"明文原则下,直接读 cooccurrence_store / sparse_pairwise / delta_p_cold_fork / natural_correction 既有底座后产出
- 落地:Codex 在审查通过后 6 天落地

End of Phase 20.2 + 20.3 Unified Design.
