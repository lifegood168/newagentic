# CLAUDE.md

> 本文件用于让 Claude 在进入本仓库时，立即站在正确的架构坐标系里工作。
> 它不是产品文档，也不是设计文档——只记录"Claude 不知道就会做错"的内容。

---

## 1. 项目定位

**这是什么**：面向企业的 Agentic 平台，承接客户的多种 Agent 落地需求（客服、研发助手、运营自动化、知识问答等）。

**核心能力**：Agent 编排、工具 / MCP 接入、多租户隔离、可观测与审计、模型路由。

**不是什么**：
- 不是通用 Chatbot 产品
- 不是单一 Agent 框架（如 LangGraph）的二次封装
- 不是面向 C 端的 AI 助手

> 一切判断的基线：**平台 ≠ 应用**。本仓库只做平台能力，不写具体业务 Agent。

---

## 2. 架构总览

```
┌───────────────────────────────────────────────┐
│  接入层    OpenAPI / SDK / Console UI         │
├───────────────────────────────────────────────┤
│  Agent 运行时    Planner / Executor / Memory  │
├───────────────────────────────────────────────┤
│  能力层    Tools / MCP / Knowledge / RAG      │
├───────────────────────────────────────────────┤
│  模型网关  Multi-LLM Router / Cache / Quota   │
├───────────────────────────────────────────────┤
│  平台底座  Tenant / Auth / Billing / Audit    │
│            Observability / Config             │
└───────────────────────────────────────────────┘
```

**分层规则**：
- 上层可调用下层，下层**不可反向依赖**上层
- 跨层调用必须经过相邻层暴露的接口，不允许"穿透"
- 业务/客户定制代码不进入本仓库，通过插件 / MCP 注入

---

## 3. 核心术语表

| 术语 | 含义 | 容易混淆的概念 |
|------|------|----------------|
| Agent | 一个**运行中**的智能体实例 | ≠ Agent 模板 / 配置 |
| Agent Template | 可复用的 Agent 定义（提示词 + 工具集 + 模型配置） | ≠ Agent 实例 |
| Skill | 平台层的"高阶能力封装"，可由多个 Tool 组合而成 | ≠ Tool |
| Tool | 单次原子调用（函数级） | ≠ MCP Server |
| MCP Server | 通过 MCP 协议接入的外部能力提供方 | 内部 Tool 走平台原生协议 |
| Session | 一次用户会话上下文（可跨多个 Run） | ≠ Conversation（前端概念） |
| Run | Agent 的一次完整执行（一个 user turn → 一次最终回复） | ≠ Step |
| Step | Run 内的一次模型调用或工具调用 | |
| Tenant | 企业租户（计费 / 隔离单位） | |
| Workspace | 租户下的工作空间（团队级） | |
| Project | Workspace 下的 Agent 集合 | |

---

## 4. 技术栈与工程约定

### 语言与运行时

- **主语言**：**Python 3.11+**（单语言起步，不引入 Rust / FFI）
- **Web 框架**：**FastAPI**（asyncio 原生，OpenAPI 自动生成）
- **ASGI Server**：uvicorn（dev 单进程） / gunicorn + uvicorn workers（prod 多进程）
- **异步范式**：全链路 `async/await`，禁止在 async 路径中调用阻塞 IO
- **类型**：强制 `mypy --strict`（或 pyright），所有公共接口必须有类型注解

### 存储（V1：本地 / 单机优先）

> 选型原则：**V1 用 SQLite 跑通，本地联调零依赖**；负载或多租户硬隔离需要时再迁。

- **关系存储**：**SQLite（WAL 模式）**
  - 元数据、Run/Step 事件、审计日志、租户配置全部落 SQLite
  - 单文件，便于本地调试、单机部署、回归测试
- **全文检索**：SQLite **FTS5**（内置）
- **向量检索**：**sqlite-vec** 扩展（与主库同进程，避免引入外部服务）
- **缓存 / 队列**：**进程内** + 文件队列起步；高并发再切 Redis
- **对象存储**：本地文件系统（dev） / S3 兼容接口（prod）

