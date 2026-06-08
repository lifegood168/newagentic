# 总架构

> 本文档定义平台的最终形态、核心概念、分层规则。所有后续设计和实现以此为基准。
> 最近一次修订：补充 Session State / 区分 Knowledge vs Memory / 完整 Step schema / 登记未实现能力。

---

## 一、平台定位

**这是什么**：平安健康内部使用的企业级 Agentic 平台，承接多个业务线的 Agent 落地（销售助理、研发问答、HR、医疗辅助等）。

**核心命题**：让各业务线在 1-2 周内上线一个生产可用 Agent，**而不是每次都从零写代码**。

**边界**：
- ✅ 平台提供：Agent 运行时、工具/技能注册、知识检索、模型网关、审计治理、Session 业务态管理
- ❌ 平台不做：具体业务 Agent 的 Prompt 和业务 Tool（以 YAML / 业务 Tool 入仓，但不进核心引擎）
- ❌ 平台不做：C 端高并发场景（V1-V2）；首期面向 B 端内部业务

**单租户假设（V1-V2）**：纯内部使用，多租户简化为"业务线 metadata 打标"，不做硬隔离。

---

## 二、分层架构

```
┌────────────────────────────────────────────────────────────────┐
│  接入层    OpenAPI (SSE) / Console UI / SDK                     │
├────────────────────────────────────────────────────────────────┤
│  Agent Factory   Agent Template 加载 / 版本 / 配置              │
├────────────────────────────────────────────────────────────────┤
│  Agent 运行时    ReAct Loop（四阶段）/ Tool 调度 / Subagent      │
│                  Session 业务态 / Run / Step 事件溯源            │
├────────────────────────────────────────────────────────────────┤
│  能力层    Tools 注册 / Skills 注册 / MCP 接入                  │
│            （ES / KG / DB / 内部 API 都视为 Tool）              │
├────────────────────────────────────────────────────────────────┤
│  Knowledge   文档摄入 / 切片 / 嵌入 / 混合检索                  │
│  Memory      Agent 学习态（用户偏好/纠正/模式）—— Phase 3+      │
├────────────────────────────────────────────────────────────────┤
│  模型网关    OpenAI 兼容协议出口（对接公司内部网关）             │
├────────────────────────────────────────────────────────────────┤
│  平台底座    Tenant / BusinessLine / Audit / Observability      │
└────────────────────────────────────────────────────────────────┘
```

**分层规则**：
- 上层调下层，下层不依赖上层
- 跨层调用必须经过相邻层接口，禁止穿透
- 业务专属代码不进引擎层，通过 Agent Template + Tool 注入

---

## 三、核心概念

### 3.1 组织与隔离

| 概念 | 定义 |
|------|------|
| **Tenant** | 顶层隔离单位（V1 默认单租户：平安健康） |
| **BusinessLine** | 业务线（销售/研发/HR/医疗…），所有 Run / Step / Tool 调用必带 |

### 3.2 Agent 定义与实例

| 概念 | 定义 |
|------|------|
| **Agent Template** | Agent 的可复用定义（YAML 源 + DB 快照），含版本号 |
| **Agent Instance** | Template 绑定到某 BusinessLine 的具体启用 |

### 3.3 执行单元

| 概念 | 定义 |
|------|------|
| **Session** | 一段连续用户会话；**持有业务态 `state_json`**（current_client / current_plan / 已确认约束等） |
| **Run** | 一次完整执行（user input → final reply） |
| **Step** | Run 内的一次模型调用 / 工具调用 / Subagent 调用（事件溯源单元） |

### 3.4 能力

| 概念 | 定义 |
|------|------|
| **Tool** | 原子能力（函数级），有 JSONSchema；接收 ToolContext（tenant/business_line/user/run_id） |
| **Skill** | 任务级方法论（Prompt 模板 + 一组 Tool）—— Phase 2 引入 |
| **MCP Server** | 外部能力提供方 —— Phase 2 引入 |

### 3.5 数据资产（**注意区分**）

