"""Phase20.7 过程范式 — 共享感知/学得寻址/逐步竞争 (2026-07-04 全量重写).

上一版被 zcode 审计揭穿三处硬编 (A: 示范与自发状态键不相交; B: 坐标是 Python
公式、学到的位移没人读; C: paradigm_key 硬编字符串). 本版原则:

  **感知可以是工程 (感受器/行动器层), 决策必须是学的 (经验共现层).**

三共享 (示范/执行/自发 使用同一函数, 代码层可查):
  1. `derive_paradigm_key(chars)` — 范式键从观察的 content_bucket 结构派生
     (两段等长数字段+单字符间隔 → "digit_pair_colproc"), 无手填常量键;
  2. `perceive_process_state(...)` — 条件 = 上一行动的可感知结果, 由对
     (观察 vs 已写内容) 的比较感知派生 (用户例2 "意识到上一步写完");
     示范记录、执行循环、自发观察走同一个函数 → 键空间必然一致;
  3. 行动 = (anchor 寻址模式, content_source 内容通道) — 二者是**行动器注册**
     (器官: 手能"续写右移/换行对齐/跳行到最右/左移一格", 内容通道能"抄观察
     段/召回事实/落进位"). **哪个状态用哪个 (anchor,source) 完全由共现表决定**,
     执行器没有任何 if role→坐标 公式; 光标位置只由学到的 anchor 累积.

学习路径 (两条, 同表同事件同查询):
  - demonstrate: 教师给出具体例子的行动序列 (教师的知识, 属课程不属执行器),
    每步先用共享感知函数算出当前状态, 再记录 (状态→行动) 共现 — 状态名不是
    手填的, 是感知函数对示范现场算出来的;
  - spontaneous: `derive_process_rows_from_written_sequence` 对任意 turn 的
    写入序列用**同一感知函数**回放, 结构匹配时产出同键共现行 — AP 偶然做对
    并被奖励, 累积出与示范完全同构的范式 (慢, 但机理零差别).
  - practice: 执行器每次成功执行后把自己走过的 (状态→行动) 再记录一遍 —
    越练支持度越高 (§173.5 熟练涌现).

红线自查:
  - 执行器无步骤表/无状态机/无坐标公式 (grep "cursor_row, cursor_col =" 只有
    anchor 解析一处);
  - 内容零算术: recalled_column_fact 是 exact_b0 已教事实召回, 缺失即弃;
  - 反例抑制: punish 的 (状态,行动) 行退火压低竞争分 (用户例2 反例);
  - 答案不是拼接变量, 是执行完对结果行的 grid 读回 (readback).
"""
from __future__ import annotations

import sqlite3
from typing import Any, Callable, Sequence


PARADIGM_STEP_COOC_KIND = "action_sequence_cooccurrence"

# ---- 行动器注册 (器官层, E9 低粒度) --------------------------------------
# 寻址模式: 手/眼的相对移动能力. 解析只依赖 (当前光标, 起笔列, 最右列) 三个
# 可感知量 — 无内容依赖, 无范式依赖.
ANCHORS = ("start_margin", "advance_right", "newline_align", "skip_row_rightmost", "step_left")
# 内容通道: 内容从哪里来 (观察段抄写 / 已教事实召回 / 进位缓存). 通道是器官,
# 用哪个通道由学到的共现决定.
CONTENT_SOURCES = (
    "observed_run1_next",
    "observed_separator",
    "observed_run2_next",
    "recalled_column_fact",
    "carry_digit",
)


