from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path


PASS_MARKER = "V2_REQ_12_RAW_REMEDIATION_PROGRESS_CHECKPOINT_PASS"
FAIL_MARKER = "V2_REQ_12_RAW_REMEDIATION_PROGRESS_CHECKPOINT_FAIL"
RECOMMENDED_NEXT_STEP = "V2-REQ-13_CREATE_COVERAGE_CLOSURE_PLAN_FROM_RAW_REM_03_TO_05"


@dataclass(frozen=True)
class Failure:
    code: str
    expected: str
    actual: str
    source_file: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify the V2-REQ-12 raw-remediation checkpoint.")
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    return parser.parse_args()


def add(failures: list[Failure], code: str, expected: str, actual: str, source: Path) -> None:
    failures.append(Failure(code, expected, actual, str(source)))


def require_once(failures: list[Failure], text: str, value: str, code: str, source: Path) -> None:
    count = text.count(value)
    if count != 1:
        add(failures, code, "exactly one occurrence", str(count), source)


def require_text(failures: list[Failure], text: str, value: str, code: str, source: Path) -> None:
    if value not in text:
        add(failures, code, value, "missing", source)


def verify(repo_root: Path) -> tuple[list[Failure], dict[str, int | str]]:
    paths = {
        "checkpoint": repo_root / "specs/runtime/raw_remediation/V2_REQ_12_RAW_REMEDIATION_PROGRESS_CHECKPOINT.md",
        "plan": repo_root / "specs/runtime/V1_SOURCE_RAW_LOGIC_REMEDIATION_PLAN.md",
        "coverage": repo_root / "specs/runtime/V1_SOURCE_RAW_LOGIC_COVERAGE_VERIFICATION.md",
        "raw01": repo_root / "specs/runtime/raw_remediation/RAW_REM_01_SOURCE_UNCERTAINTY_VERIFICATION.md",
        "raw02": repo_root / "specs/runtime/raw_remediation/RAW_REM_02_FALSE_POSITIVE_TRIVIAL_LOGIC_VERIFICATION.md",
        "raw03": repo_root / "specs/runtime/raw_remediation/RAW_REM_03_HIGH_RISK_TAX_FIXATION_INDEXATION_VERIFICATION.md",
        "raw04": repo_root / "specs/runtime/raw_remediation/RAW_REM_04_CLEARINGHOUSE_PARSER_BALANCE_LEDGER_VERIFICATION.md",
        "raw05": repo_root / "specs/runtime/raw_remediation/RAW_REM_05_PENSION_COEFFICIENT_ANNUITY_CAPITAL_CONVERSION_VERIFICATION.md",
    }
    failures: list[Failure] = []
    text: dict[str, str] = {}
    for key, path in paths.items():
        try:
            text[key] = path.read_text(encoding="utf-8")
        except OSError as exc:
            add(failures, "REQUIRED_FILE_READ_ERROR", "readable required file", str(exc), path)
    if failures:
        return failures, {}

    checkpoint = text["checkpoint"]
    require_once(failures, checkpoint, PASS_MARKER, "INVALID_FINAL_PASS_MARKER", paths["checkpoint"])
    if FAIL_MARKER in checkpoint:
        add(failures, "UNEXPECTED_FAIL_MARKER", "zero FAIL markers", str(checkpoint.count(FAIL_MARKER)), paths["checkpoint"])
    if "READY_FOR_REVIEW" in checkpoint:
        add(failures, "READY_FOR_REVIEW_FORBIDDEN", "zero occurrences", str(checkpoint.count("READY_FOR_REVIEW")), paths["checkpoint"])

    required_checkpoint_values = {
        "RAW_COVERAGE_STATUS_INVALID": "Raw V1 source logic coverage: `FAIL`",
        "PLANNING_COMPLETENESS_INVALID": "Full planning completeness: `NOT_PROVEN`",
        "EXECUTION_AUTHORIZATION_INVALID": "Execution authorized: `NO`",
        "02M_STATUS_INVALID": "02M: `FROZEN`",
        "COMPLETED_PACKAGES_INVALID": "Completed RAW-REM packages: `5 of 10`",
        "COMPLETED_CHECKED_INVALID": "Completed checked items: `2,421`",
        "COMPLETED_RESOLVED_INVALID": "Completed resolved items: `0`",
        "COMPLETED_BLOCKING_INVALID": "Completed remaining blocking items: `2,421`",
        "NOT_PROCESSED_INVALID": "Not-yet-processed RAW-REM items: `4,270`",
        "TOTAL_BLOCKING_SCOPE_INVALID": "Total blocking scope remains: `6,691`",
        "RAW_REM_06_TO_10_NECESSITY_MISSING": "Do not skip RAW-REM-06..10 permanently; they remain necessary unless a later management decision changes scope.",
    }
    for code, value in required_checkpoint_values.items():
        require_text(failures, checkpoint, value, code, paths["checkpoint"])
    require_once(failures, checkpoint, RECOMMENDED_NEXT_STEP, "RECOMMENDED_NEXT_STEP_INVALID", paths["checkpoint"])

    for commit in ("0c87025", "5bfdbef", "7401e8f", "0cf1bc5", "f57656c"):
        require_once(failures, checkpoint, commit, f"COMMIT_{commit}_INVALID", paths["checkpoint"])

    upstream_markers = {
        "raw01": "RAW_REM_01_SOURCE_UNCERTAINTY_VERIFICATION_PASS",
        "raw02": "RAW_REM_02_FALSE_POSITIVE_TRIVIAL_LOGIC_VERIFICATION_PASS",
        "raw03": "RAW_REM_03_HIGH_RISK_TAX_FIXATION_INDEXATION_VERIFICATION_PASS",
        "raw04": "RAW_REM_04_CLEARINGHOUSE_PARSER_BALANCE_LEDGER_VERIFICATION_PASS",
        "raw05": "RAW_REM_05_PENSION_COEFFICIENT_ANNUITY_CAPITAL_CONVERSION_VERIFICATION_PASS",
    }
    for key, marker in upstream_markers.items():
        require_once(failures, text[key], marker, f"UPSTREAM_{key.upper()}_MARKER_INVALID", paths[key])

    require_text(failures, text["coverage"], "Result: `FAIL`", "UPSTREAM_RAW_COVERAGE_NOT_FAIL", paths["coverage"])
    if "V1_SOURCE_RAW_LOGIC_COVERAGE_VERIFICATION_FAIL" not in text["coverage"]:
        add(
            failures,
            "UPSTREAM_RAW_COVERAGE_MARKER_INVALID",
            "FAIL marker present",
            "missing",
            paths["coverage"],
        )
    for value in ("6,736", "6,457", "234", "6,691"):
        require_text(failures, text["plan"], value, f"PLAN_BASELINE_{value.replace(',', '')}_MISSING", paths["plan"])

    forbidden_patterns = {
        "IMPLEMENTATION_RECOMMENDED": r"(?i)(?:recommend(?:ed|ation)?|next step)\s*:\s*(?:begin|start|proceed with|authorize)[^\n]{0,40}implementation",
        "02M_RECOMMENDED": r"(?i)(?:recommend(?:ed|ation)?|next step)\s*:\s*(?:proceed to|begin|start|unfreeze|authorize)[^\n]{0,20}02M",
        "PLANNING_COMPLETENESS_CLAIMED": r"(?i)full planning completeness\s*(?:is|:)\s*`?(?:PROVEN|PASS|COMPLETE)`?",
        "RAW_REM_06_TO_10_DECLARED_UNNECESSARY": r"(?i)RAW-REM-06\.\.10 (?:are|is) unnecessary",
    }
    for code, pattern in forbidden_patterns.items():
        match = re.search(pattern, checkpoint)
        if match:
            add(failures, code, "forbidden conclusion absent", match.group(0), paths["checkpoint"])

    counts: dict[str, int | str] = {
        "completed_packages": 5,
        "completed_checked_items": 2421,
        "completed_resolved_items": 0,
        "completed_remaining_blocking": 2421,
        "not_yet_processed_items": 4270,
        "total_blocking_scope": 6691,
        "recommended_next_step": RECOMMENDED_NEXT_STEP,
    }
    return failures, counts


def main() -> int:
    failures, counts = verify(parse_args().repo_root.resolve())
    if failures:
        print("V2_REQ_12_RAW_REMEDIATION_PROGRESS_CHECKPOINT_VERIFICATION_FAIL")
        for failure in failures:
            print(
                f"failure_code={failure.code}; expected={failure.expected}; "
                f"actual={failure.actual}; source_file={failure.source_file}"
            )
        return 1
    print("V2_REQ_12_RAW_REMEDIATION_PROGRESS_CHECKPOINT_VERIFICATION_PASS")
    for key, value in counts.items():
        print(f"{key}={value}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
