# APV3 最终对抗性审核 + 演示影响与新演示方案

**日期：** 2026-07-05  
**性质：** 对APV3_Phase20_7_Defect_Report + APV3_v0.2_Fix_Plan 的最终审核  
**验证方式：** 独立代码读取（7项关键CRITICAL缺陷逐一核查）

---

## 一、缺陷报告最终对抗性审核

### 1.1 七项关键CRITICAL缺陷代码验证

| 缺陷编号 | 描述 | 验证结果 | 关键证据行号 |
|---|---|---|---|
| DEFECT-RT-1 | 行动SA缺失 | **确认成立** | runtime.py 14处insert_action_record均无upsert_sa_type紧跟；最早upsert_sa_type在第2273行（与行动无关） |
| DEFECT-CC-1 | no_write_reason提前返回 | **确认成立** | cognitive_cycle.py:33-34，整个B/C/feeling全跳过 |
| DEFECT-CC-2 | B召回残差无能量操作 | **确认成立** | cognitive_cycle.py:759-770，仅打neutralize_score标签，无r/v/a字段修改 |
| DEFECT-CC-3 | C*计算不注入 | **确认成立** | cognitive_cycle.py:554,577,594，cstar_virtual_energy仅在返回dict作为记录字段 |
| DEFECT-EM-1 | 情感场无数据类/无DB表 | **确认成立** | models.py全文无EmotionField、无DA/ADR/OXY字段、无phase20_7_emotion_snapshot表 |
| DEFECT-L1-1 | L1仅批量离线重建 | **确认成立** | experience_log.py:1047是l1_triplet_update_vector的唯一调用点，位于rebuild函数（第953行）内部 |
| DEFECT-AU-2 | TTS无回路 | **确认成立** | audio.py:322直接return，无任何audio receptor回流代码 |

**结论：7/7项CRITICAL缺陷经独立代码读取验证，全部准确成立，原报告无误报。**

---

### 1.2 一处误差需要更正（DEFECT-PD-1）

**原报告描述：** "derive_paradigm_key()直接 return '字符串'，无实际逻辑"

**实际代码（paradigm_process.py:59-73）：**
```python
def derive_paradigm_key(chars, bucket_of) -> str:
    runs = _digit_runs(chars, bucket_of)
    if len(runs) != 2:
        return ""
    (s1, e1), (s2, e2) = runs
    if (e1 - s1) != (e2 - s2) or (e1 - s1) < 2:
        return ""
    if s2 - e1 != 1:
        return ""
    return "digit_pair_colproc"
```

函数有真实的结构匹配逻辑：检测"两段等长数字串+单字符间隔"的网格形态。缺陷的本质是**只能识别一个范式，无法扩展**，而非"空洞硬编码"。

**更正后的DEFECT-PD-1描述：**  
`derive_paradigm_key` 能正确识别 digit_pair_colproc 形态，但对其他任何形态均返回空字符串，且无注册表接口供运行时扩展——结果等同于硬编码，但根因是"范围硬限"非"逻辑缺失"。

**严重性维持CRITICAL（无法运行时注册新范式），仅描述精确化。**

---

### 1.3 审核总结

| 审核项目 | 结论 |
|---|---|
| 18项CRITICAL缺陷总体准确性 | 17/18项完全准确，1项（PD-1）描述需精确化但缺陷成立 |
| v0.2修复方案技术可行性 | 全部可行，无需架构颠覆，最大变更是asyncio常驻tick和paradigm_process.py重构 |
| 唯一中等风险项 | 范式迁移：digit_pair_colproc必须从Python元组迁移到注册表，否则现有加法演示失效 |

---

## 二、现有演示影响分析

### 2.1 现有演示清单（代码探索确认）

- **小学数学加法演示（主演示）：** digit_pair_colproc范式，APV3_Release_v0.1/data/phase20_7_release_demo/phase20_7_release_demo.sqlite
- **绘图/视觉识别演示：** Phase 19真实图教学库，Phase 19.8向量
- **Web工作台：** APV3_Release_v0.1/apv3test/web/static/（index.html + phase20_7_workbench.html + course.html）