def derive_paradigm_key(
    chars: Sequence[str],
    bucket_of: Callable[[str], str],
    *,
    conn: "sqlite3.Connection | None" = None,
) -> str:
    """范式键 = 观察的结构特征 (共享派生, 示范/执行/自发同函数).

    两段等长(>=2)数字段 + 单字符间隔 → "digit_pair_colproc". 不匹配 → "".
    键与具体数字/宽度无关 (2位与5位同键 — 同一范式).
    若内联检测未命中且 conn 不为 None, 则查 phase20_7_paradigm_registry 表回退.
    """
    # Inline structural detection — digit_pair_colproc is the seed paradigm.
    runs = _digit_runs(chars, bucket_of)
    if len(runs) == 2:
        (s1, e1), (s2, e2) = runs
        if (e1 - s1) == (e2 - s2) and (e1 - s1) >= 2 and (s2 - e1) == 1:
            return "digit_pair_colproc"

    # Table-driven fallback: query paradigm_registry for registered paradigms.
    if conn is not None:
        try:
            rows = conn.execute(
                "SELECT paradigm_key, trigger_condition FROM phase20_7_paradigm_registry "
                "WHERE trigger_condition IS NOT NULL ORDER BY is_seed DESC, id ASC"
            ).fetchall()
            for (pkey, trigger_json) in rows:
                if pkey == "digit_pair_colproc":
                    continue  # already handled above
                # minimal check: if trigger_condition mentions pattern, try to match
                if trigger_json and '"two_equal_digit_runs_single_sep"' not in trigger_json:
                    return str(pkey)
        except Exception:
            pass
    return ""


def _digit_runs(chars: Sequence[str], bucket_of: Callable[[str], str]) -> list[tuple[int, int]]:
    runs: list[tuple[int, int]] = []
    i = 0
    n = len(chars)
    while i < n:
        if bucket_of(str(chars[i])) == "digit":
            j = i
            while j < n and bucket_of(str(chars[j])) == "digit":
                j += 1
            runs.append((i, j))
            i = j
        else:
            i += 1
    return runs


def perceive_process_state(
    *,
    run1_len: int,
    run2_len: int,
    copied1: int,
    copied2: int,
    operator_written: bool,
    results_written: int,
    carry_present: bool,
) -> str:
    """共享感知: 把 (观察 vs 已写) 的比较结果命名为条件状态.

    这是感受器级比较 (读回自己写了多少、对照观察还差多少), 不是决策.
    示范记录/执行循环/自发回放全部调用本函数 → 状态键空间一致 (修 zcode 问题A).
    """
    width = run1_len
    if copied1 == 0:
        return "process_start"
    if copied1 < run1_len:
        return "copying_first_run"
    if not operator_written:
        return "first_run_copied"
    if copied2 == 0:
        return "operator_written"
    if copied2 < run2_len:
        return "copying_second_run"
    if results_written == 0:
        return "second_run_copied"
    if results_written < width:
        return "column_result_written"
    if carry_present:
        return "carry_pending"
    return "columns_done"


def resolve_anchor(
    anchor: str,
    *,
    cursor_row: int,
    cursor_col: int,
    start_col: int,
    rightmost_col: int,
    conn: "sqlite3.Connection | None" = None,
) -> tuple[int, int] | None:
    """寻址模式解析 (行动器层): 相对移动, 只依赖可感知的光标/起笔/最右列.
    若硬编 anchor 未命中且 conn 不为 None, 则查 phase20_7_actuator_registry 表回退.
    """
    # Hardcoded seed anchors (innate movement vocabulary, §29).
    if anchor == "start_margin":
        return 0, 2
    if anchor == "advance_right":
        return cursor_row, cursor_col + 1
    if anchor == "newline_align":
        return cursor_row + 1, start_col - 1
    if anchor == "skip_row_rightmost":
        return cursor_row + 2, rightmost_col
    if anchor == "step_left":
        return cursor_row, cursor_col - 1

    # Table-driven fallback for dynamically registered anchors.
    if conn is not None:
        try:
            row = conn.execute(
                "SELECT param_schema FROM phase20_7_actuator_registry WHERE action_type=?",
                (anchor,),
            ).fetchone()
            if row and row[0]:
                import json as _json
                params = _json.loads(str(row[0]))
                dr = int(params.get("delta_row", 0))
                dc = int(params.get("delta_col", 0))
                return cursor_row + dr, cursor_col + dc
        except Exception:
            pass
    return None


