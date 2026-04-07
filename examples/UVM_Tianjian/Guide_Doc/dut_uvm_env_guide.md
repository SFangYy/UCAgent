# UVM 环境定制指南（天箭骨架代码填充说明）

## 概述

天箭（Tianjian）生成引擎自动生成了完整的 UVM 验证平台骨架，但各组件内部均为空模板。本指南说明如何在 Stage 6 中为这些骨架填充实际业务逻辑。

---

## 1. Transaction 约束定义 (`*_xaction.sv`)

### 目标
为 `rand` 字段添加有意义的 `constraint`，确保随机化生成的事务符合协议规格。

### 定制要点

#### 1.1 字段约束
```systemverilog
// 天箭生成的空模板：
class ahb_xaction extends uvm_sequence_item;
    rand bit [31:0] addr;
    rand bit [31:0] data;
    rand bit [2:0]  burst_type;
    // TODO: Add constraints

// 填充后：
    constraint c_addr_align {
        addr[1:0] == 2'b00;  // 字对齐
    }
    constraint c_burst_legal {
        burst_type inside {3'b000, 3'b001, 3'b010};  // 仅合法 burst 类型
    }
    constraint c_addr_range {
        addr inside {[32'h0000_0000 : 32'h0000_FFFF]};  // 地址空间限制
    }
```

#### 1.2 compare() 函数
```systemverilog
function bit compare(ahb_xaction rhs);
    compare = 1;
    if (this.addr !== rhs.addr) begin
        `uvm_error("CMP", $sformatf("addr mismatch: exp=0x%08h, act=0x%08h", this.addr, rhs.addr))
        compare = 0;
    end
    if (this.data !== rhs.data) begin
        `uvm_error("CMP", $sformatf("data mismatch: exp=0x%08h, act=0x%08h", this.data, rhs.data))
        compare = 0;
    end
endfunction
```

#### 1.3 psdisplay() 函数
```systemverilog
function string psdisplay(string prefix = "");
    return $sformatf("%s addr=0x%08h data=0x%08h burst=%0d", prefix, addr, data, burst_type);
endfunction
```

---

## 2. Scoreboard 参考模型 (`*_scb.sv`)

### 目标
实现参考模型（Golden Model），接收 exp 和 act 两路数据进行逐字段比对。

### 定制要点

#### 2.1 参考模型结构
```systemverilog
// 在 Scoreboard 中实现参考模型逻辑
class env_scb extends uvm_scoreboard;
    // 天箭生成的 TLM 端口
    uvm_tlm_analysis_fifo #(agent_xaction) exp_fifo;
    uvm_tlm_analysis_fifo #(agent_xaction) act_fifo;

    // 参考模型状态
    bit [31:0] ref_memory [int];  // 参考存储
    int compare_count = 0;
    int mismatch_count = 0;

    task run_phase(uvm_phase phase);
        agent_xaction exp_tr, act_tr;
        forever begin
            exp_fifo.get(exp_tr);
            act_fifo.get(act_tr);
            compare_and_report(exp_tr, act_tr);
        end
    endtask

    function void compare_and_report(agent_xaction exp, agent_xaction act);
        compare_count++;
        if (!exp.compare(act)) begin
            mismatch_count++;
            `uvm_error("SCB", {
                "Mismatch #", $sformatf("%0d", mismatch_count), "\n",
                "  EXP: ", exp.psdisplay(), "\n",
                "  ACT: ", act.psdisplay()
            })
        end
    endfunction
endclass
```

#### 2.2 比对原则
- **逐字段比较**：不要只比较整体，逐字段比对可快速定位问题
- **详细日志**：每次 mismatch 输出 `uvm_error`，包含 exp 和 act 的完整信息
- **统计计数**：在 `report_phase` 中输出总比对数和失败数

---

## 3. 功能覆盖率埋点 (`*_fcov.sv`)

### 目标
严格按 FG→covergroup, FC→coverpoint, CK→bins 映射建立覆盖率模型。

### 定制要点

#### 3.1 映射规则
```
03_{DUT}_functions_and_checks.md 标签    →    fcov.sv 代码
<FG-DATAPATH>                           →    covergroup cg_datapath;
  <FC-DATA-FORWARD>                     →      coverpoint cp_data_forward { ... }
    <CK-NORM-DATA-PASS>                 →        bins normal_pass = { ... };
    <CK-EDGE-MAX-WIDTH>                 →        bins max_width = { ... };
