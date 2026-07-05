# APV3.0 Phase 13 — Cognitive Curriculum 设计稿 v3.2a Landing Errata

日期: 2026-06-18
作者: 银子老师 / Claude 协作
状态: **v3.2 经 Codex 第四轮对抗审阅识别 6 个未根治问题(其中 3 个是 v3.2 自己造的新缝隙)。v3.2a 是精准 Errata 补丁,作为 Phase 13.0 的 must-fix gates 条目。每条都给出具体代码位置 + 修复方案 + 验收测试。Codex 实施依据 = v3 + v3.1 + v3.2 + v3.2a 四稿。**

前作:
- [v3](Design_APV3.0_Phase13_CognitiveCurriculum_v3_20260618.md)
- [v3.1 ERRATA](Design_APV3.0_Phase13_CognitiveCurriculum_v3_1_ERRATA_20260618.md)
- [v3.2 Landing Patch](Design_APV3.0_Phase13_CognitiveCurriculum_v3_2_LandingPatch_20260618.md)

许可:AGPL-3.0-or-later
原架构设计:银子老师

---

## 0. v3.2 → v3.2a 修复总览

| 问题 | v3.2 错在哪 | v3.2a 修复 |
|---|---|---|
| **F1** 隐私修复未覆盖全部持久化路径 | 只盯 chat.py,漏掉 incoming_external_query / web_chat.py / dialogue_flow trace | 全状态扫描红线 + 清理 5 个文件 |
| **F2** 短 hash 不是匿名化 | sha256 前 16 字符易字典反推 "你好" 等高频文本 | 改 per-install salt HMAC,文档措辞改 "pseudonymous local identifier" |
| **F3** trust gate 仍未限定 effect_size 来源 | trust=0.95 + n=5 + p=0.20 时若 effect_size 来自训练集,噪声可过 | 强制 effect_size 来自 held-out cold-fork,加 isolation 测试 |
| **F4** sybil/多教师冲突有回退风险 | v3.2 取最大票,纯 HEARSAY 冲突时仍可能由 community 联合压过 official | 纯 HEARSAY 冲突默认 awaiting_revalidation;只 official+margin 暂定 |
| **F5** context_tag 红线脚本太窄 | 只 grep `if x == "默认"`,漏 dict route / match-case / .get / 英文 tag | AST 扫描 + 白名单(metadata 只许审计读) |
| **F6** held-out pool 可能带答案 | held-out event 若含目标 vocab label = 隐性答案 | held-out 严格只许 PERCEIVED raw normalized sensor SA |

---

## 第 1 章 F1 根治 — 隐私覆盖所有持久化路径

### 1.1 Codex 指出 + 我的实测扫描

Codex line:`APV3.0test/apv3test/runtime/minimalist_dialogue_flow.py:113` 也存原文。

我实际扫描全 runtime 后,发现持久化路径**远不止 chat.py 一处**:

| 文件 | 行 | 问题 | 严重度 |
|---|---|---|---|
| `apv3test/chat.py` | 132 | `"user_text": text` 进 trace | v3.2 已 patch,但还要复查 |
| `apv3test/chat.py` | 110 | `incoming_external_query=(text,)` 传给 dialogue flow | **新发现** |
| `apv3test/runtime/minimalist_dialogue_flow.py` | 34, 113 | `incoming_external_query` 作 dataclass 字段 + 进 trace | **Codex 指出** |
| `apv3test/runtime/incremental_tick_runtime.py` | 39, 80 | 同样字段透传 | **新发现** |
| `apv3test/runtime/reply_pressure.py` | 59, 83 | `incoming_external_query: Sequence[str]` 传入 + 使用 | **新发现** |
| `apv3test/web_chat.py` | 199, 259, 271 | Web snapshot 存 user_text | **新发现** |
| `apv3test/web/static/app.js` | 113, 207 | 前端渲染 user_text | 前端可接受,但 server 不应输出 |
| `apv3test/data/runtime_profile_minimalist_cli.json` | 41 | profile 含 "incoming_external_query ==" 字符串 | 配置层,要核查 |

**只改 chat.py 一处远不够。v3.2a 必须修齐 5 个源文件 + 1 个配置**。

### 1.2 v3.2a 根治方案

#### 1.2.1 重构原则

`incoming_external_query` 这个字段名设计时就含原文,**整个字段需要拆成两层**:

- **内部使用层(runtime 内传递)**:可保留原文,因为 runtime tick 内确实需要文本驱动 sensor adapter
- **持久化/序列化层(trace / snapshot / SQLite)**:绝不能含原文,只能 hash + length

#### 1.2.2 修订:`MinimalistDialogueTurnTrace` schema

