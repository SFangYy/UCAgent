# DUT 功能点与检测点描述指南 (UVM Verification Edition)

## 概述

本文档是 UVM 动态仿真验证的**核心规划蓝图**。通过系统化的功能分组、功能点识别和检测点设计，为后续 Scoreboard 判断逻辑、Functional Coverage 模型和 Sequence 开发奠定基础。

### 核心原则

**1. 对应性原则**：本文档中定义的每一个 `<CK-...>` 检测点都必须在 UVM 环境中有对应实现——或作为 Scoreboard 的比对逻辑，或作为 fcov 的 bins，或作为专项 Sequence 的验证目标。

**2. 独立性原则**：检测点之间应尽可能独立，避免逻辑交叉覆盖，确保 Bug 定位的精准性。

**3. 可测试性原则**：每个检测点必须能通过 DUT 的输入输出端口进行验证，不依赖内部信号（除非通过 Interface 引出）。

### UVM 覆盖率映射关系

在 UVM 场景下，FG/FC/CK 标签体系直接映射为覆盖率模型：

| 标签层级 | UVM 映射 | 说明 |
|----------|----------|------|
| `<FG-*>` | `covergroup` | 每个功能分组对应一个 covergroup |
| `<FC-*>` | `coverpoint` | 每个功能点对应一组 coverpoint |
| `<CK-*>` | `bins` / Sequence | 每个检测点对应 bins 定义或专项激励序列 |

## 文档结构层次

### 层次关系
```
DUT整体功能
├── 功能分组 <FG-*>
│   ├── 功能点1 <FC-*>
│   │   ├── 检测点1 <CK-*>
│   │   ├── 检测点2 <CK-*>
│   │   └── ...
│   ├── 功能点2 <FC-*>
│   │   └── ...
│   └── ...
└── ...
```

### 标签系统
- **功能分组标签**：`<FG-{group-name}>` — 标识大的功能模块或逻辑分类
- **功能点标签**：`<FC-{function-name}>` — 标识具体的设计意图或功能规格
- **检测点标签**：`<CK-{check-point-name}>` — 标识具体的验证点

**重要提醒**：
- Checker 工具通过这些标签进行规范检测，标签格式必须严格遵循规范
- 标签应独立成行，与标题之间用空行分隔
- 检查点之间尽可能独立，避免功能交叉覆盖

## 命名规范

### 功能分组命名
```markdown
<FG-DATAPATH>      # 数据通路
<FG-FLOW-CTRL>     # 流控逻辑
<FG-RESET>         # 复位行为
<FG-FSM>           # 状态机
<FG-MEMORY>        # 存储操作
<FG-API>           # 接口级行为（强制要求）
```

### 功能点命名
```markdown
<FC-VALID-DATA-PASS>        # 有效数据传输
<FC-BACKPRESSURE-HOLD>      # 背压保持
<FC-FSM-STATE-TRANSITION>   # 状态跳转
```

### 检测点命名
```markdown
<CK-NORM-*>        # 正常行为
<CK-EDGE-*>        # 边界条件
<CK-ERR-*>         # 错误/异常场景
<CK-RESET-*>       # 复位相关
```

## 强制性要求

### 必须包含的功能分组
每份功能点与检测点文档**必须**包含：

1. **`<FG-API>`** — 接口级行为描述，定义 DUT 对外接口的协议规格。

### 检测点覆盖要求

设计检测点时，应覆盖以下三类场景：

1. **正常功能**：标准操作路径下的正确行为
2. **边界条件**：满/空、最大/最小、溢出/下溢等极限场景
3. **异常处理**：非法输入、协议违规、错误恢复等

## 标准文档格式

### 文档模板

```markdown
# {DUT名称} 功能点与检测点描述

## DUT 整体功能描述

[描述 DUT 的整体功能，包括：]
- 主要用途和应用场景
- 输入输出接口说明
- 关键性能指标
- 工作原理概述

### 端口接口说明
- 输入端口：[端口名称、位宽、功能描述]
- 输出端口：[端口名称、位宽、功能描述]
- 控制信号：[控制信号说明]

## 功能分组与检测点

### 功能分组A

<FG-GROUP-A>

[功能分组的整体描述]

#### 具体功能A1

<FC-FUNCTION-A1>

[详细描述功能A1的具体实现、输入输出关系、预期行为]

**检测点：**
- <CK-CHECK-A1-1> [具体的检测条件和判断标准]
- <CK-CHECK-A1-2> [具体的检测条件和判断标准]
```

### 标签放置规范

**✅ 正确的标签放置**
```markdown
### 具体功能1

<FC-FUNC1>

功能描述内容...
```

**❌ 错误的标签放置**
```markdown
### 具体功能1 <FC-FUNC1>
功能描述内容...
```

## 完整示例：AXI 数据旁路模块

### DUT 功能概述
一个 AXI4-Lite 配置的数据旁路模块，支持地址映射和数据转发。

### 端口接口
- `clk, rst_n`: 系统时钟与复位
- `s_axi_*`: AXI4-Lite 从接口
- `data_out, data_valid`: 数据输出
- `cfg_bypass_en`: 旁路使能

---

## 功能分组与检测点

### 1. 接口行为

<FG-API>

#### AXI 接口协议

<FC-AXI-PROTOCOL>

**检测点：**
- <CK-AXI-WRITE-RESP> 写操作后应收到 BRESP=OKAY
- <CK-AXI-READ-DATA>  读操作应返回正确的寄存器数据

### 2. 数据通路

<FG-DATAPATH>

#### 正常数据转发

<FC-DATA-FORWARD>

**检测点：**
- <CK-NORM-DATA-PASS>   正常模式下数据 1:1 转发
- <CK-NORM-VALID-TIMING> valid 信号延迟不超过 1 拍
- <CK-EDGE-MAX-WIDTH>    最大位宽数据传输正确

#### 旁路模式

<FC-BYPASS-MODE>

**检测点：**
- <CK-BYPASS-ENABLE>   bypass_en 有效时数据走旁路通路
- <CK-BYPASS-DISABLE>  bypass_en 无效时数据走正常通路
- <CK-BYPASS-SWITCH>   运行中切换 bypass_en 无数据丢失

### 3. 复位行为

<FG-RESET>

#### 复位清零

<FC-RESET-CLEAR>

**检测点：**
- <CK-RESET-OUTPUT-ZERO>     复位后所有输出归零
- <CK-RESET-REG-DEFAULT>     复位后寄存器恢复默认值
- <CK-RESET-DEASSERT-RESUME> 复位释放后功能正常

## 质量检查清单

- [ ] 每个功能分组至少包含一个功能点
- [ ] 每个功能点至少包含一个检测点
- [ ] 所有标签格式正确且唯一
- [ ] 必须包含 `<FG-API>` 功能分组
- [ ] 检测点覆盖正常、边界、异常三类场景
- [ ] 标签独立成行
