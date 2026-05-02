**Golden Fixation Cases For V1**

Assumed locked V1 formulas:

```text
initial_exempt_capital = monthly_cap * 180 * exemption_percentage
grant_limited_amount = round(indexed_full * ratio_32y, 2)
grant_impact = 0 if 15-year exclusion applies, else round(grant_limited_amount * 1.35, 2)
future_grant_impact = future_grant_reserved * 1.35
actual_capitalization_impact = sum(actual_capitalizations)
idf_impact = round(min(reduction_amount * original_percent / current_percent, monthly_cap * 0.35) * overlap_months, 2)
total_impact = grant_impact_total + future_grant_impact + actual_capitalization_impact + idf_impact
remaining_exempt_capital = max(initial_exempt_capital - total_impact, 0)
monthly_exempt_pension = round(remaining_exempt_capital / 180, 2)
capital_exemption_percentage = remaining_exempt_capital / initial_exempt_capital
pension_exemption_percentage = (remaining_exempt_capital / 180) / monthly_cap
```

All cases use:

```json
{
  "eligibility_date": "2025-01-01",
  "eligibility_year": 2025,
  "monthly_cap": 9430,
  "exemption_percentage": 0.57,
  "multiplier": 180,
  "initial_exempt_capital": 967518
}
```

**1. Base Case**

Input:
```json
{
  "grants": [],
  "future_grant_reserved": 0,
  "actual_capitalizations": [],
  "idf": null
}
```

Expected output:
```json
{
  "grant_impact_total": 0,
  "future_grant_impact": 0,
  "actual_capitalization_impact": 0,
  "idf_impact": 0,
  "total_impact": 0,
  "remaining_exempt_capital": 967518,
  "monthly_exempt_pension": 5375.10,
  "capital_exemption_percentage": 1.000000000000,
  "pension_exemption_percentage": 0.570000000000,
  "audit_rows": []
}
```

**2. Single Grant With Full Impact**

Input:
```json
{
  "grants": [
    {
      "id": "G1",
      "grant_amount": 100000,
      "indexed_full": 100000,
      "grant_date": "2024-01-01",
      "work_start_date": "2020-01-01",
      "work_end_date": "2021-01-01",
      "ratio_32y": 1,
      "years_from_grant_to_eligibility": 1,
      "excluded_by_15_year_rule": false
    }
  ],
  "future_grant_reserved": 0,
  "actual_capitalizations": [],
  "idf": null
}
```

Expected output:
```json
{
  "grant_rows": [
    {
      "id": "G1",
      "limited_indexed_amount": 100000,
      "impact": 135000
    }
  ],
  "grant_impact_total": 135000,
  "future_grant_impact": 0,
  "actual_capitalization_impact": 0,
  "idf_impact": 0,
  "total_impact": 135000,
  "remaining_exempt_capital": 832518,
  "monthly_exempt_pension": 4625.10,
  "capital_exemption_percentage": 0.860467712229,
  "pension_exemption_percentage": 0.490466595970
}
```

**3. Grant With 15-Year Exclusion**

Input:
```json
{
  "grants": [
    {
      "id": "G1",
      "grant_amount": 100000,
      "indexed_full": 100000,
      "grant_date": "2000-01-01",
      "work_start_date": "1999-01-01",
      "work_end_date": "2000-01-01",
      "ratio_32y": 1,
      "years_from_grant_to_eligibility": 25,
      "excluded_by_15_year_rule": true
    }
  ],
  "future_grant_reserved": 0,
  "actual_capitalizations": [],
  "idf": null
}
```

Expected output:
```json
{
  "grant_rows": [
    {
      "id": "G1",
      "limited_indexed_amount": 100000,
      "impact": 0,
      "exclusion_reason": "15_year_rule"
    }
  ],
  "grant_impact_total": 0,
  "total_impact": 0,
  "remaining_exempt_capital": 967518,
  "monthly_exempt_pension": 5375.10,
  "capital_exemption_percentage": 1.000000000000,
  "pension_exemption_percentage": 0.570000000000
}
```

**4. Grant With Partial 32-Year Ratio**

