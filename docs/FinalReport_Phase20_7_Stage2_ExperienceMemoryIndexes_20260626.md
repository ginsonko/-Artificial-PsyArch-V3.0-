# Phase20.7 Stage 2 Experience Memory Indexes 验收报告

日期: 2026-06-26  
范围: 完整经验流查询、可重建 exact B0 派生索引、统一本地记忆视图、记忆包 provenance 与 tombstone 卸载。

---

## 1. 本阶段目标

Stage 2 的目标是在 Stage 1 文本闭环基础上, 把经验流变成后续工作台和记忆包可以使用的稳定底座:

1. exact B0 不再每次全量扫描经验事件, 而是优先查询可重建派生索引。
2. 索引不是事实源, 删除索引后必须能从 `phase20_7_experience_events` 重建。
3. 本地记忆只提供一个统一入口, 内部分为 `fast_tendency` 与 `slow_trace`。
4. 用户删除记忆不破坏经验流事实, 而是写入 tombstone, 后续召回不再使用该事件。
5. 记忆包导入/归属/卸载有 provenance, 卸载通过 tombstone 移除驱动力。

---

## 2. 已落地内容

### 2.1 可重建 exact B0 索引

`models.py` 新增:

1. `phase20_7_exact_b0_index`
2. `idx_phase20_7_exact_b0_lookup`

`experience_log.py` 新增:

1. `upsert_exact_b0_index(...)`
2. `rebuild_phase20_7_indexes(...)`

`runtime.py` 已更新:

1. 教师反馈写入 `experience_alignment` 后同步写入 exact B0 派生索引。
2. 召回时优先查 `phase20_7_exact_b0_index`。
3. 索引缺失时可回退到经验流并补回索引。
4. tombstoned event 不参与召回。

### 2.2 统一记忆视图

`experience_log.py` 新增:

1. `list_unified_memory_entries(...)`

该视图只从统一经验流和 tombstone 状态派生:

```text
local_memory_package_unified
├─ fast_tendency: 高支持度 experience_alignment
└─ slow_trace: 文本感受器留下的处理痕迹
```

这不是两套快慢数据库, 而是一个经验流的不同处理倾向展示。

### 2.3 tombstone 删除

`models.py` 新增:

1. `phase20_7_memory_tombstones`
2. `idx_phase20_7_memory_tombstones_ref`

`experience_log.py` 新增:

1. `tombstone_memory_entry(...)`
2. `insert_tombstone(...)`
3. `is_tombstoned(...)`

删除记忆时不直接抹掉经验事件, 而是写入“该事件不再驱动当前召回”的 tombstone。这样保留白箱审计与 AP 的“放下/来源移除”拟人过程。

### 2.4 记忆包 provenance

`experience_log.py` 新增:

1. `create_import_batch(...)`
2. `attach_package_membership(...)`
3. `unload_import_batch(...)`

卸载包时只 tombstone `was_new=1` 的 package member。共享/去重对象不应被错误删除。

---

## 3. 当前可展示效果

示例:

```text
1. 用户: 你好啊
2. 教师反馈: 你也好
3. AP: 嗯,记下了。
4. 删除 exact_b0_index 全部派生行
5. rebuild_phase20_7_indexes()
6. 用户: 你好啊
7. AP: 你也好
8. 用户在统一记忆视图删除“你好啊 -> 你也好”
9. 用户: 你好啊
10. AP: 我还不太知道怎么说。
```

这证明索引可重建, 记忆可展示, 删除不会破坏事实源但会影响后续行动。

---

## 4. 本阶段能证明什么

Stage 2 可以证明:

1. Phase20.7 已有可重建派生索引。
2. exact B0 召回性能路径从全表扫描升级为索引优先。
3. 索引删除后可从统一经验流恢复。
4. 本地记忆显示是一个入口, 不是快慢双数据库。
5. 记忆显示包含可读文本, 便于用户选择性删除。
6. tombstone 可以让旧经验不再驱动回复。
7. 记忆包卸载可以通过 provenance 找到新增对象并移除驱动力。

---

## 5. 本阶段尚未证明什么

Stage 2 还不证明:

1. 相似结构召回。
2. C_forward / C_backward / C*。
3. 在线嵌入 L1/L2/L3。
4. 未闭合感和 idle_think。
5. 视觉、听觉、画板和发布工作台。

Stage 3 应继续在 Stage 2 的索引与记忆基础上实现 B/C/C*。

---

## 6. 验收命令

### 6.1 Stage 0-2 单测

```powershell
python -m pytest .\tests\test_phase20_7_stage0_runtime_boundary.py .\tests\test_phase20_7_stage1_text_closed_loop.py .\tests\test_phase20_7_stage2_experience_memory_indexes.py -q
```

结果: `14 passed`。

### 6.2 Stage 2 红线扫描

```powershell
python .\scripts\red_line_check_v14.py --phase 20.7-stage2
```

结果: 见最终运行记录。

---

## 7. 下一阶段入口

Stage 3 应实现:

1. B: 当前认知, 由 SSP query 对历史结构相似召回后叠加。
2. C_forward: 从被召回结构向后传播, 形成预测认知。
3. C_backward: 从被召回结构向前传播, 形成解释认知。
4. C*: 预测与解释回灌 StatePool, 但不直接生成答案。
5. 反例和 tombstone 能松动旧的高把握路径。