> 迁移路径已预留：所有数据访问走 Repository 接口，未来切换 Postgres + pgvector 不影响业务层。**编写 SQL 必须考虑这一点：不用 SQLite 独有语法，除非加 `# sqlite-only` 注释并在 ADR 登记。**

### 模型与协议

- **默认模型**：Claude Sonnet 4.6（`claude-sonnet-4-6`）
- **模型网关**：统一抽象 OpenAI 兼容 + Anthropic 原生两套协议
- **流式协议**：对外 **SSE**；内部组件间默认 HTTP/JSON，性能瓶颈点再考虑 gRPC
- **MCP**：作为外部工具接入的默认协议

### 部署

- **dev**：`uvicorn` 单进程 + SQLite 文件，零外部依赖一行启动
- **prod**：Docker 镜像 + K8s（Helm chart 在 `/deploy`），SQLite 通过持久卷挂载（早期）或切 Postgres

### 工程命令（占位，确定后回填）

- 安装依赖：`uv sync` 或 `pip install -e ".[dev]"`
- 启动 dev：`make dev`（启动 FastAPI + 初始化 SQLite schema）
- 测试：`pytest`
- 类型检查：`mypy .`
- Lint / Format：`ruff check . && ruff format .`

---

## 5. 目录结构语义

> 新增目录前先在此登记，写清"职责 + 不允许依赖谁"。

```
/app
  /api          对外 OpenAPI 入口（FastAPI router 聚合）
                只做参数校验 + 调用 service，不写业务逻辑

  /runtime      Agent 执行引擎（Planner / Executor / 状态机）
                禁止依赖 /api、/console、/gateway 之外的上层

  /gateway      模型网关，统一 LLM 接口（含路由、缓存、配额、重试）
                业务代码禁止绕过本目录直连任何 LLM SDK

  /tools        平台原生工具实现
                新工具默认走 MCP 接入，确有强耦合需求才进此目录

  /mcp          MCP 接入层（client + server registry + 鉴权）

  /knowledge    文档摄入、切片、向量化、检索
                不直接暴露给 Agent，通过 /tools 的检索工具调用

  /tenancy      租户、Workspace、Project、权限、配额
                所有数据访问层必须经过这里做隔离校验

  /audit        审计日志（追加写、不可篡改），所有 Run/Step/工具调用落库

  /storage      Repository 抽象 + SQLite 实现
                所有 DB 访问必须通过 Repository 接口，禁止裸 SQL 散落各处

  /console      管理后台（前后端）
                只读 + 配置类操作，不参与 Agent 执行链路

  /internal     平台内部共享库（日志、错误、配置、ID 生成、redact 等）

/tests          pytest 测试（按上面目录镜像组织）
/deploy         Dockerfile / Helm chart / 部署脚本
/docs/adr       架构决策记录（Architecture Decision Records）
/scripts        一次性脚本、数据迁移、本地工具
```

---

## 6. 关键设计决策（ADR 摘要）

> 详细 ADR 见 `/docs/adr/`。这里只放 Claude 需要在写代码时随时记住的取舍。

1. **语言选型：Python 单语言起步**
   决策：主体 Python，不引入 Rust / Go / FFI
   原因：Agent 平台 99% 耗时在 LLM 调用与外部 IO，引擎语言性能不是瓶颈；迭代速度与生态优先
   含义：禁止以"性能"为由提议引入 Rust 模块；真有热点先 profile，再考虑独立服务（gRPC sidecar），不走进程内 FFI

2. **DB 选型：SQLite 起步，预留迁移**
   决策：V1 全部使用 SQLite（WAL + FTS5 + sqlite-vec）
   原因：本地联调零依赖，单文件备份恢复简单，足以支撑前 10 个企业客户的 PoC
   含义：所有 SQL 走 Repository 抽象；写 SQL 时避免 SQLite 独有语法；何时切 Postgres 由"并发写冲突 / 多实例部署"触发，不是拍脑袋

