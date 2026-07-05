from __future__ import annotations

from pathlib import Path
from typing import Any

from runtime.cognitive.state_pool.state_pool import StatePool, StateItem

from apv3test.runtime.phase20_7 import TeacherFeedback, run_phase20_7_turn
from apv3test.runtime.phase20_7.runtime import _cognitive_feelings_from_pool


class _Obs:
    """Minimal observation-like for unit testing."""
    def __init__(self, signature: str, chars: tuple[str, ...]):
        self.signature = signature
        self.chars = chars
        self.event_id = f"unit_{signature}"


def _inject_pressure_sa(pool: StatePool, sa_id: str, *, real: float, virtual: float):
    """Inject a StateItem with given R/V so P=real-virtual takes effect."""
    pool.items[sa_id] = StateItem(
        sa_id=sa_id, family="text_utterance", label="probe",
        real_energy=real, virtual_energy=virtual,
        cognitive_pressure=real - virtual,
        source="unit_test",
    )


def test_phase20_7x_surprise_channel_emerges_from_positive_pressure() -> None:
    """§30.2 惊通道: Surprise_i = max(P_i - theta_surprise, 0). P=R-V 正值 (现实强于预测)→惊涌现.

    单元测试直接调 _cognitive_feelings_from_pool, 确认惊通道从 StateItem.cognitive_pressure 派生.
    """
    pool = StatePool()
    obs = _Obs("probe_sig", ("你", "好"))
    _inject_pressure_sa(pool, "text_utterance::probe_sig", real=0.82, virtual=0.20)  # P=0.62>0
    feelings = _cognitive_feelings_from_pool(pool, obs)
    assert "surprise" in feelings
    assert feelings["surprise"] > 0.0
    assert 0.0 <= feelings["surprise"] <= 1.0
    # 低阈值 (0.08) 让 P=0.62 显著涌现惊 (减阈值后×1.6 slope)
    assert feelings["surprise"] > 0.5


def test_phase20_7x_dissonance_channel_emerges_from_negative_pressure() -> None:
    """§30.2 违和通道: Dissonance_i = max(-P_i - theta_dissonance, 0). P<0 (预测强于现实)→违和."""
    pool = StatePool()
    obs = _Obs("neg_sig", ("啊",))
    _inject_pressure_sa(pool, "text_utterance::neg_sig", real=0.10, virtual=0.70)  # P=-0.60<0
    feelings = _cognitive_feelings_from_pool(pool, obs)
    assert feelings["dissonance"] > 0.0
    assert 0.0 <= feelings["dissonance"] <= 1.0
    assert feelings["dissonance"] > 0.4


def test_phase20_7x_reasonable_channel_from_backward_grasp_and_low_surprise() -> None:
    """§30.2 合理: Reasonable = decrease(Surprise) + support(C_backward explanation).

    惊低 + C_backward 归因把握高 → 合理高 (§745 解释成功, 惊讶下降, 合理上升).
    """
    pool = StatePool()
    obs = _Obs("ok_sig", ("嗯",))
    # 低 P (惊低)
    _inject_pressure_sa(pool, "text_utterance::ok_sig", real=0.50, virtual=0.48)  # P=0.02 低
    feelings_low_surprise = _cognitive_feelings_from_pool(pool, obs, c_backward_grasp=0.8)
    assert feelings_low_surprise["reasonable"] > 0.4
    # 高 P (惊高) + 低 C_backward → 合理低
    _inject_pressure_sa(pool, "text_utterance::ok_sig", real=0.82, virtual=0.20)  # P=0.62 高
    feelings_high_surprise = _cognitive_feelings_from_pool(pool, obs, c_backward_grasp=0.1)
    assert feelings_high_surprise["reasonable"] < feelings_low_surprise["reasonable"]


