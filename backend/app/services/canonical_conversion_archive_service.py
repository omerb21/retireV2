def install_conversion_guards(connection, tables):
    """Database-enforced history retention, independent of API reachability."""
    immutable = {"canonical_conversion_allocations", "canonical_conversion_reversals"}
    mutable = {
        "canonical_conversion_batches": {"result"},
        "canonical_conversions": {"status", "version", "reversed_at"},
        "canonical_pension_destinations": {"status", "version", "reversed_at"},
        "capital_asset": {"lifecycle_status", "updated_at"},
    }
    for table in tables:
        name = table.name
        fields = [c.name for c in table.columns if c.name not in mutable.get(name, set())]
        archive = "OLD.origin_kind = 'canonical_component_conversion'" if name == "capital_asset" else "1=1"
        # A capital destination may retire only with its canonical reversal
        # record already present in this transaction. Retirement is terminal.
        capital_transition_bad = """(OLD.lifecycle_status <> 'current'
            OR NEW.lifecycle_status <> 'superseded' OR NOT EXISTS (
              SELECT 1 FROM canonical_conversions c
              JOIN canonical_conversion_reversals r ON r.conversion_id = c.conversion_id
              WHERE c.conversion_id = OLD.conversion_id AND c.client_id = OLD.client_id
                AND r.client_id = OLD.client_id AND c.status = 'reversed'))"""
        if connection.dialect.name == "postgresql":
            comparisons = " OR ".join(f'to_jsonb(NEW."{field}") IS DISTINCT FROM to_jsonb(OLD."{field}")' for field in fields)
            update_bad = "TRUE" if name in immutable else "(" + comparisons + ")"
            if name == "canonical_conversion_batches":
                update_bad += " OR OLD.result::jsonb <> '{}'::jsonb"
            if name in {"canonical_conversions", "canonical_pension_destinations"}:
                update_bad += " OR OLD.status <> 'active' OR NEW.status <> 'reversed' OR NEW.version <> OLD.version + 1 OR NEW.reversed_at IS NULL"
            if name == "capital_asset":
                update_bad += f" OR (NEW.lifecycle_status IS DISTINCT FROM OLD.lifecycle_status AND {capital_transition_bad})"
                update_bad = f"(({archive}) AND ({update_bad})) OR NEW.origin_kind IS DISTINCT FROM OLD.origin_kind OR NEW.conversion_id IS DISTINCT FROM OLD.conversion_id"
            fn = "guard_" + name + "_canonical"
            connection.exec_driver_sql(f"""CREATE FUNCTION {fn}() RETURNS trigger LANGUAGE plpgsql AS $$
                BEGIN
                  IF TG_OP = 'DELETE' THEN
                    IF {archive} THEN RAISE EXCEPTION 'CANONICAL_CONVERSION_HISTORY_IMMUTABLE'; END IF;
                    RETURN OLD;
                  END IF;
                  IF {update_bad} THEN RAISE EXCEPTION 'CANONICAL_CONVERSION_HISTORY_IMMUTABLE'; END IF;
                  RETURN NEW;
                END $$""")
            connection.exec_driver_sql(f"CREATE TRIGGER trg_{name}_canonical BEFORE UPDATE OR DELETE ON {name} FOR EACH ROW EXECUTE FUNCTION {fn}()")
        else:
            comparisons = " OR ".join(f'NEW."{field}" IS NOT OLD."{field}"' for field in fields)
            update_bad = "1=1" if name in immutable else "(" + comparisons + ")"
            if name == "canonical_conversion_batches":
                update_bad += " OR OLD.result <> '{}'"
            if name in {"canonical_conversions", "canonical_pension_destinations"}:
                update_bad += " OR OLD.status <> 'active' OR NEW.status <> 'reversed' OR NEW.version <> OLD.version + 1 OR NEW.reversed_at IS NULL"
            if name == "capital_asset":
                update_bad += f" OR (NEW.lifecycle_status IS NOT OLD.lifecycle_status AND {capital_transition_bad})"
                update_bad = f"(({archive}) AND ({update_bad})) OR NEW.origin_kind IS NOT OLD.origin_kind OR NEW.conversion_id IS NOT OLD.conversion_id"
            connection.exec_driver_sql(f"""CREATE TRIGGER trg_{name}_canonical_delete BEFORE DELETE ON {name}
                WHEN {archive} BEGIN SELECT RAISE(ABORT, 'CANONICAL_CONVERSION_HISTORY_IMMUTABLE'); END""")
            connection.exec_driver_sql(f"""CREATE TRIGGER trg_{name}_canonical_update BEFORE UPDATE ON {name}
                WHEN {update_bad} BEGIN SELECT RAISE(ABORT, 'CANONICAL_CONVERSION_HISTORY_IMMUTABLE'); END""")