3. **自研编排 vs 现成框架**
   决策：自研轻量编排核心，不直接绑定 LangGraph / AutoGen
   原因：企业场景对多租户、审计、可中断/可重放要求高，现成框架抽象不够
   含义：可以借鉴它们的设计，但不引入为运行时依赖

4. **工具协议统一收敛到 MCP**
   决策：对外接入一律 MCP，内部原生 Tool 仅在性能 / 强耦合场景使用
   含义：新增能力优先考虑 MCP Server，而非写进 `/tools`

5. **多租户隔离策略**
   决策：行级 `tenant_id` 强制隔离 + Repository 层统一拦截
   原因：SQLite 无 schema 概念，行级是唯一可行方案；未来迁 Postgres 再加 schema 隔离
   含义：所有数据访问必须带 tenant 上下文，禁止裸 SQL 跨租户查询

6. **上下文管理优先级**
   决策：截断（硬上限） > 摘要（保留语义） > RAG（外部召回）
   含义：不要默认引入复杂的上下文压缩链路

7. **流式协议**
   决策：对外 SSE，内部默认 HTTP/JSON
   含义：不要在对外 API 引入 WebSocket；不要预先引入 gRPC

8. **LLM 调用路径**
   决策：所有 LLM 调用**必须**经过 `/gateway`
   含义：业务代码出现 `anthropic.Client(...)` 或同类直连 = 违规

9. **Agent 状态持久化**
   决策：每个 Step 作为事件落库（事件溯源），支持中断恢复与重放
   含义：Agent 运行时禁止用纯内存状态机；Step 表是核心审计入口

10. **同步/异步纪律**
    决策：FastAPI 路径必须 `async`，调用阻塞库（含 sqlite3 标准库）一律走线程池（`asyncio.to_thread` 或 `aiosqlite`）
    含义：禁止在 async 路径中直接 `requests.get()` / `time.sleep()` / 同步文件 IO

---

## 7. 安全与合规红线

以下任何一条被违反都视为**架构性错误**，PR 必须打回：

- **租户隔离不可绕过**：跨租户数据访问只能通过受审计的平台接口
- **LLM 调用必须经网关**：业务代码禁止直连任何模型 SDK
- **全链路审计**：Run / Step / Tool 调用 / Prompt / 模型 IO 全部入 `/audit`
- **密钥管理**：禁止硬编码任何 API Key / Token，统一走 secret 管理
- **PII 处理**：日志与 trace 中的 PII 必须脱敏，脱敏规则集中在 `/app/internal/redact`
- **越权防护**：工具调用前必须校验当前 Agent 在当前 Tenant 下的权限
- **Prompt 注入防护**：所有外部内容（文档、网页、工具返回）拼入 prompt 前需经隔离标记
- **SQL 注入**：禁止字符串拼接 SQL，统一使用参数化查询 / SQLAlchemy core

---

## 8. 协作约定

- **新增模块 / 跨层接口**：先在 `/docs/adr` 写一份 ADR，再写代码
- **测试要求**：`/runtime`、`/gateway`、`/tenancy`、`/storage` 必须有集成测试
- **Commit 风格**：Conventional Commits（`feat: ...`、`fix: ...`、`refactor: ...`）
- **不要做的事**：
  - 不要在本仓库写示例业务 Agent（放到独立的 `agentic-examples` 仓库）
  - 不要为了演示便利引入"全局单例 LLM 客户端"
  - 不要在初期就做过度抽象（如插件化一切）——三处重复再抽象
  - 不要为"未来可能切 Postgres"提前写双实现，写好 Repository 抽象即可

---

## 9. 给 Claude 的工作偏好

- 改动前先确认所在目录的职责边界（见 §5），避免跨层
- 涉及多租户 / 审计 / 模型调用时，**默认假设有红线**（§7），不确定就先问
- 早期阶段优先**简单直白**的实现，不要预先设计扩展点
- 写 SQL 前先看 Repository 是否已有方法，没有再加
- 不主动新增 README / 文档文件，除非显式被要求
- 中文沟通，代码注释除"为什么"外尽量不写