Input:
```json
{
  "grants": [
    {
      "id": "G1",
      "grant_amount": 100000,
      "indexed_full": 100000,
      "grant_date": "2024-01-01",
      "work_start_date": "1990-01-01",
      "work_end_date": "2000-01-01",
      "eligibility_date": "2025-01-01",
      "window_start": "1993-01-01",
      "total_days": 3652,
      "overlap_days": 2556,
      "ratio_32y": 0.699890470974808,
      "excluded_by_15_year_rule": false
    }
  ],
  "future_grant_reserved": 0,
  "actual_capitalizations": [],
  "idf": null
}
```

Expected output:
```json
{
  "grant_rows": [
    {
      "id": "G1",
      "limited_indexed_amount": 69989.05,
      "impact": 94485.22
    }
  ],
  "grant_impact_total": 94485.22,
  "total_impact": 94485.22,
  "remaining_exempt_capital": 873032.78,
  "monthly_exempt_pension": 4850.18,
  "capital_exemption_percentage": 0.902342674762,
  "pension_exemption_percentage": 0.514335324614
}
```

**5. Multiple Grants Combined**

Input:
```json
{
  "grants": [
    {
      "id": "G1",
      "indexed_full": 100000,
      "ratio_32y": 1,
      "excluded_by_15_year_rule": false
    },
    {
      "id": "G2",
      "indexed_full": 50000,
      "ratio_32y": 1,
      "excluded_by_15_year_rule": false
    },
    {
      "id": "G3",
      "indexed_full": 100000,
      "ratio_32y": 0.699890470974808,
      "excluded_by_15_year_rule": false
    }
  ],
  "future_grant_reserved": 0,
  "actual_capitalizations": [],
  "idf": null
}
```

Expected output:
```json
{
  "grant_rows": [
    {
      "id": "G1",
      "limited_indexed_amount": 100000,
      "impact": 135000
    },
    {
      "id": "G2",
      "limited_indexed_amount": 50000,
      "impact": 67500
    },
    {
      "id": "G3",
      "limited_indexed_amount": 69989.05,
      "impact": 94485.22
    }
  ],
  "grant_impact_total": 296985.22,
  "total_impact": 296985.22,
  "remaining_exempt_capital": 670532.78,
  "monthly_exempt_pension": 3725.18,
  "capital_exemption_percentage": 0.693044243105,
  "pension_exemption_percentage": 0.395035218570
}
```

**6. Future Grant Reserve Only**

Input:
```json
{
  "grants": [],
  "future_grant_reserved": 50000,
  "actual_capitalizations": [],
  "idf": null
}
```

Expected output:
```json
{
  "grant_impact_total": 0,
  "future_grant_impact": 67500,
  "actual_capitalization_impact": 0,
  "idf_impact": 0,
  "total_impact": 67500,
  "remaining_exempt_capital": 900018,
  "monthly_exempt_pension": 5000.10,
  "capital_exemption_percentage": 0.930233856114,
  "pension_exemption_percentage": 0.530233297985,
  "audit_rows": [
    {
      "type": "future_grant_reserve",
      "amount": 50000,
      "factor": 1.35,
      "impact": 67500
    }
  ]
}
```

**7. Actual Capitalization Impact**

Input:
```json
{
  "grants": [],
  "future_grant_reserved": 0,
  "actual_capitalizations": [
    {
      "id": "C1",
      "amount": 120000
    }
  ],
  "idf": null
}
```

Expected output:
```json
{
  "grant_impact_total": 0,
  "future_grant_impact": 0,
  "actual_capitalization_impact": 120000,
  "idf_impact": 0,
  "total_impact": 120000,
  "remaining_exempt_capital": 847518,
  "monthly_exempt_pension": 4708.43,
  "capital_exemption_percentage": 0.875971299759,
  "pension_exemption_percentage": 0.499303640862,
  "audit_rows": [
    {
      "type": "actual_capitalization",
      "id": "C1",
      "impact": 120000
    }
  ]
}
```

**8. IDF Impact Case**

Input:
```json
{
  "grants": [],
  "future_grant_reserved": 0,
  "actual_capitalizations": [],
  "idf": {
    "reduction_amount": 1000,
    "original_commutation_percent": 25,
    "current_commutation_percent": 20,
    "monthly_cap": 9430,
    "eligibility_date": "2025-01-01",
    "commutation_date": "2025-01-01",
    "promoter_age_date": "2027-01-01",
    "overlap_months": 24
  }
}
```

