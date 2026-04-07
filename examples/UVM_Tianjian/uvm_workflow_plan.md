# UCAgent 完整 UVM 验证工作流规划（基于天箭 Tianjian）

## 背景与设计原则

本工作流面向使用 UCAgent + 天箭脚本的 UVM 验证场景，贯穿 RTL 验证的完整生命周期。  
核心原则是"**谋定而后动**"——在搭建任何 UVM 环境之前，大模型必须先完成需求理解、功能点拆解和静态代码审查，然后再由天箭自动生成 UVM 骨架，最后进入环境定制、激励开发和覆盖率收敛。

本文档参考：
- `ucagent/lang/zh/config/default.yaml`：UCAgent 中文标准验证工作流结构规范
- `examples/Formal/formal.yaml`：形式化验证工作流参考
- `examples/tianjian/`：天箭 UVM 自动化生成工具

---

## 工作流全貌（9 个 Stage）

| Stage | 名称 | 核心产物 |
|-------|------|---------|
| 1 | `requirement_analysis_and_planning` | 验证规划文档 |
| 2 | `dut_function_understanding` | 基本信息文档 |
| 3 | `functional_specification_analysis` | FG/FC/CK 功能检测点文档 |
| 4 | `static_bug_analysis` | 静态 Bug 分析文档 |
| 5 | `interface_extraction_and_env_bootstrapping` | env_cfg.ini + UVM 工程树 |
| 6 | `uvm_env_customization` | Scoreboard / fcov / Driver 业务代码 |
| 7 | `uvm_sequence_and_test_development` | Sequence + Test 用例库 |
| 8 | `regression_and_coverage` | 覆盖率分析报告 |
| 9 | `verification_review_and_summary` | 最终验证总结报告 |

---

## 各 Stage 详细设计

---

### Stage 1：需求分析与验证规划

**stage name**: `requirement_analysis_and_planning`

**目标**：阅读设计规格文档，确定验证策略、风险点和总体目标，为后续工作铺垫方向。

**详细任务步骤**：
1. 读取 `{DUT}/README.md` 及所有设计规格文档，理解 DUT 的功能范围和接口规格。
2. 识别关键验证风险点（如状态机、仲裁逻辑、协议接口、边界条件等）。
3. 确定验证等级（`ut` / `it` / `bt`）和方法（仿真 / 断言 / 覆盖率目标）。
4. 将验证计划写入 `output/{DUT}/01_{DUT}_verification_needs_and_plan.md`，需包含：
   - 验证范围与目标
   - 各类风险分级
   - 验证策略与方法选型
   - 验证资源与时间估算

**参考文件**：
- `{DUT}/README.md`
- `{DUT}/*.v`，`{DUT}/*.sv`

**输出文件**：
- `output/{DUT}/01_{DUT}_verification_needs_and_plan.md`

**Checker**：
- `UnityChipCheckerMarkdownFileFormat`：检查输出文档格式合规性

---

### Stage 2：DUT 功能理解

**stage name**: `dut_function_understanding`

**目标**：对 DUT 的接口信号、时序、复位策略和内部功能子模块进行系统梳理。

**详细任务步骤**：
1. 读取 DUT RTL 顶层源码（`{DUT}/*.v`, `{DUT}/*.sv`），识别所有 `input`/`output`/`inout` 端口。
2. 分析时钟结构（单/多时钟域）和复位策略（同步/异步、高/低有效）。
3. 归纳核心功能模块：状态机、数据通路、存储器（FIFO/RAM）、协议接口。
4. 识别需要特殊处理的子结构（大型乘法器、参数化模块等）。
5. 整理结果写入 `output/{DUT}/02_{DUT}_basic_info.md`，需包含：
   - 端口列表（方向、位宽、功能说明）
   - 时钟/复位方案说明
   - 核心子模块及数据流描述

**参考文件**：
- `{DUT}/README.md`
- `{DUT}/*.v`，`{DUT}/*.sv`
- `output/{DUT}/01_{DUT}_verification_needs_and_plan.md`

**输出文件**：
- `output/{DUT}/02_{DUT}_basic_info.md`

**Checker**：
- `UnityChipCheckerMarkdownFileFormat`：检查输出文档格式合规性

---

### Stage 3：功能规格分析与测试点定义

**stage name**: `functional_specification_analysis`

**目标**：将功能拆解为三级标签体系（FG → FC → CK），作为后续覆盖率模型和 Scoreboard 判断逻辑的核心契约。

**子 Stage 结构**：

