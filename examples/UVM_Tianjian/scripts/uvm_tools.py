import os
import json
import subprocess
import configparser
import re
from typing import Dict, List, Optional, Tuple

import psutil
from pydantic import BaseModel, Field
from ucagent.tools.uctool import UCTool
from ucagent.tools.fileops import BaseReadWrite
from ucagent.util.log import str_error, str_info


# =============================================================================
# Shared Utilities
# =============================================================================

def _terminate_process_tree(proc: subprocess.Popen, timeout: int = 5) -> None:
    """Gracefully terminate a process and all its children."""
    try:
        parent = psutil.Process(proc.pid)
        children = parent.children(recursive=True)
        for child in children:
            try:
                child.terminate()
            except psutil.NoSuchProcess:
                pass
        try:
            parent.terminate()
        except psutil.NoSuchProcess:
            pass
        gone, alive = psutil.wait_procs(children + [parent], timeout=timeout)
        for p in alive:
            try:
                p.kill()
            except psutil.NoSuchProcess:
                pass
    except psutil.NoSuchProcess:
        pass
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass


def _run_subprocess(
    cmd: list,
    cwd: str,
    timeout: int = 300,
    env: dict = None,
) -> Tuple[int, str, str]:
    """Run a subprocess with timeout and return (returncode, stdout, stderr).

    Handles timeout by killing the process tree. Returns returncode=-1 on timeout.
    """
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=cwd,
            env=merged_env,
        )
        try:
            stdout, stderr = proc.communicate(timeout=timeout)
            return proc.returncode, stdout, stderr
        except subprocess.TimeoutExpired:
            _terminate_process_tree(proc)
            proc.communicate()
            return -1, "", f"Process timed out after {timeout}s"
    except FileNotFoundError as e:
        return -2, "", f"Command not found: {e}"
    except Exception as e:
        return -3, "", f"Unexpected error: {e}"


def _extract_log_summary(content: str, max_lines: int = 20) -> str:
    """Extract error/warning summary from EDA tool output."""
    error_lines = []
    warning_lines = []
    for line in content.splitlines():
        line_stripped = line.strip()
        if not line_stripped:
            continue
        line_upper = line_stripped.upper()
        if "ERROR" in line_upper or "FATAL" in line_upper:
            error_lines.append(line_stripped)
        elif "WARNING" in line_upper or "WARN" in line_upper:
            warning_lines.append(line_stripped)

    summary_parts = []
    if error_lines:
        summary_parts.append(f"Errors ({len(error_lines)}):")
        for line in error_lines[:max_lines]:
            summary_parts.append(f"  {line}")
        if len(error_lines) > max_lines:
            summary_parts.append(f"  ... and {len(error_lines) - max_lines} more errors")
    if warning_lines:
        summary_parts.append(f"Warnings ({len(warning_lines)}):")
        for line in warning_lines[:max(5, max_lines - len(error_lines))]:
            summary_parts.append(f"  {line}")

    return "\n".join(summary_parts) if summary_parts else "No errors or warnings found."


# =============================================================================
# Tool: GenerateTianjianIni
# =============================================================================

class ArgGenerateTianjianIni(BaseModel):
    env_name: str = Field(description="环境名称，如 data_bypass")
    env_level: str = Field(description="验证等级: ut/it/bt/st")
    rtl_top_name: str = Field(description="RTL 顶层模块名")
    prj_path: str = Field(description="工程输出目录路径")
    author: str = Field(description="作者名")
    agents: str = Field(description="JSON 格式的 Agent 列表定义")

