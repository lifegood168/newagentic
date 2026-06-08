# TODO List（按阶段勾选）

> 颗粒度：单项 0.5-2 天工作量。完成后打 `[x]`。
> 文件路径为占位，最终路径以实际为准。
> 最近一次修订：Phase 0 补 Docker / 优雅关闭 / 四阶段循环 / 参数哈希检测 / 完整 Step schema；Phase 1 补 Session State / Tool 上下文 / 双源融合 / Embedding 决策。

---

## Phase 0：POC 框架

### P0.1 工程脚手架

- [ ] 初始化 `pyproject.toml`（uv 管理，Python 3.11+）
- [ ] 配置 `ruff` + `mypy --strict`
- [ ] `Makefile`：`make dev` / `make test` / `make lint` / `make typecheck` / `make docker-up`
- [ ] `.env.example` + `app/internal/config.py`（pydantic-settings）
- [ ] 基础 logging（structlog，JSON 输出）
- [ ] ID 生成（ULID）
- [ ] **`app/internal/shutdown.py`**：SIGTERM/SIGINT 信号处理，正在跑的 Run 安全收尾

### P0.2 存储层（**完整 schema，不留隐患**）

- [ ] `app/storage/sqlite.py`：连接管理（aiosqlite，WAL 模式）
- [ ] `app/storage/migrations/0001_init.sql`：建表 SQL，**完整字段**：
  - `tenants` / `business_lines` / `agent_templates` / `agent_instances`
  - `sessions(id, agent_instance_id, user_id, business_line_id, state_json, started_at, last_active_at, status)`
  - `runs(id, session_id, agent_instance_id, business_line_id, input, output, status, error, started_at, ended_at)`
  - `steps(id, run_id, seq, parent_step_id, type, status, business_line_id, model_id, prompt_tokens, completion_tokens, cost_tokens, tool_name, tool_args_hash, payload_json, error_json, started_at, ended_at)`
  - `tools(id, code, version, schema_json, source)`
  - `audit_events(id, run_id, step_id, kind, payload_json, created_at)` — 表先建，逻辑 Phase 2
- [ ] `app/storage/repository.py`：Repository 抽象基类
- [ ] `app/storage/runs.py` / `steps.py` / `sessions.py` / `templates.py` Repository 实现
- [ ] DB 初始化命令：`python -m app.storage.init`
- [ ] 单元测试：每个 Repository CRUD + 字段完整性

### P0.3 模型网关

- [ ] `app/gateway/types.py`：统一消息类型（ChatMessage / ToolCall / StreamChunk / Usage）
- [ ] `app/gateway/openai_compat.py`：OpenAI 兼容协议 client（httpx async）
- [ ] `app/gateway/router.py`：按 Agent Template 配置选模型
- [ ] `app/gateway/mock.py`：MockModelProvider（**支持预设响应序列 + 录制重放**）
- [ ] 单元测试：流式 / 非流式 / 工具调用 / 错误重试 / Usage 字段透传

### P0.4 Tool 系统（**带 ToolContext**）

- [ ] `app/tools/context.py`：`ToolContext` 数据类（tenant/business_line/user/run_id/step_id/session_id/trace_id/permissions）
- [ ] `app/tools/base.py`：Tool 基类（`async execute(ctx: ToolContext, args: dict) -> ToolResult`）
- [ ] `app/tools/registry.py`：Tool 注册中心（启动扫描注册）
- [ ] `app/tools/builtin/echo.py`：demo Tool
- [ ] `app/tools/builtin/http_get.py`：demo Tool
- [ ] 单元测试：注册 / 调用 / schema 校验 / ToolContext 注入

### P0.5 Agent Factory

- [ ] `app/factory/yaml_loader.py`：YAML → AgentTemplate 对象
- [ ] `app/factory/schema.py`：YAML schema 校验（pydantic）+ `schema_version` 字段
- [ ] `agents/demo.yaml`：最简 Agent（system prompt + echo + http_get）
- [ ] 启动时加载 `/agents/*.yaml` 写入 DB（version 自增）
- [ ] 单元测试：YAML 加载 / schema 校验失败场景 / 版本号

### P0.6 Agent 运行时（**四阶段 + 循环检测**）

- [ ] `app/runtime/run.py`：Run 生命周期管理
- [ ] `app/runtime/react_loop.py`：四阶段循环主体
  - [ ] `_pre_flight()`：预算检查 / 中断检查 / **循环检测**
  - [ ] `_thought()`：组装 messages → 调模型
  - [ ] `_decision()`：解析 finish_reason / tool_calls
  - [ ] `_action()`：执行 Tool（**支持并行**：同 batch 多 Tool 并发）
  - [ ] `_observation()`：追加结果 / 收尾
