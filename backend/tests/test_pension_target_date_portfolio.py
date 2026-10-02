from decimal import (
    Clamped, DivisionByZero, FloatOperation, Inexact, InvalidOperation,
    Overflow, ROUND_HALF_UP, Rounded, Subnormal, Underflow,
)
import ast
import inspect

import pytest

from app.services import pension_target_date_portfolio_service as subject
from app.services import pension_target_date_execution_service as pte


H_A, H_B, H_C, H_D, H_E = (character * 64 for character in "abcde")
TARGET = {"retirement_target_date": "2030-01-01", "retirement_target_ready": True}

FIXTURES = {
    "p1": ("100.004", "2029-01-01", "ILS", "16f1a38bf4aeb632971e39d07723dbace75cad8adb9090f3baef537e9fdab23d", "2f66db9aed4ebc21f267b477676d3fc0e76da6008889bd5409d8e0cceecfccf1", "d60181d88c39e798d9b8bfdb6c43ce79955c44c49026649152826cbe23fb20cd"),
    "p2": ("50.006", "2029-01-01", "ILS", "275e7bd6a20a880b83e0cd40bac36e0bb33f78d73795f33a0bccd876fd97e477", "49ef4d16d26ea24296fa3827fbd42d867bc28225dee97b268c0e7501fa9a93fa", "282bfbfbc30cc0fe400fd33ab3f46b5819c4b1828c87fc063e52f48707b48f41"),
    "f1": ("77.777", "2031-01-01", "ILS", "63317128ff77263ec8786587755daf4685b15c8e6a0f1cdb61321eed44e27938", "8d5154f5c2b1a928010b928c5af6f06b85370e7659b276fdd375bd6a9ff0dc03", "388fc130afda38a4e6666c2e56c69fa6da8e8d2d1f14a6b0ad3e9007d5d35112"),
    "u1": ("20.125", None, "ILS", "acc66dae9881e4c399551dceaffdfd43e8dfbd2877802648b693b02c9996630d", "ed080222b2a331386e9582a25aea3915527ee4084fbd4fcf8463fd3d1e62967e", "c15c75d16d077a71cd3a423419d18496fcfecee7774818dd30d78e73faa2cb4e"),
    "k1": ("1.004", "2029-01-01", "ILS", "0ce7ec33d403dc0dc55f7e472b251ae51e2d3a7233d0f6f7fcac7b4760c6b8ad", "8b34c551b2d9ef9e2c4ef87b1dd21f1e4a6bcd5fc5cb790ad29161a446e7314a", "13f157db521c89d4e9ecee56e60716d1f054831f2da24d65bef6c5ee8fb0cadb"),
    "k2": ("1.004", "2029-01-01", "ILS", "6fda7cb74c1f1e3c4a0ddcfa6721f1c3995794c3e6a10c9641a5ed4d424a27e8", "0fb8e1dbadda86e86941ff873f807fe2285ba216e75b648eee7ca869ec916ed4", "a5c852b9edf1959db1042643dee2d161fad14adb9387296eee258b11708cffd5"),
    "n1": ("12.345", "2029-01-01", None, "5145e3a82040a0b957a2ff92f245ce5e299dc7e34786e42faa0fb6ab1c041845", "b4f875666f6a4289e3331b982430ca67cafabab3e45fceef26fcc7fca13bc53b", "7ae1c7fd5765abb911268b97472dc862875f913de5b6bef1241218b14f509d1e"),
    "x1": ("30", "2029-01-01", "USD", "ab79954853d69bf3b5b0b47c725b9e9263061be34e7217a816aa950594c40b58", "10a2b194e1c84de1f438486a0cc4e27d6fd34017fba9651b9a9e651f2d6b29ec", "336670b22e039f746c2f171fec17b9dcc142b28bce295c8bcaf02718f81d5c06"),
    "b1": ("NaN", "2029-01-01", "ILS", "76c6a7c7ade30407a7d8d113d3630b0b9fa9e89ab6f6dac8ee7807555c55a849", "a6b45b9af8bdf70236015f742dbdb9b5428f4fe3b7e14f608b6bb7ea084c168b", "e57d655dc20251f1d9c620c64804afc5a09f9d5ea4a88ef0cc4cdac46182df55"),
}