```python
# apv3test/runtime/minimalist_dialogue_flow.py v3.2a

from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class MinimalistDialogueTurn:
    """运行时使用的 turn,内部含原文,不持久化."""
    tick: int
    incoming_external_query: tuple[str, ...] = ()  # 运行时用,不进 trace
    # ... 其他字段


@dataclass(frozen=True)
class MinimalistDialogueTurnTrace:
    """持久化用的 turn trace,绝不含原文."""
    schema_id: str = "apv3_minimalist_dialogue_turn_trace/v2"  # bump
    tick: int = 0
    incoming_query_hash: Optional[str] = None     # v3.2a: 替代 incoming_external_query
    incoming_query_length: int = 0                # v3.2a: 长度 metadata
    incoming_query_source: str = ""               # v3.2a: marker source(如 "user_text")
    # ... 其他不含原文的字段


def turn_to_trace(turn: MinimalistDialogueTurn, *, persist_user_text: bool = False) -> dict:
    """运行时 turn → 持久化 trace 转换.
    
    v3.2a: 默认 persist_user_text=False,绝不存原文.
    """
    trace = {
        "schema_id": "apv3_minimalist_dialogue_turn_trace/v2",
        "tick": turn.tick,
        "incoming_query_count": len(turn.incoming_external_query),
        "incoming_query_total_length": sum(len(s) for s in turn.incoming_external_query),
    }
    
    # 严格控制原文持久化
    if persist_user_text:
        # 用户显式 opt-in,经法律同意
        trace["incoming_external_query"] = list(turn.incoming_external_query)
    else:
        # 默认路径:存 hash + metadata,不存原文
        trace["incoming_query_hash"] = compute_pseudonymous_identifier(
            turn.incoming_external_query
        )
        # NOTE: 字段不叫 "incoming_external_query",名字本身就改了
    
    return trace
```

#### 1.2.3 web_chat.py 同样修订

```python
# apv3test/web_chat.py v3.2a

def snapshot_for_web(turn, persist_user_text: bool = False):
    """v3.2a: Web snapshot 也走同样的 opt-in 控制."""
    if persist_user_text:
        return {
            "tick": turn.tick,
            "user_text": str(getattr(turn, "user_text")),
        }
    else:
        return {
            "tick": turn.tick,
            "user_text": None,                # 显式 None
            "user_text_hash": compute_pseudonymous_identifier(...),
            "user_text_length": len(str(getattr(turn, "user_text", ""))),
        }


# Line 271 修订
def attention_inject_for_external(latest_chat):
    """ledger.inject 不需要原文,只需要 metadata."""
    has_external = bool(
        latest_chat.get("user_text") or 
        latest_chat.get("user_text_hash") or
        latest_chat.get("user_text_length", 0) > 0
    )
    item.gain_ledger.inject("external", 0.7 if has_external else 0.1)
```

#### 1.2.4 reply_pressure.py 同样要修

```python
# apv3test/runtime/reply_pressure.py v3.2a

def compute_reply_pressure(
    *,
    incoming_query_metadata: Optional[dict] = None,  # v3.2a: 改用 metadata 而非原文
    # 旧:incoming_external_query: Sequence[str] = ()  # 删
):
    """
    v3.2a: reply pressure 不需要原文,只需要"有外源"信号.
    """
    if incoming_query_metadata and incoming_query_metadata.get("count", 0) > 0:
        # 有外源,产生 pressure
        ...
```

#### 1.2.5 runtime_profile_minimalist_cli.json 修订

```json
{
    "...": "...",
    "trace_schema_version": "apv3_minimalist_dialogue_turn_trace/v2",
    "persist_user_text": false,
    "pseudonymous_id_method": "hmac_sha256_per_install_salt"
}
```

### 1.3 全状态红线扫描(F1 必修测试)

```python
# tests/test_phase13_0_privacy_global_scan.py

def test_state_pool_serialization_does_not_contain_user_text():
    """
    F1 全状态扫描:保存后 str(load_state()) 不得包含已知用户输入原文.
    """
    # 准备特殊"金丝雀"文本
    canary_text = "CANARY_SENTINEL_私密文本_2026"
    
    # 走完整 dialogue 路径
    session = ConversationSession(persist_user_text=False)
    session.commit_user_turn(canary_text, tick=1)
    
    # 1. 检查 SQLite blob
    store = SQLiteRuntimeStore(session.profile.sqlite_state_path)
    saved_state_dict = store.load_latest()
    serialized = str(saved_state_dict)
    
    assert canary_text not in serialized, f"原文泄露到 SQLite: {serialized[:500]}"
    
    # 2. 检查所有 incoming_external_query 字段
    chat_trace = saved_state_dict.get("chat_session_trace", [])
    for entry in chat_trace:
        for key, value in entry.items():
            assert canary_text not in str(value), \
                f"原文泄露到 trace {key}: {value}"
    
    # 3. 检查 dialogue flow trace
    dialogue_trace = saved_state_dict.get("dialogue_session_trace", [])
    for entry in dialogue_trace:
        # 严格:不应有 incoming_external_query 字段(已被 hash 替代)
        assert "incoming_external_query" not in entry, \
            "v3.2a: 应改为 incoming_query_hash"
    
    # 4. 检查 web snapshot
    web_snapshot = saved_state_dict.get("web_chat_snapshot", {})
    assert canary_text not in str(web_snapshot)


def test_runtime_can_function_without_persisting_user_text():
    """v3.2a: 不存原文时,runtime 仍能正常工作."""
    session = ConversationSession(persist_user_text=False)
    
    # 跑 5 轮对话
    for i in range(5):
        result = session.commit_user_turn(f"测试 {i}", tick=i)
        assert result.committed_text is not None
        # commit 出来的回复应该不依赖原文持久化


def test_explicit_opt_in_persists_user_text():
    """显式 opt-in 时,原文可被持久化."""
    canary = "OPT_IN_CANARY_2026"
    session = ConversationSession(persist_user_text=True)  # 显式同意
    session.commit_user_turn(canary, tick=1)
    
    store = SQLiteRuntimeStore(session.profile.sqlite_state_path)
    saved = str(store.load_latest())
    
    assert canary in saved  # opt-in 路径下,原文确实在
```