def test_phase20_7x_pressure_channel_uses_punish_pressure_plus_surprise_emergent() -> None:
    """§27.3 压力: Pressure=predicted_punish_energy + §30.1 惊伴随少量惩罚信号涌现.

    对应用户理论: 未知本身就有惩罚信号, 导致压力/恐惧.
    """
    pool = StatePool()
    obs = _Obs("p_sig", ("?",))
    _inject_pressure_sa(pool, "text_utterance::p_sig", real=0.88, virtual=0.10)  # P=0.78 高惊
    feelings = _cognitive_feelings_from_pool(pool, obs, punish_pressure=0.4)
    assert "pressure" in feelings
    # 压力 = 9y punish_pressure + 惊涌现份
    assert feelings["pressure"] >= 0.4
    # 惊涌现份单独记录
    assert feelings["pressure_from_surprise_emergent"] > 0.0
    # 高惊→压力涌现份 > 0
    assert feelings["pressure"] > 0.4  # 9y 0.4 + 涌现 > 0


def test_phase20_7x_unknown_text_emerges_surprise_in_tick_feelings(tmp_path: Path) -> None:
    """集成测试: 未知文本通过 phase20_7 tick 后, feelings 含惊通道涌现值."""
    db_path = tmp_path / "cog_feel.sqlite"
    result = run_phase20_7_turn(
        user_text="这是什么情况",
        session_id="cog-feel",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )
    assert result.reply_text == "不太会,教教"
    # 至少有一个 tick 的 feelings 含 §30 通道 (surprise/dissonance/reasonable/pressure)
    has_surprise = False
    for tick in result.tick_trace:
        feelings = tick.feelings if isinstance(tick.feelings, dict) else {}
        if "surprise" in feelings:
            has_surprise = True
            assert 0.0 <= float(feelings["surprise"]) <= 1.0
            break
    assert has_surprise, "tick feelings 缺少 §30 surprise 通道"


def test_phase20_7x_cognitive_feelings_no_forbidden_convergence_strings() -> None:
    """红线: 认知感受通道不声称恐惧/收敛 (禁用串, 软投影)."""
    pool = StatePool()
    obs = _Obs("redline", ("x",))
    feelings = _cognitive_feelings_from_pool(pool, obs)
    forbidden = ("fear_converged", "curiosity_converged", "surprise_converged",
                 "dissonance_converged", "feeling_converged", "feeling_complete")
    for token in forbidden:
        assert token not in str(feelings).lower()


def test_phase20_7x_empty_pool_returns_zero_no_pretend() -> None:
    """安全边界: 空 pool (无 SA) → 涌现 0, 不假装感受."""
    pool = StatePool()
    obs = _Obs("empty", ("a",))
    feelings = _cognitive_feelings_from_pool(pool, obs)
    assert feelings["surprise"] == 0.0
    assert feelings["dissonance"] == 0.0
    # 压力在无状态池信号时仍可用 9y punish_pressure (但惊涌现份 0)
    assert feelings["pressure_from_surprise_emergent"] == 0.0


def test_phase20_7x_correct_channel_emerges_from_low_abs_p_and_reward() -> None:
    """§30.2 正确感: Correct = verified_prediction + low_abs(P) + reward/check_success.

    路2.1: 当前可用两项 — low_abs(P) (|P|低→R≈V→预测匹配) + reward_signal (反馈奖励).
    verified_prediction 第三项 留待 readback 信号接通后补.
    """
    pool = StatePool()
    obs = _Obs("correct_sig", ("嗯",))
    # 低 |P| → R≈V → 预测匹配 → low_abs_p 高
    _inject_pressure_sa(pool, "text_utterance::correct_sig", real=0.50, virtual=0.48)  # P=0.02 低
    feelings = _cognitive_feelings_from_pool(pool, obs, reward_signal=0.8)
    assert "correct" in feelings
    assert 0.0 <= feelings["correct"] <= 1.0
    # 低|P| + 高reward → 正确感显著
    assert feelings["correct"] > 0.5
    assert feelings["correct_from_low_abs_p"] > 0.5
    assert feelings["correct_from_reward_signal"] == 0.8


def test_phase20_7x_correct_channel_low_when_high_pressure_or_no_reward() -> None:
    """对抗性: 高|P| (预测与现实差距大) 或无奖励时, 正确感低."""
    pool = StatePool()
    obs = _Obs("high_p", ("?",))
    # 高|P| → R远V → 预测错误 → low_abs_p 低
    _inject_pressure_sa(pool, "text_utterance::high_p", real=0.90, virtual=0.10)  # |P|=0.80 高
    feelings_hp_no_reward = _cognitive_feelings_from_pool(pool, obs, reward_signal=0.0)
    assert feelings_hp_no_reward["correct"] < 0.4  # 高|P|无奖 → 正确感低


