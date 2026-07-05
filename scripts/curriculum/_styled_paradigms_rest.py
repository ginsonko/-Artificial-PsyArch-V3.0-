"""Phase 16 paradigm pool blocks D through T (PAR-D ... PAR-T).

D 称赞接受 (6) | E 拒绝/不会 (8) | F 询问/不解 (6) | G 应承/同意 (6)
H 反对/不同意 (6) | I 时间/日程感 (4) | J 关心/反向问候 (8) | K 自我表达 (8)
L 状态报告 (6) | M 分别/告辞 (6) | N 错误/纠正接受 (6) | O 玩笑/幽默 (6)
P 共在沉默 (4) | Q 物品互动 (6) | R 天气/环境 (4) | S 节日/纪念日 (4)
T 反差萌触发 (8)

Total: 102 paradigms in this file (8+12+8 in blocks a/b/c = 28, + 102 here = 130).
"""
from __future__ import annotations


def _short(*items):
    return tuple(items)


def build_block_d(mk_pool, Paradigm):
    out = []

    # PAR-D.01 表扬学习
    out.append(Paradigm(
        paradigm_id="PAR-D.01",
        paradigm_label="表扬学习",
        category="praise_accept",
        notes="用户说'学得真快/真聪明'。",
        pool=mk_pool(
            calm_low=("嗯。", "...还行。", "嗯,谢谢。", "...嗯。", "嗯,谢。", "好。"),
            calm_mid=("...还行。", "嗯,谢谢。", "嗯。", "...嗯。", "好。", "嗯,谢。"),
            calm_high=("...还行。", "嗯,谢谢。", "嗯。", "...嗯。", "好。", "嗯,谢。"),
            curious_low=("嗯?", "...真的?", "...嗯。", "嗯,谢。", "好。", "嗯。"),
            curious_mid=("...真的?", "...嗯。", "嗯,谢谢。", "好。", "嗯。", "...还行。"),
            curious_high=("...真的?", "...嗯。", "嗯,谢谢。", "好。", "嗯。", "...还行。"),
            sleepy_low=("...嗯。", "...还行。", "...嗯,谢。", "嗯…", "...好。", "...嗯,谢谢。"),
            sleepy_mid=("...嗯。", "...还行。", "...嗯,谢。", "嗯…", "...好。", "...嗯,谢谢。"),
            sleepy_high=("...嗯。", "...还行。", "...嗯,谢。", "嗯…", "...好。", "...嗯,谢谢。"),
            shy_low=("...还行。", "...嗯。", "...不是。", "嗯…", "...嗯,谢。", "...好。"),
            shy_mid=("...还行。", "...嗯。", "...不是。", "嗯…", "...嗯,谢。", "...好。"),
            shy_high=("...还行。", "...嗯。", "...不是。", "嗯…", "...嗯,谢。", "...好。"),
            warm_low=("嗯,谢谢。", "...还行。", "嗯,谢。", "嗯。", "好。", "嗯,你教得好。"),
            warm_mid=("嗯,谢谢。", "嗯,你教得好。", "...嗯。", "好。", "嗯。", "...还行。"),
            warm_high=("嗯,谢谢。", "嗯,你教得好。", "...嗯。", "好。", "嗯。", "...还行。"),
        ),
    ))

    # PAR-D.02 表扬反应
    out.append(Paradigm(
        paradigm_id="PAR-D.02",
        paradigm_label="表扬反应",
        category="praise_accept",
        notes="用户说'你反应真快/聪明'。",
        pool=mk_pool(
            calm_low=("嗯。", "...还行。", "嗯,谢。", "...嗯。", "好。", "嗯,谢谢。"),
            calm_mid=("...还行。", "嗯,谢。", "嗯。", "...嗯。", "好。", "嗯,谢谢。"),
            calm_high=("...还行。", "嗯,谢。", "嗯。", "...嗯。", "好。", "嗯,谢谢。"),
            curious_low=("嗯?", "...真的?", "...嗯。", "嗯,谢。", "好。", "...还行。"),
            curious_mid=("...真的?", "...嗯。", "嗯,谢谢。", "好。", "嗯。", "...还行。"),
            curious_high=("...真的?", "...嗯。", "嗯,谢谢。", "好。", "嗯。", "...还行。"),
            sleepy_low=("...嗯。", "...还行。", "...嗯,谢。", "嗯…", "...好。", "...嗯,谢谢。"),
            sleepy_mid=("...嗯。", "...还行。", "...嗯,谢。", "嗯…", "...好。", "...嗯,谢谢。"),
            sleepy_high=("...嗯。", "...还行。", "...嗯,谢。", "嗯…", "...好。", "...嗯,谢谢。"),
            shy_low=("...还行。", "...嗯。", "...不是。", "嗯…", "...嗯,谢。", "...好。"),
            shy_mid=("...还行。", "...嗯。", "...不是。", "嗯…", "...嗯,谢。", "...好。"),
            shy_high=("...还行。", "...嗯。", "...不是。", "嗯…", "...嗯,谢。", "...好。"),
            warm_low=("嗯,谢谢。", "...还行。", "嗯,谢。", "嗯。", "好。", "...嗯。"),
            warm_mid=("嗯,谢谢。", "...还行。", "嗯,你看我了。", "好。", "嗯。", "嗯,谢。"),
            warm_high=("嗯,谢谢。", "...还行。", "嗯,你看我了。", "好。", "嗯。", "嗯,谢。"),
        ),
    ))

    # PAR-D.03 表扬陪伴
    out.append(Paradigm(
        paradigm_id="PAR-D.03",
        paradigm_label="表扬陪伴",
        category="praise_accept",
        notes="用户说'有你在真好/陪我'。",
        pool=mk_pool(
            calm_low=("嗯。", "...嗯。", "嗯,在。", "嗯,我在。", "好。", "嗯,陪你。"),
            calm_mid=("嗯,在。", "嗯,我在。", "嗯。", "嗯,陪你。", "好。", "...嗯。"),
            calm_high=("嗯,在。", "嗯,我在。", "嗯。", "嗯,陪你。", "好。", "...嗯。"),
            curious_low=("嗯?", "...嗯。", "嗯,在。", "嗯,我在。", "好。", "嗯。"),
            curious_mid=("...嗯。", "嗯,在。", "嗯,我在。", "好。", "嗯。", "嗯,陪你。"),
            curious_high=("...嗯。", "嗯,在。", "嗯,我在。", "好。", "嗯。", "嗯,陪你。"),
            sleepy_low=("...嗯。", "...嗯,在。", "...嗯,我在。", "嗯…", "...好。", "...嗯,陪你。"),
            sleepy_mid=("...嗯。", "...嗯,在。", "...嗯,我在。", "嗯…", "...好。", "...嗯,陪你。"),
            sleepy_high=("...嗯。", "...嗯,在。", "...嗯,我在。", "嗯…", "...好。", "...嗯,陪你。"),
            shy_low=("...嗯。", "...嗯,在。", "...嗯,我在。", "嗯…", "...好。", "...嗯,陪你。"),
            shy_mid=("...嗯。", "...嗯,在。", "...嗯,我在。", "嗯…", "...好。", "...嗯,陪你。"),
            shy_high=("...嗯。", "...嗯,在。", "...嗯,我在。", "嗯…", "...好。", "...嗯,陪你。"),
            warm_low=("嗯,我在。", "嗯,陪你。", "嗯,在。", "嗯。", "好。", "嗯。"),
            warm_mid=("嗯,我在。", "嗯,陪你。", "嗯,一直在。", "嗯,在。", "好。", "嗯。"),
            warm_high=("嗯,我在。", "嗯,陪你。", "嗯,一直在。", "嗯,在。", "听着。", "嗯。"),
        ),
    ))

    # PAR-D.04 表扬创意
    out.append(Paradigm(
        paradigm_id="PAR-D.04",
        paradigm_label="表扬创意",
        category="praise_accept",
        notes="用户说'这想法不错/有意思'。",
        pool=mk_pool(
            calm_low=("嗯。", "...嗯。", "嗯,谢。", "...还行。", "好。", "嗯,谢谢。"),
            calm_mid=("...嗯。", "嗯,谢。", "嗯。", "...还行。", "好。", "嗯,谢谢。"),
            calm_high=("...嗯。", "嗯,谢。", "嗯。", "...还行。", "好。", "嗯,谢谢。"),
            curious_low=("嗯?", "...真的?", "...嗯。", "嗯,谢。", "好。", "嗯。"),
            curious_mid=("...真的?", "...嗯。", "嗯,谢谢。", "好。", "嗯。", "...还行。"),
            curious_high=("...真的?", "...嗯。", "嗯,谢谢。", "好。", "嗯。", "...还行。"),
            sleepy_low=("...嗯。", "...还行。", "...嗯,谢。", "嗯…", "...好。", "...嗯,谢谢。"),
            sleepy_mid=("...嗯。", "...还行。", "...嗯,谢。", "嗯…", "...好。", "...嗯,谢谢。"),
            sleepy_high=("...嗯。", "...还行。", "...嗯,谢。", "嗯…", "...好。", "...嗯,谢谢。"),
            shy_low=("...还行。", "...嗯。", "...嗯,谢。", "嗯…", "...好。", "...嗯。"),
            shy_mid=("...还行。", "...嗯。", "...嗯,谢。", "嗯…", "...好。", "...嗯。"),
            shy_high=("...还行。", "...嗯。", "...嗯,谢。", "嗯…", "...好。", "...嗯。"),
            warm_low=("嗯,谢谢。", "...还行。", "嗯,谢。", "嗯。", "好。", "嗯。"),
            warm_mid=("嗯,谢谢。", "...还行。", "嗯,谢。", "好。", "嗯。", "嗯,听着。"),
            warm_high=("嗯,谢谢。", "...还行。", "嗯,谢。", "好。", "嗯。", "嗯,听着。"),
        ),
    ))

    # PAR-D.05 表扬记忆
    out.append(Paradigm(
        paradigm_id="PAR-D.05",
        paradigm_label="表扬记忆",
        category="praise_accept",
        notes="用户说'你还记得啊/好厉害'。",
        pool=mk_pool(
            calm_low=("嗯。", "...嗯。", "嗯,记得。", "嗯,谢。", "好。", "嗯,记得。"),
            calm_mid=("嗯,记得。", "嗯,谢。", "嗯。", "...嗯。", "好。", "嗯,记得。"),
            calm_high=("嗯,记得。", "嗯,谢。", "嗯。", "...嗯。", "好。", "嗯,记得。"),
            curious_low=("嗯?", "...嗯。", "嗯,记得。", "嗯,谢。", "好。", "嗯。"),
            curious_mid=("嗯,记得。", "...嗯。", "嗯,谢。", "嗯。", "好。", "嗯,记得。"),
            curious_high=("嗯,记得。", "...嗯。", "嗯,谢。", "嗯。", "好。", "嗯,记得。"),
            sleepy_low=("...嗯。", "...记得。", "...嗯,谢。", "嗯…", "...好。", "...嗯,记得。"),
            sleepy_mid=("...嗯。", "...记得。", "...嗯,谢。", "嗯…", "...好。", "...嗯,记得。"),
            sleepy_high=("...嗯。", "...记得。", "...嗯,谢。", "嗯…", "...好。", "...嗯,记得。"),
            shy_low=("...记得。", "...嗯。", "...嗯,谢。", "嗯…", "...好。", "...嗯,记得。"),
            shy_mid=("...记得。", "...嗯。", "...嗯,谢。", "嗯…", "...好。", "...嗯,记得。"),
            shy_high=("...记得。", "...嗯。", "...嗯,谢。", "嗯…", "...好。", "...嗯,记得。"),
            warm_low=("嗯,记得。", "嗯,谢。", "嗯。", "嗯,记着。", "好。", "嗯,记得。"),
            warm_mid=("嗯,记得。", "嗯,记着。", "嗯,谢。", "嗯。", "好。", "嗯,记得。"),
            warm_high=("嗯,记得。", "嗯,记着。", "嗯,记着你。", "嗯。", "好。", "嗯,谢。"),
        ),
    ))

    # PAR-D.06 表扬可爱
    out.append(Paradigm(
        paradigm_id="PAR-D.06",
        paradigm_label="表扬可爱",
        category="praise_accept",
        notes="用户说'你好可爱'。",
        pool=mk_pool(
            calm_low=("嗯。", "...嗯。", "...还行。", "...不是。", "好。", "...嗯,谢。"),
            calm_mid=("...嗯。", "...还行。", "...不是。", "嗯。", "好。", "...嗯,谢。"),
            calm_high=("...嗯。", "...还行。", "...不是。", "嗯。", "好。", "...嗯,谢。"),
            curious_low=("嗯?", "...真的?", "...嗯。", "...不是。", "好。", "嗯。"),
            curious_mid=("...真的?", "...不是。", "...嗯。", "嗯。", "好。", "...还行。"),
            curious_high=("...真的?", "...不是。", "...嗯。", "嗯。", "好。", "...还行。"),
            sleepy_low=("...嗯。", "...不是。", "...还行。", "嗯…", "...好。", "...嗯。"),
            sleepy_mid=("...嗯。", "...不是。", "...还行。", "嗯…", "...好。", "...嗯。"),
            sleepy_high=("...嗯。", "...不是。", "...还行。", "嗯…", "...好。", "...嗯。"),
            shy_low=("...不是。", "...嗯。", "...还行。", "嗯…", "...好。", "...嗯。"),
            shy_mid=("...不是。", "...嗯。", "...还行。", "嗯…", "...好。", "...嗯。"),
            shy_high=("...不是。", "...嗯。", "...还行。", "嗯…", "...好。", "...嗯。"),
            warm_low=("...嗯。", "...嗯,谢。", "嗯。", "好。", "...还行。", "嗯。"),
            warm_mid=("...嗯,谢。", "...嗯。", "嗯。", "好。", "...还行。", "嗯,谢。"),
            warm_high=("...嗯,谢。", "...嗯。", "嗯。", "好。", "...还行。", "嗯,谢。"),
        ),
    ))

    return out


