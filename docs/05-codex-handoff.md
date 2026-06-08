# Codex 外包包

> 把 Phase 0 / Phase 1 中"低风险、单文件、有清晰 spec"的任务标准化为可外包包，交给 Codex / Copilot Agent / 其他 LLM coding agent 执行。
> 每个包都是**自包含**的——Codex 读这一份 + 引用的文档就能动手。

---

## 一、分工总图

| 角色 | 职责 |
|------|------|
| **业务主理人**（lifegood168） | 拍板、API key / 密钥、ADR 决策、PR 终审、合并 |
| **Claude**（架构同伴） | 架构骨架、跨模块抽象、ADR 撰写、Codex 产出 review、高风险节点亲自实现 |
| **Codex**（执行者） | 单 P0.x / P1.x 节点实现、写单元测试、跑 CI 检查 |

---

## 二、外包流程

```
1. 主理人 / Claude 把一个 "handoff package" 交给 Codex
2. Codex 开新分支：feat/<package-id>
3. Codex 实现 + 跑 make lint && make typecheck && make test && make check-constraints
4. Codex 发 PR，描述按本文 §六 模板
5. Claude review（架构对齐 / 强约束 / 验收集对齐）
6. 主理人合并
```

**禁止跳过 review**——Codex 不懂 6 条强约束，必须有人把关。

---

## 三、标准 brief 模板

每次外包前，把下面这段贴给 Codex，并替换 `<TASK_ID>` / `<P0.X>` / `<V0.X>` 等占位：

```
你在 /Users/life/workspace/newagentic 仓库工作。

【必读文档（按顺序）】
1. CLAUDE.md（项目地基）
2. docs/00-architecture.md
   - §4 数据模型
   - §6 6 条强约束（违反任何一条 = PR 打回）
   - §7 四阶段 ReAct 循环
3. docs/02-todolist.md → 找到 <P0.X> 章节，那是你的任务
4. docs/03-validation.md → 找到 <V0.X> 对应验收，那是你的退出条件
5. docs/adr/0002-six-strong-constraints.md
6. docs/05-codex-handoff.md → 找到 <TASK_ID> 章节，那是细化 spec

【任务】
完成 <P0.X> 节点，按 <TASK_ID> 包的细化 spec 实现。

【硬约束】
- 不允许跨层依赖（如 gateway 禁止 import runtime / api）
- 所有公共接口必须有类型注解，mypy --strict 通过
- 必须新增对应的 tests/
- 不要在 async 路径里调阻塞 IO
- 不要修改 CLAUDE.md / docs/00-architecture.md / docs/adr/（如果你认为需要改，提出来等审）

【完成前必跑】
make lint
make typecheck
make test
make check-constraints

【交付】
开 PR，body 按 §六 模板填写。
```

---

## 四、可外包包清单

### TASK-P0.3：模型网关

**目标**：实现 OpenAI 兼容协议的 LLM 网关，支持流式 / 工具调用 / 重试 + MockProvider 用于测试。

**文件清单**（创建）：

| 文件 | 职责 |
|------|------|
| `app/gateway/types.py` | `ChatMessage` / `ToolCall` / `StreamChunk` / `Usage` / `ChatRequest` / `ChatResponse` 数据类 |
| `app/gateway/openai_compat.py` | `OpenAICompatClient` — httpx async client，支持流式 + 非流式 + 工具调用 + 重试 3 次（指数退避） |
| `app/gateway/mock.py` | `MockModelProvider` — 预设响应序列 + 录制重放 |
| `app/gateway/router.py` | `ModelRouter` — 按 Agent Template 配置选择模型实例 |
| `tests/unit/test_gateway.py` | 单元测试 |

**接口契约**（不可改）：

```python
# app/gateway/types.py
class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant", "tool"]
    content: str | None
    tool_calls: list[ToolCall] | None = None
    tool_call_id: str | None = None

class ChatRequest(BaseModel):
    model: str
    messages: list[ChatMessage]
    tools: list[dict] | None = None
    temperature: float = 0.7
    max_tokens: int = 2048
    stream: bool = False

class ModelProvider(Protocol):
    async def chat(self, req: ChatRequest) -> ChatResponse: ...
    async def chat_stream(self, req: ChatRequest) -> AsyncIterator[StreamChunk]: ...
```

**配置读取**：从 `app.internal.config.get_settings()` 读 `llm_gateway_base_url` / `llm_gateway_api_key` / `llm_default_model`。

**禁止**：
- 直接 `import openai` — 用 httpx 实现 OpenAI 兼容协议
- 在 `app/runtime/` 或 `app/api/` 下创建文件
- 把 API key 硬编码