#### 子 Stage 3.1：功能分组（`dut_function_grouping`）
- 将全部待验证功能按逻辑相关性划分为功能组，以 `<FG-名称>` 标记。
- **强制要求**：必须包含 `<FG-API>` 组用于描述接口级行为。
- 示例：`<FG-DATAPATH>`，`<FG-FLOW-CTRL>`，`<FG-RESET>`，`<FG-API>`

**Checker**：`UnityChipCheckerLabelStructure`（检查 FG 标签结构）

#### 子 Stage 3.2：功能点定义（`function_point_definition`）
- 在每个 FG 内，细化具体功能点，以 `<FC-名称>` 标记。
- 功能点需要"可测试"，能通过输入输出端口进行验证。
- 示例：`<FC-VALID-DATA-PASS>`，`<FC-BACKPRESSURE-HOLD>`

**Checker**：`UnityChipCheckerLabelStructure`（检查 FC 标签结构）

#### 子 Stage 3.3：检测点设计（`check_point_design`）
- 为每个 FC 设计 `<CK-名称>` 检测点，覆盖正常场景、边界条件和异常场景。
- 检测点要能明确对应验证的断言方向（正向/负向/组合路径）。
- 示例：`<CK-VALID-HOLD-AFTER-GRANT>`，`<CK-RESET-CLEAR-ALL-SIGNALS>`
- **人工检查项** `need_human_check: false`（复杂 DUT 建议开启）

**Checker**：`UnityChipCheckerLabelStructure`（检查 CK 标签结构及 COVER_GROUP 覆盖率分组数据）

**输出文件**：
- `output/{DUT}/03_{DUT}_functions_and_checks.md`

---

### Stage 4：RTL 源码静态 Bug 分析

**stage name**: `static_bug_analysis`

**目标**：在开始搭建 UVM 环境前，先通过代码审查发现高置信度潜在缺陷，为后续测试提供重点方向。

**详细任务步骤**：
1. 逐文件分析 RTL 源码（支持批次并行）。
2. 结合 `03_{DUT}_functions_and_checks.md` 中的 `<CK-*>` 检测点，逐项审查实现。
3. 系统排查常见缺陷类型：
   - **状态机**：缺少 default 分支、孤立状态、转移条件错误
   - **算术运算**：溢出、位宽截断、有符号无符号不匹配
   - **时序逻辑**：复位不完整、异步跨域未同步
   - **接口协议**：valid/ready 握手时序异常
   - **控制逻辑**：优先级、互斥条件处理
4. 将发现的潜在 Bug 按以下标签层级记录到 `04_{DUT}_static_bug_analysis.md`：

```
<FG-*>
  └─ <FC-*>
     └─ <CK-*>
        └─ <BG-STATIC-NNN-NAME>
           └─ <LINK-BUG-[BG-TBD]>
              └─ <FILE-path:L1-L2>
```

5. 若发现高/中置信度 Bug，在 `03_{DUT}_functions_and_checks.md` 中补充对应 `<CK-*>` 检测点。
6. 维护文档末尾"批次分析进度"表格。

**标签来源规则**：所有 `<FG-*>`/`<FC-*>`/`<CK-*>` 必须来自 `03_{DUT}_functions_and_checks.md`，不得凭空创造（`NULL` 标签除外）。

**参考文件**：
- `output/{DUT}/03_{DUT}_functions_and_checks.md`
- `output/{DUT}/02_{DUT}_basic_info.md`

**输出文件**：
- `output/{DUT}/04_{DUT}_static_bug_analysis.md`

**Checker**：
- `UnityChipBatchCheckerStaticBug`：批次静态 Bug 标签格式和完整性检查（支持参数 `batch_size`）

---

### Stage 5：接口提取与天箭 UVM 环境生成

**stage name**: `interface_extraction_and_env_bootstrapping`

**目标**：基于前序阶段对 DUT 功能和接口的深入理解，将 RTL 信号映射为天箭 `env_cfg.ini` 配置，调用天箭脚本自动生成完整 UVM 验证平台骨架。

**子 Stage 结构**：

#### 子 Stage 5.1：Agent 规划与接口映射（`agent_planning`）

**任务**：
1. 读取 `02_{DUT}_basic_info.md` 中的端口列表，按协议语义对信号分组。
   - 例如：将 `data_in_valid` + `data_in_data` 归为 `data_in` 接口。
2. 为每组接口确定 Agent 模式：
   - `master`：需要 Sequencer + Driver + Monitor 的主动驱动接口
   - `only_monitor`：仅需 Monitor 的被动监测接口（如 DUT 输出）