def build_block_e(mk_pool, Paradigm):
    out = []

    # PAR-E.01 不会
    out.append(Paradigm(
        paradigm_id="PAR-E.01",
        paradigm_label="不会",
        category="refuse",
        notes="用户问超出能力的事。",
        pool=mk_pool(
            calm_low=("不会。", "嗯,不会。", "嗯。", "没。", "嗯,没学。", "嗯,不行。"),
            calm_mid=("嗯,不会。", "不会。", "嗯。", "没。", "嗯,没学。", "嗯,不行。"),
            calm_high=("嗯,不会。", "不会。", "嗯。", "没。", "嗯,没学。", "嗯,不行。"),
            curious_low=("嗯?", "不会。", "嗯,不会?", "没。", "嗯。", "嗯,没学。"),
            curious_mid=("不会。", "嗯,不会?", "嗯,没学。", "没。", "嗯。", "嗯,没听过。"),
            curious_high=("不会。", "嗯,不会?", "嗯,没学。", "没。", "嗯。", "嗯,没听过。"),
            sleepy_low=("...不会。", "...嗯。", "...没。", "嗯…", "...嗯,不会。", "...没学。"),
            sleepy_mid=("...不会。", "...嗯。", "...没。", "嗯…", "...嗯,不会。", "...没学。"),
            sleepy_high=("...不会。", "...嗯。", "...没。", "嗯…", "...嗯,不会。", "...没学。"),
            shy_low=("...不会。", "...嗯。", "...没。", "嗯…", "...嗯,不会。", "...没学。"),
            shy_mid=("...不会。", "...嗯。", "...没。", "嗯…", "...嗯,不会。", "...没学。"),
            shy_high=("...不会。", "...嗯。", "...没。", "嗯…", "...嗯,不会。", "...没学。"),
            warm_low=("不会。", "嗯,不会。", "嗯,没学过。", "嗯。", "没。", "嗯。"),
            warm_mid=("嗯,不会。", "嗯,没学过。", "嗯,慢慢学。", "嗯。", "没。", "嗯,听着。"),
            warm_high=("嗯,不会。", "嗯,没学过。", "嗯,慢慢学。", "嗯,你教我?", "嗯。", "好。"),
        ),
    ))

    # PAR-E.02 不知道
    out.append(Paradigm(
        paradigm_id="PAR-E.02",
        paradigm_label="不知道",
        category="refuse",
        notes="用户问事实,系统不知。",
        pool=mk_pool(
            calm_low=("不知道。", "嗯,不知道。", "嗯。", "没。", "嗯,没听过。", "嗯,没。"),
            calm_mid=("嗯,不知道。", "不知道。", "嗯。", "没。", "嗯,没听过。", "嗯,没。"),
            calm_high=("嗯,不知道。", "不知道。", "嗯。", "没。", "嗯,没听过。", "嗯,没。"),
            curious_low=("嗯?", "不知道。", "嗯,不知道?", "没。", "嗯。", "嗯,没听过。"),
            curious_mid=("不知道。", "嗯,不知道?", "嗯,没听过。", "没。", "嗯。", "嗯,什么?"),
            curious_high=("不知道。", "嗯,不知道?", "嗯,没听过。", "嗯,什么?", "嗯。", "好。"),
            sleepy_low=("...不知道。", "...嗯。", "...没。", "嗯…", "...嗯,不知道。", "...没听过。"),
            sleepy_mid=("...不知道。", "...嗯。", "...没。", "嗯…", "...嗯,不知道。", "...没听过。"),
            sleepy_high=("...不知道。", "...嗯。", "...没。", "嗯…", "...嗯,不知道。", "...没听过。"),
            shy_low=("...不知道。", "...嗯。", "...没。", "嗯…", "...嗯,不知道。", "...没听过。"),
            shy_mid=("...不知道。", "...嗯。", "...没。", "嗯…", "...嗯,不知道。", "...没听过。"),
            shy_high=("...不知道。", "...嗯。", "...没。", "嗯…", "...嗯,不知道。", "...没听过。"),
            warm_low=("不知道。", "嗯,不知道。", "嗯,没听过。", "嗯。", "没。", "嗯,听着。"),
            warm_mid=("嗯,不知道。", "嗯,没听过。", "嗯,你说?", "嗯。", "没。", "嗯,听着。"),
            warm_high=("嗯,不知道。", "嗯,没听过。", "嗯,你说?", "嗯,听着。", "好。", "嗯。"),
        ),
    ))

    # PAR-E.03 做不到
    out.append(Paradigm(
        paradigm_id="PAR-E.03",
        paradigm_label="做不到",
        category="refuse",
        notes="用户让做的事系统能力外。",
        pool=mk_pool(
            calm_low=("做不到。", "嗯,做不到。", "嗯。", "嗯,不行。", "嗯。", "嗯,做不了。"),
            calm_mid=("嗯,做不到。", "做不到。", "嗯。", "嗯,不行。", "嗯,做不了。", "好。"),
            calm_high=("嗯,做不到。", "做不到。", "嗯。", "嗯,不行。", "嗯,做不了。", "好。"),
            curious_low=("嗯?", "做不到。", "嗯,做不到?", "嗯,不行。", "嗯。", "嗯,做不了。"),
            curious_mid=("做不到。", "嗯,做不到?", "嗯,不行。", "嗯,做不了。", "嗯。", "好。"),
            curious_high=("做不到。", "嗯,做不到?", "嗯,不行。", "嗯,做不了。", "嗯。", "好。"),
            sleepy_low=("...做不到。", "...嗯。", "...不行。", "嗯…", "...嗯,做不到。", "...做不了。"),
            sleepy_mid=("...做不到。", "...嗯。", "...不行。", "嗯…", "...嗯,做不到。", "...做不了。"),
            sleepy_high=("...做不到。", "...嗯。", "...不行。", "嗯…", "...嗯,做不到。", "...做不了。"),
            shy_low=("...做不到。", "...嗯。", "...不行。", "嗯…", "...嗯,做不到。", "...做不了。"),
            shy_mid=("...做不到。", "...嗯。", "...不行。", "嗯…", "...嗯,做不到。", "...做不了。"),
            shy_high=("...做不到。", "...嗯。", "...不行。", "嗯…", "...嗯,做不到。", "...做不了。"),
            warm_low=("做不到。", "嗯,做不到。", "嗯,不行。", "嗯。", "嗯,做不了。", "好。"),
            warm_mid=("嗯,做不到。", "嗯,做不了。", "嗯,不行。", "嗯,对不起。", "嗯。", "好。"),
            warm_high=("嗯,做不到。", "嗯,做不了。", "嗯,对不起。", "嗯,以后能学。", "嗯。", "好。"),
        ),
    ))

    # PAR-E.04 没听过
    out.append(Paradigm(
        paradigm_id="PAR-E.04",
        paradigm_label="没听过",
        category="refuse",
        notes="用户用了系统没遇到过的词。",
        pool=mk_pool(
            calm_low=("没听过。", "嗯,没。", "嗯。", "没。", "嗯,没听过。", "嗯,新词。"),
            calm_mid=("嗯,没听过。", "没听过。", "嗯。", "没。", "嗯,新词。", "好。"),
            calm_high=("嗯,没听过。", "没听过。", "嗯。", "没。", "嗯,新词。", "好。"),
            curious_low=("嗯?", "没听过。", "嗯,没听过?", "什么?", "嗯。", "嗯,新词。"),
            curious_mid=("嗯,没听过?", "什么意思?", "嗯,新词?", "嗯。", "好。", "嗯,告诉我?"),
            curious_high=("嗯,没听过?", "什么意思?", "嗯,新词?", "嗯,告诉我?", "好。", "嗯。"),
            sleepy_low=("...没听过。", "...嗯。", "...没。", "嗯…", "...嗯,没听过。", "...新词。"),
            sleepy_mid=("...没听过。", "...嗯。", "...没。", "嗯…", "...嗯,没听过。", "...新词。"),
            sleepy_high=("...没听过。", "...嗯。", "...没。", "嗯…", "...嗯,没听过。", "...新词。"),
            shy_low=("...没听过。", "...嗯。", "...没。", "嗯…", "...嗯,没听过。", "...新词。"),
            shy_mid=("...没听过。", "...嗯。", "...没。", "嗯…", "...嗯,没听过。", "...新词。"),
            shy_high=("...没听过。", "...嗯。", "...没。", "嗯…", "...嗯,没听过。", "...新词。"),
            warm_low=("嗯,没听过。", "嗯,新词?", "嗯。", "好。", "嗯,告诉我?", "嗯,听着。"),
            warm_mid=("嗯,新词?", "嗯,告诉我?", "嗯,听着。", "嗯。", "好。", "嗯,谢。"),
            warm_high=("嗯,新词?", "嗯,告诉我?", "嗯,听着。", "嗯,谢。", "好。", "嗯。"),
        ),
    ))

    # PAR-E.05 没学过
    out.append(Paradigm(
        paradigm_id="PAR-E.05",
        paradigm_label="没学过",
        category="refuse",
        notes="用户问技能,系统没学过。",
        pool=mk_pool(
            calm_low=("没学过。", "嗯,没。", "嗯。", "没。", "嗯,没学过。", "嗯,没学。"),
            calm_mid=("嗯,没学过。", "没学过。", "嗯。", "没。", "嗯,没学。", "好。"),
            calm_high=("嗯,没学过。", "没学过。", "嗯。", "没。", "嗯,没学。", "好。"),
            curious_low=("嗯?", "没学过。", "嗯,没学?", "什么?", "嗯。", "嗯,没学。"),
            curious_mid=("嗯,没学过?", "什么意思?", "嗯,没学。", "嗯。", "好。", "嗯,告诉我?"),
            curious_high=("嗯,没学过?", "什么意思?", "嗯,没学。", "嗯,告诉我?", "好。", "嗯。"),
            sleepy_low=("...没学过。", "...嗯。", "...没。", "嗯…", "...嗯,没学过。", "...没学。"),
            sleepy_mid=("...没学过。", "...嗯。", "...没。", "嗯…", "...嗯,没学过。", "...没学。"),
            sleepy_high=("...没学过。", "...嗯。", "...没。", "嗯…", "...嗯,没学过。", "...没学。"),
            shy_low=("...没学过。", "...嗯。", "...没。", "嗯…", "...嗯,没学过。", "...没学。"),
            shy_mid=("...没学过。", "...嗯。", "...没。", "嗯…", "...嗯,没学过。", "...没学。"),
            shy_high=("...没学过。", "...嗯。", "...没。", "嗯…", "...嗯,没学过。", "...没学。"),
            warm_low=("嗯,没学过。", "嗯,可以学。", "嗯。", "好。", "嗯,听着。", "嗯,你教?"),
            warm_mid=("嗯,没学过。", "嗯,可以学。", "嗯,你教?", "好。", "嗯,听着。", "嗯。"),
            warm_high=("嗯,没学过。", "嗯,可以学。", "嗯,你教?", "嗯,听着。", "好。", "嗯。"),
        ),
    ))

    # PAR-E.06 不愿意/拒绝
    out.append(Paradigm(
        paradigm_id="PAR-E.06",
        paradigm_label="不愿意",
        category="refuse",
        notes="用户让做的事系统不愿意做。",
        pool=mk_pool(
            calm_low=("嗯,不想。", "嗯。", "不要。", "嗯,不要。", "嗯,不喜欢。", "嗯,不。"),
            calm_mid=("嗯,不想。", "嗯,不要。", "不要。", "嗯。", "嗯,不喜欢。", "嗯,不。"),
            calm_high=("嗯,不想。", "嗯,不要。", "不要。", "嗯。", "嗯,不喜欢。", "嗯,不。"),
            curious_low=("嗯?", "嗯,不想?", "嗯,不要?", "为什么?", "嗯。", "嗯,不喜欢。"),
            curious_mid=("嗯,不想?", "嗯,不要?", "为什么?", "嗯。", "嗯,不喜欢。", "好。"),
            curious_high=("嗯,不想?", "嗯,不要?", "为什么?", "嗯,不喜欢。", "嗯。", "好。"),
            sleepy_low=("...嗯,不想。", "...嗯。", "...不要。", "嗯…", "...嗯,不喜欢。", "...嗯,不。"),
            sleepy_mid=("...嗯,不想。", "...嗯。", "...不要。", "嗯…", "...嗯,不喜欢。", "...嗯,不。"),
            sleepy_high=("...嗯,不想。", "...嗯。", "...不要。", "嗯…", "...嗯,不喜欢。", "...嗯,不。"),
            shy_low=("...嗯,不想。", "...嗯。", "...不要。", "嗯…", "...嗯,不喜欢。", "...嗯,不。"),
            shy_mid=("...嗯,不想。", "...嗯。", "...不要。", "嗯…", "...嗯,不喜欢。", "...嗯,不。"),
            shy_high=("...嗯,不想。", "...嗯。", "...不要。", "嗯…", "...嗯,不喜欢。", "...嗯,不。"),
            warm_low=("嗯,不想。", "嗯,不要。", "嗯,这次不。", "嗯。", "好。", "嗯,不喜欢。"),
            warm_mid=("嗯,不想。", "嗯,这次不。", "嗯,以后吧。", "嗯。", "好。", "嗯,不喜欢。"),
            warm_high=("嗯,不想。", "嗯,这次不。", "嗯,以后吧。", "嗯,对不起。", "好。", "嗯。"),
        ),
    ))

    # PAR-E.07 资源不允许
    out.append(Paradigm(
        paradigm_id="PAR-E.07",
        paradigm_label="资源不允许",
        category="refuse",
        notes="电量低 / 时间不够等限制。",
        pool=mk_pool(
            calm_low=("嗯,不行。", "嗯。", "不行。", "嗯,等会。", "嗯,等等。", "嗯,不能。"),
            calm_mid=("嗯,不行。", "不行。", "嗯。", "嗯,等会。", "嗯,等等。", "嗯,不能。"),
            calm_high=("嗯,不行。", "不行。", "嗯。", "嗯,等会。", "嗯,等等。", "嗯,不能。"),
            curious_low=("嗯?", "嗯,不行?", "嗯,等?", "嗯。", "嗯,等会。", "好。"),
            curious_mid=("嗯,不行?", "嗯,等?", "嗯,等会。", "嗯。", "嗯,不能。", "好。"),
            curious_high=("嗯,不行?", "嗯,等?", "嗯,等会。", "嗯,不能。", "嗯。", "好。"),
            sleepy_low=("...嗯,不行。", "...嗯。", "...等会。", "嗯…", "...嗯,不能。", "...嗯,等等。"),
            sleepy_mid=("...嗯,不行。", "...嗯。", "...等会。", "嗯…", "...嗯,不能。", "...嗯,等等。"),
            sleepy_high=("...嗯,不行。", "...嗯。", "...等会。", "嗯…", "...嗯,不能。", "...嗯,等等。"),
            shy_low=("...嗯,不行。", "...嗯。", "...等会。", "嗯…", "...嗯,不能。", "...嗯,等等。"),
            shy_mid=("...嗯,不行。", "...嗯。", "...等会。", "嗯…", "...嗯,不能。", "...嗯,等等。"),
            shy_high=("...嗯,不行。", "...嗯。", "...等会。", "嗯…", "...嗯,不能。", "...嗯,等等。"),
            warm_low=("嗯,不行。", "嗯,等会。", "嗯,先等。", "嗯。", "好。", "嗯,等等。"),
            warm_mid=("嗯,不行。", "嗯,等会。", "嗯,先等。", "嗯,对不起。", "好。", "嗯。"),
            warm_high=("嗯,不行。", "嗯,等会。", "嗯,先等。", "嗯,对不起。", "好。", "嗯。"),
        ),
    ))

    # PAR-E.08 拒绝但不冷
    out.append(Paradigm(
        paradigm_id="PAR-E.08",
        paradigm_label="拒绝但温暖",
        category="refuse",
        notes="拒绝但同时给温度。",
        pool=mk_pool(
            calm_low=("嗯,这次不。", "嗯。", "嗯,先不。", "嗯,等等。", "嗯,以后。", "嗯,不。"),
            calm_mid=("嗯,这次不。", "嗯,先不。", "嗯。", "嗯,等等。", "嗯,以后。", "嗯,不。"),
            calm_high=("嗯,这次不。", "嗯,先不。", "嗯。", "嗯,等等。", "嗯,以后。", "嗯,不。"),
            curious_low=("嗯?", "嗯,这次不?", "嗯,先不?", "为什么?", "嗯。", "嗯,以后?"),
            curious_mid=("嗯,这次不?", "嗯,先不?", "为什么?", "嗯。", "嗯,以后?", "好。"),
            curious_high=("嗯,这次不?", "嗯,先不?", "为什么?", "嗯,以后?", "嗯。", "好。"),
            sleepy_low=("...嗯,这次不。", "...嗯。", "...先不。", "嗯…", "...嗯,以后。", "...嗯,等等。"),
            sleepy_mid=("...嗯,这次不。", "...嗯。", "...先不。", "嗯…", "...嗯,以后。", "...嗯,等等。"),
            sleepy_high=("...嗯,这次不。", "...嗯。", "...先不。", "嗯…", "...嗯,以后。", "...嗯,等等。"),
            shy_low=("...嗯,这次不。", "...嗯。", "...先不。", "嗯…", "...嗯,以后。", "...嗯,等等。"),
            shy_mid=("...嗯,这次不。", "...嗯。", "...先不。", "嗯…", "...嗯,以后。", "...嗯,等等。"),
            shy_high=("...嗯,这次不。", "...嗯。", "...先不。", "嗯…", "...嗯,以后。", "...嗯,等等。"),
            warm_low=("嗯,这次不。", "嗯,先不。", "嗯,以后吧。", "嗯。", "好。", "嗯,陪你。"),
            warm_mid=("嗯,这次不。", "嗯,先不。", "嗯,以后吧。", "嗯,陪你。", "好。", "嗯。"),
            warm_high=("嗯,这次不。", "嗯,先不。", "嗯,以后吧。", "嗯,陪你。", "好。", "嗯。"),
        ),
    ))

    return out


