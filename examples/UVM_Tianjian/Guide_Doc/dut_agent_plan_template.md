# DUT Agent 规划指南

## 概述

在 UVM Tianjian 工作流的 Stage 5 中，大模型需要将 DUT 的端口信号按协议语义分组，规划出合理的 Agent 架构，然后通过 `GenerateTianjianIni` 工具生成天箭配置文件 `env_cfg.ini`。本文档定义了 Agent 规划的完整方法论和输出格式。

---

## Agent 规划方法论

### 第 1 步：信号分组

从 `02_{DUT}_basic_info.md` 中的端口列表出发，按**协议语义**对信号分组：

| 分组原则 | 示例 |
|----------|------|
| 同一总线协议 | AXI 的 AW/W/B/AR/R 通道归为一个 AXI Agent |
| 同一握手接口 | `data_in_valid` + `data_in_ready` + `data_in_data` → `data_in` Agent |
| 时钟/复位 | `clk`, `rst_n` 不归入任何 Agent，由顶层直接连接 |
| 独立控制信号 | `cfg_bypass_en` 等可归入专门的 `cfg` Agent |

### 第 2 步：确定 Agent 模式

| 模式 | 含义 | 适用场景 |
|------|------|----------|
| `master` | Driver + Monitor + Sequencer 三件套 | DUT 的**输入接口** — 需要主动驱动激励 |
| `only_monitor` | 仅 Monitor | DUT 的**输出接口** — 仅需被动采样观测 |

**判断规则**：
- DUT 的 `input` 端口方向 → 该接口对应 `master` Agent（驱动输入）
- DUT 的 `output` 端口方向 → 该接口对应 `only_monitor` Agent（采样输出）
- 双向端口或协议级接口（如 AXI slave）需根据实际握手方向综合判断

### 第 3 步：识别可复用 Agent

当多个接口的信号列表**完全一致**（仅方向可能不同）时，可通过 `instance_by` 复用同一 Agent 定义：

```
Agent A: instance_by = self     （自建 Agent，天箭会生成完整目录）
Agent B: instance_by = A        （复用 A 的定义，天箭只生成实例化代码）
```

### 第 4 步：确定 Scoreboard 连接策略

每个 Agent 的 Monitor 数据需要连接到 Scoreboard 的某一侧：

| `scb_port_sel` | 含义 | 典型用途 |
|-----------------|------|----------|
| `exp` | 预期侧（Expected） | 输入 Agent — 驱动数据作为参考模型的输入 |
| `act` | 实际侧（Actual） | 输出 Agent — DUT 实际输出用于比对 |

---

## GenerateTianjianIni 工具参数

### agents 参数 JSON 格式

`agents` 参数接收 JSON 字符串，数组中每个对象描述一个 Agent：

```json
[
  {
    "agent_name": "data_in",
    "agent_mode": "master",
    "instance_by": "self",
    "instance_num": 1,
    "interface_list": "input bit data_in_valid\ninput bit [31:0] data_in_data\noutput bit data_in_ready",
    "dut_list": "dut_data_in_valid\ndut_data_in_data\ndut_data_in_ready",
    "scb_port_sel": "exp"
  },
  {
    "agent_name": "data_out",
    "agent_mode": "only_monitor",
    "instance_by": "self",
    "instance_num": 1,
    "interface_list": "output bit data_out_valid\noutput bit [31:0] data_out_data\ninput bit data_out_ready",
    "dut_list": "dut_data_out_valid\ndut_data_out_data\ndut_data_out_ready",
    "scb_port_sel": "act"
  }
]
```

