from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path


UNIVERSE_PATH = Path("specs/runtime/V2_REQUIRED_CAPABILITY_UNIVERSE.md")
LEDGER_PATH = Path("specs/runtime/V1_TO_V2_MECHANICAL_PARITY_LEDGER.md")
GAP_PATH = Path("specs/runtime/V2_FULL_GAP_REGISTER_FROM_PARITY_LEDGER.md")
MASTER_PATH = Path("specs/runtime/V2_MASTER_BUILD_SEQUENCE_FULL_SYSTEM.md")
PROOF_PATH = Path("specs/runtime/V2_UNIVERSE_COVERAGE_PROOF.md")

EXPECTED_REQ_COUNTS = {
    "REQ_MAPPED_VERIFIED": 18,
    "REQ_MAPPED_GAP": 91,
    "REQ_MAPPED_UNKNOWN": 24,
    "REQ_UNMAPPED": 0,
    "REQ_NEEDS_DOMAIN_DECISION": 4,
}
EXPECTED_LEDGER_COUNTS = {
    "V2_EXISTS_VERIFIED": 17,
    "V2_PARTIAL": 32,
    "V2_MISSING": 41,
    "V2_REPLACED_BY_NEW_DESIGN": 2,
    "V2_EXCLUDED_BY_DECISION": 0,
    "UNKNOWN_NEEDS_INSPECTION": 21,
}
EXPECTED_SEVERITY_COUNTS = {
    "CRITICAL_BLOCKER": 72,
    "HIGH": 16,
    "MEDIUM": 3,
    "LOW": 2,
    "UNKNOWN_RISK": 3,
}
EXPECTED_DECISIONS = {"REQ-072", "REQ-107", "REQ-125", "REQ-126"}


@dataclass(frozen=True)
class Failure:
    code: str
    requirement_id: str
    expected: str
    actual: str
    source: str

    def render(self) -> str:
        requirement = self.requirement_id or "-"
        return (
            f"failure_code={self.code} requirement_id={requirement} "
            f"expected={self.expected!r} actual={self.actual!r} source={self.source}"
        )


@dataclass
class VerificationResult:
    failures: list[Failure]
    requirements_checked: int
    req_unmapped: int
    ledger_rows: int
    gap_rows: int
    domain_decisions: int

    @property
    def passed(self) -> bool:
        return not self.failures


def _read(root: Path, relative: Path, failures: list[Failure]) -> str:
    path = root / relative
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        failures.append(Failure("FILE_READ", "", "readable UTF-8 file", str(exc), str(relative)))
        return ""


def _fields(line: str) -> list[str]:
    return [field.strip() for field in line.strip()[1:-1].split("|")]


def _section(text: str, start: str, end: str) -> list[str]:
    lines = text.splitlines()
    try:
        start_index = next(i for i, line in enumerate(lines) if line == start) + 1
        end_index = next(i for i, line in enumerate(lines[start_index:], start_index) if line == end)
    except StopIteration:
        return []
    return lines[start_index:end_index]


def _rows(
    lines: list[str],
    pattern: str,
    width: int | tuple[int, ...],
    source: Path,
    failures: list[Failure],
) -> list[list[str]]:
    parsed: list[list[str]] = []
    allowed_widths = (width,) if isinstance(width, int) else width
    for line in lines:
        if not re.match(pattern, line):
            continue
        fields = _fields(line)
        if len(fields) not in allowed_widths:
            failures.append(Failure("BROAD_PARSE_FAILURE", fields[0] if fields else "", str(allowed_widths), str(len(fields)), str(source)))
            continue
        parsed.append(fields)
    return parsed


def _ids(value: str) -> list[str]:
    if value in {"", "None"}:
        return []
    return [item.strip() for item in value.split(",")]


def _count_check(
    failures: list[Failure], code: str, expected: int, actual: int, source: Path
) -> None:
    if expected != actual:
        failures.append(Failure(code, "", str(expected), str(actual), str(source)))