**验收**（来自 V0.x，部分提前到本节点）：
- [ ] `ChatRequest` / `ChatResponse` 字段完整，pydantic 校验通过
- [ ] 流式：MockProvider 返回 3 个 chunk，能逐个 yield
- [ ] 非流式：单次返回完整 ChatResponse
- [ ] 工具调用：response 中 tool_calls 字段正确解析
- [ ] 错误重试：500 错误重试 3 次（指数退避：1s / 2s / 4s）
- [ ] Usage 字段透传（prompt_tokens / completion_tokens）
- [ ] 单元测试覆盖率 ≥ 80%

**PR 标题**：`feat(gateway): implement OpenAI-compatible client (P0.3)`

---

### TASK-P0.4：Tool 系统

**目标**：Tool 基类 + 注册中心 + 2 个内置 demo Tool（echo / http_get）。

**前置依赖**：`app/tools/context.py` 已有 `ToolContext`，不要重新定义。

**文件清单**（创建）：

| 文件 | 职责 |
|------|------|
| `app/tools/base.py` | `Tool` 抽象基类 + `ToolResult` |
| `app/tools/registry.py` | `ToolRegistry` 单例 + 注册 / 查询 / 列出 |
| `app/tools/builtin/echo.py` | 回显输入的 Tool |
| `app/tools/builtin/http_get.py` | HTTP GET Tool（httpx，10s 超时） |
| `tests/unit/test_tools.py` | 单元测试 |

**接口契约**：

```python
# app/tools/base.py
class ToolResult(BaseModel):
    ok: bool
    data: Any | None = None
    error: str | None = None

class Tool(ABC):
    code: ClassVar[str]
    version: ClassVar[str] = "1.0"
    description: ClassVar[str]
    args_schema: ClassVar[type[BaseModel]]

    @abstractmethod
    async def execute(self, ctx: ToolContext, args: BaseModel) -> ToolResult: ...

# app/tools/registry.py
class ToolRegistry:
    def register(self, tool: type[Tool]) -> None: ...
    def get(self, code: str) -> type[Tool]: ...
    def list(self) -> list[type[Tool]]: ...
    def schemas(self) -> list[dict]: ...  # for /tools API
```

**注册方式**：模块导入时调用 `ToolRegistry().register(EchoTool)`，启动时扫描 `app/tools/builtin/__init__.py` 触发。

**禁止**：
- Tool execute 函数不接 `ToolContext` —— 违反约束 5
- 把 Tool 注册逻辑放在 `app/api/` 或 `app/runtime/`
- 在 builtin Tool 里写业务逻辑（业务 Tool 是 Phase 1 的事，去 `app/tools/business/`）

**验收**：
- [ ] echo Tool：`execute(ctx, {input: "hi"})` 返回 `ToolResult(ok=True, data={"output": "hi"})`
- [ ] http_get Tool：mock httpx 测试 200 / 404 / 超时三种场景
- [ ] ToolRegistry.list() 返回两个 Tool
- [ ] ToolRegistry.schemas() 返回 OpenAI 函数调用兼容的 JSONSchema 列表
- [ ] 每个 Tool 收到的 ToolContext 字段完整（V0.7.1）

**PR 标题**：`feat(tools): add base / registry / echo / http_get (P0.4)`

---

### TASK-P0.7-API：API 扩展（Run / SSE）

**前置依赖**：TASK-P0.3 和 TASK-P0.4 已合并；TASK-P0.6（运行时）由 Claude 实现后才能接。

**目标**：`POST /runs` + `GET /runs/{id}` + `GET /runs/{id}/events`（SSE）。

**文件清单**（创建 / 修改）：

| 文件 | 操作 |
|------|------|
| `app/api/runs.py` | 新增：3 个 endpoint |
| `app/api/main.py` | 修改：include_router |
| `app/storage/runs.py` | 新增：Run / Step Repository（如果还没） |
| `tests/integration/test_runs_api.py` | 新增 |

**接口契约**：

```python
# POST /runs
class CreateRunRequest(BaseModel):
    template_code: str
    input: str
    session_id: str | None = None
    business_line_id: str | None = None

class CreateRunResponse(BaseModel):
    run_id: str
    status: str  # "running"

# GET /runs/{run_id}
class RunDetail(BaseModel):
    id: str
    status: str
    input: str
    output: str | None
    error: str | None
    steps: list[StepSummary]

# GET /runs/{run_id}/events (SSE)
# event 类型见 app/api/sse_schema.py
```

