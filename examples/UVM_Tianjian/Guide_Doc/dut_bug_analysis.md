# {DUT} 静态 Bug 分析报告模板

## 概述

本文档记录了在 RTL 源码静态审查阶段发现的所有潜在设计缺陷。每个缺陷通过代码审查识别，并与功能检测点文档中的 `<CK-*>` 检测点关联。

---

## 标签层级结构

Bug 记录必须按照以下标签层级组织：

```
<FG-功能组名>
  └─ <FC-功能点名>
     └─ <CK-检测点名>
        └─ <BG-STATIC-NNN-NAME>
           └─ <LINK-BUG-[BG-TBD]>
              └─ <FILE-path:L1-L2>
```

### 标签说明

| 标签 | 含义 | 示例 |
|------|------|------|
| `<FG-*>` | 来自 03 文档的功能组 | `<FG-DATAPATH>` |
| `<FC-*>` | 来自 03 文档的功能点 | `<FC-DATA-FORWARD>` |
| `<CK-*>` | 来自 03 文档的检测点 | `<CK-NORM-DATA-PASS>` |
| `<BG-STATIC-NNN-NAME>` | 静态 Bug 标签 | `<BG-STATIC-001-FSM-DEFAULT>` |
| `<LINK-BUG-[BG-TBD]>` | 动态验证关联（待填） | 初始为 TBD，后续关联 |
| `<FILE-path:L1-L2>` | 源码定位 | `<FILE-dut.v:42-45>` |

### 重要规则

1. **标签来源**：所有 `<FG-*>` / `<FC-*>` / `<CK-*>` 必须来自 `03_{DUT}_functions_and_checks.md`，不得凭空创造。
2. **NULL 标签**：若某文件未发现 Bug，添加 `<FG-NULL><FC-NULL><CK-NULL><BG-STATIC-NULL>`。
3. **关联规则**：`<LINK-BUG-[BG-TBD]>` 在静态分析阶段初始设为 TBD，在验证总结阶段关联为实际 Bug 标签或 `[BG-NA]`。

---

## BG-STATIC 命名规范

| 前缀 | 类型 | 示例 |
|------|------|------|
| BG-STATIC-NNN-FSM-* | 状态机相关 | BG-STATIC-001-FSM-DEFAULT-MISSING |
| BG-STATIC-NNN-ARITH-* | 算术运算相关 | BG-STATIC-002-ARITH-OVERFLOW |
| BG-STATIC-NNN-TIMING-* | 时序逻辑相关 | BG-STATIC-003-TIMING-ASYNC-RST |
| BG-STATIC-NNN-INTF-* | 接口协议相关 | BG-STATIC-004-INTF-HANDSHAKE |
| BG-STATIC-NNN-CTRL-* | 控制逻辑相关 | BG-STATIC-005-CTRL-PRIORITY |

---

## 静态审查检查项

### 状态机逻辑
- 状态枚举是否完整
- 转移条件是否正确
- 是否有孤立/死锁状态
- default 分支是否缺失

### 算术运算
- 溢出/下溢风险
- 位宽截断
- 有符号/无符号类型不匹配

### 时序逻辑
- 复位条件完整性
- 异步信号同步
- 竞争冒险
- 亚稳态

### 接口协议
- valid/ready 握手时序
- 数据有效窗口
- 读写使能逻辑

### 控制逻辑
- 优先级处理
- 互斥条件
- 未处理的输入组合

---

## Bug 报告模板

<!-- 从这里开始复制，为每个发现的静态 Bug 创建一段 -->

<FG-功能组名>

<FC-功能点名>

<CK-关联检测点>

### <BG-STATIC-NNN-NAME> Bug 标题

<LINK-BUG-[BG-TBD]>

<FILE-RTL文件路径:行号>

**问题描述**：简要描述发现的潜在缺陷。

**触发条件**：描述可能触发此缺陷的输入组合或状态序列。

**预期行为**：设计规格要求的正确表现。

**实际代码行为**：当前 RTL 代码的问题所在。

**修复建议**：提供具体的逻辑修改建议。

**置信度**：高 | 中 | 低

<!-- 复制上方块以记录更多 Bug -->

---

## 批次分析进度

| 源文件 | 发现疑似Bug数 | 状态 |
|--------|-------------|------|
| <!-- 由 LLM 在分析过程中填充 --> | | |