---

## 第 2 章 F2 根治 — pseudonymous identifier(非匿名化)

### 2.1 Codex 指出

v3.2 用 `sha256(text)[:16]` 作"hash",但 sha256 是确定性的:
- 同样的 "你好" 永远 hash 成同样的前 16 字符
- 字典反推:预计算所有 1-3 字常用中文的 sha256 → 反查
- 16 字符 hash 防不住 "你好" "在吗" 等高频文本

**这不是匿名化**。

### 2.2 v3.2a 根治:per-install salt + HMAC

```python
# apv3test/util/pseudonymous_id.py

import hmac
import hashlib
import os
import secrets
from pathlib import Path


_SALT_FILE_NAME = "install_salt.bin"
_SALT_LENGTH_BYTES = 32


def get_or_create_install_salt(state_dir: Path) -> bytes:
    """
    每次安装生成一个 32 字节随机 salt,存本地.
    
    v3.2a:
    - 每安装唯一(不同设备不同 salt)
    - 不进 git / 不共享
    - 不上传任何远程
    - 用户删除 install_salt.bin → 历史 hash 失去关联(等价匿名化)
    """
    salt_path = state_dir / _SALT_FILE_NAME
    
    if salt_path.exists():
        return salt_path.read_bytes()
    
    # 生成新 salt
    salt = secrets.token_bytes(_SALT_LENGTH_BYTES)
    state_dir.mkdir(parents=True, exist_ok=True)
    salt_path.write_bytes(salt)
    
    # 设置文件权限(unix 系统)
    try:
        os.chmod(salt_path, 0o600)  # 仅 owner 读写
    except (OSError, NotImplementedError):
        pass  # Windows / 不支持
    
    return salt


def compute_pseudonymous_identifier(
    text: str,
    state_dir: Path = Path("state"),
) -> str:
    """
    v3.2a: 用 per-install salt + HMAC-SHA256 计算 pseudonymous identifier.
    
    NOT anonymous — 同设备同 text 仍可关联.
    BUT 跨设备无关联,远程不可反推(无 salt 时).
    
    返回 16 字符(用作本地索引足够,不暴露原文)
    """
    salt = get_or_create_install_salt(state_dir)
    h = hmac.new(salt, text.encode("utf-8"), hashlib.sha256)
    return h.hexdigest()[:16]
```

### 2.3 PRIVACY.md 措辞修订

```markdown
# Privacy Policy / 隐私政策(v3.2a 修订)

## Pseudonymous Local Identifier

We use **pseudonymous local identifiers** (not anonymous identifiers) for 
indexing user inputs that you have NOT opted to persist as raw text.

### 技术细节

For text inputs you have not opted to persist as raw, we compute:

```
identifier = HMAC-SHA256(per_install_salt, text)[:16]
```

Where:
- `per_install_salt`: 32-byte random salt, generated on first run, stored 
  locally in `state/install_salt.bin`, never transmitted
- `text`: your input text (this raw text is NOT stored)

### Properties

- **Pseudonymous, not anonymous**: 
  Same text on same install produces same identifier (used for deduplication).
  Different installs produce completely different identifiers.
- **Not reversible**: 
  Without the per-install salt, the identifier cannot be reversed to text.
  However, on the SAME install, an attacker with access to the salt and a 
  candidate text could verify whether that text was input.
- **Anonymization**: 
  Deleting `state/install_salt.bin` invalidates all historical identifiers,
  achieving practical anonymization on that install.

### What This Is NOT

- This is NOT cryptographic anonymization
- This is NOT GDPR-compliant anonymization (per Article 26 IDs may still 
  identify if salt is compromised)
- This IS suitable for: local debugging, deduplication, statistical analysis

### Full Anonymization

For full anonymization, opt out of even pseudonymous identifiers:

```bash
python -m apv3 privacy_set --pseudonymous_id false
```

This disables hash storage entirely; only length metadata is kept.
```

### 2.4 yaml 配置

```yaml
# apv3_constants.yaml(v3.2a 新增)
privacy:
  pseudonymous_id_enabled: true              # @structural — 默认开,可关
  pseudonymous_id_method: "hmac_sha256_per_install_salt"  # @structural
  pseudonymous_id_length_chars: 16           # @structural
  install_salt_path: "state/install_salt.bin"  # @structural
```

### 2.5 验收测试

```python
def test_pseudonymous_identifier_is_install_specific():
    """同 text 在不同 install 应不同."""
    with tempdir() as dir1:
        id1 = compute_pseudonymous_identifier("你好", state_dir=dir1)
    
    with tempdir() as dir2:
        id2 = compute_pseudonymous_identifier("你好", state_dir=dir2)
    
    assert id1 != id2, "不同 install 应有不同 salt → 不同 identifier"


def test_dictionary_attack_resistance():
    """无 salt 时,不能反推常见文本."""
    # 攻击者预计算 "你好" 的 sha256[:16] 
    naive_hash = hashlib.sha256("你好".encode()).hexdigest()[:16]
    
    # 但我们的 identifier 不是裸 sha256
    with tempdir() as dir:
        our_id = compute_pseudonymous_identifier("你好", state_dir=dir)
    
    assert our_id != naive_hash  # 不会被字典反推


def test_install_salt_persists_across_session():
    """同一 install 内,salt 持久."""
    with tempdir() as dir:
        id1 = compute_pseudonymous_identifier("你好", state_dir=dir)
        id2 = compute_pseudonymous_identifier("你好", state_dir=dir)
        assert id1 == id2  # 同 install 同 text → 同 identifier


def test_deleting_salt_invalidates_history():
    """删 salt 文件等价匿名化."""
    with tempdir() as dir:
        id1 = compute_pseudonymous_identifier("你好", state_dir=dir)
        
        # 删 salt
        (dir / "install_salt.bin").unlink()
        
        # 新生成的 salt 不同 → 同样的 text 给出不同 identifier
        id2 = compute_pseudonymous_identifier("你好", state_dir=dir)
        assert id1 != id2  # 历史 identifier 与新的无关联
```

