"""Privacy-safe XML assembled here, never copied from owner source files.

Only the explicitly authorized account/product identifiers and golden amounts
and statement date are retained. Provider and wrappers are synthetic data.
"""
import ast
from decimal import Decimal
from pathlib import Path
import subprocess

import pytest

from app.models.pension_product import COMPONENT_CODES
from app.services import pension_product_import_service as importer
from app.services.pension_product_service import PensionProductError
from test_recovery_pension_products import engine, layer
from test_recovery_batch_import import ingest, snapshot

GOLDENS = [
    ("444-914-295865-0", "מיטב גמל בניהול אישי", "8267592.26"),
    ("032-252-566418-0", "מיטב גמל", "1077664.59"),
]


def row(code="4", amount="10", extra=""):
    return f"<PerutYitrot><KOD-SUG-HAFRASHA>{code}</KOD-SUG-HAFRASHA><TOTAL-CHISACHON-MTZBR>{amount}</TOTAL-CHISACHON-MTZBR><TOTAL-ERKEI-PIDION>{amount}</TOTAL-ERKEI-PIDION>{extra}</PerutYitrot>"


def xml(account="fixture-A", name="מוצר בדיקה", amount="10", *, rows=None, primary="", extras="", product_type="3"):
    severance = "".join(f"<{tag}>0</{tag}>" for tag in (
        "ERECH-PIDION-PITZUIM-MAASIK-NOCHECHI", "TZVIRAT-PITZUIM-PTURIM-MAAVIDIM-KODMIM",
        "TZVIRAT-PITZUIM-MAAVIDIM-KODMIM-BERETZEF-ZECHUYOT", "TZVIRAT-PITZUIM-MAAVIDIM-KODMIM-BERETZEF-KITZBA"))
    return f"""<Root><SHEM-YATZRAN>ספק בדיקה</SHEM-YATZRAN>
      <Mutzar><NetuneiMutzar><SUG-MUTZAR>{product_type}</SUG-MUTZAR></NetuneiMutzar>
      <HeshbonOPolisa><MISPAR-POLISA-O-HESHBON>{account}</MISPAR-POLISA-O-HESHBON>
      <SHEM-TOCHNIT>{name}</SHEM-TOCHNIT><TAARICH-NECHONUT-YITROT>20260228</TAARICH-NECHONUT-YITROT>
      <PirteiTaktziv><BlockItrot><Yitrot>{primary}{row(amount=amount) if rows is None else rows}
      <NesilutTag><YITRAT-KASPEY-TAGMULIM>{amount}</YITRAT-KASPEY-TAGMULIM></NesilutTag>
      {severance}</Yitrot></BlockItrot></PirteiTaktziv>{extras}</HeshbonOPolisa></Mutzar></Root>""".encode()


def states(account):
    return {d["component"]: d["state"] for d in account["diagnostics"] if d["code"] == "component_source_state"}


def test_clean_two_real_structure_products_exact_golden_and_source_states(engine):
    files = [(f"privacy-safe-{i}.xml", xml(account, name, amount, primary=layer("4", "7", amount)))
             for i, (account, name, amount) in enumerate(GOLDENS)]
    batch = ingest(engine, files)
    assert batch["product_count"] == 2 and batch["file_count"] == 2
    products = {p["account_reference"]: p for p in batch["products"]}
    assert len({p["source_identity"] for p in batch["products"]}) == 2
    for account, name, amount in GOLDENS:
        p = products[account]
        assert p["product_name"] == name and p["product_type"] == "קופת גמל"
        assert p["statement_date"] == "2026-02-28"
        assert p["reported_product_total"] == p["reported_rewards_total"] == amount
        assert p["reported_severance_total"] is None
        assert p["components"][COMPONENT_CODES[6]] == amount
        assert len(p["components"]) == 11 and set(p["components"]) == set(COMPONENT_CODES)
        assert all(v == "0.00" for k, v in p["components"].items() if k != COMPONENT_CODES[6])
        assert p["reconciliation"]["product_component_sum"] == amount
        assert p["reconciliation"]["product_discrepancy"] == "0.00"
        assert p["reconciliation"]["rewards_discrepancy"] == "0.00"
        assert p["reconciliation"]["severance_discrepancy"] is None
        parsed = importer._parse_source(files[GOLDENS.index((account, name, amount))][1])[0]
        expected = dict.fromkeys(COMPONENT_CODES, "SOURCE_ABSENT")
        expected.update({COMPONENT_CODES[i]: "SOURCE_EXPLICIT_ZERO" for i in (0, 2, 3, 4)})
        expected[COMPONENT_CODES[6]] = "SOURCE_PRESENT_NONZERO_MAPPED"
        assert states(parsed) == expected