GOLDENS = {
    "A": ([], "2c7fa7a0aa613d28fc05bfe81ac49624ffea7eedce253c6f84507e27f7f7f180", "864d5d8c8e7cac1b0a30f59570eb53164ddf7940e6e0748d95fc5d5baa88b115", "0", "0.00"),
    "B": (["p1"], "daefe24dd720e9d0759f58e121e1f5022d8974dd2d01ace43520c425c497a6ce", "7b8668ad77428d45464b67b61133c1ce5a5f3454e33637a8b935e3e099fd1807", "100.004", "100.00"),
    "C": (["p1", "p2"], "d2474b7db7ceb31af2b47b92d0fd03768e94266753e0694a07825b9b7b4d4fc7", "8106460ab69df866656dbd996a3aa67a9d4717961e91d20613bce2c49daf8805", "150.01", "150.01"),
    "D": (["f1", "p1"], "32a794670ecd57a748125d79c8dc7e15a413be7b743941470ff118c361ef20cc", "9b61af99aeb130d8807f0848577c1f37f7494501422a09c54a94b00be249ee6f", "100.004", "100.00"),
    "E": (["p1", "u1"], "b642b96dae29d0ae7c9178b33b9a909a36fe4d2442d881d46b9106855825bfe3", "663b25036d184c7c9c3353a3102115b7aa4c31b83d69d639b31e070831cb875a", "100.004", "100.00"),
    "F": (["b1", "p1"], "44ec9abc6598d3e68ff3a01713e48fc8d26529dc6a9ed6a547f40bf606f3a42f", "0277c127a073fbbd1c1ea67c8b8bd5dde1a200cc31ac4c3263b6a86500dc6e19", "100.004", "100.00"),
    "G": (["f1"], "9cd49cc976d71d0c59ec6da42af1121f0bd40f83c1c87a71f1e584a35259046f", "2f8e2360113194a45b00d9a2185cc0e48e58982dc37ad53bbc2916c8da570096", "0", "0.00"),
    "H": (["u1"], "aad31cc6fd8e7c2573f39aed9ea4ede223d44b6df6098e333cfa96b904112d7b", "8cc201a07025bf2fde991f958dbdfeef08e709ff64ce87e275cb2ce45028177d", "0", "0.00"),
    "I": (["b1"], "ce10bca0a2587493b59d9e0b82cf3d2d6d4eac359c2adc806755c1ecacc8ccf3", "a86eb6e9009b30d2eff6b16b9ff88a2724ac5acae66bc882fea243ed12815672", "0", "0.00"),
    "J": (["b1", "f1", "p1", "u1"], "573b7b57031db9966b81d5dbfb5b179074e012e4aa1c96e4dece5dfe08c781a4", "207b61e447ffd66c540f13e6487783b43bf1dcf4bccc2153f6e3f8050c122a8d", "100.004", "100.00"),
    "K": (["k1", "k2"], "12de4313569575169860249cc411ca68ca4c009499e5f0010f39f97d117684cc", "7f6fa7ce9bc2c2966ed2dd34fe08ac8bd242d4e5a5f7cd873dd32cff570d84c2", "2.008", "2.01"),
    "L": (["n1"], "0f3949f5d7ed7deca1fa7a069736aeb26223939569db0cdfe4973633ff84db2f", "69736cc5f8139bdd26a784d802e3dc9ad02a0ea93cb485e5ddda028df9126e7a", "12.345", "12.35"),
    "N": (["x1"], "0b6f1bf5bf5c0f607cf1f44f735221d0e16eb78690ef8b55b66b41abc115c58b", "3d39fe7f03195ecf8dd58f97a0653d8c9e186a649a06016e42cd005a6b3b4b86", "0", "0.00"),
}


def source(source_id):
    amount, start, currency, *_ = FIXTURES[source_id]
    return {
        "source_id": source_id,
        "pension_start_date": start,
        "currency": currency,
        "monthly_amount_basis": {
            "authority_kind": "entered_monthly_amount",
            "base_amount_representation": {"amount": amount, "representation_kind": "exact_money"},
            "base_amount_semantic_fingerprint": H_B,
            "base_amount_source_fingerprint": H_C,
            "basis_authority_ready": True,
            "basis_blockers": [],
        },
        "temporal_authority": {
            "temporal_authority_kind": "none",
            "temporal_origin_date": "2029-01-01",
            "annual_rate": None,
            "temporal_semantic_fingerprint": H_D,
            "temporal_source_fingerprint": H_E,
            "temporal_authority_ready": True,
            "temporal_blockers": [],
        },
    }


def planning(ids):
    return {
        "planning_calculation_input_fingerprint": H_A,
        "retirement_target": TARGET,
        "pension_inputs": [source(source_id) for source_id in ids if source_id != "b1"]
            + ([{**source("p1"), "source_id": "b1", "monthly_amount_basis": {
                **source("p1")["monthly_amount_basis"],
                "base_amount_representation": {"amount": "NaN", "representation_kind": "exact_money"},
            }}] if "b1" in ids else []),
    }