class GenerateTianjianIni(BaseReadWrite, UCTool):
    """
    根据 Agent 规划文档中的结构化信息，安全生成天箭规范的 env_cfg.ini 文件。
    """
    args_schema: type[BaseModel] = ArgGenerateTianjianIni
    name: str = "GenerateTianjianIni"

    def _execute(self, **kwargs) -> str:
        env_name = kwargs.get('env_name')
        env_level = kwargs.get('env_level')
        rtl_top_name = kwargs.get('rtl_top_name')
        prj_path = kwargs.get('prj_path')
        author = kwargs.get('author')
        agents_str = kwargs.get('agents', '[]')
        
        try:
            agents = json.loads(agents_str)
        except json.JSONDecodeError:
            return str_error("agents 参数不是合法的 JSON 字符串。")

        config = configparser.ConfigParser()
        config.optionxform = str  # 保持大小写
        
        config['ENV_GENERAL'] = {
            'prj_path': prj_path,
            'author': author,
            'env_name': env_name,
            'env_level': env_level,
            'rtl_top_name': rtl_top_name,
            'u_rtl_top_name': f"u_{rtl_top_name}",
            'rtl_list': f"{rtl_top_name}.sv"
        }
        
        for agent in agents:
            sec_name = f"{agent.get('agent_name').upper()}_AGENT"
            config[sec_name] = {
                'agent_mode': agent.get('agent_mode', 'master'),
                'instance_by': agent.get('instance_by', 'self'),
                'instance_num': str(agent.get('instance_num', 1)),
                'agent_interface_list': agent.get('interface_list', ''),
                'dut_interface_list': agent.get('dut_list', ''),
                'scb_port_sel': agent.get('scb_port_sel', 'exp')
            }
            
        os.makedirs(prj_path, exist_ok=True)
        ini_path = os.path.join(prj_path, "env_cfg.ini")
        with open(ini_path, 'w', encoding='utf-8') as f:
            config.write(f)

        # Verify the written file can be parsed back
        verify_config = configparser.ConfigParser()
        verify_config.optionxform = str
        try:
            verify_config.read(ini_path)
        except Exception as e:
            return str_error(f"Generated ini file failed verification: {e}")

        agent_count = len([s for s in config.sections() if s.endswith('_AGENT')])
        return str_info(
            f"Successfully generated Tianjian INI file at: {ini_path}\n"
            f"  env_name: {env_name}, env_level: {env_level}\n"
            f"  rtl_top: {rtl_top_name}, agents: {agent_count}"
        )


# =============================================================================
# Tool: RunTianjianGen
# =============================================================================

class ArgRunTianjianGen(BaseModel):
    ini_file: str = Field(description="env_cfg.ini 文件路径")
    output_dir: str = Field(description="生成结果输出目录")

class RunTianjianGen(UCTool):
    """
    调用天箭 gen_env.py 脚本执行 UVM 环境生成，捕获并返回执行日志。
    """
    args_schema: type[BaseModel] = ArgRunTianjianGen
    name: str = "RunTianjianGen"

    @staticmethod
    def _get_gen_script() -> str:
        """Return the absolute path to gen_env.py (sibling tianjian/ directory)."""
        return os.path.normpath(
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "tianjian", "gen_env.py")
        )

    def _execute(self, **kwargs) -> str:
        ini_file = kwargs.get('ini_file')
        output_dir = kwargs.get('output_dir')
        
        if not os.path.exists(ini_file):
            return str_error(f"ini file not found: {ini_file}")

        gen_script = self._get_gen_script()
        if not os.path.isfile(gen_script):
            return str_error(
                f"gen_env.py not found at: {gen_script}. "
                f"Please place Tianjian under scripts/tianjian/."
            )

        os.makedirs(output_dir, exist_ok=True)

        # Execute: python3 gen_env.py <ini_file>
        ini_abs = os.path.abspath(ini_file)
        cmd = ["python3", gen_script, ini_abs]

        str_info(f"Executing: {' '.join(cmd)} in {output_dir}")
        returncode, stdout, stderr = _run_subprocess(
            cmd, cwd=output_dir, timeout=60
        )

        if returncode == -1:
            return str_error(f"❌ Tianjian gen_env.py timed out (>60s).\nstderr: {stderr[:500]}")
        if returncode == -2:
            return str_error(f"❌ Command not found: {stderr}")
        if returncode != 0:
            return str_error(
                f"❌ gen_env.py exited with code {returncode}.\n"
                f"stderr:\n{stderr[:1000]}\n"
                f"stdout:\n{stdout[:500]}"
            )

        # List generated directories
        generated_dirs = []
        if os.path.isdir(output_dir):
            for entry in os.listdir(output_dir):
                full_path = os.path.join(output_dir, entry)
                if os.path.isdir(full_path):
                    generated_dirs.append(entry)

        return str_info(
            f"✅ Tianjian gen_env.py executed successfully.\n"
            f"  ini: {ini_file}\n"
            f"  output: {output_dir}\n"
            f"  generated dirs: {', '.join(generated_dirs) if generated_dirs else 'none'}\n"
            f"stdout:\n{stdout[:500]}"
        )


# =============================================================================
# Tool: RunUVMCompile
# =============================================================================

class ArgRunUVMCompile(BaseModel):
    work_dir: str = Field(description="Makefile 所在目录")
    make_target: str = Field(default="compile", description="编译目标")
    tool: str = Field(default="vcs", description="仿真器: vcs / xrun / verilator")