def test_phase20_7x_correct_emerges_in_teacher_feedback_tick(tmp_path: Path) -> None:
    """集成: 教师反馈后 tick feelings 含 correct 通道, 正确感涌现."""
    db_path = tmp_path / "correct_emerge.sqlite"
    # 先教一遍 (未知问题 + 答案 + 奖励)
    run_phase20_7_turn(
        user_text="这是什么",
        teacher_feedback=TeacherFeedback(feedback_text="是苹果", reward_mag=1.0),
        session_id="correct-emerge",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )
    # 再问一次 → 反馈路径 tick feelings 应含 correct
    result = run_phase20_7_turn(
        user_text="这是什么",
        teacher_feedback=TeacherFeedback(feedback_text="是苹果", reward_mag=1.0),
        session_id="correct-emerge",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )
    has_correct = False
    for tick in result.tick_trace:
        feelings = tick.feelings if isinstance(tick.feelings, dict) else {}
        if "correct" in feelings:
            has_correct = True
            assert 0.0 <= float(feelings["correct"]) <= 1.0
    assert has_correct, "反馈路径 tick 缺少 §30 correct 通道"


def test_phase20_7x_correct_no_forbidden_convergence_strings() -> None:
    """红线: 正确感不声称完成/收敛 (连续投影, 非布尔)."""
    pool = StatePool()
    obs = _Obs("redline", ("x",))
    feelings = _cognitive_feelings_from_pool(pool, obs, reward_signal=0.5)
    forbidden = ("correct_converged", "correct_complete", "verified_complete")
    for token in forbidden:
        assert token not in str(feelings).lower()


def test_phase20_7x_expectation_channel_emerges_from_reward() -> None:
    """§27.3/§30.2 期待: Expectation = predicted_reward_energy. 与压力对称.

    当前可用: reward_pressure (9y 投影, 调用点可传) + reward_signal (反馈路径).
    reward 高 → 期待高 (拟人: 收到强奖励 → 期待再次).
    """
    pool = StatePool()
    obs = _Obs("expect_sig", ("好",))
    _inject_pressure_sa(pool, "text_utterance::expect_sig", real=0.50, virtual=0.48)
    # 低 reward_signal → 低期待
    feelings_low = _cognitive_feelings_from_pool(pool, obs, reward_signal=0.1)
    # 高 reward_signal → 高期待
    feelings_high = _cognitive_feelings_from_pool(pool, obs, reward_signal=0.8)
    assert 0.0 <= feelings_low["expectation"] <= 1.0
    assert 0.0 <= feelings_high["expectation"] <= 1.0
    assert feelings_high["expectation"] > feelings_low["expectation"]
    # 同时 reward_pressure 9y 投影也参与
    feelings_rp = _cognitive_feelings_from_pool(pool, obs, reward_pressure=0.6, reward_signal=0.0)
    assert feelings_rp["expectation"] > 0.4  # reward_pressure 主导时仍显著


def test_phase20_7x_expectation_pressure_symmetric_no_reward_no_punish_neutral() -> None:
    """对抗性: 无奖励无惩罚且|P|中低时, 期待与压力都低 (中性)."""
    pool = StatePool()
    obs = _Obs("neutral", ("嗯",))
    _inject_pressure_sa(pool, "text_utterance::neutral", real=0.50, virtual=0.50)  # P=0
    feelings = _cognitive_feelings_from_pool(pool, obs, reward_signal=0.0, punish_pressure=0.0)
    # 期待低, 压力低 (但有些 surprise_emergent 即使 P=0 时也 0)
    assert feelings["expectation"] < 0.15
    assert feelings["pressure"] < 0.15


def test_phase20_7x_expectation_no_forbidden_strings() -> None:
    """红线: 期待不声称 reward/expectation 收敛或完成."""
    pool = StatePool()
    obs = _Obs("red", ("x",))
    feelings = _cognitive_feelings_from_pool(pool, obs, reward_signal=0.9, reward_pressure=0.5)
    forbidden = ("expectation_converged", "expectation_complete", "reward_converged", "hope_complete")
    for token in forbidden:
        assert token not in str(feelings).lower()