| 概念 | 来源 | 写入 | 隔离 | 上线 |
|------|------|------|------|------|
| **Knowledge** | 上传的文档 / 产品库 / KG | 人工 / 批处理 | 业务线 | Phase 1 |
| **Memory** | Agent 运行时自动学习（偏好 / 纠正 / 工作流模式） | Agent / Dreaming 后台 | 用户 + 业务线 | **Phase 3+** |

> 这两件事**架构上必须分开**，避免重蹈"被调用但未定义"的覆辙。Phase 1-2 不做 Memory，所有"记忆"需求一律走 Knowledge 或 Session.state_json。

---

## 四、数据模型（V1 必备）

### 4.1 组织表

```
tenants(id, name, created_at)
business_lines(id, tenant_id, code, name)
```

### 4.2 Agent 定义表

```
agent_templates(
  id, code, version, yaml_source, status, schema_version,
  created_at, created_by
)
agent_instances(
  id, template_id, business_line_id, config_override_json
)
```

### 4.3 执行表（核心）

```
sessions(
  id, agent_instance_id, user_id, business_line_id,
  state_json,           -- 业务态：current_client / current_plan / 约束
  started_at, last_active_at, status
)

runs(
  id, session_id, agent_instance_id, business_line_id,
  input, output, status, error,
  started_at, ended_at
)

steps(
  id, run_id, seq,
  parent_step_id,       -- Subagent 调用嵌套
  type,                 -- model_call / tool_call / subagent_call / system / interrupt
  status,               -- pending / running / ok / failed / aborted / awaiting_human
  business_line_id,
  -- 模型 step 字段
  model_id, prompt_tokens, completion_tokens, cost_tokens,
  -- 工具 step 字段
  tool_name, tool_args_hash,
  -- 通用
  payload_json,         -- 完整 IO（模型 messages / 工具 input+output）
  error_json,
  started_at, ended_at
)
```

### 4.4 能力与审计

```
tools(id, code, version, schema_json, source)       -- 元数据
audit_events(id, run_id, step_id, kind, payload_json, created_at)  -- Phase 2 扩展
```

**关键约束**：
- `steps` 表是事件流，Run 状态由 Steps 派生
- 所有业务表带 `business_line_id`（V1 不强校验，V2 校验）
- `payload_json` 全量落，禁止"为节省空间裁剪"
- `tool_args_hash` 用于参数哈希循环检测

---

## 五、Tool 调用上下文（**容易漏的关键点**）

每次 Tool 调用必须传入 `ToolContext`：

```
ToolContext {
  tenant_id, business_line_id, user_id,
  run_id, step_id, session_id,
  trace_id,           -- 用于跨服务 trace
  permissions,        -- 当前 Agent 在该业务线下的权限列表
}
```

业务 Tool（如 KG / ES）用此上下文做下游鉴权与审计。**禁止裸调外部系统**。

---

## 六、6 条强约束

> 违反任意一条 = 架构性错误。

1. **Agent = 配置不是代码**
   新 Agent 上线 = 新 YAML；若需改引擎代码 = 平台缺能力 → 往能力层补。

2. **所有 LLM 调用经模型网关**
   业务代码出现 `openai.Client(...)` / `anthropic.Client(...)` = 违规。

3. **Run / Step 全量事件溯源**
   每个 Step 一条事件落库，模型 IO / 工具 IO 全留痕。

4. **能力层是平台资产**
   Tool / Skill 必须可被多个 Agent 引用；业务专属 Tool 也走平台注册流程。

5. **配置化优先于框架化**
   引擎只保证 ReAct Loop + Tool 调用 + Subagent 委派三个原语，Agent 怎么用是 Template 的事。

6. **Knowledge ≠ Memory，不混用**
   静态文档库走 Knowledge；Agent 自学走 Memory（Phase 3+）。短期上下文需求走 `sessions.state_json`，不要新造概念。

---

## 七、ReAct 循环（四阶段，**Phase 0 即按此实现**）

