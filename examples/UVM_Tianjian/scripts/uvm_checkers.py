import os
import re
import glob
import configparser
from ucagent.checkers.base import Checker


class TianjianIniSyntaxChecker(Checker):
    """校验生成的 env_cfg.ini 格式合法性。"""

    def __init__(self, ini_file: str, rtl_file: str = None, **kwargs):
        super().__init__(**kwargs)
        self.ini_file = ini_file

    def do_check(self, timeout=0, **kwargs) -> tuple[bool, object]:
        """检查天箭 env_cfg.ini 配置文件格式是否合法。"""
        if not os.path.exists(self.ini_file):
            return False, f"File {self.ini_file} does not exist."
        
        config = configparser.ConfigParser()
        config.optionxform = str
        try:
            config.read(self.ini_file)
        except Exception as e:
            return False, f"Failed to parse ini file: {e}"

        if 'ENV_GENERAL' not in config.sections():
            return False, "Missing [ENV_GENERAL] section."
        
        gen_sec = config['ENV_GENERAL']
        required_keys = ['prj_path', 'author', 'env_name', 'env_level',
                         'rtl_top_name', 'u_rtl_top_name', 'rtl_list']
        for k in required_keys:
            if k not in gen_sec:
                return False, f"Missing required key '{k}' in [ENV_GENERAL]"
            
        if gen_sec.get('env_level') not in ['st', 'it', 'bt', 'ut']:
            return False, "env_level must be one of st, it, bt, ut."

        valid_agents = set()
        agent_sections = [s for s in config.sections()
                          if s != 'ENV_GENERAL' and s.endswith('_AGENT')]
        
        for sec in agent_sections:
            agent_name = sec.replace('_AGENT', '').lower()
            valid_agents.add(agent_name)
            
        for sec in agent_sections:
            agent_sec = config[sec]
            if agent_sec.get('agent_mode') not in ['master', 'only_monitor']:
                return False, f"agent_mode in {sec} must be master or only_monitor."
            
            inst_by = agent_sec.get('instance_by', '').lower()
            if inst_by != 'self' and inst_by not in valid_agents:
                return False, f"instance_by in {sec} refers to unknown agent {inst_by}."

        return True, "Ini syntax check passed."


class TianjianOutputChecker(Checker):
    """校验天箭 gen_env.py 执行后生成的 UVM 目录树完整性。"""

    def __init__(self, ini_file: str, gen_output_dir: str, **kwargs):
        super().__init__(**kwargs)
        self.ini_file = ini_file
        self.gen_output_dir = gen_output_dir

    def do_check(self, timeout=0, **kwargs) -> tuple[bool, object]:
        """检查天箭生成的 UVM 目录树是否完整。"""
        if not os.path.exists(self.ini_file):
            return False, f"Ini file {self.ini_file} missing."
            
        config = configparser.ConfigParser()
        config.optionxform = str
        config.read(self.ini_file)
        
        env_name = config.get('ENV_GENERAL', 'env_name', fallback=None)
        if not env_name:
            return False, "No env_name found in ini."

        missing = []

        # Check common directory
        common_dir = os.path.join(self.gen_output_dir, f"{env_name}_common")
        if not os.path.isdir(common_dir):
            missing.append(f"{env_name}_common/")

        # Check env directory
        env_dir = os.path.join(self.gen_output_dir, f"{env_name}_env")
        if not os.path.isdir(env_dir):
            missing.append(f"{env_name}_env/")

        # Check each self-instanced Agent directory
        agent_sections = [s for s in config.sections()
                          if s != 'ENV_GENERAL' and s.endswith('_AGENT')]
        for sec in agent_sections:
            inst_by = config.get(sec, 'instance_by', fallback='self').lower()
            if inst_by == 'self':
                agent_name = sec.replace('_AGENT', '').lower()
                agent_dir = os.path.join(self.gen_output_dir, f"{agent_name}_agent")
                if not os.path.isdir(agent_dir):
                    missing.append(f"{agent_name}_agent/")

        if missing:
            return False, {
                "error": "Missing generated directories",
                "missing": missing,
                "hint": "Please run RunTianjianGen to generate the UVM directory tree."
            }
            
        return True, "UVM generation output check passed."