def verify_repository(root: Path) -> VerificationResult:
    root = root.resolve()
    failures: list[Failure] = []
    universe_text = _read(root, UNIVERSE_PATH, failures)
    ledger_text = _read(root, LEDGER_PATH, failures)
    gap_text = _read(root, GAP_PATH, failures)
    master_text = _read(root, MASTER_PATH, failures)
    proof_text = _read(root, PROOF_PATH, failures)

    requirement_lines = _section(
        universe_text,
        "## 4. Required Capability Universe Table",
        "## 5. Mandatory Requirement Domains",
    )
    requirements = _rows(requirement_lines, r"^\| REQ-\d{3} \|", 14, UNIVERSE_PATH, failures)
    ledger_rows = _rows(ledger_text.splitlines(), r"^\| [A-O]-\d{3} \|", 14, LEDGER_PATH, failures)
    # GAP-001..093 include the optional package-prefix column; GAP-094..096
    # predate that normalized shape. Required validation fields stay at 0..12.
    gap_rows = _rows(gap_text.splitlines(), r"^\| GAP-\d{3} \|", (15, 16), GAP_PATH, failures)

    requirement_ids = [row[0] for row in requirements]
    expected_requirement_ids = [f"REQ-{number:03d}" for number in range(1, 138)]
    _count_check(failures, "REQ_ROW_COUNT", 137, len(requirements), UNIVERSE_PATH)
    duplicate_requirements = sorted(item for item, count in Counter(requirement_ids).items() if count > 1)
    if duplicate_requirements:
        failures.append(Failure("REQ_DUPLICATE", ",".join(duplicate_requirements), "unique IDs", "duplicates", str(UNIVERSE_PATH)))
    missing_requirements = sorted(set(expected_requirement_ids) - set(requirement_ids))
    extra_requirements = sorted(set(requirement_ids) - set(expected_requirement_ids))
    if missing_requirements or extra_requirements:
        failures.append(
            Failure(
                "REQ_ID_SEQUENCE",
                "",
                "REQ-001..REQ-137",
                f"missing={missing_requirements}; extra={extra_requirements}",
                str(UNIVERSE_PATH),
            )
        )

    requirement_statuses = Counter(row[8] for row in requirements)
    for status, expected in EXPECTED_REQ_COUNTS.items():
        _count_check(failures, f"REQ_STATUS_COUNT_{status}", expected, requirement_statuses[status], UNIVERSE_PATH)
    allowed_requirement_statuses = set(EXPECTED_REQ_COUNTS)
    unexpected_statuses = sorted(set(requirement_statuses) - allowed_requirement_statuses)
    if unexpected_statuses:
        failures.append(Failure("REQ_STATUS_UNEXPECTED", "", str(sorted(allowed_requirement_statuses)), str(unexpected_statuses), str(UNIVERSE_PATH)))
    if requirement_statuses["REQ_UNMAPPED"]:
        failures.append(Failure("REQ_UNMAPPED_PRESENT", "", "0", str(requirement_statuses["REQ_UNMAPPED"]), str(UNIVERSE_PATH)))

    ledger_ids = [row[0] for row in ledger_rows]
    _count_check(failures, "LEDGER_ROW_COUNT", 113, len(ledger_rows), LEDGER_PATH)
    if len(set(ledger_ids)) != len(ledger_ids):
        failures.append(Failure("LEDGER_DUPLICATE", "", "unique IDs", "duplicates found", str(LEDGER_PATH)))
    ledger_by_id = {row[0]: row for row in ledger_rows}
    ledger_statuses = Counter(row[10] for row in ledger_rows)
    for status, expected in EXPECTED_LEDGER_COUNTS.items():
        _count_check(failures, f"LEDGER_STATUS_COUNT_{status}", expected, ledger_statuses[status], LEDGER_PATH)
    l009 = ledger_by_id.get("L-009")
    if l009 is None:
        failures.append(Failure("LEDGER_L009_MISSING", "", "L-009", "missing", str(LEDGER_PATH)))
    else:
        if l009[2] != "RTL/Hebrew layout":
            failures.append(Failure("LEDGER_L009_CAPABILITY", "", "RTL/Hebrew layout", l009[2], str(LEDGER_PATH)))
        if l009[10] != "V2_MISSING":
            failures.append(Failure("LEDGER_L009_STATUS", "", "V2_MISSING", l009[10], str(LEDGER_PATH)))

    gap_ids = [row[0] for row in gap_rows]
    _count_check(failures, "GAP_ROW_COUNT", 96, len(gap_rows), GAP_PATH)
    if len(set(gap_ids)) != len(gap_ids):
        failures.append(Failure("GAP_DUPLICATE", "", "unique IDs", "duplicates found", str(GAP_PATH)))
    gap_by_id = {row[0]: row for row in gap_rows}
    severities = Counter(row[6] for row in gap_rows)
    for severity, expected in EXPECTED_SEVERITY_COUNTS.items():
        _count_check(failures, f"GAP_SEVERITY_COUNT_{severity}", expected, severities[severity], GAP_PATH)
    gap096 = gap_by_id.get("GAP-096")
    if gap096 is None:
        failures.append(Failure("GAP_096_MISSING", "", "GAP-096", "missing", str(GAP_PATH)))
    else:
        if gap096[1] != "L-009":
            failures.append(Failure("GAP_096_LEDGER", "", "L-009", gap096[1], str(GAP_PATH)))
        if gap096[3] != "RTL/Hebrew layout":
            failures.append(Failure("GAP_096_CAPABILITY", "", "RTL/Hebrew layout", gap096[3], str(GAP_PATH)))

    master_milestones = set(re.findall(r"^### (M\d{2}) ", master_text, flags=re.MULTILINE))
    expected_milestones = {f"M{number:02d}" for number in range(1, 17)}
    if master_milestones != expected_milestones:
        failures.append(Failure("MASTER_MILESTONES", "", str(sorted(expected_milestones)), str(sorted(master_milestones)), str(MASTER_PATH)))

    domain_decisions: set[str] = set()
    for row in requirements:
        requirement_id, milestone, ledger_value, gap_value, status = row[0], row[5], row[6], row[7], row[8]
        ledger_refs = _ids(ledger_value)
        gap_refs = _ids(gap_value)
        missing_details = row[10]
        mapped_ledgers = [ledger_by_id.get(item) for item in ledger_refs]
        mapped_gaps = [gap_by_id.get(item) for item in gap_refs]

        if status == "REQ_MAPPED_VERIFIED":
            if not ledger_refs:
                failures.append(Failure("REQ_VERIFIED_LEDGER_MISSING", requirement_id, "one or more Ledger IDs", ledger_value, str(UNIVERSE_PATH)))
            for ledger_id, ledger_row in zip(ledger_refs, mapped_ledgers):
                if ledger_row is None:
                    failures.append(Failure("REQ_LEDGER_NOT_FOUND", requirement_id, ledger_id, "missing", str(LEDGER_PATH)))
            if mapped_ledgers and not any(item and item[10] == "V2_EXISTS_VERIFIED" for item in mapped_ledgers):
                failures.append(Failure("REQ_VERIFIED_STATUS", requirement_id, "at least one V2_EXISTS_VERIFIED", str([item[10] for item in mapped_ledgers if item]), str(LEDGER_PATH)))
        elif status in {"REQ_MAPPED_GAP", "REQ_MAPPED_UNKNOWN"}:
            if not ledger_refs:
                failures.append(Failure("REQ_MAPPED_LEDGER_MISSING", requirement_id, "one or more Ledger IDs", ledger_value, str(UNIVERSE_PATH)))
            if not gap_refs:
                failures.append(Failure("REQ_MAPPED_GAP_MISSING", requirement_id, "one or more Gap IDs", gap_value, str(UNIVERSE_PATH)))
            for ledger_id, ledger_row in zip(ledger_refs, mapped_ledgers):
                if ledger_row is None:
                    failures.append(Failure("REQ_LEDGER_NOT_FOUND", requirement_id, ledger_id, "missing", str(LEDGER_PATH)))
            for gap_id, gap_row in zip(gap_refs, mapped_gaps):
                if gap_row is None:
                    failures.append(Failure("REQ_GAP_NOT_FOUND", requirement_id, gap_id, "missing", str(GAP_PATH)))
                elif gap_row[1] not in ledger_refs:
                    failures.append(Failure("REQ_GAP_WRONG_LEDGER", requirement_id, str(ledger_refs), gap_row[1], str(GAP_PATH)))
            if status == "REQ_MAPPED_GAP" and mapped_ledgers and not any(item and item[10] != "V2_EXISTS_VERIFIED" for item in mapped_ledgers):
                failures.append(Failure("REQ_GAP_LEDGER_STATUS", requirement_id, "at least one non-verified ledger", str([item[10] for item in mapped_ledgers if item]), str(LEDGER_PATH)))
            if status == "REQ_MAPPED_UNKNOWN" and mapped_ledgers and not any(item and item[10] == "UNKNOWN_NEEDS_INSPECTION" for item in mapped_ledgers):
                failures.append(Failure("REQ_UNKNOWN_LEDGER_STATUS", requirement_id, "at least one UNKNOWN_NEEDS_INSPECTION", str([item[10] for item in mapped_ledgers if item]), str(LEDGER_PATH)))
        elif status == "REQ_NEEDS_DOMAIN_DECISION":
            domain_decisions.add(requirement_id)
            if not re.search(r"M\d{2}", milestone):
                failures.append(Failure("REQ_DECISION_MILESTONE", requirement_id, "named milestone", milestone, str(UNIVERSE_PATH)))
            if "decision" not in missing_details.lower():
                failures.append(Failure("REQ_DECISION_DETAILS", requirement_id, "decision need documented", missing_details, str(UNIVERSE_PATH)))
            if "no implementation" not in row[9].lower():
                failures.append(Failure("REQ_DECISION_IMPLEMENTATION", requirement_id, "no implementation authority", row[9], str(UNIVERSE_PATH)))
        else:
            failures.append(Failure("REQ_STATUS_INVALID", requirement_id, str(sorted(allowed_requirement_statuses)), status, str(UNIVERSE_PATH)))

    if domain_decisions != EXPECTED_DECISIONS:
        failures.append(Failure("REQ_DOMAIN_DECISIONS", "", str(sorted(EXPECTED_DECISIONS)), str(sorted(domain_decisions)), str(UNIVERSE_PATH)))

    pass_count = proof_text.count("UNIVERSE_COVERAGE_PROOF_PASS")
    fail_count = proof_text.count("UNIVERSE_COVERAGE_PROOF_FAIL")
    _count_check(failures, "PROOF_PASS_COUNT", 1, pass_count, PROOF_PATH)
    _count_check(failures, "PROOF_FAIL_COUNT", 0, fail_count, PROOF_PATH)
    required_sentence = "The plan is complete against the current Required Capability Universe at requirement-mapping level only."
    if required_sentence not in proof_text:
        failures.append(Failure("PROOF_CONCLUSION_MISSING", "", required_sentence, "missing", str(PROOF_PATH)))
    if "02M remains frozen" not in proof_text:
        failures.append(Failure("PROOF_FROZEN_MISSING", "", "02M remains frozen", "missing", str(PROOF_PATH)))
    if "02M is unfrozen" in proof_text:
        failures.append(Failure("PROOF_FALSE_UNFROZEN", "", "phrase absent", "02M is unfrozen", str(PROOF_PATH)))

    return VerificationResult(
        failures=failures,
        requirements_checked=len(requirements),
        req_unmapped=requirement_statuses["REQ_UNMAPPED"],
        ledger_rows=len(ledger_rows),
        gap_rows=len(gap_rows),
        domain_decisions=len(domain_decisions),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify Retire V2 Universe coverage controls.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args(argv)
    result = verify_repository(args.root)
    if result.passed:
        print("MACHINE_UNIVERSE_COVERAGE_VERIFICATION_PASS")
        print(f"requirements_checked={result.requirements_checked}")
        print("failed_requirements=0")
        print(f"req_unmapped={result.req_unmapped}")
        print(f"ledger_rows={result.ledger_rows}")
        print(f"gap_rows={result.gap_rows}")
        print(f"domain_decisions={result.domain_decisions}")
        return 0

    print("MACHINE_UNIVERSE_COVERAGE_VERIFICATION_FAIL")
    for failure in result.failures:
        print(failure.render())
    failed_requirements = len({item.requirement_id for item in result.failures if item.requirement_id})
    print(f"requirements_checked={result.requirements_checked}")
    print(f"failed_requirements={failed_requirements}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
