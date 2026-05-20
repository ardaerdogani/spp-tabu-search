# SPP Tabu Search

`spp-tabu` is a Python tabu-search solver for the Set Partitioning Problem (SPP). The repository provides:

- an OR-LIB SPP parser,
- a randomized-greedy initial construction,
- a 1-flip tabu search with an adaptive feasibility penalty, and
- a CLI for single runs.

The optimization model is:

```text
min sum_j c_j x_j
s.t. sum_j a_ij x_j = 1 for all i
x_j in {0,1}
```

## Installation

The package requires Python 3.10 or newer. All commands below assume you run them from the project root.

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e .
```

## Quick Start

Run the bundled OR-LIB benchmark instance:

```bash
spp-tabu --instance data/sppnw01.txt --seed 0 --time 30
```

Expected output (cost will vary by seed and machine):

```text
Best feasible cost=197940 | selected cols=48 | iters=7409 | elapsed=30.00s
```

## Configuration Options

These are the current user-facing CLI options exposed by [`src/spp_tabu/cli.py`](src/spp_tabu/cli.py):

| Option | Type | Default | Description |
| --- | --- | --- | --- |
| `--instance` | path | required | Path to an OR-LIB SPP instance file. |
| `--seed` | int | `0` | Random seed used by the solver. |
| `--time` | float | `10.0` | Time limit in seconds. |
| `--iters` | int | `200000` | Maximum tabu-search iterations. |
| `--base-tenure` | int | `10` | Minimum tabu tenure after each flip. |
| `--tenure-rand` | int | `10` | Random additive tenure (uniform `0..--tenure-rand`). |

The solver also has constructor-level defaults in [`src/spp_tabu/tabu.py`](src/spp_tabu/tabu.py). These are documented here for transparency, but they are not exposed in the CLI today.

| Parameter | Default | Role |
| --- | --- | --- |
| `base_tenure` | `10` | Minimum tabu tenure after a flip. |
| `tenure_rand` | `10` | Random extra tabu tenure added to `base_tenure`. |
| `stall_limit` | `20000` | Number of non-improving iterations before perturbation. |
| `cand_mult` | `30` | Candidate cap multiplier based on violated rows. |
| `lam` | `10.0` | Initial feasibility-penalty weight in the penalized objective. |

## Input Format

[`src/spp_tabu/parser.py`](src/spp_tabu/parser.py) implements the OR-LIB set partitioning format:

```text
m n
cost_1 k_1 r_1 ... r_k
cost_2 k_2 r_1 ... r_k
...
cost_n k_n r_1 ... r_k
```

- `m` is the number of rows.
- `n` is the number of columns.
- Each column line stores its cost, the number of covered rows, and the covered row indices.
- OR-LIB row indices are 1-based in the file and converted to 0-based internally.

## Algorithm Overview

The solver in [`src/spp_tabu/tabu.py`](src/spp_tabu/tabu.py) uses a randomized construction phase followed by a 1-flip tabu search with adaptive penalty updates.

```mermaid
flowchart LR
    A["Load OR-LIB instance"] --> B["Randomized construction"]
    B --> C["Greedy uncovered-row repair"]
    C --> D["Redundant-column cleanup"]
    D --> E["Start tabu iterations"]
    E --> F["Sample candidate columns from violated rows"]
    F --> G["Check tabu status and aspiration"]
    G --> H["Apply best flip move"]
    H --> I["Update lambda and feasibility state"]
    I --> J["Perturb solution if stalled"]
    J --> K["Stop on time limit or iteration cap"]
```

Implementation summary:

- `_initial_solution_randomized()` repeatedly builds a partial solution by selecting columns that cover uncovered rows while trying to minimize overlap.
- `_initial_solution_greedy()` repairs remaining uncovered rows and removes redundant selected columns when exact coverage is preserved.
- `solve()` then runs a 1-flip neighborhood search with tabu tenure, aspiration, adaptive penalty scaling for infeasibility, and a random perturbation after long stalls.
- Candidate moves are focused on columns incident to violated rows, with sampling used to cap the search effort.
- The construction phase is capped at `min(--time / 2, 10)` seconds so the tabu loop always gets a fair share of the budget, even on large instances where construction can otherwise stall.

## Code Structure

Repository map:

- [`src/spp_tabu/parser.py`](src/spp_tabu/parser.py): parses OR-LIB instances into the `SPPInstance` dataclass.
- [`src/spp_tabu/tabu.py`](src/spp_tabu/tabu.py): implements initialization, neighborhood evaluation, tabu logic, and solve-time bookkeeping.
- [`src/spp_tabu/cli.py`](src/spp_tabu/cli.py): resolves input paths, parses CLI options, and prints solver output.

## Benchmark Datasets

Six OR-Library `sppnw` instances are committed under [`data/`](data/): `sppnw01`, `sppnw06`, `sppnw10`, `sppnw20`, `sppnw41`, and `sppnw43`. The broader external benchmark family is the OR-LIB SPP suite, including `sppnw*`, `sppaa*`, `sppus*`, and `sppkl*`.