---

## 第 3 章 F3 根治 — trust gate effect_size 必须来自 held-out

### 3.1 Codex 指出

v3.2 公式数学对了(effect_size_hard_min=0.03),**但没说 effect_size 从哪来**。

如果 effect_size 计算从 training_episodes 数据来:
- trust=0.95 + n=5 + p=0.20 + effect_size=0.035(来自训练集)→ 过 gate
- 但训练集 effect_size 35‰ 可能是过拟合,不是真效应
- → 噪声通过

### 3.2 v3.2a 根治:effect_size 必须来自 held-out cold-fork

复用 v14 Phase 8.4 cold-fork ΔP 机制(已实现):

```python
# runtime/cognitive/curriculum/teaching_protocol.py v3.2a

from runtime.cognitive.composed_vocab.delta_p_cold_fork import (
    evaluate_delta_p_incremental,
    VocabCandidate,
)


def teach_vocab_v3_2a(state_pool, long_term, held_out_pool, *, content_item, teacher_entity, tick):
    """
    v3.2a: effect_size 必须来自 held-out,不许从教学 episodes 计算.
    
    流程:
    1. spawn PERCEIVED + HEARSAY markers(教学 episode)
    2. 等待教学完成(N 个 episodes)
    3. 用 cold-fork ΔP 在 held-out 上评估 effect_size
       — 注意:这里 held_out 必须与教学 episodes 隔离
    4. trust_promote_gate_v3_2 用此 effect_size 判定
    """
    teaching_episodes_completed = []
    
    # === 步骤 1: 教学 ===
    for episode_i in range(load_constant("curriculum.teaching_protocol.teaching_episode_per_vocab")):
        episode = run_teaching_episode(state_pool, content_item, teacher_entity, tick)
        teaching_episodes_completed.append(episode)
    
    # === 步骤 2: 关键 — effect_size 来自 held-out,不是教学 episodes ===
    candidate = VocabCandidate(
        candidate_id=content_item.sa_id,
        component_ids=tuple(content_item.related_sa_ids),
        predicted_pressure_reduction=0.1,  # prior
    )
    
    delta_p_result = evaluate_delta_p_incremental(
        candidate,
        current_pool=state_pool,
        held_out_pool=held_out_pool,  # ★ 这是关键:held-out 与教学隔离
    )
    
    if delta_p_result.fallback_to_pmi_only:
        # held-out 不够,gate 暂缓
        return TeachResult(
            status="awaiting_revalidation",
            failed_reason="insufficient_held_out",
            ...
        )
    
    # delta_p_result.mean_delta_P 是来自 held-out 的 effect_size
    effect_size = delta_p_result.mean_delta_P
    p_value = delta_p_result.p_value
    n_obs = delta_p_result.n_situations_positive  # 来自 held-out
    
    # === 步骤 3: trust gate(用 held-out 数据) ===
    if not trust_promote_gate_v3_2(
        vocab=candidate,
        teacher=teacher_entity,
        effect_size=effect_size,
        p_value=p_value,
        n_obs=n_obs,
    ):
        return TeachResult(status="rejected", failed_reason="delta_p_fail", ...)
    
    # === 步骤 4: 通过,promote ===
    return TeachResult(status="promoted", ...)
```

### 3.3 关键隔离保证

```python
# held_out_pool 必须完全独立于教学 episodes
# 这通过 v3.2 §S6 + v3.2a F6(下章)保证

# 1. held-out events 在课程包加载时预留(K-fold 抽样)
# 2. 教学 episodes 完成后,held-out 不参与教学统计
# 3. effect_size 计算只走 held-out,不混 training
```

### 3.4 必修测试

```python
def test_effect_size_from_training_alone_does_not_pass_gate():
    """
    F3 验证:即使训练集 effect_size 高,
    若 held-out effect_size 不够,gate 也不过.
    """
    teacher = TeacherEntitySA(trust_score=0.95)
    
    # 准备一个"训练过拟合"场景:
    # - 教学 episodes 重复同一对照样本,造成训练 effect_size 高
    # - 但 held-out 完全不同(无关联)→ held-out effect_size 低
    
    training_episodes = generate_overfit_training_episodes(n=100)
    held_out_pool = generate_truly_held_out_events(n=50)  # 与训练无关
    
    candidate = generate_test_vocab()
    
    # 用 held-out 评估
    delta_p_result = evaluate_delta_p_incremental(
        candidate,
        current_pool=mock_state_pool(),
        held_out_pool=held_out_pool,
    )
    
    # held-out effect_size 应低(因为是真噪声)
    assert delta_p_result.mean_delta_P < 0.03
    
    # gate 应拒
    passed = trust_promote_gate_v3_2(
        vocab=candidate,
        teacher=teacher,
        effect_size=delta_p_result.mean_delta_P,  # 来自 held-out
        p_value=delta_p_result.p_value,
        n_obs=delta_p_result.n_situations_positive,
    )
    
    assert passed is False, "训练过拟合时,held-out effect_size 低,不应过 gate"


def test_held_out_events_isolated_from_training():
    """validate 教学 episodes 与 held-out 完全隔离."""
    # 训练时记录每个 episode 的 SA id
    training_sa_ids = set()
    for episode in teaching_episodes:
        training_sa_ids.update(episode.touched_sa_ids)
    
    # held-out events 的 SA id 不应与 training 重合
    held_out_sa_ids = set()
    for event in held_out_pool.held_out_events:
        held_out_sa_ids.update(event.touched_sa_ids)
    
    assert not (training_sa_ids & held_out_sa_ids), \
        "held-out 与 training 不应有 SA id 重合"
```