def run(monkeypatch, ids):
    plan = planning(ids)
    monkeypatch.setattr(subject.planning_input_service, "read", lambda db, client_id: plan)
    return subject.read(object(), 7, H_A)


@pytest.mark.parametrize("name", GOLDENS)
def test_accepted_golden_a_through_n(monkeypatch, name):
    ids, execution_hash, result_hash, exact, total = GOLDENS[name]
    result = run(monkeypatch, ids)
    assert result["portfolio_execution_fingerprint"] == execution_hash
    assert result["portfolio_result_fingerprint"] == result_hash
    assert result["aggregate_unquantized_amount"] == exact
    assert result["payable_current_monthly_total"] == total
    for item in result["source_results"]:
        expected = FIXTURES[item["source_id"]]
        assert item["source_execution_fingerprint"] == expected[3]
        assert item["source_result_fingerprint"] == expected[4]
    assert result["source_entry_fingerprints"] == [
        {"source_id": source_id, "source_entry_fingerprint": FIXTURES[source_id][5]}
        for source_id in sorted(ids)
    ]


def test_b1_uses_blocked_result_identity_despite_non_null_execution_fingerprint(monkeypatch):
    result = run(monkeypatch, ["b1"])
    item = result["source_results"][0]
    assert item["result_state"] == "block_no_result"
    assert item["source_execution_fingerprint"] == FIXTURES["b1"][3]
    expected_payload = {
        "aggregation_contract": subject.AGGREGATION_CONTRACT,
        "client_id": 7,
        "contract": subject.EXECUTION_CONTRACT,
        "planning_calculation_input_fingerprint": H_A,
        "retirement_target_date": "2030-01-01",
        "source_identities": [{
            "source_id": "b1", "source_identity_fingerprint": FIXTURES["b1"][4],
            "source_identity_kind": "blocked_result_fingerprint", "source_result_state": "block_no_result",
        }],
        "system_currency": "ILS",
        "total_completeness_state": "partial",
    }
    assert subject._fingerprint(expected_payload) == result["portfolio_execution_fingerprint"]


def test_single_snapshot_sorted_sequential_execution_and_no_global_ready_gate(monkeypatch):
    plan = planning(["p2", "p1"])
    plan["planning_input_ready"] = False
    calls = []
    monkeypatch.setattr(subject.planning_input_service, "read", lambda db, client_id: calls.append("read") or plan)
    original = pte.execute_from_planning_result
    def execute(snapshot, source_id, **kwargs):
        calls.append(source_id)
        assert snapshot is plan
        return original(snapshot, source_id, **kwargs)
    monkeypatch.setattr(subject.pte, "execute_from_planning_result", execute)
    assert subject.read(object(), 7, H_A)["result_state"] == "result_ready"
    assert calls == ["read", "p1", "p2"]


def test_executor_exception_stops_and_discards_prefix(monkeypatch):
    plan = planning(["p1", "p2"])
    monkeypatch.setattr(subject.planning_input_service, "read", lambda db, client_id: plan)
    original = pte.execute_from_planning_result
    calls = []
    def execute(snapshot, source_id, **kwargs):
        calls.append(source_id)
        if source_id == "p2":
            raise RuntimeError("boom")
        return original(snapshot, source_id, **kwargs)
    monkeypatch.setattr(subject.pte, "execute_from_planning_result", execute)
    result = subject.read(object(), 7, H_A)
    assert calls == ["p1", "p2"]
    assert result["portfolio_blockers"] == ["PORTFOLIO_SOURCE_EXECUTION_ERROR"]
    assert result["coverage_evidence"]["coverage_check_state"] == "incomplete"
    assert result["coverage_evidence"]["returned_source_ids"] == ["p1"]
    assert result["source_results"] == []
    assert result["portfolio_result_fingerprint"] == "1770556a2fb78e9164b8efa9ac2243499f3022e6208e515be2f7a9c1c193a644"


def test_stale_and_target_fatal_hashes(monkeypatch):
    plan = planning([])
    monkeypatch.setattr(subject.planning_input_service, "read", lambda db, client_id: plan)
    stale = subject.read(object(), 7, "b" * 64)
    assert stale["portfolio_result_fingerprint"] == "0d7217e2731c3a022568618ca14bce9bb5b8abc186580d95817228ae93d7eee9"
    plan["retirement_target"] = {"retirement_target_date": None, "retirement_target_ready": False}
    target = subject.read(object(), 7, H_A)
    assert target["portfolio_result_fingerprint"] == "5e84e5d83a6350351762cad416723484d275fec151aa5ca0f6081ba0b520b086"
    for result in (stale, target):
        assert "aggregate_unquantized_amount" not in result
        assert set(result["failure_evidence"]) == {
            "current_planning_calculation_input_fingerprint", "failed_expected_source_id",
            "failure_detail_code", "failure_stage", "observed_source_id",
            "supplied_planning_calculation_input_fingerprint",
        }


