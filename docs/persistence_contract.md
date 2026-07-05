# APV3.0test 持久化契约

日期: 2026-06-16

## 目标

持久化不是新算法, 而是把同一套 AP-native 运行本体落到磁盘后仍能等价恢复。

APV3.0test 暂用 SQLite。默认总预算 10G, 但运行本体和白箱审计必须分库。

## 两库分离

### runtime ontology db

运行唯一依赖。删除 audit db 后仍应能正常启动。

必须保存:
- state snapshots 的运行投影。
- explicit transitions / successor edges。
- `OnlineEmbeddingStore` export state。
- `ActionOutcomeMemory` snapshot。
- `ParadigmSA` columns / support / conf / provenance。
- `PerceptPrototype` codebook。
- 必要的可重建索引元信息。

禁止保存:
- per-candidate score breakdown 全量历史。
- DP 中间矩阵全量历史。
- 长期白箱 tick trace。
- 展示页材料。

### audit db

只服务审查和观测台。可删、可限额、可滚动回收。

可保存:
- score breakdown。
- explanation pass trace。
- DP 对齐中间态。
- 最近 tick 白箱 trace。
- 测试 receipt。

## 预算与淘汰

默认:

```text
memory_db_budget_bytes = 10 * 1024 * 1024 * 1024
forgetting_enabled = true
```

淘汰顺序:

1. audit db 中最旧 trace。
2. audit db 中可重建中间态。
3. runtime db 中低权重、低调用、可重建索引。
4. runtime db 中非核心普通经历。

不得自动淘汰:
- 基础范式。
- 已验证技能核心。
- 重要奖惩后果。
- 数学基础记忆。
- `OnlineEmbeddingStore` promoted token state。
- `ParadigmSA` 高 support 核心。

## 等价性门

导出再恢复后必须比较:
- Bn top-k。
- Cn successor evidence。
- ParadigmSA recall/fill。
- OnlineEmbeddingStore learned vectors / transitions。
- ActionOutcomeMemory drive bias。
- draft token / commit 清空。

通过前不能宣称自由中文对话底座完成。

## 审计缺失行为

如果 audit db 缺失:

- runtime 不报错。
- 不降级为规则回复。
- 不重新导入审计材料。
- 只显示“audit unavailable”。