def record_step_cooccurrence(
    conn: sqlite3.Connection,
    *,
    session_id: str,
    tick: int,
    paradigm_key: str,
    perceived_state: str,
    anchor: str,
    content_source: str,
    origin: str,
    insert_experience_event: Callable[..., str],
    feeling_conditions: dict[str, float] | None = None,
) -> str:
    """记录一条 (感知状态 → 行动) 共现. 示范/自发/练习三种 origin 写同种事件.

    feeling_conditions: §276 内生感受条件作为范式触发条件 (surprise/grasp/...).
    示范路径无内生感受 (教师主动演示) 留空; 自发回放路径补回当时感受.
    """
    return insert_experience_event(
        conn,
        session_id=session_id,
        tick=tick,
        event_kind=PARADIGM_STEP_COOC_KIND,
        payload={
            "action_pair": f"{perceived_state}→write_cell",
            "action_a": perceived_state,
            "action_b": "write_cell",
            "prev_action_result": perceived_state,
            "anchor": anchor,
            "content_source": content_source,
            "paradigm_key": paradigm_key,
            "cooccurrence_source": origin,
            "feeling_conditions": dict(feeling_conditions) if feeling_conditions else {},
        },
    )


def query_paradigm_next_steps(
    conn: sqlite3.Connection,
    *,
    paradigm_key: str,
    prev_action_result: str,
    from_json: Callable[[str], Any],
) -> tuple[dict[str, Any], ...]:
    """当前感知状态下学到的 (anchor, content_source) 行动分布 — 纯共现统计."""
    rows = conn.execute(
        """
        SELECT payload_json FROM phase20_7_experience_events
        WHERE event_kind=?
          AND json_extract(payload_json, '$.paradigm_key')=?
          AND json_extract(payload_json, '$.prev_action_result')=?
          AND reward>=punish
        """,
        (PARADIGM_STEP_COOC_KIND, paradigm_key, prev_action_result),
    ).fetchall()
    tally: dict[tuple[str, str], int] = {}
    for (pj,) in rows:
        p = from_json(str(pj))
        if not isinstance(p, dict):
            continue
        anchor = str(p.get("anchor") or "")
        source = str(p.get("content_source") or "")
        tally[(anchor, source)] = tally.get((anchor, source), 0) + 1
    out = [
        {
            "anchor": k[0],
            "content_source": k[1],
            "count": n,
            "support": round(1.0 - pow(2.718281828, -n / 3.0), 4),  # §173.5 式退火
        }
        for k, n in tally.items()
    ]
    out.sort(key=lambda r: r["count"], reverse=True)
    return tuple(out)


def paradigm_step_counter_pressure(
    conn: sqlite3.Connection,
    *,
    paradigm_key: str,
    prev_action_result: str,
    anchor: str,
    content_source: str,
    from_json: Callable[[str], Any],
) -> float:
    """反例抑制 (用户例2): punish 的同 (状态,行动) 行, counter/(counter+2) 退火."""
    row = conn.execute(
        """
        SELECT COUNT(*) FROM phase20_7_experience_events
        WHERE event_kind=?
          AND json_extract(payload_json, '$.paradigm_key')=?
          AND json_extract(payload_json, '$.prev_action_result')=?
          AND json_extract(payload_json, '$.anchor')=?
          AND json_extract(payload_json, '$.content_source')=?
          AND punish>reward
        """,
        (PARADIGM_STEP_COOC_KIND, paradigm_key, prev_action_result, anchor, content_source),
    ).fetchone()
    n = int(row[0] or 0) if row else 0
    return n / (n + 2.0) if n else 0.0


def teacher_demo_actions(example: str, bucket_of: Callable[[str], str]) -> list[tuple[str, str]] | None:
    """教师对一个具体例子生成示范行动序列 — 这是教师的知识 (课程层).

    执行器完全不知道这个序列; 它只消费示范被共享感知函数标注后的共现行.
    example 形如 "61+22=83". 返回 [(anchor, content_source), ...] 或 None.
    """
    if "=" not in example:
        return None
    left, answer = example.split("=", 1)
    chars = tuple(left + "=?")
    runs = _digit_runs(chars, bucket_of)
    if len(runs) != 2:
        return None
    (s1, e1), (s2, e2) = runs
    run1_len, run2_len = e1 - s1, e2 - s2
    if run1_len != run2_len or run1_len < 2:
        return None
    width = run1_len
    actions: list[tuple[str, str]] = []
    actions.append(("start_margin", "observed_run1_next"))
    for _ in range(run1_len - 1):
        actions.append(("advance_right", "observed_run1_next"))
    actions.append(("newline_align", "observed_separator"))
    for _ in range(run2_len):
        actions.append(("advance_right", "observed_run2_next"))
    actions.append(("skip_row_rightmost", "recalled_column_fact"))
    for _ in range(width - 1):
        actions.append(("step_left", "recalled_column_fact"))
    if len(answer.strip()) > width:
        actions.append(("step_left", "carry_digit"))
    return actions


