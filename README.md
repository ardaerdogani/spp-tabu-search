# SPP Tabu Search

Tabu Search baseline for Set Partitioning Problem (SPP):

min sum_j c_j x_j
s.t. sum_j a_ij x_j = 1 for all i
x_j in {0,1}

## Install (editable)
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e .

## Run
spp-tabu --instance data/instance.txt --seed 0 --time 10

## Batch
python scripts/run_batch.py --pattern "data/*.txt" --seeds 10 --time 10