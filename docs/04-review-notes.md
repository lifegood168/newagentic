# 评审笔记

> 本文档记录对 `00-architecture.md` / `01-phases.md` / `02-todolist.md` / `03-validation.md` 首版的评审过程与修订决策。保留这份记录是为了：
> 1. 让后续 Claude / 协作者看到决策过程，不会重蹈覆辙
> 2. 形成可追溯的架构演进史
> 3. 评审本身也是验证集的一部分（避免"架构图上的完美系统"）

---

## 一、评审参考资料

- `/Users/life/WorkBuddy/2026-06-08-15-33-34/agentic-platform-design/` 8 章设计 + audit-synthesis 审计综合
- `/Users/life/workspace/gitsum/docs/` DeepAgents / DeerFlow / OpenClaw 框架对比 + 销售助理方案

---

## 二、首版评分（修订前）

| 维度 | 评分 | 备注 |
|------|------|------|
| 平台 vs 应用 边界 | 8/10 | 5 条强约束 + V1.4 验证方向正确 |
| 阶段划分合理性 | 7/10 | Phase 0 砍得对，但 Phase 1 跑不通真实业务 |
| 与销售助理方案吻合 | 5/10 | 缺 Session State，6 用例没对齐 |
| 与 ch02/ch05/ch07 吸收 | 4/10 | 三阶段循环 / 循环检测 / 长期记忆 全缺 |
| 部署 / 运维（审计 P0） | 3/10 | 重复"重内核轻运维"的错 |
| 可立即落地 | 7/10 | todolist 颗粒度 OK，Step schema 不全 |

---

## 三、识别的关键问题

### 3.1 重复了审计报告 P0 的错（部署运维缺失）

审计综合报告明确指出"8 章设计无一字涉及部署/测试/可观测"。首版 docs 把这件事推到 Phase 3，**违反同一教训**。

**修订**：Phase 0 新增 P0.9 容器化与运维（Docker / docker-compose / SIGTERM 优雅关闭），V0.2 加对应验证。

### 3.2 Step schema 不完整（事件溯源地基风险）

首版 `steps` 表只有基础字段。`parent_step_id` / `cost_tokens` / `model_id` / `tool_name` / `tool_args_hash` / `business_line_id` 全部缺失，后期补字段要全表迁移。

**修订**：Phase 0 即用完整 schema（00-architecture §4.3 / 02-todolist P0.2）。

### 3.3 Knowledge 与 Memory 概念混淆

ch07 区分了三层存储（Working / Short-term / Long-term + Dreaming），首版 docs 把"Knowledge 中台"和"记忆系统"混在一起讲。这是审计报告里 "MemoryEngine 被调用但未定义" 同款问题的前置因。

**修订**：00-architecture §3.5 显式区分：
- Knowledge = 上传的静态文档 / KG / 产品库（Phase 1）
- Memory = Agent 运行时自学（Phase 3+）
- 短期上下文需求走 `sessions.state_json`，不新造概念

### 3.4 Session State 缺失（销售助理跑不通的核心原因）

读 `B端销售助理Agent方案.md` 后意识到：销售助理在第 3 轮对话需要回忆"客户是央企/2000 人/预算 500 万"。这不在 messages 里（会被压缩），必须是平台一等公民。首版 docs 完全没有。

**修订**：Session.state_json 升级为一等概念（00 §3.3 / §4.3），Phase 1 新增 P1.1 模块 + V1.1 验证。

### 3.5 ReAct 循环没拆四阶段

ch02 明确 THOUGHT / DECISION / ACTION / OBSERVATION 四阶段（外加 PRE-FLIGHT）。首版只说"最小 ReAct loop"是黑盒。后期"加循环检测、加 Tool 鉴权、加成本统计"需要明确插入点。

**修订**：Phase 0 即按五阶段（含 PRE-FLIGHT）实现，中间件钩子可空但必须留位置。

### 3.6 循环检测最小版没要

最便宜的循环检测 = 同 Tool + 同参数哈希连续 N 次。3 行代码。Phase 0 不加，第一次模型瞎跑就烧 token。

**修订**：Phase 0 必做参数哈希一级（02 P0.6 / V0.6.2）。

### 3.7 Tool 上下文传递没设计

业务 Tool（KG / ES）需要带 tenant/business_line/user 调用下游。首版没设计 ToolContext，Tool 调用时鉴权失败。

**修订**：Phase 0 引入 `ToolContext`，每次 Tool 调用必传（02 P0.4 / V0.7）。

### 3.8 销售助理用例对齐不足

销售助理方案明确列了 6 大用例（产品问答 / 找匹配 / 服务匹配 / 方案设计 / 方案调整 / 价格合规）。首版 docs 只说"3 个 query"，过于轻量。

**修订**：Phase 1 明确对齐 6 用例（01 phases / V1.4），至少 V1.4.1 / V1.4.4 / V1.4.5 必过。

### 3.9 其他可补强（已修订）

- SSE 事件 schema 没规范 → 02 P0.7 加事件 schema 定义
- Tool 并行没提 → 02 P0.6 / V0.4.7
- YAML schema_version 缺失 → 02 P0.5 / V0.3.4
- Embedding 决策没说 → 02 P1.2 默认调内部网关 / 本地 bge fallback

### 3.10 已登记但未实现的能力（架构占位）

00-architecture §9 新增"已登记但未实现"小节，避免接口断裂：

| 能力 | 实现阶段 |
|------|---------|
| Grace Call | Phase 2 |
| 双层预算 | Phase 2 |
| 五级循环检测（当前只 L1） | Phase 2-3 |
| 人审介入完整工作流 | Phase 2 |
| 长期记忆三层存储 | Phase 3+ |
| AsyncSubagent | Phase 2 |
| Audit Collector | Phase 2 |
| 跨 Agent 协作 | Phase 3 |

---

## 四、修订后强约束（从 5 条扩到 6 条）

新增第 6 条：

> **6. Knowledge ≠ Memory，不混用**
> 静态文档库走 Knowledge；Agent 自学走 Memory（Phase 3+）。短期上下文需求走 `sessions.state_json`，不新造概念。

---

## 五、什么没改（保留首版判断）

- **路线 A（先平台后 C 端）**：保留
- **Python + SQLite 起步**：保留
- **5 条原始强约束**：保留（加第 6 条）
- **Phase 0 不绑业务**：保留
- **V1.5 平台抽象验证**（grep "sales" 引擎层零命中）：保留

---

## 六、下次评审触发点

1. Phase 0 完成时 → 跑 V0.x 全集 + 自评审一次
2. Phase 1 进行中发现"为新 Agent 改了引擎代码" → 立刻评审
3. 任何新增的"已登记未实现"能力被首次实现时 → 评审 ADR + docs
