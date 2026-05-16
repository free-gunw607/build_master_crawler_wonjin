# SOURCE FREEZE

- freeze date: 2026-05-16
- policy: keep source parser contracts stable unless site HTML structure changes.
- frozen modules:
  - `src/build_master_crawler_wonjin/main.py`:
    - LH parser (`wrtancInfoBtn` + `panId` contract)
    - i-SH parser (`getDetailView(seq)` contract)
    - GH parser (`goAnnounceView(annSeq)` contract, EUC-KR decode)
- verification snapshot:
  - 1-year run counts: LH 67 / iSH 48 / GH 57 (total 172)
  - workbook: `output/notices_first_run_1y_prod.xlsx`

## Change Trigger
Only unfreeze when one of below is observed:
1. selector miss or row count collapse
2. identifier field change (`panId`, `seq`, `annSeq`)
3. date column layout change causing incremental filter drift
