#!/usr/bin/env python3
r"""
Portability and Self-Containment Validator for Invariant Auditor.
Verifies that:
1. No hardcoded local machine paths (/Users/, /home/, C:\) exist in the repository.
2. Every skill has a valid SKILL.md with proper YAML frontmatter (name, description).
3. Every script referenced exists inside that skill's scripts/ directory.
4. All bundled Python scripts execute cleanly with --help.
"""

import os
import sys
import re
import subprocess
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent

SUB_SKILL_DIRS = [
    "recon-triage",
    "transaction-tracer",
    "boundary-sensitivity",
    "poc-engine"
]

def check_no_absolute_paths():
    print("[1/5] Checking for hardcoded absolute machine paths...")
    forbidden_patterns = [
        re.compile(r"/Users/[a-zA-Z0-9_-]+"),
        re.compile(r"/home/[a-zA-Z0-9_-]+"),
        re.compile(r"[A-Z]:\\[a-zA-Z0-9_-]+")
    ]
    violations = []

    for root, dirs, files in os.walk(ROOT_DIR):
        # Skip git, cache, and output directories
        if any(skip in root for skip in [".git", "__pycache__", ".pytest_cache", "output"]):
            continue
        for file in files:
            if file.endswith((".py", ".md", ".json", ".sh", ".toml", ".yml", ".yaml")):
                file_path = Path(root) / file
                try:
                    content = file_path.read_text(encoding="utf-8")
                    for line_num, line in enumerate(content.splitlines(), 1):
                        for pattern in forbidden_patterns:
                            if pattern.search(line):
                                violations.append((file_path.relative_to(ROOT_DIR), line_num, line.strip()))
                except Exception as e:
                    violations.append((file_path.relative_to(ROOT_DIR), 0, f"Error reading file: {e}"))

    if violations:
        print("  [FAIL] Detected hardcoded machine paths:")
        for rel_path, line_num, text in violations:
            print(f"    - {rel_path}:{line_num} -> {text}")
        return False
    print("  [PASS] Zero hardcoded machine paths found.")
    return True

def check_skill_frontmatters():
    print("[2/5] Validating SKILL.md YAML frontmatters...")
    all_valid = True
    targets = [("invariant-auditor", ROOT_DIR / "SKILL.md")]
    for skill_name in SUB_SKILL_DIRS:
        targets.append((skill_name, ROOT_DIR / skill_name / "SKILL.md"))

    for label, skill_file in targets:
        if not skill_file.exists():
            print(f"  [FAIL] Missing SKILL.md for {label}")
            all_valid = False
            continue

        content = skill_file.read_text(encoding="utf-8")
        if not content.startswith("---"):
            print(f"  [FAIL] {label}/SKILL.md does not start with YAML frontmatter delimiter (---)")
            all_valid = False
            continue

        # Simple frontmatter extractor
        parts = content.split("---", 2)
        if len(parts) < 3:
            print(f"  [FAIL] {label}/SKILL.md has unclosed frontmatter")
            all_valid = False
            continue

        frontmatter = parts[1]
        has_name = bool(re.search(r"^name:\s*[\S]+", frontmatter, re.MULTILINE))
        has_desc = bool(re.search(r"^description:", frontmatter, re.MULTILINE))

        if not has_name or not has_desc:
            print(f"  [FAIL] {label}/SKILL.md frontmatter missing required 'name' or 'description'")
            all_valid = False
        else:
            print(f"  [PASS] Valid frontmatter: {label}")

    return all_valid

