# ADR-0002: 6 条平台强约束

- **状态**：Accepted
- **日期**：2026-06-08
- **决策者**：项目主理人
- **相关**：[ADR-0001](./0001-platform-first-route.md)、[docs/00-architecture.md §6](../00-architecture.md)

---

## 背景

参考资料中 8 章设计的审计综合报告指出三个 P0 接口断裂（TaskClassification / AuditCollector / MemoryEngine 被调用未定义）。根本原因不在某条具体设计，而在缺乏"什么是平台、什么必须遵守"的硬约束。

我们需要一组**对所有 PR 强制生效**的架构约束，作为：

1. PR review 的硬性卡点
2. 后续 Claude / 协作者写代码时的边界
3. "平台 ≠ 应用"的可验证定义

---

## 决策

定义 **6 条强约束**。违反任意一条 = 架构性错误，PR 必须打回。

### 约束 1：Agent = 配置不是代码

新 Agent 上线 = 新增一份 `agents/*.yaml`（Prompt + 工具集 + 模型配置 + 预算）。
禁止为新 Agent 改引擎代码。若需改引擎 → 说明平台缺能力 → 往能力层（Tools / Skills / Knowledge）补。

**验证**：Phase 1 退出时 `grep -rn "sales\|product" app/runtime app/gateway app/storage app/factory` 零命中。

### 约束 2：所有 LLM 调用经模型网关

业务代码出现 `openai.Client(...)` / `anthropic.Client(...)` 或同类直连 = 违规。
统一走 `app/gateway/`。

**为什么**：模型路由、配额、缓存、降级、成本归属、审计——这些全靠网关唯一入口。一旦绕过，无法治理。

**验证**：grep `openai\.|anthropic\.|httpx.*v1/chat` 在 `app/` 下只允许出现在 `app/gateway/` 内。

### 约束 3：Run / Step 全量事件溯源

每个 Step 一条事件落 `steps` 表，模型 IO / 工具 IO 全量落库（`payload_json` 不裁剪）。
Run 状态由 Steps 派生，禁止用纯内存状态机。

**为什么**：审计、断点续跑、行为回放、调试——全部依赖 Step 事件流。这是平台的地基。

**验证**：V0.4.6（payload 完整性）+ V0.5（中断恢复）。

### 约束 4：能力层是平台资产

Tool / Skill 必须可被多个 Agent 引用。
业务专属 Tool 也走平台标准注册流程（`app/tools/business/` + ToolRegistry）。
禁止"为某个 Agent 写一个只它自己用的 Tool 并耦合在 Agent 代码里"。

**为什么**：能力层是平台的真正护城河。每个 Tool / Skill 都是平台资产的积累。

**验证**：所有 Tool 必须有 schema + 注册元数据（`tools` 表中可见）。

### 约束 5：配置化优先于框架化

引擎只保证三个原语：ReAct Loop（含四阶段）+ Tool 调用 + Subagent 委派。
不在引擎层硬编码 Tool / Skill / Subagent 三层范式。
Agent 怎么组合是 Template 的事，不是引擎的事。

**为什么**：业务线之间需求差异大（销售更像 ReAct + Subagent，医疗可能更像 Workflow，HR 可能是纯 RAG）。引擎硬编码一种范式会让其他场景跑不通。

**验证**：Phase 1-2 内至少出现 2 种不同范式的 Agent（销售 ReAct + HR 纯 RAG）。

### 约束 6：Knowledge ≠ Memory，不混用

| | Knowledge | Memory |
|---|-----------|--------|
| 内容 | 上传文档 / KG / 产品库 | Agent 自学（偏好 / 纠正 / 模式） |
| 写入 | 人工 / 批处理 | Agent 运行时自动 |
| 隔离 | 业务线 | 用户 + 业务线 |
| 上线 | Phase 1 | Phase 3+ |

短期上下文需求（销售助理 current_client / current_plan）走 `sessions.state_json`，**不新造概念**。

**为什么**：参考的 8 章设计就出现了 "MemoryEngine 被调用但未定义" 的典型问题，根因就是这两个概念混用。

**验证**：Phase 1 内代码层面没有 `app/memory/`；所有"记忆"需求走 Knowledge 或 Session.state_json。

---

## 备选方案

### 备选 A：3 条核心约束（轻量版）

只保留约束 1 / 2 / 3，其他作为"建议"。

**为什么不选**：审计报告里出的问题正好是约束 4-6 没要导致的。轻量化 = 重复犯错。

### 备选 B：全量约束（10+ 条）

参考 8 章设计里的"九层防御""十类审计"等。

**为什么不选**：约束太多 = 没人记得住 = 等于没有。6 条是 PR review 时可肉眼检查的上限。

---

## 后果

### 好处

- PR review 有明确的硬性卡点
- 新加入的工程师 / Claude 一上来就能看到平台的"地基"
- 避免重蹈审计报告中接口断裂、抽象失败的覆辙
- 6 条都有可验证手段（grep / 测试 / 字段检查）

### 代价

- 每条约束都需要工具支持（CI 加 grep 检查）
- 早期某些约束（如"配置化优先于框架化"）会感觉"过度"——比如想图省事直接写死

### 风险

- **风险 1**：约束被当成"建议"，逐渐松弛 → 缓解：CI 加自动化检查（约束 1 / 2 的 grep）
- **风险 2**：某条约束在实战中证明错误 → 缓解：通过新 ADR 替代本 ADR，不在本文件直接修改

---

## 验证 / 退出

### 验证

每个 Phase 退出时跑：

- [ ] 约束 1：grep 检查（V1.5.1）
- [ ] 约束 2：grep + 网关唯一入口测试
- [ ] 约束 3：V0.4.6 payload 完整性 + V0.5 中断恢复
- [ ] 约束 4：`GET /tools` 返回所有业务 Tool 元数据
- [ ] 约束 5：跨范式 Agent 共存测试
- [ ] 约束 6：Phase 1 期间 `ls app/memory/` 应不存在

### 重新评估触发

- 某条约束在 PR review 中累计否决 > 5 次（说明约束设计或团队认知不一致）
- 平台规模化后（Phase 3+）发现某条约束过于严苛
- 出现本 ADR 未覆盖但反复犯错的场景 → 增补第 7 条