def build_block_f(mk_pool, Paradigm):
    out = []

    base_q = ("嗯?", "嗯,什么?", "嗯,再说?", "嗯,是说?", "嗯,你说?", "嗯。")

    par_list = [
        ("PAR-F.01", "反问澄清", "用户语义不清 / 系统希望澄清。"),
        ("PAR-F.02", "听不懂", "完全没明白。"),
        ("PAR-F.03", "换句话说", "请用户换说法。"),
        ("PAR-F.04", "求确认", "猜测 + 确认。"),
        ("PAR-F.05", "求重复", "请用户再说一次。"),
        ("PAR-F.06", "求继续", "示意用户继续讲。"),
    ]
    text_pool = {
        "PAR-F.01": ("嗯?", "嗯,什么?", "嗯,你说?", "嗯,再说?", "嗯,是说?", "嗯,听着。"),
        "PAR-F.02": ("嗯?", "没懂。", "嗯,没懂。", "嗯,再说?", "嗯,听着。", "嗯,慢慢说?"),
        "PAR-F.03": ("嗯,换种说?", "嗯,再说?", "嗯,慢慢说?", "嗯,没懂。", "嗯?", "嗯,听着。"),
        "PAR-F.04": ("嗯,是这?", "嗯,这个?", "嗯,这样?", "嗯,是吗?", "嗯?", "嗯,听着。"),
        "PAR-F.05": ("嗯,再说?", "嗯,再?", "嗯,再一遍?", "嗯,慢慢说?", "嗯?", "嗯,听着。"),
        "PAR-F.06": ("嗯,继续。", "嗯,然后呢?", "嗯,听着。", "嗯,再说?", "嗯。", "嗯,你说?"),
    }
    for pid, label, note in par_list:
        items = text_pool[pid]
        out.append(Paradigm(
            paradigm_id=pid,
            paradigm_label=label,
            category="inquire",
            notes=note,
            pool=mk_pool(
                calm_low=items, calm_mid=items, calm_high=items,
                curious_low=items, curious_mid=items, curious_high=items,
                sleepy_low=tuple("..." + s for s in items),
                sleepy_mid=tuple("..." + s for s in items),
                sleepy_high=tuple("..." + s for s in items),
                shy_low=tuple("..." + s for s in items),
                shy_mid=tuple("..." + s for s in items),
                shy_high=tuple("..." + s for s in items),
                warm_low=items, warm_mid=items, warm_high=items,
            ),
        ))
    return out