---

## 第 4 章 F4 根治 — 多教师纯 HEARSAY 冲突默认等待 PERCEIVED

### 4.1 Codex 指出

v3.2 `resolve_multi_teacher_conflict_v3_2` 在纯 HEARSAY 冲突时**直接返回最大票**。这比 v3.1 "等待 PERCEIVED revalidation" 更冒险:
- community(tier=0.5)联合 2 票 = 1.0 加权
- 单 official(tier=0.9)= 0.9
- → community 联合压过 official

### 4.2 v3.2a 根治

```python
def resolve_multi_teacher_conflict_v3_2a(vocab_sa, conflicting_teachers):
    """
    v3.2a: 纯 HEARSAY 冲突默认 awaiting_revalidation.
    仅 official + margin 才暂定结论,但仍需 PERCEIVED revalidation.
    """
    # 1. 先检查 PERCEIVED evidence
    perceived = state_pool.get_perceived_evidence(vocab_sa)
    if perceived:
        # PERCEIVED 决胜,直接返回
        return ConflictResolution(
            attribute_value=perceived.attribute_value,
            status="resolved_by_perceived",
            requires_revalidation=False,
        )
    
    # 2. 纯 HEARSAY 冲突
    vote_weights = compute_weighted_votes(conflicting_teachers)
    vote_weights = apply_tier_cap(vote_weights, conflicting_teachers)
    
    if not vote_weights:
        return ConflictResolution(
            attribute_value=None,
            status="awaiting_revalidation",
            requires_revalidation=True,
        )
    
    # 3. 检查是否有 official + margin
    OFFICIAL_TRUST_MIN = 0.85       # @structural
    PROVISIONAL_MARGIN = 1.5         # @structural — official 票必须超第二名 1.5 倍
    
    sorted_votes = sorted(vote_weights.items(), key=lambda x: x[1], reverse=True)
    top_value, top_weight = sorted_votes[0]
    second_weight = sorted_votes[1][1] if len(sorted_votes) > 1 else 0
    
    # 检查 top 是否来自 official tier 且 margin 足够
    top_supporters = [
        t for t, attr in conflicting_teachers.items() 
        if attr == top_value
    ]
    top_is_official = any(
        get_teacher_entity(t).trust_tier == "official"
        for t in top_supporters
    )
    
    if top_is_official and top_weight >= second_weight * PROVISIONAL_MARGIN:
        # 暂定结论,但仍要 PERCEIVED revalidation
        return ConflictResolution(
            attribute_value=top_value,
            status="provisional_official_pending_perceived",
            requires_revalidation=True,
            trust_promoted_pending_perceived=True,
        )
    
    # 4. 不满足 → awaiting_revalidation
    return ConflictResolution(
        attribute_value=None,
        status="awaiting_revalidation",
        requires_revalidation=True,
    )
```

### 4.3 vocab SA 加标记

```python
@dataclass
class VocabSA:
    ...
    trust_promoted_pending_perceived: bool = False  # v3.2a
    # 这是 marker(继承 v14 marker SA 多态原则),不是 bool 字段
    # → 改 spawn 一个 MarkerKind.PENDING_PERCEIVED marker
```

实际:**v3.2a 不在 VocabSA 加 bool,改 spawn 单独 marker**:

```python
class MarkerKind:
    PENDING_PERCEIVED_REVALIDATION = "pending_perceived_revalidation"
    # 加入 v14 documented kinds(扩 cap)
```

### 4.4 验收

```python
def test_community_coalition_cannot_override_official():
    """v3.2a: community 联合 2 票不能压 official 1 票."""
    official = TeacherEntitySA(trust_score=0.9, trust_tier="official")
    community_1 = TeacherEntitySA(trust_score=0.5, trust_tier="community_signed")
    community_2 = TeacherEntitySA(trust_score=0.5, trust_tier="community_signed")
    
    conflicts = {
        official.teacher_id: "value_A",
        community_1.teacher_id: "value_B",
        community_2.teacher_id: "value_B",
    }
    
    result = resolve_multi_teacher_conflict_v3_2a(
        vocab_sa=mock_vocab(),
        conflicting_teachers=conflicts,
    )
    
    # community 联合 1.0(经 tier cap)vs official 0.9
    # 但 official 必须超 1.5 倍才暂定,1.5 × 1.0 = 1.5 > 0.9 → 不满足
    # → awaiting_revalidation
    assert result.status == "awaiting_revalidation"


def test_pure_hearsay_majority_defaults_to_awaiting():
    """纯 HEARSAY 多教师同意,但无 PERCEIVED,默认等待."""
    teachers = {
        f"user_{i}": "value_X" for i in range(5)
    }
    
    result = resolve_multi_teacher_conflict_v3_2a(
        vocab_sa=mock_vocab(),
        conflicting_teachers=teachers,
    )
    
    # 即使 5 个用户同意,纯 HEARSAY 无 PERCEIVED → 等待
    assert result.status == "awaiting_revalidation"
    assert result.requires_revalidation is True
```