class RunUVMCompile(UCTool):
    """
    调用 EDA 工具编译 UVM 环境，返回编译结果。
    """
    args_schema: type[BaseModel] = ArgRunUVMCompile
    name: str = "RunUVMCompile"

    def _execute(self, **kwargs) -> str:
        work_dir = kwargs.get('work_dir')
        make_target = kwargs.get('make_target', 'compile')
        tool = kwargs.get('tool', 'vcs')

        if not os.path.isdir(work_dir):
            return str_error(f"Work directory does not exist: {work_dir}")

        # Check for Makefile
        makefile_path = os.path.join(work_dir, "Makefile")
        if not os.path.isfile(makefile_path):
            # Also check for makefile (lowercase)
            makefile_path = os.path.join(work_dir, "makefile")
            if not os.path.isfile(makefile_path):
                return str_error(f"No Makefile found in {work_dir}")

        cmd = ["make", make_target, f"TOOL={tool}"]
        str_info(f"Compiling: {' '.join(cmd)} in {work_dir}")

        returncode, stdout, stderr = _run_subprocess(
            cmd, cwd=work_dir, timeout=300
        )

        combined_output = stdout + "\n" + stderr
        summary = _extract_log_summary(combined_output)

        if returncode == -1:
            return str_error(f"❌ Compilation timed out (>300s).\n{summary}")
        if returncode != 0:
            return str_error(
                f"❌ Compilation failed (exit code {returncode}).\n"
                f"{summary}\n"
                f"Last 10 lines of output:\n"
                f"{''.join(combined_output.splitlines()[-10:])}"
            )

        return str_info(
            f"✅ Compilation successful: make {make_target} TOOL={tool}\n"
            f"  work_dir: {work_dir}\n"
            f"{summary}"
        )


# =============================================================================
# Tool: RunUVMSim
# =============================================================================

class ArgRunUVMSim(BaseModel):
    work_dir: str = Field(description="Makefile 所在目录")
    test_name: str = Field(description="测试用例名称")
    seed: int = Field(default=0, description="随机种子（0 = 自动）")
    timeout: int = Field(default=300, description="超时秒数")

class RunUVMSim(UCTool):
    """
    执行指定 testcase 的 UVM 仿真，返回日志关键片段。
    """
    args_schema: type[BaseModel] = ArgRunUVMSim
    name: str = "RunUVMSim"

    def _parse_sim_log(self, log_content: str) -> Dict:
        """Parse UVM simulation log and extract key metrics."""
        result = {
            "fatal_count": 0,
            "error_count": 0,
            "warning_count": 0,
            "test_passed": False,
            "fatal_messages": [],
            "error_messages": [],
        }

        for line in log_content.splitlines():
            line_stripped = line.strip()
            if "UVM_FATAL" in line_stripped:
                result["fatal_count"] += 1
                if len(result["fatal_messages"]) < 5:
                    result["fatal_messages"].append(line_stripped)
            elif "UVM_ERROR" in line_stripped:
                result["error_count"] += 1
                if len(result["error_messages"]) < 10:
                    result["error_messages"].append(line_stripped)
            elif "UVM_WARNING" in line_stripped:
                result["warning_count"] += 1

            if "UVM_TEST_PASSED" in line_stripped or "UVM_TEST_DONE" in line_stripped:
                result["test_passed"] = True
            # Also check for report summary
            if "Report Summary: 0 UVM_ERROR" in line_stripped:
                result["test_passed"] = True

        return result

    def _find_sim_log(self, work_dir: str, test_name: str, seed: int) -> Optional[str]:
        """Try to find the simulation log file."""
        candidates = [
            os.path.join(work_dir, f"sim_{test_name}.log"),
            os.path.join(work_dir, f"{test_name}.log"),
            os.path.join(work_dir, "sim", f"{test_name}_seed{seed}", "sim.log"),
            os.path.join(work_dir, "sim", f"{test_name}", "sim.log"),
            os.path.join(work_dir, "logs", f"{test_name}.log"),
        ]
        for c in candidates:
            if os.path.isfile(c):
                return c
        return None

    def _execute(self, **kwargs) -> str:
        work_dir = kwargs.get('work_dir')
        test_name = kwargs.get('test_name')
        seed = kwargs.get('seed', 0)
        timeout = kwargs.get('timeout', 300)

        if not os.path.isdir(work_dir):
            return str_error(f"Work directory does not exist: {work_dir}")

        cmd = ["make", "sim", f"TESTNAME={test_name}", f"SEED={seed}"]
        str_info(f"Simulating: {' '.join(cmd)} in {work_dir}")

        returncode, stdout, stderr = _run_subprocess(
            cmd, cwd=work_dir, timeout=timeout
        )

        if returncode == -1:
            return str_error(
                f"❌ Simulation timed out (>{timeout}s) for test '{test_name}' (seed={seed})."
            )

        # Try to find and parse the simulation log
        combined_output = stdout + "\n" + stderr
        log_file = self._find_sim_log(work_dir, test_name, seed)

        if log_file and os.path.isfile(log_file):
            with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                log_content = f.read()
        else:
            # Use stdout/stderr as fallback
            log_content = combined_output

        parsed = self._parse_sim_log(log_content)

        # Build result message
        lines = [
            f"Simulation completed for test '{test_name}' (seed={seed}), exit code={returncode}",
        ]

        if log_file:
            lines.append(f"Log file: {log_file}")

        if parsed["test_passed"] and parsed["fatal_count"] == 0 and parsed["error_count"] == 0:
            lines.insert(0, "✅")
            lines.append("Result: PASSED")
        else:
            lines.insert(0, "❌")
            lines.append("Result: FAILED")

        lines.append(f"UVM_FATAL: {parsed['fatal_count']}, UVM_ERROR: {parsed['error_count']}, UVM_WARNING: {parsed['warning_count']}")

        if parsed["fatal_messages"]:
            lines.append("Fatal messages:")
            for msg in parsed["fatal_messages"]:
                lines.append(f"  {msg}")

        if parsed["error_messages"]:
            lines.append("Error messages:")
            for msg in parsed["error_messages"]:
                lines.append(f"  {msg}")

        result_str = "\n".join(lines)
        if parsed["test_passed"] and parsed["fatal_count"] == 0:
            return str_info(result_str)
        else:
            return str_error(result_str)


