# APV3.0test Claude 二次评审吸收报告

日期: 2026-06-16

## 1. 设计

本轮处理的是 Claude 对 Phase2.3 到 Phase4.1 纠偏后的二次评审。评审结论里有三类信息:

1. 已确认修正有效:
   - `role_decode.py` 的 `_emission()` 已经不再读取 `prev_role`、`index`、`last_index`。
   - `all_slot_confidence_floor` 已删除。
   - 感知槽填充测试已经从裸候选池改成有结构锚的教学证据。
2. 需要立刻清理的小问题:
   - `shared_fragment` emission 中仍有内联 `0.1` 地板。
   - `paradigm_fill.py` 中锚点草稿 strength 也有 `max(0.1, column.occupancy)` 地板。
3. 需要进入 Phase5 的设计门:
   - Viterbi transition 权重不能永远是固定 config, 后续要由观察到的角色转移统计学习。
   - 范式发现不能长期停留在批处理后处理算法, 必须走增量式在线更新。
   - 自然教学和 LLM 标准教学协议必须写入同一种 AP-native 证据, 不能让 LLM 成为学生侧运行策略。

本轮代码只处理第 2 类确定问题, 不把第 3 类提前伪装成已落地能力。

## 2. 审查完善

### 2.1 关于内联 0.1 地板

这两个地板的哲学问题一致: 它们会让低 occupancy 或低 coherence 的列获得一个人为最低强度。即使它们很小, 也会破坏 APV3.0 的证据原则:

- 低证据应该自然低能量。
- 冷启动不足时不暴露范式。
- 草稿候选和角色判断应由观察统计、关系重叠、行动后果和当前焦点共同支撑, 不能由隐藏底分支撑。

因此本轮选择直接删除地板, 而不是把 `0.1` 移到 config。原因是: 如果一个值的唯一作用是让缺证据对象不归零, 它不是需要命名的可调参数, 而是应该被移除的脚手架。

### 2.2 关于 Viterbi transition

当前 `_transition(prev_role, role)` 仍然保留弱平滑, 这是 Viterbi 解码本身合理的一部分。但它现在仍是固定 config 权重, 不能被视为完整 AP 自学习机制。

审查结论:

- 当前阶段可以保留, 因为完全移除 transition 会让角色解码退化为逐列独立分类。
- 后续 Phase5 必须把 transition 权重纳入统计学习路径。
- transition 只能作为从观察中学习到的角色连续性偏好, 不能成为人工塑造范式形状的永久先验。

### 2.3 关于教学等价性

用户补充的关键边界:

> APV3.0 中文开放自由对话底座既要支持像教育小孩子一样的自然教学, 也要允许 LLM 通过标准教学协议加快学习。两种情况下学到的内容效果理论上应该完全等价。

本轮确认:

- LLM 可以作为教师侧协议生成器、训练样例组织器、奖惩信号标注器。
- LLM 不可以作为学生侧 runtime policy、答案选择器、隐藏 solver、关键词路由器。
- 自然教学与 LLM 教学最终必须写入同一种证据:
  - learned vectors
  - explicit transitions
  - paradigm observations
  - relation/coherence statistics
  - action outcomes
  - reward/punishment traces
  - percept prototypes
  - commit boundaries

只有这样, 二者学到的能力才可能在运行时等价。

## 3. 通过落地

修改文件:

- `APV3.0test/apv3test/runtime/role_decode.py`
- `APV3.0test/apv3test/runtime/paradigm_fill.py`

具体修改:

```python
# role_decode.py
self.config.role_viterbi_shared_match_reward * column.occupancy * coherence
```

代替:

```python
self.config.role_viterbi_shared_match_reward * max(column.occupancy, 0.1) * max(0.1, coherence)
```

```python
# paradigm_fill.py
strength = max(0.0, paradigm.conf) * column.occupancy
```

代替:

```python
strength = max(0.0, paradigm.conf) * max(0.1, column.occupancy)
```

## 4. 严谨验收测试

已运行目标测试:

```powershell
python -m pytest APV3.0test\tests\test_phase2_4_role_viterbi.py APV3.0test\tests\test_phase2_6_percept_slot_fill.py APV3.0test\tests\test_phase4_0_minimal_dialogue_runtime.py APV3.0test\tests\test_phase4_1_small_skill_reproduction.py -q
```

结果:

```text
20 passed in 0.57s
```

这些测试说明: 删除地板后, 当前角色解码、感知槽填充、最小对话 runtime 和小批旧技能复现仍然可以依靠真实证据通过。

已运行全量测试:

```powershell
python -m pytest APV3.0test\tests -q
```

结果:

```text
83 passed in 1.75s
```

已运行 runtime 源码禁用通道扫描:

```powershell
rg -n --glob "*.py" "keyword|answer_table|student_side_llm|branch_alignment|math_process_tokens|regex|full_sentence_macro|黄色苹果" APV3.0test\apv3test
```

结果: 无命中。

已运行残留硬地板/旧位置语法扫描:

```powershell
rg -n "max\([^\n]*0\.1|all_slot_confidence_floor|def _emission\(.*prev_role|def _emission\(.*index|last_index|variable_seen" APV3.0test\apv3test APV3.0test\tests
```

结果: 无命中。

## 5. 最终汇总

本轮吸收结论:

- Claude 二次评审中关于内联地板的问题成立, 已修正。
- 修正选择是删除地板, 不是把地板配置化, 因为这更符合 APV3.0 的低证据低能量原则。
- Viterbi transition 暂时保留为弱平滑, 但已经列入 Phase5 学习化门槛。
- 范式发现的批处理倾向被确认为后续架构风险, 已进入 Phase5 增量式在线更新门槛。
- 自然教学与 LLM 标准教学协议的等价性被正式纳入后续设计边界。

仍不能宣称:

- 完整 APV3.0 范式通道已经全部落地。
- 完整跨模态泛化已经完成。
- 自由中文开放对话底座已经完成。
- Viterbi transition 权重已经完成后天学习化。
- 范式发现已经完全在线增量化。

下一步:

进入 Phase5 设计门, 先把增量式范式发现、transition 权重学习、教学等价合同写成不可绕过的实现标准, 再开始落地。