```

#### 3.2 代码示例
```systemverilog
class env_fcov extends uvm_component;
    // 采样接口
    agent_xaction sampled_tr;

    covergroup cg_datapath;
        cp_data_forward: coverpoint sampled_tr.data_valid {
            bins normal_pass = {1};
            bins no_data     = {0};
        }
        cp_data_width: coverpoint sampled_tr.data {
            bins zero     = {32'h0};
            bins max      = {32'hFFFF_FFFF};
            bins mid      = {[32'h1 : 32'hFFFF_FFFE]};
        }
    endgroup

    covergroup cg_flow_ctrl;
        cp_backpressure: coverpoint sampled_tr.ready {
            bins asserted   = {1};
            bins deasserted = {0};
        }
    endgroup

    function new(string name, uvm_component parent);
        super.new(name, parent);
        cg_datapath = new();
        cg_flow_ctrl = new();
    endfunction

    function void sample(agent_xaction tr);
        sampled_tr = tr;
        cg_datapath.sample();
        cg_flow_ctrl.sample();
    endfunction
endclass
```

#### 3.3 采样位置
- 在 **Monitor** 或 **Scoreboard** 的 `write()` 方法中调用 `sample()`
- 确保每笔有效事务都触发采样
- 避免在 Driver 中采样（Driver 是激励侧，不是观测侧）

---

## 4. Driver / Monitor 时序完善 (`*_drv.sv`, `*_mon.sv`)

### 目标
补全天箭默认 Driver 的协议驱动时序，和 Monitor 的信号采样逻辑。

### 定制要点

#### 4.1 Driver 时序
```systemverilog
// 天箭默认使用 drv_cb clocking block 驱动
task drive_transfer(agent_xaction tr);
    // 多拍握手示例 (AXI-like)
    drv_cb.valid <= 1'b1;
    drv_cb.data  <= tr.data;
    drv_cb.addr  <= tr.addr;
    @(drv_cb);
    while (!drv_cb.ready) @(drv_cb);  // 等待 ready
    drv_cb.valid <= 1'b0;
    @(drv_cb);
endtask
```

#### 4.2 Monitor 采样
```systemverilog
// 天箭默认使用 mon_cb clocking block 采样
task collect_transfer();
    agent_xaction tr;
    forever begin
        @(mon_cb);
        if (mon_cb.valid && mon_cb.ready) begin
            tr = agent_xaction::type_id::create("tr");
            tr.addr = mon_cb.addr;
            tr.data = mon_cb.data;
            ap.write(tr);  // 发送到 Analysis Port
        end
    end
endtask
```

#### 4.3 检查清单
- [ ] Driver: clocking block 驱动时序正确
- [ ] Driver: 多拍握手逻辑完整（valid-ready 协议）
- [ ] Driver: backpressure 处理（ready 为低时等待）
- [ ] Monitor: 采样时机使用 mon_cb（不使用直接引用）
- [ ] Monitor: 每笔有效事务发送到 Analysis Port
- [ ] Interface: 所有 DUT 端口信号连线无遗漏
- [ ] Interface: clocking block 的 `default input #1step output #0` 时序正确

---

## 5. 常见问题排查

| 问题 | 可能原因 | 解决方案 |
|------|----------|----------|
| UVM_FATAL at build_phase | Agent 未注册或连线错误 | 检查 Factory 注册和 env 中的 `create` 调用 |
| Scoreboard 无数据 | Monitor 未连接 Analysis Port | 检查 `connect_phase` 中 AP 连接 |
| 覆盖率始终为 0 | `sample()` 未被调用 | 在 Monitor 的 `write()` 中添加 `fcov.sample(tr)` |
| 编译通过但仿真 hang | Driver 死循环等待 ready | 添加 timeout 机制或检查 DUT ready 逻辑 |
| Transaction 比对全部 mismatch | compare() 字段顺序错误 | 检查 exp/act 的字段映射关系 |
