#!/usr/bin/env python3
"""V4 生活经验预热包 — 走真实教学管线灌经验流 (非答案表)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from apv3test.runtime.phase20_7 import TeacherFeedback, run_phase20_7_turn

DIALOGUES = [
    ("你好", "你好呀"), ("嗯", "嗯嗯"), ("早上好", "早"), ("晚安", "嗯晚安"),
    ("谢谢", "不客气"), ("再见", "嗯再见"), ("嗨", "嗨"), ("好的", "嗯"),
    ("在吗", "在"), ("干嘛呢", "嗯在想"), ("吃饭了吗", "还没"), ("累不累", "还好"),
    ("你叫什么", "不太会,教教"), ("你是谁", "不太会,教教"),
    ("今天开心吗", "嗯"), ("帮我个忙", "嗯?什么事"), ("对不起", "没事"),
    ("喜欢你", "嗯..."), ("讲个故事", "不太会,教教"), ("唱歌", "不太会,教教"),
    ("天气真好", "嗯"), ("无聊", "嗯...想想该做什么"), ("怎么才能变聪明", "多想想多问"),
    ("你来教我", "嗯,你教我"), ("好的好的", "嗯嗯"),
]
FACTS = [('2+3=?','5'),('4+5=?','9'),('3+2=?','5'),('2+4=?','6'),('1+1=?','2'),
         ('3+5=?','8'),('2+5=?','7'),('4+3=?','7'),('1+6=?','7'),('5+8=?','13'),
         ('4+3+1=?','8'),('2+6=?','8'),('7+5=?','12')]
DEMOS = [("23+45=?", "68"), ("31+26=?", "57")]

def build_starter_pack(db_path, session_id="phase20_7_workbench"):
    count = 0
    for text, reply in DIALOGUES:
        run_phase20_7_turn(user_text=text, teacher_feedback=TeacherFeedback(feedback_text=reply, reward_mag=1.0),
                           session_id=session_id, db_path=db_path, max_ticks=32, runtime_stage="stage6")
        count += 1
    for q, a in FACTS:
        run_phase20_7_turn(user_text=q, teacher_feedback=TeacherFeedback(feedback_text=a, reward_mag=1.0),
                           session_id=session_id, db_path=db_path, max_ticks=48, runtime_stage="stage6")
        count += 1
    for q, a in DEMOS:
        run_phase20_7_turn(user_text=q, session_id=session_id, db_path=db_path, max_ticks=48, runtime_stage="stage6")
        run_phase20_7_turn(user_text=q, teacher_feedback=TeacherFeedback(feedback_text=a, reward_mag=1.0),
                           session_id=session_id, db_path=db_path, max_ticks=48, runtime_stage="stage6")
        count += 1
    return {"taught": count, "dialogues": len(DIALOGUES), "facts": len(FACTS), "demos": len(DEMOS)}

if __name__ == "__main__":
    db = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("tmp_starter.sqlite")
    result = build_starter_pack(db)
    print(f"# 生活经验预热包\n\n- 教学条目: {result['taught']} (对话{result['dialogues']}+事实{result['facts']}+示范{result['demos']})")
    print(f"- DB: {db}\n\n注: 全部走真实教学管线(run_phase20_7_turn+TeacherFeedback), 是经验流不是答案表.")