### 字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `agent_name` | string | ✅ | Agent 名称（小写，下划线分隔），天箭按此命名生成目录 |
| `agent_mode` | string | ✅ | `master` 或 `only_monitor` |
| `instance_by` | string | ✅ | `self`（自建）或其他 Agent 名（复用） |
| `instance_num` | int | ❌ | 实例数量，默认 1。多通道时设为 N |
| `interface_list` | string | ✅ | Agent 侧信号列表，每行一个信号，格式：`方向 类型 [位宽] 信号名` |
| `dut_list` | string | ✅ | DUT 侧信号列表，与 `interface_list` 一一对应 |
| `scb_port_sel` | string | ❌ | Scoreboard 连接侧：`exp` 或 `act`，默认 `exp` |

### interface_list 信号格式

每行一个信号，格式为天箭规范：

```
方向 类型 [位宽] 信号名
```

示例：
```
input bit clk_in
input bit [7:0] addr
output bit [31:0] data
input bit valid
output bit ready
```

**注意**：
- `方向` 是从 Agent 侧看的方向（`input` = Agent 接收 / DUT 输出，`output` = Agent 驱动 / DUT 输入）
- 方向与 RTL 端口方向**相反**：RTL 的 `input` 在 Agent 中为 `output`（Agent 驱动进 DUT）
- `interface_list` 和 `dut_list` 的信号数量和顺序必须严格一致

---

## Agent 规划文档输出格式

`05_{DUT}_agent_plan.md` 应包含以下内容：

```markdown
# {DUT} Agent 规划

## DUT 端口概览
[从 02 文档中提取的端口列表]

## Agent 架构

### Agent 1: {agent_name}
- **模式**: master / only_monitor
- **实例方式**: self / 复用自 xxx
- **实例数量**: N
- **Scoreboard 连接**: exp / act
- **信号映射**:
  | Agent 信号 | DUT 信号 | 方向 | 位宽 |
  |-----------|----------|------|------|
  | ... | ... | ... | ... |

### Agent 2: ...

## Scoreboard 连接拓扑

```
Input Agent (master) ──[exp]──► Scoreboard ◄──[act]──  Output Agent (monitor)
                                    │
                               参考模型比对
```

## 设计决策说明
[解释为何如此分组和选择模式的理由]
```

---

## 完整示例：FIFO DUT

### DUT 端口

| 端口 | 方向 | 位宽 | 功能 |
|------|------|------|------|
| clk | input | 1 | 系统时钟 |
| rst_n | input | 1 | 异步复位 |
| push | input | 1 | 写请求 |
| wdata | input | 32 | 写数据 |
| full | output | 1 | 满标志 |
| pop | input | 1 | 读请求 |
| rdata | output | 32 | 读数据 |
| empty | output | 1 | 空标志 |

### Agent 规划结果

```json
[
  {
    "agent_name": "wr",
    "agent_mode": "master",
    "instance_by": "self",
    "interface_list": "output bit push\noutput bit [31:0] wdata\ninput bit full",
    "dut_list": "push\nwdata\nfull",
    "scb_port_sel": "exp"
  },
  {
    "agent_name": "rd",
    "agent_mode": "only_monitor",
    "instance_by": "self",
    "interface_list": "output bit pop\ninput bit [31:0] rdata\ninput bit empty",
    "dut_list": "pop\nrdata\nempty",
    "scb_port_sel": "act"
  }
]
```

### Scoreboard 连接

```
wr Agent (master) ──[exp]──► FIFO Scoreboard ◄──[act]── rd Agent (monitor)
                                    │
                            内部维护 ref_fifo
                          比对 push 的数据 vs pop 的数据
```

---

## 常见陷阱

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| 信号方向混淆 | Agent 侧方向与 RTL 相反 | RTL `input` → Agent `output`（Agent 驱动） |
| interface_list 与 dut_list 不匹配 | 数量或顺序不一致 | 逐行检查，保证一一对应 |
| 遗漏时钟/复位 | clk/rst 不应放入 Agent | 天箭通过 ENV_GENERAL 自动处理 |
| Scoreboard 数据方向反了 | exp/act 配置错误 | 输入 Agent → exp，输出 Agent → act |
| 多通道未复用 | 信号列表相同但创建了多个 Agent | 使用 `instance_by` 和 `instance_num` |