class UvmSyntaxChecker(Checker):
    """对 UVM SystemVerilog 文件进行基础语法校验。"""

    def __init__(self, target_file: str, **kwargs):
        super().__init__(**kwargs)
        self.target_file = target_file

    def do_check(self, timeout=0, **kwargs) -> tuple[bool, object]:
        """检查 UVM SystemVerilog 文件基础语法。"""
        if not os.path.exists(self.target_file):
            return False, f"Target path does not exist: {self.target_file}"

        # Collect all .sv files
        sv_files = []
        if os.path.isdir(self.target_file):
            for root, dirs, files in os.walk(self.target_file):
                for f in files:
                    if f.endswith('.sv') or f.endswith('.svh'):
                        sv_files.append(os.path.join(root, f))
        elif os.path.isfile(self.target_file):
            sv_files = [self.target_file]

        if not sv_files:
            return False, f"No .sv/.svh files found in {self.target_file}"

        errors = []
        for sv_file in sv_files:
            file_errors = self._check_basic_syntax(sv_file)
            if file_errors:
                errors.extend(file_errors)

        if errors:
            return False, {
                "error": f"Syntax check found {len(errors)} issue(s)",
                "details": errors[:20]
            }

        return True, f"UVM syntax check passed for {len(sv_files)} file(s)."

    def _check_basic_syntax(self, filepath: str) -> list:
        """Perform basic structural checks on a SystemVerilog file."""
        errors = []
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
        except Exception as e:
            return [f"{filepath}: Cannot read file: {e}"]

        basename = os.path.basename(filepath)

        # Check module/endmodule pairing
        module_count = len(re.findall(r'\bmodule\b', content))
        endmodule_count = len(re.findall(r'\bendmodule\b', content))
        if module_count != endmodule_count:
            errors.append(f"{basename}: module ({module_count}) / endmodule ({endmodule_count}) mismatch")

        # Check class/endclass pairing
        class_count = len(re.findall(r'\bclass\b', content))
        endclass_count = len(re.findall(r'\bendclass\b', content))
        if class_count != endclass_count:
            errors.append(f"{basename}: class ({class_count}) / endclass ({endclass_count}) mismatch")

        # Check function/endfunction pairing
        func_count = len(re.findall(r'\bfunction\b', content))
        endfunc_count = len(re.findall(r'\bendfunction\b', content))
        if func_count != endfunc_count:
            errors.append(f"{basename}: function ({func_count}) / endfunction ({endfunc_count}) mismatch")

        # Check task/endtask pairing
        task_count = len(re.findall(r'\btask\b', content))
        endtask_count = len(re.findall(r'\bendtask\b', content))
        if task_count != endtask_count:
            errors.append(f"{basename}: task ({task_count}) / endtask ({endtask_count}) mismatch")

        return errors


class UvmFcovStructureChecker(Checker):
    """检查 fcov 文件中的 Covergroup 结构是否与 FG/FC/CK 文档标签对应。"""

    def __init__(self, fcov_file: str, spec_file: str, **kwargs):
        super().__init__(**kwargs)
        self.fcov_file = fcov_file
        self.spec_file = spec_file

    def do_check(self, timeout=0, **kwargs) -> tuple[bool, object]:
        """检查 fcov 文件中 covergroup 与 FG/FC 标签的对应关系。"""
        if not os.path.exists(self.spec_file):
            return False, f"Spec file missing: {self.spec_file}"
        if not os.path.exists(self.fcov_file):
            return False, f"Fcov file missing: {self.fcov_file}"

        with open(self.spec_file, 'r', encoding='utf-8') as f:
            spec_content = f.read()
            
        with open(self.fcov_file, 'r', encoding='utf-8') as f:
            fcov_content = f.read()

        # Extract FG tags from spec
        fg_tags = re.findall(r'<FG-([\w-]+)>', spec_content)
        # Extract covergroup names from fcov
        cg_names = re.findall(r'covergroup\s+(\w+)', fcov_content)
        # Extract coverpoint names
        cp_names = re.findall(r'coverpoint\s+(\w+)', fcov_content)

        if not fg_tags:
            return False, "No <FG-*> tags found in spec file."

        if not cg_names:
            return False, "No covergroup definitions found in fcov file."

        # Check FG → covergroup mapping
        missing_fg = []
        cg_text = " ".join(cg_names).lower()
        for tag in fg_tags:
            tag_kw = tag.lower().replace('-', '_')
            # Skip API and COVERAGE groups (they are meta-groups)
            if tag_kw in ("api", "coverage"):
                continue
            if tag_kw not in cg_text:
                missing_fg.append(f"<FG-{tag}>")

        if missing_fg:
            return False, {
                "error": f"{len(missing_fg)} FG tag(s) have no corresponding covergroup",
                "missing": missing_fg,
                "existing_covergroups": cg_names,
                "hint": "Each <FG-*> (except FG-API) should map to a covergroup."
            }
                
        return True, f"Fcov structure check passed. {len(cg_names)} covergroup(s), {len(cp_names)} coverpoint(s)."