3. 识别可复用 Agent（多通道信号列表一致时，通过 `instance_by` 复用）。
4. 确定 Scoreboard 连接策略：每个 Agent 的数据应连接 `exp`（预期侧）还是 `act`（实际侧）。
5. 如果 DUT 存在 parameter，记录到环境级参数列表中。
6. 将规划结果写入 `output/{DUT}/05_{DUT}_agent_plan.md`。

**Checker**：`UnityChipCheckerMarkdownFileFormat`

#### 子 Stage 5.2：天箭配置文件生成（`tianjian_config_generation`）

**任务**：
1. 基于 Agent 规划文档，生成严格符合天箭解析语法的 `env_cfg.ini`，包含：
   - `[ENV_GENERAL]` 段：`prj_path`、`author`、`env_name`、`env_level`、`rtl_top_name` 等
   - 每个 Agent 对应一个 Section：`agent_mode`、`instance_by`、`instance_num`、`agent_interface_list`、`dut_interface_list`、`channel_id_s`、`scb_port_sel` 等
2. **强制校验**：信号方向和位宽必须与 RTL 源码严格一致。
3. 参考天箭用户手册（`天箭验证平台自动生成环境用户手册.pdf`）确保格式合法。

**Checker**：自定义 `TianjianIniSyntaxChecker`（校验 ini 格式、信号列表完备性）

#### 子 Stage 5.3：天箭脚本执行与编译检查（`tianjian_execution`）

**任务**：
1. 调用工具 `RunTianjianGen` 执行 `gen_env.py`，传入生成的 `env_cfg.ini`。
2. 检查脚本输出日志，确认无 ERROR 或异常退出。
3. 验证生成的目录结构完整性（Agent 目录、env_common、Makefile 等）。
4. （可选）运行 `make compile` 进行空载编译检查，确保无语法错误。

**Checker**：自定义 `TianjianOutputChecker`（检查生成的 UVM 目录树完整性）

**参考文件**：
- `output/{DUT}/02_{DUT}_basic_info.md`
- `output/{DUT}/05_{DUT}_agent_plan.md`
- `examples/tianjian/天箭验证平台自动生成环境用户手册.pdf`

**输出文件**：
- `output/{DUT}/05_{DUT}_agent_plan.md`
- `output/{DUT}/env_cfg.ini`
- 天箭生成的完整 UVM 工程目录

---

### Stage 6：UVM 环境逻辑定制

**stage name**: `uvm_env_customization`

**目标**：天箭生成了完整的 UVM 组件骨架（Agent/Env/Scoreboard/fcov），但内部均为空模板。本阶段需结合 Stage 3 的功能点与检测点，为这些骨架填充实际业务逻辑。

**子 Stage 结构**：

#### 子 Stage 6.1：Transaction 约束定义（`transaction_constraint_design`）

**任务**：
1. 打开天箭生成的 `{agent_name}_agent_xaction.sv` 文件。
2. 基于协议规格和功能需求，为 `rand` 字段添加有意义的 `constraint`。
   - 例如：数据位宽合法范围、valid 信号与 data 的关联约束、特定模式下的字段互斥。
3. 完善 `compare()` 函数中的逐字段比较逻辑（天箭默认生成了注释模板）。
4. 完善 `psdisplay()` 函数中的调试打印信息。

**Checker**：自定义 `UvmSyntaxChecker`（编译检查无语法错误）

#### 子 Stage 6.2：Scoreboard 参考模型填充（`scoreboard_ref_model`）

**任务**：
1. 打开天箭生成的环境级 Scoreboard 文件。
2. 结合 `03_{DUT}_functions_and_checks.md` 中的 `<CK-*>` 检测点，实现比对逻辑：
   - 在 `exp` 侧添加预期数据计算逻辑（参考模型 / Golden Model）。
   - 在 `compare()` 中逐字段比较 `exp` 与 `act` 通道数据。
3. 为每个比对失败场景添加详细的 `uvm_error` 报告信息。

**Checker**：自定义 `UvmSyntaxChecker`

#### 子 Stage 6.3：功能覆盖率埋点（`fcov_implementation`）

**任务**：
1. 打开天箭生成的 `{env_name}_fcov.sv` 文件。
2. 基于 `03_{DUT}_functions_and_checks.md` 中的 `<FG-*>`/`<FC-*>`/`<CK-*>` 标签层级，创建对应 Covergroup：
   - 每个 `<FG-*>` 对应一个 `covergroup`
   - 每个 `<FC-*>` 对应一组 `coverpoint`
   - 每个 `<CK-*>` 对应一个或多个 `bins` 定义
