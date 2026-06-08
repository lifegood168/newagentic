# 验证集

> 每个阶段的"完成定义"。验证不过不进下一阶段。
> 验证形式：自动化测试优先 + 关键场景手动验证。
> 最近一次修订：补 Docker / 优雅关闭 / Schema 完整性 / Session 跨 Run / 六用例对齐。

---

## Phase 0：POC 框架验证

### V0.1 基础设施

| # | 场景 | 验证方式 | 通过标准 |
|---|------|----------|----------|
| V0.1.1 | 服务启动 | `make dev` | uvicorn 启动无报错，日志 JSON 格式 |
| V0.1.2 | 健康检查 | `curl /healthz` / `/readyz` | 返回 200 |
| V0.1.3 | OpenAPI 文档 | 访问 `/docs` | Swagger UI 可见所有 endpoint |
| V0.1.4 | DB 初始化 | `python -m app.storage.init` | SQLite 文件生成，表结构与 `0001_init.sql` 一致 |
| V0.1.5 | mypy / ruff | `make typecheck && make lint` | 全绿 |
| V0.1.6 | **Schema 完整性** | `pragma table_info(steps)` | 字段含 parent_step_id / cost_tokens / model_id / tool_name / tool_args_hash / business_line_id |

### V0.2 容器化与优雅关闭（**审计教训补充**）

| # | 场景 | 验证方式 | 通过标准 |
|---|------|----------|----------|
| V0.2.1 | 镜像构建 | `make docker-up` | 容器启动成功，`curl /healthz` 返回 200 |
| V0.2.2 | SIGTERM 优雅关闭 | 容器跑一个长 Run 中 `docker stop` | 当前 Run 安全收尾或标为 `aborted`，进程退出码正常 |
| V0.2.3 | 重启后状态恢复 | 容器重启 | 进行中 Run 状态保留为 `running`，可 resume |

### V0.3 Agent Template

| # | 场景 | 验证方式 | 通过标准 |
|---|------|----------|----------|
| V0.3.1 | YAML 加载 | 启动时读 `/agents/*.yaml` | `GET /templates` 返回 demo Agent |
| V0.3.2 | YAML schema 失败 | 故意写错字段 | 启动失败，错误信息指出字段路径 |
| V0.3.3 | 版本变更 | 修改 YAML 重启 | DB 中 Template 版本号递增 |
| V0.3.4 | schema_version | 缺失 schema_version | 启动失败 |

### V0.4 ReAct Loop 四阶段

| # | 场景 | 验证方式 | 通过标准 |
|---|------|----------|----------|
| V0.4.1 | 四阶段独立 | 代码结构检查 | 存在 `_pre_flight` / `_thought` / `_decision` / `_action` / `_observation` 五个函数 |
| V0.4.2 | 创建 Run | `POST /runs {template:demo, input:"echo hello"}` | 返回 run_id，状态 `running` |
| V0.4.3 | SSE 事件流 schema | `curl /runs/{id}/events` | 事件类型符合 `app/api/sse_schema.py` 定义 |
| V0.4.4 | Run 结果 | `GET /runs/{id}` | 状态 `completed`，output 含 "hello"，steps 数 ≥ 3 |
| V0.4.5 | Step 字段完整 | 查 SQLite | parent_step_id / cost_tokens / model_id / tool_name 等字段按场景填充 |
| V0.4.6 | 模型 IO 全量落库 | 查 `steps.payload_json` | model_call 含完整 messages + response，无裁剪 |
| V0.4.7 | **Tool 并行** | demo Agent 模型一次返回 2 个 tool_call | 两个 Tool 并发执行，时间 ≈ max(t1, t2) 而非 t1+t2 |

### V0.5 中断恢复（事件溯源核心）

| # | 场景 | 验证方式 | 通过标准 |
|---|------|----------|----------|
| V0.5.1 | 服务重启 | Run 进行中 kill 进程，重启 | Run 状态保留 |
| V0.5.2 | 续跑 | `POST /runs/{id}/resume` | 从最后一个 Step 继续，新 Step seq 接续 |
| V0.5.3 | 重放 | `GET /runs/{id}` | 所有 Step 完整可读 |

### V0.6 预算与循环检测