def check_guidance_files():
    print("[3/5] Verifying guidance directive files (CLAUDE.md, AGENTS.md, GEMINI.md, CODEX.md)...")
    claude_md = ROOT_DIR / "CLAUDE.md"
    if not claude_md.exists():
        print("  [FAIL] Missing CLAUDE.md in repository root")
        return False
    content = claude_md.read_text(encoding="utf-8")
    if "Invariant Auditor" not in content or "Accuracy Gates" not in content:
        print("  [FAIL] CLAUDE.md missing key audit directives")
        return False

    for alias in ["AGENTS.md", "GEMINI.md", "CODEX.md"]:
        alias_path = ROOT_DIR / alias
        if not alias_path.exists():
            print(f"  [FAIL] Missing {alias} compatibility file in repository root")
            return False
        alias_content = alias_path.read_text(encoding="utf-8")
        if "Invariant Auditor" not in alias_content or "Accuracy Gates" not in alias_content:
            print(f"  [FAIL] {alias} does not resolve to CLAUDE.md directives")
            return False
        print(f"  [PASS] {alias} verified (links/resolves to CLAUDE.md).")

    print("  [PASS] All agent guidance files verified.")
    return True

def check_bundled_scripts():
    print("[4/5] Verifying bundled executable tools (Master & Satellites)...")
    expected_scripts = {
        "": [
            "audit_inspector.py",
            "audit_tracer.py",
            "liquidity_run_sim.py",
            "symbolic_sensitivity.py",
            "generate_poc_scaffold.py",
        ],
        "recon-triage": ["audit_inspector.py"],
        "transaction-tracer": ["audit_tracer.py"],
        "boundary-sensitivity": ["liquidity_run_sim.py", "symbolic_sensitivity.py"],
        "poc-engine": ["generate_poc_scaffold.py"],
    }
    all_found = True
    for skill, scripts in expected_scripts.items():
        scripts_dir = (ROOT_DIR / skill / "scripts") if skill else (ROOT_DIR / "scripts")
        label = skill if skill else "invariant-auditor (master)"
        if not scripts_dir.is_dir():
            print(f"  [FAIL] Missing scripts directory for {label}")
            all_found = False
            continue
        for script in scripts:
            script_path = scripts_dir / script
            if not script_path.exists():
                print(f"  [FAIL] Missing script: {label}/scripts/{script}")
                all_found = False
            elif not os.access(script_path, os.X_OK):
                print(f"  [WARN] Script not marked executable: {label}/scripts/{script} (fixing...)")
                script_path.chmod(0o755)
            else:
                print(f"  [PASS] Bundled tool verified: {label}/scripts/{script}")

    return all_found

def check_script_execution():
    print("[5/5] Testing CLI tool execution (--help)...")
    tools = [
        ROOT_DIR / "scripts" / "audit_inspector.py",
        ROOT_DIR / "scripts" / "audit_tracer.py",
        ROOT_DIR / "scripts" / "liquidity_run_sim.py",
        ROOT_DIR / "scripts" / "symbolic_sensitivity.py",
        ROOT_DIR / "scripts" / "generate_poc_scaffold.py",
        ROOT_DIR / "recon-triage" / "scripts" / "audit_inspector.py",
        ROOT_DIR / "transaction-tracer" / "scripts" / "audit_tracer.py",
        ROOT_DIR / "boundary-sensitivity" / "scripts" / "liquidity_run_sim.py",
        ROOT_DIR / "boundary-sensitivity" / "scripts" / "symbolic_sensitivity.py",
        ROOT_DIR / "poc-engine" / "scripts" / "generate_poc_scaffold.py",
    ]
    all_passed = True
    for tool in tools:
        cmd = [sys.executable, str(tool), "--help"]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if res.returncode != 0:
            print(f"  [FAIL] Execution failed for {tool.relative_to(ROOT_DIR)}: {res.stderr.strip()}")
            all_passed = False
        else:
            print(f"  [PASS] Clean CLI run: {tool.relative_to(ROOT_DIR)}")

    return all_passed

def main():
    print("=" * 60)
    print("  Invariant Auditor - Portability & Health Check")
    print("=" * 60)
    results = [
        check_no_absolute_paths(),
        check_skill_frontmatters(),
        check_guidance_files(),
        check_bundled_scripts(),
        check_script_execution(),
    ]

    print("=" * 60)
    if all(results):
        print("  ALL CHECKS PASSED: Suite is 100% portable & distributable.")
        print("=" * 60)
        sys.exit(0)
    else:
        print("  HEALTH CHECK FAILED: Review the errors above.")
        print("=" * 60)
        sys.exit(1)

if __name__ == "__main__":
    main()