@pytest.mark.parametrize("sug,component", [(c, COMPONENT_CODES[6]) for c in ("2", "4", "8", "10")] + [(c, COMPONENT_CODES[9]) for c in ("3", "7", "9", "11")])
def test_only_accepted_fallback_code_groups(sug, component):
    parsed = importer._parse_source(xml(rows=row(sug, "12.34"), amount="12.34"))[0]
    assert parsed["components"][component] == Decimal("12.34")
    assert sum(parsed["components"].values()) == Decimal("12.34")


def test_multiple_fallback_rows_sum_and_summary_aliases_not_double_counted():
    parsed = importer._parse_source(xml(rows=row("4", "12.34") + row("10", "56.78"), amount="69.12"))[0]
    assert parsed["components"][COMPONENT_CODES[6]] == Decimal("69.12")
    assert parsed["metadata"]["reported_product_total"] == Decimal("69.12")
    assert parsed["metadata"]["reported_rewards_total"] == Decimal("69.12")


@pytest.mark.parametrize("amount", ["0", "12.34"])
def test_primary_employee_prevents_fallback_double_count_including_explicit_zero(amount):
    parsed = importer._parse_source(xml(primary=layer("2", "7", amount), rows=row("4", "90") + row("3", "20")))[0]
    assert parsed["components"][COMPONENT_CODES[7]] == Decimal(amount)
    assert COMPONENT_CODES[6] not in parsed["components"]
    assert parsed["components"][COMPONENT_CODES[9]] == Decimal("20")  # Other role can still fallback.
    assert states(parsed)[COMPONENT_CODES[6]] == "SOURCE_ABSENT"


def test_primary_employer_blocks_only_employer_fallback():
    parsed = importer._parse_source(xml(primary=layer("3", "1", "5"), rows=row("7", "90") + row("4", "20")))[0]
    assert parsed["components"][COMPONENT_CODES[8]] == Decimal("5")
    assert COMPONENT_CODES[9] not in parsed["components"]
    assert parsed["components"][COMPONENT_CODES[6]] == Decimal("20")


def test_missing_primary_amount_does_not_prevent_valid_fallback():
    primary = '<PerutYitraLeTkufa><REKIV-ITRA-LETKUFA>2</REKIV-ITRA-LETKUFA><KOD-TECHULAT-SHICHVA>7</KOD-TECHULAT-SHICHVA></PerutYitraLeTkufa>'
    parsed = importer._parse_source(xml(primary=primary))[0]
    assert parsed["components"][COMPONENT_CODES[6]] == Decimal("10")


def test_rekiv_four_and_sug_itra_three_never_infer_employee_or_period():
    primary = layer("4", "7", "42").replace("</PerutYitraLeTkufa>", "<SUG-ITRA-LETKUFA>3</SUG-ITRA-LETKUFA></PerutYitraLeTkufa>")
    parsed = importer._parse_source(xml(primary=primary, rows=""))[0]
    assert "4" not in importer.ROLE_CODES
    assert COMPONENT_CODES[7] not in parsed["components"]
    assert sum(parsed["components"].values()) == 0
    assert any(d.get("state") == "SOURCE_PRESENT_NONZERO_UNMAPPED" and d.get("value") == "42.00" and d["unresolved"] for d in parsed["diagnostics"])


