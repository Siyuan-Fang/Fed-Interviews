# Code

Code is organized by table/figure identifier. Each directory is self-contained
where practical and uses relative paths from the repository root.

## Conventions

- Directory names use lowercase identifiers such as `table1` and `figure3`.
- Scripts are numbered by execution order: `01_`, `02_`, and so on.
- Do not hardcode absolute local paths. Use environment variables or paths
  relative to the repository root.
- Document dependencies and run order in each directory's `README.md`.

## Current code

| Artifact | Directory | Purpose |
|---|---|---|
| Table 1 | [`table1/`](table1/) | Match event windows and compute summary statistics |
| Table 2 | [`table2/`](table2/) | Compute importance measures from shared matched data |
| Table 3 | [`table3/`](table3/) | Prepare reg inputs, build factors, and estimate Panel A |
| Figure 1 | [`figure1/`](figure1/) | Generate announcement-effect histograms |
| Figure 2 | [`figure2/`](figure2/) | Generate rolling importance plots |
| Figure 3 | [`figure3/`](figure3/) | Estimate FOMC shocks and plot response bands (MATLAB) |
| Figures 4–6 | [`figure4_6/`](figure4_6/) | Estimate Chair speech and interview shock responses (MATLAB) |
| Shared | [`common/matlab/`](common/matlab/) | MATLAB helpers used by both `figure3/` and `figure4_6/` |

## MATLAB code

Figures 3–6 are produced in MATLAB (developed and verified on R2021b; requires
Optimization Toolbox for `fminunc`/`fmincon`). Both drivers resolve paths
relative to the package root and add `Code/common/matlab` to the path
themselves, so they can be run from any working directory:

```matlab
addpath('Code/figure3');   run_figure3
addpath('Code/figure4_6'); run_figures_4_5_6(4)
```

`plot_resp.m` exists in **two incompatible versions** and is deliberately not
shared. The `figure3` version takes positional arguments
(`plot_resp(Cm, Cl, Cu, maturities, names)`); the `figure4_6` version takes
name-value arguments (`variableNames=`, `RowLabels=`, `showTitles=`).

Because they share a name, each lives in its driver's `private/` subdirectory
(`figure3/private/`, `figure4_6/private/`). MATLAB resolves `private/`
functions only for the driver in the parent directory, so both drivers can be
on the path at once without one shadowing the other. Do not move these files
up into `Code/common/matlab/`.

`kr.m` and `nlogl_iidstudent_Wzn.m` are byte-identical across the two versions
and are shared from `common/matlab/`.

## Data not produced by this package

The `MP1`, `TFUT02`, `TFUT10`, and `transfact1` columns consumed by the MATLAB
estimation were prepared separately and are committed under `Data/figure3/`
and `Data/figure4_6/` as the authoritative copies. Figures 3–6 reproduce
exactly from those files.

For provenance details, see [`Data/common/README.md`](../Data/common/README.md).