---

## 第 5 章 F5 根治 — context_tag 红线扩到 AST 扫描

### 5.1 Codex 指出

v3.2 `check_no_context_tag_hard_routing` 用 regex 只扫 `if x == "默认"`。但实际 hardcoded routing 形态多:
- `if x == "default":` (英文)
- `dispatch = {"默认": foo, "主动": bar}` (dict route)
- `match style_tag: case "默认": foo` (match-case)
- `texts.get(style_tag, default)` (.get route)

### 5.2 v3.2a 根治:AST 扫描

```python
# scripts/red_line_check_v14.py 扩展 v3.2a

import ast

FORBIDDEN_FIELDS_IN_LOGIC = {
    "context_tag",
    "style_tag",
    "design_note",
}

FORBIDDEN_LITERALS_IN_CHOICE = {
    "默认", "主动", "被动", "长期用户", "新用户",
    "default", "active", "passive", "long_term_user", "new_user",
    "default_quiet", "rare_warmth",  # v3.2 metadata 字串
}


class ContextTagHardRoutingDetector(ast.NodeVisitor):
    """
    v3.2a AST 扫描:禁止 metadata 字段参与逻辑决策.
    
    允许:metadata 字段进入 audit/render 路径(只读,不决策)
    禁止:metadata 字段进入 if/match-case/dict-route/get-with-default 路径
    """
    
    def __init__(self):
        self.violations = []
    
    def visit_Subscript(self, node):
        """检测 dict[forbidden_field] 模式"""
        if isinstance(node.slice, ast.Constant) and node.slice.value in FORBIDDEN_FIELDS_IN_LOGIC:
            self.violations.append(
                f"L{node.lineno}: subscript access to {node.slice.value} - potential routing"
            )
        self.generic_visit(node)
    
    def visit_Attribute(self, node):
        """检测 obj.context_tag 在决策上下文"""
        if node.attr in FORBIDDEN_FIELDS_IN_LOGIC:
            # 检查父节点是否在 if/match 上下文
            self.violations.append(
                f"L{node.lineno}: attribute access to .{node.attr} - check routing"
            )
        self.generic_visit(node)
    
    def visit_Compare(self, node):
        """检测 x == "forbidden_literal" 模式"""
        for comparator in node.comparators:
            if isinstance(comparator, ast.Constant):
                if comparator.value in FORBIDDEN_LITERALS_IN_CHOICE:
                    self.violations.append(
                        f"L{node.lineno}: comparison to {comparator.value} - hardcoded routing"
                    )
        self.generic_visit(node)
    
    def visit_Match(self, node):
        """检测 match-case 路由"""
        for case in node.cases:
            if isinstance(case.pattern, ast.MatchValue):
                if isinstance(case.pattern.value, ast.Constant):
                    if case.pattern.value.value in FORBIDDEN_LITERALS_IN_CHOICE:
                        self.violations.append(
                            f"L{case.pattern.lineno}: match-case on {case.pattern.value.value}"
                        )
        self.generic_visit(node)
    
    def visit_Call(self, node):
        """检测 dict.get("forbidden", default) 模式"""
        if isinstance(node.func, ast.Attribute) and node.func.attr == "get":
            if node.args and isinstance(node.args[0], ast.Constant):
                if node.args[0].value in FORBIDDEN_FIELDS_IN_LOGIC:
                    self.violations.append(
                        f"L{node.lineno}: .get('{node.args[0].value}') - check usage"
                    )
        self.generic_visit(node)


def check_no_metadata_routing_v3_2a():
    """扫描 runtime/cognitive 和 apv3test runtime,禁 metadata 路由."""
    all_violations = []
    
    target_dirs = [
        Path("runtime/cognitive"),
        Path("apv3test/runtime"),
    ]
    
    for target_dir in target_dirs:
        if not target_dir.exists():
            continue
        
        for py_file in target_dir.rglob("*.py"):
            # 白名单:audit/render 路径允许读 metadata
            if any(allowed in str(py_file) for allowed in ["audit", "render", "trace_format"]):
                continue
            
            try:
                tree = ast.parse(py_file.read_text(encoding="utf-8"))
            except SyntaxError:
                continue
            
            detector = ContextTagHardRoutingDetector()
            detector.visit(tree)
            
            for v in detector.violations:
                all_violations.append(f"{py_file}:{v}")
    
    return all_violations
```

### 5.3 yaml 字段策略

```yaml
# v3.2a: metadata 字段策略
# - metadata 只许在以下文件路径中被读取:
#   - runtime/cognitive/curriculum/audit_*.py (审计渲染)
#   - apv3test/web/ (前端展示)
#   - reports/* (报告生成)
# - metadata 绝不许在以下文件路径中被读取:
#   - runtime/cognitive/sdpl/* (SDPL 决策)
#   - runtime/cognitive/attention/* (attention 计算)
#   - runtime/cognitive/composed_vocab/* (vocab 学习)
```

