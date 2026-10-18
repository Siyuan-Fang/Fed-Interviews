# Replication Package

This is the replication package for the paper. It is organized around the
paper's tables and figures, so each output traces back to the code and data
that produced it. [`trace_table.md`](trace_table.md) maps every output to its
code and inputs.

It covers Tables 1–3 Panel A and Figures 1–6.

## Directory layout

```text
main/
├── README.md
├── trace_table.md
├── requirements.txt
├── Code/
│   ├── README.md
│   ├── common/matlab/
│   ├── table1/
│   ├── table2/
│   ├── table3/
│   ├── figure1/
│   ├── figure2/
│   ├── figure3/
│   └── figure4_6/
├── Data/
│   ├── README.md
│   ├── common/
│   ├── figure3/
│   ├── figure4_6/
│   ├── table2/
│   └── table3/
├── Tables/
│   ├── README.md
│   ├── table1/
│   ├── table2/
│   └── table3/
└── Figures/
    ├── README.md
    ├── figure1/
    ├── figure2/
    ├── figure3/
    ├── figure4/
    ├── figure5/
    └── figure6/
```

Each table or figure gets a stable identifier, for example `table1` or
`figure3`. Its code lives in `Code/<id>/`, and its output in `Tables/<id>/` or
`Figures/<id>/`. Shared inputs live in `Data/common/`; table-specific inputs
live in `Data/<id>/`.

## How to add a new table or figure

1. Add a row to [`trace_table.md`](trace_table.md).
2. Create `Code/<id>/`, and either `Tables/<id>/` or `Figures/<id>/`. Only add
   `Data/<id>/` for data that is not shared.
3. Number scripts in execution order: `01_...`, `02_...`.
4. Keep shared input data under `Data/common/` and table-specific input data
   under `Data/<id>/`.
5. Document raw upstream files and external data sources in `Data/common/README.md`
   or `Data/<id>/README.md`.
6. Record the output and its provenance in `Tables/<id>/README.md` or `Figures/<id>/README.md`.

## Requirements

Python 3.12 with the packages in [`requirements.txt`](requirements.txt):

```bash
pip install -r requirements.txt
```

Figures 3–6 additionally require MATLAB (verified on R2021b) with the
Optimization Toolbox.

## Quick start for Table 1

To regenerate the matched inputs and recompute Table 1:

```bash
python3 Code/table1/generate_matched.py
python3 Code/table1/run_table1.py
```

If the matched inputs already exist, only the second command is required.

## Quick start for Table 2

```bash
python3 Code/table2/run_table2.py
```

## Quick start for Table 3 Panel A

```bash
python3 Code/table3/01_prepare_reg_inputs.py
python3 Code/table3/02_build_forward_guidance.py
python3 Code/table3/03_estimate_table3_panel_a.py
```

## Quick start for Figure 1

```bash
python3 Code/figure1/run_figure1.py
```

## Quick start for Figure 2

```bash
python3 Code/figure2/run_figure2.py
```

## Quick start for Figure 3

Run in MATLAB from the package root:

```matlab
addpath('Code/figure3')
run_figure3
```

## Quick start for Figures 4–6

Run in MATLAB from the package root:

```matlab
addpath('Code/figure4_6')
run_figures_4_5_6(4)
run_figures_4_5_6(5)
run_figures_4_5_6(6)
```

Figures 3–6 were developed and verified on MATLAB R2021b and require the
Optimization Toolbox.
