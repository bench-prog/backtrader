#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
Test runner for all backtrader sample scripts

This script discovers and runs all Python sample files in the samples directory,
capturing their output and reporting success/failure status.

Usage:
    bash
    # 只测试特定模式的示例
    python test_samples.py --pattern "data-*"

    # 设置超时时间（秒）
    python test_samples.py --timeout 60

    # 显示详细输出
    python test_samples.py --verbose

    # 指定 Python 解释器
    python test_samples.py --python /path/to/python

    # 指定 samples 目录
    python test_samples.py --samples-dir /path/to/samples
"""

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path


class SampleTester:
    def __init__(
        self, samples_dir="samples", python_exe=None, timeout=30, verbose=False
    ):
        self.samples_dir = Path(samples_dir)
        self.python_exe = python_exe or sys.executable
        self.timeout = timeout
        self.verbose = verbose
        self.results = {"passed": [], "failed": [], "skipped": [], "timeout": []}

    def find_samples(self):
        """Find all Python sample files"""
        samples = []
        for py_file in self.samples_dir.rglob("*.py"):
            # Skip __init__.py and other utility files
            if py_file.name.startswith("__"):
                continue
            samples.append(py_file)
        return sorted(samples)

    def run_sample(self, sample_path):
        """Run a single sample script"""
        print(f"\n{'=' * 70}")
        print(f"Testing: {sample_path.relative_to(self.samples_dir.parent)}")
        print(f"{'=' * 70}")

        try:
            # Change to the sample's directory
            cwd = sample_path.parent

            # Set environment variable to disable matplotlib display
            env = os.environ.copy()
            env["MPLBACKEND"] = "Agg"  # Use non-interactive backend

            # Run the sample with --help first to check if it's runnable
            result = subprocess.run(
                [self.python_exe, sample_path.name, "--help"],
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=5,
                env=env,
            )

            # Build command with various no-plot options
            cmd = [self.python_exe, sample_path.name]

            # Try different variations of no-plot flags
            help_text = result.stdout.lower() + result.stderr.lower()
            if "--noplot" in help_text:
                cmd.append("--noplot")
            elif "--no-plot" in help_text:
                cmd.append("--no-plot")
            # Don't add --plot False, just rely on MPLBACKEND=Agg

            start_time = time.time()
            result = subprocess.run(
                cmd,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                env=env,  # Use environment with non-interactive backend
            )
            elapsed = time.time() - start_time

            if result.returncode == 0:
                print(f"✅ PASSED ({elapsed:.2f}s)")
                if self.verbose and result.stdout:
                    print(f"\nOutput:\n{result.stdout[:500]}")
                return "passed"
            else:
                print(f"❌ FAILED (exit code: {result.returncode})")
                if result.stderr:
                    print(f"\nError:\n{result.stderr[:500]}")
                return "failed"

        except subprocess.TimeoutExpired:
            print(f"⏱️  TIMEOUT (>{self.timeout}s)")
            return "timeout"
        except Exception as e:
            print(f"⚠️  SKIPPED: {str(e)}")
            return "skipped"

    def run_all(self):
        """Run all sample tests"""
        samples = self.find_samples()

        print(f"\n{'#' * 70}")
        print("# Backtrader Sample Test Runner")
        print(f"# Found {len(samples)} sample files")
        print(f"# Python: {self.python_exe}")
        print(f"# Timeout: {self.timeout}s")
        print(f"{'#' * 70}\n")

        for i, sample in enumerate(samples, 1):
            print(f"\n[{i}/{len(samples)}]", end=" ")
            status = self.run_sample(sample)
            self.results[status].append(sample)

        self.print_summary()

    def print_summary(self):
        """Print test summary"""
        total = sum(len(v) for v in self.results.values())

        print(f"\n\n{'=' * 70}")
        print("TEST SUMMARY")
        print(f"{'=' * 70}")
        print(f"Total:   {total}")
        print(
            f"✅ Passed:  {len(self.results['passed'])} ({len(self.results['passed']) / total * 100:.1f}%)"
        )
        print(
            f"❌ Failed:  {len(self.results['failed'])} ({len(self.results['failed']) / total * 100:.1f}%)"
        )
        print(
            f"⏱️  Timeout: {len(self.results['timeout'])} ({len(self.results['timeout']) / total * 100:.1f}%)"
        )
        print(
            f"⚠️  Skipped: {len(self.results['skipped'])} ({len(self.results['skipped']) / total * 100:.1f}%)"
        )
        print(f"{'=' * 70}")

        if self.results["failed"]:
            print("\n❌ Failed samples:")
            for sample in self.results["failed"]:
                print(f"  - {sample.relative_to(self.samples_dir.parent)}")

        if self.results["timeout"]:
            print("\n⏱️  Timeout samples:")
            for sample in self.results["timeout"]:
                print(f"  - {sample.relative_to(self.samples_dir.parent)}")

        # Return exit code
        return 0 if not self.results["failed"] else 1


def main():
    parser = argparse.ArgumentParser(
        description="Test runner for backtrader sample scripts"
    )

    parser.add_argument(
        "--samples-dir",
        default="samples",
        help="Path to samples directory (default: samples)",
    )

    parser.add_argument(
        "--python",
        default=sys.executable,
        help="Python executable to use (default: current Python)",
    )

    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="Timeout for each sample in seconds (default: 30)",
    )

    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Show verbose output"
    )

    parser.add_argument(
        "--pattern", help='Only test samples matching this pattern (e.g., "data-*")'
    )

    args = parser.parse_args()

    tester = SampleTester(
        samples_dir=args.samples_dir,
        python_exe=args.python,
        timeout=args.timeout,
        verbose=args.verbose,
    )

    # Filter samples if pattern is provided
    if args.pattern:
        all_samples = tester.find_samples()
        filtered = [s for s in all_samples if args.pattern in str(s)]
        print(
            f"Filtered {len(all_samples)} samples to {len(filtered)} matching '{args.pattern}'"
        )
        # Override find_samples method
        tester.find_samples = lambda: filtered

    exit_code = tester.run_all()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
