#!/usr/bin/env python3
"""Parse Apex test result JSON into a structured summary with coverage analysis.

Reads test results from sf CLI output and produces a human-readable or JSON
summary with pass/fail counts, coverage percentages, and failure details.
"""

import argparse
import json
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import List, Optional


class CLIError(Exception):
    """Expected CLI failures."""
    pass


@dataclass
class TestFailure:
    class_name: str
    method_name: str
    message: str
    stack_trace: str = ""


@dataclass
class ClassCoverage:
    class_name: str
    lines_covered: int
    lines_total: int
    coverage_pct: float


@dataclass
class TestSummary:
    total: int = 0
    passing: int = 0
    failing: int = 0
    skipped: int = 0
    overall_coverage: float = 0.0
    classes_below_75: List[str] = field(default_factory=list)
    failures: List[TestFailure] = field(default_factory=list)
    coverage_details: List[ClassCoverage] = field(default_factory=list)
    duration_ms: int = 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Parse Apex test result JSON into a structured summary.",
        epilog="Examples:\n"
               "  %(prog)s --input test-results.json\n"
               "  %(prog)s --input test-results.json --format json\n"
               "  cat test-results.json | %(prog)s --format text\n",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--input", help="Path to test results JSON file (default: stdin)")
    parser.add_argument(
        "--format",
        choices=["json", "text"],
        default="text",
        help="Output format (default: text)",
    )
    parser.add_argument(
        "--coverage-threshold",
        type=float,
        default=75.0,
        help="Minimum coverage percentage to flag (default: 75.0)",
    )
    return parser.parse_args()


def load_input(input_path: Optional[str]) -> dict:
    """Load test results from file or stdin."""
    if input_path:
        path = Path(input_path)
        if not path.exists():
            raise CLIError(f"Input file not found: {input_path}")
        return json.loads(path.read_text())
    else:
        data = sys.stdin.read().strip()
        if not data:
            raise CLIError("No input provided. Use --input or pipe JSON to stdin.")
        return json.loads(data)


def parse_results(raw: dict, threshold: float) -> TestSummary:
    """Parse raw sf CLI test results into a TestSummary."""
    summary = TestSummary()

    result = raw.get("result", raw)
    run_test_result = result.get("runTestResult", result)

    # Test counts
    summary.total = int(run_test_result.get("numTestsRun", 0))
    num_failures = int(run_test_result.get("numFailures", 0))
    summary.failing = num_failures
    summary.passing = summary.total - num_failures
    summary.duration_ms = int(run_test_result.get("totalTime", 0))

    # Failures
    failures = run_test_result.get("failures", [])
    if isinstance(failures, dict):
        failures = [failures]
    for f in failures:
        summary.failures.append(TestFailure(
            class_name=f.get("name", "Unknown"),
            method_name=f.get("methodName", "Unknown"),
            message=f.get("message", ""),
            stack_trace=f.get("stackTrace", ""),
        ))

    # Coverage
    code_coverage = run_test_result.get("codeCoverage", [])
    if isinstance(code_coverage, dict):
        code_coverage = [code_coverage]

    total_lines = 0
    covered_lines = 0

    for cc in code_coverage:
        num_locations = int(cc.get("numLocations", 0))
        not_covered = int(cc.get("numLocationsNotCovered", 0))
        cls_covered = num_locations - not_covered
        pct = (cls_covered / num_locations * 100) if num_locations > 0 else 100.0

        total_lines += num_locations
        covered_lines += cls_covered

        detail = ClassCoverage(
            class_name=cc.get("name", "Unknown"),
            lines_covered=cls_covered,
            lines_total=num_locations,
            coverage_pct=round(pct, 1),
        )
        summary.coverage_details.append(detail)

        if pct < threshold and num_locations > 0:
            summary.classes_below_75.append(cc.get("name", "Unknown"))

    summary.overall_coverage = round(
        (covered_lines / total_lines * 100) if total_lines > 0 else 0, 1
    )

    return summary


def format_text(summary: TestSummary) -> str:
    """Format a TestSummary as human-readable text."""
    lines = []
    status = "PASS" if summary.failing == 0 else "FAIL"
    lines.append(f"Test Results: {status}")
    lines.append(f"  Total:    {summary.total}")
    lines.append(f"  Passing:  {summary.passing}")
    lines.append(f"  Failing:  {summary.failing}")
    lines.append(f"  Duration: {summary.duration_ms}ms")
    lines.append("")
    lines.append(f"Coverage: {summary.overall_coverage}%")

    if summary.classes_below_75:
        lines.append(f"  Below threshold: {', '.join(summary.classes_below_75)}")

    if summary.failures:
        lines.append("")
        lines.append("Failures:")
        for f in summary.failures:
            lines.append(f"  {f.class_name}.{f.method_name}")
            lines.append(f"    {f.message}")
            if f.stack_trace:
                first_line = f.stack_trace.split("\n")[0]
                lines.append(f"    at {first_line}")

    if summary.coverage_details:
        lines.append("")
        lines.append("Coverage by Class:")
        sorted_details = sorted(summary.coverage_details, key=lambda c: c.coverage_pct)
        for detail in sorted_details[:20]:
            bar = "#" * int(detail.coverage_pct / 5) + "." * (20 - int(detail.coverage_pct / 5))
            lines.append(f"  {detail.class_name:40s} [{bar}] {detail.coverage_pct:5.1f}%")

    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    raw = load_input(args.input)
    summary = parse_results(raw, args.coverage_threshold)

    if args.format == "json":
        print(json.dumps(asdict(summary), indent=2))
    else:
        print(format_text(summary))

    return 0 if summary.failing == 0 else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except CLIError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