class UvmSimLogChecker(Checker):
    """分析 UVM 仿真日志，判定测试通过/失败。"""

    def __init__(self, log_file: str, max_errors: int = 0, **kwargs):
        super().__init__(**kwargs)
        self.log_file = log_file
        self.max_errors = max_errors

    def do_check(self, timeout=0, **kwargs) -> tuple[bool, object]:
        """检查 UVM 仿真日志中是否有 FATAL/ERROR 且测试通过。"""
        if not os.path.exists(self.log_file):
            return False, f"Sim log not found: {self.log_file}"
            
        with open(self.log_file, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            
        if "UVM_FATAL" in content:
            # Extract fatal messages
            fatal_lines = [line.strip() for line in content.splitlines()
                          if "UVM_FATAL" in line][:5]
            return False, {
                "error": "Found UVM_FATAL in simulation log",
                "fatal_messages": fatal_lines,
                "hint": "UVM_FATAL must be fixed before proceeding."
            }
            
        error_count = content.count("UVM_ERROR")
        if error_count > self.max_errors:
            error_lines = [line.strip() for line in content.splitlines()
                          if "UVM_ERROR" in line][:10]
            return False, {
                "error": f"UVM_ERROR count ({error_count}) exceeds max ({self.max_errors})",
                "error_messages": error_lines
            }
            
        if "UVM_TEST_PASSED" not in content and "Report Summary: 0 UVM_ERROR" not in content:
            return False, {
                "error": "Test pass indicator not found in log",
                "hint": "Expected 'UVM_TEST_PASSED' or 'Report Summary: 0 UVM_ERROR' in log."
            }
            
        return True, f"Simulation log check passed. {error_count} UVM_ERROR(s)."


class UvmTestListChecker(Checker):
    """检查每个 CK 检测点至少有一个对应 Test 用例。"""

    def __init__(self, spec_file: str, test_dir: str, **kwargs):
        super().__init__(**kwargs)
        self.spec_file = spec_file
        self.test_dir = test_dir

    def do_check(self, timeout=0, **kwargs) -> tuple[bool, object]:
        """检查所有 CK 检测点是否有对应的测试用例覆盖。"""
        # Step 1: Extract all <CK-*> tags from spec file
        if not os.path.exists(self.spec_file):
            return False, f"Spec file not found: {self.spec_file}"

        with open(self.spec_file, 'r', encoding='utf-8') as f:
            spec_content = f.read()

        ck_tags = re.findall(r'<CK-([\w-]+)>', spec_content)
        if not ck_tags:
            return False, "No <CK-*> tags found in spec file."

        # Normalize CK tags for comparison
        ck_set = set()
        for tag in ck_tags:
            normalized = tag.upper().replace('-', '_')
            ck_set.add(normalized)

        # Step 2: Scan test directory for test files
        if not os.path.exists(self.test_dir):
            return False, f"Test directory not found: {self.test_dir}"

        test_files = []
        if os.path.isdir(self.test_dir):
            for root, dirs, files in os.walk(self.test_dir):
                for f in files:
                    if f.startswith('test_') and (f.endswith('.sv') or f.endswith('.svh')):
                        test_files.append(os.path.join(root, f))

        if not test_files:
            return False, {
                "error": "No test files (test_*.sv) found in test directory",
                "test_dir": self.test_dir,
                "ck_count": len(ck_set),
                "hint": "Create test files with naming pattern test_*.sv"
            }

        # Step 3: Extract test class names and CK annotations from test files
        test_classes = []
        ck_covered = set()

        for test_file in test_files:
            try:
                with open(test_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
            except Exception:
                continue

            # Extract class names (test classes)
            classes = re.findall(r'class\s+(\w+)\s+extends', content)
            test_classes.extend(classes)

            # Method 1: Check for explicit CK annotations
            # Format: // CK: CK-xxx or // CK: CK_xxx
            ck_annotations = re.findall(r'//\s*CK\s*:\s*CK[_-]([\w-]+)', content, re.IGNORECASE)
            for ann in ck_annotations:
                normalized = ann.upper().replace('-', '_')
                ck_covered.add(normalized)

            # Method 2: Infer from test class names
            # Pattern: test_{DUT}_{group}_{point} -> try to match CK tags
            for cls_name in classes:
                cls_upper = cls_name.upper().replace('-', '_')
                for ck in ck_set:
                    # Check if CK keyword appears in class name
                    ck_keywords = ck.split('_')
                    if len(ck_keywords) >= 2:
                        # Match if at least the last 2 keywords are in the class name
                        matched = sum(1 for kw in ck_keywords if kw in cls_upper)
                        if matched >= max(2, len(ck_keywords) // 2):
                            ck_covered.add(ck)

            # Method 3: Check file content for CK tag references
            content_upper = content.upper().replace('-', '_')
            for ck in ck_set:
                if ck in content_upper:
                    ck_covered.add(ck)

        # Step 4: Determine uncovered CK tags
        uncovered = ck_set - ck_covered

        if uncovered:
            uncovered_list = sorted([f"CK-{ck.replace('_', '-')}" for ck in uncovered])
            return False, {
                "error": f"{len(uncovered)} CK tag(s) have no corresponding test",
                "uncovered_ck": uncovered_list,
                "total_ck": len(ck_set),
                "covered_ck": len(ck_covered),
                "test_files": len(test_files),
                "test_classes": len(test_classes),
                "hint": "Add test cases for uncovered CK tags, or add '// CK: CK-xxx' annotations."
            }

        return True, {
            "success": f"All {len(ck_set)} CK tags are covered by {len(test_classes)} test class(es).",
            "test_files": len(test_files),
        }


class UvmCoverageThresholdChecker(Checker):
    """检查覆盖率是否达到目标阈值。"""

    def __init__(self, coverage_report: str, threshold: float = 90.0, **kwargs):
        super().__init__(**kwargs)
        self.coverage_report = coverage_report
        self.threshold = threshold

    def do_check(self, timeout=0, **kwargs) -> tuple[bool, object]:
        """检查代码覆盖率是否达到目标阈值（默认 90%）。"""
        if not os.path.exists(self.coverage_report):
            return False, {
                "error": f"Coverage report not found: {self.coverage_report}",
                "hint": "Run RunUVMRegression and ExtractCoverageMetrics first."
            }

        # Collect all text content from report path
        content = ""
        if os.path.isdir(self.coverage_report):
            # Directory mode (e.g., urgReport/)
            for root, dirs, files in os.walk(self.coverage_report):
                for fname in files:
                    if fname.endswith('.txt') or fname.endswith('.rpt') or fname.endswith('.html'):
                        fpath = os.path.join(root, fname)
                        try:
                            with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
                                content += f.read() + "\n"
                        except Exception:
                            continue
        elif os.path.isfile(self.coverage_report):
            with open(self.coverage_report, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

        if not content:
            return False, {
                "error": f"No readable content found in {self.coverage_report}",
                "hint": "Ensure the coverage report contains text data."
            }

        # Parse coverage metrics from content
        metrics = {}
        patterns = {
            "line": r'(?:line|statement)\s*(?:coverage)?\s*[:=]\s*([\d.]+)\s*%',
            "cond": r'(?:cond|condition)\s*(?:coverage)?\s*[:=]\s*([\d.]+)\s*%',
            "toggle": r'toggle\s*(?:coverage)?\s*[:=]\s*([\d.]+)\s*%',
            "fsm": r'fsm\s*(?:coverage)?\s*[:=]\s*([\d.]+)\s*%',
            "branch": r'branch\s*(?:coverage)?\s*[:=]\s*([\d.]+)\s*%',
            "fcov": r'(?:functional|fcov|group)\s*(?:coverage)?\s*[:=]\s*([\d.]+)\s*%',
        }

        for name, pattern in patterns.items():
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                try:
                    metrics[name] = float(match.group(1))
                except ValueError:
                    pass

        if not metrics:
            # Try alternative formats: "Total Coverage: XX.X%"
            total_match = re.search(r'total\s*(?:coverage)?\s*[:=]\s*([\d.]+)\s*%', content, re.IGNORECASE)
            if total_match:
                metrics["total"] = float(total_match.group(1))

        if not metrics:
            return False, {
                "error": "Could not parse any coverage metrics from report",
                "report_path": self.coverage_report,
                "hint": "Ensure the report contains 'Line: XX%', 'Cond: XX%' etc."
            }

        # Check against threshold
        below_threshold = {}
        above_threshold = {}
        for name, value in metrics.items():
            if value < self.threshold:
                below_threshold[name] = value
            else:
                above_threshold[name] = value

        result = {
            "threshold": self.threshold,
            "metrics": metrics,
            "met_count": len(above_threshold),
            "total_count": len(metrics),
        }

        if below_threshold:
            result["below_threshold"] = below_threshold
            result["error"] = (
                f"{len(below_threshold)} coverage dimension(s) below {self.threshold}% threshold: "
                + ", ".join(f"{k}={v:.1f}%" for k, v in below_threshold.items())
            )
            result["hint"] = (
                "Add targeted directed Sequences or relax constraints to improve coverage. "
                "Then re-run regression."
            )
            return False, result

        return True, {
            "success": f"All {len(metrics)} coverage dimensions meet {self.threshold}% threshold.",
            "metrics": metrics,
        }
