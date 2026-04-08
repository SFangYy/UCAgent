#!/usr/bin/env python3
"""init_testfile.py — 反例测试用例文件框架生成器

解析环境分析文档和 wrapper.sv，为每个 RTL_BUG 生成 Python 测试函数框架。

用法: python3 init_testfile.py --dut <DUT>
"""

import argparse
import os
import re
import sys
from typing import List, Optional, Tuple

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from formal_skill_utils import (
    get_out_dir, extract_rtl_bug_from_analysis_doc, backup_if_exists, ensure_parent_dir
)

OUT_DIR = get_out_dir()


def get_default_paths(dut: str):
    return {
        "analysis_doc": os.path.join(OUT_DIR, f"07_{dut}_env_analysis.md"),
        "wrapper": os.path.join(OUT_DIR, "tests", f"{dut}_wrapper.sv"),
        "output": os.path.join(OUT_DIR, "tests", f"test_{dut}_counterexample.py"),
    }


def parse_wrapper_clock_reset(wrapper_path: str) -> Tuple[Optional[str], Optional[str]]:
    """Parse wrapper.sv to extract RTL clock and reset port names."""
    clock_name = None
    reset_name = None

    if not os.path.exists(wrapper_path):
        return clock_name, reset_name

    with open(wrapper_path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    clk_match = re.search(r"wire\s+clk\s*=\s*(\w+)\s*;", content)
    if clk_match:
        clock_name = clk_match.group(1)

    rst_match = re.search(r"wire\s+rst_n\s*=\s*(\w+)\s*;", content)
    if rst_match:
        reset_name = rst_match.group(1)

    if clock_name is None:
        for pat in [r"input\s+(?:wire\s+)?(\w*cl(?:oc)?k\w*)", r"input\s+(?:wire\s+)?(clk\w*)"]:
            m = re.search(pat, content, re.IGNORECASE)
            if m:
                clock_name = m.group(1)
                break

    if reset_name is None:
        for pat in [r"input\s+(?:wire\s+)?(\w*res(?:et)?\w*)", r"input\s+(?:wire\s+)?(rst\w*)"]:
            m = re.search(pat, content, re.IGNORECASE)
            if m:
                reset_name = m.group(1)
                break

    return clock_name, reset_name


def prop_to_func_name(prop_name: str) -> str:
    name = prop_name.lower()
    for prefix in ("a_", "m_", "c_"):
        if name.startswith(prefix):
            name = name[len(prefix):]
            break
    return f"test_cex_{name}"


def generate_test_function(prop_name: str, fa_id: str,
                           clock_name: Optional[str],
                           reset_name: Optional[str],
                           dut_class: str) -> str:
    func_name = prop_to_func_name(prop_name)
    lines = []
    lines.append(f"def {func_name}():")
    lines.append(f'    """反例测试: {prop_name} (来源: {fa_id})')
    lines.append(f"    [LLM-TODO]: 补充 Bug 描述、反例条件、预期/实际行为")
    lines.append(f'    """')
    lines.append(f"    dut = DUT{dut_class}()")

    if clock_name:
        lines.append(f"    dut.InitClock('{clock_name}')")
        lines.append(f"    # 复位序列")
        if reset_name:
            lines.append(f"    dut.{reset_name}.value = 0")
            lines.append(f"    dut.Step(5)")
            lines.append(f"    dut.{reset_name}.value = 1")
        else:
            lines.append(f"    # [LLM-TODO]: 复位序列")
            lines.append(f"    dut.Step(5)")
        lines.append(f"    dut.Step(1)")

    lines.append(f"")
    lines.append(f"    # [LLM-TODO]: 按反例时序驱动引脚")
    lines.append(f"    dut.Step(1)")
    lines.append(f"")
    lines.append(f"    # [LLM-TODO]: 断言检查")
    lines.append(f"    # assert dut.yyy.value == expected")
    lines.append(f"")
    lines.append(f"    dut.Finish()")
    lines.append(f"")
    return "\n".join(lines)


def generate_file(dut_name: str, rtl_bugs: List[Tuple[str, str]],
                  clock_name: Optional[str], reset_name: Optional[str]) -> str:
    dut_class = dut_name[0].upper() + dut_name[1:] if dut_name else dut_name

    lines = []
    lines.append(f'"""形式化反例测试用例 — 由 init_testfile.py 自动生成"""')
    lines.append(f"")

    if not rtl_bugs:
        lines.append(f"# 形式化验证未发现 RTL 缺陷，无需生成反例测试用例")
        lines.append(f"")
        return "\n".join(lines)

    lines.append(f"from {dut_name} import DUT{dut_class}")
    lines.append(f"")
    lines.append(f"")

    for fa_id, prop_name in rtl_bugs:
        lines.append(generate_test_function(
            prop_name, fa_id, clock_name, reset_name, dut_class
        ))
        lines.append(f"")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="生成反例测试用例文件框架")
    parser.add_argument("--dut", required=True, help="DUT 名称")
    parser.add_argument("--analysis-doc", default=None, help="环境分析文档路径（可选）")
    parser.add_argument("--wrapper", default=None, help="wrapper.sv 路径（可选）")
    parser.add_argument("--output", default=None, help="输出路径（可选）")
    args = parser.parse_args()

    paths = get_default_paths(args.dut)
    analysis_path = args.analysis_doc or paths["analysis_doc"]
    wrapper_path = args.wrapper or paths["wrapper"]
    output_path = args.output or paths["output"]

    if not os.path.exists(analysis_path):
        print(f"错误: 环境分析文档不存在: {analysis_path}", file=sys.stderr)
        sys.exit(1)

    rtl_bugs = extract_rtl_bug_from_analysis_doc(analysis_path)
    clock_name, reset_name = parse_wrapper_clock_reset(wrapper_path)
    backup_if_exists(output_path)
    ensure_parent_dir(output_path)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(generate_file(args.dut, rtl_bugs, clock_name, reset_name))

    print(f"✅ 测试文件框架已生成: {output_path}")
    if rtl_bugs:
        print(f"   - RTL_BUG 数量: {len(rtl_bugs)}")
        print(f"   - 时钟: {clock_name or '[未识别]'}, 复位: {reset_name or '[未识别]'}")
        for fa_id, prop_name in rtl_bugs:
            print(f"     • {prop_to_func_name(prop_name)}() ← {fa_id}")
    else:
        print("   - 无 RTL_BUG，已生成空测试文件")


if __name__ == "__main__":
    main()
