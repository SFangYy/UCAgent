---
name: bug-report
description: 自动解析环境分析文档中的 RTL_BUG 属性，生成 Bug 报告框架（04_{DUT}_bug_report.md），LLM 填写根因分析和修复建议。
---

# Bug 报告文档生成

## 概述

自动化生成 `{OUT}/04_{DUT}_bug_report.md`，从环境分析文档提取 RTL_BUG 属性，预填 BG 条目空壳，LLM 只需在 `[LLM-TODO]` 处填写根因分析、修复建议等。

## 步骤

### 1. 生成报告框架

使用 `RunSkillScript` 执行：

```bash
python3 <init_report.py的路径> --dut {DUT}
```

脚本自动从 `07_{DUT}_env_analysis.md` 提取 RTL_BUG，生成报告框架。无 RTL_BUG 时生成无缺陷声明。

### 2. 填写分析内容

打开生成的文档，逐条填写每个 `[LLM-TODO]` 标记处的内容。所有 `<FG-*>/<FC-*>/<CK-*>` 标签必须来自 `03_{DUT}_functions_and_checks.md`。

### 3. 完成后调用 Complete
