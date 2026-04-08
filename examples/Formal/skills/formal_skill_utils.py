"""formal_skill_utils.py — 形式化验证 Skill 共享工具函数

所有 Skill 脚本共享的工具函数集中在此，避免代码重复。
脚本通过 sys.path 引入本模块。

提供:
    - parse_avis_log(): 解析 avis.log
    - extract_rtl_bug_from_analysis_doc(): 从分析文档提取 RTL_BUG
    - get_default_paths(): 按约定推导路径
    - backup_if_exists(): 备份已有文件
"""

import os
import re
import shutil
from typing import Dict, List, Tuple

# ---- Path conventions ----
OUT_DIR = "unity_test"


def get_out_dir() -> str:
    """Return the output directory name."""
    return OUT_DIR


def backup_if_exists(filepath: str) -> None:
    """If file exists, copy to .bak and print message."""
    if os.path.exists(filepath):
        bak = filepath + ".bak"
        shutil.copy2(filepath, bak)
        print(f"已备份: {filepath} -> {bak}")


def ensure_parent_dir(filepath: str) -> None:
    """Ensure the parent directory of filepath exists."""
    os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)


def parse_avis_log(log_path: str) -> Dict[str, list]:
    """Parse avis.log and return property result statistics.

    Returns a dict with keys:
        pass, trivially_true, false, cover_pass, cover_fail
    """
    result: Dict[str, list] = {
        "pass": [],
        "trivially_true": [],
        "false": [],
        "cover_pass": [],
        "cover_fail": [],
    }

    if not os.path.exists(log_path):
        return result

    with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    def _is_cover(name: str) -> bool:
        return name.startswith("C_") or "COVER" in name.upper()

    def _record(prop: str, status: str) -> None:
        is_cov = _is_cover(prop)
        if status in ("TrivT", "TRIVIALLY_TRUE"):
            if not is_cov:
                result["trivially_true"].append(prop)
        elif status in ("Fail", "FALSE"):
            (result["cover_fail"] if is_cov else result["false"]).append(prop)
        elif status in ("Pass", "TRUE"):
            (result["cover_pass"] if is_cov else result["pass"]).append(prop)

    # Strategy 1: summary table
    table_re = re.compile(
        r"^\s*\d+\s+(checker_inst\.[\w.]+)\s*:\s*(TrivT|Fail|Pass|Undec)",
        re.MULTILINE,
    )
    for m in table_re.finditer(content):
        prop = m.group(1).split(".")[-1]
        _record(prop, m.group(2))

    # Strategy 2: Info-P016
    if not any(result[k] for k in ("pass", "trivially_true", "false")):
        p016_re = re.compile(
            r"Info-P016:\s*property\s+(checker_inst\.[\w.]+)\s+is\s+"
            r"(TRIVIALLY_TRUE|TRUE|FALSE)",
            re.IGNORECASE,
        )
        for m in p016_re.finditer(content):
            prop = m.group(1).split(".")[-1]
            _record(prop, m.group(2).upper())

    # Strategy 3: Info-P014
    if not any(result[k] for k in ("pass", "trivially_true", "false")):
        p014_re = re.compile(
            r"Info-P014:\s*property\s+(false|true):\s+(checker_inst\.[\w.]+)",
            re.IGNORECASE,
        )
        for m in p014_re.finditer(content):
            prop = m.group(2).split(".")[-1]
            status = "FALSE" if m.group(1).lower() == "false" else "TRUE"
            _record(prop, status)

    return result


def extract_rtl_bug_from_analysis_doc(analysis_path: str) -> List[Tuple[str, str]]:
    """Extract RTL_BUG property names and FA IDs from the analysis doc.

    Returns list of (fa_id, prop_name) tuples.
    """
    if not os.path.exists(analysis_path):
        return []

    with open(analysis_path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    rtl_bugs: List[Tuple[str, str]] = []
    fa_pattern = re.compile(r"###\s*<(FA-\d+)>\s+(\S+)", re.MULTILINE)

    for match in fa_pattern.finditer(content):
        fa_id = match.group(1)
        prop_name = match.group(2)
        entry_start = match.end()
        next_entry = fa_pattern.search(content, entry_start)
        entry_end = next_entry.start() if next_entry else len(content)
        entry_block = content[entry_start:entry_end]

        if re.search(r"(?:判定结果|Judgment)\s*[：:]\s*.*RTL_BUG", entry_block):
            rtl_bugs.append((fa_id, prop_name))

    return rtl_bugs
