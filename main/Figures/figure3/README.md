# Figure 3

Figure 3 shows FOMC announcement shock responses with 95% bands.

## Output

- [`figure3_full.png`](figure3_full.png)
- [`figure3_full.pdf`](figure3_full.pdf)

The paper uses this full figure and crops it with LaTeX `\adjustbox{trim=...}`
into four shock panels.

## How it is generated

Run in MATLAB from the package root:

```matlab
addpath('Code/figure3')
run_figure3
```

`run_figure3(seed)` accepts an optional seed; the default is `0`.

## Inputs

- [`Data/figure3/reg_fomc_announcement.csv`](../../Data/figure3/reg_fomc_announcement.csv) — 45 FOMC announcement windows
- Code: [`Code/figure3/run_figure3.m`](../../Code/figure3/run_figure3.m),
  [`Code/figure3/private/plot_resp.m`](../../Code/figure3/private/plot_resp.m),
  [`Code/figure3/private/normalize1.m`](../../Code/figure3/private/normalize1.m)
- Shared MATLAB helpers: [`Code/common/matlab/`](../../Code/common/matlab/)

The model uses four variables (`MP1`, `TFUT02`, `TFUT10`, `SP500`), so it has
four shocks. This is why Figure 3 has four panels while Figures 4–6, which use
only `TFUT02` and `SP500`, have two.

## Also written

- `Data/figure3/figure3_maxl.mat` — estimated `C`, `W`, `U`, and variance decomposition
- `Data/figure3/figure3_U.csv`, `figure3_U1s.csv`, `figure3_U1bp.csv` — extracted shocks

## Reproducibility note

`run_figure3.m` seeds the random starting point with `rng(seed, "twister")`
so that repeated runs give the same estimates. The default seed is `0`.