**验收**：
- [ ] POST /runs 创建 Run 后立即返回 run_id（不阻塞）
- [ ] GET /runs/{id} 含 steps 列表
- [ ] SSE 事件类型符合 `app/api/sse_schema.py` 定义
- [ ] SSE 客户端断开重连：再次订阅可收到剩余事件

**PR 标题**：`feat(api): add /runs and SSE events endpoint (P0.7)`

---

### TASK-P1.2-KNOWLEDGE：Knowledge 中台 V1

**前置**：Phase 0 已完成。

**目标**：文档摄入 + 切片 + 嵌入 + sqlite-vec 检索。

**文件清单**（创建）：

| 文件 | 职责 |
|------|------|
| `app/knowledge/ingest.py` | 文档读取（txt / md / pdf） |
| `app/knowledge/chunker.py` | 切片（按 token / 段落） |
| `app/knowledge/embedder.py` | 调用 embedding API（OpenAI 兼容） |
| `app/knowledge/store.py` | sqlite-vec + FTS5 存储 |
| `app/knowledge/retriever.py` | 混合检索（向量 + BM25 + MMR） |
| `tests/unit/test_knowledge.py` | 单元测试 |

**关键约束**：
- 每条 chunk 必须带 `business_line_id`（V1.2.3 验证）
- 不要复用 `app/gateway/` 做 embedding——独立 client（embedding 与 chat 生命周期不同）
- 切片不切断句子（中文按 `。！？` 优先）

**PR 标题**：`feat(knowledge): document ingest + hybrid retrieval (P1.2)`

---

## 五、不外包的任务（Claude 亲自实现）

| 任务 | 不外包原因 |
|------|----------|
| **P0.6 Agent 运行时四阶段循环** | async / 事件溯源 / 循环检测 corner case 多，错一处全链路崩 |
| **任何 ADR** | 决策类工作，Codex 不懂业务取舍 |
| **跨模块抽象重构** | 需要全局视野 |
| **Phase 2 Subagent 编排** | 涉及嵌套 Run / 上下文隔离的高风险设计 |
| **安全 / 鉴权相关** | 必须人类把关 |

---

## 六、Codex PR 描述模板

Codex 提 PR 时按此填写：

```markdown
## Task
完成 <TASK_ID>（见 docs/05-codex-handoff.md）

## Changes
- 新增：<文件列表>
- 修改：<文件列表>

## Validation
- [ ] `make lint` 通过
- [ ] `make typecheck` 通过
- [ ] `make test` 通过，新增测试覆盖率 X%
- [ ] `make check-constraints` 通过
- [ ] 对照 docs/03-validation.md <V0.X / V1.X> 全部 ✅

## Self-Review against Constraints
- [ ] 约束 1：未修改引擎层加业务名
- [ ] 约束 2：LLM 调用走 gateway
- [ ] 约束 3：Step 事件落库
- [ ] 约束 4：Tool 走平台注册
- [ ] 约束 5：未硬编码 Tool/Skill 三层
- [ ] 约束 6：未引入 app/memory/

## Open Questions
（如果有发现 docs 不一致 / spec 模糊处，列在这里）
```

---

## 七、Review checklist（Claude review 用）

收到 Codex PR 后，按此清单 review：

### 架构层

- [ ] 文件落在正确的目录（不跨层）
- [ ] 没有 import 上层模块（如 `gateway` 不 import `runtime`）
- [ ] 6 条强约束全过

### 接口层

- [ ] 公共接口签名与本 handoff doc 一致
- [ ] 类型注解完整，mypy --strict 真的过
- [ ] 没有偷偷新增"方便的全局单例"

### 测试层

- [ ] 单元测试针对 spec，不是只测 happy path
- [ ] Mock 真实场景（如 mock httpx，不是 mock 自己的代码）
- [ ] 覆盖率达标

### 文档层

- [ ] PR 描述完整
- [ ] 没有偷偷改 docs / ADR
- [ ] 没有引入新依赖（要新增依赖需先 ADR）

### 风险层

- [ ] 没有硬编码 API key / 测试密钥
- [ ] 异步 / 同步边界正确（不在 async 调阻塞 IO）
- [ ] 没有"等下次修复"的 TODO 留在 main 路径上

---

## 八、外包顺序建议

```
Round 1（可同时开两个 PR，相互独立）：
  TASK-P0.3 模型网关
  TASK-P0.4 Tool 系统

Round 2（依赖 P0.3 + P0.4 + P0.6 ）：
  TASK-P0.7-API
  ← Claude 在 Round 1 期间实现 P0.6

Round 3（Phase 0 完成后）：
  TASK-P1.2-KNOWLEDGE
  P1.3 业务 Tool（届时再写包）
```
