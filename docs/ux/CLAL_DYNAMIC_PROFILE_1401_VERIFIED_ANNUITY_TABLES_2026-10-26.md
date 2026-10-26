# RETIRE V2 — Clal 1401 exact coefficient audit (2026-10-26)

**RESEARCH ONLY. No coefficient lookup, scenario financial result, CI, merge or deployment.**

Primary source: official Clal 32-page PDF at https://www.clalbit.co.il/media/26472/נספח-תכניות-ביטוח-מנהלים-כולל-מקדמי-קצבה-מובטחים-תוחלת-חיים-1401.pdf . Actual document is edition 07/2023, program/appendix 1401, "פרופיל דינמי הדור החדש". PDF pages 11–14 (0-based pages 10–13) were read; source image check of pages 12 and 14 was performed. Four precise schedules are identified. **All shown figures are original 2022 BASE factors, not adjusted to 2026 or proven applicable to a specific client.**

| PDF page (printed) | option | age | male_2022 | male_annual_increment_percent | female_2022 | female_annual_increment_percent |
|---|---|---:|---:|---:|---:|---:|
|11|240 guaranteed payments|60|220.78|0.0867|228.08|0.0843|
|11|240 guaranteed payments|65|204.33|0.0853|211.09|0.0876|
|11|240 guaranteed payments|67|198.16|0.0797|204.42|0.0843|
|11|240 guaranteed payments|70|189.87|0.0650|195.18|0.0733|
|11|240 guaranteed payments|75|180.88|0.0326|183.69|0.0401|
|11|240 guaranteed payments|80|177.28|0.0092|178.51|0.0110|
|12|180 guaranteed payments|60|217.20|0.1059|225.39|0.1001|
|12|180 guaranteed payments|65|197.95|0.1202|206.10|0.1179|
|12|180 guaranteed payments|67|189.79|0.1261|197.98|0.1224|
|12|180 guaranteed payments|70|178.01|0.1206|185.54|0.1236|
|12|180 guaranteed payments|75|160.82|0.0956|166.61|0.1056|
|12|180 guaranteed payments|80|150.02|0.0493|153.05|0.0599|
|13|300 guaranteed payments|60|226.07|0.0619|232.11|0.0630|
|13|300 guaranteed payments|65|214.16|0.0468|218.83|0.0521|
|13|300 guaranteed payments|67|210.52|0.0375|214.40|0.0437|
|13|300 guaranteed payments|70|206.59|0.0232|209.26|0.0287|
|13|300 guaranteed payments|75|203.53|0.0066|204.86|0.0078|
|13|300 guaranteed payments|80|202.81|0.0008|203.87|0.0007|
|14|240 payments + 60% lifelong spouse survivor|60|231.58|0.0754|232.49|0.0776|
|14|240 payments + 60% lifelong spouse survivor|65|219.54|0.0823|214.59|0.0870|
|14|240 payments + 60% lifelong spouse survivor|67|212.65|0.0840|207.36|0.0865|
|14|240 payments + 60% lifelong spouse survivor|70|202.59|0.0818|197.17|0.0781|
|14|240 payments + 60% lifelong spouse survivor|75|188.29|0.0605|184.35|0.0443|
|14|240 payments + 60% lifelong spouse survivor|80|179.94|0.0274|179.07|0.0160|

**Source applicability rules, not approximations:**

- Base year 2022, each sex/age/option has its own specified yearly coefficient adjustment. Before any future application require valid policy/rider/version and confirm adjustment convention and later endorsed riders.
- The 60%-survivor + 240 payment table assumes a **male insured four years older than his wife**, or **female insured four years younger than her husband**. Other spouse-age differences require an insurer-determined coefficient under the same actuarial assumptions. *Do not use this table with an arbitrary age gap or assume 60% alone is enough.*
- All four annexes specify 4% annual gross technical interest and annual pensioner management deductions up to 0.3%; lifetime assumptions are fixed subject to terms, while changes in technical interest can generate a regulator-approved revised rider.
- 60% survivor AND 240 guaranteed payments is a **combined** option and must not be confused with a stand-alone 60% spouse pension.
- The document explains that certain increased or one-time deposits can carry coefficient terms different from initial policy deposits. Do not treat insurer + policy name alone as proof that all balances share a single factor.
- Age range for these schedules: 60–80. For out-of-range cases, block or require specific insurer quote.
- Official XLSX sources at https://www.clalbit.co.il/allowancecoefficients/ were verified to exist with five archive years/variants, but binary download was not supported by web and network DNS is disabled in the execution container. The spreadsheets were **not** parsed or numerically verified here.

**Current accepted direction:** insurer+policy+edition+option+age/sex+spouse gap+payment guarantee+applicable deposits/technical-interest basis must be explicitly matched. Planner-selected decision-scoped manual factor and evidence/option notes are required once independently authorized. Do not duplicate `annuity_coefficient_service`, do not use its `200` default.

**Independent acceptance still required:** precise scenario-specific monthly-basis authority and approved adapter/fingerprints in Stage 6. This documentary artifact is not an implementation acceptance or authority.
