# RETIRE V2 | Official Harel More 2022 vs 2024 coefficient evidence | 2026-10-26

STATUS: DOCUMENTARY RESEARCH ONLY. No automated coefficient admission, Stage 6 execution, financial outputs, CI, merge or deployment.

## Primary official sources

- [Harel More 2024, non-guaranteed factor schedule](https://media.harel-group.co.il/media/djjmhmcu/%D7%9E%D7%A7%D7%93%D7%9E%D7%99-%D7%94%D7%9E%D7%A8%D7%94-%D7%9C%D7%A7%D7%A6%D7%91%D7%94-%D7%9E%D7%95%D7%A8-2024.pdf). Official link exposed by the [Harel employee policy landing page](https://www.harel-group.co.il/long-term-savings/independent-and-employees/policies/salaried-employees). Version marked **2024** applies to new joiners from **2025-01-01**, before age 60, with no life expectancy guarantee before age 60.
- [Harel More 2022, non-guaranteed factor schedule](https://media.harel-group.co.il/media/wdzmbivx/%D7%9E%D7%A7%D7%93%D7%9E%D7%99-%D7%94%D7%9E%D7%A8%D7%94-%D7%9C%D7%A7%D7%A6%D7%91%D7%94-%D7%9E%D7%95%D7%A8-2022.pdf). Applies to joiners from **2023-01-01**, before age 60, with no life expectancy guarantee before age 60. **Dates of joining need additional version-precedence confirmation**: publication pages can overlap cohorts and a subsequent rider may supersede prior terms.
- Both official PDF page 1 tables were visually checked in browser screenshot. They describe a **240 guaranteed-payment-month** option (20 years), not a survivor-annuity percentage option. Do not generalize to a 60% continuing spouse pension. 2022 schedule explicitly states basis includes 0.3% management fee.

## Reproducible exact base rows (no future-year roll-forward)

| pension start age | 2022 male | 2022 female | 2022 male annual increase | 2022 female annual increase | 2024 male | 2024 female | 2024 male annual increase | 2024 female annual increase |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
|60|223.16|231.37|0.151%|0.182%|226.70|232.77|0.133%|0.163%|
|65|205.73|213.41|0.163%|0.207%|208.80|214.47|0.147%|0.189%|
|67|199.17|206.32|0.163%|0.212%|201.81|207.22|0.149%|0.195%|
|70|190.46|196.39|0.153%|0.212%|192.29|197.02|0.143%|0.196%|
|75|180.38|183.47|0.113%|0.177%|180.91|183.67|0.106%|0.163%|
|80|175.83|176.52|0.061%|0.109%|175.71|176.51|0.052%|0.094%|

- 2024/2022 base male difference at age 67: (201.81/199.17 - 1)*100 = **1.3255%**. Female age 67: (207.22/206.32 - 1)*100 = **0.4362%**. Comparisons are **different edition base years and insurance joining cohorts**, not two simultaneously applicable policy options. No pricing implication without date normalization.
- Both documents include a formula to roll each age/sex-specific base factor forward from its stated base year using its annual factor increase. That is separate from a policyholder's selected retirement date and requires matching source edition, actual applicable rider and plan. No automatic code implementation authorized.

## Additional newly resolved exact links to Clal official spreadsheet sources

Clal's [official allowance coefficients landing page](https://www.clalbit.co.il/allowancecoefficients/) links to:
- [2001 XLSX](https://www.clalbit.co.il/media/20581/%D7%9E%D7%A7%D7%93%D7%9E%D7%99-%D7%A7%D7%A6%D7%91%D7%94-2001.xlsx)
- [2009 3.5% net technical interest XLSX](https://www.clalbit.co.il/media/20578/%D7%9E%D7%A7%D7%93%D7%9E%D7%99-%D7%A7%D7%A6%D7%91%D7%94-2009-%D7%9C%D7%A4%D7%99-%D7%A8%D7%99%D7%91%D7%99%D7%AA-%D7%AA%D7%97%D7%A9%D7%99%D7%91%D7%99%D7%AA-35-%D7%A0%D7%98%D7%95.xlsx)
- [2009 3% net technical interest XLSX](https://www.clalbit.co.il/media/20580/%D7%9E%D7%A7%D7%93%D7%9E%D7%99%D7%9D-2009-%D7%9C%D7%A4%D7%99-%D7%A8%D7%99%D7%91%D7%99%D7%AA-%D7%AA%D7%97%D7%A9%D7%99%D7%91%D7%99%D7%AA-3-%D7%A0%D7%98%D7%95.xlsx)
- [2013 XLSX](https://www.clalbit.co.il/media/20579/%D7%9E%D7%A7%D7%93%D7%9E%D7%99-%D7%A7%D7%A6%D7%91%D7%94-2013-%D7%9E%D7%A7%D7%93%D7%9E%D7%99-%D7%A0%D7%99%D7%95%D7%93.xlsx)
- [2022 XLSX](https://www.clalbit.co.il/media/e0fls115/%D7%9E%D7%A7%D7%93%D7%9E%D7%99-%D7%A7%D7%A6%D7%91%D7%94-2022.xlsx)

These are exact official link destinations identified, **not numerical data verified**. Web open returned unsupported XLSX content type and direct network download in this analysis environment failed. Do not claim parsing, factor counts or coefficient rows from them yet.

## Contract implications

1. 2022/2024 `הראל More` tables identify a precise product family and pension option, improving provider-specific research coverage beyond generic V1 and historical Harel 2009.
2. Each data record must retain issuer, source URL/hash, edition/base year, target cohort, policy family, sex, age, payment guarantee option, base factor and age/sex/year adjustment field. Avoid silently equating **guaranteed payment months** to **spouse survivor percentage**.
3. Admission still requires evidence connecting a client's actual policy/rider to the archived schedule, otherwise use an appropriately disclosed planning assumption or an authenticated manual coefficient.
4. No new producer: build catalog enrichment under existing `annuity_coefficient_service` after separate independent acceptance. Existing service fallback factor 200 is forbidden for hypothetical financial output.