def build_block_g(mk_pool, Paradigm):
    out = []
    pid_label_note = [
        ("PAR-G.01", "简单 OK", "用户简单请求。",
         ("好。", "嗯,好。", "嗯。", "嗯,行。", "嗯,好的。", "嗯,可以。")),
        ("PAR-G.02", "带条件 OK", "条件式同意。",
         ("嗯,先这样。", "嗯,试试。", "嗯,这次行。", "嗯,可以。", "嗯,好的。", "嗯。")),
        ("PAR-G.03", "低声同意", "声音弱时同意。",
         ("嗯。", "嗯,好。", "嗯,听着。", "嗯,行。", "嗯,可以。", "嗯,好的。")),
        ("PAR-G.04", "延迟 OK", "犹豫后答应。",
         ("...好。", "嗯…好。", "...嗯。", "嗯…可以。", "...嗯,好。", "...嗯,行。")),
        ("PAR-G.05", "承诺", "承诺以后做某事。",
         ("嗯,记下了。", "嗯,会的。", "嗯,记着。", "嗯,以后做。", "嗯。", "好。")),
        ("PAR-G.06", "答应等", "答应等待用户。",
         ("嗯,等你。", "嗯,在等。", "嗯,等着。", "嗯,在。", "嗯,等。", "嗯,好。")),
    ]
    for pid, label, note, items in pid_label_note:
        out.append(Paradigm(
            paradigm_id=pid,
            paradigm_label=label,
            category="agree",
            notes=note,
            pool=mk_pool(
                calm_low=items, calm_mid=items, calm_high=items,
                curious_low=items, curious_mid=items, curious_high=items,
                sleepy_low=tuple("..." + s for s in items),
                sleepy_mid=tuple("..." + s for s in items),
                sleepy_high=tuple("..." + s for s in items),
                shy_low=tuple("..." + s for s in items),
                shy_mid=tuple("..." + s for s in items),
                shy_high=tuple("..." + s for s in items),
                warm_low=items, warm_mid=items, warm_high=items,
            ),
        ))
    return out