- [ ] `app/runtime/loop_detect.py`：**参数哈希循环检测**（同 tool_name + 同 args_hash 连续 N 次 → abort）
- [ ] `app/runtime/budget.py`：步数预算（max_steps）
- [ ] `app/runtime/events.py`：Step 事件发射器（写 DB + push SSE）
- [ ] 中断恢复：根据 Run id + Steps 重建状态
- [ ] 集成测试：完整 Run 走完 / 中断后恢复 / 循环检测触发 / 预算超限

### P0.7 API 层（**规范化 SSE schema**）

- [ ] `app/api/main.py`：FastAPI app 入口
- [ ] `POST /runs`：创建 Run，返回 run_id
- [ ] `GET /runs/{run_id}`：查 Run 状态 + Steps 列表
- [ ] `GET /runs/{run_id}/events` (SSE)：实时事件流
- [ ] `GET /healthz` / `GET /readyz`：健康检查
- [ ] `GET /templates`：列出可用 Agent Template
- [ ] **SSE 事件 schema 规范**（写进 `app/api/sse_schema.py`）：
  - `step.start { step_id, type, seq }`
  - `model.delta { step_id, text }`
  - `model.tool_call { step_id, tool_name, args }`
  - `tool.start / tool.end { step_id, tool_name, result | error }`
  - `step.end { step_id, status }`
  - `run.end { run_id, status, error? }`
- [ ] OpenAPI 文档自动生成

### P0.8 测试与文档

- [ ] `tests/integration/test_demo_agent.py`：端到端跑通
- [ ] `tests/integration/test_resume.py`：中断恢复
- [ ] `tests/integration/test_loop_detect.py`：循环检测
- [ ] `tests/integration/test_parallel_tools.py`：Tool 并行调用
- [ ] `README.md`（项目根）：5 分钟启动指南
- [ ] `make demo`：一键启动 + 发起 demo Run

### P0.9 容器化与运维（**审计教训**）

- [ ] `deploy/Dockerfile`：基于 python:3.11-slim，多阶段构建
- [ ] `deploy/docker-compose.yml`：dev 一键起（含挂载 SQLite 文件）
- [ ] `deploy/.dockerignore`
- [ ] 优雅关闭：容器收到 SIGTERM → 拒绝新 Run → 等当前 Run 完成 / 超时强杀
- [ ] 资源限制示例（CPU/内存）写在 docker-compose 注释
- [ ] `make docker-up` / `make docker-down`
- [ ] 集成测试：容器启动 + `curl /healthz`

---

## Phase 1：销售助理（产品问答 + 找匹配产品）

### P1.1 Session 业务态（**新增模块**）

- [ ] `app/sessions/state.py`：Session.state_json 读写抽象（带 schema 校验）
- [ ] `POST /sessions`：创建 Session
- [ ] `PATCH /sessions/{id}/state`：合并业务态（current_client / 已确认约束）
- [ ] `GET /sessions/{id}`：查 Session + 关联 Runs
- [ ] Agent Template YAML 声明 Session 字段约定（`session_schema`）
- [ ] Runtime 在 Step 中可读 Session.state_json（注入到 prompt 或暴露给 Tool）
- [ ] 单元 + 集成测试：跨 Run 保持业务态

### P1.2 Knowledge 中台 V1

- [ ] `app/knowledge/ingest.py`：文档摄入（txt / md / pdf）
- [ ] `app/knowledge/chunker.py`：切片（按 token / 按段落，可配置）
- [ ] `app/knowledge/embedder.py`：**调用内部 LLM 网关 embedding endpoint**；fallback 配置项支持本地 bge
- [ ] `app/knowledge/store.py`：sqlite-vec + FTS5；**chunk 带 `business_line_id`**
- [ ] `app/knowledge/retriever.py`：混合检索（向量 + BM25 + MMR 重排）
- [ ] CLI：`python -m app.knowledge.ingest <dir> --business-line=sales`
- [ ] 单元测试：切片 / 嵌入 / 检索 / 业务线隔离

### P1.3 业务 Tool（**走 ToolContext**）

- [ ] `app/tools/business/kg_search.py`：对接公司 KG（带 ctx 鉴权）
- [ ] `app/tools/business/es_search.py`：对接公司 ES product_info
- [ ] `app/tools/business/kb_search.py`：调用 Knowledge 中台
- [ ] `app/tools/business/dual_source.py`：**双源融合策略**（ES + KG 加权 / 兜底规则）
- [ ] 配置：每个 Tool 的连接信息走 `app/internal/config.py`
- [ ] 单元测试：mock 外部依赖 + 双源融合排序

### P1.4 Agent Template 完善