| # | 场景 | 验证方式 | 通过标准 |
|---|------|----------|----------|
| V0.6.1 | 步数超限 | demo Agent 设 max_steps=3，模型一直调 Tool | Run 状态 `aborted`，error 含 "budget exceeded" |
| V0.6.2 | **参数哈希循环** | Mock 模型重复返回相同 tool_call | 第 N 次（N≤5）触发 abort，error 含 "loop detected" |
| V0.6.3 | Tool 异常 | http_get 调不存在的 URL | Step 状态 `failed`，error_json 有 stack |
| V0.6.4 | 模型 5xx | MockProvider 返回 500 | 重试 3 次后失败 |

### V0.7 ToolContext

| # | 场景 | 通过标准 |
|---|------|----------|
| V0.7.1 | Tool 执行时收到完整 ctx | `echo` Tool 把 ctx 回显，断言 tenant_id / business_line_id / run_id / step_id 都有 |

### V0.8 自动化测试

| # | 场景 | 通过标准 |
|---|------|----------|
| V0.8.1 | `pytest` 全跑 | 全绿，覆盖率 ≥ 60% |
| V0.8.2 | 集成测试套件 | demo_agent / resume / loop_detect / parallel_tools 全绿 |

**Phase 0 必须 V0.1 - V0.8 全部 ✅。**

---

## Phase 1：销售助理（产品问答 + 找匹配产品）

### V1.1 Session 业务态（**新增，关键**）

| # | 场景 | 验证方式 | 通过标准 |
|---|------|----------|----------|
| V1.1.1 | 创建 Session | `POST /sessions` | 返回 session_id，state_json 默认空 |
| V1.1.2 | 写入业务态 | `PATCH /sessions/{id}/state {current_client: {...}}` | 合并成功，再 GET 可见 |
| V1.1.3 | 跨 Run 保持 | 同一 session 跑 Run A → 写入 state → Run B 启动 | Run B 的 prompt 中能看到 current_client |
| V1.1.4 | 多 Run 并发 | 同 session 并发两个 Run | state 写入串行化，无丢失 |

### V1.2 Knowledge 中台

| # | 场景 | 验证方式 | 通过标准 |
|---|------|----------|----------|
| V1.2.1 | 文档摄入 | `ingest ./test_docs/ --business-line=sales` | chunks 记录正确，向量已生成，business_line_id=sales |
| V1.2.2 | 切片合理性 | 检查 chunk 大小 | 200-500 token，不切断句子 |
| V1.2.3 | 业务线隔离 | 注入 sales + hr 两批文档，sales 检索 | 只返回 sales 文档 |
| V1.2.4 | 混合检索 | 同 query 跑 BM25 / 向量 / 混合 | 混合 MRR ≥ 单一方法 |

### V1.3 业务 Tool

| # | 场景 | 验证方式 | 通过标准 |
|---|------|----------|----------|
| V1.3.1 | KG / ES Tool 调通 | mock 外部 + 真实调用各一次 | 返回结构化结果 |
| V1.3.2 | **ToolContext 传递** | Tool 内打日志 | 看到 tenant/business_line/user/run_id |
| V1.3.3 | **双源融合策略** | 同 query 走 dual_source | 排序合理，KG-only / ES-only 兜底场景命中 |
| V1.3.4 | Tool 鉴权失败 | mock KG 返回 403 | Step `failed`，error 清晰 |

### V1.4 销售助理用例（**对齐方案六用例**）

| # | 用例 | 通过标准 |
|---|------|----------|
| V1.4.1 | 产品问答："家庭医生是什么服务？" | 引用 KG + 产品库，回答准确，附引用来源 |
| V1.4.2 | 产品问答："团检包含哪些项目？" | 引用 ES 产品表，列出包项目 |
| V1.4.3 | 产品问答："信创合规支持吗？" | 命中合规文档 |
| V1.4.4 | 找匹配产品："2000 人央企，预算 500 万" | 返回 top-K 产品组合（Session 写入约束），可解释 |
| V1.4.5 | 找匹配产品 + 上下文延续 | 上一轮已定 current_client，本轮"换成 1000 人" | 复用 Session.current_client，只改人数 |

**至少 V1.4.1 / V1.4.4 / V1.4.5 必须过**。

### V1.5 平台抽象验证（**关键**）

