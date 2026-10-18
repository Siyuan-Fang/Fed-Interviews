# Figure 3 Data

## Regression input

`reg_fomc_announcement.csv` — 45 FOMC announcement windows, Jan 2019 to Jul
2024, with columns `date`, `MP1`, `ED2`, `ED3`, `ED4`, `SP500`, `TFUT02`,
`TFUT10`, `transfact1`.

The Figure 3 estimation reads `MP1`, `TFUT02`, `TFUT10`, and `SP500`, giving a
four-shock model. Figures 4–6 use only two variables and therefore have two
shocks.

This file is the MATLAB-side counterpart to
[`Data/table3/reg_fomc_announcement.csv`](../table3/reg_fomc_announcement.csv),
which the Python pipeline builds with only `date`, `ED2`, `ED3`, `ED4`, and
`SP500`. The extra `MP1`, `TFUT02`, `TFUT10`, and `transfact1` columns here
were prepared separately; see [`Data/figure4_6/README.md`](../figure4_6/README.md)
for how the `TFUT` columns are constructed.

## Estimation output

Running `run_figure3` writes back into this directory:

```text
figure3_maxl.mat     estimated C, W, U, v, Hessian, variance decomposition
figure3_U.csv        extracted shocks
figure3_U1s.csv      shocks normalized to unit standard deviation
figure3_U1bp.csv     shocks normalized to basis points
```