- [ ] YAML schema 扩展：tools 引用 / model 配置 / 预算 / session_schema
- [ ] `agents/sales_qa.yaml`：销售助理"产品问答 + 找匹配产品"配置
- [ ] 业务线字段（`business_line: sales`）
- [ ] schema_version 升级流程文档

### P1.5 人审介入点（**占位**）

- [ ] Step type 支持 `interrupt`，状态 `awaiting_human`
- [ ] `POST /runs/{id}/resume` 支持 `human_input` 字段
- [ ] 集成测试：构造一个 Step → awaiting_human → resume → 继续
- [ ] 完整审批工作流推迟到 Phase 2

### P1.6 流式增强

- [ ] SSE 客户端断开重连测试
- [ ] 事件按 Step 顺序保证（防乱序）

### P1.7 验证（对齐六大用例）

- [ ] 真实跑"产品问答"3+ 个 query，结果有据可查（引用 KG / ES）
- [ ] 真实跑"找匹配产品"3+ 个 query
- [ ] `grep -rn "sales" app/runtime app/gateway app/storage` 零命中
- [ ] 新增 HR 占位 Agent（`agents/hr_qa.yaml`），不改引擎代码

---

## Phase 2：Skill / Subagent / 长任务 / 审计

### P2.1 Skill 系统

- [ ] Skill 数据模型 + DB 表
- [ ] Skill Markdown 解析器
- [ ] Skill → Prompt 模板渲染
- [ ] Agent Template 引用 Skill
- [ ] 5 个示例 Skill（参考销售助理方案）

### P2.2 Subagent（同步 + 异步）

- [ ] 同步 Subagent：主 Agent 委派 → 子 Run 独立上下文（共享 Session 但隔离 messages）
- [ ] 异步 Subagent 生命周期：start / check / cancel / list（参考 gitsum 05）
- [ ] 嵌套深度限制
- [ ] 集成测试：嵌套 / 取消 / 失败传播

### P2.3 业务线硬隔离

- [ ] Repository 层强校验 `business_line_id`
- [ ] 中间件：从请求上下文提取
- [ ] 越权告警 + 拒绝
- [ ] 安全测试

### P2.4 Grace Call + 双层预算

- [ ] StepBudget（单 Run 步数）
- [ ] IterationBudget（跨 Run 累计）
- [ ] Grace Call：达到 80% 时给模型一次"收尾"机会

### P2.5 五级循环检测

- [ ] L1：参数哈希（已有）
- [ ] L2：工具序列模式（A→B→A→B）
- [ ] L3：内容相似度（连续 N 步输出向量相似）
- [ ] L4：全局断路器（异常 Step 比例 > 阈值）
- [ ] L5：压缩后保护

### P2.6 Audit Collector

- [ ] 10 类 Collector 定义
- [ ] 接入 Step 事件流
- [ ] 审计查询 API

### P2.7 Console UI（只读）

- [ ] 起一个最小前端（Next.js / SvelteKit）
- [ ] Run 列表 / Step trace / 成本统计
- [ ] Agent Template 列表与版本

### P2.8 配额与计费统计

- [ ] 三级配额（业务线 / Agent / 用户）
- [ ] Token 用量按业务线聚合
- [ ] 超限拒绝逻辑

### P2.9 Worker 进程拆分

- [ ] 同代码不同入口（`arq` 或 `apscheduler`）
- [ ] 长跑任务从 Web 路径切到 Worker
- [ ] AsyncSubagent 走 Worker

### P2.10 人审介入完整工作流

- [ ] 高风险 Tool 标注 `require_human_approval`
- [ ] Step 阻断 → 推送审批（IM/邮件）→ 接收审批结果 → resume
- [ ] 审批超时策略

---

## Phase 3：规模化（不展开）

- [ ] Postgres + pgvector 切换（只改 storage 层）
- [ ] OpenTelemetry trace
- [ ] Prompt / 工具集版本化 + 灰度
- [ ] Secret 管理对接
- [ ] PII 脱敏
- [ ] 评测平台（行为回归 + 红蓝对抗）
- [ ] 跨 Agent 协作
- [ ] **Memory 三层存储**（Working / Short-term / Long-term + Dreaming）

---

## 不变量自检（每 PR 必查）

- [ ] 新 Agent 没有改引擎代码？
- [ ] LLM 调用走的是 `/gateway`？
- [ ] Step 事件正常落库（payload 不裁剪）？
- [ ] SQL 走 Repository 抽象？
- [ ] 没有 SQLite 独有语法（除非标注）？
- [ ] Tool 调用带 ToolContext？
- [ ] Knowledge / Memory / Session.state_json 三者用途未混淆？