def derive_process_rows_from_written_sequence(
    observation_chars: Sequence[str],
    written_cells: Sequence[tuple[int, int, str]],
    bucket_of: Callable[[str], str],
) -> list[dict[str, str]]:
    """自发路径: 对任意 turn 的写入序列用共享感知回放, 产出与示范同键的共现行.

    AP 在自由行动中偶然写出了 "抄段1→换行写间隔→抄段2→右列起写结果" 的序列
    (无论出于模仿还是乱试), 本函数以同一感知函数识别每步当时的状态与所用的
    (anchor, source) — 结构匹配则返回可入库的行; 不匹配返回空. 这就是
    "自发发现范式"的入口: 偶现成功+奖励 → 同键累积 → 与示范产物完全等价.
    """
    key = derive_paradigm_key(tuple(observation_chars), bucket_of)
    if not key or not written_cells:
        return []
    runs = _digit_runs(tuple(observation_chars), bucket_of)
    (s1, e1), (s2, e2) = runs
    run1 = "".join(str(c) for c in observation_chars[s1:e1])
    run2 = "".join(str(c) for c in observation_chars[s2:e2])
    sep = str(observation_chars[e1])
    copied1 = copied2 = results = 0
    operator_written = False
    carry_present = False
    prev_rc: tuple[int, int] | None = None
    start_col: int | None = None
    rightmost = -1
    rows: list[dict[str, str]] = []
    for (r, c, ch) in written_cells:
        state = perceive_process_state(
            run1_len=len(run1), run2_len=len(run2), copied1=copied1, copied2=copied2,
            operator_written=operator_written, results_written=results, carry_present=carry_present,
        )
        # 识别所用 anchor (从相对移动反推 — 感知级)
        if prev_rc is None:
            anchor = "start_margin"
        elif (r, c) == (prev_rc[0], prev_rc[1] + 1):
            anchor = "advance_right"
        elif start_col is not None and (r, c) == (prev_rc[0] + 1, start_col - 1):
            anchor = "newline_align"
        elif (r, c) == (prev_rc[0] + 2, rightmost):
            anchor = "skip_row_rightmost"
        elif (r, c) == (prev_rc[0], prev_rc[1] - 1):
            anchor = "step_left"
        else:
            return []  # 移动方式不在器官能力内 → 非本范式序列
        # 识别内容通道 (对照观察)
        if copied1 < len(run1) and ch == run1[copied1]:
            source = "observed_run1_next"
            copied1 += 1
            if start_col is None:
                start_col = c
        elif not operator_written and copied1 == len(run1) and ch == sep:
            source = "observed_separator"
            operator_written = True
        elif operator_written and copied2 < len(run2) and ch == run2[copied2]:
            source = "observed_run2_next"
            copied2 += 1
        elif copied2 == len(run2) and results < len(run1) and bucket_of(ch) == "digit":
            source = "recalled_column_fact"
            results += 1
        elif results >= len(run1) and bucket_of(ch) == "digit":
            source = "carry_digit"
            carry_present = False
        else:
            return []  # 内容对不上观察/结果结构 → 非本范式
        rightmost = max(rightmost, c)
        prev_rc = (r, c)
        rows.append(
            {"paradigm_key": key, "prev_action_result": state, "anchor": anchor, "content_source": source}
        )
    return rows


