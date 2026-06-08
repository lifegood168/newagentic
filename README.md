# newagentic

平安健康内部 Agentic 平台。

> 当前阶段：Phase 0 — POC 框架（不绑业务）

## 5 分钟启动

前置：Python 3.11+ ，[uv](https://github.com/astral-sh/uv)

```bash
# 1. 安装依赖
uv sync --extra dev

# 2. 复制环境配置
cp .env.example .env

# 3. 初始化数据库
make init-db

# 4. 启动服务
make dev

# 5. 验证
curl http://localhost:8000/healthz
open http://localhost:8000/docs
```

## 容器化

```bash
make docker-up
make docker-down
```

## 工程命令

| 命令 | 用途 |
|------|------|
| `make dev` | 启动 dev 服务 |
| `make test` | 跑测试 + 覆盖率 |
| `make lint` | ruff 检查 |
| `make typecheck` | mypy --strict |
| `make init-db` | 初始化 SQLite schema |
| `make check-constraints` | 检查 6 条强约束（ADR-0002） |
| `make docker-up` / `docker-down` | 容器启停 |

## 文档地图

- [docs/00-architecture.md](docs/00-architecture.md) — 总架构
- [docs/01-phases.md](docs/01-phases.md) — 分步实施方案
- [docs/02-todolist.md](docs/02-todolist.md) — 可勾选清单
- [docs/03-validation.md](docs/03-validation.md) — 验证集
- [docs/04-review-notes.md](docs/04-review-notes.md) — 评审笔记
- [docs/adr/](docs/adr/) — 架构决策记录
- [CLAUDE.md](CLAUDE.md) — 给协作者 / Claude 的工作坐标系

## 6 条强约束（PR 必查）

见 [ADR-0002](docs/adr/0002-six-strong-constraints.md)。