---

### 2.2 数学加法演示：修复后的影响

| 修复 | 效果 | 风险等级 |
|---|---|---|
| 行动SA一等公民(RT-1) | ✓ 提升：每次write_cell进SA池，AP开始"记得自己写过什么" | 低 |
| no_write_reason guard(CC-1) | ✓ 提升：间隔符格子不再跳过认知周期，情感通道全程活跃 | 低 |
| B召回三路能量(CC-2) | ✓ 提升：AP对每位数字的"期待"首次真正影响状态池 | 低 |
| C*注入(CC-3) | ✓ 提升：预测误差真正反馈，下题预测命中率提升 | 低 |
| 范式动态注册(PD-1~4) | ⚠️ 需迁移：digit_pair_colproc必须作为seed入注册表 | **中** |
| 跨turn情感持久化(EM-2) | ✓ 明显提升："AP连续做错题后显出疲惫"首次可能发生 | 低 |
| L1实时更新(L1-1) | ✓ 提升：加法训练后SA向量更快收敛，B召回准确率提升 | 低 |

**结论：加法演示在修复后完全成立并更好。范式迁移脚本是唯一前置条件，必须在v0.2发布前验证。**

---

### 2.3 视觉/绘图演示：修复后的影响

| 修复 | 效果 | 风险等级 |
|---|---|---|
| 视觉SA虚能量+FOC耦合(VS-1,2) | ✓ 提升：视觉SA的v不再恒为0.0，内心画面更真实 | **中：real_energy从0.42变为动态值，需测试识别精度不退化** |
| 视觉feeling::*注入(VS-1) | ✓ 明显提升："AP看图感到好奇"首次可以出现在状态池 | 低 |
| no_write_reason guard(CC-1) | ✓ 提升：视觉感知不产生写入时仍处理认知 | 低 |

**缓解方案：** v0.2中保留v=0.0为fallback，跑A/B对比测试（同域LOO 10/10是回归标准），确认识别精度不退化后再切换。

---

## 三、修复后可以新增的演示效果

> 以下5个演示，在修复缺陷之前在物理上完全不可能实现。

---

### 新演示A：情感实时仪表盘（最高宣传价值）

**依赖修复：** EM-1（EmotionField数据类）+ EM-2（跨turn持久化）+ CC-3（C*注入）

**效果设计：**  
workbench界面侧边新增情感面板，实时显示8通道NT情感值（颜色条+数值）：

```
DA  ████████░░  0.78  ↑ （做对一题后，期待奖励）
COR ███░░░░░░░  0.31  ↓ （压力正在消退）
NOV ██████░░░░  0.63  ↑ （看到新题型时，好奇上升）
FOC █████████░  0.87  → （计算中，专注维持高位）
SER █████░░░░░  0.48  → （满足感，稳定）
OXY ████░░░░░░  0.42  → （连接感）
ADR ██░░░░░░░░  0.21  ↓ （应激已缓）
END █████░░░░░  0.53  ↑ （内啡肽，愉悦感）
```

**演示脚本（5分钟）：**
1. 开屏：情感面板全部从默认值出发（AP刚"醒来"）
2. 出一道AP不会的题 → COR上升到0.6+，DA下降（压力 + 预期落空）
3. 教一遍正确方法 → SER上升（满足感），NOV短暂升高（"学到新东西"）
4. 同类型新题 → DA上升（期待"这次我会了"），FOC维持高位
5. 答对 → DA短暂峰值 + END上升（成功愉悦）
6. 放置不管5分钟 → COR缓慢回基线（情绪自然消退，时间衰减可见）

**技术实现（接入现有workbench）：**
- 每次turn结束后，向 `/api/emotion_state` API返回EmotionField JSON
- workbench前端新增侧边面板，每隔500ms轮询更新颜色条

