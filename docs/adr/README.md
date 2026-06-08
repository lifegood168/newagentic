# Architecture Decision Records (ADR)

本目录记录平台的关键架构决策。每条 ADR 都是一次"为什么这样做、为什么不那样做"的留痕。

---

## 编号规则

- `NNNN-<kebab-case-title>.md`
- NNNN 四位数字，从 0001 递增，不复用
- 一个 ADR 一个决策；多决策必须拆开

## 状态

每条 ADR 必须在头部声明状态：

| 状态 | 含义 |
|------|------|
| `Proposed` | 待评审 |
| `Accepted` | 已采纳，生效中 |
| `Deprecated` | 已弃用（保留历史，不删除） |
| `Superseded by NNNN` | 被新 ADR 替代 |

**已 Accepted 的 ADR 不修改正文**。要变更决策 → 写新 ADR，把旧的标记为 `Superseded by`。

## 模板

```markdown
# ADR-NNNN: <Title>

- **状态**：Proposed | Accepted | Deprecated | Superseded by NNNN
- **日期**：YYYY-MM-DD
- **决策者**：<姓名 / 角色>
- **相关**：<其他 ADR 编号 / docs 链接>

## 背景（Context）
我们面对什么问题？有哪些约束？

## 决策（Decision）
我们决定怎么做？

## 备选方案（Alternatives）
还考虑过哪些？为什么没选？

## 后果（Consequences）
这个决策带来什么好处？什么代价？什么风险？

## 验证 / 退出（Verification / Exit）
怎么验证决策生效？什么信号触发重新评估？
```

## 何时写 ADR

- 新增模块 / 跨层接口
- 引入外部依赖（DB / 中间件 / 协议）
- 改变性能或安全约束
- 推翻已有决策
- 选择 A 还是 B 长期影响代码结构时

## 何时**不**需要 ADR

- 单点 bug 修复
- 命名 / 风格调整
- 单文件内部重构

---

## 已发布的 ADR

| # | 标题 | 状态 | 日期 |
|---|------|------|------|
| [0001](./0001-platform-first-route.md) | 选择"先平台后 C 端"路线 | Accepted | 2026-06-08 |
| [0002](./0002-six-strong-constraints.md) | 6 条平台强约束 | Accepted | 2026-06-08 |
| [0003](./0003-python-sqlite-stack.md) | V1 技术栈选型（Python + SQLite + OpenAI 兼容网关） | Accepted | 2026-06-08 |