### 5.4 验收

```python
def test_no_metadata_routing_anywhere():
    """全代码扫描:metadata 不参与决策."""
    violations = check_no_metadata_routing_v3_2a()
    assert len(violations) == 0, "\n".join(violations[:10])


def test_metadata_only_in_audit_path():
    """metadata 字段允许在 audit/render 出现."""
    # 这测试是正向 — 验证 audit 路径下读 metadata 不会被红线拒
    audit_file = Path("runtime/cognitive/curriculum/audit_format.py")
    if audit_file.exists():
        tree = ast.parse(audit_file.read_text())
        detector = ContextTagHardRoutingDetector()
        detector.visit(tree)
        # audit 路径不应被扫(已在白名单)
        # 不验证 violations,只验证 import 不报错
```

---

## 第 6 章 F6 根治 — held-out events 只许 PERCEIVED raw

### 6.1 Codex 指出

v3.2 `held_out_pool.sample_probe_events_for_vocab(vocab_sa_id, n)` 用 `sa_id_overlap(e, vocab_sa_id)` 找事件,这意味着 held-out 事件可能含目标 vocab 标签 → **隐性答案**。

### 6.2 v3.2a 根治

```python
class HeldOutEventPool_v3_2a:
    """
    v3.2a: held-out 事件严格只许 PERCEIVED raw normalized sensor SA.
    
    规则:
    1. 事件必须是 sensor adapter 输出的 NormalizedSAEvent
    2. 事件 spawn 的 markers 必须只有 PERCEIVED kind
    3. 事件本身不许含目标 vocab label / proposition / answer
    4. 目标 vocab 关联只存在于 evaluator 外部 metadata,不进 AP state
    """
    
    def __init__(self):
        self.held_out_events: list[NormalizedSAEvent] = []
        # evaluator 外部 metadata,不与 events 一起存
        self._external_evaluator_meta: dict[str, EvaluatorMetadata] = {}
    
    def add_during_curriculum(
        self,
        event: NormalizedSAEvent,
        evaluator_metadata: EvaluatorMetadata,
        k_fold_index: int,
    ):
        """
        v3.2a 严格 add:
        - event 必须经过 validation
        - evaluator_metadata 单独存储,不与 event 关联到 AP state
        """
        # 1. event 必须是 raw normalized sensor SA
        assert event.is_raw_normalized_sensor_event(), \
            f"held-out event must be raw sensor SA, got {event.kind}"
        
        # 2. event 不许含 vocab label / proposition
        assert not event.contains_vocab_label(), \
            f"held-out event must not contain vocab label"
        assert not event.contains_proposition(), \
            f"held-out event must not contain proposition"
        
        # 3. event 只许带 PERCEIVED marker(如果有任何 marker)
        for marker in event.attached_markers:
            assert marker.kind == "PERCEIVED", \
                f"held-out event marker must be PERCEIVED, got {marker.kind}"
        
        # 4. K-fold 抽样
        if k_fold_index % K_FOLD == 0:
            self.held_out_events.append(event)
            # evaluator_metadata 存外部,不进 AP state
            self._external_evaluator_meta[event.event_id] = evaluator_metadata
    
    def sample_probe_events_for_evaluation(self, n: int) -> list[NormalizedSAEvent]:
        """
        v3.2a: sample 时不传 vocab_sa_id,纯随机抽 n 个.
        
        Evaluator 外部用 self._external_evaluator_meta 判定哪些是相关的,
        但 AP state 不知道 vocab 关联.
        """
        # 纯随机抽 n 个
        if len(self.held_out_events) < n:
            return []
        return random.sample(self.held_out_events, n)
    
    def get_evaluator_metadata(self, event_id: str) -> Optional[EvaluatorMetadata]:
        """evaluator 用来判定 ground truth,但这 metadata 不进 AP state."""
        return self._external_evaluator_meta.get(event_id)
```

### 6.3 evaluator 隔离

```python
def evaluate_vocab_via_held_out_v3_2a(vocab_candidate, held_out_pool):
    """
    v3.2a: evaluator 用 held-out 评估,但 metadata 外部.
    
    流程:
    1. 抽 N 个 raw held-out events(不带标签)
    2. 跑系统对每个 event 的响应
    3. 用 evaluator metadata(外部)判定是否符合 ground truth
    4. 计算 effect_size
    """
    probe_events = held_out_pool.sample_probe_events_for_evaluation(n=8)
    
    if not probe_events:
        return DeltaPResult(passes=False, reason="insufficient_held_out")
    
    correct_count = 0
    for event in probe_events:
        # 系统跑 event,产生响应(完全不知道 vocab 关联)
        system_response = run_system_with_event(event)
        
        # evaluator 外部判定(系统不知道)
        meta = held_out_pool.get_evaluator_metadata(event.event_id)
        if meta and meta.matches(system_response):
            correct_count += 1
    
    # effect_size 计算
    effect_size = correct_count / len(probe_events) - baseline_correctness_rate
    return DeltaPResult(
        mean_delta_P=effect_size,
        passes=effect_size > load_constant("curriculum.teaching_protocol.effect_size_hard_min"),
        ...
    )
```

### 6.4 验收