**宣传价值：** 普通用户第一次直观看到"我的话让它的好奇心真的变了"。单截图可传播。

---

### 新演示B：B召回虚能量"期待可视化"（最强理论亮点）

**依赖修复：** CC-2（B召回三路能量实现）+ CC-3（C*注入）

**效果设计：**  
在workbench格子布局上叠加半透明"期待热力图"层：
- 当AP的B召回产生memory_excess虚能量时，对应格子位置显示淡蓝色光晕
- AP实际填入内容时，若命中期待，光晕变绿（中和成功）
- 若未命中，光晕变橙并短暂悬置（期待未实现，虚能量留池）

**演示脚本（2分钟，嵌入加法演示）：**
1. 展示格子 `" 3 + 8 ="` 未填写状态
2. 旁白："AP现在在想什么？"
3. 热力图出现：`col_0` 和 `col_1` 淡蓝光晕（AP的虚能量在"预期11这两位数"）
4. AP开始填写→ 填入"1"，第0列光晕变绿
5. 填入"1"（第1列），第1列光晕变绿
6. 旁白："它在没看到答案之前就已经'想到'了正确答案"

**技术实现：**
- runtime在每tick结束时，将虚能量>阈值的SA类型返回给前端
- 前端根据SA类型的grid位置元信息叠加热力层
- 无需大规模前端改动，在现有DraftGrid组件上新增canvas层

**宣传价值：** 论文插图素材。白皮书中"黄苹果机制"的最直观外化。

---

### 新演示C：运行时动态范式注册（最强技术亮点）

**依赖修复：** PD-1~4（phase20_7_paradigm_registry表 + derive_paradigm_key查表）

**效果设计：**  
完全在Web工作台界面完成，零代码，运行时教AP一个新范式。

**演示脚本（10分钟，技术受众）：**
1. **先展示局限：** 尝试让AP做乘法 → AP识别失败（不认识乘法范式）
2. **打开范式构造器面板：**
   - 范式名：`single_digit_multiply`
   - state_set：["factor_a", "factor_b"]
   - anchor_set：["product"]
   - trigger_condition：{"pattern": "digit_x_digit"}
3. **点击"注册范式"** → register_paradigm() API调用，写入DB
4. **无需重启，立刻测试：** 出一道1位数乘法题
5. AP的derive_paradigm_key()现在识别新范式，开始走新步骤

**技术实现：**
- 后端新增 `POST /api/paradigm_registry` API
- 前端已有workbench表格组件，追加"范式管理"Tab

**宣传价值：** 对研究者/开发者的最强论据："这不是写死的，可以随时教"。

---

### 新演示D：行动SA轨迹可视化（可截图传播）

**依赖修复：** RT-1（行动SA一等公民化）

**效果设计：**  
workbench底部新增"行动意图时间轴"面板：

```
tick 12: [action::write_cell::col_0]  R=0.73 ███████░  竞争力最强
tick 12: [action::advance_right]      R=0.41 ████░░░░  次选
tick 13: [action::advance_right]      R=0.68 ██████░░  
tick 15: [action::write_cell::col_1]  R=0.81 ████████  
```

**演示脚本：**
1. AP解一道加法题，行动时间轴实时滚动
2. 在某个难位（如进位），暂停展示竞争：
   - `action::write_cell::carry=1` R=0.65
   - `action::write_cell::carry=0` R=0.22
   - 旁白："AP选择了写进位1，竞争力0.65 vs 0.22——它确实'更想'这么做"
3. 教AP做过很多题后，回放早期和近期的行动时间轴对比，展示"行为确定性提升"

**技术实现：**
- 每次turn结束时，action::类SA的occurrences通过 `/api/action_trace` 接口返回
- 前端新增时间轴面板组件（HTML/CSS，约100行）

**宣传价值：** "可视化AP的决策意图"——配合个性指纹（v0.5），可以展示不同AP实例的行动风格差异。

