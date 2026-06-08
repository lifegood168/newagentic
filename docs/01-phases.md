# 分步实施方案

> 团队规模：1-2 工程师。先做 POC 框架，再落业务实例。每个阶段必须有可验证产出（见 `03-validation.md`）。
> 最近一次修订：Phase 0 加入 Docker / 优雅关闭 / 四阶段 ReAct / 参数哈希循环检测；Phase 1 加入 Session State / 双源融合 / 六用例对齐。

---

## Phase 0：POC 框架（不绑业务）

**目标**：跑通"配 YAML → 启动 Agent → 与 LLM 对话 → 看到 Step 事件流 → Run 持久化 → 容器化部署"的完整链路。**不接任何真实业务 Tool**。

**范围**：
- ✅ FastAPI 服务 + SQLite 初始化（含完整 schema：parent_step_id / cost_tokens / model_id / tool_name / tool_args_hash / business_line_id）
- ✅ Agent Template YAML loader（YAML 自带 schema_version）
- ✅ 模型网关（OpenAI 兼容协议 client + 流式 + 重试）
- ✅ Run / Step 事件落库 + **规范化的 SSE 事件 schema**
- ✅ Tool 基类 + 注册中心 + **ToolContext 上下文传递**
- ✅ 2 个内置 demo Tool（`echo`、`http_get`）
- ✅ **四阶段 ReAct loop**：PRE-FLIGHT → THOUGHT → DECISION → ACTION → OBSERVATION（中间件钩子留位置）
- ✅ **参数哈希循环检测**（最简版：同 Tool + 同参数连续 N 次则中断）
- ✅ Repository 抽象（SQLite 实现）
- ✅ pytest 集成测试 + MockModelProvider（含录制重放）
- ✅ **Dockerfile + docker-compose**（dev 环境一行起）
- ✅ **优雅关闭**：SIGTERM 处理、正在跑的 Run 安全收尾

**砍掉**（推到后续阶段）：
- ❌ Console UI（用 curl / SwaggerUI 验证）
- ❌ Skill 系统、Subagent、MCP
- ❌ Knowledge 中台
- ❌ Memory（Agent 学习态）
- ❌ 多业务线硬隔离（数据库带字段但不校验）
- ❌ Grace Call、双层预算、五级循环检测（只做参数哈希一级）
- ❌ Audit Collector、灰度、计费
- ❌ 真实 ES / KG / DB Tool（Phase 1）

**人力 / 工期估算**：1-2 人 × 4-5 周

**关键产物**：
- 可启动的 FastAPI 服务（本地 `make dev` + 容器 `make docker-up`）
- `/agents/demo.yaml`：空业务、调 echo + http_get 的 demo Agent
- `pytest` 全绿，覆盖率 ≥ 60%
- `docs/03-validation.md` Phase 0 验收项全通过

---

## Phase 1：第一个业务 Agent 落地（销售助理产品问答 + 找匹配产品）

**目标**：在 POC 框架上加最少代码，让销售助理两个真实场景跑通。这一阶段是**验证平台抽象能力**的关键。

**对齐销售助理方案的六大用例**：

| # | 用例 | Phase 1 必跑 | 备注 |
|---|------|-------------|------|
| 1 | 产品问答 | ✅ | 单 Skill / 双源检索 |
| 2 | 找匹配产品 | ✅ | 双源检索 + 排序 |
| 3 | 服务匹配 + 覆盖能力 | Phase 2 | 需 fulfillment_tool |
| 4 | 方案设计 | Phase 2 | 需 CP-SAT 求解器 |
| 5 | 方案调整 | Phase 2 | 需 Session.current_plan |
| 6 | 价格 / 合规问答 | Phase 2 | 需价格口径 Skill |

**范围**：
- ✅ **Session 业务态管理**（`sessions.state_json`：current_client / 已确认约束）
  - API：`POST /sessions` / `PATCH /sessions/{id}/state` / `GET /sessions/{id}`
  - 在 Run 中可读写
- ✅ Knowledge 中台 V1：文档摄入 + 切片 + 嵌入（调用 OpenAI 兼容 embedding）+ sqlite-vec 检索
  - **业务线维度隔离**：每条 chunk 带 `business_line_id`
- ✅ 3 个业务 Tool（**走平台标准注册 + ToolContext**）：
  - `kg_search_tool`（对接公司 KG）
  - `es_search_tool`（对接公司 ES product_info）
  - `kb_search_tool`（平台自管 Knowledge）