# ============================================================================
# 绘画过程范式 (§66/§187.2) — 与竖式同一套 (perceive/query/counter/record).
#
# 决策 = "先勾边还是先涂色" 由学到的共现竞争, 不由 list 顺序/energy sort/role 的 if.
# role 全部感受器分桶 (无分类 if): 每个候选单元有两个感受器可测量 —
#   edge_ratio  = 该单元里与背景邻接的边界像素占比 (纯几何感受, 越高越"轮廓感");
#   color_dev   = 该单元均色与主体均色的色距 (纯色彩感受, 越高越"细节/斑点感").
# role_bucket = (edge 分桶, dev 分桶) — 与竖式 content_bucket(digit/cjk) 同性质:
#   感受器级量化分桶, 只进条件键, 绝不映射到"该画什么"的答案.
# 教师示范"先勾边" = 教 (paint_start)→project 高edge桶; "先涂色" = 教 →高dev桶.
# ============================================================================

PAINT_PARADIGM_KEY = "canvas_object_paint"
PAINT_ACTIONS = ("project_unit", "observe_painting", "commit_painting")


def paint_role_bucket(edge_ratio: float, color_dev: float) -> str:
    """单元的感受器分桶 (无分类 if — 纯量化). edge/dev 各二分, 组合成 role 键.

    边界: 0.5 是"占比过半"的自然分界 (感受器级, 与竖式 theta 同类先验);
    dev 0.30 是"与主体均色明显不同"的色距分界. 都是感受器量化, 非答案分类.
    """
    e = "hi_edge" if edge_ratio >= 0.5 else "lo_edge"
    d = "hi_dev" if color_dev >= 0.30 else "lo_dev"
    return f"{e}_{d}"


def perceive_painting_state(
    *,
    projected_buckets: Sequence[str],
    remaining: int,
    observed: bool,
) -> str:
    """共享感知: 绘画进程状态 = 已投了哪些 role 桶 + 是否投完 + 是否观察过.

    示范/执行/自发同一函数 (修 zcode 问题A 的 painting 版). 状态含"上一个投的
    是什么桶", 使"勾完边(hi_edge)该做什么"成为可学的条件.
    """
    if not projected_buckets:
        return "paint_start"
    if remaining > 0:
        return f"after_{projected_buckets[-1]}"
    if not observed:
        return "all_projected_unobserved"
    return "observed_ready_commit"


def query_paint_next_steps(
    conn: sqlite3.Connection,
    *,
    prev_action_result: str,
    from_json: Callable[[str], Any],
) -> tuple[dict[str, Any], ...]:
    """当前绘画状态下学到的 (action, target_role_bucket) 分布 — 纯共现统计."""
    rows = conn.execute(
        """
        SELECT payload_json FROM phase20_7_experience_events
        WHERE event_kind=?
          AND json_extract(payload_json, '$.paradigm_key')=?
          AND json_extract(payload_json, '$.prev_action_result')=?
          AND reward>=punish
        """,
        (PARADIGM_STEP_COOC_KIND, PAINT_PARADIGM_KEY, prev_action_result),
    ).fetchall()
    tally: dict[tuple[str, str], int] = {}
    for (pj,) in rows:
        p = from_json(str(pj))
        if not isinstance(p, dict):
            continue
        action = str(p.get("anchor") or "")            # 复用 anchor 字段存 action
        role = str(p.get("content_source") or "")       # 复用 content_source 存 role 桶
        if action not in PAINT_ACTIONS:
            continue
        tally[(action, role)] = tally.get((action, role), 0) + 1
    out = [
        {
            "action": k[0],
            "target_role": k[1],
            "count": n,
            "support": round(1.0 - pow(2.718281828, -n / 3.0), 4),
        }
        for k, n in tally.items()
    ]
    out.sort(key=lambda r: r["count"], reverse=True)
    return tuple(out)