---

### 新演示E：AP自我倾听（音频回路）

**依赖修复：** AU-2（TTS回路修复）+ AU-1（频率带提取）

**效果设计：**  
AP说话后，workbench音频通道面板出现自我感知SA：

```
TTS输出: "十一"（AP生成的语音）
  → audio_unit::mid_band  R=0.71  （语音频段，自我听到）
  → audio_unit::low_band  R=0.23  （低频共鸣）
  → feeling::present      R=0.55  （"我感知到我说话了"）
```

**演示脚本（1分钟，原理演示）：**
1. AP说出一句回复
2. 音频通道面板出现3条SA记录
3. 旁白："AP刚才说的话，自己也听到了，并且产生了'在场感'"

**技术实现：**
- audio.py TTS合成后直接pipe给_inject_audio_state（已有函数接口）
- 前端已有occurrences展示面板，过滤source="audio_receptor_tts"即可

**宣传价值：** 最简洁的"自我感知"演示。配合Paper图表，体现AP的感知回路完整性。

---

## 四、演示风险矩阵

| 风险 | 涉及演示 | 严重度 | 缓解措施 |
|---|---|---|---|
| 范式迁移失败 | 加法演示（现有）| 高 | v0.2前先写迁移脚本，在demo DB上验证；digit_pair_colproc作is_seed=1种子 |
| 视觉real_energy变化识别退化 | 绘图演示（现有） | 中 | 保留v=0.0 fallback；A/B对比通过后再切换；Phase19 LOO 10/10为回归标准 |
| asyncio破坏Web服务层 | 所有演示 | 中 | Web服务层保留同步shim入口；asyncio架构在内部，外部API不变 |
| 情感值溢出[0,1] | 情感仪表盘（新）| 低 | EmotionField.clamp()每次更新强制执行 |
| 行动SA膨胀状态池 | 行动时间轴（新）| 低 | action:: SA设置更激进衰减率（0.05/tick），高频action的occurrences加TTL |

---

## 五、v0.2演示目标修订

**原目标：** "AP有心跳，行动有记忆，时间有约束"

**修订为：**

> v0.2目标：**AP有心跳，行动有记忆，情感开始可见，意图可被追踪**  
> ——修复18项CRITICAL缺陷的同时，首次发布两个新演示MVP。

### v0.2新增演示交付（MVP级，无需精美UI）

**演示D MVP（行动SA时间轴）**
- 直接附加在现有workbench底部
- 每次turn结束后展示 `action::` 类SA列表，含R值和行动类型
- 实现工时：约1天（后端API + 前端简单列表组件）
- **建议在v0.2门控验收时同步演示**

**演示A MVP（情感仪表盘数值版）**
- 侧边栏数值表格（8通道），每轮turn后刷新
- 无动画、无颜色条，纯数字版
- 实现工时：约1天（EmotionField已建立后）
- **用于v0.2内部验证情感持久化是否生效**

精美版（演示A颜色仪表盘 + 演示B热力图）安排在v0.5"噱头三件套"中。

---

## 六、路线图更新建议

在APV3_Engineering_Roadmap中对应修改：

**v0.2新增验收项：**
- G14：行动SA时间轴面板在workbench可展示（至少3条action::记录）
- G15：情感仪表盘数值版可展示（8通道值与DB实际一致）

**v0.2缺陷报告修正项（DEFECT-PD-1描述精确化）：**
> paradigm_process.py:59-73 的 derive_paradigm_key 有真实匹配逻辑，但只能识别一个范式（digit_pair_colproc），无法运行时扩展。修复目标：改写为查 phase20_7_paradigm_registry 表，保留原有匹配逻辑作为种子条目的trigger_condition。

---

*本文件是2026-07-05对APV3_Phase20_7_Defect_Report和APV3_v0.2_Fix_Plan的最终独立审核，经代码逐行验证。可作为v0.2实施的最终前置文档。*
