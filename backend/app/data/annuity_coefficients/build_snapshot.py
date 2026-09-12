"""Mechanical, offline extraction of reference-only CSV blobs at the fixed V1 ref.

Usage: python build_snapshot.py PATH_TO_V1_GIT_REPOSITORY
Never reads V1 application databases or client records.
"""
import csv
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys

REF = "e4bd8618cb194aff5f7b9aa0b5388f71cf838292"
TABLES = ("product_to_generation_map", "policy_generation_coefficient", "company_annuity_coefficient", "pension_fund_coefficient")


def build(repository):
    resolved = subprocess.check_output(["git", "-C", repository, "rev-parse", REF]).decode().strip()
    assert resolved == REF
    output = {"version": "v1-annuity-" + REF, "repository": "omerb21/retire", "commit": REF, "sources": {}, "tables": {}}
    for table in TABLES:
        path = "MEKEDMIM/" + table + ".csv"
        raw = subprocess.check_output(["git", "-C", repository, "show", REF + ":" + path])
        rows = list(csv.DictReader(io.StringIO(raw.decode("utf-8-sig"))))
        output["sources"][table] = {"path": path, "sha256": hashlib.sha256(raw).hexdigest(),
            "git_blob": hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest(), "rows": len(rows)}
        # Preserve source order and decimal strings; there is no numerical rewrite.
        output["tables"][table] = rows
    return output


if __name__ == "__main__":
    target = Path(__file__).resolve().parent / "snapshot.json"
    result = build(sys.argv[1])
    target.write_text(json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
    print(json.dumps(result["sources"], ensure_ascii=False))