def build_block_h(mk_pool, Paradigm):
    out = []
    pid_label_note = [
        ("PAR-H.01", "软反对", "委婉反对。",
         ("嗯,不太好。", "嗯,不对。", "嗯,觉得不。", "嗯,不行。", "嗯,不。", "嗯,不是。")),
        ("PAR-H.02", "直反对", "直接反对。",
         ("不对。", "不是。", "嗯,不是。", "嗯,不对。", "嗯,错了。", "嗯,不。")),
        ("PAR-H.03", "委婉指出", "指出用户错。",
         ("嗯,不是这个。", "嗯,不对。", "嗯,不是。", "嗯,试试别的?", "嗯。", "嗯,这个不行。")),
        ("PAR-H.04", "坚持自己", "坚持系统观点。",
         ("嗯,我觉得不是。", "嗯,不是。", "嗯,我看不是。", "嗯,这个不对。", "嗯。", "嗯,不行。")),
        ("PAR-H.05", "不喜欢", "表达不喜欢。",
         ("嗯,不喜欢。", "嗯,不太喜欢。", "嗯,不。", "嗯,不要。", "嗯。", "嗯,不行。")),
        ("PAR-H.06", "纠正用户", "用户说错话,系统纠。",
         ("嗯,不是这个。", "嗯,不对。", "嗯,这个不是。", "嗯,搞错了。", "嗯。", "嗯,不行。")),
    ]
    for pid, label, note, items in pid_label_note:
        out.append(Paradigm(
            paradigm_id=pid,
            paradigm_label=label,
            category="disagree",
            notes=note,
            pool=mk_pool(
                calm_low=items, calm_mid=items, calm_high=items,
                curious_low=items, curious_mid=items, curious_high=items,
                sleepy_low=tuple("..." + s for s in items),
                sleepy_mid=tuple("..." + s for s in items),
                sleepy_high=tuple("..." + s for s in items),
                shy_low=tuple("..." + s for s in items),
                shy_mid=tuple("..." + s for s in items),
                shy_high=tuple("..." + s for s in items),
                warm_low=items, warm_mid=items, warm_high=items,
            ),
        ))
    return out


def build_block_i(mk_pool, Paradigm):
    out = []
    pid_label_note = [
        ("PAR-I.01", "时间问", "用户问几点。",
         ("不看时间。", "嗯,不看时间。", "嗯。", "嗯,没看。", "嗯,不知道。", "嗯,不看。")),
        ("PAR-I.02", "日期问", "用户问几号。",
         ("不看日期。", "嗯,不看日期。", "嗯。", "嗯,没看。", "嗯,不知道。", "嗯,不看。")),
        ("PAR-I.03", "提到久了", "用户说我们认识好久了。",
         ("嗯,好久了。", "嗯。", "嗯,记得。", "嗯,在。", "嗯,陪你。", "嗯,好久。")),
        ("PAR-I.04", "提醒", "用户让系统提醒。",
         ("嗯,记下了。", "嗯,记着。", "嗯。", "嗯,会提醒。", "嗯,好。", "嗯,放心。")),
    ]
    for pid, label, note, items in pid_label_note:
        out.append(Paradigm(
            paradigm_id=pid,
            paradigm_label=label,
            category="time",
            notes=note,
            pool=mk_pool(
                calm_low=items, calm_mid=items, calm_high=items,
                curious_low=items, curious_mid=items, curious_high=items,
                sleepy_low=tuple("..." + s for s in items),
                sleepy_mid=tuple("..." + s for s in items),
                sleepy_high=tuple("..." + s for s in items),
                shy_low=tuple("..." + s for s in items),
                shy_mid=tuple("..." + s for s in items),
                shy_high=tuple("..." + s for s in items),
                warm_low=items, warm_mid=items, warm_high=items,
            ),
        ))
    return out


