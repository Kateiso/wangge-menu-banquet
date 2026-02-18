# Agentic Agent 技术调研报告

> 调研来源: Anthropic 官方文档 + OpenAI 官方文档（2025-2026）
> 目的: 为旺阁渔村 AI 点菜系统的自优化能力提供理论基础

---

## 1. 什么是 Agentic Agent

### Anthropic 的定义

**Agentic systems（智能体系统）** 是所有将 LLM 与工具结合的 AI 系统的总称。Anthropic 做了关键区分：

- **Workflows（工作流）**: LLM 和工具通过**预定义的代码路径**编排（确定性控制流）
- **Agents（智能体）**: LLM **动态地指导自身的流程和工具使用**，对如何完成任务保持控制权（自主控制流）

基础构建块是 **Augmented LLM（增强型 LLM）** — 一个具备检索、工具和记忆能力的模型，能自主生成搜索查询、选择合适工具、决定保留哪些信息。

### OpenAI 的定义

> "一个拥有 **instructions（指令）**、**guardrails（护栏）** 和 **tools（工具）** 的 AI 系统，**代表用户采取行动**。"

与聊天机器人的核心区别：聊天机器人回答问题，智能体**采取行动**。智能体在一个 **while 循环** 中运行 — 处理输入、调用工具、评估结果、继续执行，直到满足退出条件。

### 通俗理解

两家公司的共识：agentic system 是一个**自主决定使用哪些工具、何时使用**的 LLM，在**循环中运行直到任务完成**。

核心属性：
- **自主性**（self-directed）— 自己决定下一步做什么
- **工具使用**（acts on the world）— 不只是说，还能做
- **迭代性**（loops until done）— 循环执行直到完成
- **目标导向**（works toward defined outcome）— 朝着明确目标前进

---

## 2. 架构模式

### Anthropic 的六种模式（从简单到复杂）

| 模式 | 描述 | 适用场景 | 复杂度 |
|------|------|----------|--------|
| **Augmented LLM** | 单个 LLM + 检索 + 工具 + 记忆 | 所有模式的基础 | ★ |
| **Prompt Chaining** | 顺序调用 LLM，每步处理上一步输出，含程序化验证 | 固定子任务序列；准确性 > 速度 | ★★ |
| **Routing** | 对输入分类，导向不同的专门处理器 | 不同类别需要不同处理 | ★★ |
| **Parallelization** | 同时运行多个子任务或多次运行同一任务投票 | 速度优化或置信度提升 | ★★★ |
| **Orchestrator-Workers** | 中央 LLM 分解任务、委派给 worker、综合结果 | 子任务不可预测 | ★★★★ |
| **Evaluator-Optimizer** | 一个 LLM 生成，另一个评估并反馈，循环改进 | 有明确评估标准且可迭代改进 | ★★★★ |

**核心指导原则**: "从简单方法开始。优化单个 LLM 调用加上检索和上下文示例，通常就足够了。"

### OpenAI 的编排模式

| 模式 | 描述 |
|------|------|
| **Single Agent Loop** | 一个模型 + 工具 + 指令在 while 循环中运行 |
| **Manager Pattern** | 中央 LLM 通过工具调用编排专业 agent，保持统一上下文 |
| **Decentralized (Handoffs)** | Agent 之间单向移交执行权，附带对话状态 |

OpenAI Agents SDK 的核心原语：Agent、Handoff、Guardrail、Session、Tracing。

---

## 3. 自优化的关键组件

### A. 反馈循环

#### Anthropic 的 Agent 循环（Claude Agent SDK）

```
1. Gather Context   → 获取和组织信息
2. Take Action      → 使用工具执行任务
3. Verify Work      → 评估输出质量
4. Iterate          → 重复直到目标达成
```

三种验证策略：
- **规则验证**: 显式验证标准（lint、格式检查、测试）
- **视觉反馈**: 截图/渲染检查 UI 任务
- **LLM-as-Judge**: 第二个模型评估模糊标准（语调、质量）

#### OpenAI 的自进化循环

```
1. Baseline Agent Execution → agent 处理输入
2. Feedback Collection      → 人类专家或自动评判者评估
3. Eval-Driven Assessment   → 结构化评分器衡量指标
4. Prompt Optimization      → 改进后的指令替换表现不佳的版本
```

三种优化策略：
- **手动迭代**: 可视化反馈 + 手动重写
- **结构化反馈**: 收集评分器的具体推理
- **全自动**: metaprompt agent 程序化生成改进指令

### B. 记忆系统

#### Anthropic 的记忆架构

- **结构化笔记（agentic memory）**: agent 在上下文窗口外维护持久笔记，之后检索
- **压缩（compaction）**: 接近上下文限制时选择性总结 — 保留架构决策、未解决 bug；丢弃冗余输出
- **即时上下文检索（JIT）**: 维护轻量标识符（文件路径、查询），通过工具动态加载
- **Agent Skills**（`SKILL.md` 文件）: 通过渐进式披露按需加载的行为模块

#### OpenAI 的三层记忆架构