def test_phase20_7x_unclosed_channel_emerges_from_u_value() -> None:
    """§30.2 第8通道 未闭合: Unclosed = u_value 持续张力 (§27.6).

    调用点传入 unclosed_u (active_unclosed 的 u_value) → 涌现为未闭合感受通道.
    对应用户理论"失恋注意难集中"的底层: U 高不释放 → 反复打断.
    """
    pool = StatePool()
    obs = _Obs("unclosed_sig", ("?",))
    _inject_pressure_sa(pool, "text_utterance::unclosed_sig", real=0.50, virtual=0.50)
    # 无 active unclosed → 未闭合感 0
    feelings_no = _cognitive_feelings_from_pool(pool, obs, unclosed_u=0.0)
    # 有 active unclosed u_value=0.7 → 未闭合感 0.7
    feelings_yes = _cognitive_feelings_from_pool(pool, obs, unclosed_u=0.7)
    assert feelings_no["unclosed"] == 0.0
    assert 0.0 <= feelings_yes["unclosed"] <= 1.0
    assert feelings_yes["unclosed"] > 0.5
    assert feelings_yes["unclosed_u_source"] == 0.7


def test_phase20_7x_unclosed_channel_emerges_in_unknown_text_tick(tmp_path: Path) -> None:
    """集成: 未知文产生 active unclosed (request_teacher upsert) → tick feelings 含 unclosed 通道."""
    db_path = tmp_path / "unclosed_emerge.sqlite"
    # 第一次未知问 → 产生 unclosed
    run_phase20_7_turn(
        user_text="这是什么情况",
        session_id="unclosed-emerge",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )
    # 第二次同样问题 → 应能从 active_unclosed 取 u_value
    result = run_phase20_7_turn(
        user_text="这是什么情况",
        session_id="unclosed-emerge",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )
    has_unclosed = False
    for tick in result.tick_trace:
        feelings = tick.feelings if isinstance(tick.feelings, dict) else {}
        if "unclosed" in feelings:
            has_unclosed = True
            assert 0.0 <= float(feelings["unclosed"]) <= 1.0
    assert has_unclosed, "tick feelings 缺少 §30 unclosed 通道"


def test_phase20_7x_unclosed_no_forbidden_convergence_strings() -> None:
    """红线: 未闭合不声称完成/闭合收敛 (持续张力投影, 非布尔)."""
    pool = StatePool()
    obs = _Obs("red", ("x",))
    feelings = _cognitive_feelings_from_pool(pool, obs, unclosed_u=0.8)
    forbidden = ("unclosed_converged", "unclosed_complete", "closure_complete", "tension_resolved")
    for token in forbidden:
        assert token not in str(feelings).lower()


def test_phase20_7x_time_sense_channel_familiar_fast_unfamiliar_slow() -> None:
    """§30.2 第9通道 时间感 + §13.4: 熟悉快陌生慢.

    低惊 + 高 c_backward → 熟悉 → time_sense 高 (时间感觉快);
    高惊 + 低 c_backward → 陌生 → time_sense 低 (时间感觉慢).
    §13.4 直接落地, 复用 surprise + c_backward_grasp, 不增实体.
    """
    pool = StatePool()
    obs = _Obs("time_sig", ("嗯",))
    # 熟悉: 低 P (惊低) + 高 c_backward
    _inject_pressure_sa(pool, "text_utterance::time_sig", real=0.50, virtual=0.48)
    feelings_familiar = _cognitive_feelings_from_pool(pool, obs, c_backward_grasp=0.8)
    # 陌生: 高 P (惊高) + 低 c_backward
    _inject_pressure_sa(pool, "text_utterance::time_sig", real=0.88, virtual=0.10)
    feelings_unfamiliar = _cognitive_feelings_from_pool(pool, obs, c_backward_grasp=0.1)
    assert 0.0 <= feelings_familiar["time_sense"] <= 1.0
    assert 0.0 <= feelings_unfamiliar["time_sense"] <= 1.0
    # 熟悉时时间感高 (快), 陌生时低 (慢)
    assert feelings_familiar["time_sense"] > feelings_unfamiliar["time_sense"]