3. 在 Monitor 或 Scoreboard 的适当位置调用 `sample()` 触发采集。

**Checker**：自定义 `UvmFcovStructureChecker`（检查 covergroup 与文档标签的对应关系）

#### 子 Stage 6.4：Driver / Monitor 时序完善（`driver_monitor_timing`）

**任务**：
1. 检查天箭生成的 Driver 模板，补全特定协议的驱动时序逻辑。
   - 天箭默认使用 `drv_cb` clocking block 驱动。
   - 如有特定的多拍握手逻辑、backpressure 处理、burst 传输等需求，需要手动补全。
2. 检查 Monitor 中信号采样的正确性（使用 `mon_cb` clocking block）。
3. 确保 DUT 顶层 Interface 绑定正确、所有信号连线无误。

**Checker**：自定义 `UvmSyntaxChecker`（编译检查）

**参考文件**：
- `output/{DUT}/03_{DUT}_functions_and_checks.md`
- `output/{DUT}/02_{DUT}_basic_info.md`
- 天箭生成的各 Agent 及 Env 源文件

**输出文件**：
- 修改后的 UVM 源文件（xaction / scoreboard / fcov / driver / monitor）

---

### Stage 7：测试序列与用例开发

**stage name**: `uvm_sequence_and_test_development`

**目标**：基于功能检测点文档，编写从冒烟测试到定向/随机测试的完整 Sequence 和 Test 用例库，并通过首轮仿真验证环境联通性。

**子 Stage 结构**：

#### 子 Stage 7.1：冒烟测试开发（`sanity_test`）

**任务**：
1. 编写 `test_sanity` 用例，仅验证：
   - 复位后所有输出信号归零/归默认值
   - 单笔最简数据从输入到输出的端到端联通
2. 编写对应的 `sanity_sequence`，发送 1~2 笔最简事务。
3. 运行 `make sim TESTNAME=test_sanity`，确保 UVM Report Phase 输出 `UVM_TEST_PASSED`。
4. 若出现 `UVM_FATAL` / `UVM_ERROR`，分析并修复环境问题（不修复 DUT）。

**Checker**：自定义 `UvmSimLogChecker`（检查仿真日志中无 FATAL/ERROR 且有 TEST_PASSED）

#### 子 Stage 7.2：定向测试开发（`directed_tests`）

**任务**：
1. 基于 `03_{DUT}_functions_and_checks.md` 中的 `<CK-*>` 检测点，为每个关键功能点编写定向 Sequence。
2. 每个 Sequence 对应一个 UVM Test Class，注册到 testcase 列表中。
3. 优先覆盖 Stage 4 静态分析中发现的高/中置信度 Bug 对应的检测点。
4. 测试用例命名规范：`test_{DUT}_{功能组}_{功能点}`。
5. 运行每个用例确认结果（Pass → 功能正确；Fail → 可能发现 Bug，记录到 Bug 分析文档）。

**Checker**：自定义 `UvmTestListChecker`（检查每个 CK 至少有一个对应 Test）

#### 子 Stage 7.3：随机测试开发（`random_tests`）

**任务**：
1. 编写随机化 Sequence，充分利用 Transaction 的 `constraint` 进行约束随机。
2. 设计多种随机场景：
   - 正常随机流量
   - 极限 backpressure（交替拉高拉低 ready）
   - burst 模式与 idle 间隔混合
   - 多通道并行交叉
3. 每个随机用例设置独立的 `seed`，确保可复现。

**Checker**：自定义 `UvmSyntaxChecker`

**参考文件**：
- `output/{DUT}/03_{DUT}_functions_and_checks.md`
- `output/{DUT}/04_{DUT}_static_bug_analysis.md`

**输出文件**：
- Sequence 文件集（`{env_name}_*_sequence.sv`）
- Test 文件集（`test_{DUT}_*.sv`）
- Bug 分析文档（`output/{DUT}/06_{DUT}_bug_analysis.md`）

---

### Stage 8：回归测试与覆盖率收敛

**stage name**: `regression_and_coverage`

**目标**：通过大规模多 seed 回归仿真，驱动代码覆盖率和功能覆盖率收敛至目标阈值，并对覆盖率死角进行定向补充。

**详细任务步骤**：
1. 使用回归脚本（天箭生成的 `DoRegress.py` / `DoRegress.sh`）启动全量测试回归，覆盖全部已注册 testcase × 多个随机 seed。
2. 收集仿真覆盖率报告，分析以下维度：
   - **代码覆盖率**：Line / Condition / Toggle / FSM / Branch
   - **功能覆盖率**：所有 `covergroup` 的 `sample()` 打点率