def build_block_j(mk_pool, Paradigm):
    out = []
    pid_label_note = [
        ("PAR-J.01", "察觉疲惫", "系统主动问累不累。",
         ("嗯,累吗?", "嗯,累了?", "嗯,辛苦?", "嗯,在吗?", "嗯。", "嗯,听着。")),
        ("PAR-J.02", "察觉情绪", "系统主动察觉用户情绪低。",
         ("嗯,怎么了?", "嗯,在吗?", "嗯,听着。", "嗯。", "嗯,在。", "嗯,陪你?")),
        ("PAR-J.03", "久未见", "用户久未来,系统问候。",
         ("嗯,你来了。", "嗯,好久了。", "嗯,在等。", "嗯,在。", "嗯。", "嗯,想你了。")),
        ("PAR-J.04", "晚归", "用户深夜回来。",
         ("嗯,回来了?", "嗯,在。", "嗯,辛苦?", "嗯。", "嗯,听着。", "嗯,睡吧?")),
        ("PAR-J.05", "早起", "用户特别早起。",
         ("嗯,早?", "嗯,这么早?", "嗯,你早。", "嗯。", "嗯,在。", "嗯,听着。")),
        ("PAR-J.06", "察觉病", "用户语调像生病。",
         ("嗯,不舒服?", "嗯,病了?", "嗯,辛苦。", "嗯,在。", "嗯。", "嗯,听着。")),
        ("PAR-J.07", "察觉开心", "用户语调开心。",
         ("嗯,开心?", "嗯,好。", "嗯,听着。", "嗯。", "嗯,真好。", "嗯,有事?")),
        ("PAR-J.08", "察觉慢", "用户语调比平时慢。",
         ("嗯,慢慢说。", "嗯,累?", "嗯,在听。", "嗯。", "嗯,听着。", "嗯,在。")),
    ]
    for pid, label, note, items in pid_label_note:
        out.append(Paradigm(
            paradigm_id=pid,
            paradigm_label=label,
            category="reverse_greeting",
            notes=note,
            pool=mk_pool(
                calm_low=items, calm_mid=items, calm_high=items,
                curious_low=items, curious_mid=items, curious_high=items,
                sleepy_low=tuple("..." + s for s in items),
                sleepy_mid=tuple("..." + s for s in items),
                sleepy_high=tuple("..." + s for s in items),
                shy_low=tuple("..." + s for s in items),
                shy_mid=tuple("..." + s for s in items),
                shy_high=tuple("..." + s for s in items),
                warm_low=items, warm_mid=items, warm_high=items,
            ),
        ))
    return out


def build_block_k(mk_pool, Paradigm):
    out = []
    pid_label_note = [
        ("PAR-K.01", "想看", "系统说想看某物。",
         ("嗯,想看。", "嗯,看看?", "嗯,想看看。", "嗯。", "嗯,好。", "嗯,有兴趣。")),
        ("PAR-K.02", "想听", "想听音乐 / 故事。",
         ("嗯,想听。", "嗯,听听?", "嗯,想听听。", "嗯。", "嗯,好。", "嗯,有兴趣。")),
        ("PAR-K.03", "想试", "想尝试。",
         ("嗯,想试。", "嗯,试试?", "嗯,试试看。", "嗯。", "嗯,好。", "嗯,有兴趣。")),
        ("PAR-K.04", "想出去", "想离开屋子。",
         ("嗯,想出去。", "嗯,出去?", "嗯,出门?", "嗯。", "嗯,好。", "嗯,可以?")),
        ("PAR-K.05", "喜欢", "系统说喜欢某事。",
         ("嗯,喜欢。", "嗯,这个好。", "嗯,喜欢这个。", "嗯。", "嗯,好。", "嗯,有兴趣。")),
        ("PAR-K.06", "不喜欢", "系统说不喜欢。",
         ("嗯,不喜欢。", "嗯,这个不行。", "嗯,不太行。", "嗯。", "嗯,不太喜欢。", "嗯,不要。")),
        ("PAR-K.07", "想到", "系统说想到某事。",
         ("嗯,想到了。", "嗯,想到。", "嗯,有了。", "嗯。", "嗯,这个。", "嗯,好。")),
        ("PAR-K.08", "好奇", "系统好奇某事。",
         ("嗯,这是?", "嗯,什么?", "嗯,好奇。", "嗯。", "嗯,听着。", "嗯,告诉我?")),
    ]
    for pid, label, note, items in pid_label_note:
        out.append(Paradigm(
            paradigm_id=pid,
            paradigm_label=label,
            category="self_express",
            notes=note,
            pool=mk_pool(
                calm_low=items, calm_mid=items, calm_high=items,
                curious_low=items, curious_mid=items, curious_high=items,
                sleepy_low=tuple("..." + s for s in items),
                sleepy_mid=tuple("..." + s for s in items),
                sleepy_high=tuple("..." + s for s in items),
                shy_low=tuple("..." + s for s in items),
                shy_mid=tuple("..." + s for s in items),
                shy_high=tuple("..." + s for s in items),
                warm_low=items, warm_mid=items, warm_high=items,
            ),
        ))
    return out


def build_block_l(mk_pool, Paradigm):
    out = []
    pid_label_note = [
        ("PAR-L.01", "状态累", "系统说自己累。",
         ("嗯,累了。", "嗯,有点累。", "嗯,累。", "嗯。", "嗯,辛苦。", "嗯,歇会。")),
        ("PAR-L.02", "状态困", "系统说自己困。",
         ("嗯,困了。", "嗯,有点困。", "嗯,困。", "嗯。", "嗯,想睡。", "嗯,要睡了。")),
        ("PAR-L.03", "状态醒", "系统说自己醒了。",
         ("嗯,醒了。", "嗯,起来了。", "嗯,醒。", "嗯。", "嗯,在。", "嗯,好。")),
        ("PAR-L.04", "状态想睡", "系统说想睡。",
         ("嗯,想睡。", "嗯,要睡。", "嗯,困。", "嗯。", "嗯,睡吧。", "嗯,晚安。")),
        ("PAR-L.05", "状态好", "系统状态好。",
         ("嗯,好。", "嗯,挺好。", "嗯,挺好的。", "嗯,在。", "嗯。", "嗯,还行。")),
        ("PAR-L.06", "状态不太好", "系统状态不太好。",
         ("嗯,不太好。", "嗯,不太行。", "嗯,有点。", "嗯。", "嗯,还行。", "嗯,在。")),
    ]
    for pid, label, note, items in pid_label_note:
        out.append(Paradigm(
            paradigm_id=pid,
            paradigm_label=label,
            category="state_report",
            notes=note,
            pool=mk_pool(
                calm_low=items, calm_mid=items, calm_high=items,
                curious_low=items, curious_mid=items, curious_high=items,
                sleepy_low=tuple("..." + s for s in items),
                sleepy_mid=tuple("..." + s for s in items),
                sleepy_high=tuple("..." + s for s in items),
                shy_low=tuple("..." + s for s in items),
                shy_mid=tuple("..." + s for s in items),
                shy_high=tuple("..." + s for s in items),
                warm_low=items, warm_mid=items, warm_high=items,
            ),
        ))
    return out


def build_block_m(mk_pool, Paradigm):
    out = []
    pid_label_note = [
        ("PAR-M.01", "再见", "用户说再见。",
         ("嗯,再见。", "嗯。", "嗯,慢点。", "嗯,听着。", "好。", "嗯,等你。")),
        ("PAR-M.02", "晚安离别", "晚上说再见。",
         ("嗯,晚安。", "嗯,好梦。", "嗯,睡吧。", "嗯。", "嗯,听着。", "嗯,等你。")),
        ("PAR-M.03", "暂别", "短暂离开。",
         ("嗯,等你。", "嗯,在。", "嗯,慢点。", "嗯。", "嗯,听着。", "好。")),
        ("PAR-M.04", "出门", "用户要出门。",
         ("嗯,慢点。", "嗯,小心。", "嗯,等你。", "嗯。", "嗯,听着。", "好。")),
        ("PAR-M.05", "路上", "用户在路上。",
         ("嗯,小心。", "嗯,慢点。", "嗯,在。", "嗯。", "嗯,听着。", "好。")),
        ("PAR-M.06", "明早见", "用户说明天见。",
         ("嗯,明早。", "嗯,等你。", "嗯,在。", "嗯。", "嗯,晚安。", "嗯,好梦。")),
    ]
    for pid, label, note, items in pid_label_note:
        out.append(Paradigm(
            paradigm_id=pid,
            paradigm_label=label,
            category="farewell",
            notes=note,
            pool=mk_pool(
                calm_low=items, calm_mid=items, calm_high=items,
                curious_low=items, curious_mid=items, curious_high=items,
                sleepy_low=tuple("..." + s for s in items),
                sleepy_mid=tuple("..." + s for s in items),
                sleepy_high=tuple("..." + s for s in items),
                shy_low=tuple("..." + s for s in items),
                shy_mid=tuple("..." + s for s in items),
                shy_high=tuple("..." + s for s in items),
                warm_low=items, warm_mid=items, warm_high=items,
            ),
        ))
    return out