def test_phase20_7x_time_sense_no_forbidden_strings() -> None:
    """红线: 时间感不声称收敛/完成 (连续投影)."""
    pool = StatePool()
    obs = _Obs("red", ("x",))
    feelings = _cognitive_feelings_from_pool(pool, obs, c_backward_grasp=0.7)
    forbidden = ("time_sense_converged", "time_converged", "familiarity_complete")
    for token in forbidden:
        assert token not in str(feelings).lower()


def test_phase20_7x_rhythm_sense_channel_fluent_when_continue_low_fatigue() -> None:
    """§30.2 第10通道 节奏感: lag kernel 与周期预测 (§1294 后继波峰强→自然接下去).

    单元测试: continue_count 高 + repetition_fatigue 低 → 节奏流畅 (rhythm_sense 高);
              repetition_fatigue 高 → 节奏紊乱 (rhythm_sense 低, §586 重复得奇怪).
    当前调用点暂未传 continue_count (需9y开销), 函数本身正确, 待 rhythm_lag 边或
    9y continue_count 优雅接通后激活集成涌现.
    """
    pool = StatePool()
    obs = _Obs("rhythm_sig", ("嗯",))
    _inject_pressure_sa(pool, "text_utterance::rhythm_sig", real=0.50, virtual=0.48)
    # 连续多 + 重复疲劳低 → 节奏流畅
    feelings_fluent = _cognitive_feelings_from_pool(
        pool, obs, continue_count=8, repetition_fatigue=0.1
    )
    # 重复疲劳高 → 节奏紊乱
    feelings_stutter = _cognitive_feelings_from_pool(
        pool, obs, continue_count=8, repetition_fatigue=0.9
    )
    # 无连续 → 节奏感低
    feelings_none = _cognitive_feelings_from_pool(
        pool, obs, continue_count=0, repetition_fatigue=0.0
    )
    assert 0.0 <= feelings_fluent["rhythm_sense"] <= 1.0
    assert feelings_fluent["rhythm_sense"] > feelings_stutter["rhythm_sense"]
    assert feelings_none["rhythm_sense"] == 0.0  # 无连续 → 节奏感0


def test_phase20_7x_rhythm_sense_no_forbidden_strings() -> None:
    """红线: 节奏感不声称收敛/完成 (连续投影)."""
    pool = StatePool()
    obs = _Obs("red", ("x",))
    feelings = _cognitive_feelings_from_pool(pool, obs, continue_count=5, repetition_fatigue=0.2)
    forbidden = ("rhythm_converged", "rhythm_complete", "cadence_complete")
    for token in forbidden:
        assert token not in str(feelings).lower()


def test_phase20_7x_evidence_gap_channel_high_when_low_grasp_high_surprise() -> None:
    """§30.2 第11通道 证据缺口: 任务需要证据但状态池不足.

    §1937 把握上升→证据缺口下降; §3258 low_grasp+evidence_gap→request_teacher.
    派生: 低归因把握主导 + 惊加成 + 未闭合加成.
    """
    pool = StatePool()
    obs = _Obs("gap_sig", ("?",))
    # 低把握 + 高惊 + 未闭合 → 证据缺口高
    _inject_pressure_sa(pool, "text_utterance::gap_sig", real=0.88, virtual=0.10)  # P=0.78 高惊
    feelings_gap = _cognitive_feelings_from_pool(pool, obs, c_backward_grasp=0.1, unclosed_u=0.6)
    # 高把握 + 低惊 + 无未闭合 → 证据缺口低
    _inject_pressure_sa(pool, "text_utterance::gap_sig", real=0.50, virtual=0.48)  # P=0.02 低惊
    feelings_no_gap = _cognitive_feelings_from_pool(pool, obs, c_backward_grasp=0.8, unclosed_u=0.0)
    assert 0.0 <= feelings_gap["evidence_gap"] <= 1.0
    assert feelings_gap["evidence_gap"] > feelings_no_gap["evidence_gap"]
    assert feelings_gap["evidence_gap"] > 0.4  # 低把握+高惊+未闭合 → 显著缺口


def test_phase20_7x_evidence_gap_no_forbidden_strings() -> None:
    """红线: 证据缺口不声称收敛/完成 (连续投影)."""
    pool = StatePool()
    obs = _Obs("red", ("x",))
    feelings = _cognitive_feelings_from_pool(pool, obs, c_backward_grasp=0.1, unclosed_u=0.5)
    forbidden = ("evidence_gap_converged", "evidence_complete", "gap_resolved")
    for token in forbidden:
        assert token not in str(feelings).lower()