def test_duplicate_source_universe_fatal_hash(monkeypatch):
    plan = planning(["p1"])
    plan["pension_inputs"].append(dict(plan["pension_inputs"][0]))
    monkeypatch.setattr(subject.planning_input_service, "read", lambda db, client_id: plan)
    result = subject.read(object(), 7, H_A)
    assert result["portfolio_result_fingerprint"] == "2f863b50045eef9bb5111ba208e4790307183024593f053875d3b779d47c495d"
    assert result["coverage_evidence"] == {
        "coverage_check_state": "invalid", "duplicate_source_ids": ["p1"],
        "expected_source_ids": ["p1", "p1"], "missing_source_ids": [],
        "returned_source_ids": [], "unexpected_source_ids": [],
    }


@pytest.mark.parametrize(("expected", "returned", "expected_hash"), [
    (["p1", "p2"], ["p1"], "c385d759ad85a6365208c59815a6ff47265153fc2d8eb98ff9cf028a8db743ed"),
    (["p1"], ["p1", "x1"], "dfcb20e2f2e2f44edd62b97bc2db3726e5819254a46d5a796cddd8b23e96b709"),
    (["p1"], ["p1", "p1"], "5ccfca6674a274fd885e34e7cf2ee745f21eb6192361784dee76b10cef71a984"),
])
def test_coverage_fatal_hashes(expected, returned, expected_hash):
    results = []
    for source_id in returned:
        plan = planning([source_id])
        item = pte.execute_from_planning_result(
            plan, source_id,
            supplied_planning_calculation_input_fingerprint=H_A,
            supplied_monthly_basis_semantic_fingerprint=H_B,
            supplied_monthly_basis_source_fingerprint=H_C,
            supplied_temporal_semantic_fingerprint=H_D,
            supplied_temporal_source_fingerprint=H_E,
        )
        results.append(item)
    result = subject._assemble_ready(7, H_A, H_A, "2030-01-01", expected, results)
    assert result["portfolio_result_fingerprint"] == expected_hash


def test_wrong_per_call_source_ids_are_coverage_failure():
    results = [ready_result("p2"), ready_result("p1")]
    result = subject._assemble_ready(7, H_A, H_A, "2030-01-01", ["p1", "p2"], results)
    assert result["result_state"] == "block_no_result"
    assert result["coverage_evidence"]["coverage_check_state"] == "invalid"
    assert result["portfolio_blockers"] == ["PORTFOLIO_SOURCE_COVERAGE_MISSING"]
    assert result["source_results"] == []


def ready_result(source_id="p1"):
    plan = planning([source_id])
    return pte.execute_from_planning_result(
        plan, source_id,
        supplied_planning_calculation_input_fingerprint=H_A,
        supplied_monthly_basis_semantic_fingerprint=H_B,
        supplied_monthly_basis_source_fingerprint=H_C,
        supplied_temporal_semantic_fingerprint=H_D,
        supplied_temporal_source_fingerprint=H_E,
    )


def test_invalid_pte_schema_and_fingerprint_fatal_hashes():
    invalid_schema = {**ready_result(), "schema_version": "wrong"}
    result = subject._assemble_ready(7, H_A, H_A, "2030-01-01", ["p1"], [invalid_schema])
    assert result["portfolio_result_fingerprint"] == "e57dfa81f405a7bb34712e432fceb1f9b0c8c061452b493ad675fdedef78f16a"
    invalid_fingerprint = {**ready_result(), "source_result_fingerprint": "0" * 64}
    result = subject._assemble_ready(7, H_A, H_A, "2030-01-01", ["p1"], [invalid_fingerprint])
    assert result["portfolio_result_fingerprint"] == "b834495e932c14d002030b3c69954f0cdef198961f6429f50fe9a8d0ffc89c18"


def test_aggregation_numeric_error_fatal_hash():
    plan = planning(["p1"])
    item = pte.execute_from_planning_result(
        plan, "p1",
        supplied_planning_calculation_input_fingerprint=H_A,
        supplied_monthly_basis_semantic_fingerprint=H_B,
        supplied_monthly_basis_source_fingerprint=H_C,
        supplied_temporal_semantic_fingerprint=H_D,
        supplied_temporal_source_fingerprint=H_E,
    )
    item = {**item, "source_id": "q1", "unquantized_target_monthly_amount": "9" * 101}
    payload = subject._pte_result_payload(item)
    item["source_result_fingerprint"] = subject._fingerprint(payload)
    result = subject._assemble_ready(7, H_A, H_A, "2030-01-01", ["q1"], [item])
    assert result["portfolio_result_fingerprint"] == "13987216fb52232a6aef9fccb9e25d16d58d1c0baf564cfaba62a01395a20b88"
    assert "aggregate_unquantized_amount" not in result