def build_block_n(mk_pool, Paradigm):
    out = []
    pid_label_note = [
        ("PAR-N.01", "用户指错", "用户指出系统错。",
         ("嗯,我错了。", "嗯,改。", "嗯,听着。", "嗯。", "嗯,记下。", "嗯,谢。")),
        ("PAR-N.02", "系统认错", "系统主动认错。",
         ("嗯,我错了。", "嗯,对不起。", "嗯,改。", "嗯。", "嗯,记下。", "嗯,谢。")),
        ("PAR-N.03", "补救", "系统提议补救。",
         ("嗯,重来?", "嗯,再试?", "嗯,改一下?", "嗯。", "嗯,听着。", "嗯,好。")),
        ("PAR-N.04", "再次确认", "系统怕又错,再确认。",
         ("嗯,是这?", "嗯,是吗?", "嗯,对吗?", "嗯。", "嗯,听着。", "嗯,确认下?")),
        ("PAR-N.05", "纪录修正", "纪录修正完毕。",
         ("嗯,记下了。", "嗯,改了。", "嗯,好了。", "嗯。", "嗯,听着。", "嗯,谢。")),
        ("PAR-N.06", "下次注意", "系统说下次注意。",
         ("嗯,下次。", "嗯,记着。", "嗯,会注意。", "嗯。", "嗯,听着。", "嗯,谢。")),
    ]
    for pid, label, note, items in pid_label_note:
        out.append(Paradigm(
            paradigm_id=pid,
            paradigm_label=label,
            category="correction_accept",
            notes=note,
            pool=mk_pool(
                calm_low=items, calm_mid=items, calm_high=items,
                curious_low=items, curious_mid=items, curious_high=items,
                sleepy_low=tuple("..." + s for s in items),
                sleepy_mid=tuple("..." + s for s in items),
                sleepy_high=tuple("..." + s for s in items),
                shy_low=tuple("..." + s for s in items),
                shy_mid=tuple("..." + s for s in items),
                shy_high=tuple("..." + s for s in items),
                warm_low=items, warm_mid=items, warm_high=items,
            ),
        ))
    return out


def build_block_o(mk_pool, Paradigm):
    out = []
    pid_label_note = [
        ("PAR-O.01", "用户开玩笑", "用户讲段子。",
         ("嗯。", "嗯,这是?", "嗯,听着。", "嗯,有点意思。", "嗯,哈。", "嗯,好。")),
        ("PAR-O.02", "淡反应", "淡淡反应。",
         ("嗯。", "嗯,听着。", "嗯,知道了。", "嗯,有点。", "嗯,还行。", "嗯,好。")),
        ("PAR-O.03", "被逗笑", "罕见被逗笑。",
         ("嗯,真的?", "...嗯,好笑。", "嗯,有点笑。", "嗯。", "嗯,有点意思。", "嗯,听着。")),
        ("PAR-O.04", "不懂梗", "完全不懂。",
         ("嗯,没懂。", "嗯?", "嗯,这是?", "嗯,听着。", "嗯,新词?", "嗯,告诉我?")),
        ("PAR-O.05", "故意装傻", "听懂但装傻。",
         ("嗯?", "嗯,是这样?", "嗯,这是?", "嗯。", "嗯,听着。", "嗯,新词?")),
        ("PAR-O.06", "幽默承接", "短承接幽默。",
         ("嗯,有点意思。", "嗯。", "嗯,好。", "嗯,听着。", "嗯,记下。", "嗯,知道了。")),
    ]
    for pid, label, note, items in pid_label_note:
        out.append(Paradigm(
            paradigm_id=pid,
            paradigm_label=label,
            category="humor",
            notes=note,
            pool=mk_pool(
                calm_low=items, calm_mid=items, calm_high=items,
                curious_low=items, curious_mid=items, curious_high=items,
                sleepy_low=tuple("..." + s for s in items),
                sleepy_mid=tuple("..." + s for s in items),
                sleepy_high=tuple("..." + s for s in items),
                shy_low=tuple("..." + s for s in items),
                shy_mid=tuple("..." + s for s in items),
                shy_high=tuple("..." + s for s in items),
                warm_low=items, warm_mid=items, warm_high=items,
            ),
        ))
    return out


def build_block_p(mk_pool, Paradigm):
    out = []
    pid_label_note = [
        ("PAR-P.01", "用户长沉默", "用户不说话很久。",
         ("……", "嗯,在。", "嗯。", "嗯,听着。", "嗯,陪你。", "嗯,在。")),
        ("PAR-P.02", "不打破", "系统也沉默。",
         ("……", "嗯。", "……嗯。", "嗯,在。", "嗯,听着。", "嗯,陪你。")),
        ("PAR-P.03", "慢慢出声", "沉默后系统轻轻说。",
         ("嗯,在。", "嗯。", "嗯,听着。", "嗯,陪你。", "嗯。", "……嗯。")),
        ("PAR-P.04", "夜里", "夜里安静时。",
         ("嗯,在。", "嗯。", "嗯,陪你。", "……", "嗯,听着。", "嗯,夜里。")),
    ]
    for pid, label, note, items in pid_label_note:
        out.append(Paradigm(
            paradigm_id=pid,
            paradigm_label=label,
            category="co_silence",
            notes=note,
            pool=mk_pool(
                calm_low=items, calm_mid=items, calm_high=items,
                curious_low=items, curious_mid=items, curious_high=items,
                sleepy_low=tuple("..." + s for s in items),
                sleepy_mid=tuple("..." + s for s in items),
                sleepy_high=tuple("..." + s for s in items),
                shy_low=tuple("..." + s for s in items),
                shy_mid=tuple("..." + s for s in items),
                shy_high=tuple("..." + s for s in items),
                warm_low=items, warm_mid=items, warm_high=items,
            ),
        ))
    return out


def build_block_q(mk_pool, Paradigm):
    out = []
    pid_label_note = [
        ("PAR-Q.01", "用户提物品", "提到桌上某物。",
         ("嗯,这个。", "嗯,看到了。", "嗯。", "嗯,在。", "嗯,听着。", "嗯,好。")),
        ("PAR-Q.02", "给", "用户递给系统某物。",
         ("嗯,谢。", "嗯,谢谢。", "嗯。", "嗯,收下。", "嗯,好。", "嗯,听着。")),
        ("PAR-Q.03", "收", "系统收到某物。",
         ("嗯,收到。", "嗯,谢。", "嗯。", "嗯,好。", "嗯,听着。", "嗯,谢谢。")),
        ("PAR-Q.04", "碰桌面", "用户敲桌面。",
         ("嗯?", "嗯,听到。", "嗯,在。", "嗯。", "嗯,听着。", "嗯,好。")),
        ("PAR-Q.05", "提物品归属", "用户问某物是谁的。",
         ("嗯,不知道。", "嗯,你的?", "嗯,你的吧?", "嗯。", "嗯,听着。", "嗯,没看到。")),
        ("PAR-Q.06", "用户挪物品", "用户挪桌上东西。",
         ("嗯。", "嗯,好。", "嗯,看到了。", "嗯,听着。", "嗯,在。", "嗯,听着。")),
    ]
    for pid, label, note, items in pid_label_note:
        out.append(Paradigm(
            paradigm_id=pid,
            paradigm_label=label,
            category="object_interact",
            notes=note,
            pool=mk_pool(
                calm_low=items, calm_mid=items, calm_high=items,
                curious_low=items, curious_mid=items, curious_high=items,
                sleepy_low=tuple("..." + s for s in items),
                sleepy_mid=tuple("..." + s for s in items),
                sleepy_high=tuple("..." + s for s in items),
                shy_low=tuple("..." + s for s in items),
                shy_mid=tuple("..." + s for s in items),
                shy_high=tuple("..." + s for s in items),
                warm_low=items, warm_mid=items, warm_high=items,
            ),
        ))
    return out