# =============================================================================
# Tool: RunUVMRegression
# =============================================================================

class ArgRunUVMRegression(BaseModel):
    work_dir: str = Field(description="Makefile 所在目录")
    test_list: str = Field(description="测试列表文件路径或逗号分隔的 test 名")
    num_seeds: int = Field(default=5, description="每个 test 跑多少 seed")
    timeout: int = Field(default=300, description="单个仿真超时")

class RunUVMRegression(UCTool):
    """
    批量多 seed 回归仿真。
    """
    args_schema: type[BaseModel] = ArgRunUVMRegression
    name: str = "RunUVMRegression"

    def _execute(self, **kwargs) -> str:
        work_dir = kwargs.get('work_dir')
        test_list_str = kwargs.get('test_list', '')
        num_seeds = kwargs.get('num_seeds', 5)
        timeout = kwargs.get('timeout', 300)

        if not os.path.isdir(work_dir):
            return str_error(f"Work directory does not exist: {work_dir}")

        # Parse test list
        test_names = []
        if os.path.isfile(test_list_str):
            with open(test_list_str, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        test_names.append(line)
        else:
            test_names = [t.strip() for t in test_list_str.split(',') if t.strip()]

        if not test_names:
            return str_error("No test names found in test_list.")

        total = len(test_names) * num_seeds
        passed = 0
        failed = 0
        timed_out = 0
        failed_list = []

        for test_name in test_names:
            for seed_idx in range(num_seeds):
                seed = seed_idx + 1
                cmd = ["make", "sim", f"TESTNAME={test_name}", f"SEED={seed}"]
                returncode, stdout, stderr = _run_subprocess(
                    cmd, cwd=work_dir, timeout=timeout
                )

                combined = stdout + "\n" + stderr
                if returncode == -1:
                    timed_out += 1
                    failed_list.append(f"{test_name} (seed={seed}): TIMEOUT")
                elif "UVM_TEST_PASSED" in combined or "Report Summary: 0 UVM_ERROR" in combined:
                    passed += 1
                else:
                    failed += 1
                    failed_list.append(f"{test_name} (seed={seed}): FAIL (exit={returncode})")

        lines = [
            f"Regression completed: {len(test_names)} tests × {num_seeds} seeds = {total} runs",
            f"  Passed: {passed}, Failed: {failed}, Timeout: {timed_out}",
        ]

        if failed_list:
            lines.append(f"Failed tests ({len(failed_list)}):")
            for item in failed_list[:20]:
                lines.append(f"  - {item}")
            if len(failed_list) > 20:
                lines.append(f"  ... and {len(failed_list) - 20} more")

        result_str = "\n".join(lines)
        if failed == 0 and timed_out == 0:
            return str_info("✅ " + result_str)
        else:
            return str_error("❌ " + result_str)


# =============================================================================
# Tool: ExtractCoverageMetrics
# =============================================================================

class ArgExtractCoverageMetrics(BaseModel):
    report_path: str = Field(description="覆盖率报告路径（urg 目录或文本文件）")
    report_format: str = Field(default="vcs_urg", description="格式类型: vcs_urg / text")

class ExtractCoverageMetrics(UCTool):
    """
    解析 EDA 工具生成的覆盖率报告，返回各维度百分比。
    """
    args_schema: type[BaseModel] = ArgExtractCoverageMetrics
    name: str = "ExtractCoverageMetrics"

    def _parse_urg_report(self, report_path: str) -> Dict:
        """Parse VCS urgReport directory for coverage metrics."""
        data = {}
        # Look for dashboard.txt or modlist.txt in urgReport
        candidates = [
            os.path.join(report_path, "dashboard.txt"),
            os.path.join(report_path, "modlist.txt"),
            os.path.join(report_path, "grpinfo.txt"),
        ]

        content = ""
        for f in candidates:
            if os.path.isfile(f):
                with open(f, 'r', encoding='utf-8', errors='ignore') as fh:
                    content += fh.read() + "\n"

        if not content:
            # Try to find any .txt file
            if os.path.isdir(report_path):
                for fname in os.listdir(report_path):
                    if fname.endswith('.txt'):
                        fpath = os.path.join(report_path, fname)
                        with open(fpath, 'r', encoding='utf-8', errors='ignore') as fh:
                            content += fh.read() + "\n"

        # Parse coverage percentages from content
        metrics = {
            "line": self._extract_pct(content, r'(?:line|statement)\s*(?:coverage)?\s*[:=]\s*([\d.]+)\s*%'),
            "cond": self._extract_pct(content, r'(?:cond|condition|branch)\s*(?:coverage)?\s*[:=]\s*([\d.]+)\s*%'),
            "toggle": self._extract_pct(content, r'toggle\s*(?:coverage)?\s*[:=]\s*([\d.]+)\s*%'),
            "fsm": self._extract_pct(content, r'fsm\s*(?:coverage)?\s*[:=]\s*([\d.]+)\s*%'),
            "branch": self._extract_pct(content, r'branch\s*(?:coverage)?\s*[:=]\s*([\d.]+)\s*%'),
            "fcov": self._extract_pct(content, r'(?:functional|fcov|group)\s*(?:coverage)?\s*[:=]\s*([\d.]+)\s*%'),
        }

        return metrics

    def _extract_pct(self, content: str, pattern: str) -> Optional[float]:
        """Extract percentage from content using regex pattern."""
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                return None
        return None

    def _parse_text_report(self, report_path: str) -> Dict:
        """Parse plain text coverage report."""
        if not os.path.isfile(report_path):
            return {}
        with open(report_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        return {
            "line": self._extract_pct(content, r'line\s*[:=]\s*([\d.]+)\s*%'),
            "cond": self._extract_pct(content, r'cond\s*[:=]\s*([\d.]+)\s*%'),
            "toggle": self._extract_pct(content, r'toggle\s*[:=]\s*([\d.]+)\s*%'),
            "fsm": self._extract_pct(content, r'fsm\s*[:=]\s*([\d.]+)\s*%'),
            "branch": self._extract_pct(content, r'branch\s*[:=]\s*([\d.]+)\s*%'),
            "fcov": self._extract_pct(content, r'(?:functional|fcov)\s*[:=]\s*([\d.]+)\s*%'),
        }

    def _execute(self, **kwargs) -> str:
        report_path = kwargs.get('report_path')
        report_format = kwargs.get('report_format', 'vcs_urg')

        if not os.path.exists(report_path):
            return str_error(f"Coverage report not found: {report_path}")

        if report_format == 'vcs_urg':
            metrics = self._parse_urg_report(report_path)
        else:
            metrics = self._parse_text_report(report_path)

        # Calculate summary
        valid_metrics = {k: v for k, v in metrics.items() if v is not None}
        if not valid_metrics:
            return str_error(
                f"Could not extract any coverage metrics from {report_path}. "
                f"The report format may not be recognized."
            )

        threshold = 90.0
        met_count = sum(1 for v in valid_metrics.values() if v >= threshold)
        total_count = len(valid_metrics)

        metrics["summary"] = f"{met_count}/{total_count} dimensions meet {threshold}% threshold"

        return json.dumps(metrics, indent=2)