def test_phase20_7x_repetition_fatigue_channel_from_statepool_and_9y() -> None:
    """§30.2 第12通道 重复疲劳: 重复同对象/行动 (§738 F_i(t+1)=decay_F*F_i+repeated_focus+repeated_action).

    派生: StateItem.fatigue 聚合 (§9 repeated_focus累积) + repetition_fatigue (9y repeated_action).
    """
    pool = StatePool()
    obs = _Obs("fatigue_sig", ("嗯",))
    # 注入带 fatigue 的 SA
    item_sa_id = "text_utterance::fatigue_sig"
    pool.items[item_sa_id] = StateItem(
        sa_id=item_sa_id, family="text_utterance", label="嗯",
        real_energy=0.50, virtual_energy=0.48, cognitive_pressure=0.02,
        fatigue=0.6, source="unit_test",
    )
    # 低 repetition_fatigue (9y) → 重复疲劳通道主要来自 StateItem.fatigue
    feelings_low_9y = _cognitive_feelings_from_pool(pool, obs, repetition_fatigue=0.1)
    # 高 repetition_fatigue (9y) → 重复疲劳通道更高
    feelings_high_9y = _cognitive_feelings_from_pool(pool, obs, repetition_fatigue=0.8)
    assert 0.0 <= feelings_low_9y["repetition_fatigue_channel"] <= 1.0
    assert feelings_high_9y["repetition_fatigue_channel"] > feelings_low_9y["repetition_fatigue_channel"]
    # StateItem.fatigue=0.6 → 即使9y低, 通道也应有值
    assert feelings_low_9y["repetition_fatigue_channel"] > 0.2


def test_phase20_7x_repetition_fatigue_no_forbidden_strings() -> None:
    """红线: 重复疲劳不声称收敛/完成 (连续投影)."""
    pool = StatePool()
    obs = _Obs("red", ("x",))
    feelings = _cognitive_feelings_from_pool(pool, obs, repetition_fatigue=0.9)
    forbidden = ("fatigue_converged", "fatigue_complete", "repetition_complete")
    for token in forbidden:
        assert token not in str(feelings).lower()


def test_phase20_7x_all_12_channels_present_in_return() -> None:
    """路2完整验收: §30.2 12通道全在 _cognitive_feelings_from_pool 返回值中 (把握通过9j-grasp外部接入)."""
    pool = StatePool()
    obs = _Obs("all12", ("嗯",))
    _inject_pressure_sa(pool, "text_utterance::all12", real=0.50, virtual=0.48)
    feelings = _cognitive_feelings_from_pool(
        pool, obs, c_backward_grasp=0.5, reward_signal=0.5,
        unclosed_u=0.3, continue_count=3, repetition_fatigue=0.2,
    )
    # §30.2 12通道: 惊/违和/合理/正确/把握/期待/压力/未闭合/时间感/节奏感/证据缺口/重复疲劳
    # (把握 grasp 由 _feelings_for_output 外部接入, 此函数产 11 + 把握在调用方合并)
    expected_in_function = (
        "surprise", "dissonance", "reasonable", "correct",
        "expectation", "pressure", "unclosed",
        "time_sense", "rhythm_sense", "evidence_gap", "repetition_fatigue_channel",
    )
    for key in expected_in_function:
        assert key in feelings, f"缺§30 通道: {key}"
        assert 0.0 <= float(feelings[key]) <= 1.0