```
1. Structured Profile  → 来自内部系统的机器可读字段（稳定基线）
2. Global Memory Notes → 跨会话的持久偏好（如"偏好靠走道的座位"）
3. Session Memory Notes → 临时的会话级覆盖（如"这次我想要靠窗座位"）
```

记忆生命周期：
```
实时蒸馏（对话中捕获） → 整合（去重、解决冲突、清除临时笔记）
```

注入优先级：用户最新消息 > 会话记忆 > 全局记忆 > 结构化档案

### C. 工具使用

#### Anthropic 的工具设计原则

- 在 ACI（Agent-Computer Interface）设计上投入与 prompt 同等的精力
- 保持格式接近自然文本
- 消除格式开销（行号计数、转义需求）
- 包含涵盖边界情况的完整文档
- 实现"poka-yoke"防误设计（如要求绝对路径而非相对路径）

高级能力：
- **Tool Search Tool**: 搜索数千个工具而不消耗上下文窗口
- **Programmatic Tool Calling**: 在代码执行环境中调用工具

### D. 自我反思

- **Anthropic**: Evaluator-Optimizer 模式是自我反思的显式架构。每步通过环境反馈（工具结果、代码执行）自我纠正。
- **OpenAI**: 其内部 data agent "评估自身进展 — 如果中间结果看起来有误，agent 会调查出了什么问题、调整方法、重新尝试"。

---

## 4. 生产环境中的"从反馈中学习"

### Anthropic 的方案：Agent Skills + 迭代优化

核心机制是 **Agent Skills** — 将成功模式编码为可复用能力的结构化文件夹：

```
skill-name/
  SKILL.md          # YAML 前置元数据（name, description）+ 指令
  reference.md      # 按需加载的额外上下文
  scripts/          # 确定性代码工具
```

**渐进式披露**: 启动时预加载元数据 → 相关时加载完整 SKILL.md → 按需加载引用文件。Agent 容量因此"无限"。

**当前状态**: 人类与 agent 协作迭代，捕获成功方法。
**未来愿景**: "让 agent 能够自己创建、编辑和评估 Skills，将自身的行为模式编码为可复用能力。"

**长时间运行的 agent**: 用 git 作为检查点机制，维护结构化进度文件，feature 注册表跟踪通过/失败状态。

### OpenAI 的方案：Eval 驱动的自进化循环

```
Agent v1 → 执行 → 多评分器评估 → 打分
                                    |
                 通过（>75% 评分器 OR >85% 平均分）? → 发布
                                    |
                               否 → Metaprompt Agent
                                    |
                               Agent v2（改进后的 prompt）
                                    |
                               [重复循环]
```

**VersionedPrompt 类**: 跟踪 prompt 演进，具备回滚能力。评估失败触发 metaprompt agent，该 agent 接收原始 prompt、当前输出和失败评分器的结构化反馈。

**AgentKit** 提供完整生产管线：
- Agent Builder（可视化迭代）
- Evals（自定义评分器）
- Automated Prompt Optimization（从评估结果生成改进 prompt）

---

## 5. Agent 自调整 Prompt/规则/参数的模式

| 模式 | 来源 | 类型 | 描述 |
|------|------|------|------|
| **Evaluator-Optimizer Loop** | Anthropic | 运行时 | 一个 LLM 生成，另一个评估并反馈，生成器迭代改进 |
| **Self-Evolving Prompt Optimization** | OpenAI | 离线/批处理 | Metaprompt agent 分析评估失败并重写系统 prompt |
| **Agent Skills as Externalized Memory** | Anthropic | 动态加载 | Agent 加载/卸载 skill 文件来修改行为，而非调整 prompt 本身 |
| **Memory-Driven Personalization** | OpenAI | 持久化 | 对话中使用 `save_memory_note` 工具，会话后整合 |
| **Progress Files + Git Checkpointing** | Anthropic | 跨会话 | 维护结构化进度文件，用 git commit 作为恢复点 |

---

## 6. 警告与反模式

### Anthropic 的警告

1. **不要过度工程化**: "最成功的实现不是使用复杂框架或专用库，而是用简单、可组合的模式构建。"
2. **避免框架锁定**: 抽象层"可能遮蔽底层的 prompt 和响应，使调试更困难。"
3. **不要跳过简单方案**: "优化单个 LLM 调用加上检索和上下文示例，通常就足够了。"
4. **Agent 的成本/延迟权衡**: 只在简单方案明显失败时才使用 agentic 系统。
5. **永远不要删除测试**: "删除或编辑测试是不可接受的。"
6. **人工审查不可或缺**: 即使自动验证通过，人工审查仍然必要。

### OpenAI 的警告

1. **不要从多 agent 开始**: "从单个 agent 开始，只在需要时才演进到多 agent 系统。"
2. **记忆积累会降低质量**: "没有仔细修剪，记忆存储会积累冗余和过时信息。"
3. **PoC 瓶颈**: "Agentic 系统经常在概念验证后遇到瓶颈，因为它们依赖人类来诊断边缘情况。"
4. **人类专家仍然不可或缺**: 特别是在受监管领域。
5. **防范 prompt 注入**: 记忆系统必须禁止存储"可能操纵系统行为的指令式内容"。
6. **不要在记忆中存储敏感数据**: 禁止存储 PII、凭证或支付信息。