```
PRE-FLIGHT  → 中断检查 / 预算检查 / 循环检测（参数哈希）
   ↓
THOUGHT     → 组装消息 → 调用模型（流式）
   ↓
DECISION    → 解析 finish_reason / tool_calls
   ↓
ACTION      → 工具调用（并行 / 顺序）/ Subagent 委派
   ↓
OBSERVATION → 结果追加 / Step 收尾 / 成本汇总
   ↓
回到 PRE-FLIGHT 或退出
```

**Phase 0 实现**：四阶段必须各自独立函数；中间件钩子可空但必须留位置。

---

## 八、技术栈

- **语言**：Python 3.11+
- **Web**：FastAPI + uvicorn
- **DB**：SQLite（WAL）+ FTS5 + sqlite-vec（V1）→ Postgres + pgvector（Phase 3）
- **模型协议**：OpenAI 兼容（对接公司内部网关）
- **流式**：SSE
- **包管理**：uv
- **类型**：mypy --strict
- **测试**：pytest + MockModelProvider（含录制重放）
- **部署**：Docker（Phase 0 起）+ K8s（Phase 3 起）

---

## 九、已登记但未实现的能力（架构占位）

> 这些能力**架构上明确支持**，但首期不实现。登记是为了避免后期"接口断裂"或"被调用未定义"。

| 能力 | 来源参考 | 实现阶段 |
|------|---------|---------|
| **Grace Call**：预算耗尽前给 LLM 一次收尾机会 | ch02 | Phase 2 |
| **双层预算**：StepBudget（单 Run）+ IterationBudget（跨 Run） | ch02 | Phase 2 |
| **五级循环检测**：当前只做"参数哈希"一级 | ch05 | Phase 2-3 |
| **人审介入点**：Step 状态 `awaiting_human`（schema 预留） | 销售助理 | Phase 2 |
| **长期记忆三层存储**：Working / Short-term / Long-term + Dreaming | ch07 | Phase 3+ |
| **AsyncSubagent 生命周期**：start / check / cancel / list | gitsum 05 | Phase 2 |
| **Audit Collector**：10 类，接入 Step 事件流 | ch08 | Phase 2 |
| **跨 Agent 协作**：Agent A 把 Agent B 当 Subagent | 自研 | Phase 3 |

---

## 十、演进路径（量化触发）

```
V1 (Phase 0-1)：Python 单体 + SQLite，单进程
V1.5 (Phase 2)：Worker 拆出独立进程；SQLite → Postgres
V2 (Phase 3)：业务线硬隔离 + 配额 + 灰度 + 审计完整版
V3 (Phase 4+)：Go 接入层；C 端 Agent
```

**升级触发指标（不是拍脑袋）**：

| 触发 | 指标 |
|------|------|
| SQLite → Postgres | 并发写冲突 > 1%/min，或部署多实例 |
| 拆 Worker 进程 | 单 Run > 60s 占比 > 5% |
| 上 Go 接入层 | 单实例长连接 > 1000，或接入层 CPU 持续 > 70% |
| 上 C 端 | Phase 0-3 全部完成且稳定 6 周 |

---

## 十一、目录结构（最终态）

```
/app
  /api          FastAPI router（仅参数校验 + service 调用）
  /runtime      ReAct loop（四阶段）/ Step 调度 / 事件发射
  /gateway      模型网关（OpenAI 兼容 client）
  /tools        Tool 基类 + 注册中心 + 内置工具 + ToolContext
  /skills       Skill 注册（Phase 2）
  /mcp          MCP client（Phase 2）
  /knowledge    文档摄入 / 切片 / 嵌入 / 检索
  /memory       Agent 学习态（Phase 3+）
  /tenancy      Tenant / BusinessLine 校验
  /audit        审计事件
  /storage      Repository 抽象 + SQLite 实现
  /factory      Agent Template 加载器
  /sessions     Session 业务态读写
  /internal     共享库（id / log / config / redact / shutdown）

/agents         Agent Template YAML 文件（git 管理）
/tests          pytest（镜像 app/ 结构）
/deploy         Dockerfile / docker-compose / Helm chart（Phase 3）
/docs           本目录
/scripts        本地工具脚本
```