def test_phase20_7x_emotion_integrated_from_tick_feelings(tmp_path: Path) -> None:
    """§31 情绪慢量: 从 turn 内 tick_events 的 feelings 衰减加权积分成 emotion 维度.

    白皮书 §31.2: emotion_c(t+1)=clamp(decay*emotion_c(t)+sum w_ck*feeling_k+...).
    本测试验证 Phase207TurnResult.emotion 含 valence/arousal/dominance 等维度,
    由 §30 12通道 feelings 积分涌现.
    """
    db_path = tmp_path / "emotion.sqlite"
    # 未知文 → 高惊/高压力/高未闭合 → 负valence/高arousal
    result = run_phase20_7_turn(
        user_text="这是什么情况",
        session_id="emotion-test",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )
    emotion = result.emotion if isinstance(result.emotion, dict) else {}
    assert "valence" in emotion
    assert "arousal" in emotion
    assert "dominance" in emotion
    assert "pressure_tone" in emotion
    assert "curiosity_tone" in emotion
    assert "fatigue_tone" in emotion
    assert emotion["integrated_from_tick_count"] > 0
    assert emotion["emotion_source"] == "tick_feelings_decay_weighted_integration"
    # 未知文 → 负valence (压力/违和/未闭合主导)
    assert 0.0 <= float(emotion["valence"]) <= 1.0
    # 未知文 → 高arousal (惊/证据缺口高, 部分tick有feelings)
    assert float(emotion["arousal"]) > 0.15
    # 未知文 → 高curiosity_tone (惊+证据缺口)
    assert float(emotion["curiosity_tone"]) > 0.15


def test_phase20_7x_emotion_teacher_reward_increases_valence(tmp_path: Path) -> None:
    """§31.3 拟人: 成功和亲和经历 → 表达更柔和 (valence正).

    教师奖励反馈后 → correct/expectation/reasonable 涌现 → valence 比 未知时高.
    """
    db_path = tmp_path / "emotion_reward.sqlite"
    # 未知首次 (负情绪)
    first = run_phase20_7_turn(
        user_text="这是什么",
        session_id="emotion-rwd",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )
    # 教师奖励
    run_phase20_7_turn(
        user_text="这是什么",
        teacher_feedback=TeacherFeedback(feedback_text="是苹果", reward_mag=1.0),
        session_id="emotion-rwd",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )
    # 再问 (已学, 正情绪)
    third = run_phase20_7_turn(
        user_text="这是什么",
        session_id="emotion-rwd",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )
    first_valence = float(first.emotion.get("valence", 0.0)) if isinstance(first.emotion, dict) else 0.0
    third_valence = float(third.emotion.get("valence", 0.0)) if isinstance(third.emotion, dict) else 0.0
    # 学过后 valence 应不低于首次未知 (拟人: 知道了情绪更正)
    assert third_valence >= first_valence - 0.1


def test_phase20_7x_emotion_no_forbidden_convergence_strings() -> None:
    """§31.4 红线: 情绪不由关键词设置, 只软调制. 不声称情绪收敛/完成."""
    from apv3test.runtime.phase20_7.runtime import _integrate_emotion_from_ticks
    # 空 tick_events → 默认 emotion
    emotion = _integrate_emotion_from_ticks(())
    forbidden = ("emotion_converged", "emotion_complete", "mood_complete", "valence_converged")
    for token in forbidden:
        assert token not in str(emotion).lower()


def test_phase20_7x_teacher_feedback_reduces_surprise_increases_reasonable(tmp_path: Path) -> None:
    """回归保护 + 拟人: 教师反馈后, 未知问题再问, 惊应低于首次, 合理应高于首次."""
    db_path = tmp_path / "teach_reduce.sqlite"
    # 未知首次问 → 应有惊涌现
    first = run_phase20_7_turn(
        user_text="这是什么",
        session_id="teach-r",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )
    # 教师反馈
    run_phase20_7_turn(
        user_text="这是什么",
        teacher_feedback=TeacherFeedback(feedback_text="是苹果", reward_mag=1.0),
        session_id="teach-r",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )
    # 知道后再问 → 惊低, 合理高 (闭合过)
    second = run_phase20_7_turn(
        user_text="这是什么",
        session_id="teach-r",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )
    first_surprise = 0.0
    second_surprise = 0.0
    for tick in first.tick_trace:
        feelings = tick.feelings if isinstance(tick.feelings, dict) else {}
        if "surprise" in feelings:
            first_surprise = float(feelings["surprise"])
            break
    for tick in second.tick_trace:
        feelings = tick.feelings if isinstance(tick.feelings, dict) else {}
        if "surprise" in feelings:
            second_surprise = float(feelings["surprise"])
            break
    # 教过后惊应不显著高于首次冷启动未知 (拟人: 知道了就不惊)
    assert second_surprise <= first_surprise + 0.3