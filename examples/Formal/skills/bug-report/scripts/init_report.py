#!/usr/bin/env python3
"""init_report.py — Bug 报告文档框架生成器

解析环境分析文档中的 RTL_BUG 属性，生成 04_{DUT}_bug_report.md 框架。

用法: python3 init_report.py --dut <DUT>
"""

import argparse
import os
import sys
from typing import List, Tuple

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from formal_skill_utils import (
    get_out_dir, extract_rtl_bug_from_analysis_doc, backup_if_exists, ensure_parent_dir
)

OUT_DIR = get_out_dir()


def get_default_paths(dut: str):
    return {
        "analysis_doc": os.path.join(OUT_DIR, f"07_{dut}_env_analysis.md"),
        "output": os.path.join(OUT_DIR, f"04_{dut}_bug_report.md"),
    }


def generate_bug_entry(idx: int, fa_id: str, prop_name: str) -> str:
    ck_part = prop_name
    for prefix in ("A_CK_", "M_CK_", "C_CK_", "A_", "M_", "C_"):
        if ck_part.startswith(prefix):
            ck_part = ck_part[len(prefix):]
            break
    bg_name = f"BG-FORMAL-{idx:03d}-{ck_part.replace('_', '-')}"

    return f"""[LLM-TODO: <FG-???> 关联的功能组]

[LLM-TODO: <FC-???> 关联的功能点]

### <{bg_name}> [LLM-TODO: 缺陷标题]

[LLM-TODO: <CK-???> 关联的检测点]

<TC-FORMAL-{idx:03d}> 形式化验证反例证实（对应 {fa_id}: {prop_name}）

[LLM-TODO: <FILE-RTL文件路径:行号>]

**问题描述**: [LLM-TODO]
**根本原因**: [LLM-TODO]
**触发条件**: [LLM-TODO]
**预期行为**: [LLM-TODO]
**实际行为**: [LLM-TODO]
**修复建议**: [LLM-TODO]
**反例波形解读**: [LLM-TODO]
**影响范围**: [LLM-TODO: 严重 | 中等 | 低]
**置信度**: [LLM-TODO: 高 | 中 | 低]
**优先级**: [LLM-TODO: 最高 | 高 | 中 | 低]

---
"""


def generate_document(dut_name: str, rtl_bugs: List[Tuple[str, str]]) -> str:
    lines: List[str] = []
    lines.append(f"# {dut_name} 形式化验证缺陷报告\n")

    if not rtl_bugs:
        lines.append("形式化验证未发现 RTL 设计缺陷，所有属性已通过证明。\n")
        return "\n".join(lines)

    lines.append("> **由 init_report.py 自动生成** — [LLM-TODO] 标记处需要人工填写\n")
    lines.append(f"本报告记录了 {len(rtl_bugs)} 个 RTL 缺陷。\n")
    lines.append("---\n")

    for i, (fa_id, prop_name) in enumerate(rtl_bugs, start=1):
        lines.append(generate_bug_entry(i, fa_id, prop_name))

    lines.append("## 缺陷统计汇总\n")
    lines.append("| 序号 | BG 标签 | 对应属性 | 来源 | 影响范围 | 优先级 |")
    lines.append("|------|---------|----------|------|----------|--------|")
    for i, (fa_id, prop_name) in enumerate(rtl_bugs, start=1):
        ck_part = prop_name
        for prefix in ("A_CK_", "M_CK_", "C_CK_", "A_", "M_", "C_"):
            if ck_part.startswith(prefix):
                ck_part = ck_part[len(prefix):]
                break
        bg_name = f"BG-FORMAL-{i:03d}-{ck_part.replace('_', '-')}"
        lines.append(f"| {i} | {bg_name} | {prop_name} | {fa_id} | [LLM-TODO] | [LLM-TODO] |")
    lines.append("")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="生成 Bug 报告文档框架")
    parser.add_argument("--dut", required=True, help="DUT 名称")
    parser.add_argument("--analysis-doc", default=None, help="环境分析文档路径（可选）")
    parser.add_argument("--output", default=None, help="输出路径（可选）")
    args = parser.parse_args()

    paths = get_default_paths(args.dut)
    analysis_path = args.analysis_doc or paths["analysis_doc"]
    output_path = args.output or paths["output"]

    if not os.path.exists(analysis_path):
        print(f"错误: 环境分析文档不存在: {analysis_path}", file=sys.stderr)
        sys.exit(1)

    rtl_bugs = extract_rtl_bug_from_analysis_doc(analysis_path)
    backup_if_exists(output_path)
    ensure_parent_dir(output_path)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(generate_document(args.dut, rtl_bugs))

    print(f"✅ Bug 报告框架已生成: {output_path}")
    if rtl_bugs:
        print(f"   - RTL_BUG 数量: {len(rtl_bugs)}")
        for fa_id, prop_name in rtl_bugs:
            print(f"     • {fa_id}: {prop_name}")
    else:
        print("   - 无 RTL_BUG，已生成无缺陷声明文档")


if __name__ == "__main__":
    main()