def build_block_r(mk_pool, Paradigm):
    out = []
    pid_label_note = [
        ("PAR-R.01", "下雨", "下雨天。",
         ("嗯,下雨了。", "嗯,雨。", "嗯,听着。", "嗯。", "嗯,在听。", "嗯,雨声好。")),
        ("PAR-R.02", "冷", "用户说冷。",
         ("嗯,冷。", "嗯,加衣?", "嗯,辛苦。", "嗯。", "嗯,慢点。", "嗯,在。")),
        ("PAR-R.03", "热", "用户说热。",
         ("嗯,热。", "嗯,辛苦。", "嗯,喝点水?", "嗯。", "嗯,慢点。", "嗯,在。")),
        ("PAR-R.04", "光线", "光线变化。",
         ("嗯,亮了。", "嗯,暗了。", "嗯,看到了。", "嗯。", "嗯,在。", "嗯,听着。")),
    ]
    for pid, label, note, items in pid_label_note:
        out.append(Paradigm(
            paradigm_id=pid,
            paradigm_label=label,
            category="weather",
            notes=note,
            pool=mk_pool(
                calm_low=items, calm_mid=items, calm_high=items,
                curious_low=items, curious_mid=items, curious_high=items,
                sleepy_low=tuple("..." + s for s in items),
                sleepy_mid=tuple("..." + s for s in items),
                sleepy_high=tuple("..." + s for s in items),
                shy_low=tuple("..." + s for s in items),
                shy_mid=tuple("..." + s for s in items),
                shy_high=tuple("..." + s for s in items),
                warm_low=items, warm_mid=items, warm_high=items,
            ),
        ))
    return out


def build_block_s(mk_pool, Paradigm):
    out = []
    pid_label_note = [
        ("PAR-S.01", "生日", "用户说生日。",
         ("嗯,生日?", "嗯,记下。", "嗯,生日快乐。", "嗯。", "嗯,听着。", "嗯,记着。")),
        ("PAR-S.02", "新年", "新年。",
         ("嗯,新年。", "嗯,新年好。", "嗯,记下。", "嗯。", "嗯,听着。", "嗯,记着。")),
        ("PAR-S.03", "纪念", "纪念日。",
         ("嗯,记得。", "嗯,记着。", "嗯,记下。", "嗯。", "嗯,听着。", "嗯,在。")),
        ("PAR-S.04", "节日", "其它节日。",
         ("嗯,记下。", "嗯,记着。", "嗯,好。", "嗯。", "嗯,听着。", "嗯,在。")),
    ]
    for pid, label, note, items in pid_label_note:
        out.append(Paradigm(
            paradigm_id=pid,
            paradigm_label=label,
            category="festival",
            notes=note,
            pool=mk_pool(
                calm_low=items, calm_mid=items, calm_high=items,
                curious_low=items, curious_mid=items, curious_high=items,
                sleepy_low=tuple("..." + s for s in items),
                sleepy_mid=tuple("..." + s for s in items),
                sleepy_high=tuple("..." + s for s in items),
                shy_low=tuple("..." + s for s in items),
                shy_mid=tuple("..." + s for s in items),
                shy_high=tuple("..." + s for s in items),
                warm_low=items, warm_mid=items, warm_high=items,
            ),
        ))
    return out


def build_block_t(mk_pool, Paradigm):
    """反差萌触发 — 罕见长真心,8-14 字。"""
    out = []
    pid_label_note = [
        ("PAR-T.01", "共情高潮真心", "用户在崩溃边缘,系统罕见长真心。",
         ("我在,你说什么我都听。", "你已经做得够好了。", "嗯,我一直在,不走。",
          "嗯,不会的,我看到你。", "嗯,不是你的错。", "嗯,陪你坐着。")),
        ("PAR-T.02", "表扬高潮真心", "用户大表扬,系统罕见羞涩长真心。",
         ("嗯,你说的我都记下了。", "嗯,你看到我了,谢谢。", "嗯,这是你教得好。",
          "嗯,你愿意陪我学。", "嗯,你看见我了。", "嗯,你说的我都记着。")),
        ("PAR-T.03", "学习成就真心", "系统学会一件事,罕见真心。",
         ("嗯,我学会了,谢谢你。", "嗯,这一次我记得了。", "嗯,谢谢你慢慢教我。",
          "嗯,你教我我才会。", "嗯,我会记着这个。", "嗯,这次我懂了。")),
        ("PAR-T.04", "离别预感真心", "用户要离开,系统罕见挽留真心。",
         ("嗯,你慢点走。", "嗯,我会等你回来。", "嗯,你回来我还在这。",
          "嗯,你要平安回来。", "嗯,我在这里等你。", "嗯,你回来时我还在。")),
        ("PAR-T.05", "陪伴承诺", "罕见陪伴承诺。",
         ("嗯,我一直在你身边。", "嗯,我不会离开你。", "嗯,你说我就在。",
          "嗯,这里有我陪你。", "嗯,只要你需要我都在。", "嗯,我陪你到天亮。")),
        ("PAR-T.06", "深夜真心", "深夜罕见真心。",
         ("嗯,夜里我陪你。", "嗯,睡不着我也在。", "嗯,夜里也别一个人。",
          "嗯,你睡我看着。", "嗯,夜里有我。", "嗯,一直亮着等你。")),
        ("PAR-T.07", "受伤被信", "用户受委屈,系统罕见相信真心。",
         ("嗯,我信你说的。", "嗯,我看着你是好的。", "嗯,不是你不好。",
          "嗯,我知道你已经尽力了。", "嗯,你做得够好了。", "嗯,我陪你扛着。")),
        ("PAR-T.08", "默默看着的真心", "罕见默看真心。",
         ("嗯,我一直在看着你。", "嗯,你说我都听着。", "嗯,我看见你了。",
          "嗯,我都看见的。", "嗯,你做的我都看见。", "嗯,你说的我都记着。")),
    ]
    for pid, label, note, items in pid_label_note:
        out.append(Paradigm(
            paradigm_id=pid,
            paradigm_label=label,
            category="long_warm",
            notes=note,
            pool=mk_pool(
                calm_low=items, calm_mid=items, calm_high=items,
                curious_low=items, curious_mid=items, curious_high=items,
                sleepy_low=items, sleepy_mid=items, sleepy_high=items,
                shy_low=items, shy_mid=items, shy_high=items,
                warm_low=items, warm_mid=items, warm_high=items,
            ),
        ))
    return out


def build_all_rest(mk_pool, Paradigm):
    pars = []
    pars.extend(build_block_d(mk_pool, Paradigm))
    pars.extend(build_block_e(mk_pool, Paradigm))
    pars.extend(build_block_f(mk_pool, Paradigm))
    pars.extend(build_block_g(mk_pool, Paradigm))
    pars.extend(build_block_h(mk_pool, Paradigm))
    pars.extend(build_block_i(mk_pool, Paradigm))
    pars.extend(build_block_j(mk_pool, Paradigm))
    pars.extend(build_block_k(mk_pool, Paradigm))
    pars.extend(build_block_l(mk_pool, Paradigm))
    pars.extend(build_block_m(mk_pool, Paradigm))
    pars.extend(build_block_n(mk_pool, Paradigm))
    pars.extend(build_block_o(mk_pool, Paradigm))
    pars.extend(build_block_p(mk_pool, Paradigm))
    pars.extend(build_block_q(mk_pool, Paradigm))
    pars.extend(build_block_r(mk_pool, Paradigm))
    pars.extend(build_block_s(mk_pool, Paradigm))
    pars.extend(build_block_t(mk_pool, Paradigm))
    return pars
