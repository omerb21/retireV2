#!/usr/bin/env python3
"""Fail-closed verifier for the V1-to-Universe exhaustiveness map."""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path


PASS_MARKER = "V1_TO_UNIVERSE_EXHAUSTIVENESS_MAP_PASS"
FAIL_MARKER = "V1_TO_UNIVERSE_EXHAUSTIVENESS_MAP_FAIL"
ALLOWED_STATUSES = {
    "V1_MAPPED_TO_REQ",
    "V1_DUPLICATE_OF_REQ",
    "V1_REPLACED_BY_REQ",
    "V1_EXCLUDED_WITH_REASON",
    "V1_NOT_APPLICABLE_WITH_REASON",
    "V1_UNMAPPED_FAIL",
}
REQ_REQUIRED = {
    "V1_MAPPED_TO_REQ",
    "V1_DUPLICATE_OF_REQ",
    "V1_REPLACED_BY_REQ",
}
REASON_REQUIRED = {
    "V1_DUPLICATE_OF_REQ",
    "V1_REPLACED_BY_REQ",
    "V1_EXCLUDED_WITH_REASON",
    "V1_NOT_APPLICABLE_WITH_REASON",
}
ROUTE_RE = re.compile(
    r"^(?:GET|POST|PUT|PATCH|DELETE|OPTIONS|HEAD)(?:,(?:GET|POST|PUT|PATCH|DELETE|OPTIONS|HEAD))*\s+/\S*\s+\S+$"
)
MOUNT_RE = re.compile(r"^\s+/\S*\s+\S+$")
LOG_RE = re.compile(r"^\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}(?:,\d+)?\s+")
CAPABILITY_RE = re.compile(r"^###\s+(V1-CAP-\d{3})\b", re.MULTILINE)
COLLECT_NODE_RE = re.compile(r"^(\s*)<(Dir|Package|Module)\s+([^>]+)>\s*$")


@dataclass(frozen=True)
class MapRow:
    item_id: str
    name: str
    source_type: str
    evidence_file: str
    evidence_reference: str
    behavior: str
    req_cell: str
    status: str
    reason: str
    confidence: str
    note: str


@dataclass(frozen=True)
class Failure:
    code: str
    item_id: str
    expected: str
    actual: str
    source_file: str


def parse_args() -> argparse.Namespace:
    script_root = Path(__file__).resolve().parents[1]
    default_evidence = Path(
        r"C:\Users\omer\OneDrive\AI PROJECTS\WINSURDF\dev\Retire V2"
        r"\V1_Source_Verified_Capability_Map_Evidence_2026-07-08"
    )
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=script_root)
    parser.add_argument("--v1-evidence-root", type=Path, default=default_evidence)
    return parser.parse_args()


def parse_inventory_rows(text: str) -> list[MapRow]:
    rows: list[MapRow] = []
    for line in text.splitlines():
        if not re.match(r"^\|\s*V1ITEM-\d{3}\s*\|", line):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) != 11:
            continue
        rows.append(MapRow(*cells))
    return rows


def read_evidence_text(path: Path) -> str:
    data = path.read_bytes()
    if data.startswith((b"\xff\xfe", b"\xfe\xff")):
        return data.decode("utf-16")
    if data.startswith(b"\xef\xbb\xbf"):
        return data.decode("utf-8-sig")
    return data.decode("utf-8", errors="replace")


def enumerate_routes(path: Path) -> tuple[list[str], list[str]]:
    routes: list[str] = []
    uncertain: list[str] = []
    for raw in read_evidence_text(path).splitlines():
        line = raw.rstrip()
        if not line.strip():
            continue
        if ROUTE_RE.match(line) or MOUNT_RE.match(line):
            routes.append(line)
        elif not LOG_RE.match(line):
            uncertain.append(line)
    return routes, uncertain


def enumerate_test_modules(path: Path) -> tuple[list[str], list[str]]:
    stack: dict[int, tuple[str, str]] = {}
    modules: list[str] = []
    uncertain: list[str] = []
    text = read_evidence_text(path)
    for raw in text.splitlines():
        match = COLLECT_NODE_RE.match(raw)
        if not match:
            continue
        indent, kind, name = len(match.group(1)), match.group(2), match.group(3)
        for key in [key for key in stack if key >= indent]:
            del stack[key]
        if kind == "Module":
            parents = [value[1] for _, value in sorted(stack.items())]
            if parents and parents[0].lower() in {"retire", "v1", "repo"}:
                parents = parents[1:]
            module = "/".join([*parents, name]).replace("\\", "/")
            modules.append(module)
        else:
            stack[indent] = (kind, name)
    collected_match = re.search(r"(\d+) tests collected", text)
    if collected_match and int(collected_match.group(1)) > 0 and not modules:
        uncertain.append("pytest reported collected tests but no module nodes were parsed")
    return modules, uncertain