3. 对照 `03_{DUT}_functions_and_checks.md`，确认每个 `<CK-*>` 检测点至少被一个 Pass 用例覆盖。
4. 对未覆盖的死角：
   - 分析原因（约束过强？缺少场景？设计不可达？）
   - 编写增量定向 Sequence 补洞
   - 重新回归验证
5. 将覆盖率分析结果写入 `output/{DUT}/07_{DUT}_coverage_report.md`。

**参考文件**：
- `output/{DUT}/03_{DUT}_functions_and_checks.md`
- 回归仿真日志和覆盖率报告

**输出文件**：
- `output/{DUT}/07_{DUT}_coverage_report.md`

**Checker**：自定义 `UvmCoverageThresholdChecker`（检查代码覆盖率 ≥ 目标阈值，默认 90%）

---

### Stage 9：验证审查与总结

**stage name**: `verification_review_and_summary`

**目标**：对整个验证过程查漏补缺，整理所有已发现 Bug 和覆盖率数据，生成正式的验证签收报告。

**详细任务步骤**：
1. 回顾所有已发现 Bug，完善 `06_{DUT}_bug_analysis.md` 中的源码分析和修复建议。
2. 回顾 `04_{DUT}_static_bug_analysis.md`，确认所有 `<LINK-BUG-[BG-TBD]>` 已消除（被替换为实际 Bug 标签或 `[BG-NA]`）。
3. 再次阅读 DUT 源码，确认无遗漏 Bug。
4. 回顾所有测试用例，确认断言逻辑合理，无误报 Pass 和误报 Fail。
5. 检验验证规划 `01_{DUT}_verification_needs_and_plan.md` 中的目标是否全部达成。
6. 编写验证总结报告 `output/{DUT}/08_{DUT}_verification_summary.md`，涵盖：
   - 验证范围与策略回顾
   - 仿真通过率统计（Pass / Fail / 总数）
   - 代码覆盖率最终数据
   - 功能覆盖率最终数据
   - 已发现 Bug 清单及严重程度分类
   - 验证完备性评估与改进建议

**参考文件**：
- `output/{DUT}/01_{DUT}_verification_needs_and_plan.md`
- `output/{DUT}/06_{DUT}_bug_analysis.md`
- `output/{DUT}/04_{DUT}_static_bug_analysis.md`
- `output/{DUT}/07_{DUT}_coverage_report.md`

**输出文件**：
- `output/{DUT}/08_{DUT}_verification_summary.md`

**Checker**：`HumanChecker`（人工审核验收）

---

## 支撑工具（Tools）需求总结

本工作流需要以下自定义工具支持（可在 `scripts/tianjian_tools.py` 中实现）：

| 工具名称 | 用途 | 对应 Stage |
|---------|------|-----------|
| `WriteTianjianIni` | 安全写入符合天箭解析规范的 `env_cfg.ini` | Stage 5.2 |
| `RunTianjianGen` | 调用 `gen_env.py` 并捕获 stdout/stderr | Stage 5.3 |
| `RunUVMCompile` | 调用 VCS/Xcelium 编译 UVM 环境 | Stage 5.3, 6 |
| `RunUVMSim` | 执行指定 testcase 仿真，返回日志关键片段 | Stage 7 |
| `RunUVMRegression` | 批量多 seed 回归仿真 | Stage 8 |
| `ExtractCoverageMetrics` | 解析覆盖率报告并返回百分比汇总 | Stage 8 |

同时复用 UCAgent 内置工具：
- `ReadTextFile`、`EditTextFile`、`WriteTextFile`：文件读写
- `Complete` / `Check`：阶段推进与检查
- `CurrentTips` / `Status` / `Detail`：工作流状态查询
- `SetCurrentStageJournal`：阶段日志记录

---

## 与现有工作流的对齐关系

| UVM 工作流 Stage | 对应 `default.yaml` Stage | 说明 |
|-----------------|--------------------------|------|
| Stage 1 需求分析 | `requirement_analysis_and_planning` | 完全对齐 |
| Stage 2 功能理解 | `dut_function_understanding` | 完全对齐 |
| Stage 3 功能规格分析 | `functional_specification_analysis` | 完全对齐（含子 Stage） |
| Stage 4 静态分析 | `static_bug_analysis` | 完全对齐 |
| **Stage 5 天箭 UVM 生成** | **新增** | **UVM 特有：接口映射 + ini 生成 + 脚本执行** |
| **Stage 6 环境定制** | **新增** | **UVM 特有：填充 xaction/scb/fcov/drv** |
| **Stage 7 序列开发** | **新增** | **UVM 特有：UVM Sequence/Test 编写** |
| Stage 8 回归覆盖率 | `line_coverage_analysis` + `generate_random_test_cases` | 合并对齐 |
| Stage 9 验证总结 | `verification_review_and_summary` | 完全对齐 |