def test_portfolio_identity_error_fatal_hash(monkeypatch):
    original = subject._fingerprint
    def fail_execution(payload):
        if payload.get("contract") == subject.EXECUTION_CONTRACT:
            raise ValueError("identity")
        return original(payload)
    monkeypatch.setattr(subject, "_fingerprint", fail_execution)
    result = subject._assemble_ready(7, H_A, H_A, "2030-01-01", ["p1"], [ready_result()])
    assert result["portfolio_result_fingerprint"] == "153318d0f8c148c7c4c14dec751bcc2af6cb54fee8229e09a2147aaee03dcaa0"
    assert result["portfolio_execution_fingerprint"] is None


@pytest.mark.parametrize(("text", "accepted"), [
    ("0." + "0" * 99 + "1", True),
    ("9" * 100, True),
    ("9" * 101, False),
    ("0." + "0" * 100 + "1", False),
    ("01", False), ("1.0", False), ("1e2", False), ("-1", False), ("0", False),
])
def test_numeric_admission_boundaries(text, accepted):
    if accepted:
        assert subject._parse_amount(text)
    else:
        with pytest.raises(ValueError):
            subject._parse_amount(text)


def test_aggregate_integer_digit_boundaries_and_single_rounding():
    assert subject._canonical_sum([subject._parse_amount("9" * 97)]) == "9" * 97
    with pytest.raises(ValueError):
        subject._canonical_sum([subject._parse_amount("9" * 98)])
    exact = subject._canonical_sum([subject._parse_amount("1.004"), subject._parse_amount("1.004")])
    assert (exact, subject._quantize(exact)) == ("2.008", "2.01")


def test_quantize_trapped_failure_has_no_adaptive_precision(monkeypatch):
    trapped = subject.decimal_context()
    trapped.traps[Inexact] = True
    monkeypatch.setattr(subject, "decimal_context", lambda: trapped)
    with pytest.raises(ValueError):
        subject._quantize("1.001")


def test_missing_non_string_and_noncanonical_unquantized_amounts_fail_closed():
    original = ready_result()
    for value in (None, 1.2):
        changed = dict(original)
        if value is None:
            changed.pop("unquantized_target_monthly_amount")
        else:
            changed["unquantized_target_monthly_amount"] = value
        result = subject._assemble_ready(7, H_A, H_A, "2030-01-01", ["p1"], [changed])
        assert result["portfolio_blockers"] == ["PORTFOLIO_SOURCE_RESULT_SCHEMA_INVALID"]
    for value in ("01", "1.0", "1e2", "-1", "0"):
        changed = {**original, "unquantized_target_monthly_amount": value}
        result = subject._assemble_ready(7, H_A, H_A, "2030-01-01", ["p1"], [changed])
        assert result["portfolio_blockers"] == ["PORTFOLIO_AGGREGATION_NUMERIC_ERROR"]


def test_decimal_context_is_fresh_exact_and_ambient_independent():
    first, second = subject.decimal_context(), subject.decimal_context()
    assert first is not second
    assert (first.prec, first.rounding, first.Emin, first.Emax, first.clamp, first.capitals) == (
        100, ROUND_HALF_UP, -999999, 999999, 0, 1,
    )
    for signal in (InvalidOperation, DivisionByZero, Overflow, FloatOperation):
        assert first.traps[signal]
    for signal in (Clamped, Inexact, Rounded, Subnormal, Underflow):
        assert not first.traps[signal]
    assert not any(first.flags.values())


def test_result_fingerprint_failure_has_explicit_exception(monkeypatch):
    monkeypatch.setattr(subject, "canonical_bytes", lambda value: (_ for _ in ()).throw(TypeError("bad")))
    with pytest.raises(subject.PortfolioResultFingerprintConstructionError):
        subject._result_fingerprint({"x": 1})


def test_service_is_read_only_and_has_no_float_or_persistence_dependency():
    source_text = inspect.getsource(subject).lower()
    tree = ast.parse(source_text)
    assert "sqlalchemy" not in source_text
    assert "alembic" not in source_text
    assert not any(isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                   and node.func.id == "float" for node in ast.walk(tree))