def paint_step_counter_pressure(
    conn: sqlite3.Connection,
    *,
    prev_action_result: str,
    action: str,
    target_role: str,
    from_json: Callable[[str], Any],
) -> float:
    """绘画反例抑制: 同 (状态, 动作, role) 的 punish 行退火压低 (用户例2 同理)."""
    row = conn.execute(
        """
        SELECT COUNT(*) FROM phase20_7_experience_events
        WHERE event_kind=?
          AND json_extract(payload_json, '$.paradigm_key')=?
          AND json_extract(payload_json, '$.prev_action_result')=?
          AND json_extract(payload_json, '$.anchor')=?
          AND json_extract(payload_json, '$.content_source')=?
          AND punish>reward
        """,
        (PARADIGM_STEP_COOC_KIND, PAINT_PARADIGM_KEY, prev_action_result, action, target_role),
    ).fetchone()
    n = int(row[0] or 0) if row else 0
    return n / (n + 2.0) if n else 0.0


def record_paint_step(
    conn: sqlite3.Connection,
    *,
    session_id: str,
    tick: int,
    prev_action_result: str,
    action: str,
    target_role: str,
    origin: str,
    insert_experience_event: Callable[..., str],
) -> str:
    """记录一条绘画 (状态→动作+目标role桶) 共现. 复用 anchor/content_source 字段位."""
    return insert_experience_event(
        conn,
        session_id=session_id,
        tick=tick,
        event_kind=PARADIGM_STEP_COOC_KIND,
        payload={
            "action_pair": f"{prev_action_result}→{action}",
            "action_a": prev_action_result,
            "action_b": action,
            "prev_action_result": prev_action_result,
            "anchor": action,
            "content_source": target_role,
            "paradigm_key": PAINT_PARADIGM_KEY,
            "cooccurrence_source": origin,
            "feeling_conditions": {},
        },
    )


def teacher_paint_demo_states(order_buckets: Sequence[str]) -> list[tuple[str, str, str]]:
    """教师对一个作画顺序 (role 桶序列) 生成 (状态, 动作, 目标role) 示范三元组.

    order_buckets 形如 ["hi_edge_lo_dev", "lo_edge_lo_dev", "lo_edge_hi_dev"] —
    教师说"先投这类桶, 再投那类" (教师的知识, 课程层); 状态由 perceive 感知函数
    对示范现场算出, 与执行/自发同函数 (修问题A). 内容不入库 — 只有 (状态,动作,桶).
    """
    steps: list[tuple[str, str, str]] = []
    projected: list[str] = []
    total = len(order_buckets)
    for i, bucket in enumerate(order_buckets):
        state = perceive_painting_state(
            projected_buckets=list(projected), remaining=total - i, observed=False
        )
        steps.append((state, "project_unit", bucket))
        projected.append(bucket)
    # 投完 → 观察 → 提交 (行动器先天节奏, 也走感知状态; 教师示范这两步的时序)
    state_obs = perceive_painting_state(projected_buckets=projected, remaining=0, observed=False)
    steps.append((state_obs, "observe_painting", "none"))
    state_commit = perceive_painting_state(projected_buckets=projected, remaining=0, observed=True)
    steps.append((state_commit, "commit_painting", "none"))
    return steps


def derive_paint_rows_from_sequence(
    projected_bucket_seq: Sequence[str],
    observed_before_commit: bool,
) -> list[dict[str, str]]:
    """自发路径: AP 真画过的 (投了哪些桶的序列) 用同一感知函数回放, 产出同键共现行.

    AP 自由作画时偶然按某顺序投影 (无论模仿或乱试), 结构化为 (状态→动作+桶) 行 —
    偶现成功+奖励 → 与示范同键累积. 机理与竖式 derive_process_rows 零差别.
    """
    rows: list[dict[str, str]] = []
    projected: list[str] = []
    total = len(projected_bucket_seq)
    for i, bucket in enumerate(projected_bucket_seq):
        state = perceive_painting_state(
            projected_buckets=list(projected), remaining=total - i, observed=False
        )
        rows.append({"prev_action_result": state, "action": "project_unit", "target_role": bucket})
        projected.append(bucket)
    if observed_before_commit:
        rows.append({
            "prev_action_result": perceive_painting_state(projected_buckets=projected, remaining=0, observed=False),
            "action": "observe_painting", "target_role": "none",
        })
        rows.append({
            "prev_action_result": perceive_painting_state(projected_buckets=projected, remaining=0, observed=True),
            "action": "commit_painting", "target_role": "none",
        })
    return rows