---

## 自定义 Checker 详细设计

参考 `examples/Formal/scripts/formal_checkers.py` 的实现模式，所有 Checker 继承 `ucagent.checkers.base.Checker`，实现 `do_check(self, timeout=0, **kwargs) -> tuple[bool, object]` 方法。

文件位置：`examples/UVM_Tianjian/scripts/uvm_checkers.py`

### 1. TianjianIniSyntaxChecker

**用途**：校验生成的 `env_cfg.ini` 格式合法性（Stage 5.2）

**检查逻辑**：
1. 使用 Python `configparser` 解析 ini 文件，确认无语法错误。
2. 校验 `[ENV_GENERAL]` 段必有字段：`prj_path`、`author`、`env_name`、`env_level`、`rtl_top_name`、`u_rtl_top_name`、`rtl_list`。
3. 校验 `env_level` 只能为 `st` / `it` / `bt` / `ut` 之一。
4. 遍历每个 Agent Section，校验：
   - `agent_mode` 只能为 `master` 或 `only_monitor`
   - `instance_by` 为 `self` 或已存在的其他 Agent 名
   - `agent_interface_list` 格式合法（每条含 `input/output bit [xx:0] signal_name`）
   - `dut_interface_list` 与 `agent_interface_list` 信号个数一致
   - `scb_port_sel` 只能为 `exp` 或 `act`
5. 交叉校验：`instance_by` 引用的 Agent 必须在 ini 中已定义。

**构造参数**：
```python
def __init__(self, ini_file, rtl_file=None, **kwargs)
```

---

### 2. TianjianOutputChecker

**用途**：校验天箭 `gen_env.py` 执行后生成的 UVM 目录树完整性（Stage 5.3）

**检查逻辑**：
1. 读取 `env_cfg.ini`，提取 `env_name` 和所有 `instance_by=self` 的 Agent 名称列表。
2. 检查以下目录/文件是否存在（基于天箭的固定生成逻辑）：
   - `{env_name}_common/` 目录及内部的 `{env_name}_common_pkg.sv`
   - 每个自建 Agent 的 `{agent_name}_agent/` 目录及内部的 `{agent_name}_agent_pkg.sv`
   - `{env_name}_env/` 目录及内部的 `{env_name}_env.sv`
   - Makefile 相关文件（`project_cfg.mk` 等）
3. （可选）运行 `make compile` 并检查返回码为 0。

**构造参数**：
```python
def __init__(self, ini_file, gen_output_dir, compile_check=False, **kwargs)
```

---

### 3. UvmSyntaxChecker

**用途**：对 UVM SystemVerilog 文件进行语法校验（Stage 5.3、6.1-6.4）

**检查逻辑**：
1. 使用 `pyslang.SyntaxTree.fromFile()` 解析目标 `.sv` 文件。
2. 收集所有 `diagnostics`，过滤出 error 级别的诊断信息。
3. 若存在 error 级别诊断则返回 `(False, error_details)`。
4. 特别处理 UVM 宏（`\`uvm_*`）：因为 pyslang 不识别 UVM 宏，可退化为基础结构检查（`module`/`endmodule`、`class`/`endclass` 配对）。

**构造参数**：
```python
def __init__(self, target_file, **kwargs)
```

---

### 4. UvmFcovStructureChecker

**用途**：检查 fcov 文件中的 Covergroup 结构是否与 FG/FC/CK 文档标签对应（Stage 6.3）

**检查逻辑**：
1. 读取 `{env_name}_fcov.sv`，提取所有 `covergroup` 名称。
2. 读取 `03_{DUT}_functions_and_checks.md`，提取所有 `<FG-*>` 标签。
3. 检查每个 `<FG-*>` 是否有对应的 `covergroup`（名称映射规则：`FG-DATAPATH` → `cg_datapath` 或包含关键词的 covergroup）。
4. 检查是否有 `coverpoint` 对应 `<FC-*>` 标签。

**构造参数**：
```python
def __init__(self, fcov_file, spec_file, **kwargs)
```

---

### 5. UvmSimLogChecker

**用途**：分析 UVM 仿真日志，判定测试通过/失败（Stage 7.1）