| # | 场景 | 通过标准 |
|---|------|----------|
| V1.5.1 | 引擎层无业务残留 | `grep -rn "sales\|product\|client" app/runtime app/gateway app/storage app/factory` | 零命中 |
| V1.5.2 | 新增 HR 占位 Agent | 只增 `agents/hr_qa.yaml` + 引用现有 Tool，不改引擎 | HR Agent 可启动并响应 |
| V1.5.3 | 模型切换 | 改 YAML 一行换模型 | 重启生效，新 Run 用新模型（Step.model_id 体现） |

### V1.6 人审介入占位

| # | 场景 | 通过标准 |
|---|------|----------|
| V1.6.1 | 构造 interrupt Step | Mock 路径触发 | Step 状态 `awaiting_human`，Run 暂停 |
| V1.6.2 | resume with human_input | `POST /runs/{id}/resume {human_input:"approve"}` | Run 继续，新 Step seq 接续 |

**V1.5 不过 = Phase 1 不算完成**（说明平台变成了应用）。

---

## Phase 2：Skill / Subagent / 长任务 / 审计

### V2.1 Skill 系统

| # | 场景 | 通过标准 |
|---|------|----------|
| V2.1.1 | Skill Markdown 加载 | Console 看到所有 Skill |
| V2.1.2 | Agent 调用 Skill | Run trace 能看到 Skill 触发 + 内部 Tool |
| V2.1.3 | Skill 复用 | 同一 Skill 被 2 个 Agent 引用，互不影响 |

### V2.2 Subagent

| # | 场景 | 通过标准 |
|---|------|----------|
| V2.2.1 | 同步 Subagent 委派 | 子 Run 创建，独立 messages，共享 Session |
| V2.2.2 | 异步 Subagent start/check/cancel | 4 个生命周期 API 全通 |
| V2.2.3 | 嵌套上限 | 超限被拒 |
| V2.2.4 | 子 Run 失败 | 主 Run 收到错误，不污染 |

### V2.3 Grace Call + 双层预算

| # | 场景 | 通过标准 |
|---|------|----------|
| V2.3.1 | StepBudget 触发 Grace | 80% 时模型收到"请收尾"指令，输出最终答案 |
| V2.3.2 | IterationBudget 跨 Run | 累计达到上限，新 Run 被拒 |

### V2.4 五级循环检测

| # | 场景 | 通过标准 |
|---|------|----------|
| V2.4.1 | L2 工具序列模式 | A→B→A→B 触发 |
| V2.4.2 | L3 内容相似 | 连续 5 步语义相似度 > 阈值触发 |
| V2.4.3 | L4 全局断路器 | 失败 Step 比例超限触发 |

### V2.5 业务线隔离

| # | 场景 | 通过标准 |
|---|------|----------|
| V2.5.1 | 跨业务线越权 | Repository 拒绝 + 审计 |
| V2.5.2 | 中间件提取 business_line | 所有 Run / Step 自动带标 |

### V2.6 配额

| # | 场景 | 通过标准 |
|---|------|----------|
| V2.6.1 | 用户限流 | 超限 429 |
| V2.6.2 | 业务线 Token 配额 | 月度超限告警 + 拒绝 |

### V2.7 Console UI

| # | 场景 | 通过标准 |
|---|------|----------|
| V2.7.1 | Run 列表 | 分页 / 过滤业务线 |
| V2.7.2 | Step trace | 时间轴可读，模型 IO 可展开 |
| V2.7.3 | 成本统计 | 按业务线 / Agent / 时间聚合 |

### V2.8 3 Agent 同跑 + 长任务

| # | 场景 | 通过标准 |
|---|------|----------|
| V2.8.1 | 销售 + HR + 研发同时在线 | 互不影响 |
| V2.8.2 | 销售 solution_writer Subagent 跑长任务 | 异步 start → check → 完成 |
| V2.8.3 | 并发压测 | 3 Agent × 10 并发 Run 持续 10 分钟无错 |

---

## Phase 3 / 4 验证（待细化）

到时再补，原则相同：每个能力点必须有具体的可验证场景。

---

## 验证流程约定

1. 每完成 todolist 一组，运行对应验证集
2. 验证失败 → 修复 → 重跑，不补丁绕过
3. Phase 退出时，验证集结果归档到 `docs/validation-results/phase-N.md`
4. 不变量验证（见 todolist 末尾）每 PR 都要跑