---

## 7. Anthropic vs OpenAI 对比

| 维度 | Anthropic | OpenAI |
|------|-----------|--------|
| **定义** | Agent = LLM 动态指导自身流程 | Agent = 指令 + 护栏 + 工具代用户行动 |
| **核心哲学** | "简单、可组合的模式" | "可组合的原语" |
| **自优化机制** | Agent Skills（外部化行为模块）+ Evaluator-Optimizer | Self-Evolving Loop（eval 驱动 prompt 重写）+ 记忆个性化 |
| **记忆** | Agentic notes + 压缩 + JIT 检索 | 三层记忆（档案/全局/会话）+ 蒸馏与整合 |
| **反馈机制** | 规则 + 视觉 + LLM-as-Judge | 人工审查 + LLM-as-Judge + 多评分器 evals |
| **生产学习** | Skills 文件（人工策划、agent 加载） | VersionedPrompt + metaprompt agent（自动化） |
| **SDK** | Claude Agent SDK（计算机使用导向） | Agents SDK（Python/TypeScript，handoffs + guardrails + tracing） |
| **独特创新** | 渐进式技能披露；MCP 工具集成 | AgentKit（可视化构建 + evals + 自动优化）；GEPA 框架 |

---

## 8. 对旺阁渔村点菜系统的应用建议

### 推荐架构: 记忆驱动 + Evaluator-Optimizer

基于两家公司的最佳实践，推荐采用 **"规则存储 + Prompt 注入 + 后验评估"** 的最小方案：

```
┌─────────────────────────────────────────────────────────┐
│                    反馈闭环架构                           │
│                                                         │
│  ① 老板反馈 ──→ ② LLM 解析为规则 ──→ ③ 规则存储(SQLite) │
│       ↑                                    ↓            │
│       │              ④ Prompt 注入 ←───────┘            │
│       │                   ↓                              │
│  ⑦ 菜单展示 ←── ⑥ 后验评估 ←── ⑤ LLM 生成菜单          │
│       │              ↓                                   │
│       └──────── ⑧ 评估反馈 ──→ ② (自动微调参数)          │
└─────────────────────────────────────────────────────────┘
```

### 为什么选这个方案

1. **简单**: 不引入外部框架（LangChain、CrewAI），用现有 FastAPI + SQLite
2. **可逆**: 所有规则都可以查看、停用、回滚
3. **安全**: 规则变更必须用户确认后才生效
4. **透明**: 老板能看到哪些规则在影响配菜结果
5. **渐进**: 先做规则存储 → 再做反馈解析 → 最后做自动评估

### 实施路线（交付后）

```
Phase B1: 规则基础设施
  → SystemRule 表 + RuleService + 硬编码参数迁移

Phase B2: 反馈引擎
  → FeedbackEngine + LLM 反馈分析 + 规则生成

Phase B3: 后验评估器
  → MenuEvaluation + 自动评分 + 微调建议

Phase B4: 多租户
  → tenant_id + 数据隔离 + 部署方案

Phase B5: 前端 UI
  → 规则管理页 + 反馈历史 + 评估报告
```

---

## 参考资料

### Anthropic 官方
- [Building Effective AI Agents](https://www.anthropic.com/research/building-effective-agents) — 核心模式指南
- [Agent Skills](https://claude.com/blog/equipping-agents-for-the-real-world-with-agent-skills) — 动态技能加载系统
- [Context Engineering for AI Agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents) — 记忆与上下文管理
- [Building Agents with Claude Agent SDK](https://claude.com/blog/building-agents-with-the-claude-agent-sdk) — SDK 架构与反馈循环
- [Effective Harnesses for Long-Running Agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents) — 检查点与状态持久化
- [New Agent Capabilities API](https://www.anthropic.com/news/agent-capabilities-api) — 代码执行、MCP、Files API
- [Advanced Tool Use](https://www.anthropic.com/engineering/advanced-tool-use) — Tool Search、Programmatic Tool Calling

### OpenAI 官方
- [Building Agents Track](https://developers.openai.com/tracks/building-agents/) — 全面的 agent 架构指南
- [Agents SDK Documentation](https://platform.openai.com/docs/guides/agents-sdk) — SDK 参考
- [Self-Evolving Agents Cookbook](https://developers.openai.com/cookbook/examples/partners/self_evolving_agents/autonomous_agent_retraining) — 自主重训练循环
- [Context Personalization Cookbook](https://developers.openai.com/cookbook/examples/agents_sdk/context_personalization) — 记忆与状态管理
- [A Practical Guide to Building Agents](https://openai.com/business/guides-and-resources/a-practical-guide-to-building-ai-agents/) — 编排模式与最佳实践
- [AgentKit Walkthrough](https://developers.openai.com/cookbook/examples/agentkit/agentkit_walkthrough) — 可视化构建 + evals + 自动优化
- [New Tools for Building Agents](https://openai.com/index/new-tools-for-building-agents/) — 生态系统概览
