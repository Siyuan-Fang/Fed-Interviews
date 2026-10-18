# Table 3 Data

## Directory contents

```text
Data/table3/
├── reg_*.csv      # Table 3 regression inputs
└── factor_*.csv   # standardized forward-guidance factors
```

The regression inputs are built from shared matched files:

```text
Data/common/matched/
```

## Scripts

- `Code/table3/01_prepare_reg_inputs.py` creates `reg_*.csv`.
- `Code/table3/02_build_forward_guidance.py` creates `factor_*.csv`.