@pytest.mark.parametrize("amount,state", [("42", "SOURCE_PRESENT_NONZERO_UNMAPPED"), ("0", "SOURCE_EXPLICIT_ZERO")])
def test_unknown_fallback_role_is_not_distributed(amount, state):
    parsed = importer._parse_source(xml(rows=row("99", amount), amount=amount))[0]
    assert sum(parsed["components"].values()) == 0
    assert all(states(parsed)[code] == "SOURCE_ABSENT" for code in COMPONENT_CODES[5:])
    assert any(d["code"] == "unmapped_fallback_role" and d["value"] == "99" for d in parsed["diagnostics"])
    assert any(d.get("state") == state and d.get("component") is None for d in parsed["diagnostics"])


def test_zero_fallback_is_distinct_from_absent_component():
    parsed = importer._parse_source(xml(amount="0"))[0]
    assert states(parsed)[COMPONENT_CODES[6]] == "SOURCE_EXPLICIT_ZERO"
    assert states(parsed)[COMPONENT_CODES[5]] == "SOURCE_ABSENT"
    assert parsed["metadata"]["reported_severance_total"] is None


def test_nearest_product_metadata_scope_never_leaks_between_products():
    first = xml("A", product_type="3").decode().split("<Mutzar>", 1)[1].split("</Mutzar>", 1)[0]
    second = xml("B", product_type="4").decode().split("<Mutzar>", 1)[1].split("</Mutzar>", 1)[0]
    raw = f"<Root><Provider>fixture</Provider><Mutzar><NetuneiMutzar><SUG-MUTZAR>1</SUG-MUTZAR></NetuneiMutzar><Mutzar>{first}</Mutzar></Mutzar><Mutzar>{second}</Mutzar></Root>".encode()
    accounts = importer._parse_source(raw)
    assert {a["metadata"]["account_reference"]: a["metadata"]["product_type"] for a in accounts} == {"A": "3", "B": "4"}


@pytest.mark.parametrize("wrapper", ["TachazitPrisha", "NetuneiShanaKodemet", "UnrecognizedContainer"])
def test_noncurrent_hierarchies_not_used_for_totals_or_fallback(wrapper):
    extra = f"<{wrapper}><PirteiTaktziv><BlockItrot><Yitrot>{row('4', '999999')}<NesilutTag><YITRAT-KASPEY-TAGMULIM>888888</YITRAT-KASPEY-TAGMULIM><YITRAT-PITZUIM>777777</YITRAT-PITZUIM></NesilutTag></Yitrot></BlockItrot></PirteiTaktziv></{wrapper}>"
    parsed = importer._parse_source(xml(extras=extra))[0]
    assert parsed["metadata"]["reported_product_total"] == Decimal("10")
    assert parsed["metadata"]["reported_rewards_total"] == Decimal("10")
    assert parsed["metadata"]["reported_severance_total"] is None
    assert parsed["components"][COMPONENT_CODES[6]] == Decimal("10")
    without_current = xml(rows="", extras=extra).decode().replace("<YITRAT-KASPEY-TAGMULIM>10</YITRAT-KASPEY-TAGMULIM>", "").encode()
    absent = importer._parse_source(without_current)[0]
    assert all(absent["metadata"][key] is None for key in ("reported_product_total", "reported_rewards_total", "reported_severance_total"))
    assert COMPONENT_CODES[6] not in absent["components"]


def test_obsolete_flat_summary_is_not_current_balance_authority():
    raw = b"<Root><Provider>fixture</Provider><Account><MISPAR-HESHBON>A</MISPAR-HESHBON><TOTAL-CHISACHON-MTZBR>999</TOTAL-CHISACHON-MTZBR><YITRAT-KASPEY-TAGMULIM>999</YITRAT-KASPEY-TAGMULIM><YITRAT-PITZUIM>999</YITRAT-PITZUIM></Account></Root>"
    parsed = importer._parse_source(raw)[0]
    assert all(parsed["metadata"][key] is None for key in ("reported_product_total", "reported_rewards_total", "reported_severance_total"))
    assert parsed["components"] == {}


def test_fallback_role_must_belong_to_the_current_row_not_nested_history():
    raw = xml(rows="<PerutYitrot><PriorYear><KOD-SUG-HAFRASHA>4</KOD-SUG-HAFRASHA></PriorYear><TOTAL-CHISACHON-MTZBR>10</TOTAL-CHISACHON-MTZBR></PerutYitrot>")
    parsed = importer._parse_source(raw)[0]
    assert COMPONENT_CODES[6] not in parsed["components"]
    assert any(d.get("unresolved") and d["value"] == "10.00" for d in parsed["diagnostics"])


