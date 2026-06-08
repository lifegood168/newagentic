# ADR-0003: V1 技术栈选型（Python + SQLite + OpenAI 兼容网关）

- **状态**：Accepted
- **日期**：2026-06-08
- **决策者**：项目主理人
- **相关**：[ADR-0001](./0001-platform-first-route.md)、[CLAUDE.md §4](../../CLAUDE.md)

---

## 背景

1-2 工程师团队需要快速跑通 V1 POC 框架。技术栈选择影响：

- 迭代速度（语言生态、调试体验）
- 招聘成本（中型团队可持续）
- 运维复杂度（部署、监控、备份）
- 与公司基础设施的契合度

公司基础设施现状：

- 已有 LLM 网关（OpenAI 兼容协议）
- 已有 KG / ES / DB（作为业务 Tool 接入）
- 团队 Python 生态最熟悉

---

## 决策

| 维度 | 选型 |
|------|------|
| 主语言 | **Python 3.11+** |
| Web 框架 | FastAPI + uvicorn |
| 关系存储 | **SQLite（WAL）** + FTS5 + sqlite-vec |
| 模型协议 | **公司内部 LLM 网关（OpenAI 兼容）** |
| 流式协议 | SSE |
| 包管理 | uv |
| 类型检查 | mypy --strict |
| 测试 | pytest + MockModelProvider |
| 容器化 | Docker（Phase 0 起） |

---

## 备选方案

### 备选 A：Rust + Python FFI（参考文档原方案）

**为什么不选**：

- Agent 平台 99% 耗时在 LLM 调用与外部 IO，引擎语言性能不是瓶颈
- FFI 边界（GIL / 异步桥 / 内存所有权 / 构建矩阵 / 段错误调试）会拖慢 1-2 人小团队 2-3 倍
- Rust + PyO3 同时熟练的工程师市场上极少，扩团队困难

### 备选 B：Go 主体 + Python 局部

**为什么不选**：

- Go 部署友好但 LLM / RAG 生态薄
- 1-2 人维护双语言，构建矩阵和调试体验都会被拖累
- 可作为 **Phase 3 接入层备选**（当并发 / SSE 长连接成为瓶颈时）

### 备选 C：Python + Postgres（跳过 SQLite）

**为什么不选**：

- Postgres 本地联调要起容器，schema 迁移工具链负担重
- V1 阶段单文件 SQLite + Repository 抽象足够
- 触发切换的指标已量化（见 00-architecture §10）

---

## 后果

### 好处

- 本地零依赖一键起：`uv sync && make dev`
- Python 异步生态成熟（FastAPI + httpx + aiosqlite）
- 团队技能匹配，无需额外培训
- 模型网关复用公司基础设施，不重造轮子
- SQLite 单文件 → 备份恢复、回归测试、CI 友好

### 代价

- 异步 / 阻塞 IO 边界要纪律：不在 async 路径直接调 sqlite3 标准库（统一走 aiosqlite 或 `asyncio.to_thread`）
- SQLite 多实例部署需切 Postgres（触发条件已在 00-architecture §10 量化）
- Python 类型系统弱 → mypy --strict + pydantic 全量使用补救

### 风险

| 风险 | 缓解 |
|------|------|
| Python 性能不够 | Phase 0-2 不会触发；Phase 3 评估前置 Go 接入层（见 ADR-0001 演进） |
| SQLite WAL 在 NFS 等共享挂载不稳 | dev 用本地盘；prod 用 K8s 持久卷（不跨节点） |
| 异步代码混入阻塞 IO | ruff `ASYNC` rules + code review |

---

## 验证 / 退出

### 验证决策生效

- Phase 0 V0.1.1 - V0.1.5（启动 / 健康检查 / DB 初始化 / 类型检查）全过
- Phase 1 在该栈上跑通销售助理两个用例

### 重新评估触发点

| 触发 | 重评内容 |
|------|---------|
| 并发写冲突 > 1%/min | SQLite → Postgres |
| 部署多实例 | SQLite → Postgres |
| 单实例长连接 > 1000 | 评估前置 Go 接入层 |
| Python 异步生态出现重大不稳定（不太可能） | 重评主语言 |

变更需通过新 ADR（如 0010-postgres-migration），本 ADR 标记 `Superseded by 0010`。