Expected output:
```json
{
  "idf": {
    "base_reduction": 1250,
    "max_reduction": 3300.50,
    "monthly_reduction_for_calc": 1250,
    "overlap_months": 24,
    "impact": 30000
  },
  "grant_impact_total": 0,
  "future_grant_impact": 0,
  "actual_capitalization_impact": 0,
  "idf_impact": 30000,
  "total_impact": 30000,
  "remaining_exempt_capital": 937518,
  "monthly_exempt_pension": 5208.43,
  "capital_exemption_percentage": 0.968992824940,
  "pension_exemption_percentage": 0.552325910216
}
```

**9. Combined Full Scenario**

Input:
```json
{
  "grants": [
    {
      "id": "G1",
      "indexed_full": 100000,
      "ratio_32y": 1,
      "excluded_by_15_year_rule": false
    },
    {
      "id": "G2",
      "indexed_full": 50000,
      "ratio_32y": 1,
      "excluded_by_15_year_rule": false
    }
  ],
  "future_grant_reserved": 30000,
  "actual_capitalizations": [
    {
      "id": "C1",
      "amount": 120000
    }
  ],
  "idf": {
    "reduction_amount": 1000,
    "original_commutation_percent": 25,
    "current_commutation_percent": 20,
    "monthly_cap": 9430,
    "overlap_months": 24
  }
}
```

Expected output:
```json
{
  "grant_rows": [
    {
      "id": "G1",
      "limited_indexed_amount": 100000,
      "impact": 135000
    },
    {
      "id": "G2",
      "limited_indexed_amount": 50000,
      "impact": 67500
    }
  ],
  "grant_impact_total": 202500,
  "future_grant_impact": 40500,
  "actual_capitalization_impact": 120000,
  "idf_impact": 30000,
  "total_impact": 393000,
  "remaining_exempt_capital": 574518,
  "monthly_exempt_pension": 3191.77,
  "capital_exemption_percentage": 0.593806006710,
  "pension_exemption_percentage": 0.338469423825
}
```

**10. Edge Case: Zero Remaining Exemption**

Input:
```json
{
  "grants": [
    {
      "id": "G1",
      "indexed_full": 888888.89,
      "ratio_32y": 1,
      "excluded_by_15_year_rule": false
    }
  ],
  "future_grant_reserved": 0,
  "actual_capitalizations": [],
  "idf": null
}
```

Expected output:
```json
{
  "grant_rows": [
    {
      "id": "G1",
      "limited_indexed_amount": 888888.89,
      "impact": 1200000.00
    }
  ],
  "grant_impact_total": 1200000.00,
  "total_impact": 1200000.00,
  "remaining_exempt_capital": 0,
  "monthly_exempt_pension": 0,
  "capital_exemption_percentage": 0,
  "pension_exemption_percentage": 0
}
```

**11. Edge Case: Ratio Boundaries**

Input:
```json
{
  "grants": [
    {
      "id": "R0",
      "indexed_full": 100000,
      "work_start_date": "1980-01-01",
      "work_end_date": "1990-01-01",
      "eligibility_date": "2025-01-01",
      "window_start": "1993-01-01",
      "ratio_32y": 0,
      "excluded_by_15_year_rule": false
    },
    {
      "id": "R1",
      "indexed_full": 100000,
      "work_start_date": "2020-01-01",
      "work_end_date": "2021-01-01",
      "eligibility_date": "2025-01-01",
      "window_start": "1993-01-01",
      "ratio_32y": 1,
      "excluded_by_15_year_rule": false
    }
  ],
  "future_grant_reserved": 0,
  "actual_capitalizations": [],
  "idf": null
}
```

Expected output:
```json
{
  "grant_rows": [
    {
      "id": "R0",
      "limited_indexed_amount": 0,
      "impact": 0
    },
    {
      "id": "R1",
      "limited_indexed_amount": 100000,
      "impact": 135000
    }
  ],
  "grant_impact_total": 135000,
  "total_impact": 135000,
  "remaining_exempt_capital": 832518,
  "monthly_exempt_pension": 4625.10,
  "capital_exemption_percentage": 0.860467712229,
  "pension_exemption_percentage": 0.490466595970
}
```