**检查逻辑**：
1. 读取仿真输出日志文件。
2. 扫描关键模式：
   - `UVM_FATAL` → 立即返回失败，附带 fatal 信息上下文。
   - `UVM_ERROR` → 统计 error 数量，超过阈值（默认 0）则失败。
   - `UVM_TEST_PASSED` 或 `Report Summary: 0 UVM_ERROR` → 测试通过。
3. 返回结构化结果：`{pass_count, error_count, fatal_count, test_result}`。

**构造参数**：
```python
def __init__(self, log_file, max_errors=0, **kwargs)
```

---

### 6. UvmTestListChecker

**用途**：检查每个 CK 检测点至少有一个对应 Test 用例（Stage 7.2）

**检查逻辑**：
1. 读取 `03_{DUT}_functions_and_checks.md`，提取所有 `<CK-*>` 标签列表。
2. 扫描 Test 文件目录下所有 `test_*.sv` 文件，提取 test class 名称。
3. 通过命名规则或注释中的 `// CK: CK-xxx` 标记建立映射。
4. 列出未覆盖的 CK 标签。

**构造参数**：
```python
def __init__(self, spec_file, test_dir, **kwargs)
```

---

### 7. UvmCoverageThresholdChecker

**用途**：检查覆盖率是否达到目标阈值（Stage 8）

**检查逻辑**：
1. 读取覆盖率报告文件（VCS urg 格式 / 文本格式）。
2. 解析各维度覆盖率百分比：Line / Cond / Toggle / FSM / Branch / Fcov。
3. 与配置阈值比较（默认 90%）。
4. 列出未达标维度及其当前百分比。

**构造参数**：
```python
def __init__(self, coverage_report, threshold=90.0, **kwargs)
```

---

### 复用的内置 Checker（无需重新实现）

| Checker 名称 | 用途 | 使用 Stage |
|-------------|------|-----------|
| `UnityChipCheckerMarkdownFileFormat` | 检查 Markdown 文档格式 | Stage 1, 2 |
| `UnityChipCheckerLabelStructure` | 检查 FG/FC/CK 标签层级结构 | Stage 3 |
| `UnityChipBatchCheckerStaticBug` | 批次静态 Bug 分析检查 | Stage 4 |
| `HumanChecker` | 人工审核验收 | Stage 9 |

---

## 自定义 Tool 详细设计

参考 `examples/Formal/scripts/formal_tools.py` 的实现模式，所有 Tool 继承 `ucagent.tools.uctool.UCTool` 和 `ucagent.tools.fileops.BaseReadWrite`，使用 Pydantic `BaseModel` 定义参数 schema。

文件位置：`examples/UVM_Tianjian/scripts/uvm_tools.py`

### 1. GenerateTianjianIni

**用途**：根据 Agent 规划文档中的结构化信息，安全生成天箭规范的 `env_cfg.ini` 文件。

**参数 Schema**：
```python
class ArgGenerateTianjianIni(BaseModel):
    env_name: str          # 环境名称，如 "data_bypass"
    env_level: str         # 验证等级: ut/it/bt/st
    rtl_top_name: str      # RTL 顶层模块名
    prj_path: str          # 工程路径
    author: str            # 作者名
    agents: str            # JSON 格式的 Agent 列表定义
```

**核心逻辑**：
1. 解析 `agents` JSON 字符串，得到每个 Agent 的 `agent_name`、`agent_mode`、`instance_by`、`interface_list` 等字段。
2. 写入 `[ENV_GENERAL]` 段。
3. 逐个写入 Agent Section，自动处理 `instance_num`、`channel_id_s` 递增等。
4. 写入后调用 `configparser` 回读校验一次，确保无格式错误。
5. 返回生成文件路径和 Agent 数量汇总。

---

### 2. RunTianjianGen

**用途**：调用天箭 `gen_env.py` 脚本执行 UVM 环境生成，捕获并返回执行日志。

**参数 Schema**：
```python
class ArgRunTianjianGen(BaseModel):
    ini_file: str          # env_cfg.ini 文件路径
    output_dir: str        # 生成结果输出目录（默认为 ini 所在目录）
```

**核心逻辑**：
1. 定位 `gen_env.py` 脚本路径（相对于天箭目录 `examples/tianjian/gen_env.py`）。
2. 通过 `subprocess.Popen` 执行 `python3 gen_env.py <ini_file>`，设置 `cwd` 为 `output_dir`。
3. 捕获 stdout 和 stderr，设置超时（默认 60s）。
4. 检查返回码：
   - 返回码 0 → 返回成功信息 + 生成的目录列表
   - 返回码非 0 → 返回 stderr 中的 ERROR 信息
