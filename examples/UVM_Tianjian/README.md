# README

## UVM Tianjian 自动化验证工作流

天箭（Tianjian）是一款强大的基于 Python 的自动化 UVM 生成引擎。本项目将其与 UCAgent 的大模型智能融合，实现了从阅读 RTL 源码，到自主理解协议规范、抽取驱动 Agent、自动建立仿真骨架、编写 Testcase、最终回归与收集覆盖率的全自动闭环验证。

### 目录结构

- `uvm.yaml`：验证工作流配置定义（9 个 Stage）
- `scripts/`：UCAgent 调用的各类自定义工具脚本 (Tools 与 Checkers)
- `Guide_Doc/`：提供给大语言模型的各种 UVM 模板和输出规范
- `uvm_workflow_plan.md`：详细的验证实施工作流指南

### 工作流大纲

1. 需求分析 (`requirement_analysis_and_planning`)
2. 功能理解 (`dut_function_understanding`)
3. 功能拆解与覆盖率点建立 (`functional_specification_analysis`)
4. 静态源码 Bug 扫描 (`static_bug_analysis`)
5. UVM 环境基线生成 (`tianjian_uvm_generation`)
6. 驱动、检测与记分板定制 (`uvm_environment_customization`)
7. 激励与用例开发 (`uvm_sequence_development`)
8. 批量回归与覆盖率迭代 (`regression_and_coverage`)
9. 验证闭环全景分析 (`verification_review_and_summary`)
