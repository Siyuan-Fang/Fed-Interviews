# Provenance

Every table and figure in the paper, with the code that produces it and the
data it reads. All paths are relative to this package.

| Output | Paper location | Code | Input data |
|---|---|---|---|
| Table 1 | Section 2, summary statistics | `Code/table1/generate_matched.py`, `Code/table1/run_table1.py` | `Data/common/{events,raw,auxiliary}/` → `Data/common/matched/` |
| Table 2 | Section 3, importance by announcement type | `Code/table2/run_table2.py` | `Data/common/matched/`, `Data/table2/overtime_sum_variance.csv` |
| Table 3 Panel A | Section 5, forward guidance effects | `Code/table3/01_prepare_reg_inputs.py`, `02_build_forward_guidance.py`, `03_estimate_table3_panel_a.py` | `Data/common/matched/` → `Data/table3/reg_*.csv`, `factor_*.csv` |
| Figure 1 | Section 2, histograms | `Code/figure1/run_figure1.py` | `Data/common/matched/` |
| Figure 2 | Section 4, importance over time | `Code/figure2/run_figure2.py` | `Data/table2/overtime_sum_variance.csv` |
| Figure 3 | Section 5, FOMC announcement responses | `Code/figure3/run_figure3.m` | `Data/figure3/reg_fomc_announcement.csv` |
| Figure 4 | Section 5, Fed Chair speech responses | `Code/figure4_6/run_figures_4_5_6.m` | `Data/figure4_6/reg_baha_powell_79.csv` |
| Figure 5 | Section 5, interview responses, top 100 | `Code/figure4_6/run_figures_4_5_6.m` | `Data/figure4_6/reg_interview_top100_without200402.csv` |
| Figure 6 | Section 5, interview responses, top 200 | `Code/figure4_6/run_figures_4_5_6.m` | `Data/figure4_6/reg_interviews_top200.csv` |

Outputs are written to `Tables/<id>/` and `Figures/<id>/`.

## Scope

This package covers Tables 1–3 Panel A and Figures 1–6. Table 3 Panel B,
Table 4, and Figure 7 are not included.

## Notes

- Figure 5 uses a top-100 sample that excludes the 2004-02 observation; see
  `Data/figure4_6/README.md`.
- The `MP1`, `TFUT02`, `TFUT10`, and `transfact1` columns read by the MATLAB
  estimation were prepared outside the Python pipeline in this package and are
  committed as given; see `Code/README.md`.
- The raw futures files are too large for GitHub and are not committed. They
  are only needed to regenerate `Data/common/matched/`, which is committed, so
  every table and figure here reproduces without them. See
  `Data/common/README.md`.
