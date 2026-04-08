#!/usr/bin/env python3
"""init_analysis.py — 环境分析文档框架生成器

解析 avis.log，自动生成 07_{DUT}_env_analysis.md 框架文档。

用法: python3 init_analysis.py --dut <DUT>
"""

import argparse
import os
import sys
from typing import Dict, List

# Import shared utilities
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from formal_skill_utils import (
    get_out_dir, parse_avis_log, backup_if_exists, ensure_parent_dir
)

OUT_DIR = get_out_dir()


def get_default_paths(dut: str):
    return {
        "log": os.path.join(OUT_DIR, "tests", "avis.log"),
        "output": os.path.join(OUT_DIR, f"07_{dut}_env_analysis.md"),
    }


def generate_tt_entry(idx: int, prop_name: str) -> str:
    return f"""### <TT-{idx:03d}> {prop_name}
- **属性名**: {prop_name}
- **SVA 代码**:
  ```systemverilog
  // [LLM-TODO]: 从 checker.sv 中提取对应属性的完整代码
  ```
- **根因分类**: [LLM-TODO: ASSUME_TOO_STRONG | SIGNAL_CONSTANT | WRAPPER_ERROR | DESIGN_EXPECTED]
- **关联 Assume**: [LLM-TODO: M_CK_YYY 或 N/A]
- **分析**: [LLM-TODO: 具体描述为何此属性 trivially true]
- **修复动作**: [LLM-TODO: FIXED | ACCEPTED]
- **修复说明**: [LLM-TODO: 描述修改内容或接受理由]
"""


def generate_fa_entry(idx: int, prop_name: str, prop_type: str) -> str:
    return f"""### <FA-{idx:03d}> {prop_name}
- **属性名**: {prop_name}
- **属性类型**: {prop_type}
- **SVA 代码**:
  ```systemverilog
  // [LLM-TODO]: 从 checker.sv 中提取对应属性的完整代码
  ```
- **判定结果**: [LLM-TODO: RTL_BUG | ENV_ISSUE | COVER_EXPECTED_FAIL]
- **反例/分析**: [LLM-TODO: 描述反例中的信号值和时序关系]
- **修复动作**: [LLM-TODO: MARKED_RTL_BUG | ASSUME_ADDED | ASSUME_MODIFIED | COVER_EXPECTED_FAIL]
- **修复说明**: [LLM-TODO: 具体描述修复内容或标记原因]
"""


def generate_document(dut_name: str, log_result: Dict[str, list]) -> str:
    n_pass = len(log_result["pass"])
    n_tt = len(log_result["trivially_true"])
    n_false = len(log_result["false"])
    n_cover_pass = len(log_result["cover_pass"])
    n_cover_fail = len(log_result["cover_fail"])
    n_total = n_pass + n_tt + n_false + n_cover_pass + n_cover_fail

    lines: List[str] = []
    lines.append(f"# {dut_name} 形式化验证环境分析报告\n")
    lines.append("> **由 init_analysis.py 自动生成** — [LLM-TODO] 标记处需要人工填写\n")
    lines.append("---\n")

    lines.append("## 1. 验证结果概览\n")
    lines.append("| 类型 | 数量 |")
    lines.append("|------|------|")
    lines.append(f"| Assert Pass | {n_pass} |")
    lines.append(f"| Assert TRIVIALLY_TRUE | {n_tt} |")
    lines.append(f"| Assert Fail | {n_false} |")
    lines.append(f"| Cover Pass | {n_cover_pass} |")
    lines.append(f"| Cover Fail | {n_cover_fail} |")
    lines.append(f"| **Total** | **{n_total}** |")
    lines.append("")
    lines.append("---\n")

    lines.append("## 2. TRIVIALLY_TRUE 属性分析\n")
    if n_tt == 0:
        lines.append("> 无 TRIVIALLY_TRUE 属性，验证环境约束健康。\n")
    else:
        lines.append(f"> 共 {n_tt} 个 TRIVIALLY_TRUE 属性需要分析。\n")
        for i, prop in enumerate(log_result["trivially_true"], start=1):
            lines.append(generate_tt_entry(i, prop))
    lines.append("---\n")

    lines.append("## 3. FALSE 属性分析\n")
    false_props = [(p, "assert") for p in log_result["false"]]
    false_props += [(p, "cover") for p in log_result["cover_fail"]]
    n_fa = len(false_props)
    if n_fa == 0:
        lines.append("> 无 FALSE 属性，所有断言和覆盖属性均已通过。\n")
    else:
        lines.append(f"> 共 {n_fa} 个 FALSE 属性需要分析。\n")
        for i, (prop, ptype) in enumerate(false_props, start=1):
            lines.append(generate_fa_entry(i, prop, ptype))
    lines.append("---\n")

    lines.append("## 4. 环境健康度总结\n")
    lines.append("| 指标 | 值 |")
    lines.append("|------|------|")
    lines.append(f"| TRIVIALLY_TRUE 已分析 | [LLM-TODO]/{n_tt} |")
    lines.append("| TRIVIALLY_TRUE 已修复 (FIXED) | [LLM-TODO] |")
    lines.append("| TRIVIALLY_TRUE 已接受 (ACCEPTED) | [LLM-TODO] |")
    lines.append("| ACCEPTED 比例 | [LLM-TODO]% |")
    lines.append(f"| FALSE 已分析 | [LLM-TODO]/{n_fa} |")
    lines.append("| FALSE 判定为 RTL_BUG | [LLM-TODO] |")
    lines.append("| FALSE 判定为 ENV_ISSUE | [LLM-TODO] |")
    lines.append("| FALSE 判定为 COVER_EXPECTED_FAIL | [LLM-TODO] |")
    lines.append("| 未修复的 ENV_ISSUE | [LLM-TODO] |")
    lines.append("")
    lines.append("**环境声明**: [LLM-TODO: ✅ 所有异常属性已分析完成 | ❌ 仍有 N 个属性未分析]")
    lines.append("")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="生成环境分析文档框架")
    parser.add_argument("--dut", required=True, help="DUT 名称")
    parser.add_argument("--log", default=None, help="avis.log 路径（可选）")
    parser.add_argument("--output", default=None, help="输出路径（可选）")
    args = parser.parse_args()

    paths = get_default_paths(args.dut)
    log_path = args.log or paths["log"]
    output_path = args.output or paths["output"]

    if not os.path.exists(log_path):
        print(f"错误: 日志文件不存在: {log_path}", file=sys.stderr)
        sys.exit(1)

    log_result = parse_avis_log(log_path)
    backup_if_exists(output_path)
    ensure_parent_dir(output_path)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(generate_document(args.dut, log_result))

    n_tt = len(log_result["trivially_true"])
    n_false = len(log_result["false"]) + len(log_result["cover_fail"])
    print(f"✅ 文档框架已生成: {output_path}")
    print(f"   - TRIVIALLY_TRUE 条目: {n_tt}")
    print(f"   - FALSE 条目: {n_false}")
    print(f"   - 共需填写 {n_tt + n_false} 个 [LLM-TODO] 条目")


if __name__ == "__main__":
    main()