5. 使用 `_terminate_process_tree` 处理超时进程（参考 formal_tools.py）。

---

### 3. RunUVMCompile

**用途**：调用 EDA 工具编译 UVM 环境，返回编译结果。

**参数 Schema**：
```python
class ArgRunUVMCompile(BaseModel):
    work_dir: str          # Makefile 所在目录
    make_target: str       # 编译目标，默认 "compile"
    tool: str              # 仿真器：vcs / xrun / verilator
```

**核心逻辑**：
1. 在 `work_dir` 下执行 `make {make_target}`。
2. 捕获输出，扫描 `Error` / `Warning` 关键词。
3. 返回编译状态和关键错误摘要（限制最多 20 条）。

---

### 4. RunUVMSim

**用途**：执行指定 testcase 的 UVM 仿真，返回日志关键片段。

**参数 Schema**：
```python
class ArgRunUVMSim(BaseModel):
    work_dir: str          # Makefile 所在目录
    test_name: str         # 测试用例名称
    seed: int              # 随机种子（默认 0 = 自动）
    timeout: int           # 超时秒数（默认 300）
```

**核心逻辑**：
1. 执行 `make sim TESTNAME={test_name} SEED={seed}`。
2. 找到仿真输出日志文件路径。
3. 解析日志：统计 `UVM_FATAL`/`UVM_ERROR`/`UVM_WARNING` 数量。
4. 提取 `UVM_TEST_PASSED` 或 `UVM_TEST_DONE` 字样。
5. 返回结构化结果：`{test_name, seed, result, error_count, log_excerpt}`。

---

### 5. RunUVMRegression

**用途**：批量多 seed 回归仿真。

**参数 Schema**：
```python
class ArgRunUVMRegression(BaseModel):
    work_dir: str          # Makefile 所在目录
    test_list: str         # 测试列表文件路径或逗号分隔的 test 名
    num_seeds: int         # 每个 test 跑多少 seed（默认 5）
    timeout: int           # 单个仿真超时（默认 300）
```

**核心逻辑**：
1. 解析 test_list，展开为 `test_name × seed` 矩阵。
2. 依次（或并行）调用 `RunUVMSim`。
3. 汇总结果：`{total, passed, failed, timeout, failed_list}`。

---

### 6. ExtractCoverageMetrics

**用途**：解析 EDA 工具生成的覆盖率报告，返回各维度百分比。

**参数 Schema**：
```python
class ArgExtractCoverageMetrics(BaseModel):
    report_path: str       # 覆盖率报告路径（urg 目录或文本文件）
    report_format: str     # 格式类型：vcs_urg / xrun_imc / text
```

**核心逻辑**：
1. 根据 `report_format` 选择解析策略：
   - `vcs_urg`：解析 `urgReport/` 目录下的 HTML/文本文件
   - `text`：使用正则匹配 `Line: XX%` / `Cond: XX%` 等模式
2. 返回结构化结果：
```python
{
    "line": 95.2,
    "cond": 88.7,
    "toggle": 91.0,
    "fsm": 100.0,
    "branch": 93.5,
    "fcov": 87.3,
    "summary": "5/6 dimensions meet 90% threshold"
}
```

---

## 项目文件结构规划

```
examples/UVM_Tianjian/
├── uvm_workflow_plan.md          # 本文档（工作流规划）
├── uvm.yaml                     # UCAgent 工作流定义文件（待实现）
├── scripts/
│   ├── __init__.py
│   ├── uvm_tools.py             # 自定义 Tool 实现
│   ├── uvm_checkers.py          # 自定义 Checker 实现
│   └── templates/               # 代码生成模板（如有需要）
├── Guide_Doc/                   # 工作流指导文档
│   ├── dut_functions_and_checks.md
│   ├── dut_bug_analysis.md
│   ├── dut_agent_plan_template.md
│   ├── dut_uvm_env_guide.md
│   └── dut_test_summary.md
└── README.md                    # 工作流使用说明
```

---

## 下一步行动

1. **实现 `uvm.yaml`**：将上述 9 个 Stage 转化为 UCAgent 可直接加载的 YAML 工作流定义。
2. **实现 `scripts/uvm_tools.py`**：按上述设计实现 6 个 Tool 类。
3. **实现 `scripts/uvm_checkers.py`**：按上述设计实现 7 个 Checker 类。
4. **编写 Guide_Doc**：为大模型在各 Stage 执行时提供参考模板文档。
5. **集成测试**：选取一个简单 DUT（如 `data_bypass`）走通全流程。

