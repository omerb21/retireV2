from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/verify_closure_03a_tax_behavior_contracts.py"
B = Path("specs/runtime/V1_BEHAVIOR_FORMULA_RULE_PARITY_MAP.md")
T = Path("specs/runtime/raw_remediation/closure/CLOSURE_INT_01_RAWLOGIC_TRACEABILITY_INDEX.md")
R = Path("specs/runtime/raw_remediation/closure/CLOSURE_03A_TAX_BEHAVIOR_CONTRACTS.md")
D = Path("specs/runtime/raw_remediation/RAW_REM_03_HIGH_RISK_TAX_FIXATION_INDEXATION_DECISIONS.md")

@pytest.fixture()
def repo(tmp_path):
    root = tmp_path / "repo"
    for path in (B, T, R, D):
        (root / path.parent).mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / path, root / path)
    return root

def run(root):
    return subprocess.run([sys.executable, str(SCRIPT), "--repo-root", str(root)], capture_output=True, text=True)

def mutate(root, path, fn):
    target = root / path
    target.write_text(fn(target.read_text(encoding="utf-8")), encoding="utf-8")

def replace_row(text, prefix, width, predicate, index, value):
    for line in text.splitlines():
        if line.startswith(f"| {prefix}"):
            cells=[x.strip() for x in line.strip("|").split("|")]
            if len(cells)==width and predicate(cells):
                cells[index]=value
                return text.replace(line, "| " + " | ".join(cells) + " |", 1)
    raise AssertionError("row not found")

def test_current_passes():
    result=run(ROOT); assert result.returncode==0, result.stdout

def test_selected_count_change_fails(repo):
    mutate(repo,D,lambda x: x.replace(next(l for l in x.splitlines() if l.startswith("| V1LOGIC-") and "TAXMAP_NEEDS_BEHAVIOR_CONTRACT" in l)+"\n","",1))
    assert "SELECTED_SCOPE_COUNT" in run(repo).stdout

def test_behavior_contract_missing_fails(repo):
    mutate(repo,B,lambda x: x.replace(next(l for l in x.splitlines() if l.startswith("| C03A-BEH-"))+"\n","",1))
    assert "BEHAVIOR_CONTRACT" in run(repo).stdout

def test_selected_trace_not_closed_fails(repo):
    mutate(repo,T,lambda x: replace_row(x,"V1LOGIC-",11,lambda c:c[3]=="TAXMAP_NEEDS_BEHAVIOR_CONTRACT",8,"NOT_CLOSED"))
    assert "TRACE_SELECTED_NOT_CLOSED" in run(repo).stdout

@pytest.mark.parametrize("source,outcome",[("RAW-REM-03","TAXMAP_NEEDS_FORMULA_RULE_CONTRACT"),("RAW-REM-04",None),("RAW-REM-05",None)])
def test_extra_row_closed_fails(repo,source,outcome):
    def edit(x):
        y=replace_row(x,"V1LOGIC-",11,lambda c:c[1]==source and (outcome is None or c[3]==outcome),8,"CLOSED_BY_FUTURE_PATCH")
        return replace_row(y,"V1LOGIC-",11,lambda c:c[1]==source and c[8]=="CLOSED_BY_FUTURE_PATCH",9,"fake")
    mutate(repo,T,edit)
    assert "EXTRA_ROW_CLOSED" in run(repo).stdout

def test_trace_evidence_missing_contract_fails(repo):
    mutate(repo,T,lambda x: replace_row(x,"V1LOGIC-",11,lambda c:c[3]=="TAXMAP_NEEDS_BEHAVIOR_CONTRACT",9,"CLOSURE-03A_TAX_BEHAVIOR_CONTRACTS"))
    assert "TRACE_EVIDENCE_INVALID" in run(repo).stdout

def test_forbidden_language_fails(repo):
    mutate(repo,B,lambda x: replace_row(x,"C03A-BEH-",13,lambda c:True,5,"standard tax rule"))
    assert "FORBIDDEN_CONTENT" in run(repo).stdout

def test_implementation_recommendation_fails(repo):
    mutate(repo,R,lambda x:x.replace("## 5. Effect on Raw Coverage","Recommended next step: implementation ready\n\n## 5. Effect on Raw Coverage"))
    assert "FORBIDDEN_CONTENT" in run(repo).stdout

def test_02m_unfrozen_fails(repo):
    mutate(repo,R,lambda x:x.replace("02M: FROZEN","02M: UNFROZEN",1))
    assert "02M_STATUS" in run(repo).stdout

def test_planning_proven_fails(repo):
    mutate(repo,R,lambda x:x.replace("Full planning completeness: NOT_PROVEN","Full planning completeness: PROVEN",1))
    assert "PLANNING_STATUS" in run(repo).stdout

def test_final_marker_missing_fails(repo):
    mutate(repo,R,lambda x:x.replace("CLOSURE_03A_TAX_BEHAVIOR_CONTRACTS_PASS",""))
    assert "FINAL_MARKER_INVALID" in run(repo).stdout

def test_ready_for_review_fails(repo):
    mutate(repo,R,lambda x:x.replace("## 7. Final Marker","READY_FOR_REVIEW\n\n## 7. Final Marker"))
    assert "READY_FOR_REVIEW_FORBIDDEN" in run(repo).stdout