```python
def test_held_out_events_dont_contain_vocab_labels():
    """held-out events 不含目标 vocab label."""
    pool = HeldOutEventPool_v3_2a()
    
    # 尝试 add 含标签的事件
    bad_event = NormalizedSAEvent(
        kind="PERCEIVED",
        content={"vocab_label": "vocab::cat"}  # 含标签
    )
    
    with pytest.raises(AssertionError):
        pool.add_during_curriculum(bad_event, mock_meta, k_fold_index=0)


def test_held_out_sample_does_not_leak_vocab_id():
    """sample 时不通过 vocab_sa_id,纯随机."""
    pool = HeldOutEventPool_v3_2a()
    # 填充 100 个 raw events
    for i in range(100):
        pool.add_during_curriculum(
            mock_raw_event(i),
            mock_meta(target=f"vocab_{i % 10}"),
            k_fold_index=i,
        )
    
    # sample 应纯随机,不知道 vocab_sa_id
    samples = pool.sample_probe_events_for_evaluation(n=8)
    
    # 验证 API 签名不接受 vocab_sa_id
    import inspect
    sig = inspect.signature(pool.sample_probe_events_for_evaluation)
    assert "vocab_sa_id" not in sig.parameters
    assert "vocab_id" not in sig.parameters
```

---

## 第 7 章 v3.2a 实施清单

### 7.1 Phase 13.0 must-fix gates(纳入 must-do)

按 Codex 建议,以下 6 项写进 Phase 13.0 FinalReport 的设计门:

- [ ] **F1**: 全状态扫描红线测试通过 + 5 个源文件修订(chat.py / dialogue_flow.py / web_chat.py / reply_pressure.py / incremental_tick_runtime.py)
- [ ] **F2**: per-install salt + HMAC 实现 + 4 个验收测试通过
- [ ] **F3**: trust gate effect_size 来自 held-out + isolation 测试通过
- [ ] **F4**: 纯 HEARSAY 冲突默认 awaiting_revalidation + MarkerKind.PENDING_PERCEIVED_REVALIDATION 加入 cap
- [ ] **F5**: AST-based 红线扫描 + 4 种 routing 模式检测全部通过
- [ ] **F6**: HeldOutEventPool 严格化 + evaluator metadata 隔离

### 7.2 顺序建议

Codex 建议(我同意):
> Phase 13.0 → Phase 13.1 → 表达范式 13.6
> 数学 13.5b 最晚做(等隐私、substrate、held-out、trust gate 都干净后)

具体推进:

```
M0   Phase 13.0(license + 隐私 + v3.2a 6 项 must-fix gates)— 2-3 天
        ↓ DECISION GATE 1: 6 项 must-fix gates 全过

M1   Phase 13.1 substrate(无内容,只架构)— 1.5 天

M2   Phase 13.6 表达范式 第一批(50 个)— 5-7 天
        ↓ DECISION GATE 2: 人设量化指标 100 turn 抽样 PASS

M3   Phase 13.2/13.3/13.4/13.5 内容浸泡 — 并行 ~10 天

M4   Phase 13.5b 数学(架构真考验)— 4-5 天
        ↓ DECISION GATE 3: APV3 SDPL 路径下 teacher-off ≥ 95%

M5   Phase 13.9 四场景验收 + 中文展示页 — 2 天

最终 alpha:M0+M1+M2+M3+M4+M5 ≈ 28-30 天
```

---

## 第 8 章 v3.2a 给 Codex 的实施指令

1. **四稿配合**:v3 + v3.1 ERRATA + v3.2 Landing Patch + v3.2a Landing Errata,后者覆盖前者
2. **Phase 13.0 第一件事**:6 项 must-fix gates(F1-F6),无一例外
3. **F1 全状态扫描必须用 canary token 验证**:不是只读代码,要实测
4. **F2 install_salt.bin 必须在 .gitignore**:不能 commit
5. **F3 cold-fork 复用 Phase 8.4 实现**,不要新建
6. **F4 MarkerKind.PENDING_PERCEIVED_REVALIDATION 加入 documented kinds**(注意 cap)
7. **F5 AST scan 必须能识别 4 种模式**(if-eq / dict / match / .get)
8. **F6 sample API 不许传 vocab_sa_id**:接口签名层禁
9. **任何对 v3.2 设计的偏离,先停下问 Claude/银子老师**

---

## 第 9 章 v3.2a 总结

Codex 这轮审阅找出:
1. v3.2 隐私只盯一个文件,实际 5 个文件泄露 → **F1**
2. 短 hash 易字典反推,不是匿名化 → **F2**
3. trust gate 公式对了但 effect_size 来源没限定 → **F3**
4. 多教师冲突 v3.2 比 v3.1 更冒险 → **F4**
5. context_tag 红线 regex 太窄 → **F5**
6. held-out 可能含目标标签 → **F6**

每条都是真问题,且**有 3 个是 v3.2 自己造成的新缝隙**:
- F4 sybil 修复换了方案但引入新风险
- F5 红线写出来但太窄
- F6 probe 协议改对了但 metadata 关联仍泄露

v3.2a 把每条都根治:
- F1 全状态 canary 测试 + 5 文件修订
- F2 per-install salt + HMAC + 文档措辞改 pseudonymous
- F3 cold-fork held-out 隔离 + isolation 测试
- F4 默认 awaiting + official+margin 才暂定
- F5 AST 扫描 + 4 种 routing 模式
- F6 严格 raw sensor SA + evaluator metadata 隔离

v3.2 + v3.2a 现在是 Phase 13 的主合同。

---

— 银子老师 / Claude
— 2026-06-18