- ✅ **双数据源融合策略**：ES + KG 加权 + 兜底，封装在 `kb_search_tool` 或独立 service
- ✅ Agent Template YAML 完整字段：system prompt / tools 引用 / model 配置 / 预算 / Session 字段声明
- ✅ `/agents/sales_qa.yaml`：销售助理"产品问答 + 找匹配产品"配置
- ✅ Run 中断恢复（基于 Step 事件流）
- ✅ **人审介入点占位**：Step type 支持 `interrupt`，状态 `awaiting_human`（不实现完整工作流，但 schema 走通）
- ✅ 业务线打标（`business_line=sales`，不做硬校验）
- ✅ **Embedding 决策**：默认调内部 LLM 网关的 embedding endpoint；若无则 fallback 本地 bge（决策记入 ADR）

**砍掉**：
- ❌ Subagent（solution_writer 等）—— Phase 2
- ❌ Skill 注册中心 —— Phase 2（Phase 1 用 system prompt 内嵌）
- ❌ CP-SAT 求解器、价格口径硬规则 —— Phase 2
- ❌ Memory 自学 —— Phase 3+

**人力 / 工期估算**：1-2 人 × 4-5 周

**关键产物**：
- 销售跑通"产品问答"和"找匹配产品"两个场景，回答有据可查
- 平台代码层面**没有"销售业务逻辑"**（grep 验证）
- Session State 跨 Run 持有客户档案

**关键验证点**：
- 写第二个 Agent（如 HR 问答）只需新增 YAML + 复用 `kb_search_tool`，不改引擎代码

---

## Phase 2：多业务线 + Skill / Subagent / 长任务 / 审计

**目标**：支持 3-5 个内部 B 端 Agent 同时跑，引擎抽象经受考验，治理可见。

**范围**：
- ✅ Skill 注册中心（Skill = Markdown + Prompt 模板 + 一组 Tool 引用）
- ✅ Subagent 同步编排 + AsyncSubagent 异步生命周期（start / check / cancel / list）
- ✅ 业务线硬隔离（Repository 层强校验 `business_line_id`）
- ✅ **Grace Call + 双层预算**
- ✅ **五级循环检测体系**（不只是参数哈希）
- ✅ Audit Collector 系统（10 类事件接入 Step 流）
- ✅ Console UI V1（只读：看 Run / Step trace / 成本统计）
- ✅ Agent Template 版本化 + 灰度（YAML 走 git，DB 存版本快照）
- ✅ 配额（业务线 / Agent / 用户三级）
- ✅ Worker 进程拆出（长跑 Agent / 异步任务）
- ✅ 完整人审介入工作流（高风险 Tool 阻断 → 审批 → 继续）

**新增 Agent 候选**：研发问答 / HR 问答 / 销售助理完整版（含 solution_writer Subagent / CP-SAT 求解 / 方案调整）

**人力 / 工期估算**：2-3 人 × 6-8 周

---

## Phase 3：规模化与生产化

**目标**：扛住 50+ Agent、内部全员可用。

**范围**：
- ✅ SQLite → Postgres + pgvector（仅 storage 层动）
- ✅ OpenTelemetry trace 端到端
- ✅ Prompt / 工具集版本化 + 灰度 + 回滚
- ✅ Secret 管理对接公司基础设施
- ✅ PII 脱敏中间件
- ✅ 评测平台（行为回归 + 红蓝对抗）
- ✅ 跨 Agent 协作
- ✅ **Memory 三层存储**（Working / Short-term / Long-term + Dreaming）

**人力 / 工期估算**：3-5 人 × 8-12 周

---

## Phase 4：C 端 Agent（医疗问答等）

**前提**：Phase 0-3 完成，平台稳定 6 周以上。

**新增挑战**：
- 首 token < 1s（Prompt 缓存 / 流式优化 / 模型预热）
- 千级并发（评估前置 Go 接入层）
- 医疗强合规（每条输出过滤 + 人审兜底 + 转人工）
- C 端容错（错误兜底话术 + 降级策略）

**这是独立项目级别的工作量**，不要和平台建设混合规划。

---

## 阶段退出准则

| 阶段 | 退出准则 |
|------|----------|
| Phase 0 | `03-validation.md` Phase 0 全部 ✅ + Docker 部署可用 |
| Phase 1 | 销售两个用例上线，平台代码零业务逻辑，Session State 跨 Run 工作 |
| Phase 2 | 3 个 Agent 在跑，新增 Agent 只改 YAML 无需改引擎 |
| Phase 3 | 通过公司安全/合规评审，月活业务用户 100+ |
| Phase 4 | （独立立项）|

---

## 不变量（任何阶段都不能违反）

- Agent = 配置，不是代码
- LLM 调用必经 `/gateway`
- Run / Step 事件全量入库（payload 不裁剪）
- 所有 SQL 走 Repository 抽象，不出现裸 SQL
- SQL 不依赖 SQLite 独有语法（除非 `# sqlite-only` 标注）
- Knowledge ≠ Memory，不互相混用
- 每个 Tool 调用必带 ToolContext