def add_failure(
    failures: list[Failure],
    code: str,
    item_id: str,
    expected: str,
    actual: str,
    source_file: Path,
) -> None:
    failures.append(Failure(code, item_id or "not_applicable", expected, actual, str(source_file)))


def verify(repo_root: Path, evidence_root: Path) -> tuple[list[Failure], dict[str, int]]:
    map_path = repo_root / "specs/runtime/V1_TO_UNIVERSE_EXHAUSTIVENESS_MAP.md"
    universe_path = repo_root / "specs/runtime/V2_REQUIRED_CAPABILITY_UNIVERSE.md"
    failures: list[Failure] = []

    try:
        map_text = map_path.read_text(encoding="utf-8")
    except OSError as exc:
        add_failure(failures, "MAP_READ_ERROR", "", "readable map", str(exc), map_path)
        return failures, {}
    try:
        universe_text = universe_path.read_text(encoding="utf-8")
    except OSError as exc:
        add_failure(failures, "UNIVERSE_READ_ERROR", "", "readable Universe", str(exc), universe_path)
        return failures, {}

    rows = parse_inventory_rows(map_text)
    if not rows:
        add_failure(failures, "V1_INVENTORY_EMPTY", "", "one or more rows", "0", map_path)

    ids = [row.item_id for row in rows]
    expected_ids = [f"V1ITEM-{index:03d}" for index in range(1, len(rows) + 1)]
    if len(ids) != len(set(ids)):
        add_failure(failures, "DUPLICATE_V1_ITEM_ID", "", "unique IDs", "duplicates present", map_path)
    if ids != expected_ids:
        add_failure(
            failures,
            "NON_SEQUENTIAL_V1_ITEM_ID",
            "",
            f"V1ITEM-001..V1ITEM-{len(rows):03d}",
            ",".join(ids[:5]) + ("..." if len(ids) > 5 else ""),
            map_path,
        )

    universe_ids = set(re.findall(r"\bREQ-\d{3}\b", universe_text))
    req_references_checked = 0
    for row in rows:
        reqs = re.findall(r"\bREQ-\d{3}\b", row.req_cell)
        req_references_checked += len(reqs)
        if row.status not in ALLOWED_STATUSES:
            add_failure(failures, "INVALID_MAPPING_STATUS", row.item_id, "allowed status", row.status, map_path)
        if row.status == "V1_UNMAPPED_FAIL":
            add_failure(failures, "V1_UNMAPPED_FAIL_PRESENT", row.item_id, "mapped or classified", row.status, map_path)
        if row.status in REQ_REQUIRED and not reqs:
            add_failure(failures, "MISSING_REQ_TARGET", row.item_id, "at least one REQ ID", row.req_cell, map_path)
        for req in reqs:
            if req not in universe_ids:
                add_failure(failures, "UNKNOWN_REQ_REFERENCE", row.item_id, "existing Universe REQ", req, universe_path)
        if row.status in REASON_REQUIRED and not row.reason.strip():
            add_failure(failures, "MISSING_CLASSIFICATION_REASON", row.item_id, "explicit non-empty reason", "empty", map_path)

    pass_count = map_text.count(PASS_MARKER)
    fail_count = map_text.count(FAIL_MARKER)
    if pass_count != 1 or fail_count != 0:
        add_failure(
            failures,
            "INVALID_FINAL_MARKER",
            "",
            "exactly one PASS and zero FAIL markers",
            f"PASS={pass_count}; FAIL={fail_count}",
            map_path,
        )

    routes_path = evidence_root / "routes_output_clean.txt"
    if routes_path.exists():
        routes, uncertain = enumerate_routes(routes_path)
        if uncertain or not routes:
            add_failure(
                failures,
                "V1_ROUTE_ENUMERATION_UNCERTAIN",
                "",
                "all non-log lines mechanically classified and at least one route",
                "; ".join(uncertain[:3]) if uncertain else "zero routes",
                routes_path,
            )
        route_rows = [row for row in rows if row.source_type == "V1_ROUTE"]
        for route in routes:
            matches = [row for row in route_rows if route.strip() == row.evidence_reference.strip()]
            if len(matches) != 1:
                add_failure(
                    failures,
                    "V1_ROUTE_NOT_EXACTLY_ONCE",
                    matches[0].item_id if matches else "",
                    "one V1_ROUTE inventory reference",
                    f"matches={len(matches)}; route={route}",
                    routes_path,
                )
    else:
        add_failure(failures, "V1_ROUTE_EVIDENCE_MISSING", "", "routes_output_clean.txt", "missing", routes_path)

    collect_path = evidence_root / "pytest_collect_output.txt"
    if collect_path.exists():
        modules, uncertain = enumerate_test_modules(collect_path)
        if uncertain or not modules:
            add_failure(
                failures,
                "V1_TEST_ENUMERATION_UNCERTAIN",
                "",
                "one or more reliably parsed test modules",
                "; ".join(uncertain) if uncertain else "zero modules",
                collect_path,
            )
        test_rows = [row for row in rows if row.source_type == "V1_TEST"]
        for module in modules:
            matches = [row for row in test_rows if module == row.evidence_reference]
            if len(matches) != 1:
                add_failure(
                    failures,
                    "V1_TEST_MODULE_NOT_EXACTLY_ONCE",
                    matches[0].item_id if matches else "",
                    "one exact V1_TEST inventory reference",
                    f"matches={len(matches)}; module={module}",
                    collect_path,
                )
    else:
        add_failure(failures, "V1_TEST_EVIDENCE_MISSING", "", "pytest_collect_output.txt", "missing", collect_path)

    capability_path = evidence_root / "V1_FULL_SOURCE_VERIFIED_CAPABILITY_MAP.md"
    if capability_path.exists():
        capability_ids = CAPABILITY_RE.findall(read_evidence_text(capability_path))
        capability_rows = [row for row in rows if row.source_type == "V1_EVIDENCE_MAP"]
        for capability_id in capability_ids:
            matches = [row for row in capability_rows if capability_id in row.evidence_reference]
            if len(matches) != 1:
                add_failure(
                    failures,
                    "V1_CAPABILITY_NOT_EXACTLY_ONCE",
                    matches[0].item_id if matches else "",
                    "one V1_EVIDENCE_MAP inventory reference",
                    f"matches={len(matches)}; capability={capability_id}",
                    capability_path,
                )
    else:
        add_failure(failures, "V1_CAPABILITY_EVIDENCE_MISSING", "", capability_path.name, "missing", capability_path)

    runtime_rows = [row for row in rows if row.source_type == "V1_RUNTIME_EVIDENCE"]
    runtime_path = evidence_root / "V1_RUNTIME_EVIDENCE_ADDENDUM.md"
    if not runtime_path.exists():
        add_failure(failures, "V1_RUNTIME_EVIDENCE_MISSING", "", runtime_path.name, "missing", runtime_path)
    elif len(runtime_rows) < 5:
        add_failure(failures, "V1_RUNTIME_INVENTORY_INCOMPLETE", "", "at least 5 runtime evidence rows", str(len(runtime_rows)), map_path)

    counts = {
        "v1_items_checked": len(rows),
        "v1_unmapped_fail": sum(row.status == "V1_UNMAPPED_FAIL" for row in rows),
        "req_references_checked": req_references_checked,
        "excluded_or_not_applicable": sum(
            row.status in {"V1_EXCLUDED_WITH_REASON", "V1_NOT_APPLICABLE_WITH_REASON"} for row in rows
        ),
        "replaced_or_duplicate": sum(
            row.status in {"V1_REPLACED_BY_REQ", "V1_DUPLICATE_OF_REQ"} for row in rows
        ),
    }
    return failures, counts


def main() -> int:
    args = parse_args()
    failures, counts = verify(args.repo_root.resolve(), args.v1_evidence_root.resolve())
    if failures:
        print("V1_TO_UNIVERSE_EXHAUSTIVENESS_VERIFICATION_FAIL")
        for failure in failures:
            print(
                f"failure_code={failure.code}; V1_item_id={failure.item_id}; "
                f"expected={failure.expected}; actual={failure.actual}; source_file={failure.source_file}"
            )
        return 1
    print("V1_TO_UNIVERSE_EXHAUSTIVENESS_VERIFICATION_PASS")
    for key in (
        "v1_items_checked",
        "v1_unmapped_fail",
        "req_references_checked",
        "excluded_or_not_applicable",
        "replaced_or_duplicate",
    ):
        print(f"{key}={counts[key]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