def test_missing_total_does_not_become_explicit_zero_or_usable_fallback():
    raw = xml(rows="<PerutYitrot><KOD-SUG-HAFRASHA>4</KOD-SUG-HAFRASHA></PerutYitrot>")
    parsed = importer._parse_source(raw)[0]
    assert parsed["metadata"]["reported_product_total"] is None
    assert states(parsed)[COMPONENT_CODES[6]] == "SOURCE_ABSENT"


def test_redemption_total_is_summary_only_not_a_fallback_amount():
    raw = xml(rows="<PerutYitrot><KOD-SUG-HAFRASHA>4</KOD-SUG-HAFRASHA><TOTAL-ERKEI-PIDION>10</TOTAL-ERKEI-PIDION></PerutYitrot>")
    parsed = importer._parse_source(raw)[0]
    assert parsed["metadata"]["reported_product_total"] == Decimal("10")
    assert COMPONENT_CODES[6] not in parsed["components"]
    assert any(d.get("unresolved") and d["value"] == "10.00" for d in parsed["diagnostics"])


def test_equal_monetary_aliases_with_different_formatting_are_one_total():
    raw = xml(rows=row(amount="10").replace("<TOTAL-ERKEI-PIDION>10<", "<TOTAL-ERKEI-PIDION>10.00<"))
    parsed = importer._parse_source(raw)[0]
    assert parsed["metadata"]["reported_product_total"] == Decimal("10")
    assert parsed["components"][COMPONENT_CODES[6]] == Decimal("10")


def test_conflicting_current_summary_aliases_fail_closed():
    raw = xml(rows=row(amount="10").replace("<TOTAL-ERKEI-PIDION>10<", "<TOTAL-ERKEI-PIDION>11<"))
    with pytest.raises(PensionProductError) as failure:
        importer._parse_source(raw)
    assert failure.value.code == "AMBIGUOUS_SOURCE_FACT"


def test_partial_single_then_full_batch_fails_without_mutation(engine):
    files = [(f"safe-{i}.xml", xml(*golden)) for i, golden in enumerate(GOLDENS)]
    ingest(engine, files[:1])
    before = snapshot(engine)
    with pytest.raises(PensionProductError) as failure:
        ingest(engine, files)
    assert failure.value.code == "PARTIAL_OVERLAP_SOURCE_BATCH"
    assert snapshot(engine) == before


def test_real_structure_exact_retry_preserves_all_rows(engine):
    files = [(f"safe-{i}.xml", xml(*golden)) for i, golden in enumerate(GOLDENS)]
    first = ingest(engine, files)
    before = snapshot(engine)
    retry = ingest(engine, [("renamed.dat", raw) for _, raw in reversed(files)])
    assert retry["batch_identity"] == first["batch_identity"] and retry["product_count"] == 2
    assert snapshot(engine) == before


def test_namespace_does_not_change_real_structure_mapping():
    raw = xml().replace(b"<Root>", b'<Root xmlns="urn:privacy-safe-test">')
    parsed = importer._parse_source(raw)[0]
    assert parsed["components"][COMPONENT_CODES[6]] == Decimal("10")
    assert parsed["metadata"]["product_type"] == "3"


def test_batch_engine_currentization_and_identity_functions_unchanged_from_accepted_base():
    root = Path(__file__).resolve().parents[2]
    path = "backend/app/services/pension_product_import_service.py"
    accepted = subprocess.check_output(["git", "show", f"a2ebdeffc1809820433774da9e7fad7346b0becd:{path}"], cwd=root).decode("utf-8")
    current = (root / path).read_text(encoding="utf-8")
    def functions(text):
        return {node.name: ast.dump(node, include_attributes=False) for node in ast.parse(text).body if isinstance(node, ast.FunctionDef)}
    for name in ("source_identity", "rewards_component", "_prepare_batch", "import_source_batch"):
        assert functions(accepted)[name] == functions(current)[name], name
